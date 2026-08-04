"""
Configuration Flow voor ANWB Charging Integration.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_DEVICE_TRACKER,
    CONF_ORS_API_KEY,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initiële setup flow voor ANWB Charging integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle initiële configuratie."""

        if user_input is not None:
            await self.async_set_unique_id(
                user_input[CONF_DEVICE_TRACKER]
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="ANWB Charging",
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
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={
                    CONF_ORS_API_KEY: user_input.get(
                        CONF_ORS_API_KEY,
                        ""
                    )
                },
            )

            return self.async_create_entry(
                title="",
                data={}
            )

        current_ors_key = (
            self.config_entry.options.get(CONF_ORS_API_KEY)
            or self.config_entry.data.get(CONF_ORS_API_KEY)
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
                    )
                }
            ),
        )
