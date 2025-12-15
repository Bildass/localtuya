"""Platform to present any Tuya DP as a number."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.number import DOMAIN, NumberEntity, NumberDeviceClass
from homeassistant.const import CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT, STATE_UNKNOWN

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_DEFAULT_VALUE,
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    CONF_PASSIVE_ENTITY,
    CONF_RESTORE_ON_RECONNECT,
    CONF_SCALING,
    CONF_STEPSIZE_VALUE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_MIN = 0
DEFAULT_MAX = 100000
DEFAULT_STEP = 1.0
DEFAULT_PRECISION = 2

# Device classes supported by NumberEntity
NUMBER_DEVICE_CLASSES = [cls.value for cls in NumberDeviceClass]


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
        vol.Required(CONF_STEPSIZE_VALUE, default=DEFAULT_STEP): vol.All(
            vol.Coerce(float),
            vol.Range(min=0.0, max=1000000.0),
        ),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(NUMBER_DEVICE_CLASSES),
        vol.Required(CONF_RESTORE_ON_RECONNECT): bool,
        vol.Required(CONF_PASSIVE_ENTITY): bool,
        vol.Optional(CONF_DEFAULT_VALUE): str,
    }


class LocaltuyaNumber(LocalTuyaEntity, NumberEntity):
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

        self._max_value = DEFAULT_MAX
        if CONF_MAX_VALUE in self._config:
            self._max_value = self._config.get(CONF_MAX_VALUE)

        self._step_size = DEFAULT_STEP
        if CONF_STEPSIZE_VALUE in self._config:
            self._step_size = self._config.get(CONF_STEPSIZE_VALUE)

        # Override standard default value handling to cast to a float
        default_value = self._config.get(CONF_DEFAULT_VALUE)
        if default_value is not None:
            self._default_value = float(default_value)

    @property
    def native_value(self) -> float:
        """Return sensor state."""
        return self._state

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._min_value

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._max_value

    @property
    def native_step(self) -> float:
        """Return the maximum value."""
        return self._step_size

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    def status_updated(self):
        """Device status was updated."""
        state = self.dps(self._dp_id)
        scale_factor = self._config.get(CONF_SCALING)
        if scale_factor is not None and isinstance(state, (int, float)):
            state = round(state * scale_factor, DEFAULT_PRECISION)
        self._state = state

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        scale_factor = self._config.get(CONF_SCALING)
        if scale_factor is not None and scale_factor != 0:
            # Inverse scaling: convert displayed value back to raw DP value
            value = round(value / scale_factor)
        await self._device.set_dp(value, self._dp_id)

    # Default value is the minimum value
    def entity_default_value(self):
        """Return the minimum value as the default for this entity type."""
        return self._min_value


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaNumber, flow_schema)
