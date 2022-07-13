"""Platform to present any Tuya DP as a number."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity
from homeassistant.const import CONF_DEVICE_CLASS, STATE_UNKNOWN
from homeassistant.helpers.restore_state import RestoreEntity

from .common import LocalTuyaEntity, async_setup_entry

_LOGGER = logging.getLogger(__name__)

from .const import (
    CONF_DEFAULT_VALUE,
    CONF_MIN_VALUE,
    CONF_MAX_VALUE,
    CONF_DEFAULT_VALUE,
    CONF_RESTORE_ON_RECONNECT,
)

DEFAULT_MIN = 0
DEFAULT_MAX = 100000


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_MIN_VALUE, default=DEFAULT_MIN): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Required(CONF_MAX_VALUE, default=DEFAULT_MAX): vol.All(
            vol.Coerce(float),
            vol.Range(min=-1000000.0, max=1000000.0),
        ),
        vol.Optional(CONF_DEFAULT_VALUE): str,
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
    }


class LocaltuyaNumber(LocalTuyaEntity, NumberEntity, RestoreEntity):
    """Representation of a Tuya Number."""

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

        self._min_value = DEFAULT_MIN
        if CONF_MIN_VALUE in self._config:
            self._min_value = self._config.get(CONF_MIN_VALUE)

        self._max_value = self._config.get(CONF_MAX_VALUE)

        #Override standard default value handling to cast to a float
        default_value = self._config.get(CONF_DEFAULT_VALUE)
        if default_value is not None:
            self._default_value = float(default_value)

    @property
    def value(self) -> float:
        """Return sensor state."""
        return self._state

    @property
    def min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    async def async_set_value(self, value: float) -> None:
        """Update the current value."""
        await self._device.set_dp(value, self._dp_id)

    # Default value is the minimum value
    def entity_default_value(self):
        return self._min_value


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaNumber, flow_schema)
