# PyTuya Protocol Module
# -*- coding: utf-8 -*-
"""
Message packing and unpacking for Tuya protocol.

Supports both 55AA (Protocol 3.1-3.4) and 6699 (Protocol 3.5) formats.
"""

import binascii
import hmac
import logging
import os
import struct
from hashlib import sha256
from typing import Optional, Tuple

from .cipher import AESCipher
from .constants import (
    DecodeError,
    MESSAGE_END_FMT,
    MESSAGE_END_FMT_6699,
    MESSAGE_END_FMT_HMAC,
    MESSAGE_HEADER_FMT,
    MESSAGE_HEADER_FMT_6699,
    MESSAGE_RETCODE_FMT,
    PREFIX_55AA_BIN,
    PREFIX_55AA_VALUE,
    PREFIX_6699_BIN,
    PREFIX_6699_VALUE,
    SUFFIX_55AA_BIN,
    SUFFIX_55AA_VALUE,
    SUFFIX_6699_BIN,
    SUFFIX_6699_VALUE,
)
from .message import MessagePayload, TuyaHeader, TuyaMessage

_LOGGER = logging.getLogger(__name__)

# Header sizes
HEADER_SIZE_55AA = struct.calcsize(MESSAGE_HEADER_FMT)  # 16 bytes
HEADER_SIZE_6699 = struct.calcsize(MESSAGE_HEADER_FMT_6699)  # 18 bytes


# =============================================================================
# Header Parsing
# =============================================================================

def parse_header(data: bytes) -> TuyaHeader:
    """
    Parse message header from raw data.

    Automatically detects 55AA or 6699 format based on prefix.

    Args:
        data: Raw message data (at least 16/18 bytes)

    Returns:
        TuyaHeader with parsed values

    Raises:
        DecodeError: If header format is invalid
    """
    if len(data) < 4:
        raise DecodeError(f"Data too short for header: {len(data)} bytes")

    # Check prefix to determine format
    prefix = struct.unpack(">I", data[:4])[0]

    if prefix == PREFIX_6699_VALUE:
        # Protocol 3.5 format
        if len(data) < HEADER_SIZE_6699:
            raise DecodeError(f"Data too short for 6699 header: {len(data)} < {HEADER_SIZE_6699}")

        prefix, unknown, seqno, cmd, length = struct.unpack(
            MESSAGE_HEADER_FMT_6699, data[:HEADER_SIZE_6699]
        )
        total_length = HEADER_SIZE_6699 + length + 4  # header + payload + suffix
        return TuyaHeader(prefix, seqno, cmd, length, total_length)

    elif prefix == PREFIX_55AA_VALUE:
        # Standard format (Protocol 3.1-3.4)
        if len(data) < HEADER_SIZE_55AA:
            raise DecodeError(f"Data too short for 55AA header: {len(data)} < {HEADER_SIZE_55AA}")

        prefix, seqno, cmd, length = struct.unpack(
            MESSAGE_HEADER_FMT, data[:HEADER_SIZE_55AA]
        )
        total_length = HEADER_SIZE_55AA + length
        return TuyaHeader(prefix, seqno, cmd, length, total_length)

    else:
        raise DecodeError(f"Unknown message prefix: {hex(prefix)}")


# =============================================================================
# Message Packing - 55AA Format (Protocol 3.1-3.4)
# =============================================================================

def pack_message_55aa(
    msg: MessagePayload,
    seqno: int,
    hmac_key: Optional[bytes] = None,
    retcode: Optional[int] = None,
) -> bytes:
    """
    Pack a message in 55AA format (Protocol 3.1-3.4).

    Structure:
        [prefix 4B] [seqno 4B] [cmd 4B] [length 4B]
        [payload NB]
        [crc/hmac 4B/32B] [suffix 4B]

    Args:
        msg: Message payload to pack
        seqno: Sequence number
        hmac_key: HMAC key for Protocol 3.4+ (None for 3.1-3.3)
        retcode: Optional return code to include

    Returns:
        Packed message bytes
    """
    payload = msg.payload

    # Determine CRC format
    if hmac_key:
        end_fmt = MESSAGE_END_FMT_HMAC
    else:
        end_fmt = MESSAGE_END_FMT

    # Calculate total payload length including CRC and suffix
    payload_length = len(payload) + struct.calcsize(end_fmt)

    # Pack header
    header = struct.pack(
        MESSAGE_HEADER_FMT,
        PREFIX_55AA_VALUE,
        seqno,
        msg.cmd,
        payload_length,
    )

    # Create buffer for CRC calculation (header + payload)
    buffer = header + payload

    # Calculate CRC or HMAC
    if hmac_key:
        crc = hmac.new(hmac_key, buffer, sha256).digest()
    else:
        crc = binascii.crc32(buffer) & 0xFFFFFFFF

    # Pack message ending
    buffer += struct.pack(end_fmt, crc, SUFFIX_55AA_VALUE)

    return buffer


# =============================================================================
# Message Packing - 6699 Format (Protocol 3.5)
# =============================================================================

