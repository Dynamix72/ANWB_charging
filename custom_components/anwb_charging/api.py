from math import cos
from math import radians

import aiohttp


class AnwbApi:

    async def get_chargers(
        self,
        lat,
        lon,
        radius,
    ):

        lat_delta = radius / 111.0
        lon_delta = radius / (
            111.0 * cos(radians(lat))
        )

        bbox = (
            f"{lon-lon_delta},"
            f"{lat-lat_delta},"
            f"{lon+lon_delta},"
            f"{lat+lat_delta}"
        )

        params = {
            "bounding-box-filter": bbox,
            "type-filter": "CHARGING_LOCATION",
        }

        async with aiohttp.ClientSession() as session:

            async with session.get(
                "https://api.anwb.nl/routing/points-of-interest/v3/all",
                params=params,
            ) as response:

                return await response.json()
