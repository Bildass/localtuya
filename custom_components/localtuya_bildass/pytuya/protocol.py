# -*- coding: utf-8 -*-
"""
Tuya Protocol message packing and unpacking.

Handles both 55AA (Protocol 3.1-3.4) and 6699 (Protocol 3.5) formats.

Message formats:
===============

55AA Format (Protocol 3.1-3.4):
    000055aa [SEQNO:4] [CMD:4] [LENGTH:4] [RETCODE:4]? [PAYLOAD] [CRC/HMAC] 0000aa55
    - LENGTH: includes retcode (if present), payload, crc/hmac, and suffix
    - CRC: 4 bytes CRC32 (v3.1-3.3) or 32 bytes HMAC-SHA256 (v3.4)
    - RETCODE: only in device responses

6699 Format (Protocol 3.5):
    00006699 [VER:1] [RES:1] [SEQNO:4] [CMD:4] [LENGTH:4] [NONCE:12] [PAYLOAD] [TAG:16] 00009966
    - LENGTH: includes nonce, payload, and tag (excludes suffix)
    - NONCE: 12-byte IV for AES-GCM
    - TAG: 16-byte GCM authentication tag
    - AAD (authenticated additional data): bytes 4-18 of header (ver, res, seqno, cmd, length)
"""

import binascii
import hmac
import os
import struct
import logging
from hashlib import sha256
from typing import Optional, Tuple

from .cipher import AESCipher
from .constants import (
    PREFIX_55AA, PREFIX_55AA_BIN, SUFFIX_55AA, SUFFIX_55AA_BIN,
    PREFIX_6699, PREFIX_6699_BIN, SUFFIX_6699, SUFFIX_6699_BIN,
    HEADER_FMT_55AA, HEADER_SIZE_55AA,
    HEADER_FMT_6699, HEADER_SIZE_6699,
    RETCODE_FMT, RETCODE_SIZE,
    FOOTER_FMT_55AA_CRC, FOOTER_SIZE_55AA_CRC,
    FOOTER_FMT_55AA_HMAC, FOOTER_SIZE_55AA_HMAC,
    FOOTER_FMT_6699, FOOTER_SIZE_6699,
    GCM_NONCE_SIZE, GCM_TAG_SIZE,
    MAX_PAYLOAD_SIZE, SESSION_KEY_CMDS,
)
from .message import TuyaHeader, TuyaMessage, DecodeError

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# HEADER PARSING
# =============================================================================

def parse_header(data: bytes) -> TuyaHeader:
    """Parse message header to determine format and length.

    Args:
        data: Raw message bytes (at least header size needed)

    Returns:
        TuyaHeader with parsed values

    Raises:
        DecodeError: If header is invalid or not enough data
    """
    if len(data) < 4:
        raise DecodeError("Not enough data to parse header prefix")

    # Determine format by prefix
    if data[:4] == PREFIX_6699_BIN:
        return _parse_header_6699(data)
    elif data[:4] == PREFIX_55AA_BIN:
        return _parse_header_55aa(data)
    else:
        prefix_hex = binascii.hexlify(data[:4]).decode()
        raise DecodeError(f"Unknown header prefix: {prefix_hex}")


def _parse_header_55aa(data: bytes) -> TuyaHeader:
    """Parse 55AA format header."""
    if len(data) < HEADER_SIZE_55AA:
        raise DecodeError(f"Not enough data for 55AA header: need {HEADER_SIZE_55AA}, got {len(data)}")

    prefix, seqno, cmd, length = struct.unpack(HEADER_FMT_55AA, data[:HEADER_SIZE_55AA])

    # Sanity check
    if length > MAX_PAYLOAD_SIZE:
        raise DecodeError(f"Header claims packet size {length} > {MAX_PAYLOAD_SIZE} bytes")

    # Total length = header + payload (which includes suffix)
    total_length = HEADER_SIZE_55AA + length

    return TuyaHeader(
        prefix=prefix,
        seqno=seqno,
        cmd=cmd,
        length=length,
        total_length=total_length
    )


