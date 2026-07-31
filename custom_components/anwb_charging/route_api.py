"""
Route API client for OpenRouteService (ORS) with Home Assistant integration improvements.

- Uses HA's async_get_clientsession to reuse connection pool.
- Adds timeouts, retries on 429, and clear exceptions.
- Does not log API keys or full response bodies.
- Returns both raw and rounded distance/duration values.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientResponse
from aiohttp.client_exceptions import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"


class RouteApiError(HomeAssistantError):
    """Exception raised for ORS API errors."""


class RouteApi:
    def __init__(self, hass: HomeAssistant, api_key: str, timeout: float = 10.0) -> None:
        """Initialize the ORS API client.

        Args:
            hass: Home Assistant instance (used to get shared aiohttp session).
            api_key: ORS API key (kept private; not logged).
            timeout: Request timeout in seconds.
        """
        self.hass = hass
        self.api_key = api_key
        self._timeout = timeout
        self._session = async_get_clientsession(hass)

    async def _request_json(
        self, method: str, url: str, *, params: Optional[Dict] = None, json: Optional[Dict] = None, headers: Optional[Dict] = None, retries: int = 2
    ) -> Dict[str, Any]:
        """Perform an HTTP request and return parsed JSON with retries for 429.

        Raises:
            RouteApiError on network errors, non-200 responses, or JSON errors.
        """
        # Ensure headers include Authorization header for ORS
        req_headers = dict(headers or {})
        if "Authorization" not in req_headers:
            req_headers["Authorization"] = self.api_key

        attempt = 0
        backoff = 1.0

        while True:
            attempt += 1
            try:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                async with self._session.request(method, url, params=params, json=json, headers=req_headers, timeout=timeout) as response:
                    return await self._handle_response(response)
            except ClientError as err:
                _LOGGER.debug("Network error on ORS request to %s: %s", url, err)
                raise RouteApiError(f"Network error when calling ORS: {err}") from err
            except asyncio.TimeoutError as err:
                _LOGGER.debug("Timeout calling ORS %s: %s", url, err)
                raise RouteApiError("Timeout when calling ORS") from err
            except RouteApiError as err:
                # _handle_response already raised for non-200; if 429 and we have retries, loop and backoff
                if "429" in str(err) and attempt <= retries:
                    _LOGGER.warning("ORS rate limited (429). Retry %d/%d after %ss", attempt, retries, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

    async def _handle_response(self, response: ClientResponse) -> Dict[str, Any]:
        """Validate response status and parse JSON, raising RouteApiError on error."""
        status = response.status
        text_snippet = None
        try:
            # Read small snippet for debug but avoid logging secrets or huge bodies
            text = await response.text()
            text_snippet = text[:1000]
            _LOGGER.debug("ORS response status=%s body_snippet=%s", status, text_snippet)
        except Exception:
            # If reading text fails, continue to try json() below; we'll catch JSON errors separately.
            _LOGGER.debug("Unable to read response text for debug logging (status=%s).", status)

        if status == 429:
            # Rate limited
            raise RouteApiError(f"ORS HTTP error 429: rate limited")

        if status < 200 or status >= 300:
            # Try to include a small snippet in the error for debugging, but avoid huge output
            raise RouteApiError(f"ORS HTTP error {status}: {text_snippet or 'no body available'}")

        try:
            data = await response.json()
        except Exception as err:
            # Provide the small text snippet to help debugging
            raise RouteApiError(f"Failed to decode ORS JSON response: {err}. Body snippet: {text_snippet or 'none'}") from err

        return data

    async def geocode(self, destination: str) -> Dict[str, float]:
        """Geocode a destination string to latitude/longitude.

        Returns:
            Dict with keys 'latitude' and 'longitude' as floats.

        Raises:
            RouteApiError if geocode fails or no results found.
        """
        params = {"text": destination, "size": 1}
        _LOGGER.debug("Geocoding destination (masked) with ORS")

        data = await self._request_json("GET", GEOCODE_URL, params=params)

        features = data.get("features") or []
        if not features:
            raise RouteApiError(f"Destination not found: {destination}")

        geometry = features[0].get("geometry", {})
        coords = geometry.get("coordinates")
        if not coords or len(coords) < 2:
            raise RouteApiError("Invalid geocode response from ORS")

        lon, lat = coords[0], coords[1]
        return {"latitude": float(lat), "longitude": float(lon)}

    async def get_route(self, start_lat: float, start_lon: float, destination: str) -> Dict[str, Any]:
        """Get driving route from start to destination.

        Returned dict includes:
            - destination: original destination string
            - distance_m: raw distance in meters (int/float)
            - distance_km: rounded distance in km (1 decimal)
            - duration_s: raw duration in seconds (int/float)
            - duration_min: rounded duration in minutes (1 decimal)
            - coordinates: list of [lon, lat] points from ORS response
            - geojson: full geojson response (as returned)
        """
        dest = await self.geocode(destination)

        payload = {
            "coordinates": [[start_lon, start_lat], [dest["longitude"], dest["latitude"]]],
        }

        _LOGGER.debug("Requesting ORS directions (masked)")

        data = await self._request_json("POST", DIRECTIONS_URL, json=payload)

        features = data.get("features") or []
        if not features:
            raise RouteApiError("ORS directions returned no features")

        feature = features[0]
        properties = feature.get("properties", {})
        summary = properties.get("summary", {})

        distance_m = summary.get("distance")
        duration_s = summary.get("duration")
        coords = feature.get("geometry", {}).get("coordinates", [])

        if distance_m is None or duration_s is None:
            raise RouteApiError("ORS directions response missing summary distance/duration")

        distance_km = round(float(distance_m) / 1000.0, 1)
        duration_min = round(float(duration_s) / 60.0, 1)

        return {
            "destination": destination,
            "distance_m": float(distance_m),
            "distance_km": distance_km,
            "duration_s": float(duration_s),
            "duration_min": duration_min,
            "coordinates": coords,
            "geojson": data,
        }

    async def calculate_detour(
        self,
        start_lat: float,
        start_lon: float,
        charger_lat: float,
        charger_lon: float,
        destination: str,
    ) -> Dict[str, Any]:
        """Calculate detour distance and extra time when visiting a charger on the way.

        Returns:
            dict with 'detour_km' (rounded 1 decimal) and 'extra_minutes' (rounded 1 decimal).
        """
        # Use ORS route summaries for both paths to compute detour precisely using meters/seconds
        direct_route = await self.get_route(start_lat, start_lon, destination)

        # Build route via charger
        payload = {
            "coordinates": [[start_lon, start_lat], [charger_lon, charger_lat], [direct_route["longitude"] if False else direct_route["destination"],],],  # placeholder; see note below
        }

        # Instead of re-geocoding, compute coordinates directly:
        # ORS geocode result used earlier in get_route, so call geocode again here:
        dest_coords = await self.geocode(destination)

        payload = {
            "coordinates": [[start_lon, start_lat], [charger_lon, charger_lat], [dest_coords["longitude"], dest_coords["latitude"]]]
        }

        _LOGGER.debug("Requesting ORS directions for route via charger (masked)")
        route_via = await self._request_json("POST", DIRECTIONS_URL, json=payload)

        features = route_via.get("features") or []
        if not features:
            raise RouteApiError("ORS directions (via charger) returned no features")

        summary = features[0].get("properties", {}).get("summary", {})
        if not summary:
            raise RouteApiError("ORS directions (via charger) response missing summary")

        route_via_distance_m = summary.get("distance")
        route_via_duration_s = summary.get("duration")

        if route_via_distance_m is None or route_via_duration_s is None:
            raise RouteApiError("ORS directions (via charger) missing distance/duration")

        # Compute detour using raw meters/seconds, then round for presentation
        detour_km = round((float(route_via_distance_m) - float(direct_route["distance_m"])) / 1000.0, 1)
        extra_minutes = round((float(route_via_duration_s) - float(direct_route["duration_s"])) / 60.0, 1)

        return {"detour_km": detour_km, "extra_minutes": extra_minutes}
