"""
ANWB Charging integration entrypoints.
"""

import logging
from typing import Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "anwb_charging"
PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Dict) -> bool:
    """Initialize integration data when Home Assistant starts."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("ANWB_charging: async_setup completed")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up a config entry.

    This stores a small per-entry dict in hass.data and forwards platform setup.
    Coordinator/API objects are typically created in the coordinator module or the platform,
    but you can instantiate them here and store in hass.data[DOMAIN][entry.entry_id]
    if you prefer centralised creation.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Store the ConfigEntry itself for other modules to access if needed
    hass.data[DOMAIN][entry.entry_id]["entry"] = entry

    _LOGGER.debug("ANWB_charging: setting up entry %s", entry.entry_id)

    # Forward setup to platforms (sensor.py will receive the entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry and its platforms, cleaning up stored data.
    """
    _LOGGER.debug("ANWB_charging: unloading entry %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Called when the config entry is removed. Clean up stored data if any.
    """
    _LOGGER.debug("ANWB_charging: removing entry %s", entry.entry_id)
    hass.data[DOMAIN].pop(entry.entry_id, None)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Optional: migrate old config entry data when you bump integration version.

    Extend this to perform migration steps and return True when successful.
    """
    _LOGGER.debug("ANWB_charging: migrating entry %s (version=%s)", entry.entry_id, entry.version)
    # Example migration stub:
    # if entry.version == 1:
    #     data = {**entry.data}
    #     # transform data...
    #     hass.config_entries.async_update_entry(entry, data=data, version=2)
    #     return True
    return True
