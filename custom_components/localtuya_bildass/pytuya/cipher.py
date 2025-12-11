# PyTuya Cipher Module
# -*- coding: utf-8 -*-
"""
AES encryption/decryption for Tuya protocol.

Supports both ECB (Protocol 3.1-3.4) and GCM (Protocol 3.5) modes.
Based on TinyTuya implementation for Protocol 3.5 compatibility.
"""

import logging
import os
from hashlib import md5
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


# UDP broadcast decryption keys
UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()
UDP_KEY_35 = md5(b"A]c#n0r@xqhk,XuM").digest()


class AESCipher:
    """
    AES Cipher for Tuya protocol encryption/decryption.

    Provides separate methods for ECB and GCM modes to avoid confusion
    and enable proper testing of each mode independently.
    """

    def __init__(self, key: bytes):
        """
        Initialize cipher with encryption key.

        Args:
            key: 16-byte AES key (device local_key or session key)
        """
        if isinstance(key, str):
            key = key.encode('utf-8')

        if len(key) != 16:
            raise ValueError(f"AES key must be 16 bytes, got {len(key)}")

        self.key = key

    # =========================================================================
    # ECB Mode (Protocol 3.1-3.4)
    # =========================================================================

    def encrypt_ecb(self, data: bytes, pad: bool = True) -> bytes:
        """
        Encrypt data using AES-ECB mode.

        Args:
            data: Plaintext to encrypt
            pad: Whether to apply PKCS7 padding (default: True)

        Returns:
            Encrypted ciphertext
        """
        if pad:
            data = self._pad(data)

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.ECB(),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def decrypt_ecb(self, data: bytes, unpad: bool = True) -> bytes:
        """
        Decrypt data using AES-ECB mode.

        Args:
            data: Ciphertext to decrypt
            unpad: Whether to remove PKCS7 padding (default: True)

        Returns:
            Decrypted plaintext
        """
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.ECB(),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(data) + decryptor.finalize()

        if unpad:
            decrypted = self._unpad(decrypted)

        return decrypted

    # =========================================================================
    # GCM Mode (Protocol 3.5)
    # =========================================================================

    def encrypt_gcm(
        self,
        data: bytes,
        iv: Optional[bytes] = None,
        aad: Optional[bytes] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Encrypt data using AES-GCM mode.

        Args:
            data: Plaintext to encrypt
            iv: 12-byte initialization vector (generated if not provided)
            aad: Additional authenticated data (optional)

        Returns:
            Tuple of (iv, ciphertext, tag)
            - iv: 12-byte initialization vector
            - ciphertext: Encrypted data (same length as input, NO padding)
            - tag: 16-byte authentication tag
        """
        if iv is None:
            iv = os.urandom(12)

        if len(iv) != 12:
            raise ValueError(f"GCM IV must be 12 bytes, got {len(iv)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        if aad is not None:
            encryptor.authenticate_additional_data(aad)

        ciphertext = encryptor.update(data) + encryptor.finalize()
        tag = encryptor.tag

        return iv, ciphertext, tag

    def decrypt_gcm(
        self,
        ciphertext: bytes,
        iv: bytes,
        tag: bytes,
        aad: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using AES-GCM mode.

        Args:
            ciphertext: Encrypted data
            iv: 12-byte initialization vector
            tag: 16-byte authentication tag
            aad: Additional authenticated data (must match encryption)

        Returns:
            Decrypted plaintext

        Raises:
            InvalidTag: If authentication fails
        """
        if len(iv) != 12:
            raise ValueError(f"GCM IV must be 12 bytes, got {len(iv)}")
        if len(tag) != 16:
            raise ValueError(f"GCM tag must be 16 bytes, got {len(tag)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        if aad is not None:
            decryptor.authenticate_additional_data(aad)

        return decryptor.update(ciphertext) + decryptor.finalize()

    def decrypt_gcm_with_fallback(
        self,
        ciphertext: bytes,
        iv: bytes,
        tag: bytes,
        aad: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt with GCM, falling back to no-AAD if verification fails.

        Some Tuya devices don't properly use AAD, so we try both methods.

        Args:
            ciphertext: Encrypted data
            iv: 12-byte initialization vector
            tag: 16-byte authentication tag
            aad: Additional authenticated data to try first

        Returns:
            Decrypted plaintext
        """
        # Try with AAD first
        if aad is not None:
            try:
                return self.decrypt_gcm(ciphertext, iv, tag, aad)
            except Exception as ex:
                _LOGGER.debug("GCM decrypt with AAD failed: %s, trying without AAD", ex)

        # Try without AAD
        try:
            return self.decrypt_gcm(ciphertext, iv, tag, None)
        except Exception as ex:
            _LOGGER.debug("GCM decrypt without AAD also failed: %s", ex)
            raise

    # =========================================================================
    # Hybrid encrypt/decrypt (for backward compatibility)
    # =========================================================================

    def encrypt(
        self,
        data: bytes,
        use_gcm: bool = False,
        iv: Optional[bytes] = None,
        aad: Optional[bytes] = None,
        pad: bool = True
    ) -> bytes:
        """
        Encrypt data using ECB or GCM mode.

        For GCM mode, returns: IV(12) + ciphertext + tag(16)
        For ECB mode, returns: padded ciphertext

        Args:
            data: Plaintext to encrypt
            use_gcm: Use GCM mode (Protocol 3.5) instead of ECB
            iv: IV for GCM mode (12 bytes, generated if None)
            aad: Additional authenticated data for GCM mode
            pad: Apply padding for ECB mode

        Returns:
            Encrypted data
        """
        if use_gcm:
            iv_out, ciphertext, tag = self.encrypt_gcm(data, iv, aad)
            return iv_out + ciphertext + tag
        else:
            return self.encrypt_ecb(data, pad)

    def decrypt(
        self,
        data: bytes,
        use_gcm: bool = False,
        aad: Optional[bytes] = None,
        unpad: bool = True
    ) -> bytes:
        """
        Decrypt data using ECB or GCM mode.

        For GCM mode, expects: IV(12) + ciphertext + tag(16)
        For ECB mode, expects: padded ciphertext

        Args:
            data: Encrypted data
            use_gcm: Use GCM mode (Protocol 3.5) instead of ECB
            aad: Additional authenticated data for GCM mode
            unpad: Remove padding for ECB mode

        Returns:
            Decrypted plaintext
        """
        if use_gcm:
            iv = data[:12]
            tag = data[-16:]
            ciphertext = data[12:-16]
            return self.decrypt_gcm_with_fallback(ciphertext, iv, tag, aad)
        else:
            return self.decrypt_ecb(data, unpad)

    # =========================================================================
    # Padding helpers (PKCS7)
    # =========================================================================

    @staticmethod
    def _pad(data: bytes, block_size: int = 16) -> bytes:
        """Apply PKCS7 padding to data."""
        pad_len = block_size - (len(data) % block_size)
        return data + bytes([pad_len] * pad_len)

    @staticmethod
    def _unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding from data."""
        if not data:
            return data
        pad_len = data[-1]
        if pad_len > 16 or pad_len == 0:
            return data  # Invalid padding, return as-is
        if data[-pad_len:] != bytes([pad_len] * pad_len):
            return data  # Invalid padding, return as-is
        return data[:-pad_len]


# =============================================================================
# UDP Broadcast Decryption Functions
# =============================================================================

def decrypt_udp_broadcast(data: bytes) -> str:
    """
    Decrypt UDP broadcast message (55AA format, Protocol 3.1-3.4).

    Args:
        data: Raw UDP payload (encrypted)

    Returns:
        Decrypted JSON string
    """
    cipher = AESCipher(UDP_KEY)
    decrypted = cipher.decrypt_ecb(data, unpad=True)
    return decrypted.decode('utf-8')


def decrypt_udp_broadcast_35(data: bytes) -> str:
    """
    Decrypt UDP broadcast message (6699 format, Protocol 3.5).

    Tries multiple decryption methods for compatibility.

    Args:
        data: Raw UDP payload (IV + encrypted + tag or just encrypted)

    Returns:
        Decrypted JSON string

    Raises:
        ValueError: If all decryption methods fail
    """
    # Method 1: Try ECB with standard UDP key
    try:
        cipher = AESCipher(UDP_KEY)
        decrypted = cipher.decrypt_ecb(data, unpad=True)
        result = decrypted.decode('utf-8')
        if '{' in result:
            return result
    except Exception:
        pass

    # Method 2: Try ECB with Protocol 3.5 specific key
    try:
        cipher = AESCipher(UDP_KEY_35)
        decrypted = cipher.decrypt_ecb(data, unpad=True)
        result = decrypted.decode('utf-8')
        if '{' in result:
            return result
    except Exception:
        pass

    # Method 3: Try GCM without AAD (most common for v3.5)
    # Format: IV(12) + encrypted + tag(16)
    if len(data) > 28:  # Minimum: 12 (IV) + 16 (tag) + some data
        try:
            iv = data[:12]
            tag = data[-16:]
            ciphertext = data[12:-16]

            cipher = AESCipher(UDP_KEY)
            decrypted = cipher.decrypt_gcm(ciphertext, iv, tag, None)
            return decrypted.decode('utf-8')
        except Exception:
            pass

    # Method 4: Try GCM with UDP_KEY_35
    if len(data) > 28:
        try:
            iv = data[:12]
            tag = data[-16:]
            ciphertext = data[12:-16]

            cipher = AESCipher(UDP_KEY_35)
            decrypted = cipher.decrypt_gcm(ciphertext, iv, tag, None)
            return decrypted.decode('utf-8')
        except Exception:
            pass

    raise ValueError("All UDP broadcast decryption methods failed")
