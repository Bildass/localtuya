# PyTuya Message Module
# -*- coding: utf-8 -*-
"""
Message structures and payload generation for Tuya protocol.

Provides dataclass-based message types and helper functions for
creating command payloads.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union

from .constants import (
    AP_CONFIG,
    CONTROL,
    CONTROL_NEW,
    DP_QUERY,
    DP_QUERY_NEW,
    HEART_BEAT,
    NO_PROTOCOL_HEADER_CMDS,
    PAYLOAD_DICT,
    PREFIX_55AA_VALUE,
    PREFIX_6699_VALUE,
    PROTOCOL_33_HEADER,
    PROTOCOL_34_HEADER,
    PROTOCOL_35_HEADER,
    SESS_KEY_NEG_FINISH,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_START,
    STATUS,
    UPDATEDPS,
)

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Message Data Classes
# =============================================================================

@dataclass
class TuyaMessage:
    """
    Represents a Tuya protocol message.

    Attributes:
        seqno: Sequence number for message tracking
        cmd: Command type (e.g., CONTROL, STATUS, DP_QUERY)
        retcode: Return code from device (0 = success)
        payload: Message payload (bytes)
        crc: CRC or HMAC value
        crc_good: Whether CRC/HMAC verification passed
        prefix: Message prefix (55AA or 6699)
        iv: Initialization vector for GCM encryption (Protocol 3.5)
        tag: GCM authentication tag (Protocol 3.5)
    """
    seqno: int
    cmd: int
    retcode: int = 0
    payload: bytes = b""
    crc: bytes = b""
    crc_good: bool = True
    prefix: int = PREFIX_55AA_VALUE
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None

    @property
    def is_6699_format(self) -> bool:
        """Check if message uses Protocol 3.5 (6699) format."""
        return self.prefix == PREFIX_6699_VALUE

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for debugging."""
        return {
            "seqno": self.seqno,
            "cmd": hex(self.cmd),
            "retcode": self.retcode,
            "payload_len": len(self.payload),
            "crc_good": self.crc_good,
            "prefix": hex(self.prefix),
            "has_iv": self.iv is not None,
        }


@dataclass
class MessagePayload:
    """
    Simple command + payload pair for sending messages.

    Used as input to the protocol layer before encoding.
    """
    cmd: int
    payload: bytes = b""


@dataclass
class TuyaHeader:
    """
    Parsed message header.

    Attributes:
        prefix: Message prefix (55AA or 6699)
        seqno: Sequence number
        cmd: Command type
        length: Payload length
        total_length: Total message length (including header)
    """
    prefix: int
    seqno: int
    cmd: int
    length: int
    total_length: int = 0

    @property
    def is_6699_format(self) -> bool:
        """Check if header uses Protocol 3.5 (6699) format."""
        return self.prefix == PREFIX_6699_VALUE


# =============================================================================
# Payload Generation
# =============================================================================

