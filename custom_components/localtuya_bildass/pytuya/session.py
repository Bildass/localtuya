# PyTuya Session Key Negotiation
# -*- coding: utf-8 -*-
"""
Session key negotiation for Tuya Protocol 3.4 and 3.5.

Based on TinyTuya implementation for correct Protocol 3.5 support.
Reference: https://github.com/jasonacox/tinytuya/discussions/260

Session Key Negotiation Flow:
1. Client -> Device: SESS_KEY_NEG_START with local_nonce (16 bytes)
2. Device -> Client: SESS_KEY_NEG_RESP with remote_nonce (16 bytes) + HMAC (32 bytes)
3. Client verifies HMAC = HMAC-SHA256(device_key, local_nonce)
4. Client calculates session_key = encrypt(XOR(local_nonce, remote_nonce))
5. Client -> Device: SESS_KEY_NEG_FINISH with HMAC-SHA256(device_key, remote_nonce)
6. Both sides now use session_key for further communication
"""

import hmac
import logging
import os
from hashlib import sha256
from typing import Optional, Tuple

from .cipher import AESCipher
from .constants import (
    HMACVerificationError,
    SESS_KEY_NEG_FINISH,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_START,
    SessionKeyError,
    SessionKeyInvalidError,
)
from .message import MessagePayload

_LOGGER = logging.getLogger(__name__)


class SessionKeyNegotiator:
    """
    Handles session key negotiation for Tuya Protocol 3.4 and 3.5.

    This class encapsulates the session key negotiation logic,
    making it easier to test and debug.
    """

    # Maximum number of retries if session key starts with 0x00
    MAX_RETRIES = 5

    def __init__(
        self,
        device_key: bytes,
        protocol_version: float,
        strict_hmac: bool = False,
    ):
        """
        Initialize session key negotiator.

        Args:
            device_key: Device's local_key (16 bytes)
            protocol_version: Protocol version (3.4 or 3.5)
            strict_hmac: If True, raise exception on HMAC mismatch
                        If False, log warning but continue (some devices don't match)
        """
        if isinstance(device_key, str):
            device_key = device_key.encode('utf-8')

        if len(device_key) != 16:
            raise ValueError(f"Device key must be 16 bytes, got {len(device_key)}")

        self.device_key = device_key
        self.version = protocol_version
        self.strict_hmac = strict_hmac

        # Session state
        self.local_nonce: Optional[bytes] = None
        self.remote_nonce: Optional[bytes] = None
        self.session_key: Optional[bytes] = None
        self.retry_count = 0

    def reset(self):
        """Reset session state for new negotiation."""
        self.local_nonce = None
        self.remote_nonce = None
        self.session_key = None
        self.retry_count = 0

    # =========================================================================
    # Step 1: Generate local nonce
    # =========================================================================

    def create_step1_payload(self) -> MessagePayload:
        """
        Create SESS_KEY_NEG_START payload.

        Generates a random 16-byte local nonce.

        Returns:
            MessagePayload with local_nonce as payload
        """
        self.local_nonce = os.urandom(16)
        _LOGGER.debug("Session negotiation step 1: local_nonce=%s", self.local_nonce.hex())
        return MessagePayload(cmd=SESS_KEY_NEG_START, payload=self.local_nonce)

    # =========================================================================
    # Step 2: Process device response
    # =========================================================================

    def process_step2_response(self, payload: bytes) -> bool:
        """
        Process SESS_KEY_NEG_RESP from device.

        Extracts remote_nonce and verifies HMAC.

        Args:
            payload: Decrypted response payload (48 bytes: nonce + HMAC)

        Returns:
            True if HMAC verification passed (or was ignored)

        Raises:
            SessionKeyError: If payload is too short
            HMACVerificationError: If strict_hmac is True and HMAC doesn't match
        """
        # Handle retcode prefix (some devices include 4-byte retcode)
        if len(payload) >= 52 and payload[:4] == b'\x00\x00\x00\x00':
            _LOGGER.debug("Stripping 4-byte retcode from step 2 payload")
            payload = payload[4:]

        if len(payload) < 48:
            raise SessionKeyError(
                f"Step 2 payload too short: {len(payload)} bytes (expected 48)"
            )

        # Extract remote nonce (first 16 bytes)
        self.remote_nonce = payload[:16]

        # Extract device's HMAC (next 32 bytes)
        received_hmac = payload[16:48]

        _LOGGER.debug(
            "Session negotiation step 2: remote_nonce=%s, received_hmac=%s",
            self.remote_nonce.hex(),
            received_hmac.hex()[:32] + "..."
        )

        # Verify HMAC: HMAC-SHA256(device_key, local_nonce)
        expected_hmac = hmac.new(self.device_key, self.local_nonce, sha256).digest()

        if not hmac.compare_digest(expected_hmac, received_hmac):
            _LOGGER.warning(
                "HMAC verification failed: expected=%s, received=%s",
                expected_hmac.hex()[:32] + "...",
                received_hmac.hex()[:32] + "..."
            )
            if self.strict_hmac:
                raise HMACVerificationError(
                    "Device HMAC doesn't match expected value"
                )
            # Continue anyway - some devices have broken HMAC implementation
            return False

        _LOGGER.debug("HMAC verification passed")
        return True

    # =========================================================================
    # Step 3: Calculate session key
    # =========================================================================

    def calculate_session_key(self) -> bytes:
        """
        Calculate session key from local and remote nonces.

        Algorithm:
        1. XOR local_nonce with remote_nonce
        2. Encrypt XOR result:
           - Protocol 3.4: AES-ECB
           - Protocol 3.5: AES-GCM with IV=local_nonce[:12]
        3. Session key = first 16 bytes of ciphertext

        Returns:
            16-byte session key

        Raises:
            SessionKeyError: If nonces are not set
            SessionKeyInvalidError: If session key starts with 0x00
        """
        if self.local_nonce is None or self.remote_nonce is None:
            raise SessionKeyError("Cannot calculate session key: nonces not set")

        # Step 1: XOR the nonces
        xor_result = bytes([a ^ b for a, b in zip(self.local_nonce, self.remote_nonce)])
        _LOGGER.debug("XOR result: %s", xor_result.hex())

        cipher = AESCipher(self.device_key)

        if self.version >= 3.5:
            # Protocol 3.5: AES-GCM encryption
            # IV = first 12 bytes of local_nonce (client's nonce)
            iv = self.local_nonce[:12]
            _LOGGER.debug(
                "Calculating v3.5 session key: XOR=%s, IV=%s, device_key=%s",
                xor_result.hex(), iv.hex(), self.device_key.hex()
            )

            # GCM encrypt returns (iv, ciphertext, tag)
            # We only use the ciphertext portion
            _, ciphertext, tag = cipher.encrypt_gcm(xor_result, iv, None)

            _LOGGER.debug(
                "GCM encrypt result: ciphertext=%s (len=%d), tag=%s",
                ciphertext.hex(), len(ciphertext), tag.hex()
            )

            # Session key is the ciphertext (NOT including IV or tag)
            # This is 16 bytes because XOR result is 16 bytes and GCM doesn't pad
            session_key = ciphertext[:16]
        else:
            # Protocol 3.4: AES-ECB encryption
            _LOGGER.debug("Calculating v3.4 session key with ECB")
            session_key = cipher.encrypt_ecb(xor_result, pad=False)

        _LOGGER.debug("Calculated session key: %s", session_key.hex())

        # Validate session key - TinyTuya notes that if first byte is 0x00,
        # the device will reject it
        if session_key[0] == 0x00:
            self.retry_count += 1
            if self.retry_count >= self.MAX_RETRIES:
                raise SessionKeyInvalidError(
                    f"Session key starts with 0x00 after {self.retry_count} retries"
                )
            _LOGGER.warning(
                "Session key starts with 0x00, retry %d/%d",
                self.retry_count, self.MAX_RETRIES
            )
            raise SessionKeyInvalidError("Session key starts with 0x00, retry needed")

        self.session_key = session_key
        return session_key

    # =========================================================================
    # Step 4: Create finish payload
    # =========================================================================

    def create_step3_payload(self) -> MessagePayload:
        """
        Create SESS_KEY_NEG_FINISH payload.

        Payload is HMAC-SHA256(device_key, remote_nonce).

        Returns:
            MessagePayload with HMAC as payload

        Raises:
            SessionKeyError: If remote_nonce is not set
        """
        if self.remote_nonce is None:
            raise SessionKeyError("Cannot create step 3 payload: remote_nonce not set")

        # Calculate HMAC of remote nonce
        finish_hmac = hmac.new(self.device_key, self.remote_nonce, sha256).digest()

        _LOGGER.debug(
            "Session negotiation step 3: HMAC=%s",
            finish_hmac.hex()[:32] + "..."
        )

        return MessagePayload(cmd=SESS_KEY_NEG_FINISH, payload=finish_hmac)

    # =========================================================================
    # High-level negotiation
    # =========================================================================

    def get_session_key(self) -> Optional[bytes]:
        """Get the negotiated session key, or None if not yet negotiated."""
        return self.session_key

    def is_negotiation_needed(self) -> bool:
        """Check if session key negotiation is required."""
        return self.version >= 3.4

    def needs_retry(self) -> bool:
        """Check if negotiation needs to be retried (due to 0x00 session key)."""
        return self.retry_count > 0 and self.retry_count < self.MAX_RETRIES


