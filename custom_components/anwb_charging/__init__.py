from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True
