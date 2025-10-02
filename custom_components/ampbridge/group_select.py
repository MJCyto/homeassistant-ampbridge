"""Select platform for AmpBridge group integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_SOURCE
from .coordinator import AmpBridgeCoordinator

_LOGGER = logging.getLogger(__name__)

# Default source options - will be dynamically updated from MQTT data
DEFAULT_SOURCE_OPTIONS = ["Off", "Source 1", "Source 2", "Source 3", "Source 4"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge group select entities based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create select entities for discovered groups
    entities = []
    
    # Wait for groups to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if hasattr(coordinator, 'groups') and coordinator.groups:
            break
        await asyncio.sleep(0.2)
    
    # Create select entities for all discovered groups
    for group_id, group_data in coordinator.groups.items():
        entities.append(
            AmpBridgeGroupSourceSelect(coordinator, config_entry, group_id, group_data.get("name", f"Group {group_id}"))
        )

    async_add_entities(entities)


class AmpBridgeGroupSourceSelect(CoordinatorEntity, SelectEntity):
    """Representation of an AmpBridge group source select entity."""

    def __init__(
        self,
        coordinator: AmpBridgeCoordinator,
        config_entry: ConfigEntry,
        group_id: int,
        name: str,
    ) -> None:
        """Initialize the group source select entity."""
        super().__init__(coordinator)
        self._group_id = group_id
        self._attr_name = f"{name} Source"
        self._attr_unique_id = f"{config_entry.entry_id}_group_{group_id}_source"
        self._attr_icon = ICON_SOURCE
        self._attr_options = DEFAULT_SOURCE_OPTIONS.copy()

    @property
    def current_option(self) -> str | None:
        """Return the currently selected source."""
        if self._group_id in self.coordinator.groups:
            return self.coordinator.groups[self._group_id].get("source", "Off")
        return "Off"

    async def async_select_option(self, option: str) -> None:
        """Change the selected source."""
        await self.coordinator.async_send_group_command(self._group_id, "source", option)
