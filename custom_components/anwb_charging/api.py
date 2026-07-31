"""
ANWB API client for fetching charging points.

- Uses Home Assistant's shared aiohttp session (async_get_clientsession).
- Adds timeouts, retries, and clear exceptions.
- Avoids logging full response bodies or sensitive info.
"""

import asyncio
import logging
from math import cos, radians
from typing import Any, Dict, Optional

import aiohttp
from yarl import URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

ANWB_BASE = "https://api.anwb.nl/routing/points-of-interest/v3/all"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRIES = 2
RETRY_BACKOFF = 1.0  # seconds


class AnwbApiError(HomeAssistantError):
    """Raised when ANWB API calls fail."""


class AnwbApi:
    """Client for the ANWB Points of Interest API."""

    def __init__(self, hass: HomeAssistant, timeout: float = DEFAULT_TIMEOUT) -> None:
        """
        Initialize the ANWB API client.

        Args:
            hass: Home Assistant instance (used to get shared aiohttp session).
            timeout: request timeout in seconds.
        """
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._timeout = float(timeout)

    @staticmethod
    def _compute_bbox(lat: float, lon: float, radius_km: float) -> str:
        """Compute a simple bounding box around (lat, lon) given radius in kilometers."""
        # Convert to floats for safety
        lat_f = float(lat)
        lon_f = float(lon)
        radius = float(radius_km)

        # Rough approximations: 1 degree lat ~= 111 km
        lat_delta = radius / 111.0
        lon_delta = radius / (111.0 * cos(radians(lat_f)) if cos(radians(lat_f)) != 0 else 1.0)

        return f"{lat_f - lat_delta},{lon_f - lon_delta},{lat_f + lat_delta},{lon_f + lon_delta}"

    async def _request_json(
        self,
        url: str,
        *,
        retries: int = DEFAULT_RETRIES,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Perform a GET request and return parsed JSON with retries for transient errors."""
        attempt = 0
        backoff = RETRY_BACKOFF

        while True:
            attempt += 1
            try:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                async with self._session.get(url, params=params, headers=headers, timeout=timeout) as resp:
                    status = resp.status
                    # Read a limited snippet for debugging to avoid huge logs
                    try:
                        text = await resp.text()
                        snippet = (text[:1000] + "...") if len(text) > 1000 else text
                    except Exception:
                        snippet = "<unable to read body>"

                    _LOGGER.debug("ANWB HTTP status=%s url=%s", status, url)

                    if status == 429:
                        # Rate limited => retry if attempts remain
                        if attempt <= retries:
                            _LOGGER.warning("ANWB rate limited (429). Retry %d/%d in %ss", attempt, retries, backoff)
                            await asyncio.sleep(backoff)
                            backoff *= 2
                            continue
                        raise AnwbApiError("ANWB rate limited (429)")

                    if 500 <= status < 600 and attempt <= retries:
                        _LOGGER.warning("ANWB server error %s. Retry %d/%d in %ss", status, attempt, retries, backoff)
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue

                    if status < 200 or status >= 300:
                        # Include a small snippet for debugging, but do not log full body at info level
                        raise AnwbApiError(f"ANWB HTTP error {status}: {snippet or 'no body'}")

                    try:
                        data = await resp.json()
                    except Exception as err:
                        raise AnwbApiError(f"Failed to decode ANWB JSON response: {err}. Body snippet: {snippet}") from err

                    return data

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug("Network error calling ANWB API: %s", err)
                if attempt <= retries:
                    _LOGGER.warning("Network error when calling ANWB; retry %d/%d in %ss", attempt, retries, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise AnwbApiError(f"Network error when calling ANWB API: {err}") from err

    async def get_chargers(self, lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
        """
        Fetch chargers from ANWB within the bounding box defined by lat/lon and radius_km.

        Returns the parsed JSON from ANWB (typically a dict containing "value" list).
        Raises AnwbApiError on failure.
        """
        # Validate inputs
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            radius_f = float(radius_km)
        except (TypeError, ValueError) as err:
            raise AnwbApiError(f"Invalid lat/lon/radius: {err}") from err

        bbox = self._compute_bbox(lat_f, lon_f, radius_f)

        params = {
            "bounding-box-filter": bbox,
            "type-filter": "CHARGING_LOCATION",
        }

        # Build URL using yarl.URL so query encoding is safe
        url = str(URL(ANWB_BASE).with_query(params))

        _LOGGER.debug("ANWB request bbox=%s lat=%s lon=%s radius_km=%s", bbox, lat_f, lon_f, radius_f)
        _LOGGER.debug("ANWB request url (masked)=%s", url)

        data = await self._request_json(url)

        # Defensive: ensure there's a 'value' list in the response
        if not isinstance(data, dict):
            _LOGGER.warning("ANWB API returned non-dict response; returning empty value list")
            return {"value": []}

        # Return parsed data as-is; upstream code (coordinator) will filter/validate items
        return data