def pack_message_6699(
    msg: MessagePayload,
    seqno: int,
    key: bytes,
    retcode: Optional[int] = None,
) -> bytes:
    """
    Pack a message in 6699 format (Protocol 3.5).

    Structure:
        [prefix 4B] [unknown 2B] [seqno 4B] [cmd 4B] [length 4B]
        [IV 12B] [encrypted payload NB] [GCM tag 16B]
        [suffix 4B]

    Args:
        msg: Message payload to pack
        seqno: Sequence number
        key: Encryption key (session key or device key)
        retcode: Optional return code to include in payload

    Returns:
        Packed message bytes
    """
    # Prepare payload
    raw_payload = msg.payload
    if retcode is not None:
        raw_payload = struct.pack(MESSAGE_RETCODE_FMT, retcode) + raw_payload

    # Generate random IV
    iv = os.urandom(12)

    # Calculate length: IV(12) + encrypted(N) + tag(16)
    # Note: GCM doesn't add padding, so encrypted length = raw length
    length = 12 + len(raw_payload) + 16

    # Pack header
    header = struct.pack(
        MESSAGE_HEADER_FMT_6699,
        PREFIX_6699_VALUE,
        0,  # unknown 2 bytes
        seqno,
        msg.cmd,
        length,
    )

    # AAD is header without prefix (bytes 4-18)
    aad = header[4:]

    # Encrypt with GCM
    cipher = AESCipher(key)
    _, ciphertext, tag = cipher.encrypt_gcm(raw_payload, iv, aad)

    # Combine: header + IV + ciphertext + tag + suffix
    return header + iv + ciphertext + tag + SUFFIX_6699_BIN


# =============================================================================
# Message Unpacking - 55AA Format
# =============================================================================

def unpack_message_55aa(
    data: bytes,
    hmac_key: Optional[bytes] = None,
    header: Optional[TuyaHeader] = None,
) -> TuyaMessage:
    """
    Unpack a message in 55AA format (Protocol 3.1-3.4).

    Args:
        data: Raw message data
        hmac_key: HMAC key for verification (Protocol 3.4+)
        header: Pre-parsed header (optional)

    Returns:
        TuyaMessage with parsed fields

    Raises:
        DecodeError: If message format is invalid
    """
    if header is None:
        header = parse_header(data)

    if header.prefix != PREFIX_55AA_VALUE:
        raise DecodeError(f"Expected 55AA prefix, got {hex(header.prefix)}")

    # Determine CRC format and sizes
    if hmac_key:
        end_fmt = MESSAGE_END_FMT_HMAC
        crc_size = 32
    else:
        end_fmt = MESSAGE_END_FMT
        crc_size = 4

    suffix_size = 4
    end_size = crc_size + suffix_size

    # Extract payload (between header and CRC)
    payload_start = HEADER_SIZE_55AA
    payload_end = HEADER_SIZE_55AA + header.length - end_size
    payload = data[payload_start:payload_end]

    # Extract and verify CRC
    crc_start = payload_end
    crc_data = data[crc_start:crc_start + crc_size]

    # Verify CRC/HMAC
    crc_good = True
    if hmac_key:
        expected_crc = hmac.new(
            hmac_key,
            data[:payload_end],
            sha256
        ).digest()
        crc_good = (crc_data == expected_crc)
    else:
        expected_crc = binascii.crc32(data[:payload_end]) & 0xFFFFFFFF
        actual_crc = struct.unpack(">I", crc_data)[0] if len(crc_data) == 4 else 0
        crc_good = (actual_crc == expected_crc)

    if not crc_good:
        _LOGGER.debug("CRC/HMAC verification failed")

    # Extract retcode if present (first 4 bytes of payload)
    retcode = 0
    if len(payload) >= 4:
        possible_retcode = struct.unpack(">I", payload[:4])[0]
        # Retcode is usually 0 or a small number
        if possible_retcode < 256:
            retcode = possible_retcode
            # Don't strip retcode from payload - let caller decide

    return TuyaMessage(
        seqno=header.seqno,
        cmd=header.cmd,
        retcode=retcode,
        payload=payload,
        crc=crc_data,
        crc_good=crc_good,
        prefix=header.prefix,
        iv=None,
        tag=None,
    )


# =============================================================================
# Message Unpacking - 6699 Format
# =============================================================================

