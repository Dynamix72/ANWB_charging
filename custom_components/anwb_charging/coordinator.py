from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import AnwbApi

_LOGGER = logging.getLogger(__name__)


class AnwbCoordinator(DataUpdateCoordinator):

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
            logger=_LOGGER,
            name="ANWB Charging",
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):

        tracker = self.hass.states.get(
            self.tracker_id
        )

        if tracker is None:
            _LOGGER.error(
                "Tracker %s niet gevonden",
                self.tracker_id,
            )
            return {"value": []}

        lat = tracker.attributes.get("latitude")
        lon = tracker.attributes.get("longitude")

        _LOGGER.warning(
            "ANWB GPS lat=%s lon=%s",
            lat,
            lon,
        )

        data = await self.api.get_chargers(
            lat,
            lon,
            self.radius,
        )

        _LOGGER.warning(
            "ANWB RESPONSE=%s",
            data,
        )

        return data
