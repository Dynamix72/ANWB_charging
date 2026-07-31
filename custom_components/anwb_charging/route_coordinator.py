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
from .const import (
    CONF_MAX_DETOUR_KM,
    CONF_CHARGER_TYPE,
    CONF_DESTINATION,
    DEFAULT_MAX_DETOUR_KM,
    DEFAULT_CHARGER_TYPE,
)

_LOGGER = logging.getLogger(__name__)


class RouteCoordinator(
    DataUpdateCoordinator
):

    def __init__(
        self,
        hass,
        entry,
        tracker_id,
        radius,
        min_power_kw,
        ors_api_key,
    ):

        self.hass = hass
        self.entry = entry

        self.tracker_id = tracker_id

        self.radius = radius

        self.min_power_kw = min_power_kw

        self.ors_api_key = ors_api_key

        self.anwb_api = AnwbApi()

        self.route_api = RouteApi(
            ors_api_key
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name="ANWB Route Charging",
            update_interval=timedelta(minutes=5),
        )

    def _get_config_value(self, key, default):
        """Get config value from options or data."""
        return (
            self.entry.options.get(key)
            or self.entry.data.get(key)
            or default
        )

    async def _async_update_data(self):

        # Get configuration from entry (can be updated via UI)
        max_detour_km = self._get_config_value(
            CONF_MAX_DETOUR_KM,
            DEFAULT_MAX_DETOUR_KM
        )
        charger_type = self._get_config_value(
            CONF_CHARGER_TYPE,
            DEFAULT_CHARGER_TYPE
        )
        destination = self._get_config_value(
            CONF_DESTINATION,
            ""
        )

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

        if not destination:

            _LOGGER.warning(
                "Geen bestemming ingevuld"
            )

            return {
                "route": None,
                "chargers": [],
            }

        _LOGGER.info(
            "Route berekenen naar %s (max omrijden: %s km, ladertype: %s)",
            destination,
            max_detour_km,
            charger_type,
        )

        route = await (
            self.route_api.get_route(
                vehicle_lat,
                vehicle_lon,
                destination,
            )
        )

        _LOGGER.info(
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

        _LOGGER.info(
            "ANWB laadpalen gevonden=%s",
            len(chargers),
        )

        filtered = (
            filter_chargers_on_route(
                chargers=chargers,
                route_points=route[
                    "coordinates"
                ],
                vehicle_lat=vehicle_lat,
                vehicle_lon=vehicle_lon,
                charger_mode=charger_type,
                min_power_kw=(
                    self.min_power_kw
                ),
                max_route_distance_km=5,  # Afstand tot route (vast)
            )
        )

        _LOGGER.info(
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

        # Filter op maximale omrijafstand
        filtered = [
            c
            for c in filtered
            if c["detour_km"] <= max_detour_km
        ]

        # Sorteer op prijs en daarna op omrijafstand
        filtered.sort(
            key=lambda c: (
                c["price"],
                c["detour_km"],
            )
        )

        _LOGGER.info(
            "Resultaat na omrijfilter (max %s km)=%s",
            max_detour_km,
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
            
            "max_detour_km":
                max_detour_km,
            
            "charger_type":
                charger_type,
        }
