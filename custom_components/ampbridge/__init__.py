"""The AmpBridge integration."""
from __future__ import annotations

from typing import Any

from .const import DOMAIN


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up AmpBridge from a config entry."""
    from homeassistant.const import Platform

    from .coordinator import AmpBridgeCoordinator

    hass.data.setdefault(DOMAIN, {})

    coordinator = AmpBridgeCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_start()

    platforms = [
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.SWITCH,
        Platform.NUMBER,
        Platform.SELECT,
    ]
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a config entry."""
    from homeassistant.const import Platform

    coordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.async_stop()

    platforms = [
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.SWITCH,
        Platform.NUMBER,
        Platform.SELECT,
    ]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
