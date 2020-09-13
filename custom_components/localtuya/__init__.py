"""The LocalTuya integration integration."""
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_ID,
    CONF_ICON,
    CONF_NAME,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_PLATFORM,
    CONF_ENTITIES,
)
import homeassistant.helpers.config_validation as cv

from . import pytuya
from .const import CONF_LOCAL_KEY, CONF_PROTOCOL_VERSION, DOMAIN, PLATFORMS


DEFAULT_ID = "1"
DEFAULT_PROTOCOL_VERSION = 3.3

BASE_PLATFORM_SCHEMA = {
    vol.Optional(CONF_ICON): cv.icon,  # Deprecated: not used
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Optional(CONF_NAME): cv.string,  # Deprecated: not used
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(
        float
    ),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
}


def prepare_setup_entities(config_entry, platform):
    """Prepare ro setup entities for a platform."""
    entities_to_setup = [
        entity
        for entity in config_entry.data[CONF_ENTITIES]
        if entity[CONF_PLATFORM] == platform
    ]
    if not entities_to_setup:
        return None, None

    device = pytuya.BulbDevice(
        config_entry.data[CONF_DEVICE_ID],
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_LOCAL_KEY],
    )
    device.set_version(float(config_entry.data[CONF_PROTOCOL_VERSION]))
    device.set_dpsUsed({})
    return device, entities_to_setup


def import_from_yaml(hass, config, platform):
    """Import configuration from YAML."""
    config[CONF_PLATFORM] = platform
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=config
        )
    )

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the LocalTuya integration component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up LocalTuya integration from a config entry."""
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Nothing is stored and no persistent connections exist, so nothing to do
    return True
