"""
ANWB Fuel & Charging integration entrypoints.

Display name updated to reflect support for both charging locations and fuel stations.
Includes migration logic to rename existing config entries so the UI shows the new display name.
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
    Migrate existing config entries to the new integration display name and version.

    - If an existing config entry has the old title "ANWB Charging", rename it to
      "ANWB Fuel & Charging" so it shows correctly in the Home Assistant UI.
    - Bumps the entry.version to 2 to indicate migration was applied.

    Return True on success.
    """
    _LOGGER.debug(
        "ANWB_charging: migrating entry %s (version=%s)", entry.entry_id, entry.version
    )

    # Only run migration logic for version 1 entries
    if entry.version == 1:
        try:
            # Rename title if it matches the old display name
            if entry.title == "ANWB Charging":
                _LOGGER.info(
                    "Migrating config entry title for %s -> 'ANWB Fuel & Charging'",
                    entry.entry_id,
                )
                hass.config_entries.async_update_entry(entry, title="ANWB Fuel & Charging")

            # If you need to modify stored data/options also do it here. Example:
            # data = {**entry.data}
            # data.setdefault('data_mode', 'chargers')
            # hass.config_entries.async_update_entry(entry, data=data)

            # Bump version to 2 so migration does not run again
            entry.version = 2
            _LOGGER.info("Migration of ANWB entry %s to version 2 complete", entry.entry_id)
        except Exception as err:
            _LOGGER.exception("Failed to migrate ANWB config entry %s: %s", entry.entry_id, err)
            return False

    return True
