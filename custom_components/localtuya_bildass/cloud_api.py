"""Enhanced Tuya Cloud API with aiohttp, caching, and pagination.

BildaSystem fork - ported from domácnost project.
"""
import hashlib
import hmac
import logging
import time
import uuid
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Tuya API regions
TUYA_REGIONS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}


class TuyaCloudApi:
    """Enhanced Tuya Cloud API client with caching and pagination."""

    def __init__(self, hass, region_code: str, client_id: str, secret: str, user_id: str):
        """Initialize the Tuya Cloud API client."""
        self._hass = hass
        self._region = region_code.lower()
        self._base_url = TUYA_REGIONS.get(self._region, TUYA_REGIONS["eu"])
        self._client_id = client_id
        self._secret = secret
        self._user_id = user_id

        # Token caching
        self._access_token: str = ""
        self._token_expiry: int = 0

        # Device caching
        self.device_list: dict[str, dict] = {}
        self._device_cache_time: int = 0
        self._specification_cache: dict[str, dict] = {}

    def _create_signature(
        self,
        timestamp: str,
        nonce: str,
        method: str,
        path: str,
        body: str = "",
        access_token: str = "",
    ) -> str:
        """Create HMAC-SHA256 signature for Tuya API requests."""
        # Content hash (SHA256 of body)
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

        # String to sign
        string_to_sign = "\n".join([
            method,
            content_hash,
            "",  # Headers (empty for simple requests)
            path,
        ])

        # Sign string
        sign_str = self._client_id + access_token + timestamp + nonce + string_to_sign

        # HMAC-SHA256
        signature = hmac.new(
            key=self._secret.encode("utf-8"),
            msg=sign_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest().upper()

        return signature

    async def _async_request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> dict[str, Any]:
        """Make an async request to Tuya API."""
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        body_str = "" if body is None else str(body).replace("'", '"')

        signature = self._create_signature(
            timestamp=timestamp,
            nonce=nonce,
            method=method,
            path=path,
            body=body_str if method in ("POST", "PUT") else "",
            access_token=self._access_token,
        )

        headers = {
            "client_id": self._client_id,
            "sign": signature,
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "nonce": nonce,
            "Content-Type": "application/json",
        }

        if self._access_token:
            headers["access_token"] = self._access_token

        url = f"{self._base_url}{path}"

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=headers) as resp:
                        if not resp.ok:
                            return {"success": False, "msg": f"HTTP {resp.status}"}
                        return await resp.json()
                elif method == "POST":
                    async with session.post(url, headers=headers, json=body) as resp:
                        if not resp.ok:
                            return {"success": False, "msg": f"HTTP {resp.status}"}
                        return await resp.json()
                elif method == "PUT":
                    async with session.put(url, headers=headers, json=body) as resp:
                        if not resp.ok:
                            return {"success": False, "msg": f"HTTP {resp.status}"}
                        return await resp.json()
        except aiohttp.ClientError as e:
            _LOGGER.error("Tuya API request failed: %s", e)
            return {"success": False, "msg": str(e)}

        return {"success": False, "msg": "Unknown method"}

    async def async_get_access_token(self) -> str:
        """Get access token with caching (refresh 60s before expiry)."""
        # Check if we have a valid token
        current_time = int(time.time() * 1000)
        if self._access_token and current_time < self._token_expiry - 60000:
            return "ok"

        path = "/v1.0/token?grant_type=1"
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())

        signature = self._create_signature(
            timestamp=timestamp,
            nonce=nonce,
            method="GET",
            path=path,
            body="",
            access_token="",
        )

        headers = {
            "client_id": self._client_id,
            "sign": signature,
            "sign_method": "HMAC-SHA256",
            "t": timestamp,
            "nonce": nonce,
        }

        url = f"{self._base_url}{path}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if not resp.ok:
                        return f"Request failed, status {resp.status}"
                    data = await resp.json()
        except aiohttp.ClientError as e:
            return f"Request failed: {e}"

        if not data.get("success"):
            return f"Error {data.get('code', 'unknown')}: {data.get('msg', 'unknown')}"

        result = data.get("result", {})
        self._access_token = result.get("access_token", "")
        expire_time = result.get("expire_time", 7200)  # Default 2 hours
        self._token_expiry = int(time.time() * 1000) + (expire_time * 1000)

        _LOGGER.debug("Tuya Cloud token obtained, expires in %s seconds", expire_time)
        return "ok"

    async def async_get_devices_list(self, force_refresh: bool = False) -> str:
        """Get list of all devices with pagination support."""
        # Check cache (5 minute TTL)
        current_time = int(time.time())
        if not force_refresh and self.device_list and (current_time - self._device_cache_time) < 300:
            _LOGGER.debug("Using cached device list (%d devices)", len(self.device_list))
            return "ok"

        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return token_result

        devices: dict[str, dict] = {}
        has_more = True
        last_row_key = ""

        # Paginate through all devices
        while has_more:
            if last_row_key:
                path = f"/v1.0/iot-01/associated-users/devices?last_row_key={last_row_key}&size=100"
            else:
                path = "/v1.0/iot-01/associated-users/devices?size=100"

            data = await self._async_request("GET", path)

            if not data.get("success"):
                # Fallback to old API if new one fails
                _LOGGER.debug("Trying fallback API endpoint")
                path = f"/v1.0/users/{self._user_id}/devices"
                data = await self._async_request("GET", path)
                if not data.get("success"):
                    return f"Error {data.get('code', 'unknown')}: {data.get('msg', 'unknown')}"
                # Old API doesn't paginate
                device_list = data.get("result", [])
                for device in device_list:
                    devices[device["id"]] = device
                break

            result = data.get("result", {})
            device_list = result.get("devices") or result.get("list") or []

            for device in device_list:
                devices[device["id"]] = device

            has_more = result.get("has_more", False)
            if has_more and device_list:
                last_row_key = device_list[-1]["id"]
            else:
                has_more = False

        self.device_list = devices
        self._device_cache_time = current_time
        _LOGGER.info("Loaded %d devices from Tuya Cloud", len(devices))
        return "ok"

    async def async_get_device_specification(self, device_id: str) -> dict | None:
        """Get device specification (DP functions) with caching."""
        # Check cache
        if device_id in self._specification_cache:
            return self._specification_cache[device_id]

        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return None

        path = f"/v1.0/devices/{device_id}/specification"
        data = await self._async_request("GET", path)

        if not data.get("success"):
            _LOGGER.warning("Failed to get specification for %s: %s", device_id, data.get("msg"))
            return None

        result = data.get("result", {})
        self._specification_cache[device_id] = result
        return result

    async def async_get_device_status(self, device_id: str) -> list | None:
        """Get current device status (DP values)."""
        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return None

        path = f"/v1.0/devices/{device_id}/status"
        data = await self._async_request("GET", path)

        if not data.get("success"):
            _LOGGER.warning("Failed to get status for %s: %s", device_id, data.get("msg"))
            return None

        return data.get("result", [])

    async def async_get_device_functions(self, device_id: str) -> dict | None:
        """Get device functions (alternative to specification)."""
        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return None

        path = f"/v1.0/devices/{device_id}/functions"
        data = await self._async_request("GET", path)

        if not data.get("success"):
            _LOGGER.warning("Failed to get functions for %s: %s", device_id, data.get("msg"))
            return None

        return data.get("result", {})

    async def async_sync_local_keys(self, configured_devices: dict) -> dict:
        """Sync local keys for all configured devices.

        Returns dict with device_id -> {old_key, new_key, changed} for each device.
        """
        result = {}

        # Refresh device list from cloud
        refresh_result = await self.async_get_devices_list(force_refresh=True)
        if refresh_result != "ok":
            _LOGGER.error("Failed to refresh device list: %s", refresh_result)
            return result

        for device_id, device_config in configured_devices.items():
            old_key = device_config.get("local_key", "")
            cloud_device = self.device_list.get(device_id)

            if cloud_device:
                new_key = cloud_device.get("local_key", "")
                result[device_id] = {
                    "name": cloud_device.get("name", device_config.get("name", "Unknown")),
                    "old_key": old_key,
                    "new_key": new_key,
                    "changed": old_key != new_key and new_key != "",
                    "found": True,
                }
            else:
                result[device_id] = {
                    "name": device_config.get("name", "Unknown"),
                    "old_key": old_key,
                    "new_key": "",
                    "changed": False,
                    "found": False,
                }

        return result

    def get_device_info(self, device_id: str) -> dict | None:
        """Get device info from cache."""
        return self.device_list.get(device_id)

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.device_list = {}
        self._device_cache_time = 0
        self._specification_cache = {}
        self._access_token = ""
        self._token_expiry = 0
