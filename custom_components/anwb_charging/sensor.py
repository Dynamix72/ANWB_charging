"""
ANWB charging sensors for Home Assistant.

Improvements over the original:
- No direct /config/secrets.yaml reads (API keys should come from the coordinator or config entry).
- Uses logging instead of print.
- Safer dict access with .get() to avoid KeyError.
- Adds device_info and better unique_id generation.
- Returns None for unknown states (HA will show "unavailable"/unknown) instead of nonstandard strings.
"""

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import AnwbCoordinator
from .route_coordinator import RouteCoordinator
from .const import (
    CONF_ORS_API_KEY,
    DEFAULT_MIN_POWER_KW,
)

DOMAIN = "anwb_charging"

_LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def filter_valid_chargers(chargers: List[Dict]) -> List[Dict]:
    """Return chargers that have price information and at least one AVAILABLE or CHARGING evse."""
    valid: List[Dict] = []

    for charger in chargers:
        if charger.get("price") is None:
            continue

        evses = charger.get("electricVehicleSupplyEquipment", [])
        if not isinstance(evses, list):
            continue

        statuses = [evse.get("status") for evse in evses if isinstance(evse, dict)]

        if "AVAILABLE" in statuses or "CHARGING" in statuses:
            valid.append(charger)

    return valid


def sorted_chargers(data: Dict, hass=None) -> List[Dict]:
    """
    Return the sorted list of valid chargers by price (lowest first).
    Optionally apply a power filter based on an input_select helper in Home Assistant.
    """
    chargers = filter_valid_chargers(data.get("value", []))

    _LOGGER.debug("VALID CHARGERS=%d", len(chargers))

    if hass:
        helper = hass.states.get("input_select.anwb_lader_filter")
        if helper:
            mode = helper.state
            filtered: List[Dict] = []

            for charger in chargers:
                info = extract_charger_info(charger)
                power = info.get("max_power_kw", 0)
    
                if mode == "AC laders":
                    if power < 50:
                        filtered.append(charger)
                
                elif mode == "Snelladers":
                    if 50 <= power < 100:
                        filtered.append(charger)
                
                elif mode == "Ultrasnelladers":
                    if power >= 100:
                        filtered.append(charger)
                
                else:
                    filtered.append(charger)

            chargers = filtered

    _LOGGER.debug("AFTER POWER FILTER=%d", len(chargers))

    def _price_key(c: Dict) -> float:
        try:
            return _safe_float(c.get("price", {}).get("price"))
        except Exception:
            return float("inf")

    return sorted(chargers, key=_price_key)


