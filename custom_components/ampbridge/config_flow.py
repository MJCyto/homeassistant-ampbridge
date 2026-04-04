"""Config flow for AmpBridge integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_PORT,
    CONF_MQTT_BASE_TOPIC,
    CONF_USE_SSL,
    DEFAULT_API_PORT,
    DEFAULT_MQTT_PORT,
    DOMAIN,
    MQTT_BASE_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_MQTT_PORT): int,
        vol.Optional(CONF_API_PORT, default=DEFAULT_API_PORT): vol.Coerce(int),
        vol.Optional(CONF_USE_SSL, default=False): bool,
        vol.Optional(CONF_MQTT_BASE_TOPIC, default=MQTT_BASE_TOPIC): str,
    }
)


async def _async_check_api(host: str, api_port: int, use_ssl: bool) -> None:
    """Verify AmpBridge HTTP API returns zones. Raises aiohttp.ClientError on failure."""
    scheme = "https" if use_ssl else "http"
    url = f"{scheme}://{host}:{api_port}/api/zones"
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                msg = f"HTTP {response.status} from {url}"
                raise ValueError(msg)
            data = await response.json()
            if not isinstance(data, dict) or not data.get("success"):
                raise ValueError("API response missing success or invalid JSON")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AmpBridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        host = user_input[CONF_HOST].strip()
        mqtt_port = user_input[CONF_PORT]
        api_port = int(user_input.get(CONF_API_PORT, DEFAULT_API_PORT))
        use_ssl = bool(user_input.get(CONF_USE_SSL, False))
        mqtt_base = (user_input.get(CONF_MQTT_BASE_TOPIC) or MQTT_BASE_TOPIC).strip(
            "/"
        )

        try:
            await _async_check_api(host, api_port, use_ssl)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            _LOGGER.warning("AmpBridge API check failed: %s", err)
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error checking AmpBridge API")
            errors["base"] = "unknown"

        if not errors:
            await self.async_set_unique_id(f"{host}:{mqtt_port}")
            self._abort_if_unique_id_configured()

        if not errors:
            data = {
                CONF_HOST: host,
                CONF_PORT: mqtt_port,
                CONF_API_PORT: api_port,
                CONF_USE_SSL: use_ssl,
                CONF_MQTT_BASE_TOPIC: mqtt_base,
            }
            return self.async_create_entry(
                title=f"AmpBridge ({host})",
                data=data,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
