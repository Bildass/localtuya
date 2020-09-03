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
import voluptuous as vol
from homeassistant.const import (CONF_HOST, CONF_ID, CONF_SWITCHES, CONF_FRIENDLY_NAME, CONF_ICON, CONF_NAME)
import homeassistant.helpers.config_validation as cv
from time import time, sleep
from threading import Lock
import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
    PLATFORM_SCHEMA
)
from homeassistant.util import color as colorutil
import socket

REQUIREMENTS = ['pytuya==7.0.8']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'
CONF_PROTOCOL_VERSION = 'protocol_version'
# IMPORTANT, id is used as key for state and turning on and off, 1 was fine switched apparently but my bulbs need 20, other feature attributes count up from this, e.g. 21 mode, 22 brightnes etc, see my pytuya modification.
DEFAULT_ID = '1'
DEFAULT_PROTOCOL_VERSION = 3.3
MIN_MIRED = 153
MAX_MIRED = 370
UPDATE_RETRY_LIMIT = 3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(float),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
})
log = logging.getLogger(__name__)
log.setLevel(level=logging.DEBUG)  # Debug hack!


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    from . import pytuya

    lights = []
    pytuyadevice = pytuya.BulbDevice(config.get(CONF_DEVICE_ID), config.get(CONF_HOST), config.get(CONF_LOCAL_KEY))
    pytuyadevice.set_version(float(config.get(CONF_PROTOCOL_VERSION)))

    bulb_device = TuyaCache(pytuyadevice)
    lights.append(
            TuyaDevice(
                bulb_device,
                config.get(CONF_NAME),
                config.get(CONF_FRIENDLY_NAME),
                config.get(CONF_ICON), 
                config.get(CONF_ID)
            )
    )

    add_devices(lights)

class TuyaCache:
    """Cache wrapper for pytuya.BulbDevice"""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ''
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
                status = self._device.status()['dps'][switchid]
                return status
            except ConnectionError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to get status after {} tries".format(UPDATE_RETRY_LIMIT))

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_status(state, switchid)
            except ConnectionError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to set status after {} tries".format(UPDATE_RETRY_LIMIT))

    def status(self, switchid):
        """Get state of Tuya switch and cache the results."""
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 30:
                sleep(0.5)
                self._cached_status = self.__get_status(switchid)
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()

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
            except ConnectionError:
                pass
            except KeyError:
                return "999"
            except socket.timeout:
                pass
        log.warn(
            "Failed to get brightness after {} tries".format(UPDATE_RETRY_LIMIT))

    def color_temp(self):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.colourtemp()
            except ConnectionError:
                pass
            except KeyError:
                return "999"
            except socket.timeout:
                pass
        log.warn(
            "Failed to get color temp after {} tries".format(UPDATE_RETRY_LIMIT))

    def set_brightness(self, brightness):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_brightness(brightness)
            except ConnectionError:
                pass
            except KeyError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to set brightness after {} tries".format(UPDATE_RETRY_LIMIT))

    def set_color_temp(self, color_temp):
        for _ in range(UPDATE_RETRY_LIMIT):
            try:
                return self._device.set_colourtemp(color_temp)
            except ConnectionError:
                pass
            except KeyError:
                pass
            except socket.timeout:
                pass
        log.warn(
            "Failed to set color temp after {} tries".format(UPDATE_RETRY_LIMIT))

    def state(self):
        self._device.state();
 
    def turn_on(self):
        self._device.turn_on();

    def turn_off(self):
        self._device.turn_off();

class TuyaDevice(LightEntity):
    """Representation of a Tuya switch."""

    def __init__(self, device, name, friendly_name, icon, bulbid):
        """Initialize the Tuya switch."""
        self._device = device
        self._available = False
        self._name = friendly_name
        self._state = False
        self._brightness = 127
        self._color_temp = 127
        self._icon = icon
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

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

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
        log.debug("Turning on, state: " + str(self._device.cached_status()))
        if  not self._device.cached_status():
            self._device.set_status(True, self._bulb_id)
        if ATTR_BRIGHTNESS in kwargs:
            converted_brightness = int(kwargs[ATTR_BRIGHTNESS])
            if converted_brightness <= 25:
                converted_brightness = 25
            self._device.set_brightness(converted_brightness)
        if ATTR_HS_COLOR in kwargs:
            raise ValueError(" TODO implement RGB from HS")
        if ATTR_COLOR_TEMP in kwargs:
            color_temp = int(255 - (255 / (MAX_MIRED - MIN_MIRED)) * (int(kwargs[ATTR_COLOR_TEMP]) - MIN_MIRED))
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
        #supports = supports | SUPPORT_COLOR_TEMP
        return supports
