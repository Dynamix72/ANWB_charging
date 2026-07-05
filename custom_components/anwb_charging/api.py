from math import radians, cos

import aiohttp


def create_bbox(lat, lon, km):

    lat_delta = km / 111.0
    lon_delta = km / (111.0 * cos(radians(lat)))

    return (
        lon - lon_delta,
        lat - lat_delta,
        lon + lon_delta,
        lat + lat_delta,
    )


class AnwbApi:

    def __init__(self, api_key):
        self.api_key = api_key

    async def get_chargers(self, lat, lon, radius):

        bbox = create_bbox(lat, lon, radius)

        params = {
            "bounding-box-filter":
                f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "type-filter":
                "CHARGING_LOCATION",
        }

        headers = {
            "apikey": self.api_key
        }

        async with aiohttp.ClientSession() as session:

            async with session.get(
                "https://api.anwb.nl/routing/points-of-interest/v3/all",
                params=params,
                headers=headers,
            ) as response:

                return await response.json()
