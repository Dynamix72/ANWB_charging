"""
Coordinator for ANWB route-based selection and fuel/charger fetching.

This module implements RouteCoordinator which is responsible for:
- Deciding whether to fetch chargers, fuel stations, or both (data_mode).
- Respecting runtime overrides via input_select.anwb_data_mode and input_select.anwb_fuel_type when present.
- Performing efficient bounding-box queries against the ANWB POI endpoint and calculating
  distances/durations using OpenRouteService when needed.

Changes in recent updates:
- Added support for fuel station fetching and parsing (euro95/diesel/autogas).
- Reduced noisy logging: many former `_LOGGER.warning` calls were replaced with `info` or `debug`.
"""

from datetime import timedelta
import logging

from geopy.distance import geodesic
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import RouteApi
from .const import (
    CONF_CHARGER_TYPE,
    CONF_DATA_MODE,
    CONF_DESTINATION,
    CONF_FUEL_TYPE,
    DATA_MODES,
    DEFAULT_CHARGER_TYPE,
    DEFAULT_DATA_MODE,
    DEFAULT_FUEL_TYPE,
    DEFAULT_MAX_DETOUR_KM,
    FUEL_TYPES,
)

_LOGGER = logging.getLogger(__name__)


def point_on_route(route_points, target_km):
    """Zoek een punt op de route op target_km vanaf de start."""
    travelled = 0.0
    for i in range(len(route_points) - 1):
        p1 = (route_points[i][1], route_points[i][0])
        p2 = (route_points[i + 1][1], route_points[i + 1][0])
        segment = geodesic(p1, p2).km

        if travelled + segment >= target_km:
            return {"latitude": p2[0], "longitude": p2[1]}

        travelled += segment

    return {"latitude": route_points[-1][1], "longitude": route_points[-1][0]}


