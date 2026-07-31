"""
AnwbCoordinator voor basiscoordinator functionaliteit.

Dit coordinator haalt laadpalen op van de ANWB API gebaseerd op:
- Huidige voertuigpositie (van device tracker)
- Ingestelde radius (standaard 10 km, vast)

Dit is de eenvoudigere variant zonder routeberekening.
Gebruikt voor het ophalen van laadpalen in een bepaald gebied.

Updates: Geen automatische updates - alleen op knopdruk via UI
"""

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import AnwbApi

_LOGGER = logging.getLogger(__name__)


class AnwbCoordinator(DataUpdateCoordinator):
    """Coordinator voor ANWB laadpaal API data ophalen."""

    def __init__(
        self,
        hass,
        tracker_id,
        radius,
    ):
        """Initialiseer AnwbCoordinator.
        
        Args:
            hass: Home Assistant instance
            tracker_id: Entity ID van device tracker (voor GPS locatie)
            radius: Search radius in km rond huidige locatie (standaard 10 km)
        """

        self.hass = hass
        self.tracker_id = tracker_id
        self.radius = radius
        
        # Initialiseer ANWB API client
        self.api = AnwbApi(hass)

        # Geen automatische updates - coordinator wordt alleen handmatig aangeroepen
        super().__init__(
            hass,
            logger=_LOGGER,
            name="ANWB Charging",
            update_interval=None,
        )

    async def _async_update_data(self):
        """Haal laadpalen op van ANWB API.
        
        Dit is de main methode die wordt aangeroepen wanneer gebruiker
        de "Update" knop indrukt in de UI.
        
        Returns:
            Dict met ANWB API response (bevat "value" list met laadpalen)
        """

        # Haal huidige voertuigpositie op via device tracker
        tracker = self.hass.states.get(
            self.tracker_id
        )

        if tracker is None:
            _LOGGER.error(
                "Tracker %s niet gevonden",
                self.tracker_id,
            )
            return {"value": []}

        # Extraheer GPS coordinaten
        lat = tracker.attributes.get("latitude")
        lon = tracker.attributes.get("longitude")

        _LOGGER.info(
            "ANWB GPS lat=%s lon=%s",
            lat,
            lon,
        )

        # Roep ANWB API aan om laadpalen in radius op te halen
        data = await self.api.get_chargers(
            lat,
            lon,
            self.radius,
        )

        _LOGGER.info(
            "ANWB Response: %d chargers gevonden",
            len(data.get("value", [])),
        )

        return data
