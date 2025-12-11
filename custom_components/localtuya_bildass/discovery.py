"""Discovery module for Tuya devices.

Based on tuya-convert discovery script:
https://github.com/ct-Open-Source/tuya-convert/blob/master/scripts/tuya-discovery.py
"""
import asyncio
import json
import logging

from .pytuya import decrypt_udp, UDP_KEY

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 6.0


class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, callback=None):
        """Initialize a new TuyaDiscovery."""
        self.devices = {}
        self._listeners = []
        self._callback = callback

    async def start(self):
        """Start discovery by listening to broadcasts."""
        loop = asyncio.get_running_loop()

        # Port 6666: unencrypted broadcasts (older devices)
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), reuse_port=True
        )
        # Port 6667: encrypted broadcasts (newer devices)
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
        # Strip Tuya header (20 bytes) and footer (8 bytes)
        data = data[20:-8]

        # Try to decrypt (encrypted broadcasts on port 6667)
        try:
            data = decrypt_udp(data)
            if isinstance(data, bytes):
                data = data.decode("utf-8")
        except Exception:
            # Unencrypted broadcast on port 6666
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
            except Exception:
                _LOGGER.debug("Failed to decode broadcast data")
                return

        # Parse JSON
        try:
            decoded = json.loads(data)
            self.device_found(decoded)
        except json.JSONDecodeError:
            _LOGGER.debug("Failed to parse broadcast JSON: %s", data[:100])

    def device_found(self, device):
        """Handle discovered device."""
        device_id = device.get("gwId")
        if device_id and device_id not in self.devices:
            self.devices[device_id] = device
            _LOGGER.debug("Discovered device: %s", device)

        if self._callback:
            self._callback(device)


async def discover(timeout: float = DEFAULT_TIMEOUT):
    """Discover and return devices on local network.

    Args:
        timeout: How long to listen for broadcasts (default 6 seconds)

    Returns:
        Dictionary of discovered devices {device_id: device_info}
    """
    discovery = TuyaDiscovery()
    try:
        await discovery.start()
        await asyncio.sleep(timeout)
    finally:
        discovery.close()
    return discovery.devices
