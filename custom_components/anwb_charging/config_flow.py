"""
Configuration Flow voor ANWB Charging Integration.

Dit bestand definieert:
1. ConfigFlow - initiële setup formulier
2. OptionsFlowHandler - instellingen wijzigen formulier

Gebruiker kan instellen:
- Device Tracker (GPS bron)
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

    async def async_step_init(self, user_input=None):
        """Toon instellingen formulier."""
    
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.entry,
                options={
                    CONF_ORS_API_KEY: user_input.get(CONF_ORS_API_KEY, "")
                },
            )
            return self.async_create_entry(title="", data={})
    
        current_ors_key = (
            self.entry.options.get(CONF_ORS_API_KEY)
            or self.entry.data.get(CONF_ORS_API_KEY)
            or ""
        )
    
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default=current_ors_key,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False,
                        )
                    ),
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
    - ORS API Key
    """

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialiseer options handler."""
        self.entry = entry

    async def async_step_init(self, user_input=None):
    """Toon instellingen formulier."""

    if user_input is not None:
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={
                CONF_ORS_API_KEY: user_input.get(
                    CONF_ORS_API_KEY,
                    ""
                )
            },
        )
        return self.async_create_entry(title="", data={})

    current_ors_key = (
        self.entry.options.get(CONF_ORS_API_KEY)
        or self.entry.data.get(CONF_ORS_API_KEY)
        or ""
    )

    return self.async_show_form(
        step_id="init",
        data_schema=vol.Schema(
            {
                vol.Optional(
                    CONF_ORS_API_KEY,
                    default=current_ors_key,
                ): TextSelector(
                    TextSelectorConfig(
                        multiline=False
                    )
                ),
            }
        ),
    )
