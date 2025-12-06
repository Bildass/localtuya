"""Cloud API using Tuya Sharing for QR code authentication.

This module provides an alternative authentication method using QR codes
instead of requiring Tuya Developer Portal credentials. Users simply scan
a QR code with their Smart Life or Tuya Smart app to authenticate.
"""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

try:
    from tuya_sharing import (
        CustomerDevice,
        LoginControl,
        Manager,
        SharingDeviceListener,
        SharingTokenListener,
    )
    TUYA_SHARING_AVAILABLE = True
except ImportError:
    TUYA_SHARING_AVAILABLE = False

from .const import (
    CONF_DEVICE_CID,
    CONF_ENDPOINT,
    CONF_LOCAL_KEY,
    CONF_TERMINAL_ID,
    DOMAIN,
    HUB_CATEGORIES,
    TUYA_CLIENT_ID,
    TUYA_RESPONSE_CODE,
    TUYA_RESPONSE_MSG,
    TUYA_RESPONSE_QR_CODE,
    TUYA_RESPONSE_RESULT,
    TUYA_RESPONSE_SUCCESS,
    TUYA_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)


class TuyaCloudSharing:
    """Tuya Cloud interface using QR code authentication.

    This class provides device discovery and local key retrieval using
    the Tuya Sharing API, which allows authentication via QR code scanning
    in the Smart Life or Tuya Smart mobile app.
    """

    def __init__(self, hass: HomeAssistant):
        """Initialize the cloud sharing interface."""
        if not TUYA_SHARING_AVAILABLE:
            raise ImportError(
                "tuya_sharing package is not installed. "
                "Please install it with: pip install tuya-sharing"
            )

        self._hass = hass
        self._login_control = LoginControl()
        self._authentication = {}
        self._user_code = None
        self._qr_code = None
        self._error_code = None
        self._error_msg = None
        self.device_list = {}

        # Restore cached authentication if available
        if DOMAIN in self._hass.data:
            cached = self._hass.data[DOMAIN].get("auth_cache")
            if cached:
                self._authentication = cached
                _LOGGER.debug("Restored cached authentication")

    async def async_get_qr_code(self, user_code: str) -> str | bool:
        """Get QR code from Tuya server.

        Args:
            user_code: A unique identifier for this login session.
                      Can be any string (e.g., "localtuya_setup").

        Returns:
            QR code string on success, False on failure.
        """
        if not user_code:
            _LOGGER.error("Cannot get QR code without a user code")
            return False

        try:
            response = await self._hass.async_add_executor_job(
                self._login_control.qr_code,
                TUYA_CLIENT_ID,
                TUYA_SCHEMA,
                user_code,
            )

            if response.get(TUYA_RESPONSE_SUCCESS, False):
                self._user_code = user_code
                self._qr_code = response[TUYA_RESPONSE_RESULT][TUYA_RESPONSE_QR_CODE]
                _LOGGER.debug("QR code generated successfully")
                return self._qr_code

            _LOGGER.error("Failed to get QR code: %s", response)
            self._error_code = response.get(TUYA_RESPONSE_CODE)
            self._error_msg = response.get(TUYA_RESPONSE_MSG, "Unknown error")
            return False

        except Exception as ex:
            _LOGGER.exception("Error getting QR code: %s", ex)
            self._error_msg = str(ex)
            return False

    async def async_check_login(self) -> bool:
        """Check if QR code has been scanned and login is complete.

        Returns:
            True if login was successful, False otherwise.
        """
        if not self._user_code or not self._qr_code:
            _LOGGER.warning("Login check attempted without QR code generation")
            return False

        try:
            success, info = await self._hass.async_add_executor_job(
                self._login_control.login_result,
                self._qr_code,
                TUYA_CLIENT_ID,
                self._user_code,
            )

            if success:
                self._authentication = {
                    "user_code": self._user_code,
                    "terminal_id": info[CONF_TERMINAL_ID],
                    "endpoint": info[CONF_ENDPOINT],
                    "token_info": {
                        "t": info["t"],
                        "uid": info["uid"],
                        "expire_time": info["expire_time"],
                        "access_token": info["access_token"],
                        "refresh_token": info["refresh_token"],
                    },
                }

                # Cache authentication in hass.data
                if DOMAIN not in self._hass.data:
                    self._hass.data[DOMAIN] = {}
                self._hass.data[DOMAIN]["auth_cache"] = self._authentication

                _LOGGER.info("QR code login successful")
                return True
            else:
                _LOGGER.debug("QR code not yet scanned or login pending: %s", info)
                self._error_code = info.get(TUYA_RESPONSE_CODE) if isinstance(info, dict) else None
                self._error_msg = info.get(TUYA_RESPONSE_MSG, "Pending scan") if isinstance(info, dict) else "Pending scan"
                return False

        except Exception as ex:
            _LOGGER.exception("Error checking login: %s", ex)
            self._error_msg = str(ex)
            return False

    async def async_get_devices_list(self) -> str:
        """Get all devices associated with the authenticated account.

        Returns:
            "ok" on success, error message on failure.
        """
        if not self.is_authenticated:
            return "Not authenticated. Please scan QR code first."

        try:
            token_listener = TokenListener(self._hass)
            manager = Manager(
                TUYA_CLIENT_ID,
                self._authentication["user_code"],
                self._authentication["terminal_id"],
                self._authentication["endpoint"],
                self._authentication["token_info"],
                token_listener,
            )

            listener = DeviceListener(self._hass, manager)
            manager.add_device_listener(listener)

            # Get all devices from Tuya cloud
            await self._hass.async_add_executor_job(manager.update_device_cache)

            # Build device list
            self.device_list = {}
            for device in manager.device_map.values():
                local_key = ""
                if hasattr(device, "local_key") and device.local_key:
                    local_key = device.local_key

                is_hub = (
                    device.category in HUB_CATEGORIES
                    or not hasattr(device, "local_key")
                    or not device.local_key
                )

                self.device_list[device.id] = {
                    "id": device.id,
                    "name": device.name,
                    "local_key": local_key,
                    "category": device.category,
                    "product_id": device.product_id,
                    "product_name": device.product_name if hasattr(device, "product_name") else "",
                    "ip": device.ip if hasattr(device, "ip") else "",
                    "online": device.online if hasattr(device, "online") else False,
                    "node_id": device.node_id if hasattr(device, "node_id") else "",
                    "uuid": device.uuid if hasattr(device, "uuid") else "",
                    "support_local": device.support_local if hasattr(device, "support_local") else False,
                    "is_hub": is_hub,
                    CONF_DEVICE_CID: None,
                    "version": None,
                }

                _LOGGER.debug(
                    "Found device: %s (%s) - local_key: %s",
                    device.name,
                    device.id,
                    "present" if local_key else "not available"
                )

            _LOGGER.info("Retrieved %d devices from Tuya cloud", len(self.device_list))
            return "ok"

        except Exception as ex:
            _LOGGER.exception("Error getting devices: %s", ex)
            return f"Error: {str(ex)}"

    def logout(self) -> None:
        """Clear authentication and logout."""
        _LOGGER.debug("Logging out from Tuya cloud")
        if DOMAIN in self._hass.data:
            self._hass.data[DOMAIN]["auth_cache"] = None
        self._authentication = {}
        self._user_code = None
        self._qr_code = None
        self.device_list = {}

    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return bool(self._authentication)

    @property
    def qr_code(self) -> str | None:
        """Get the current QR code string."""
        return self._qr_code

    @property
    def last_error(self) -> dict[str, Any] | None:
        """Get the last error code and message."""
        if self._error_code is not None or self._error_msg:
            return {
                TUYA_RESPONSE_MSG: self._error_msg,
                TUYA_RESPONSE_CODE: self._error_code,
            }
        return None


