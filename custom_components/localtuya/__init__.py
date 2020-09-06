"""The LocalTuya integration integration."""
import asyncio

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_TYPE, DOMAIN, DEVICE_TYPE_POWER_OUTLET


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    if entry.data[CONF_DEVICE_TYPE] == DEVICE_TYPE_POWER_OUTLET:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "switch")
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Nothing is stored and no persistent connections exist, so nothing to do
    return True
