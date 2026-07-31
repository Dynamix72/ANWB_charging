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
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial configuration form."""
        if user_input is not None:
            # use device_tracker value as unique id to prevent duplicate installs for same tracker
            await self.async_set_unique_id(user_input[CONF_DEVICE_TRACKER])
            self._abort_if_unique_id_configured()

            # Store entered values (including optional ors_api_key) on the config entry
            return self.async_create_entry(title="ANWB Charging", data=user_input)

        # Default values come from nothing (first run). If you want defaults from options, add logic.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TRACKER
                    ): EntitySelector(
                        EntitySelectorConfig(domain="device_tracker")
                    ),
                    vol.Required(
                        CONF_DESTINATION,
                        default=DEFAULT_DESTINATION,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False,
                            type="text",
                        )
                    ),
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
                    vol.Required(
                        CONF_CHARGER_TYPE,
                        default=DEFAULT_CHARGER_TYPE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=CHARGER_TYPES,
                        )
                    ),
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
        """Return options flow handler for this config entry."""
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for ANWB Charging (destination, max detour, charger type, and ORS API key)."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Show options form to update settings."""
        if user_input is not None:
            # Merge previous options with new values
            # We use config entry options so users can update these without re-creating the entry
            new_options = {**self.entry.options, **user_input}
            self.hass.config_entries.async_update_entry(self.entry, options=new_options)
            return self.async_create_entry(title="", data=new_options)

        # Pre-fill form with existing values (fallback to entry.data or defaults)
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DESTINATION,
                        default=current_destination,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False,
                            type="text",
                        )
                    ),
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
                    vol.Required(
                        CONF_CHARGER_TYPE,
                        default=current_charger_type,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=CHARGER_TYPES,
                        )
                    ),
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default=current_ors_key,
                    ): TextSelector(
                        TextSelectorConfig(multiline=False)
                    ),
                }
            ),
        )