def extract_charger_info(charger: Dict) -> Dict:
    """Extract aggregated information from charger data."""
    max_power_kw = 0
    total_points = 0
    available_points = 0
    energy_price = None
    energy_display_text: List = []
    session_price = None
    session_display_text: List = []

    evses = charger.get("electricVehicleSupplyEquipment", []) or []
    for evse in evses:
        if not isinstance(evse, dict):
            continue

        total_points += 1
        if evse.get("status") == "AVAILABLE":
            available_points += 1

        connectors = evse.get("connectors", []) or []
        for connector in connectors:
            if not isinstance(connector, dict):
                continue

            max_power_kw = max(
                max_power_kw, _safe_float(connector.get("maxPowerInKW", 0), 0)
            )

            for tariff in connector.get("prices", []) or []:
                if not isinstance(tariff, dict):
                    continue
                for component in tariff.get("priceComponents", []) or []:
                    if not isinstance(component, dict):
                        continue

                    code = component.get("code")
                    if code == "ENERGY" and energy_price is None:
                        energy_price = component.get("value")
                        energy_display_text = component.get("displayText", [])
                    if code == "SESSION" and session_price is None:
                        session_price = component.get("value")
                        session_display_text = component.get("displayText", [])

    return {
        "max_power_kw": max_power_kw,
        "charge_points_total": total_points,
        "charge_points_available": available_points,
        "availability_text": f"{available_points}/{total_points}",
        "energy_price": energy_price,
        "energy_display_text": energy_display_text,
        "session_price": session_price,
        "session_display_text": session_display_text,
    }


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up ANWB sensors from a config entry."""
    # Coordinator should be responsible for API key and refresh logic.
    coordinator = AnwbCoordinator(
        hass,
        entry.data.get("device_tracker"),
        entry.options.get("radius")
        or entry.data.get("radius")
        or 10,
    )

    await coordinator.async_config_entry_first_refresh()
 
    route_coordinator = RouteCoordinator(
        hass,
        entry,
        entry.data.get("device_tracker"),
        entry.options.get("radius")
        or entry.data.get("radius")
        or 10,
        DEFAULT_MIN_POWER_KW,
        entry.options.get(CONF_ORS_API_KEY)
        or entry.data.get(CONF_ORS_API_KEY)
        or "",
    )

    await route_coordinator.async_config_entry_first_refresh()

    entities: List[SensorEntity] = [
        CheapestChargerSensor(route_coordinator, entry.entry_id),
        ChargerCountSensor(route_coordinator, entry.entry_id),
    
        RouteGeoJsonSensor(
            route_coordinator,
            entry.entry_id,
        ),
    ]

    # Create top N sensors (1..10)
    for rank in range(1, 11):
        entities.append(TopChargerSensor(route_coordinator, entry.entry_id, rank))

    async_add_entities(entities)


class AnwbBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for ANWB sensors."""

    def __init__(self, coordinator, entry_id: Optional[str], name: str, unique_id: str):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = name
        # include entry_id in unique_id when present to allow multiple installs
        self._attr_unique_id = f"{entry_id}_{unique_id}" if entry_id else unique_id
        self._attr_should_poll = False

        # device_info to group all sensors under one device in HA
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id or unique_id)},
            "name": "ANWB Charging",
            "manufacturer": "ANWB",
            "model": "ANWB Charging Integration",
        }


class CheapestChargerSensor(AnwbBaseSensor):
    """Sensor that exposes the title of the cheapest charger."""

    def __init__(self, coordinator, entry_id: Optional[str]):
        super().__init__(
            coordinator,
            entry_id,
            name="ANWB Cheapest Charger",
            unique_id="anwb_cheapest",
        )

    @property
    def native_value(self) -> Optional[str]:
        chargers = sorted_chargers(self.coordinator.data, self.coordinator.hass)

        if not chargers:
            return None

        return chargers[0].get("title")


class ChargerCountSensor(AnwbBaseSensor):
    """Sensor that returns the number of (filtered) chargers."""

    def __init__(self, coordinator, entry_id: Optional[str]):
        super().__init__(
            coordinator,
            entry_id,
            name="ANWB Charger Count",
            unique_id="anwb_charger_count",
        )
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> Optional[int]:
    
        data = self.coordinator.data or {}
    
        chargers
            "chargers",
            []
        )
    
        return len(chargers)


