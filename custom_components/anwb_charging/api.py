"""
Route API client for OpenRouteService (ORS) with Home Assistant integration improvements.

- Uses HA's async_get_clientsession to reuse connection pool.
- Adds timeouts, retries on 429, and clear exceptions.
- Does not log API keys or full response bodies.
- Returns both raw and rounded distance/duration values.

Notes:
- Extended to support fetching ANWB fuel stations (type-filter=FUEL_STATION).
- Reduced noisy logging: legacy `_LOGGER.warning` calls were lowered to `info` or `debug` where appropriate.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from math import cos, radians

import aiohttp
from aiohttp import ClientResponse
from aiohttp.client_exceptions import ClientError
from yarl import URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

# OpenRouteService URLs (using new api.heigit.org endpoint)
GEOCODE_URL = "https://api.heigit.org/pelias/v1/search"
DIRECTIONS_URL = "https://api.heigit.org/openrouteservice/v2/directions/driving-car/geojson"

# ANWB API
ANWB_BASE = "https://api.anwb.nl/routing/points-of-interest/v3/all"


class RouteApiError(HomeAssistantError):
    """Exception raised for ORS API errors."""


class AnwbApiError(HomeAssistantError):
    """Raised when ANWB API calls fail."""


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
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retries: int = 2,
        use_auth_header: bool = False,
    ) -> Dict[str, Any]:
        """Perform an HTTP request and return parsed JSON with retries for 429.

        Raises RouteApiError on network errors, non-200 responses, or JSON errors.
        """
        req_headers = dict(headers or {})

        if use_auth_header:
            req_headers["Authorization"] = self.api_key

        if params is None:
            params = {}
        else:
            params = dict(params)

        if not use_auth_header and "api_key" not in params:
            params["api_key"] = self.api_key

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
                # convert previously noisy warnings to info for rate-limited retries
                if "429" in str(err) and attempt <= retries:
                    _LOGGER.info("ORS rate limited (429). Retry %d/%d after %ss", attempt, retries, backoff)
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
            _LOGGER.debug("Unable to read response text for debug logging (status=%s).", status)

        if status == 429:
            raise RouteApiError("ORS HTTP error 429: rate limited")

        if status < 200 or status >= 300:
            raise RouteApiError(f"ORS HTTP error {status}: {text_snippet or 'no body available'}")

        try:
            data = await response.json()
        except Exception as err:
            raise RouteApiError(f"Failed to decode ORS JSON response: {err}. Body snippet: {text_snippet or 'none'}") from err

        return data

    async def geocode(self, destination: str) -> Dict[str, float]:
        """Geocode a destination string to latitude/longitude."""
        if "," in destination:
            try:
                lat, lon = destination.split(",")
                return {"latitude": float(lat.strip()), "longitude": float(lon.strip())}
            except ValueError:
                pass

        params = {"text": destination, "size": 1}
        data = await self._request_json("GET", GEOCODE_URL, params=params, use_auth_header=False)

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
        """Get driving route from start to destination."""
        dest = await self.geocode(destination)
        payload = {"coordinates": [[start_lon, start_lat], [dest["longitude"], dest["latitude"]]]}
        data = await self._request_json("POST", DIRECTIONS_URL, json=payload, use_auth_header=True)

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

        return {
            "destination": destination,
            "distance_m": float(distance_m),
            "distance_km": round(float(distance_m) / 1000.0, 1),
            "duration_s": float(duration_s),
            "duration_min": round(float(duration_s) / 60.0, 1),
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
        """Calculate detour distance and extra time when visiting a charger on the way."""
        direct_route = await self.get_route(start_lat, start_lon, destination)
        dest_coords = await self.geocode(destination)
        payload = {
            "coordinates": [[start_lon, start_lat], [charger_lon, charger_lat], [dest_coords["longitude"], dest_coords["latitude"]]]
        }
        route_via = await self._request_json("POST", DIRECTIONS_URL, json=payload, use_auth_header=True)

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

        detour_km = round((float(route_via_distance_m) - float(direct_route["distance_m"])) / 1000.0, 1)
        extra_minutes = round((float(route_via_duration_s) - float(direct_route["duration_s"])) / 60.0, 1)

        return {"detour_km": detour_km, "extra_minutes": extra_minutes}

    @staticmethod
    def _compute_bbox(lat: float, lon: float, radius_km: float) -> str:
        """Compute a simple bounding box around (lat, lon) given radius in kilometers."""
        lat_f = float(lat)
        lon_f = float(lon)
        radius = float(radius_km)

        lat_delta = radius / 111.0
        lon_delta = radius / (111.0 * cos(radians(lat_f)) if cos(radians(lat_f)) != 0 else 1.0)

        return f"{lat_f - lat_delta},{lon_f - lon_delta},{lat_f + lat_delta},{lon_f + lon_delta}"

    async def _request_anwb(
        self,
        url: str,
        *,
        retries: int = 2,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Perform a GET request to ANWB and return parsed JSON with retries."""
        attempt = 0
        backoff = 1.0

        while True:
            attempt += 1
            try:
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                async with self._session.get(url, params=params, headers=headers, timeout=timeout) as resp:
                    status = resp.status
                    try:
                        text = await resp.text()
                        snippet = (text[:1000] + "...") if len(text) > 1000 else text
                    except Exception:
                        snippet = "<unable to read body>"

                    _LOGGER.debug("ANWB HTTP status=%s url=%s", status, url)

                    if status == 429:
                        if attempt <= retries:
                            _LOGGER.info("ANWB rate limited (429). Retry %d/%d in %ss", attempt, retries, backoff)
                            await asyncio.sleep(backoff)
                            backoff *= 2
                            continue
                        raise AnwbApiError("ANWB rate limited (429)")

                    if 500 <= status < 600 and attempt <= retries:
                        _LOGGER.info("ANWB server error %s. Retry %d/%d in %ss", status, attempt, retries, backoff)
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue

                    if status < 200 or status >= 300:
                        raise AnwbApiError(f"ANWB HTTP error {status}: {snippet or 'no body'}")

                    try:
                        data = await resp.json()
                    except Exception as err:
                        raise AnwbApiError(f"Failed to decode ANWB JSON response: {err}. Body snippet: {snippet}") from err

                    return data

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.debug("Network error calling ANWB API: %s", err)
                if attempt <= retries:
                    _LOGGER.info("Network error when calling ANWB; retry %d/%d in %ss", attempt, retries, backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise AnwbApiError(f"Network error when calling ANWB API: {err}") from err

    async def get_chargers(self, lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
        """Fetch chargers from ANWB within the bounding box defined by lat/lon and radius_km."""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            radius_f = float(radius_km)
        except (TypeError, ValueError) as err:
            raise AnwbApiError(f"Invalid lat/lon/radius: {err}") from err

        bbox = self._compute_bbox(lat_f, lon_f, radius_f)
        params = {"bounding-box-filter": bbox, "type-filter": "CHARGING_LOCATION"}
        url = str(URL(ANWB_BASE).with_query(params))

        data = await self._request_anwb(url)
        if not isinstance(data, dict):
            return {"value": []}
        return data

    async def get_fuel_stations(self, lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
        """Fetch fuel stations from ANWB within the bounding box defined by lat/lon and radius_km."""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            radius_f = float(radius_km)
        except (TypeError, ValueError) as err:
            raise AnwbApiError(f"Invalid lat/lon/radius: {err}") from err

        bbox = self._compute_bbox(lat_f, lon_f, radius_f)
        params = {"bounding-box-filter": bbox, "type-filter": "FUEL_STATION"}
        url = str(URL(ANWB_BASE).with_query(params))

        data = await self._request_anwb(url)
        if not isinstance(data, dict):
            return {"value": []}
        return data
