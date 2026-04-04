"""Pure helpers for AmpBridge integration (unit-testable without Home Assistant)."""
from __future__ import annotations

from typing import Any, Mapping

from .const import CONF_API_PORT, CONF_USE_SSL, DEFAULT_API_PORT


def build_api_base_url(entry_data: Mapping[str, Any]) -> str:
    """Build `http(s)://host:port/api` from config entry data."""
    host = str(entry_data["host"]).strip()
    api_port = int(entry_data.get(CONF_API_PORT, DEFAULT_API_PORT))
    use_ssl = bool(entry_data.get(CONF_USE_SSL, False))
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{api_port}/api"


def parse_zone_mqtt_topic(
    mqtt_base_topic: str, full_topic: str
) -> tuple[int, str] | None:
    """Parse `{base}/{zone_id}/{attribute}` from a full MQTT topic."""
    base_parts = mqtt_base_topic.strip("/").split("/")
    parts = full_topic.split("/")
    blen = len(base_parts)
    if len(parts) < blen + 2:
        return None
    if parts[:blen] != base_parts:
        return None
    try:
        zone_id = int(parts[blen])
    except ValueError:
        return None
    attribute = parts[blen + 1]
    return zone_id, attribute


def map_display_source_to_ampbridge(
    source_name: str, available_sources: list[str]
) -> str:
    """Map HA select label to AmpBridge MQTT payload (Source N or Off)."""
    if source_name == "Off":
        return "Off"
    try:
        index = available_sources.index(source_name)
        return f"Source {index + 1}"
    except ValueError:
        if source_name.startswith("Source ") and source_name[7:].isdigit():
            return source_name
        return source_name