class DeviceListener(SharingDeviceListener):
    """Listener for device updates from Tuya cloud."""

    def __init__(self, hass: HomeAssistant, manager: Manager):
        """Initialize the device listener."""
        self._hass = hass
        self._manager = manager

    def update_device(
        self,
        device: CustomerDevice,
        updated_status_properties: list[str] | None,
    ) -> None:
        """Handle device status updates."""
        _LOGGER.debug(
            "Device %s updated: %s",
            device.id,
            updated_status_properties,
        )

    def add_device(self, device: CustomerDevice) -> None:
        """Handle new device added."""
        _LOGGER.debug("Device added: %s", device.id)

    def remove_device(self, device_id: str) -> None:
        """Handle device removed."""
        _LOGGER.debug("Device removed: %s", device_id)


class TokenListener(SharingTokenListener):
    """Listener for token updates from Tuya cloud."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the token listener."""
        self._hass = hass

    def update_token(self, token_info: dict[str, Any]) -> None:
        """Handle token refresh."""
        _LOGGER.debug("Token refreshed")
        # Update cached token
        if DOMAIN in self._hass.data and "auth_cache" in self._hass.data[DOMAIN]:
            self._hass.data[DOMAIN]["auth_cache"]["token_info"] = token_info


def is_tuya_sharing_available() -> bool:
    """Check if tuya_sharing package is available."""
    return TUYA_SHARING_AVAILABLE
