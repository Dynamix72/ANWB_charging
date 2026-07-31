"""
Configuration Flow voor ANWB Charging Integration.

Dit bestand definieert:
1. ConfigFlow - initiële setup formulier
2. OptionsFlowHandler - instellingen wijzigen formulier

Gebruiker kan instellen:
- Device Tracker (GPS bron)
- Bestemming (waar wil je heen)
- Maximale omrijafstand (hoeveel km extra rijden accepteer je)
- Ladertype (AC, Snellader, Ultrasnellader, of Alle)
- OpenRouteService API Key (optioneel, voor routeberekening)
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_DEVICE_TRACKER,
    CONF_RADIUS,
    CONF_MAX_DETOUR_KM,
    CONF_CHARGER_TYPE,
    CONF_DESTINATION,
    CONF_ORS_API_KEY,
    DEFAULT_RADIUS,
    DEFAULT_MAX_DETOUR_KM,
    DEFAULT_CHARGER_TYPE,
    DEFAULT_DESTINATION,
    CHARGER_TYPES,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initiële setup flow voor ANWB Charging integration."""
    
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle de initiële configuratie stap.
        
        Gebruiker moet selecteren:
        - Device Tracker (voor GPS locatie)
        - Bestemming (waar wil je heen)
        - Maximale omrijafstand (hoeveel km extra rijden is ok)
        - Ladertype (welke soort laadpalen)
        - ORS API Key (optioneel, voor betere routeberekening)
        """
        if user_input is not None:
            # Gebruik device_tracker als unique ID om duplicaten te voorkomen
            await self.async_set_unique_id(user_input[CONF_DEVICE_TRACKER])
            self._abort_if_unique_id_configured()

            # Sla instellingen op in config entry
            return self.async_create_entry(title="ANWB Charging", data=user_input)

        # Toon setup formulier met alle velden
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    # Verplicht: Selecteer device tracker voor GPS
                    vol.Required(
                        CONF_DEVICE_TRACKER
                    ): EntitySelector(
                        EntitySelectorConfig(domain="device_tracker")
                    ),
                    
                    # Verplicht: Bestemming (adres of plaats)
                    vol.Required(
                        CONF_DESTINATION,
                        default=DEFAULT_DESTINATION,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False,
                            type="text",
                        )
                    ),
                    
                    # Verplicht: Maximale omrijafstand (1-100 km)
                    vol.Required(
                        CONF_MAX_DETOUR_KM,
                        default=DEFAULT_MAX_DETOUR_KM,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=100,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    
                    # Verplicht: Ladertype selectie
                    vol.Required(
                        CONF_CHARGER_TYPE,
                        default=DEFAULT_CHARGER_TYPE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=CHARGER_TYPES,
                        )
                    ),
                    
                    # Optioneel: OpenRouteService API Key voor routeberekening
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default="",
                    ): TextSelector(TextSelectorConfig(multiline=False)),
                }
            ),
        )

    @staticmethod
    @config_entries.HANDLERS.register("anwb_charging")
    def async_get_options_flow(entry):
        """Geef options flow handler terug voor instellingen wijzigen.
        
        Dit staat gebruiker toe om instellingen aan te passen
        zonder de integration opnieuw in te stellen.
        """
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle instellingen wijzigen na initiële setup.
    
    Gebruiker kan wijzigen:
    - Bestemming
    - Maximale omrijafstand
    - Ladertype
    - ORS API Key
    """

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialiseer options handler."""
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Toon instellingen formulier en verwerk wijzigingen.
        
        Wijzigingen worden direct opgeslagen en kunnen onmiddellijk
        gebruikt worden door coordinators.
        """
        if user_input is not None:
            # Merge vorige opties met nieuwe waarden
            # Options hebben voorrang boven data (initiële setup)
            new_options = {**self.entry.options, **user_input}
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            return self.async_create_entry(title="", data=new_options)

        # Pre-fill formulier met huidige waarden
        # Prioriteit: options > data > default
        current_destination = (
            self.entry.options.get(CONF_DESTINATION)
            or self.entry.data.get(CONF_DESTINATION)
            or DEFAULT_DESTINATION
        )
        current_max_detour = (
            self.entry.options.get(CONF_MAX_DETOUR_KM)
            or self.entry.data.get(CONF_MAX_DETOUR_KM)
            or DEFAULT_MAX_DETOUR_KM
        )
        current_charger_type = (
            self.entry.options.get(CONF_CHARGER_TYPE)
            or self.entry.data.get(CONF_CHARGER_TYPE)
            or DEFAULT_CHARGER_TYPE
        )
        current_ors_key = (
            self.entry.options.get(CONF_ORS_API_KEY)
            or self.entry.data.get(CONF_ORS_API_KEY)
            or ""
        )

        # Toon instellingen formulier
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # Wijzigbare: Bestemming
                    vol.Required(
                        CONF_DESTINATION,
                        default=current_destination,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False,
                            type="text",
                        )
                    ),
                    
                    # Wijzigbare: Maximale omrijafstand
                    vol.Required(
                        CONF_MAX_DETOUR_KM,
                        default=current_max_detour,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=1,
                            max=100,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    
                    # Wijzigbare: Ladertype
                    vol.Required(
                        CONF_CHARGER_TYPE,
                        default=current_charger_type,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=CHARGER_TYPES,
                        )
                    ),
                    
                    # Wijzigbare: ORS API Key
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default=current_ors_key,
                    ): TextSelector(
                        TextSelectorConfig(multiline=False)
                    ),
                }
            ),
        )
