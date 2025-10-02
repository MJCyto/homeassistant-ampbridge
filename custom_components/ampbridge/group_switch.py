"""Switch platform for AmpBridge group integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON_MUTE
from .coordinator import AmpBridgeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AmpBridge group switches based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create switches for discovered groups
    entities = []
    
    # Wait for groups to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if hasattr(coordinator, 'groups') and coordinator.groups:
            break
        await asyncio.sleep(0.2)
    
    # Create switches for all discovered groups
    for group_id, group_data in coordinator.groups.items():
        entities.append(
            AmpBridgeGroupMuteSwitch(coordinator, config_entry, group_id, group_data.get("name", f"Group {group_id}"))
        )

    async_add_entities(entities)


class AmpBridgeGroupMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an AmpBridge group mute switch."""

    def __init__(
        self,
        coordinator: AmpBridgeCoordinator,
        config_entry: ConfigEntry,
        group_id: int,
        name: str,
    ) -> None:
        """Initialize the group mute switch entity."""
        super().__init__(coordinator)
        self._group_id = group_id
        self._attr_name = f"{name} Mute"
        self._attr_unique_id = f"{config_entry.entry_id}_group_{group_id}_mute"
        self._attr_icon = ICON_MUTE

    @property
    def is_on(self) -> bool:
        """Return True if the group is muted."""
        if self._group_id in self.coordinator.groups:
            return self.coordinator.groups[self._group_id].get("mute") == "ON"
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the mute (mute the group)."""
        await self.coordinator.async_send_group_command(self._group_id, "mute", "ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the mute (unmute the group)."""
        await self.coordinator.async_send_group_command(self._group_id, "mute", "OFF")
