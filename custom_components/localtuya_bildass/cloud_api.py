"""Enhanced Tuya Cloud API with aiohttp, caching, and pagination.

BildaSystem fork - ported from domácnost project.
"""
import asyncio
import hashlib
import hmac
import logging
import time
import uuid
from typing import Any

import aiohttp

from . import pytuya

_LOGGER = logging.getLogger(__name__)

# Tuya API regions - all available data centers
# Reference: https://developer.tuya.com/en/docs/iot/api-request?id=Ka4a8uuo1j4t4
TUYA_REGIONS = {
    "eu": "https://openapi.tuyaeu.com",           # Central Europe
    "eu_west": "https://openapi-weaz.tuyaeu.com", # Western Europe
    "us": "https://openapi.tuyaus.com",           # Western America
    "us_east": "https://openapi-ueaz.tuyaus.com", # Eastern America
    "cn": "https://openapi.tuyacn.com",           # China
    "in": "https://openapi.tuyain.com",           # India
    "sg": "https://openapi-sg.iotbing.com",       # Singapore (launched June 2025)
}

# Human-readable region names for UI
TUYA_REGION_NAMES = {
    "eu": "EU - Central Europe",
    "eu_west": "EU West - Western Europe",
    "us": "US - Western America",
    "us_east": "US East - Eastern America",
    "cn": "CN - China",
    "in": "IN - India",
    "sg": "SG - Singapore",
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

    async def _test_device_key(
        self,
        host: str,
        device_id: str,
        local_key: str,
        protocol_version: float,
        timeout: float = 5.0
    ) -> bool:
        """Test if a local_key works for connecting to device.

        Args:
            host: Device IP address
            device_id: Device ID
            local_key: Local key to test
            protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
            timeout: Connection timeout

        Returns:
            True if connection successful, False otherwise
        """
        if not host or not local_key:
            return False

        try:
            protocol = await pytuya.connect(
                address=host,
                device_id=device_id,
                local_key=local_key,
                protocol_version=protocol_version,
                timeout=timeout
            )
            # Connection successful, close it
            protocol.close()
            await asyncio.sleep(0.1)  # Give time to close cleanly
            return True
        except Exception as e:
            _LOGGER.debug("Key test failed for %s: %s", device_id, e)
            return False

    async def async_sync_local_keys(self, configured_devices: dict, verify_keys: bool = True) -> dict:
        """Sync local keys for all configured devices with optional verification.

        IMPORTANT: If verify_keys is True (default), this function will:
        1. Test if the current (old) key works
        2. Only suggest changing to new key if old key doesn't work AND new key works
        3. This prevents overwriting working keys with stale cloud data

        Returns dict with device_id -> {
            name, old_key, new_key, changed, found,
            old_key_works, new_key_works, recommendation
        }
        """
        result = {}

        # Refresh device list from cloud
        refresh_result = await self.async_get_devices_list(force_refresh=True)
        if refresh_result != "ok":
            _LOGGER.error("Failed to refresh device list: %s", refresh_result)
            return result

        for device_id, device_config in configured_devices.items():
            old_key = device_config.get("local_key", "")
            host = device_config.get("host", "")
            protocol_version = device_config.get("protocol_version", 3.3)
            cloud_device = self.device_list.get(device_id)

            device_name = device_config.get("name", "Unknown")
            if cloud_device:
                device_name = cloud_device.get("name", device_name)
                new_key = cloud_device.get("local_key", "")
            else:
                new_key = ""

            # Default result
            device_result = {
                "name": device_name,
                "old_key": old_key,
                "new_key": new_key,
                "changed": False,
                "found": cloud_device is not None,
                "old_key_works": None,
                "new_key_works": None,
                "recommendation": "keep",  # keep, update, or manual
            }

            # If keys are the same, no change needed
            if old_key == new_key or not new_key:
                device_result["recommendation"] = "keep"
                result[device_id] = device_result
                continue

            # Keys differ - verify if requested
            if verify_keys and host:
                _LOGGER.info("Testing keys for %s (%s)...", device_name, device_id[:8])

                # Test old key first
                old_works = await self._test_device_key(
                    host, device_id, old_key, protocol_version
                )
                device_result["old_key_works"] = old_works

                if old_works:
                    # Old key works - DON'T change it!
                    _LOGGER.info(
                        "Device %s: current key WORKS, keeping it (cloud has different key)",
                        device_name
                    )
                    device_result["recommendation"] = "keep"
                    device_result["changed"] = False
                else:
                    # Old key doesn't work - test new key
                    new_works = await self._test_device_key(
                        host, device_id, new_key, protocol_version
                    )
                    device_result["new_key_works"] = new_works

                    if new_works:
                        # New key works, old doesn't - recommend update
                        _LOGGER.info(
                            "Device %s: current key BROKEN, cloud key WORKS - recommending update",
                            device_name
                        )
                        device_result["recommendation"] = "update"
                        device_result["changed"] = True
                    else:
                        # Neither key works - manual intervention needed
                        _LOGGER.warning(
                            "Device %s: BOTH keys broken - manual re-pairing needed",
                            device_name
                        )
                        device_result["recommendation"] = "manual"
                        device_result["changed"] = False
            else:
                # No verification - use old behavior (mark as changed if different)
                device_result["changed"] = old_key != new_key and new_key != ""
                if device_result["changed"]:
                    device_result["recommendation"] = "update"

            result[device_id] = device_result

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

    async def async_get_device_mac(self, device_id: str) -> str | None:
        """Get MAC address for device from Tuya factory-infos endpoint."""
        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return None

        path = f"/v1.0/devices/factory-infos?device_ids={device_id}"
        data = await self._async_request("GET", path)

        if not data.get("success"):
            _LOGGER.warning("Failed to get factory info for %s: %s", device_id, data.get("msg"))
            return None

        result = data.get("result", [])
        if result and len(result) > 0:
            mac = result[0].get("mac")
            if mac:
                _LOGGER.debug("Got MAC %s for device %s", mac, device_id)
                return mac.lower()
        return None

    async def async_get_devices_mac_batch(self, device_ids: list[str]) -> dict[str, str]:
        """Get MAC addresses for multiple devices in one request."""
        # Ensure we have a valid token
        token_result = await self.async_get_access_token()
        if token_result != "ok":
            return {}

        # API supports comma-separated device IDs
        ids_str = ",".join(device_ids)
        path = f"/v1.0/devices/factory-infos?device_ids={ids_str}"
        data = await self._async_request("GET", path)

        result_map = {}
        if data.get("success"):
            for item in data.get("result", []):
                dev_id = item.get("id")
                mac = item.get("mac")
                if dev_id and mac:
                    result_map[dev_id] = mac.lower()
                    _LOGGER.debug("Got MAC %s for device %s", mac, dev_id)

        return result_map

    @staticmethod
    def find_ip_by_mac(mac_address: str) -> str | None:
        """Find local IP address by MAC address using ARP table."""
        if not mac_address:
            return None

        # Normalize MAC to lowercase with colons
        mac_clean = mac_address.lower().replace("-", ":")

        try:
            with open("/proc/net/arp", "r") as f:
                for line in f:
                    # Skip header
                    if line.startswith("IP address"):
                        continue
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        arp_mac = parts[3].lower()
                        if arp_mac == mac_clean:
                            _LOGGER.info("Found IP %s for MAC %s in ARP table", ip, mac_address)
                            return ip
        except Exception as e:
            _LOGGER.warning("Failed to read ARP table: %s", e)

        _LOGGER.debug("MAC %s not found in ARP table", mac_address)
        return None

    async def async_get_device_local_ip(self, device_id: str) -> str | None:
        """Get local IP for device by looking up MAC in ARP table."""
        mac = await self.async_get_device_mac(device_id)
        if mac:
            return self.find_ip_by_mac(mac)
        return None
