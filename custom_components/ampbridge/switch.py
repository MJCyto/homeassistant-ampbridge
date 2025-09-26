"""Switch platform for AmpBridge integration."""
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
    """Set up AmpBridge switches based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create switches for discovered zones
    entities = []
    
    # Wait for zones to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if coordinator.data:
            break
        await asyncio.sleep(0.2)
    
    # Create switches for all discovered zones
    for zone_id, zone_data in coordinator.data.items():
        entities.append(
            AmpBridgeMuteSwitch(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )

    async_add_entities(entities)


class AmpBridgeMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an AmpBridge mute switch."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        # Name will be dynamic via property
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_mute_switch"
        self._attr_icon = ICON_MUTE
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_name = zone_data.get("name", f"Zone {self._zone_id + 1}")
            return f"{current_name} Mute"
        return f"Zone {self._zone_id + 1} Mute"

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
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            return zone_data.get("mute") == "ON"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (mute the zone)."""
        await self.coordinator.async_send_command(self._zone_id, "mute", "ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (unmute the zone)."""
        await self.coordinator.async_send_command(self._zone_id, "mute", "OFF")
