"""HTTP client helpers for AmpBridge (minimal deps for unit tests)."""
from __future__ import annotations

import aiohttp


async def async_check_zones_api(host: str, api_port: int, use_ssl: bool) -> None:
    """Verify AmpBridge HTTP API returns success. Raises on failure."""
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
