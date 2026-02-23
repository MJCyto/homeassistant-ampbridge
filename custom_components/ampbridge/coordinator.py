"""MQTT coordinator for AmpBridge integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
import paho.mqtt.client as mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MQTT_BASE_TOPIC

_LOGGER = logging.getLogger(__name__)
_LOG_PREFIX = "[AmpBridge:source]"


class AmpBridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage AmpBridge MQTT data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.mqtt_client: mqtt.Client | None = None
        self.connected = False
        self.zones: dict[int, dict[str, Any]] = {}
        self.api_url = f"http://{entry.data['host']}:4000/api"
        
        # Initialize with empty data
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # We'll update via MQTT messages
        )

    async def async_start(self) -> None:
        """Start the MQTT client and discover zones."""
        # First discover zones via API
        await self._discover_zones_via_api()
        
        # Then start MQTT client
        await self.hass.async_add_executor_job(self._start_mqtt_client)

    def _start_mqtt_client(self) -> None:
        """Start the MQTT client in executor thread."""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

        try:
            host = self.entry.data["host"]
            port = self.entry.data["port"]
            _LOGGER.info(f"Connecting to MQTT broker at {host}:{port}")
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_start()
        except Exception as err:
            _LOGGER.error(f"Failed to connect to MQTT broker: {err}")
            raise UpdateFailed(f"Failed to connect to MQTT broker: {err}")

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker")
            self.connected = True
            # Subscribe to all zone topics
            client.subscribe(f"{MQTT_BASE_TOPIC}/#")
            _LOGGER.info(f"Subscribed to {MQTT_BASE_TOPIC}/#")
        else:
            _LOGGER.error(f"Failed to connect to MQTT broker: {rc}")
            self.connected = False

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            _LOGGER.debug(f"Received MQTT message: {topic} = {payload}")
            
            # Parse topic to extract zone info
            # Expected format: ampbridge/zones/{zone_id}/{attribute}
            parts = topic.split("/")
            if len(parts) >= 4 and parts[0] == "ampbridge" and parts[1] == "zones":
                try:
                    zone_id = int(parts[2])
                    attribute = parts[3]
                    
                    # Only update existing zones from MQTT, don't create new ones
                    # Zone creation is now handled by API discovery
                    if zone_id not in self.zones:
                        _LOGGER.debug(f"Received MQTT message for unknown zone {zone_id}, skipping")
                        return
                    
                    # Update zone data
                    if attribute == "name":
                        self.zones[zone_id]["name"] = payload
                    elif attribute == "volume":
                        try:
                            self.zones[zone_id]["volume"] = int(payload)
                        except ValueError:
                            _LOGGER.warning(f"Invalid volume value: {payload}")
                    elif attribute == "mute":
                        self.zones[zone_id]["mute"] = payload
                    elif attribute == "source":
                        old_val = self.zones[zone_id].get("source")
                        self.zones[zone_id]["source"] = payload
                        _LOGGER.info(
                            "%s MQTT source zone_id=%s topic=%s old=%s new=%s",
                            _LOG_PREFIX, zone_id, topic, old_val, payload,
                        )
                    elif attribute == "connected":
                        self.zones[zone_id]["connected"] = payload
                    
                    # Trigger update - schedule on the event loop
                    self.hass.loop.call_soon_threadsafe(
                        lambda: self.async_set_updated_data(self.zones.copy())
                    )
                    
                except ValueError:
                    _LOGGER.warning(f"Invalid zone ID in topic: {topic}")
                    
        except Exception as err:
            _LOGGER.error(f"Error processing MQTT message: {err}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.warning(f"Disconnected from MQTT broker: {rc}")
        self.connected = False

    async def async_send_command(self, zone_id: int, command: str, value: str) -> None:
        """Send a command to AmpBridge via MQTT."""
        if not self.mqtt_client or not self.connected:
            _LOGGER.error("%s MQTT client not connected, cannot send command", _LOG_PREFIX)
            return

        # Map source names to "Source X" format for AmpBridge
        mapped_value = value
        if command == "source":
            mapped_value = self._map_source_name(value)
            _LOGGER.info(
                "%s async_send_command zone_id=%s command=source value=%r mapped_value=%r",
                _LOG_PREFIX, zone_id, value, mapped_value,
            )

        topic = f"{MQTT_BASE_TOPIC}/{zone_id}/{command}/set"
        _LOGGER.info("%s publish topic=%s payload=%r", _LOG_PREFIX, topic, mapped_value)
        
        def _publish():
            self.mqtt_client.publish(topic, mapped_value)
        
        await self.hass.async_add_executor_job(_publish)

        # Optimistic update: set zone state so the UI shows the selected option
        # immediately instead of waiting for MQTT. Backend updates will overwrite.
        if command == "source" and zone_id in self.zones:
            self.zones[zone_id]["source"] = value
            self.async_set_updated_data(self.zones.copy())

    def _map_source_name(self, source_name: str) -> str:
        """Map source names to AmpBridge format."""
        # Handle "Off" specially
        if source_name == "Off":
            _LOGGER.debug("%s _map_source_name %r -> Off (explicit)", _LOG_PREFIX, source_name)
            return "Off"
        
        # First try hardcoded mappings for backwards compatibility
        source_mapping = {
            "Echo": "Source 1",
            "Server": "Source 2",
            "TV": "Source 3",
            "Bluetooth": "Source 4",
            "Aux": "Source 5",
            "CD": "Source 6",
            "Tuner": "Source 7",
            "Phono": "Source 8",
        }
        
        if source_name in source_mapping:
            out = source_mapping[source_name]
            _LOGGER.debug("%s _map_source_name %r -> %s (hardcoded)", _LOG_PREFIX, source_name, out)
            return out
        
        # If not in hardcoded mapping, look up in available sources using
        # backend order (same order as API) so "Source N" matches backend index
        available_sources = self._get_available_sources_in_backend_order()
        try:
            index = available_sources.index(source_name)
            out = f"Source {index + 1}"
            _LOGGER.info(
                "%s _map_source_name %r -> %s (backend index %d, order=%s)",
                _LOG_PREFIX, source_name, out, index, available_sources,
            )
            return out
        except ValueError:
            # Source name not found in available sources
            # If it's already in "Source X" format, return as-is
            if source_name.startswith("Source ") and source_name[7:].isdigit():
                _LOGGER.debug("%s _map_source_name %r -> as-is (Source N format)", _LOG_PREFIX, source_name)
                return source_name
            # Otherwise, log warning and return original
            _LOGGER.warning(
                "%s _map_source_name could not map %r (not in available_sources=%s), returning as-is",
                _LOG_PREFIX, source_name, available_sources,
            )
            return source_name

    def get_available_sources(self) -> list[str]:
        """Return available source names for the select dropdown.
        Uses backend order (from API) so the list matches source indices."""
        ordered = self._get_available_sources_in_backend_order()
        if ordered:
            return ordered
        # Fallback if no zones yet: unique names sorted (legacy)
        sources = set()
        for zone_data in self.zones.values():
            sources.update(zone_data.get("available_sources", []))
        return sorted(list(sources))

    def _get_available_sources_in_backend_order(self) -> list[str]:
        """Return available_sources in the same order as the backend (API source index order).
        Used for mapping display name -> 'Source N' so we send the correct index."""
        for zone_data in self.zones.values():
            sources = zone_data.get("available_sources", [])
            if sources:
                return list(sources)
        return []

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via MQTT."""
        # Data is updated via MQTT messages, so we just return current data
        return self.zones.copy()

    async def _discover_zones_via_api(self) -> None:
        """Discover zones via API call."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/zones") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("success") and "zones" in data:
                            _LOGGER.info(
                                "%s API discovery: %d zones",
                                _LOG_PREFIX, len(data["zones"]),
                            )
                            # Convert API zones to our format
                            for zone_data in data["zones"]:
                                zone_id = zone_data["id"]
                                source = zone_data.get("source")
                                available_sources = zone_data.get("available_sources", [])
                                _LOGGER.info(
                                    "%s API zone zone_id=%s name=%s source=%s available_sources=%s",
                                    _LOG_PREFIX, zone_id, zone_data.get("name"),
                                    source, available_sources,
                                )
                                self.zones[zone_id] = {
                                    "zone_id": zone_id,
                                    "name": zone_data["name"],
                                    "volume": zone_data["volume"],
                                    "mute": "ON" if zone_data["muted"] else "OFF",
                                    "source": source,
                                    "connected": "ON" if zone_data["connected"] else "OFF",
                                    "available_sources": available_sources,
                                }
                            
                            # Trigger update with discovered zones
                            self.async_set_updated_data(self.zones.copy())
                        else:
                            _LOGGER.error("API returned unsuccessful response")
                    else:
                        _LOGGER.error(f"API request failed with status {response.status}")
        except Exception as err:
            _LOGGER.error(f"Failed to discover zones via API: {err}")

    async def async_stop(self) -> None:
        """Stop the MQTT client."""
        if self.mqtt_client:
            await self.hass.async_add_executor_job(self._stop_mqtt_client)

    def _stop_mqtt_client(self) -> None:
        """Stop the MQTT client in executor thread."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self.mqtt_client = None