class RouteCoordinator(DataUpdateCoordinator):
    """Coordinator voor route-gebaseerde ANWB selectie."""

    def __init__(self, hass, entry, tracker_id, radius, min_power_kw, ors_api_key):
        self.hass = hass
        self.entry = entry
        self.tracker_id = tracker_id
        self.radius = radius
        self.min_power_kw = min_power_kw
        self.ors_api_key = ors_api_key
        self.route_api = RouteApi(hass, ors_api_key)

        super().__init__(
            hass,
            logger=_LOGGER,
            name="ANWB Route Charging",
            update_interval=None,
        )

    def _get_config_value(self, key, default):
        return self.entry.options.get(key) or self.entry.data.get(key) or default

    def _get_entity_state(self, entity_id, default=None):
        entity = self.hass.states.get(entity_id)
        if entity is None:
            return default
        state = (entity.state or "").strip()
        return state if state else default

    def _get_data_mode(self):
        value = self._get_entity_state("input_select.anwb_data_mode")
        if value in DATA_MODES:
            return value
        return self._get_config_value(CONF_DATA_MODE, DEFAULT_DATA_MODE)

    def _get_fuel_type(self):
        value = self._get_entity_state("input_select.anwb_fuel_type")
        if value in FUEL_TYPES:
            return value
        return self._get_config_value(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE)

    def _extract_price_from_station(self, station, fuel_type):
        """Extract the relevant fuel price from an ANWB fuel station object."""
        if not isinstance(station, dict):
            return None

        # Direct price field
        price_data = station.get("price")
        if isinstance(price_data, dict) and price_data.get("price") is not None:
            try:
                return float(price_data.get("price"))
            except (TypeError, ValueError):
                pass

        # Try common fields in ANWB responses
        for field_name in ("fuelPrices", "prices", "fuel_price", "priceComponents"):
            values = station.get(field_name, [])
            if not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict):
                    continue
                code = str(item.get("code") or item.get("name") or item.get("type") or "").upper()
                if item.get("price") is not None and self._fuel_code_matches(code, fuel_type):
                    try:
                        return float(item.get("price"))
                    except (TypeError, ValueError):
                        pass
                components = item.get("priceComponents", [])
                if isinstance(components, list):
                    for component in components:
                        if not isinstance(component, dict):
                            continue
                        component_code = str(component.get("code") or component.get("name") or "").upper()
                        value = component.get("value")
                        if value is not None and self._fuel_code_matches(component_code, fuel_type):
                            try:
                                return float(value)
                            except (TypeError, ValueError):
                                pass

        return None

    def _fuel_code_matches(self, code, fuel_type):
        normalized = str(code).upper().replace("-", "").replace(" ", "")
        if fuel_type == "euro95":
            return normalized in {"EURO95", "E95", "95", "E10", "EURO95E10"}
        if fuel_type == "diesel":
            return normalized in {"DIESEL", "B7", "B100"}
        if fuel_type == "autogas":
            return normalized in {"AUTOGAS", "LPG", "LPGAUTOGAS"}
        return False

    async def _async_fetch_fuels(self, vehicle_lat, vehicle_lon, target_km=None):
        if target_km and target_km < self.radius:
            search_radius = target_km
        else:
            search_radius = self.radius

        fuel_type = self._get_fuel_type()
        data = await self.route_api.get_fuel_stations(vehicle_lat, vehicle_lon, search_radius)
        stations = data.get("value", [])

        filtered = []
        for station in stations:
            price = self._extract_price_from_station(station, fuel_type)
            if price is None:
                continue

            coords = station.get("coordinates", {}) or {}
            lat = coords.get("latitude")
            lon = coords.get("longitude")
            item = {"station": station, "price": price, "power": 0, "distance_km": 0, "duration_minutes": 0}

            if lat is not None and lon is not None:
                try:
                    route_to_station = await self.route_api.get_route(vehicle_lat, vehicle_lon, f"{lat},{lon}")
                    item["distance_km"] = round(route_to_station["distance_km"], 1)
                    item["duration_minutes"] = round(route_to_station["duration_min"], 0)
                except Exception:
                    item["distance_km"] = 0
                    item["duration_minutes"] = 0

            filtered.append(item)

        filtered.sort(key=lambda item: item["price"])
        filtered = filtered[:10]

        return {
            "route": None,
            "chargers": filtered,
            "fuel_stations": filtered,
            "fuel_type": fuel_type,
            "data_mode": "fuels",
            "vehicle": {"latitude": vehicle_lat, "longitude": vehicle_lon},
            "destination": None,
            "charger_type": "fuel",
        }

    async def _async_fetch_chargers(self, vehicle_lat, vehicle_lon, charger_type, destination=None, target_km=None):
        if destination:
            route = await self.route_api.get_route(vehicle_lat, vehicle_lon, destination)
            search_point = point_on_route(route["coordinates"], target_km or 0)
            search_radius = self.radius
        else:
            route = None
            if target_km and target_km < self.radius:
                search_radius = target_km
            else:
                search_radius = self.radius
            search_point = {"latitude": vehicle_lat, "longitude": vehicle_lon}

        anwb_data = await self.route_api.get_chargers(search_point["latitude"], search_point["longitude"], search_radius)
        chargers = anwb_data.get("value", [])

        filtered = []
        for charger in chargers:
            evses = charger.get("electricVehicleSupplyEquipment", []) or []
            statuses = [evse.get("status") for evse in evses if isinstance(evse, dict)]
            if "AVAILABLE" not in statuses and "CHARGING" not in statuses:
                continue

            max_power = 0
            for evse in evses:
                for connector in evse.get("connectors", []) or []:
                    max_power = max(max_power, connector.get("maxPowerInKW", 0))

            if charger_type == "AC laders" and max_power >= 50:
                continue
            elif charger_type == "Snelladers" and (max_power < 50 or max_power >= 100):
                continue
            elif charger_type == "Ultrasnelladers" and max_power < 100:
                continue

            price_data = charger.get("price")
            if price_data and price_data.get("price") is not None:
                price = float(price_data.get("price"))
            else:
                energy_prices = []
                for evse in evses:
                    for connector in evse.get("connectors", []) or []:
                        for tariff in connector.get("prices", []) or []:
                            for component in tariff.get("priceComponents", []) or []:
                                if component.get("code") == "ENERGY":
                                    value = component.get("value")
                                    if value is not None:
                                        energy_prices.append(float(value))
                if not energy_prices:
                    continue
                price = energy_prices[0]

            item = {"charger": charger, "price": price, "power": max_power, "distance_km": 0, "duration_minutes": 0}
            filtered.append(item)

        filtered.sort(key=lambda c: c["price"])[:]
        filtered = filtered[:10]

        for item in filtered:
            charger = item["charger"]
            coords = charger.get("coordinates", {}) or {}
            charger_lat = coords.get("latitude")
            charger_lon = coords.get("longitude")
            if charger_lat is None or charger_lon is None:
                continue
            if destination:
                try:
                    detour = await self.route_api.calculate_detour(vehicle_lat, vehicle_lon, charger_lat, charger_lon, destination)
                    item["distance_km"] = detour.get("detour_km", 0)
                    item["duration_minutes"] = detour.get("extra_minutes", 0)
                except Exception:
                    item["distance_km"] = 0
                    item["duration_minutes"] = 0
            else:
                try:
                    route_to_charger = await self.route_api.get_route(vehicle_lat, vehicle_lon, f"{charger_lat},{charger_lon}")
                    item["distance_km"] = round(route_to_charger["distance_km"], 1)
                    item["duration_minutes"] = round(route_to_charger["duration_min"], 0)
                except Exception:
                    item["distance_km"] = 0
                    item["duration_minutes"] = 0

        return {
            "route": route,
            "chargers": filtered,
            "fuel_stations": [],
            "vehicle": {"latitude": vehicle_lat, "longitude": vehicle_lon},
            "destination": destination,
            "charger_type": charger_type,
            "data_mode": "chargers",
            "fuel_type": self._get_fuel_type(),
        }

    async def _async_update_data(self):
        charger_type_entity = self.hass.states.get("input_select.anwb_lader_filter")
        charger_type = charger_type_entity.state if charger_type_entity else DEFAULT_CHARGER_TYPE

        destination_entity = self.hass.states.get("input_text.anwb_destination")
        destination = (destination_entity.state or "").strip() if destination_entity else ""

        target_km = None
        if destination:
            distance_entity = self.hass.states.get("input_number.anwb_max_detour_km")
            try:
                target_km = float(distance_entity.state)
            except Exception:
                target_km = 10

        tracker = self.hass.states.get(self.tracker_id)
        if tracker is None:
            _LOGGER.info("Tracker %s niet gevonden", self.tracker_id)
            return {"route": None, "chargers": [], "fuel_stations": [], "data_mode": DEFAULT_DATA_MODE, "fuel_type": DEFAULT_FUEL_TYPE}

        vehicle_lat = tracker.attributes.get("latitude")
        vehicle_lon = tracker.attributes.get("longitude")
        if vehicle_lat is None or vehicle_lon is None:
            _LOGGER.info("GPS positie ontbreekt voor tracker %s", self.tracker_id)
            return {"route": None, "chargers": [], "fuel_stations": [], "data_mode": DEFAULT_DATA_MODE, "fuel_type": DEFAULT_FUEL_TYPE}

        data_mode = self._get_data_mode()
        if data_mode == "fuels":
            return await self._async_fetch_fuels(vehicle_lat, vehicle_lon, target_km)
        if data_mode == "both":
            chargers_data = await self._async_fetch_chargers(vehicle_lat, vehicle_lon, charger_type, destination, target_km)
            fuels_data = await self._async_fetch_fuels(vehicle_lat, vehicle_lon, target_km)
            combined = {
                "route": chargers_data.get("route"),
                "chargers": chargers_data.get("chargers", []),
                "fuel_stations": fuels_data.get("fuel_stations", []),
                "vehicle": chargers_data.get("vehicle", {"latitude": vehicle_lat, "longitude": vehicle_lon}),
                "destination": destination,
                "charger_type": charger_type,
                "data_mode": "both",
                "fuel_type": self._get_fuel_type(),
            }
            return combined

        return await self._async_fetch_chargers(vehicle_lat, vehicle_lon, charger_type, destination, target_km)


__all__ = ["RouteCoordinator", "point_on_route"]