def unpack_message_6699(
    data: bytes,
    key: bytes,
    header: Optional[TuyaHeader] = None,
) -> TuyaMessage:
    """
    Unpack a message in 6699 format (Protocol 3.5).

    Args:
        data: Raw message data
        key: Decryption key (session key or device key)
        header: Pre-parsed header (optional)

    Returns:
        TuyaMessage with parsed and decrypted fields

    Raises:
        DecodeError: If message format is invalid or decryption fails
    """
    if header is None:
        header = parse_header(data)

    if header.prefix != PREFIX_6699_VALUE:
        raise DecodeError(f"Expected 6699 prefix, got {hex(header.prefix)}")

    # Extract encrypted payload (after header, before suffix)
    payload_start = HEADER_SIZE_6699
    payload_end = payload_start + header.length

    # Extract IV, ciphertext, and tag
    iv = data[payload_start:payload_start + 12]
    tag = data[payload_end - 16:payload_end]
    ciphertext = data[payload_start + 12:payload_end - 16]

    # AAD is header without prefix (bytes 4-18)
    aad = data[4:HEADER_SIZE_6699]

    # Decrypt
    cipher = AESCipher(key)
    crc_good = True

    try:
        # Try with AAD first
        payload = cipher.decrypt_gcm(ciphertext, iv, tag, aad)
    except Exception as ex:
        _LOGGER.debug("GCM decrypt with AAD failed: %s, trying without", ex)
        try:
            # Try without AAD
            payload = cipher.decrypt_gcm(ciphertext, iv, tag, None)
        except Exception as ex2:
            _LOGGER.warning("GCM decrypt failed: %s", ex2)
            crc_good = False
            payload = b""

    # Extract retcode if present
    retcode = 0
    if len(payload) >= 4:
        possible_retcode = struct.unpack(">I", payload[:4])[0]
        if possible_retcode < 256:
            retcode = possible_retcode

    return TuyaMessage(
        seqno=header.seqno,
        cmd=header.cmd,
        retcode=retcode,
        payload=payload,
        crc=tag,
        crc_good=crc_good,
        prefix=header.prefix,
        iv=iv,
        tag=tag,
    )


# =============================================================================
# Unified Pack/Unpack Functions
# =============================================================================

def pack_message(
    msg: MessagePayload,
    seqno: int,
    protocol_version: float,
    key: Optional[bytes] = None,
    retcode: Optional[int] = None,
) -> bytes:
    """
    Pack a message in appropriate format based on protocol version.

    Args:
        msg: Message payload to pack
        seqno: Sequence number
        protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
        key: Encryption/HMAC key
        retcode: Optional return code

    Returns:
        Packed message bytes
    """
    if protocol_version >= 3.5:
        if key is None:
            raise ValueError("Key required for Protocol 3.5")
        return pack_message_6699(msg, seqno, key, retcode)
    elif protocol_version >= 3.4:
        return pack_message_55aa(msg, seqno, key, retcode)
    else:
        return pack_message_55aa(msg, seqno, None, retcode)


def unpack_message(
    data: bytes,
    protocol_version: float,
    key: Optional[bytes] = None,
    header: Optional[TuyaHeader] = None,
) -> TuyaMessage:
    """
    Unpack a message based on protocol version and detected format.

    Args:
        data: Raw message data
        protocol_version: Expected protocol version
        key: Decryption/HMAC key
        header: Pre-parsed header (optional)

    Returns:
        TuyaMessage with parsed fields
    """
    if header is None:
        header = parse_header(data)

    if header.prefix == PREFIX_6699_VALUE:
        if key is None:
            raise ValueError("Key required for 6699 format")
        return unpack_message_6699(data, key, header)
    else:
        hmac_key = key if protocol_version >= 3.4 else None
        return unpack_message_55aa(data, hmac_key, header)


# =============================================================================
# Buffer Management
# =============================================================================

def find_message_in_buffer(buffer: bytes) -> Tuple[Optional[bytes], bytes]:
    """
    Find a complete message in a buffer.

    Searches for 55AA or 6699 prefix and extracts complete message.

    Args:
        buffer: Data buffer to search

    Returns:
        Tuple of (message_bytes, remaining_buffer)
        - message_bytes is None if no complete message found
    """
    # Search for either prefix
    pos_55aa = buffer.find(PREFIX_55AA_BIN)
    pos_6699 = buffer.find(PREFIX_6699_BIN)

    # Find first valid prefix
    if pos_55aa == -1 and pos_6699 == -1:
        return None, buffer

    # Determine which prefix comes first
    if pos_55aa == -1:
        start_pos = pos_6699
    elif pos_6699 == -1:
        start_pos = pos_55aa
    else:
        start_pos = min(pos_55aa, pos_6699)

    # Skip any junk before prefix
    if start_pos > 0:
        _LOGGER.debug("Skipping %d bytes before message prefix", start_pos)
        buffer = buffer[start_pos:]

    # Try to parse header
    try:
        header = parse_header(buffer)
    except DecodeError:
        return None, buffer

    # Check if we have complete message
    if len(buffer) < header.total_length:
        return None, buffer

    # Extract message and remaining buffer
    message = buffer[:header.total_length]
    remaining = buffer[header.total_length:]

    return message, remaining


def extract_messages(buffer: bytes) -> Tuple[list, bytes]:
    """
    Extract all complete messages from a buffer.

    Args:
        buffer: Data buffer

    Returns:
        Tuple of (list of message bytes, remaining buffer)
    """
    messages = []

    while True:
        message, buffer = find_message_in_buffer(buffer)
        if message is None:
            break
        messages.append(message)

    return messages, buffer
