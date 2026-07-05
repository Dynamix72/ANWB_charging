from datetime import timedelta

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import AnwbApi


class AnwbCoordinator(
    DataUpdateCoordinator
):

    def __init__(
        self,
        hass,
        tracker_id,
        radius,
    ):

        self.hass = hass
        self.tracker_id = tracker_id
        self.radius = radius
        self.api = AnwbApi()

        super().__init__(
            hass,
            logger=None,
            name="ANWB Charging",
            update_interval=timedelta(
                minutes=5
            ),
        )

    async def _async_update_data(self):

        tracker = self.hass.states.get(
            self.tracker_id
        )

        if tracker is None:
            return {"value": []}

        lat = tracker.attributes.get(
            "latitude"
        )

        lon = tracker.attributes.get(
            "longitude"
        )

        return await self.api.get_chargers(
            lat,
            lon,
            self.radius,
        )