class PayloadGenerator:
    """
    Generates command payloads for Tuya devices.

    Handles protocol version differences and device type variations.
    """

    def __init__(
        self,
        dev_id: str,
        protocol_version: float = 3.3,
        dev_type: str = "type_0a",
        local_key: Optional[bytes] = None,
    ):
        """
        Initialize payload generator.

        Args:
            dev_id: Device ID
            protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
            dev_type: Device type ("type_0a" or "type_0d")
            local_key: Local encryption key (for generating MD5 hash)
        """
        self.dev_id = dev_id
        self.version = protocol_version
        self.dev_type = dev_type
        self.local_key = local_key

    def generate(
        self,
        command: int,
        data: Optional[Dict[str, Any]] = None,
        gw_id: Optional[str] = None,
        uid: Optional[str] = None,
        dpid: Optional[list] = None,
    ) -> MessagePayload:
        """
        Generate a command payload.

        Args:
            command: Command type (CONTROL, STATUS, DP_QUERY, etc.)
            data: Data to include in payload (e.g., DPS values)
            gw_id: Gateway ID (defaults to dev_id)
            uid: User ID (defaults to dev_id)
            dpid: List of DP IDs for UPDATEDPS command

        Returns:
            MessagePayload with command and encoded payload
        """
        if gw_id is None:
            gw_id = self.dev_id
        if uid is None:
            uid = self.dev_id

        # Get command template from payload dictionary
        cmd_data = self._get_command_template(command)
        actual_command = cmd_data.get("command_override", command)
        template = cmd_data.get("command", {})

        # Build JSON payload
        json_data = self._build_json_payload(
            template, command, data, gw_id, uid, dpid
        )

        # Encode payload with protocol header if needed
        payload = self._encode_payload(actual_command, json_data)

        return MessagePayload(cmd=actual_command, payload=payload)

    def _get_command_template(self, command: int) -> Dict[str, Any]:
        """Get command template from payload dictionary."""
        # Check protocol-specific overrides first
        version_key = f"v{self.version}"
        if version_key in PAYLOAD_DICT:
            if command in PAYLOAD_DICT[version_key]:
                return PAYLOAD_DICT[version_key][command]

        # Check device type
        if self.dev_type in PAYLOAD_DICT:
            if command in PAYLOAD_DICT[self.dev_type]:
                return PAYLOAD_DICT[self.dev_type][command]

        # Return empty template for commands not in dictionary
        return {}

    def _build_json_payload(
        self,
        template: Dict[str, Any],
        command: int,
        data: Optional[Dict[str, Any]],
        gw_id: str,
        uid: str,
        dpid: Optional[list],
    ) -> Dict[str, Any]:
        """Build JSON payload from template."""
        json_data = template.copy()

        # Fill in template placeholders
        if "gwId" in json_data:
            json_data["gwId"] = gw_id
        if "devId" in json_data:
            json_data["devId"] = self.dev_id
        if "uid" in json_data:
            json_data["uid"] = uid
        if "t" in json_data:
            json_data["t"] = str(int(time.time()))

        # Handle UPDATEDPS command
        if command == UPDATEDPS and dpid is not None:
            json_data["dpId"] = dpid

        # Handle CONTROL command with DPS data
        if data is not None:
            if command in (CONTROL, CONTROL_NEW):
                if self.version >= 3.4:
                    # Protocol 3.4+ uses nested data format
                    json_data["data"] = {"dps": data}
                else:
                    json_data["dps"] = data
            elif command in (DP_QUERY, DP_QUERY_NEW, STATUS):
                # For query commands, data might contain specific DPS to query
                if "dps" in data:
                    json_data["dps"] = data["dps"]

        return json_data

    def _encode_payload(self, command: int, json_data: Dict[str, Any]) -> bytes:
        """Encode payload with appropriate protocol header."""
        json_str = json.dumps(json_data, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")

        # Commands that don't need protocol header
        if command in NO_PROTOCOL_HEADER_CMDS:
            return json_bytes

        # Add protocol version header
        if self.version >= 3.5:
            return PROTOCOL_35_HEADER + json_bytes
        elif self.version >= 3.4:
            return PROTOCOL_34_HEADER + json_bytes
        elif self.version >= 3.3:
            return PROTOCOL_33_HEADER + json_bytes
        else:
            # Protocol 3.1 uses MD5 hash as header
            from hashlib import md5
            if self.local_key:
                md5_hash = md5(json_bytes + self.local_key).digest()
                return md5_hash + json_bytes
            return json_bytes


# =============================================================================
# Helper Functions
# =============================================================================

def create_heartbeat_payload(dev_id: str) -> MessagePayload:
    """Create a heartbeat message payload."""
    json_data = {"gwId": dev_id, "devId": dev_id}
    payload = json.dumps(json_data, separators=(",", ":")).encode("utf-8")
    return MessagePayload(cmd=HEART_BEAT, payload=payload)


def create_status_payload(
    dev_id: str,
    protocol_version: float = 3.3,
) -> MessagePayload:
    """Create a status query message payload."""
    generator = PayloadGenerator(dev_id, protocol_version)
    return generator.generate(STATUS)


def create_dp_query_payload(
    dev_id: str,
    protocol_version: float = 3.3,
) -> MessagePayload:
    """Create a DP query message payload."""
    generator = PayloadGenerator(dev_id, protocol_version)
    return generator.generate(DP_QUERY)


def create_control_payload(
    dev_id: str,
    dps: Dict[str, Any],
    protocol_version: float = 3.3,
) -> MessagePayload:
    """Create a control message payload to set DPS values."""
    generator = PayloadGenerator(dev_id, protocol_version)
    return generator.generate(CONTROL, data=dps)


def create_session_start_payload(local_nonce: bytes) -> MessagePayload:
    """Create session key negotiation start payload."""
    return MessagePayload(cmd=SESS_KEY_NEG_START, payload=local_nonce)


def create_session_finish_payload(hmac_value: bytes) -> MessagePayload:
    """Create session key negotiation finish payload."""
    return MessagePayload(cmd=SESS_KEY_NEG_FINISH, payload=hmac_value)


def parse_status_response(payload: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse status response payload to extract DPS values.

    Args:
        payload: Decrypted payload from device

    Returns:
        Dictionary with 'dps' key containing DPS values, or None if parsing fails
    """
    try:
        # Try to decode as JSON
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8")
        else:
            payload_str = payload

        # Find JSON start
        json_start = payload_str.find("{")
        if json_start == -1:
            return None

        json_str = payload_str[json_start:]
        data = json.loads(json_str)

        # Handle different response formats
        if "dps" in data:
            return data
        elif "data" in data and isinstance(data["data"], dict):
            if "dps" in data["data"]:
                return {"dps": data["data"]["dps"]}
            return {"dps": data["data"]}

        return data

    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        _LOGGER.debug("Failed to parse status response: %s", ex)
        return None