# =============================================================================
# Convenience Functions
# =============================================================================

def negotiate_session_key(
    device_key: bytes,
    local_nonce: bytes,
    remote_nonce: bytes,
    protocol_version: float,
) -> bytes:
    """
    Calculate session key from nonces (standalone function).

    This is a convenience function for testing or one-off calculations.

    Args:
        device_key: Device's local_key (16 bytes)
        local_nonce: Client's nonce (16 bytes)
        remote_nonce: Device's nonce (16 bytes)
        protocol_version: Protocol version (3.4 or 3.5)

    Returns:
        16-byte session key

    Raises:
        SessionKeyInvalidError: If session key starts with 0x00
    """
    negotiator = SessionKeyNegotiator(device_key, protocol_version)
    negotiator.local_nonce = local_nonce
    negotiator.remote_nonce = remote_nonce
    return negotiator.calculate_session_key()


def verify_device_hmac(
    device_key: bytes,
    local_nonce: bytes,
    received_hmac: bytes,
) -> bool:
    """
    Verify HMAC received from device.

    Args:
        device_key: Device's local_key
        local_nonce: Client's nonce sent in step 1
        received_hmac: HMAC received from device in step 2

    Returns:
        True if HMAC matches
    """
    expected_hmac = hmac.new(device_key, local_nonce, sha256).digest()
    return hmac.compare_digest(expected_hmac, received_hmac)


def create_finish_hmac(device_key: bytes, remote_nonce: bytes) -> bytes:
    """
    Create HMAC for SESS_KEY_NEG_FINISH step.

    Args:
        device_key: Device's local_key
        remote_nonce: Device's nonce received in step 2

    Returns:
        32-byte HMAC
    """
    return hmac.new(device_key, remote_nonce, sha256).digest()
