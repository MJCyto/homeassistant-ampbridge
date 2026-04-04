"""Tests for HTTP API validation (mocked; no Home Assistant install required)."""
from __future__ import annotations

import pytest
from aioresponses import aioresponses

from custom_components.ampbridge.api_client import async_check_zones_api


@pytest.mark.asyncio
async def test_async_check_zones_api_success() -> None:
    with aioresponses() as m:
        m.get(
            "http://ampbridge.local:4000/api/zones",
            payload={"success": True, "zones": [{"id": 0}]},
        )
        await async_check_zones_api("ampbridge.local", 4000, False)


@pytest.mark.asyncio
async def test_async_check_zones_api_https() -> None:
    with aioresponses() as m:
        m.get(
            "https://ampbridge.local:443/api/zones",
            payload={"success": True, "zones": []},
        )
        await async_check_zones_api("ampbridge.local", 443, True)


@pytest.mark.asyncio
async def test_async_check_zones_api_http_error() -> None:
    with aioresponses() as m:
        m.get("http://ampbridge.local:4000/api/zones", status=503)
        with pytest.raises(ValueError, match="HTTP 503"):
            await async_check_zones_api("ampbridge.local", 4000, False)


@pytest.mark.asyncio
async def test_async_check_zones_api_missing_success() -> None:
    with aioresponses() as m:
        m.get(
            "http://ampbridge.local:4000/api/zones",
            payload={"ok": True},
        )
        with pytest.raises(ValueError, match="success"):
            await async_check_zones_api("ampbridge.local", 4000, False)


@pytest.mark.asyncio
async def test_async_check_zones_api_json_array() -> None:
    with aioresponses() as m:
        m.get(
            "http://ampbridge.local:4000/api/zones",
            body="[]",
            content_type="application/json",
        )
        with pytest.raises(ValueError, match="success"):
            await async_check_zones_api("ampbridge.local", 4000, False)
