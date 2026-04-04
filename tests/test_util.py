"""Unit tests for pure helpers (no Home Assistant runtime)."""
from __future__ import annotations

import pytest

from custom_components.ampbridge.const import CONF_API_PORT, CONF_USE_SSL
from custom_components.ampbridge.util import (
    build_api_base_url,
    map_display_source_to_ampbridge,
    parse_zone_mqtt_topic,
)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"host": "192.168.1.10", "port": 1885}, "http://192.168.1.10:4000/api"),
        (
            {"host": "  hub.local ", "port": 1885, CONF_API_PORT: 8080},
            "http://hub.local:8080/api",
        ),
        (
            {"host": "secure.example", "port": 1883, CONF_USE_SSL: True},
            "https://secure.example:4000/api",
        ),
        (
            {
                "host": "secure.example",
                "port": 1883,
                CONF_API_PORT: 443,
                CONF_USE_SSL: True,
            },
            "https://secure.example:443/api",
        ),
    ],
)
def test_build_api_base_url(data: dict, expected: str) -> None:
    assert build_api_base_url(data) == expected


@pytest.mark.parametrize(
    ("base", "topic", "expected"),
    [
        ("ampbridge/zones", "ampbridge/zones/0/volume", (0, "volume")),
        ("ampbridge/zones", "ampbridge/zones/2/source", (2, "source")),
        ("custom/zones", "custom/zones/1/mute", (1, "mute")),
        ("ampbridge/zones", "other/zones/0/volume", None),
        ("ampbridge/zones", "ampbridge/zones/notint/volume", None),
        ("a/b", "a/b/3/name", (3, "name")),
    ],
)
def test_parse_zone_mqtt_topic(
    base: str, topic: str, expected: tuple[int, str] | None
) -> None:
    assert parse_zone_mqtt_topic(base, topic) == expected


def test_map_display_source_echo_third_slot() -> None:
    """Regression: custom names use list index, not hardcoded Echo->Source1."""
    order = ["Wiim", "Zenbook", "Echo"]
    assert map_display_source_to_ampbridge("Echo", order) == "Source 3"
    assert map_display_source_to_ampbridge("Wiim", order) == "Source 1"


@pytest.mark.parametrize(
    ("label", "order", "want"),
    [
        ("Off", ["A", "B"], "Off"),
        ("Source 2", [], "Source 2"),
        ("Unknown", ["A"], "Unknown"),
    ],
)
def test_map_display_source_edge_cases(
    label: str, order: list[str], want: str
) -> None:
    assert map_display_source_to_ampbridge(label, order) == want
