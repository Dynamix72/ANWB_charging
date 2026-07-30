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

        self.anwb_api = AnwbApi()

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

        if tracker is None:

            _LOGGER.error(
                "Tracker %s niet gevonden",
                self.tracker_id,
            )

            return {
                "route": None,
                "chargers": [],
            }

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

        if (
            vehicle_lat is None
            or vehicle_lon is None
        ):

            _LOGGER.error(
                "GPS positie ontbreekt"
            )

            return {
                "route": None,
                "chargers": [],
            }

        destination_entity = (
            self.hass.states.get(
                "input_text.anwb_route_destination"
            )
        )

        if (
            destination_entity is None
        ):

            _LOGGER.warning(
                "input_text.anwb_route_destination niet gevonden"
            )

            return {
                "route": None,
                "chargers": [],
            }
            
            _LOGGER.warning(
                "ROUTE TEST bestemming=%s "
                "afstand=%s km "
                "duur=%s min",
                destination,
                route["distance_km"],
                route["duration_min"],
            )
        destination = (
            destination_entity.state.strip()
        )

        if not destination:

            _LOGGER.warning(
                "Geen bestemming ingevuld"
            )

            return {
                "route": None,
                "chargers": [],
            }

        _LOGGER.warning(
            "Route berekenen naar %s",
            destination,
        )

        route = await (
            self.route_api.get_route(
                vehicle_lat,
                vehicle_lon,
                destination,
            )
        )

        _LOGGER.warning(
            "Route afstand=%s km tijd=%s min",
            route["distance_km"],
            route["duration_min"],
        )

        anwb_data = await (
            self.anwb_api.get_chargers(
                vehicle_lat,
                vehicle_lon,
                self.radius,
            )
        )

        chargers = anwb_data.get(
            "value",
            []
        )

        _LOGGER.warning(
            "ANWB laadpalen gevonden=%s",
            len(chargers),
        )

        helper = self.hass.states.get(
            "input_select.anwb_lader_filter"
        )

        charger_mode = (
            helper.state
            if helper
            else "Alle laders"
        )

        filtered = (
            filter_chargers_on_route(
                chargers=chargers,
                route_points=route[
                    "coordinates"
                ],
                vehicle_lat=vehicle_lat,
                vehicle_lon=vehicle_lon,
                charger_mode=charger_mode,
                min_power_kw=(
                    self.min_power_kw
                ),
                max_route_distance_km=(
                    self.max_route_distance_km
                ),
            )
        )

        _LOGGER.warning(
            "Route laadpalen over=%s",
            len(filtered),
        )

        for charger in filtered:

            try:

                detour = await (
                    self.route_api.calculate_detour(
                        start_lat=vehicle_lat,
                        start_lon=vehicle_lon,

                        charger_lat=
                        charger[
                            "charger"
                        ][
                            "coordinates"
                        ][
                            "latitude"
                        ],

                        charger_lon=
                        charger[
                            "charger"
                        ][
                            "coordinates"
                        ][
                            "longitude"
                        ],

                        destination=
                        destination,
                    )
                )

                charger[
                    "detour_km"
                ] = detour[
                    "detour_km"
                ]

                charger[
                    "extra_minutes"
                ] = detour[
                    "extra_minutes"
                ]

            except Exception as err:

                _LOGGER.error(
                    "Omrijberekening mislukt: %s",
                    err,
                )

                charger[
                    "detour_km"
                ] = 999

                charger[
                    "extra_minutes"
                ] = 999

        filtered = [
            c
            for c in filtered
            if c["detour_km"] <= 10
        ]

        filtered.sort(
            key=lambda c: (
                c["price"],
                c["detour_km"],
            )
        )

        _LOGGER.warning(
            "Resultaat na omrijfilter=%s",
            len(filtered),
        )
        _LOGGER.warning(
            "ROUTE RESULT route=%s chargers=%s",
            route,
            len(filtered),
        )
        return {

            "route": route,

            "chargers": filtered,

            "vehicle": {

                "latitude":
                    vehicle_lat,

                "longitude":
                    vehicle_lon,
            },

            "destination":
                destination,
        }
