"""Select platform for AmpBridge integration."""
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
    """Set up AmpBridge select entities based on a config entry."""
    coordinator: AmpBridgeCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create select entities for discovered zones
    entities = []
    
    # Wait for zones to be discovered via MQTT
    for _ in range(50):  # 50 * 0.2s = 10 seconds
        if coordinator.data:
            break
        await asyncio.sleep(0.2)
    
    # Create select entities for all discovered zones
    for zone_id, zone_data in coordinator.data.items():
        entities.append(
            AmpBridgeSourceSelect(coordinator, config_entry, zone_id, zone_data.get("name", f"Zone {zone_id + 1}"))
        )

    async_add_entities(entities)


class AmpBridgeSourceSelect(CoordinatorEntity, SelectEntity):
    """Representation of an AmpBridge source select entity."""

    def __init__(self, coordinator: AmpBridgeCoordinator, config_entry: ConfigEntry, zone_id: int, zone_name: str):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_name = zone_name
        self._attr_unique_id = f"ampbridge_zone_{zone_id}_source_select"
        self._attr_icon = ICON_SOURCE
        # Device info will be dynamic via property

    @property
    def name(self) -> str:
        """Return the name of the select entity."""
        return "Source"

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
    def options(self) -> list[str]:
        """Return the list of available options."""
        # Get available sources from coordinator and add "Off"
        available_sources = self.coordinator.get_available_sources()
        return ["Off"] + available_sources

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        zone_data = self.coordinator.data.get(self._zone_id)
        if zone_data:
            current_source = zone_data.get("source")
            if current_source in self.options:
                return current_source
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_send_command(self._zone_id, "source", option)
    
    @property
    def should_poll(self) -> bool:
        """Return False since we get updates via coordinator."""
        return False