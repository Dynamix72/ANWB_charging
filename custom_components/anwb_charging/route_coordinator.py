from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import AnwbApi
from .route_api import RouteApi
from .geo import (
    filter_chargers_on_route,
)

_LOGGER = logging.getLogger(__name__)


class RouteCoordinator(
    DataUpdateCoordinator
):

    def __init__(
        self,
        hass,
        tracker_id,
        radius,
        min_power_kw,
        max_route_distance_km,
        ors_api_key,
    ):

        self.hass = hass
        self.tracker_id = tracker_id

        self.radius = radius

        self.min_power_kw = min_power_kw

        self.max_route_distance_km = (
            max_route_distance_km
        )

        self.ors_api_key = ors_api_key

        self.anwb = AnwbApi()
        self.route_api = RouteApi(
            ors_api_key
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name="ANWB Route Charging",
            update_interval=timedelta(
                minutes=15
            ),
        )

    async def _async_update_data(self):

        tracker = self.hass.states.get(
            self.tracker_id
        )

        if not tracker:
            return {}

        vehicle_lat = (
            tracker.attributes.get(
                "latitude"
            )
        )

        vehicle_lon = (
            tracker.attributes.get(
                "longitude"
            )
        )

        destination = self.hass.states.get(
            "input_text.anwb_route_destination"
        )

        if (
            destination is None
            or destination.state == ""
        ):
            return {}

        route = await (
            self.route_api.get_route(
                vehicle_lat,
                vehicle_lon,
                destination.state,
            )
        )

        chargers = await (
            self.anwb.get_chargers(
                vehicle_lat,
                vehicle_lon,
                self.radius,
            )
        )

        filtered = (
            filter_chargers_on_route(
                chargers.get(
                    "value",
                    [],
                ),
                route["coordinates"],
                vehicle_lat,
                vehicle_lon,
                self.min_power_kw,
                self.max_route_distance_km,
            )
        )

        return {

            "route": route,

            "chargers": filtered,
        }