class TopChargerSensor(AnwbBaseSensor):
    """Sensor for the Nth top charger."""

    def __init__(self, coordinator, entry_id: Optional[str], rank: int):
        super().__init__(
            coordinator,
            entry_id,
            name=f"ANWB Top {rank}",
            unique_id=f"anwb_top_{rank}",
        )
        self.rank = rank

    def _charger(self):
        chargers = (
            self.coordinator.data or {}
        ).get(
            "chargers",
            []
        )
    
        index = self.rank - 1
    
        if index < 0 or index >= len(chargers):
            return None
    
        charger_data = chargers[index]
    
        if isinstance(charger_data, dict):
            return charger_data.get(
                "charger",
                charger_data,
            )
    
        return None
     

    @property
    def available(self) -> bool:
        """Alleen beschikbaar als er een laadpaal bestaat."""
        return self._charger() is not None
    
    @property
    def native_value(self) -> Optional[str]:
        charger = self._charger()
        if charger is None:
            return None
        return charger.get("title")

    @property
    def extra_state_attributes(self) -> Dict:
        charger = self._charger()
        if charger is None:
            return {}

        status = "AVAILABLE"
        for evse in charger.get("electricVehicleSupplyEquipment", []) or []:
            if evse.get("status") == "CHARGING":
                status = "CHARGING"
                break

        info = extract_charger_info(charger)

        price_info = charger.get("price") or {}
        address = charger.get("address") or {}
        coords = charger.get("coordinates") or {}

        attributes = {
            "rank": self.rank,
            "price_per_kwh": info.get("energy_price"),
            "price_display_text": info.get("energy_display_text"),
            "session_price": info.get("session_price"),
            "session_display_text": info.get("session_display_text"),
            "max_power_kw": info.get("max_power_kw"),
            "charge_points_total": info.get("charge_points_total"),
            "charge_points_available": info.get("charge_points_available"),
            "availability_text": info.get("availability_text"),
            "currency": price_info.get("currency"),
            "street": address.get("streetAddress"),
            "postal_code": address.get("postalCode"),
            "city": address.get("city"),
            "full_address": ", ".join(
                filter(
                    None,
                    [
                        address.get("streetAddress"),
                        address.get("postalCode"),
                        address.get("city"),
                    ],
                )
            ),
            "status": status,
            "icon": "mdi:lightning-bolt" if status == "CHARGING" else "mdi:ev-station",
            "latitude": _safe_float(coords.get("latitude"), None),
            "longitude": _safe_float(coords.get("longitude"), None),
        }

        # Remove None values to keep attributes compact/serializable
        return {k: v for k, v in attributes.items() if v is not None}


# Route sensors left largely as-is, but should be wired to a RouteCoordinator if used.
class RouteTestSensor(AnwbBaseSensor):
    def __init__(self, coordinator, entry_id: Optional[str]):
        super().__init__(
            coordinator,
            entry_id,
            name="ANWB Route Test",
            unique_id="anwb_route_test",
        )

    @property
    def native_value(self):
        return "Route API OK"

    @property
    def extra_state_attributes(self):
        return {"status": "Test sensor actief"}


class RouteDistanceSensor(SensorEntity):
    def __init__(self, route_coordinator):
        self.coordinator = route_coordinator
        self._attr_name = "ANWB Route Distance"
        self._attr_unique_id = f"anwb_route_distance_{getattr(route_coordinator, 'entry_id', '')}"
        self._attr_should_poll = False

    @property
    def native_value(self):
        return str(self.coordinator.data)[:255]

    @property
    def extra_state_attributes(self):
        route = self.coordinator.data.get("route")
        if not route:
            return {}
        return {
            "duration_min": route.get("duration_min"),
            "destination": route.get("destination"),
            "route_points": len(route.get("coordinates", [])),
            "coordinates": route.get("coordinates", []),
        }


class RouteGeoJsonSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id: Optional[str]):
        super().__init__(coordinator)
        self._attr_name = "ANWB Route GeoJSON"
        self._attr_unique_id = f"anwb_route_geojson_{entry_id or ''}"
        self._attr_should_poll = False

    @property
    def native_value(self):
        route = (self.coordinator.data or {}).get("route") or {}
    
        if not route.get("geojson"):
            return "geen_route"
    
        return "route"
        
    @property
    def extra_state_attributes(self):
        route = (self.coordinator.data or {}).get("route") or {}
        geojson = route.get("geojson", {})
    
        latitude = None
        longitude = None
    
        try:
            coords = geojson["features"][0]["geometry"]["coordinates"][0]
            longitude = coords[0]
            latitude = coords[1]
        except Exception:
            pass
    
        return {
            "geojson": geojson,
            "latitude": latitude,
            "longitude": longitude,
        }

