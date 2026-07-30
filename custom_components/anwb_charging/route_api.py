import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

GEOCODE_URL = (
    "https://api.openrouteservice.org/geocode/search"
)

DIRECTIONS_URL = (
    "https://api.heigit.org/openrouteservice/"
    "v2/directions/driving-car/geojson"
)


class RouteApi:

    def __init__(
        self,
        api_key,
    ):
        self.api_key = api_key

    async def _request_json(
        self,
        method,
        url,
        **kwargs,
    ):

        async with aiohttp.ClientSession() as session:

            async with session.request(
                method,
                url,
                **kwargs,
            ) as response:

                text = await response.text()

                _LOGGER.debug(
                    "ORS status=%s body=%s",
                    response.status,
                    text[:1000],
                )

                if response.status != 200:

                    raise Exception(
                        f"ORS HTTP error "
                        f"{response.status}: "
                        f"{text}"
                    )

                return await response.json()      

    async def geocode(
        self,
        destination,
    ):
    
        params = {
            "api_key": self.api_key,
            "text": destination,
            "size": 1,
        }
        
        _LOGGER.warning(
            "GEOCODE URL=%s",
            GEOCODE_URL,
        )
    
        _LOGGER.warning(
            "GEOCODE PARAMS=%s",
            params,
        )
        data = await self._request_json(
            "GET",
            GEOCODE_URL,
            params=params,
        )
    
        features = data.get(
            "features",
            []
        )
    
        if not features:
            raise Exception(
                f"Bestemming niet gevonden: "
                f"{destination}"
            )
    
        lon, lat = (
            features[0]
            ["geometry"]
            ["coordinates"]
        )
    
        return {
            "latitude": lat,
            "longitude": lon,
        }
    
    
    async def get_route(
        self,
        start_lat,
        start_lon,
        destination,
    ):
    
        dest = await self.geocode(
            destination
        )
    
        payload = {
            "coordinates": [
                [start_lon, start_lat],
                [
                    dest["longitude"],
                    dest["latitude"],
                ],
            ]
        }
    
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
    
        data = await self._request_json(
            "POST",
            DIRECTIONS_URL,
            headers=headers,
            json=payload,
        )
    
        feature = data["features"][0]
    
        summary = (
            feature["properties"]["summary"]
        )
    
        return {
            "distance_km": round(
                summary["distance"] / 1000,
                1,
            ),
            "duration_min": round(
                summary["duration"] / 60,
                1,
            ),
            "coordinates":
                feature["geometry"][
                    "coordinates"
                ],
            "geojson": data,
        }
            
    async def calculate_detour(
        self,
        start_lat,
        start_lon,
        charger_lat,
        charger_lon,
        destination,
    ):
    
        direct_route = await self.get_route(
            start_lat,
            start_lon,
            destination,
        )
    
        dest = await self.geocode(
            destination
        )
    
        payload = {
            "coordinates": [
                [start_lon, start_lat],
                [charger_lon, charger_lat],
                [
                    dest["longitude"],
                    dest["latitude"],
                ],
            ]
        }
    
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
    
        route_via_charger = await self._request_json(
            "POST",
            DIRECTIONS_URL,
            headers=headers,
            json=payload,
        )
    
        summary = (
            route_via_charger["features"][0]
            ["properties"]["summary"]
        )
    
        route_via_distance = (
            summary["distance"] / 1000
        )
    
        detour_km = round(
            route_via_distance
            - direct_route["distance_km"],
            1,
        )
    
        return {
            "detour_km": detour_km,
            "extra_minutes": round(
                (
                    summary["duration"]
                    / 60
                )
                - direct_route[
                    "duration_min"
                ],
                1,
            ),
        }
