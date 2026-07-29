import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

GEOCODE_URL = (
    "https://api.openrouteservice.org/geocode/search"
)

DIRECTIONS_URL = (
    "https://api.openrouteservice.org/"
    "v2/directions/driving-car/geojson"
)


class RouteApi:

    def __init__(
        self,
        api_key,
    ):
        self.api_key = api_key

    async def _get_json(
        self,
        session,
        url,
        **kwargs,
    ):

        async with session.get(
            url,
            **kwargs,
        ) as response:

            if response.status != 200:

                text = await response.text()

                raise Exception(
                    f"HTTP {response.status}: "
                    f"{text}"
                )

            return await response.json()

    async def geocode(
        self,
        destination,
    ):

        headers = {
            "Authorization": self.api_key,
        }

        params = {
            "text": destination,
            "size": 1,
        }

        async with aiohttp.ClientSession() as session:

            data = await self._get_json(
                session,
                GEOCODE_URL,
                headers=headers,
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

        headers = {
            "Authorization": self.api_key,
            "Content-Type":
                "application/json",
        }

        payload = {
            "coordinates": [
                [start_lon, start_lat],
                [
                    dest["longitude"],
                    dest["latitude"],
                ],
            ]
        }

        async with aiohttp.ClientSession() as session:

            async with session.post(
                DIRECTIONS_URL,
                headers=headers,
                json=payload,
            ) as response:

                if response.status != 200:

                    text = await response.text()

                    raise Exception(
                        f"ORS route fout: "
                        f"{response.status} "
                        f"{text}"
                    )

                data = (
                    await response.json()
                )

        feature = (
            data["features"][0]
        )

        geometry = (
            feature["geometry"]
        )

        properties = (
            feature["properties"]
        )

        summary = (
            properties["summary"]
        )

        coordinates = (
            geometry["coordinates"]
        )

        return {

            "destination": destination,

            "destination_latitude":
                dest["latitude"],

            "destination_longitude":
                dest["longitude"],

            "distance_km":
                round(
                    summary["distance"]
                    / 1000,
                    1,
                ),

            "duration_min":
                round(
                    summary["duration"]
                    / 60,
                    1,
                ),

            "coordinates":
                coordinates,

            "geojson":
                data,
        }

    async def get_route_via_charger(
        self,
        start_lat,
        start_lon,
        charger_lat,
        charger_lon,
        destination,
    ):

        dest = await self.geocode(
            destination
        )

        headers = {
            "Authorization": self.api_key,
            "Content-Type":
                "application/json",
        }

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

        async with aiohttp.ClientSession() as session:

            async with session.post(
                DIRECTIONS_URL,
                headers=headers,
                json=payload,
            ) as response:

                if response.status != 200:

                    text = await response.text()

                    raise Exception(
                        f"ORS route via "
                        f"laadpaal fout: "
                        f"{response.status} "
                        f"{text}"
                    )

                data = (
                    await response.json()
                )

        feature = (
            data["features"][0]
        )

        summary = (
            feature["properties"]
            ["summary"]
        )

        return {

            "distance_km":
                round(
                    summary["distance"]
                    / 1000,
                    1,
                ),

            "duration_min":
                round(
                    summary["duration"]
                    / 60,
                    1,
                ),
        }

    async def calculate_detour(
        self,
        start_lat,
        start_lon,
        charger_lat,
        charger_lon,
        destination,
    ):

        normal_route = (
            await self.get_route(
                start_lat,
                start_lon,
                destination,
            )
        )

        charger_route = (
            await self.get_route_via_charger(
                start_lat,
                start_lon,
                charger_lat,
                charger_lon,
                destination,
            )
        )

        return {

            "detour_km":
                round(
                    charger_route[
                        "distance_km"
                    ]
                    - normal_route[
                        "distance_km"
                    ],
                    1,
                ),

            "extra_minutes":
                round(
                    charger_route[
                        "duration_min"
                    ]
                    - normal_route[
                        "duration_min"
                    ],
                    1,
                ),
        }
