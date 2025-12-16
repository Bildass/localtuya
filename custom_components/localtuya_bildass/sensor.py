"""Platform to present any Tuya DP as a sensor."""
import logging
from functools import partial

import voluptuous as vol
from homeassistant.components.sensor import DEVICE_CLASSES, DOMAIN, SensorDeviceClass
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import CONF_SCALING, CONF_ENUM_OPTIONS, CONF_ENUM_OPTIONS_FRIENDLY

_LOGGER = logging.getLogger(__name__)

DEFAULT_PRECISION = 2


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): str,
        vol.Optional(CONF_DEVICE_CLASS): vol.In(DEVICE_CLASSES),
        vol.Optional(CONF_SCALING): vol.All(
            vol.Coerce(float), vol.Range(min=-1000000.0, max=1000000.0)
        ),
        # For device_class: enum - specify raw values and friendly names
        vol.Optional(CONF_ENUM_OPTIONS): str,  # e.g. "0;1;2" or "heating;cooling;off"
        vol.Optional(CONF_ENUM_OPTIONS_FRIENDLY): str,  # e.g. "Heating;Cooling;Off"
    }


class LocaltuyaSensor(LocalTuyaEntity):
    """Representation of a Tuya sensor."""

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

        # Parse enum options if configured (for device_class: enum)
        self._enum_options = []  # Raw values from device
        self._enum_options_friendly = []  # Friendly display names

        enum_options_str = self._config.get(CONF_ENUM_OPTIONS)
        if enum_options_str:
            self._enum_options = [opt.strip() for opt in enum_options_str.split(";")]

            # Parse friendly names
            enum_friendly_str = self._config.get(CONF_ENUM_OPTIONS_FRIENDLY)
            if enum_friendly_str:
                self._enum_options_friendly = [
                    opt.strip() for opt in enum_friendly_str.split(";")
                ]
            else:
                # Default to raw values if no friendly names provided
                self._enum_options_friendly = self._enum_options.copy()

            # Pad friendly names if shorter than raw options
            while len(self._enum_options_friendly) < len(self._enum_options):
                self._enum_options_friendly.append(
                    self._enum_options[len(self._enum_options_friendly)]
                )

            _LOGGER.debug(
                "Sensor %s enum options: %s -> %s",
                sensorid,
                self._enum_options,
                self._enum_options_friendly,
            )

    @property
    def state(self):
        """Return sensor state."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this device."""
        return self._config.get(CONF_DEVICE_CLASS)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._config.get(CONF_UNIT_OF_MEASUREMENT)

    @property
    def options(self):
        """Return the list of available options for enum sensors."""
        if self._config.get(CONF_DEVICE_CLASS) == SensorDeviceClass.ENUM:
            return self._enum_options_friendly if self._enum_options_friendly else None
        return None

    def status_updated(self):
        """Device status was updated."""
        state = self.dps(self._dp_id)
        scale_factor = self._config.get(CONF_SCALING)

        # Handle enum device_class - translate raw value to friendly name
        if (
            self._config.get(CONF_DEVICE_CLASS) == SensorDeviceClass.ENUM
            and self._enum_options
        ):
            state_str = str(state)
            if state_str in self._enum_options:
                idx = self._enum_options.index(state_str)
                state = self._enum_options_friendly[idx]
            else:
                _LOGGER.debug(
                    "Sensor %s received unknown enum value: %s (known: %s)",
                    self._dp_id,
                    state,
                    self._enum_options,
                )
                # Keep raw value if not in known options
        elif scale_factor is not None and isinstance(state, (int, float)):
            state = round(state * scale_factor, DEFAULT_PRECISION)

        self._state = state

    # No need to restore state for a sensor
    async def restore_state_when_connected(self):
        """Do nothing for a sensor."""
        return


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSensor, flow_schema)
