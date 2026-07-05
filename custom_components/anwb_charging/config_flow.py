from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_DEVICE_TRACKER,
    CONF_RADIUS,
    DEFAULT_RADIUS,
)


class AnwbChargingConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """ANWB Charging config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input=None,
    ):
        errors = {}

        if user_input is not None:

            await self.async_set_unique_id(
                f"anwb_charging_{user_input[CONF_DEVICE_TRACKER]}"
            )

            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="ANWB Charging",
                data=user_input,
            )

        registry = er.async_get(self.hass)

        device_trackers = [
            entity_id
            for entity_id in registry.entities
            if entity_id.startswith("device_tracker.")
        ]

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY
                ): TextSelector(),

                vol.Required(
                    CONF_DEVICE_TRACKER
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="device_tracker"
                    )
                ),

                vol.Required(
                    CONF_RADIUS,
                    default=DEFAULT_RADIUS,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
`
