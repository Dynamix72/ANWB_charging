"""
Configuration Flow voor ANWB Fuel & Charging Integration.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_DEVICE_TRACKER,
    CONF_ORS_API_KEY,
    CONF_DATA_MODE,
    CONF_FUEL_TYPE,
    DEFAULT_DATA_MODE,
    DEFAULT_FUEL_TYPE,
    DATA_MODES,
    FUEL_TYPES,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initiële setup flow voor ANWB Fuel & Charging integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle initiële configuratie."""

        if user_input is not None:
            await self.async_set_unique_id(
                user_input[CONF_DEVICE_TRACKER]
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="ANWB Fuel & Charging",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TRACKER
                    ): EntitySelector(
                        EntitySelectorConfig(
                            domain="device_tracker"
                        )
                    ),
                    vol.Optional(
                        CONF_DATA_MODE,
                        default=DEFAULT_DATA_MODE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=DATA_MODES,
                            mode="dropdown",
                            translation_key="data_mode",
                        )
                    ),
                    vol.Optional(
                        CONF_FUEL_TYPE,
                        default=DEFAULT_FUEL_TYPE,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=FUEL_TYPES,
                            mode="dropdown",
                            translation_key="fuel_type",
                        )
                    ),
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default="",
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False
                        )
                    ),
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialiseer options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Toon opties."""

        if user_input is not None:
            new_options = {
                CONF_ORS_API_KEY: user_input.get(CONF_ORS_API_KEY, ""),
                CONF_DATA_MODE: user_input.get(CONF_DATA_MODE, DEFAULT_DATA_MODE),
                CONF_FUEL_TYPE: user_input.get(CONF_FUEL_TYPE, DEFAULT_FUEL_TYPE),
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=new_options,
            )

            return self.async_create_entry(
                title="",
                data={},
            )

        current_ors_key = (
            self.config_entry.options.get(CONF_ORS_API_KEY)
            or self.config_entry.data.get(CONF_ORS_API_KEY)
            or ""
        )
        current_data_mode = (
            self.config_entry.options.get(CONF_DATA_MODE)
            or self.config_entry.data.get(CONF_DATA_MODE)
            or DEFAULT_DATA_MODE
        )
        current_fuel_type = (
            self.config_entry.options.get(CONF_FUEL_TYPE)
            or self.config_entry.data.get(CONF_FUEL_TYPE)
            or DEFAULT_FUEL_TYPE
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DATA_MODE,
                        default=current_data_mode,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=DATA_MODES,
                            mode="dropdown",
                            translation_key="data_mode",
                        )
                    ),
                    vol.Optional(
                        CONF_FUEL_TYPE,
                        default=current_fuel_type,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=FUEL_TYPES,
                            mode="dropdown",
                            translation_key="fuel_type",
                        )
                    ),
                    vol.Optional(
                        CONF_ORS_API_KEY,
                        default=current_ors_key,
                    ): TextSelector(
                        TextSelectorConfig(
                            multiline=False
                        )
                    )
                }
            ),
        )
