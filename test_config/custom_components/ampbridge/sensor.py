"""Sensor platform for AmpBridge integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_VOLUME, ICON_SOURCE
from .coordinator import AmpBridgeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge sensor based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Wait for zones to be discovered via MQTT
    # Poll until we have zone data or timeout after 10 seconds
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if coordinator.data:
            break
        await asyncio.sleep(0.2)
    
    # Create sensors for all discovered zones
    entities = []
    for zone_id, zone_data in coordinator.data.items():
        entities.append(
            AmpBridgeVolumeSensor(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )
        entities.append(
            AmpBridgeSourceSensor(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )

    async_add_entities(entities)


class AmpBridgeVolumeSensor(CoordinatorEntity, SensorEntity):
    """Representation of an AmpBridge volume sensor."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_volume"
        self._attr_icon = ICON_VOLUME
        self._attr_native_unit_of_measurement = "%"
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_name = zone_data.get("name", f"Zone {self._zone_id + 1}")
            return f"{current_name} Volume"
        return f"Zone {self._zone_id + 1} Volume"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_name = zone_data.get("name", f"Zone {self._zone_id + 1}")
        else:
            current_name = f"Zone {self._zone_id + 1}"
        
        return {
            "identifiers": {(DOMAIN, f"zone_{self._zone_id}")},
            "name": current_name,
            "manufacturer": "AmpBridge",
            "model": "Audio Zone",
        }

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            return zone_data.get("volume")
        return None


class AmpBridgeSourceSensor(CoordinatorEntity, SensorEntity):
    """Representation of an AmpBridge source sensor."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_source"
        self._attr_icon = ICON_SOURCE
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_name = zone_data.get("name", f"Zone {self._zone_id + 1}")
            return f"{current_name} Source"
        return f"Zone {self._zone_id + 1} Source"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_name = zone_data.get("name", f"Zone {self._zone_id + 1}")
        else:
            current_name = f"Zone {self._zone_id + 1}"
        
        return {
            "identifiers": {(DOMAIN, f"zone_{self._zone_id}")},
            "name": current_name,
            "manufacturer": "AmpBridge",
            "model": "Audio Zone",
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            return zone_data.get("source")
        return None