def _parse_header_6699(data: bytes) -> TuyaHeader:
    """Parse 6699 format header."""
    if len(data) < HEADER_SIZE_6699:
        raise DecodeError(f"Not enough data for 6699 header: need {HEADER_SIZE_6699}, got {len(data)}")

    prefix, version, reserved, seqno, cmd, length = struct.unpack(
        HEADER_FMT_6699, data[:HEADER_SIZE_6699]
    )

    # Sanity check
    if length > MAX_PAYLOAD_SIZE:
        raise DecodeError(f"Header claims packet size {length} > {MAX_PAYLOAD_SIZE} bytes")

    # Total length = header + length (nonce+payload+tag) + suffix (4 bytes)
    total_length = HEADER_SIZE_6699 + length + 4

    return TuyaHeader(
        prefix=prefix,
        seqno=seqno,
        cmd=cmd,
        length=length,
        total_length=total_length
    )


# =============================================================================
# MESSAGE PACKING
# =============================================================================

def pack_message(
    seqno: int,
    cmd: int,
    payload: bytes,
    key: bytes,
    protocol_version: float,
    encrypt: bool = True
) -> bytes:
    """Pack a message for sending to device.

    Args:
        seqno: Sequence number
        cmd: Command type
        payload: Payload bytes (unencrypted)
        key: Encryption key (device key or session key)
        protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
        encrypt: Whether to encrypt payload (default True)

    Returns:
        Packed message bytes ready to send
    """
    if protocol_version >= 3.5:
        return _pack_message_6699(seqno, cmd, payload, key, encrypt)
    else:
        use_hmac = protocol_version >= 3.4
        return _pack_message_55aa(seqno, cmd, payload, key, encrypt, use_hmac)


def _pack_message_55aa(
    seqno: int,
    cmd: int,
    payload: bytes,
    key: bytes,
    encrypt: bool,
    use_hmac: bool
) -> bytes:
    """Pack message in 55AA format (Protocol 3.1-3.4).

    Structure: [header 16B] [payload] [crc/hmac] [suffix 4B]
    Length field = len(payload) + len(crc/hmac) + len(suffix)
    """
    cipher = AESCipher(key)

    # Encrypt payload if needed
    if encrypt and payload:
        payload = cipher.encrypt_ecb(payload, pad=True)

    # Calculate footer size
    footer_size = FOOTER_SIZE_55AA_HMAC if use_hmac else FOOTER_SIZE_55AA_CRC

    # Length = payload + footer (includes suffix)
    length = len(payload) + footer_size

    # Build header
    header = struct.pack(HEADER_FMT_55AA, PREFIX_55AA, seqno, cmd, length)

    # Calculate CRC/HMAC over header + payload
    data_to_sign = header + payload

    if use_hmac:
        signature = hmac.new(key, data_to_sign, sha256).digest()
        footer = struct.pack(FOOTER_FMT_55AA_HMAC, signature, SUFFIX_55AA)
    else:
        crc = binascii.crc32(data_to_sign) & 0xFFFFFFFF
        footer = struct.pack(FOOTER_FMT_55AA_CRC, crc, SUFFIX_55AA)

    return header + payload + footer


