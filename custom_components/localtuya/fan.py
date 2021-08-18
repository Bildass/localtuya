# DPS [1] VALUE [True] --> fan on,off > True, False
# DPS [3] VALUE [6] --> fan speed > 1-6
# DPS [4] VALUE [forward] --> fan direction > forward, reverse
# DPS [102] VALUE [normal] --> preset mode > normal, sleep, nature
# DPS [103] VALUE [off] --> timer > off, 1hour, 2hour, 4hour, 8hour

"""Platform to locally control Tuya-based fan devices."""
import logging
from functools import partial

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

    @property
    def oscillating(self):
        """Return current oscillating status."""
        return self._oscillating

    @property
    def current_direction(self):
        """Return the current direction of the fan."""
        direction = self.service.value(CharacteristicsTypes.ROTATION_DIRECTION)
        return TUYA_DIRECTION_TO_HA[direction]

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

        if percentage is not None
            await self._device.set_dp(
                math.ceil(
                    percentage_to_ranged_value(self._speed_range, percentage)
                    ),
                self._config.get(CONF_FAN_SPEED_CONTROL)
                )

    # async def async_set_speed(self, speed: str) -> None:
    #     """Set the speed of the fan."""
    #     mapping = {
    #         SPEED_LOW: self._config.get(CONF_FAN_SPEED_LOW),
    #         SPEED_MEDIUM: self._config.get(CONF_FAN_SPEED_MEDIUM),
    #         SPEED_HIGH: self._config.get(CONF_FAN_SPEED_HIGH),
    #     }

    #     if speed == SPEED_OFF:
    #         await self._device.set_dp(False, self._dp_id)
    #     else:
    #         await self._device.set_dp(
    #             mapping.get(speed), self._config.get(CONF_FAN_SPEED_CONTROL)
    #         )

    #     self.schedule_update_ha_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        await self._device.set_dp(
            oscillating, self._config.get(CONF_FAN_OSCILLATING_CONTROL)
        )
        self.schedule_update_ha_state()

    async def async_set_direction(self, direction):
        """Set the direction of the fan."""
        await self.async_put_characteristics(
            {CharacteristicsTypes.ROTATION_DIRECTION: DIRECTION_TO_TUYA[direction]}
        )

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
        return self.has_config(CONF_FAN_SPEED_COUNT)
        )

    def status_updated(self):
        """Get state of Tuya fan."""

        self._is_on = self.dps(self._dp_id)

        if self.has_config(CONF_FAN_SPEED_COUNT):
            self._percentage = ranged_value_to_percentage(
                self._speed_range, self.dps_conf(CONF_FAN_SPEED_CONTROL)
                )
            if self._percentage is None:
                self.warning(
                    "%s/%s: Ignoring unknown fan controller state: %s",
                    self.name,
                    self.entity_id,
                    self.dps_conf(CONF_FAN_SPEED_CONTROL),
                )
                self._percentage = None


    #     mappings = {
    #         self._config.get(CONF_FAN_SPEED_LOW): SPEED_LOW,
    #         self._config.get(CONF_FAN_SPEED_MEDIUM): SPEED_MEDIUM,
    #         self._config.get(CONF_FAN_SPEED_HIGH): SPEED_HIGH,
    #     }

    #     if self.has_config(CONF_FAN_SPEED_CONTROL):
    #         self._speed = mappings.get(self.dps_conf(CONF_FAN_SPEED_CONTROL))
    #         if self.speed is None:
    #             self.warning(
    #                 "%s/%s: Ignoring unknown fan controller state: %s",
    #                 self.name,
    #                 self.entity_id,
    #                 self.dps_conf(CONF_FAN_SPEED_CONTROL),
    #             )
    #             self._speed = None

        if self.has_config(CONF_FAN_OSCILLATING_CONTROL):
            self._oscillating = self.dps_conf(CONF_FAN_OSCILLATING_CONTROL)


async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaFan, flow_schema)
