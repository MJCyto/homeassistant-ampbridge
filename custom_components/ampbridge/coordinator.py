"""MQTT coordinator for AmpBridge integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import paho.mqtt.client as mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_MQTT_BASE_TOPIC, DOMAIN, MQTT_BASE_TOPIC
from .util import build_api_base_url, map_display_source_to_ampbridge, parse_zone_mqtt_topic

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
        self.api_url = build_api_base_url(entry.data)
        self.mqtt_base_topic = (
            entry.data.get(CONF_MQTT_BASE_TOPIC) or MQTT_BASE_TOPIC
        ).strip("/")

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

    def _parse_zone_topic(self, topic: str) -> tuple[int, str] | None:
        """Parse {mqtt_base_topic}/{zone_id}/{attribute} from a full topic."""
        return parse_zone_mqtt_topic(self.mqtt_base_topic, topic)

    async def async_start(self) -> None:
        """Start the MQTT client and discover zones."""
        await self._discover_zones_via_api()
        await self.hass.async_add_executor_job(self._start_mqtt_client)

    def _start_mqtt_client(self) -> None:
        """Start the MQTT client in executor thread."""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

        try:
            host = self.entry.data["host"].strip()
            port = self.entry.data["port"]
            _LOGGER.info(
                "Connecting to MQTT broker at %s:%s (base topic %s)",
                host,
                port,
                self.mqtt_base_topic,
            )
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_start()
        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            raise UpdateFailed(f"Failed to connect to MQTT broker: {err}") from err

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker")
            self.connected = True
            pattern = f"{self.mqtt_base_topic}/#"
            client.subscribe(pattern)
            _LOGGER.info("Subscribed to %s", pattern)
        else:
            _LOGGER.error("Failed to connect to MQTT broker: %s", rc)
            self.connected = False

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle MQTT messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            _LOGGER.debug("Received MQTT message: %s = %s", topic, payload)

            parsed = self._parse_zone_topic(topic)
            if parsed is None:
                return

            zone_id, attribute = parsed

            if zone_id not in self.zones:
                _LOGGER.debug(
                    "Received MQTT message for unknown zone %s, skipping", zone_id
                )
                return

            if attribute == "name":
                self.zones[zone_id]["name"] = payload
            elif attribute == "volume":
                try:
                    self.zones[zone_id]["volume"] = int(payload)
                except ValueError:
                    _LOGGER.warning("Invalid volume value: %s", payload)
            elif attribute == "mute":
                self.zones[zone_id]["mute"] = payload
            elif attribute == "source":
                old_val = self.zones[zone_id].get("source")
                self.zones[zone_id]["source"] = payload
                _LOGGER.info(
                    "%s MQTT source zone_id=%s topic=%s old=%s new=%s",
                    _LOG_PREFIX,
                    zone_id,
                    topic,
                    old_val,
                    payload,
                )
            elif attribute == "connected":
                self.zones[zone_id]["connected"] = payload

            self.hass.loop.call_soon_threadsafe(
                lambda: self.async_set_updated_data(self.zones.copy())
            )

        except Exception as err:
            _LOGGER.error("Error processing MQTT message: %s", err)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.warning("Disconnected from MQTT broker: %s", rc)
        self.connected = False

    async def async_send_command(self, zone_id: int, command: str, value: str) -> None:
        """Send a command to AmpBridge via MQTT."""
        if not self.mqtt_client or not self.connected:
            _LOGGER.error(
                "%s MQTT client not connected, cannot send command", _LOG_PREFIX
            )
            return

        mapped_value = value
        if command == "source":
            mapped_value = self._map_source_name(value)
            _LOGGER.info(
                "%s async_send_command zone_id=%s command=source value=%r mapped_value=%r",
                _LOG_PREFIX,
                zone_id,
                value,
                mapped_value,
            )

        topic = f"{self.mqtt_base_topic}/{zone_id}/{command}/set"
        _LOGGER.info("%s publish topic=%s payload=%r", _LOG_PREFIX, topic, mapped_value)

        def _publish() -> None:
            assert self.mqtt_client is not None
            self.mqtt_client.publish(topic, mapped_value)

        await self.hass.async_add_executor_job(_publish)

        if command == "source" and zone_id in self.zones:
            self.zones[zone_id]["source"] = value
            self.async_set_updated_data(self.zones.copy())

    def _map_source_name(self, source_name: str) -> str:
        """Map source names to AmpBridge format."""
        available_sources = self._get_available_sources_in_backend_order()
        out = map_display_source_to_ampbridge(source_name, available_sources)
        if source_name == "Off":
            _LOGGER.debug(
                "%s _map_source_name %r -> Off (explicit)", _LOG_PREFIX, source_name
            )
        elif out.startswith("Source ") and out != source_name:
            _LOGGER.info(
                "%s _map_source_name %r -> %s (order=%s)",
                _LOG_PREFIX,
                source_name,
                out,
                available_sources,
            )
        elif source_name.startswith("Source ") and source_name[7:].isdigit():
            _LOGGER.debug(
                "%s _map_source_name %r -> as-is (Source N format)",
                _LOG_PREFIX,
                source_name,
            )
        elif out == source_name and source_name != "Off":
            _LOGGER.warning(
                "%s _map_source_name could not map %r (not in available_sources=%s), returning as-is",
                _LOG_PREFIX,
                source_name,
                available_sources,
            )
        return out

    def get_available_sources(self) -> list[str]:
        """Return available source names for the select dropdown."""
        ordered = self._get_available_sources_in_backend_order()
        if ordered:
            return ordered
        sources: set[str] = set()
        for zone_data in self.zones.values():
            sources.update(zone_data.get("available_sources", []))
        return sorted(list(sources))

    def _get_available_sources_in_backend_order(self) -> list[str]:
        """Return available_sources in backend (API) order."""
        for zone_data in self.zones.values():
            sources = zone_data.get("available_sources", [])
            if sources:
                return list(sources)
        return []

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via MQTT."""
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
                                _LOG_PREFIX,
                                len(data["zones"]),
                            )
                            for zone_data in data["zones"]:
                                zone_id = zone_data["id"]
                                source = zone_data.get("source")
                                available_sources = zone_data.get(
                                    "available_sources", []
                                )
                                _LOGGER.info(
                                    "%s API zone zone_id=%s name=%s source=%s available_sources=%s",
                                    _LOG_PREFIX,
                                    zone_id,
                                    zone_data.get("name"),
                                    source,
                                    available_sources,
                                )
                                self.zones[zone_id] = {
                                    "zone_id": zone_id,
                                    "name": zone_data["name"],
                                    "volume": zone_data["volume"],
                                    "mute": "ON" if zone_data["muted"] else "OFF",
                                    "source": source,
                                    "connected": "ON"
                                    if zone_data["connected"]
                                    else "OFF",
                                    "available_sources": available_sources,
                                }

                            self.async_set_updated_data(self.zones.copy())
                        else:
                            _LOGGER.error("API returned unsuccessful response")
                    else:
                        _LOGGER.error(
                            "API request failed with status %s", response.status
                        )
        except Exception as err:
            _LOGGER.error("Failed to discover zones via API: %s", err)

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