def _pack_message_6699(
    seqno: int,
    cmd: int,
    payload: bytes,
    key: bytes,
    encrypt: bool
) -> bytes:
    """Pack message in 6699 format (Protocol 3.5).

    Structure: [header 18B] [nonce 12B] [encrypted_payload] [tag 16B] [suffix 4B]
    Length field = len(nonce) + len(encrypted_payload) + len(tag) = payload_len + 28
    AAD = header bytes 4-18 (version, reserved, seqno, cmd, length)
    """
    # Generate random nonce
    nonce = os.urandom(GCM_NONCE_SIZE)

    # Build header first (we need AAD)
    # Length = nonce(12) + encrypted_payload + tag(16)
    payload_len = len(payload)
    length = GCM_NONCE_SIZE + payload_len + GCM_TAG_SIZE

    header = struct.pack(
        HEADER_FMT_6699,
        PREFIX_6699,
        0x00,  # version
        0x00,  # reserved
        seqno,
        cmd,
        length
    )

    # AAD is header without prefix (bytes 4-18)
    aad = header[4:]

    # Encrypt payload with GCM
    cipher = AESCipher(key)
    if encrypt and payload:
        ciphertext, tag = cipher.encrypt_gcm(payload, nonce, aad)
    else:
        # Even "unencrypted" 6699 needs GCM format
        ciphertext, tag = cipher.encrypt_gcm(payload, nonce, aad)

    # Build footer
    footer = struct.pack(FOOTER_FMT_6699, tag, SUFFIX_6699)

    return header + nonce + ciphertext + footer


# =============================================================================
# MESSAGE UNPACKING
# =============================================================================

def unpack_message(
    data: bytes,
    key: bytes,
    protocol_version: float,
    header: Optional[TuyaHeader] = None,
    no_retcode: bool = False
) -> TuyaMessage:
    """Unpack received message.

    Args:
        data: Raw message bytes
        key: Decryption key (device key or session key)
        protocol_version: Protocol version
        header: Pre-parsed header (optional, will parse if not provided)
        no_retcode: Skip retcode parsing (for some message types)

    Returns:
        TuyaMessage with decrypted payload

    Raises:
        DecodeError: If message cannot be unpacked
    """
    if header is None:
        header = parse_header(data)

    if header.prefix == PREFIX_6699:
        return _unpack_message_6699(data, key, header)
    else:
        use_hmac = protocol_version >= 3.4
        return _unpack_message_55aa(data, key, header, use_hmac, no_retcode)


def _unpack_message_55aa(
    data: bytes,
    key: bytes,
    header: TuyaHeader,
    use_hmac: bool,
    no_retcode: bool
) -> TuyaMessage:
    """Unpack 55AA format message."""
    footer_size = FOOTER_SIZE_55AA_HMAC if use_hmac else FOOTER_SIZE_55AA_CRC

    # Check we have enough data
    if len(data) < header.total_length:
        raise DecodeError(
            f"Not enough data: need {header.total_length}, got {len(data)}"
        )

    # Extract retcode (if present)
    payload_start = HEADER_SIZE_55AA
    retcode = 0

    if not no_retcode:
        if len(data) >= payload_start + RETCODE_SIZE:
            # Check if this looks like a retcode (usually 0 or small number)
            potential_retcode = struct.unpack(
                RETCODE_FMT,
                data[payload_start:payload_start + RETCODE_SIZE]
            )[0]
            # Retcode is usually present in device responses
            if potential_retcode < 100:  # Reasonable retcode range
                retcode = potential_retcode
                payload_start += RETCODE_SIZE

    # Extract payload (everything between header/retcode and footer)
    payload_end = HEADER_SIZE_55AA + header.length - footer_size
    payload = data[payload_start:payload_end]

    # Extract and verify footer
    footer_start = payload_end
    footer_data = data[footer_start:footer_start + footer_size]

    crc_good = True
    if use_hmac:
        received_hmac, suffix = struct.unpack(FOOTER_FMT_55AA_HMAC, footer_data)
        expected_hmac = hmac.new(key, data[:footer_start], sha256).digest()
        crc_good = hmac.compare_digest(expected_hmac, received_hmac)
        if suffix != SUFFIX_55AA:
            _LOGGER.debug("55AA suffix mismatch: got %08X", suffix)
    else:
        received_crc, suffix = struct.unpack(FOOTER_FMT_55AA_CRC, footer_data)
        expected_crc = binascii.crc32(data[:footer_start]) & 0xFFFFFFFF
        crc_good = (expected_crc == received_crc)
        if suffix != SUFFIX_55AA:
            _LOGGER.debug("55AA suffix mismatch: got %08X", suffix)

    return TuyaMessage(
        seqno=header.seqno,
        cmd=header.cmd,
        payload=payload,
        retcode=retcode,
        crc_good=crc_good,
        prefix=header.prefix,
        nonce=None,
        tag=None
    )


