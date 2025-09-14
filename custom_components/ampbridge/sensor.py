"""Sensor platform for AmpBridge integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MQTT_BASE_TOPIC

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create volume sensors for each zone
    entities = []
    for zone_id in range(7):  # Zones 0-6
        entities.append(
            AmpBridgeVolumeSensor(
                coordinator, config_entry, zone_id, f"Zone {zone_id + 1}"
            )
        )
        entities.append(
            AmpBridgeSourceSensor(
                coordinator, config_entry, zone_id, f"Zone {zone_id + 1}"
            )
        )

    async_add_entities(entities)


class AmpBridgeVolumeSensor(CoordinatorEntity, SensorEntity):
    """Representation of an AmpBridge volume sensor."""

    def __init__(self, coordinator, config_entry, zone_id, zone_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Volume"
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_volume"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"zone_{zone_id}")},
            "name": zone_name,
            "manufacturer": "AmpBridge",
            "model": "Audio Zone",
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        # This would be populated by the coordinator
        return self.coordinator.data.get(f"zone_{self._zone_id}_volume")


class AmpBridgeSourceSensor(CoordinatorEntity, SensorEntity):
    """Representation of an AmpBridge source sensor."""

    def __init__(self, coordinator, config_entry, zone_id, zone_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Source"
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_source"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"zone_{zone_id}")},
            "name": zone_name,
            "manufacturer": "AmpBridge",
            "model": "Audio Zone",
        }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        # This would be populated by the coordinator
        return self.coordinator.data.get(f"zone_{self._zone_id}_source")
