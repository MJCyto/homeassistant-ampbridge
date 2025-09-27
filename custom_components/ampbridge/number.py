"""Number platform for AmpBridge integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_NUMBER
from .coordinator import AmpBridgeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge number entities based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create number entities for discovered zones
    entities = []
    
    # Wait for zones to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if coordinator.data:
            break
        await asyncio.sleep(0.2)
    
    # Create number entities for all discovered zones
    for zone_id, zone_data in coordinator.data.items():
        entities.append(
            AmpBridgeVolumeNumber(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )

    async_add_entities(entities)


class AmpBridgeVolumeNumber(CoordinatorEntity, NumberEntity):
    """Representation of an AmpBridge volume number entity."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        # Name will be dynamic via property
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_volume_number"
        self._attr_icon = ICON_NUMBER
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "%"
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the number entity."""
        return "Volume"

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
    def native_value(self) -> float | None:
        """Return the current value."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            volume = zone_data.get("volume")
            if volume is not None:
                return float(volume)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.async_send_command(self._zone_id, "volume", str(int(value)))
