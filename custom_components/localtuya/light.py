"""
Simple platform to control LOCALLY Tuya switch devices.

Sample config yaml

light:
  - platform: localtuya
    host: 192.168.0.1
    local_key: 1234567891234567
    device_id: 12345678912345671234
    name: tuya_01
    friendly_name: This Light
    protocol_version: 3.3
"""
import socket
import logging
from time import time, sleep
from threading import Lock

from homeassistant.const import (
    CONF_ID,
    CONF_FRIENDLY_NAME,
)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.util import color as colorutil

from . import BASE_PLATFORM_SCHEMA, import_from_yaml, prepare_setup_entities
from .pytuya import BulbDevice

_LOGGER = logging.getLogger(__name__)

MIN_MIRED = 153
MAX_MIRED = 370
UPDATE_RETRY_LIMIT = 3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(BASE_PLATFORM_SCHEMA)


def flow_schema(dps):
    """Return schema used in config flow."""
    return {}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup a Tuya switch based on a config entry."""
    device, entities_to_setup = prepare_setup_entities(
        config_entry, "light", BulbDevice
    )
    if not entities_to_setup:
        return

    lights = []
    for device_config in entities_to_setup:
        lights.append(
            TuyaDevice(
                TuyaCache(device),
                device_config[CONF_FRIENDLY_NAME],
                device_config[CONF_ID],
            )
        )

    async_add_entities(lights, True)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    return import_from_yaml(hass, config, "light")


class TuyaCache:
    """Cache wrapper for pytuya.BulbDevice"""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return self._device.id

    def __get_status(self, switchid):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.status()["dps"][switchid]
            except (ConnectionError, socket.timeout):
                pass
        _LOGGER.warning("Failed to get status after %d tries", UPDATE_RETRY_LIMIT)

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ""
        self._cached_status_time = 0
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_status(state, switchid)
            except (ConnectionError, socket.timeout):
                pass
        _LOGGER.warning("Failed to set status after %d tries", UPDATE_RETRY_LIMIT)

    def status(self, switchid):
        """Get state of Tuya switch and cache the results."""
        with self._lock:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 30:
                sleep(0.5)
                self._cached_status = self.__get_status(switchid)
                self._cached_status_time = time()
            return self._cached_status

    def cached_status(self):
        return self._cached_status

    def support_color(self):
        return self._device.support_color()

    def support_color_temp(self):
        return self._device.support_color_temp()

    def brightness(self):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.brightness()
            except (ConnectionError, socket.timeout):
                pass
            except KeyError:
                return "999"
        _LOGGER.warning("Failed to get brightness after %d tries", UPDATE_RETRY_LIMIT)

    def color_temp(self):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.colourtemp()
            except (ConnectionError, socket.timeout):
                pass
            except KeyError:
                return "999"
        _LOGGER.warning("Failed to get color temp after %d tries", UPDATE_RETRY_LIMIT)

    def set_brightness(self, brightness):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_brightness(brightness)
            except (ConnectionError, KeyError, socket.timeout):
                pass
        _LOGGER.warning("Failed to set brightness after %d tries", UPDATE_RETRY_LIMIT)

    def set_color_temp(self, color_temp):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_colourtemp(color_temp)
            except (ConnectionError, KeyError, socket.timeout):
                pass
        _LOGGER.warning("Failed to set color temp after %d tries", UPDATE_RETRY_LIMIT)

    def state(self):
        self._device.state()

    def turn_on(self):
        self._device.turn_on()

    def turn_off(self):
        self._device.turn_off()


class TuyaDevice(LightEntity):
    """Representation of a Tuya switch."""

    def __init__(self, device, friendly_name, bulbid):
        """Initialize the Tuya switch."""
        self._device = device
        self._available = False
        self._name = friendly_name
        self._state = False
        self._brightness = 127
        self._color_temp = 127
        self._bulb_id = bulbid

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def unique_id(self):
        """Return unique device identifier."""
        return f"local_{self._device.unique_id}"

    @property
    def available(self):
        """Return if device is available or not."""
        return self._available

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    def update(self):
        """Get state of Tuya switch."""
        try:
            self._update_state()
        except:
            self._available = False
        else:
            self._available = True

    def _update_state(self):
        status = self._device.status(self._bulb_id)
        self._state = status
        try:
            brightness = int(self._device.brightness())
            if brightness > 254:
                brightness = 255
            if brightness < 25:
                brightness = 25
            self._brightness = brightness
        except TypeError:
            pass
        self._color_temp = self._device.color_temp()

    @property
    def brightness(self):
        """Return the brightness of the light."""
        return self._brightness

    #    @property
    #    def hs_color(self):
    #        """Return the hs_color of the light."""
    #        return (self._device.color_hsv()[0],self._device.color_hsv()[1])

    @property
    def color_temp(self):
        """Return the color_temp of the light."""
        try:
            return int(MAX_MIRED - (((MAX_MIRED - MIN_MIRED) / 255) * self._color_temp))
        except TypeError:
            pass

    @property
    def min_mireds(self):
        """Return color temperature min mireds."""
        return MIN_MIRED

    @property
    def max_mireds(self):
        """Return color temperature max mireds."""
        return MAX_MIRED

    def turn_on(self, **kwargs):
        """Turn on or control the light."""
        _LOGGER.debug("Turning on, state: %s", self._device.cached_status())
        if not self._device.cached_status():
            self._device.set_status(True, self._bulb_id)
        if ATTR_BRIGHTNESS in kwargs:
            converted_brightness = int(kwargs[ATTR_BRIGHTNESS])
            if converted_brightness <= 25:
                converted_brightness = 25
            self._device.set_brightness(converted_brightness)
        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")
        if ATTR_COLOR_TEMP in kwargs:
            color_temp = int(
                255
                - (255 / (MAX_MIRED - MIN_MIRED))
                * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED)
            )
            self._device.set_color_temp(color_temp)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_status(False, self._bulb_id)

    @property
    def supported_features(self):
        """Flag supported features."""
        supports = SUPPORT_BRIGHTNESS
        if self._device.color_temp() != "999":
            supports = supports | SUPPORT_COLOR
        # supports = supports | SUPPORT_COLOR_TEMP
        return supports
