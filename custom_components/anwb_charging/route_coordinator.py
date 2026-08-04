"""
RouteCoordinator voor ANWB Charging Integration.

Dit coordinator verwerkt routes naar een bestemming en zoekt de goedkoopste laadpalen
onderweg rekening houdend met omrijafstand.

Workflow:
1. Haalt configuratie op (bestemming, max omrijafstand, ladertype)
2. PROBEERT route via OpenRouteService (ORS) te berekenen
3. Bij fout of geen bestemming: FALLBACK naar simpele laadpaalzoeken op huidige locatie
4. Haalt beschikbare laadpalen op via ANWB API
5. Filtert laadpalen op basis van route (indien beschikbaar) of gewoon beschikbaarheid
6. Berekent omrijafstand voor elke laadpaal (indien route beschikbaar)
7. Sorteert op prijs en omrijafstand
8. Retourneert gefilterde en gesorteerde resultaten

Updates: Geen automatische updates - alleen op knopdruk via UI

FALLBACK SCENARIO:
- Geen bestemming ingevuld → Zoekt laadpalen bij huidige locatie
- Route API error (quota, timeout) → Zoekt laadpalen bij huidige locatie
- Geen laadpalen op route → Toont laadpalen in buurt
"""

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
    """Coordinator voor route-gebaseerde laadpaalselectie met omrijfiltering.
    
    Ondersteunt fallback naar simpele laadpaalzoeken als route niet beschikbaar is.
    """

    def __init__(
        self,
        hass,
        entry,
        tracker_id,
        radius,
        min_power_kw,
        ors_api_key,
    ):
        """Initialiseer RouteCoordinator.
        
        Args:
            hass: Home Assistant instance
            entry: Config entry met instellingen
            tracker_id: Entity ID van device tracker (voor GPS locatie)
            radius: Search radius in km rond huidige locatie (vast 10 km)
            min_power_kw: Minimaal vermogen laadpaal in kW
            ors_api_key: OpenRouteService API key voor routeberekening
        """

        self.hass = hass
        self.entry = entry

        self.tracker_id = tracker_id
        self.radius = radius
        self.min_power_kw = min_power_kw
        self.ors_api_key = ors_api_key

        # Initialiseer API clients
        self.anwb_api = AnwbApi(hass)
        self.route_api = RouteApi(hass, ors_api_key)

        # Geen automatische updates - coordinator wordt alleen handmatig aangeroepen
        super().__init__(
            hass,
            logger=_LOGGER,
            name="ANWB Route Charging",
            update_interval=None,
        )

    def _get_config_value(self, key, default):
        """Haal configuratiewaarde op uit options of data.
        
        Prioriteit:
        1. entry.options (door gebruiker ingesteld in UI)
        2. entry.data (initiële setup waarden)
        3. default waarde
        
        Args:
            key: Configuratiekey
            default: Default waarde als key niet gevonden
            
        Returns:
            Configuratiewaarde
        """
        return (
            self.entry.options.get(key)
            or self.entry.data.get(key)
            or default
        )

    async def _async_update_data(self):
        """Voer volledige route en laadpaalanalyse uit.
        
        Dit is de main methode die wordt aangeroepen wanneer gebruiker
        de "Update" knop indrukt in de UI.
        
        FALLBACK: Als geen bestemming of route error:
        - Zoekt laadpalen bij huidige locatie
        - Sorteert alleen op prijs
        - Geen omrijberekening
        
        Returns:
            Dict met route data (of None), gefilterde laadpalen en voertuigpositie
        """

        # Lees huidige instellingen uit configuratie
        max_detour_km = self._get_config_value(
            CONF_MAX_DETOUR_KM,
            DEFAULT_MAX_DETOUR_KM
        )
        charger_type = self._get_config_value(
            CONF_CHARGER_TYPE,
            DEFAULT_CHARGER_TYPE
        )
        destination_entity = self.hass.states.get(
            "input_text.anwb_route_destination"
        )
        
        if destination_entity:
            destination = (destination_entity.state or "").strip()
        else:
            destination = ""

        # Haal huidige voertuigpositie op via device tracker
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

        # Extraheer GPS coordinaten
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

        # FALLBACK: Als geen bestemming ingevuld, ga direct naar laadpalen zoeken
        if not destination:
            _LOGGER.info(
                "Geen bestemming ingevuld - FALLBACK naar simpel laadpaal zoeken"
            )
            return await self._async_fallback_chargers(
                vehicle_lat,
                vehicle_lon,
                charger_type,
            )

        # STAP 1: Bereken route via OpenRouteService
        route = None
        try:
            _LOGGER.info(
                "Route berekenen naar %s (max omrijden: %s km, ladertype: %s)",
                destination,
                max_detour_km,
                charger_type,
            )

            route = await self.route_api.get_route(
                vehicle_lat,
                vehicle_lon,
                destination,
            )

            _LOGGER.info(
                "Route afstand=%s km tijd=%s min",
                route["distance_km"],
                route["duration_min"],
            )

        except Exception as err:
            # FALLBACK: Route error (quota overschreden, timeout, etc)
            _LOGGER.warning(
                "Route berekening mislukt (%s) - FALLBACK naar simpel laadpaal zoeken",
                err,
            )
            return await self._async_fallback_chargers(
                vehicle_lat,
                vehicle_lon,
                charger_type,
            )

        # STAP 2: Haal laadpalen op van ANWB
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

        # STAP 3: Filter laadpalen op route
        # Filters:
        # - Laadpaal beschikbaar (AVAILABLE of CHARGING status)
        # - Juiste ladertype (AC/Snellader/Ultrasnellader)
        # - Maximaal 5 km van de route af
        # - Voor de auto op de route
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
                max_route_distance_km=5,  # Vast ingesteld - niet aanpasbaar
            )
        )

        _LOGGER.info(
            "Route laadpalen over=%s",
            len(filtered),
        )


        # Alleen sorteren op prijs
        filtered.sort(
            key=lambda c: c["price"]
        )
        
        # Top 10 goedkoopste laadpalen op de route
        filtered = filtered[:10]
        
        _LOGGER.info(
            "Top 10 goedkoopste laadpalen op route=%s",
            len(filtered),
        )

        return {
            "route": route,
            "chargers": filtered,
            "vehicle": {
                "latitude": vehicle_lat,
                "longitude": vehicle_lon,
            },
            "destination": destination,
            "charger_type": charger_type,
        }

    async def _async_fallback_chargers(
        self,
        vehicle_lat,
        vehicle_lon,
        charger_type,
    ):
        """FALLBACK: Zoek laadpalen bij huidige locatie zonder routeberekening.
        
        Dit wordt gebruikt als:
        - Geen bestemming ingevuld
        - Route API error (quota overschreden, timeout, etc)
        - Geen laadpalen op route gevonden
        
        Args:
            vehicle_lat: Huidige breedtegraad
            vehicle_lon: Huidige lengtegraad
            charger_type: Ladertype filter
            
        Returns:
            Dict met laadpalen gesorteerd op prijs
        """
        _LOGGER.info(
            "FALLBACK: Laadpalen zoeken op huidige locatie (geen route)"
        )

        # Haal laadpalen op van ANWB
        anwb_data = await self.anwb_api.get_chargers(
            vehicle_lat,
            vehicle_lon,
            self.radius,
        )

        chargers = anwb_data.get("value", [])

        _LOGGER.info(
            "FALLBACK: %d laadpalen gevonden",
            len(chargers),
        )

        # Eenvoudig filter: beschikbaarheid en ladertype
        filtered = []
        for charger in chargers:
            # Check beschikbaarheid
            evses = charger.get("electricVehicleSupplyEquipment", [])
            statuses = [evse.get("status") for evse in evses if isinstance(evse, dict)]
            
            if "AVAILABLE" not in statuses and "CHARGING" not in statuses:
                continue

            # Check ladertype
            max_power = 0
            for evse in evses:
                for connector in evse.get("connectors", []):
                    max_power = max(max_power, connector.get("maxPowerInKW", 0))

            # Filter op ladertype
            if charger_type == "AC laders" and max_power >= 50:
                continue
            elif charger_type == "Snelladers" and (max_power < 50 or max_power >= 150):
                continue
            elif charger_type == "Ultrasnelladers" and max_power < 150:
                continue

            # Extract prijs
            price_data = charger.get("price", {})
            if not price_data:
                price = 999
            else:
                try:
                    price = float(price_data.get("price", 999))
                except Exception:
                    price = 999

            filtered.append({
                "charger": charger,
                "price": price,
                "power": max_power,
                "detour_km": 0,  # Geen omrijden nodig - we zijn op deze locatie
                "extra_minutes": 0,
            })

        # Sorteer alleen op prijs (geen route beschikbaar)
        filtered.sort(key=lambda c: c["price"])

        _LOGGER.info(
            "FALLBACK: %d laadpalen beschikbaar na filter",
            len(filtered),
        )

        return {
            "route": {},  # Geen route berekend
            "chargers": filtered,
            "vehicle": {
                "latitude": vehicle_lat,
                "longitude": vehicle_lon,
            },
            "destination": None,
            "max_detour_km": 0,
            "charger_type": charger_type,
        }
