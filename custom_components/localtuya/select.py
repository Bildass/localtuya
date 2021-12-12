"""Platform to present any Tuya DP as an enumeration."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.select import DOMAIN, SelectEntity
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    STATE_UNKNOWN,
)

from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)

CONF_OPTIONS = "select_options"
CONF_OPTIONS_FRIENDLY = "select_options_friendly"


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Required(CONF_OPTIONS): str,
        vol.Optional(CONF_OPTIONS_FRIENDLY): str,
    }


class LocaltuyaSelect(LocalTuyaEntity, SelectEntity):
    """Representation of a Tuya Enumeration."""

    def __init__(
        self,
        device,
        config_entry,
        sensorid,
        **kwargs,
    ):
        """Initialize the Tuya sensor."""
        super().__init__(device, config_entry, sensorid, _LOGGER, **kwargs)
        self._state = STATE_UNKNOWN
        self._validOptions = self._config.get(CONF_OPTIONS).split(';')

        # Set Display options
        self._displayOptions = []
        displayOptionsStr = ""
        if (CONF_OPTIONS_FRIENDLY in self._config):
            displayOptionsStr = self._config.get(CONF_OPTIONS_FRIENDLY).strip()
        _LOGGER.debug("Display Options Configured: " + displayOptionsStr)

        if (displayOptionsStr.find(";") >= 0):
            self._displayOptions = displayOptionsStr.split(';')
        elif (len(displayOptionsStr.strip()) > 0):
            self._displayOptions.append(displayOptionsStr)
        else:
            # Default display string to raw string
            _LOGGER.debug("No Display options configured - defaulting to raw values")
            self._displayOptions = self._validOptions

        _LOGGER.debug("Total Raw Options: " + str(len(self._validOptions)) + 
                      " - Total Display Options: " + str(len(self._displayOptions)))
        if (len(self._validOptions) > len(self._displayOptions)):
            # If list of display items smaller than list of valid items, 
            # then default remaining items to be the raw value
            _LOGGER.debug("Valid options is larger than display options - \
                           filling up with raw values")
            for i in range(len(self._displayOptions), len(self._validOptions)):
                self._displayOptions.append(self._validOptions[i])

    @property
    def current_option(self) -> str:
        """Return the current value."""
        return self._stateFriendly

    @property
    def options(self) -> list:
        """Return the list of values."""
        return self._displayOptions

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_select_option(self, option: str) -> None:
        """Update the current value."""
        optionValue = self._validOptions[self._displayOptions.index(option)]
        _LOGGER.debug("Sending Option: " + option + " -> " + optionValue)
        await self._device.set_dp(optionValue, self._dp_id)

    def status_updated(self):
        """Device status was updated."""
        state = self.dps(self._dp_id)
        self._stateFriendly = self._displayOptions[self._validOptions.index(state)]
        self._state = state


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSelect, flow_schema)
