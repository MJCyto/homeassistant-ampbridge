"""Binary sensor platform for AmpBridge integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_CONNECTIVITY
from .coordinator import AmpBridgeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge binary sensors based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create binary sensors for discovered zones
    entities = []
    
    # Wait for zones to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if coordinator.data:
            break
        await asyncio.sleep(0.2)
    
    # Create binary sensors for all discovered zones
    for zone_id, zone_data in coordinator.data.items():
        # Only create connected sensor - mute is handled by switch entity
        entities.append(
            AmpBridgeConnectedBinarySensor(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )

    async_add_entities(entities)


# AmpBridgeMuteBinarySensor removed - using AmpBridgeMuteSwitch instead

class AmpBridgeConnectedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an AmpBridge connected binary sensor."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        # Name will be dynamic via property
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_connected"
        self._attr_icon = ICON_CONNECTIVITY
        self._attr_device_class = "connectivity"
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return "Connected"

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
            "name": f"AmpBridge - {current_name}",
            "manufacturer": "AmpBridge",
            "model": "Audio Zone",
        }

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            return zone_data.get("connected") == "ON"
        return None
