"""
Simple platform to control LOCALLY Tuya cover devices.

Sample config yaml

cover:
  - platform: localtuya
    host: 192.168.0.123
    local_key: 1234567891234567
    device_id: 123456789123456789abcd
    name: Cover guests
    protocol_version: 3.3
    id: 1
"""

import logging
import requests

import voluptuous as vol

from homeassistant.components.cover import (
    CoverDevice,
    PLATFORM_SCHEMA,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_STOP,
)

"""from . import DATA_TUYA, TuyaDevice"""
"""from homeassistant.components.cover import CoverDevice, PLATFORM_SCHEMA"""
from homeassistant.const import (CONF_HOST, CONF_ID, CONF_FRIENDLY_NAME, CONF_ICON, CONF_NAME)
import homeassistant.helpers.config_validation as cv
from time import time, sleep
from threading import Lock

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'localtuyacover'

REQUIREMENTS = ['pytuya==7.0.7']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'
CONF_PROTOCOL_VERSION = 'protocol_version'

DEFAULT_ID = '1'
DEFAULT_PROTOCOL_VERSION = 3.3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION): vol.Coerce(float),
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
})




def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up Tuya cover devices."""
    from . import pytuya

    covers = []
    localtuyadevice = pytuya.CoverDevice(config.get(CONF_DEVICE_ID), config.get(CONF_HOST), config.get(CONF_LOCAL_KEY))
    localtuyadevice.set_version(float(config.get(CONF_PROTOCOL_VERSION)))

    cover_device = TuyaCoverCache(localtuyadevice)
    covers.append(
            TuyaDevice(
                cover_device,
                config.get(CONF_NAME),
                config.get(CONF_ICON),
                config.get(CONF_ID),
            )
	)
    print('Setup localtuya cover [{}] with device ID [{}] '.format(config.get(CONF_NAME), config.get(CONF_ID)))

    add_entities(covers)


class TuyaCoverCache:
    """Cache wrapper for pytuya.CoverDevice"""

    def __init__(self, device):
        """Initialize the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        self._device = device
        self._lock = Lock()

    def __get_status(self):
        for i in range(20):
            try:
                status = self._device.status()
                return status
            except ConnectionError:
                if i+1 == 3:
                    raise ConnectionError("Failed to update status.")

    def set_status(self, state, switchid):
        """Change the Tuya switch status and clear the cache."""
        self._cached_status = ''
        self._cached_status_time = 0
        for i in range(20):
            try:
                return self._device.set_status(state, switchid)
            except ConnectionError:
                if i+1 == 5:
                    raise ConnectionError("Failed to set status.")

    def status(self):
        """Get state of Tuya switch and cache the results."""
        self._lock.acquire()
        try:
            now = time()
            if not self._cached_status or now - self._cached_status_time > 30:
                sleep(0.5)
                self._cached_status = self.__get_status()
                self._cached_status_time = time()
            return self._cached_status
        finally:
            self._lock.release()

class TuyaDevice(CoverDevice):
    """Tuya cover devices."""

    def __init__(self, device, name, icon, switchid):
        self._device = device
        self._name = name
        self._icon = icon
        self._switch_id = switchid
        #self.entity_id = ENTITY_ID_FORMAT.format(_device.object_id())
        self._status = self._device.status()
        self._state = self._status['dps'][self._switch_id]
        print('Initialized tuya cover [{}] with switch status [{}] and state [{}]'.format(self._name, self._status, self._state))

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP
        return supported_features

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def is_opening(self):
        #self.update()
        state = self._state
        #print('is_opening() : state [{}]'.format(state))
        if state == 'on':
            return True
        return False

    @property
    def is_closing(self):
        #self.update()
        state = self._state
        #print('is_closing() : state [{}]'.format(state))
        if state == 'off':
            return True
        return False

    @property
    def is_closed(self):
        """Return if the cover is closed or not."""
        #self.update()
        state = self._state
        #print('is_closed() : state [{}]'.format(state))
        if state == 'off':
            return False
        if state == 'on':
            return True
        return None

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._device.set_status('on', self._switch_id)
#        self._state = 'on'
#        self._device._device.open_cover()

    def close_cover(self, **kwargs):
        """Close cover."""
        self._device.set_status('off', self._switch_id)
#        self._state = 'off'
#        self._device._device.close_cover()

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self._device.set_status('stop', self._switch_id)
#        self._state = 'stop'
#        self._device._device.stop_cover()

    def update(self):
        """Get state of Tuya switch."""
        self._status = self._device.status()
        self._state = self._status['dps'][self._switch_id]
        #print('update() : state [{}]'.format(self._state))
