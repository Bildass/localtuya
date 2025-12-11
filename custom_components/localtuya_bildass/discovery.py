"""Discovery module for Tuya devices.

Entirely based on tuya-convert.py from tuya-convert:

https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py

Updated to support Protocol 3.5 (6699 format) devices.
Refactored to use shared cipher module for better maintainability.
"""
import asyncio
import json
import logging

from .pytuya.cipher import (
    UDP_KEY,
    UDP_KEY_35,
    decrypt_udp_broadcast,
    decrypt_udp_broadcast_35,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 6.0

# Protocol prefixes
PREFIX_55AA = b'\x00\x00\x55\xaa'
PREFIX_6699 = b'\x00\x00\x66\x99'


class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, callback=None):
        """Initialize a new BaseDiscovery."""
        self.devices = {}
        self._listeners = []
        self._callback = callback

    async def start(self):
        """Start discovery by listening to broadcasts."""
        loop = asyncio.get_running_loop()
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), reuse_port=True
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667), reuse_port=True
        )

        self._listeners = await asyncio.gather(listener, encrypted_listener)
        _LOGGER.debug("Listening to broadcasts on UDP port 6666 and 6667")

    def close(self):
        """Stop discovery."""
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        try:
            # Check prefix to determine format
            if data[:4] == PREFIX_6699:
                # Protocol 3.5 format (6699)
                # Header: prefix(4) + unknown(2) + seqno(4) + cmd(4) + length(4) = 18 bytes
                # Suffix: 4 bytes (99 66 00 00)
                _LOGGER.debug(
                    "Received 6699 format broadcast from %s, data len: %d",
                    addr, len(data)
                )
                payload = data[18:-4]
                try:
                    decoded_str = decrypt_udp_broadcast_35(payload)
                    decoded = json.loads(decoded_str)
                    _LOGGER.debug("Decrypted 6699 device: %s", decoded)
                except Exception as ex:
                    _LOGGER.debug("Failed to decrypt 6699 broadcast from %s: %s", addr, ex)
                    return
            else:
                # Standard 55AA format
                # Strip header (20 bytes) and suffix (8 bytes)
                payload = data[20:-8]
                try:
                    decoded_str = decrypt_udp_broadcast(payload)
                except Exception:
                    # Unencrypted broadcast
                    decoded_str = payload.decode()
                decoded = json.loads(decoded_str)

            self.device_found(decoded)
        except Exception as ex:
            _LOGGER.debug(
                "Failed to process broadcast from %s: %s (data: %s)",
                addr, ex, data[:20].hex()
            )

    def device_found(self, device):
        """Discover a new device."""
        if device.get("gwId") not in self.devices:
            self.devices[device.get("gwId")] = device
            _LOGGER.debug("Discovered device: %s", device)

        if self._callback:
            self._callback(device)


async def discover():
    """Discover and return devices on local network."""
    discovery = TuyaDiscovery()
    try:
        await discovery.start()
        await asyncio.sleep(DEFAULT_TIMEOUT)
    finally:
        discovery.close()
    return discovery.devices
