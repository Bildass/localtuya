"""
Simple platform to control LOCALLY Tuya cover devices.

Sample config yaml

fan:
  - platform: localtuya
    host: 192.168.0.123
    local_key: 1234567891234567
    device_id: 123456789123456789abcd
    name: fan guests
    friendly_name: fan guests
    protocol_version: 3.3
    id: 1

"""
import logging

import voluptuous as vol

from homeassistant.components.fan import (
    FanEntity,
    PLATFORM_SCHEMA,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SUPPORT_SET_SPEED,
    SUPPORT_OSCILLATE,
    SUPPORT_DIRECTION,
)
from homeassistant.const import CONF_ID, CONF_FRIENDLY_NAME, STATE_OFF
import homeassistant.helpers.config_validation as cv

from . import BASE_PLATFORM_SCHEMA, prepare_setup_entities, import_from_yaml
from .pytuya import TuyaDevice

_LOGGER = logging.getLogger(__name__)

PLATFORM = "fan"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya fan based on a config entry."""
    device, entities_to_setup = prepare_setup_entities(
        config_entry, PLATFORM
    )
    if not entities_to_setup:
        return

    fans = []

    for device_config in entities_to_setup:
        fans.append(
            LocaltuyaFan(
                device,
                device_config[CONF_FRIENDLY_NAME],
                device_config[CONF_ID],
            )
        )

    async_add_entities(fans, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya fan."""
    return import_from_yaml(hass, config, PLATFORM)


class LocaltuyaFan(FanEntity):
    """Representation of a Tuya fan."""

    def __init__(self, device, friendly_name, switchid):
        """Initialize the entity."""
        self._device = device
        self._name = friendly_name
        self._available = False
        self._friendly_name = friendly_name
        self._switch_id = switchid
        self._status = self._device.status()
        self._state = False
        self._supported_features = SUPPORT_SET_SPEED | SUPPORT_OSCILLATE
        self._speed = STATE_OFF
        self._oscillating = False

    @property
    def oscillating(self):
        """Return current oscillating status."""
        # if self._speed == STATE_OFF:
        #    return False
        _LOGGER.debug("localtuya fan: oscillating = %s", self._oscillating)
        return self._oscillating

    @property
    def name(self) -> str:
        """Get entity name."""
        return self._name

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._speed

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return [STATE_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]
        # return ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity."""
        _LOGGER.debug("localtuya fan: turn_on speed to: %s", speed)
        # if speed is None:
        #    speed = SPEED_MEDIUM
        # self.set_speed(speed)
        self._device.turn_on()
        if speed is not None:
            self.set_speed(speed)
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        _LOGGER.debug("localtuya fan: turn_off")
        self._device.set_dps(False, '1')
        self._state = False
        self.schedule_update_ha_state()

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        _LOGGER.debug("localtuya fan: set_speed to: %s", speed)
        self._speed = speed
        # self.schedule_update_ha_state()
        if speed == STATE_OFF:
            self._device.set_dps(False, '1')
            self._state = False
        elif speed == SPEED_LOW:
            self._device.set_dps('1', '2')
        elif speed == SPEED_MEDIUM:
            self._device.set_dps('2', '2')
        elif speed == SPEED_HIGH:
            self._device.set_dps('3', '2')
        self.schedule_update_ha_state()

    # def set_direction(self, direction: str) -> None:
    #    """Set the direction of the fan."""
    #    self.direction = direction
    #    self.schedule_update_ha_state()

    def oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self._device.set_value("8", oscillating)
        self.schedule_update_ha_state()

    # @property
    # def current_direction(self) -> str:
    #    """Fan direction."""
    #    return self.direction

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._device.id}_{self._switch_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    def update(self):
        """Get state of Tuya switch."""
        success = False
        for i in range(3):
            if success is False:
                try:
                    status = self._device.status()
                    _LOGGER.debug("localtuya fan: status = %s", status)
                    self._state = status["dps"]["1"]
                    if status["dps"]["1"] == False:
                        self._speed = STATE_OFF
                    elif int(status["dps"]["2"]) == 1:
                        self._speed = SPEED_LOW
                    elif int(status["dps"]["2"]) == 2:
                        self._speed = SPEED_MEDIUM
                    elif int(status["dps"]["2"]) == 3:
                        self._speed = SPEED_HIGH
                    # self._speed = status['dps']['2']
                    self._oscillating = status["dps"]["8"]
                    success = True
                except ConnectionError:
                    if i + 1 == 3:
                        success = False
                        raise ConnectionError("Failed to update status.")
        self._available = success
