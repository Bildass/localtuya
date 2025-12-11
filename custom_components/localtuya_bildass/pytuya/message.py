# -*- coding: utf-8 -*-
"""
Tuya Message structures.

Defines data structures for Tuya protocol messages.
"""

from dataclasses import dataclass, field
from typing import Optional

from .constants import PREFIX_55AA


@dataclass
class TuyaHeader:
    """Parsed message header.

    Attributes:
        prefix: Message prefix (0x55AA or 0x6699)
        seqno: Sequence number
        cmd: Command type
        length: Payload length (meaning varies by protocol)
        total_length: Total message length including header and footer
    """
    prefix: int
    seqno: int
    cmd: int
    length: int
    total_length: int


@dataclass
class TuyaMessage:
    """Complete Tuya message.

    Attributes:
        seqno: Sequence number
        cmd: Command type
        payload: Decrypted payload bytes
        retcode: Return code (0 = success)
        crc_good: Whether CRC/HMAC/GCM-tag verification passed
        prefix: Message prefix (55AA or 6699)
        nonce: GCM nonce/IV for Protocol 3.5 (12 bytes)
        tag: GCM authentication tag for Protocol 3.5 (16 bytes)
    """
    seqno: int
    cmd: int
    payload: bytes = b""
    retcode: int = 0
    crc_good: bool = True
    prefix: int = PREFIX_55AA
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None


@dataclass
class MessagePayload:
    """Payload to be sent to device.

    Attributes:
        cmd: Command type
        payload: Raw payload bytes (before encryption)
    """
    cmd: int
    payload: bytes = b""


@dataclass
class DeviceStatus:
    """Device status response.

    Attributes:
        dps: Data points dictionary {dp_id: value}
        cid: Sub-device ID (for gateways)
        t: Timestamp
    """
    dps: dict = field(default_factory=dict)
    cid: Optional[str] = None
    t: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceStatus":
        """Create DeviceStatus from parsed JSON response.

        Args:
            data: Parsed JSON dictionary

        Returns:
            DeviceStatus instance
        """
        # Handle nested data structure from v3.4+
        if "dps" not in data and "data" in data and "dps" in data.get("data", {}):
            dps = data["data"]["dps"]
        else:
            dps = data.get("dps", {})

        return cls(
            dps=dps,
            cid=data.get("cid"),
            t=data.get("t")
        )


class TuyaError(Exception):
    """Base exception for Tuya errors."""
    pass


class DecodeError(TuyaError):
    """Error decoding message."""
    pass


class EncryptionError(TuyaError):
    """Error during encryption/decryption."""
    pass


class ConnectionError(TuyaError):
    """Error connecting to device."""
    pass


class SessionKeyError(TuyaError):
    """Error during session key negotiation."""
    pass


class TimeoutError(TuyaError):
    """Operation timed out."""
    pass
