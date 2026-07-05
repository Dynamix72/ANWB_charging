from math import cos
from math import radians
import logging

import aiohttp
from yarl import URL

_LOGGER = logging.getLogger(__name__)


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
            f"{lon - lon_delta},"
            f"{lat - lat_delta},"
            f"{lon + lon_delta},"
            f"{lat + lat_delta}"
        )

        params = {
            "bounding-box-filter": bbox,
            "type-filter": "CHARGING_LOCATION",
        }

        url = URL(
            "https://api.anwb.nl/routing/points-of-interest/v3/all"
        ).with_query(params)

        _LOGGER.warning(
            "ANWB GPS lat=%s lon=%s radius=%s",
            lat,
            lon,
            radius,
        )

        _LOGGER.warning(
            "ANWB BBOX=%s",
            bbox,
        )

        _LOGGER.warning(
            "ANWB REQUEST URL=%s",
            str(url),
        )

        async with aiohttp.ClientSession() as session:

            async with session.get(
                str(url)
            ) as response:

                _LOGGER.warning(
                    "ANWB HTTP STATUS=%s",
                    response.status,
                )

                text = await response.text()

                _LOGGER.warning(
                    "ANWB RAW RESPONSE=%s",
                    text,
                )

                try:
                    data = await response.json()

                    _LOGGER.warning(
                        "ANWB TOTAL RESULTS=%s",
                        data.get(
                            "totalResults",
                            "unknown",
                        ),
                    )

                    return data

                except Exception as err:

                    _LOGGER.error(
                        "ANWB JSON ERROR=%s",
                        err,
                    )

                    return {
                        "value": []
                    }
