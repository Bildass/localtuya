"""Platform to locally control Tuya-based fan devices."""
import logging
from functools import partial
import math

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.fan import (
    DOMAIN,
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    SUPPORT_DIRECTION,
    SUPPORT_OSCILLATE,
    SUPPORT_SET_SPEED,
    FanEntity,
)

from .common import LocalTuyaEntity, async_setup_entry
from .const import (
    CONF_FAN_OSCILLATING_CONTROL,
    CONF_FAN_SPEED_CONTROL,
    CONF_FAN_DIRECTION,
    CONF_FAN_SPEED_COUNT
)

from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
    int_states_in_range
)

_LOGGER = logging.getLogger(__name__)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {
        vol.Optional(CONF_FAN_SPEED_CONTROL): vol.In(dps),
        vol.Optional(CONF_FAN_OSCILLATING_CONTROL): vol.In(dps),
        vol.Optional(CONF_FAN_DIRECTION): vol.In(dps),
        vol.Optional(CONF_FAN_SPEED_COUNT, default=3): cv.positive_int
    }

# make this configurable later
DIRECTION_TO_TUYA = {
    DIRECTION_REVERSE: "reverse",
    DIRECTION_FORWARD: "forward",
}
TUYA_DIRECTION_TO_HA = {v: k for (k, v) in DIRECTION_TO_TUYA.items()}

class LocaltuyaFan(LocalTuyaEntity, FanEntity):
    """Representation of a Tuya fan."""

    def __init__(
        self,
        device,
        config_entry,
        fanid,
        **kwargs,
    ):
        """Initialize the entity."""
        super().__init__(device, config_entry, fanid, _LOGGER, **kwargs)
        self._is_on = False
        self._oscillating = None
        self._direction = None
        self._percentage = None
        self._speed_range = (
            1, self._config.get(CONF_FAN_SPEED_COUNT),
        )

    @property
    def oscillating(self):
        """Return current oscillating status."""
        return self._oscillating

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        return self._direction


    @property
    def is_on(self):
        """Check if Tuya fan is on."""
        return self._is_on

    @property
    def percentage(self):
        """Return the current percentage."""
        return self._percentage

    # @property
    # def speed(self) -> str:
    #     """Return the current speed."""
    #     return self._speed

    # @property
    # def speed_list(self) -> list:
    #     """Get the list of available speeds."""
    #     return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        await self._device.set_dp(True, self._dp_id)
        if speed is not None:
            await self.async_set_speed(speed)
        else:
            self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        await self._device.set_dp(False, self._dp_id)
        self.schedule_update_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the speed of the fan."""
        if percentage == 0:
            return await self.async_turn_off()

        if not self.is_on:
            await self.async_turn_on()

        if percentage is not None:
            await self._device.set_dp(
                str(math.ceil(
                    percentage_to_ranged_value(self._speed_range, percentage)
                    )),
                self._config.get(CONF_FAN_SPEED_CONTROL)
                )


    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        await self._device.set_dp(
            oscillating, self._config.get(CONF_FAN_OSCILLATING_CONTROL)
        )
        self.schedule_update_ha_state()

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        await self._device.set_dp(
            DIRECTION_TO_TUYA[direction], self._config.get(CONF_FAN_DIRECTION)
        )
        self.schedule_update_ha_state()        

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        features = 0

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            features |= SUPPORT_OSCILLATE

        if self.has_config(CONF_FAN_SPEED_CONTROL):
            features |= SUPPORT_SET_SPEED

        if self.has_config(CONF_FAN_DIRECTION):
            features |= SUPPORT_DIRECTION

        return features 
    
    @property
    def speed_count(self) -> int:
        """Speed count for the fan."""
        return int_states_in_range(self._speed_range)


    def status_updated(self):
        """Get state of Tuya fan."""

        self._is_on = self.dps(self._dp_id)

        if self.has_config(CONF_FAN_SPEED_COUNT):
            value = int(self.dps_conf(CONF_FAN_SPEED_CONTROL))
            if value is not None:
                self._percentage = ranged_value_to_percentage(self._speed_range, value)
            else:
                self.warning(
                    "%s/%s: Ignoring unknown fan controller state: %s",
                    self.name,
                    self.entity_id,
                    value,
                )

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            self._oscillating = self.dps_conf(CONF_FAN_OSCILLATING_CONTROL)

        if self.has_config(CONF_FAN_DIRECTION):
            value = self.dps_conf(CONF_FAN_DIRECTION)
            if value is not None:
                self._direction = TUYA_DIRECTION_TO_HA[value]   


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaFan, flow_schema)
