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

from .const import DOMAIN, MQTT_BASE_TOPIC, MQTT_GROUPS_BASE_TOPIC

_LOGGER = logging.getLogger(__name__)


class AmpBridgeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage AmpBridge MQTT data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self.mqtt_client: mqtt.Client | None = None
        self.connected = False
        self.zones: dict[int, dict[str, Any]] = {}
        self.groups: dict[int, dict[str, Any]] = {}
        self.api_url = f"http://{entry.data['host']}:4000/api"
        
        # Initialize with empty data
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # We'll update via MQTT messages
        )

    async def async_start(self) -> None:
        """Start the MQTT client and discover zones and groups."""
        # First discover zones and groups via API
        await self._discover_zones_via_api()
        await self._discover_groups_via_api()
        
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
            
            # Parse topic to extract zone or group info
            # Expected format: ampbridge/zones/{zone_id}/{attribute} or ampbridge/groups/{group_id}/{attribute}
            parts = topic.split("/")
            if len(parts) >= 4 and parts[0] == "ampbridge":
                if parts[1] == "zones":
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
                            self.zones[zone_id]["source"] = payload
                        elif attribute == "connected":
                            self.zones[zone_id]["connected"] = payload
                        
                        # Trigger update - schedule on the event loop
                        self.hass.loop.call_soon_threadsafe(
                            lambda: self.async_set_updated_data(self.zones.copy())
                        )
                        
                    except ValueError:
                        _LOGGER.warning(f"Invalid zone ID in topic: {topic}")
                        
                elif parts[1] == "groups":
                    try:
                        group_id = int(parts[2])
                        attribute = parts[3]
                        
                        # Create group if it doesn't exist
                        if group_id not in self.groups:
                            self.groups[group_id] = {
                                "group_id": group_id,
                                "name": f"Group {group_id}",
                                "volume": 50,
                                "mute": "OFF",
                                "source": "Off",
                                "description": "",
                                "zone_count": 0
                            }
                        
                        # Update group data
                        if attribute == "name":
                            self.groups[group_id]["name"] = payload
                        elif attribute == "description":
                            self.groups[group_id]["description"] = payload
                        elif attribute == "volume":
                            try:
                                self.groups[group_id]["volume"] = int(payload)
                            except ValueError:
                                _LOGGER.warning(f"Invalid volume value: {payload}")
                        elif attribute == "mute":
                            self.groups[group_id]["mute"] = payload
                        elif attribute == "source":
                            self.groups[group_id]["source"] = payload
                        elif attribute == "zone_count":
                            try:
                                self.groups[group_id]["zone_count"] = int(payload)
                            except ValueError:
                                _LOGGER.warning(f"Invalid zone_count value: {payload}")
                        
                        # Trigger update - schedule on the event loop
                        self.hass.loop.call_soon_threadsafe(
                            lambda: self.async_set_updated_data(self.zones.copy())
                        )
                        
                    except ValueError:
                        _LOGGER.warning(f"Invalid group ID in topic: {topic}")
                    
                else:
                    _LOGGER.debug(f"Unknown MQTT topic type: {topic}")
                    
            except ValueError:
                _LOGGER.warning(f"Invalid ID in topic: {topic}")
                    
        except Exception as err:
            _LOGGER.error(f"Error processing MQTT message: {err}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.warning(f"Disconnected from MQTT broker: {rc}")
        self.connected = False

    async def async_send_command(self, zone_id: int, command: str, value: str) -> None:
        """Send a command to AmpBridge via MQTT."""
        if not self.mqtt_client or not self.connected:
            _LOGGER.error("MQTT client not connected")
            return

        # Map source names to "Source X" format for AmpBridge
        mapped_value = value
        if command == "source":
            mapped_value = self._map_source_name(value)

        topic = f"{MQTT_BASE_TOPIC}/{zone_id}/{command}/set"
        _LOGGER.info(f"Sending command: {topic} = {value} -> {mapped_value}")
        
        def _publish():
            self.mqtt_client.publish(topic, mapped_value)
        
        await self.hass.async_add_executor_job(_publish)

    async def async_send_group_command(self, group_id: int, command: str, value: str) -> None:
        """Send a command to AmpBridge group via MQTT."""
        if not self.mqtt_client or not self.connected:
            _LOGGER.error("MQTT client not connected")
            return

        # Map source names to "Source X" format for AmpBridge
        mapped_value = value
        if command == "source":
            mapped_value = self._map_source_name(value)

        topic = f"{MQTT_GROUPS_BASE_TOPIC}/{group_id}/{command}/set"
        _LOGGER.info(f"Sending group command: {topic} = {value} -> {mapped_value}")
        
        def _publish():
            self.mqtt_client.publish(topic, mapped_value)
        
        await self.hass.async_add_executor_job(_publish)

    def _map_source_name(self, source_name: str) -> str:
        """Map source names to AmpBridge format."""
        # Map common source names to "Source X" format
        source_mapping = {
            "Off": "Off",
            "Echo": "Source 1",
            "Server": "Source 2",
            "TV": "Source 3",
            "Bluetooth": "Source 4",
            "Aux": "Source 5",
            "CD": "Source 6",
            "Tuner": "Source 7",
            "Phono": "Source 8",
        }
        
        # Return mapped value or original if not found
        return source_mapping.get(source_name, source_name)

    def get_available_sources(self) -> list[str]:
        """Get all available sources from all zones."""
        sources = set()
        for zone_data in self.zones.values():
            # Get available sources from the zone data
            available_sources = zone_data.get("available_sources", [])
            sources.update(available_sources)
        return sorted(list(sources))

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
                            _LOGGER.info(f"Discovered {len(data['zones'])} zones via API")
                            
                            # Convert API zones to our format
                            for zone_data in data["zones"]:
                                zone_id = zone_data["id"]
                                self.zones[zone_id] = {
                                    "zone_id": zone_id,
                                    "name": zone_data["name"],
                                    "volume": zone_data["volume"],
                                    "mute": "ON" if zone_data["muted"] else "OFF",
                                    "source": zone_data["source"],
                                    "connected": "ON" if zone_data["connected"] else "OFF",
                                    "available_sources": zone_data.get("available_sources", []),
                                }
                            
                            # Trigger update with discovered zones
                            self.async_set_updated_data(self.zones.copy())
                        else:
                            _LOGGER.error("API returned unsuccessful response")
                    else:
                        _LOGGER.error(f"API request failed with status {response.status}")
        except Exception as err:
            _LOGGER.error(f"Failed to discover zones via API: {err}")

    async def _discover_groups_via_api(self) -> None:
        """Discover zone groups via API."""
        try:
            # For now, we'll discover groups via MQTT since there's no API endpoint yet
            # This could be extended to call a groups API endpoint in the future
            _LOGGER.info("Group discovery will be handled via MQTT messages")
            self.groups = {}
        except Exception as err:
            _LOGGER.error(f"Failed to discover groups via API: {err}")
            self.groups = {}

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