def _unpack_message_6699(
    data: bytes,
    key: bytes,
    header: TuyaHeader
) -> TuyaMessage:
    """Unpack 6699 format message (Protocol 3.5).

    Structure: [header 18B] [nonce 12B] [encrypted_payload] [tag 16B] [suffix 4B]
    """
    # Check we have enough data
    if len(data) < header.total_length:
        raise DecodeError(
            f"Not enough data: need {header.total_length}, got {len(data)}"
        )

    # Extract nonce (12 bytes after header)
    nonce_start = HEADER_SIZE_6699
    nonce = data[nonce_start:nonce_start + GCM_NONCE_SIZE]

    # Extract encrypted payload (between nonce and tag)
    payload_start = nonce_start + GCM_NONCE_SIZE
    payload_end = HEADER_SIZE_6699 + header.length - GCM_TAG_SIZE
    ciphertext = data[payload_start:payload_end]

    # Extract tag (16 bytes before suffix)
    tag_start = payload_end
    tag = data[tag_start:tag_start + GCM_TAG_SIZE]

    # Extract suffix
    suffix_start = tag_start + GCM_TAG_SIZE
    suffix = struct.unpack(">I", data[suffix_start:suffix_start + 4])[0]
    if suffix != SUFFIX_6699:
        _LOGGER.debug("6699 suffix mismatch: got %08X, expected %08X", suffix, SUFFIX_6699)

    # AAD is header bytes 4-18 (excluding prefix)
    aad = data[4:HEADER_SIZE_6699]

    # Decrypt with GCM
    cipher = AESCipher(key)
    crc_good = True
    payload = b""

    # Try GCM with AAD first
    try:
        payload = cipher.decrypt_gcm(ciphertext, nonce, tag, aad)
    except Exception as e1:
        _LOGGER.debug("GCM decrypt with AAD failed: %s", e1)
        # Try without AAD
        try:
            payload = cipher.decrypt_gcm(ciphertext, nonce, tag, None)
        except Exception as e2:
            _LOGGER.debug("GCM decrypt without AAD failed: %s", e2)
            # Last resort: CTR mode (no authentication)
            try:
                payload = cipher.decrypt_gcm_noauth(ciphertext, nonce)
                crc_good = False  # No authentication
            except Exception as e3:
                _LOGGER.warning(
                    "Protocol 3.5 decrypt failed (all methods). cmd=%d, ciphertext_len=%d: %s",
                    header.cmd, len(ciphertext), e3
                )
                # Return empty payload instead of encrypted garbage to avoid JSON parse errors
                payload = b""
                crc_good = False

    # Extract retcode from payload if present (not for session key commands)
    retcode = 0
    if len(payload) >= 4 and payload[:4] == b'\x00\x00\x00\x00':
        # Check if this looks like a retcode followed by data
        if len(payload) > 4:
            retcode = struct.unpack(RETCODE_FMT, payload[:4])[0]
            payload = payload[4:]

    return TuyaMessage(
        seqno=header.seqno,
        cmd=header.cmd,
        payload=payload,
        retcode=retcode,
        crc_good=crc_good,
        prefix=header.prefix,
        nonce=nonce,
        tag=tag
    )


# =============================================================================
# UTILITIES
# =============================================================================

def calculate_crc32(data: bytes) -> int:
    """Calculate CRC32 checksum."""
    return binascii.crc32(data) & 0xFFFFFFFF


def calculate_hmac_sha256(key: bytes, data: bytes) -> bytes:
    """Calculate HMAC-SHA256."""
    return hmac.new(key, data, sha256).digest()
