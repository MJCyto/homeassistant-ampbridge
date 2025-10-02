"""Number platform for AmpBridge group integration."""
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
    """Set up AmpBridge group number entities based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create number entities for discovered groups
    entities = []
    
    # Wait for groups to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if hasattr(coordinator, 'groups') and coordinator.groups:
            break
        await asyncio.sleep(0.2)
    
    # Create number entities for all discovered groups
    for group_id, group_data in coordinator.groups.items():
        entities.append(
            AmpBridgeGroupVolumeNumber(coordinator, config_entry, group_id, group_data.get("name", f"Group {group_id}"))
        )

    async_add_entities(entities)


class AmpBridgeGroupVolumeNumber(CoordinatorEntity, NumberEntity):
    """Representation of an AmpBridge group volume number entity."""

    def __init__(
        self,
        coordinator: AmpBridgeCoordinator,
        config_entry: ConfigEntry,
        group_id: int,
        name: str,
    ) -> None:
        """Initialize the group volume number entity."""
        super().__init__(coordinator)
        self._group_id = group_id
        self._attr_name = f"{name} Volume"
        self._attr_unique_id = f"{config_entry.entry_id}_group_{group_id}_volume"
        self._attr_icon = ICON_NUMBER
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> float | None:
        """Return the current volume value."""
        if self._group_id in self.coordinator.groups:
            return float(self.coordinator.groups[self._group_id].get("volume", 50))
        return 50.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume value."""
        await self.coordinator.async_send_group_command(self._group_id, "volume", str(int(value)))
