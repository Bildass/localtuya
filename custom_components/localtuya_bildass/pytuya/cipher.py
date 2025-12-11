# -*- coding: utf-8 -*-
"""
AES Cipher module for Tuya communication.

Provides:
- ECB mode encryption/decryption for Protocol 3.1-3.4
- GCM mode encryption/decryption for Protocol 3.5

Based on TinyTuya implementation.
"""

import base64
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .constants import AES_BLOCK_SIZE, GCM_NONCE_SIZE, GCM_TAG_SIZE


class AESCipher:
    """AES cipher for Tuya device communication.

    Supports both ECB mode (Protocol 3.1-3.4) and GCM mode (Protocol 3.5).
    """

    def __init__(self, key: bytes):
        """Initialize cipher with encryption key.

        Args:
            key: 16-byte AES key (device local_key or session key)
        """
        if isinstance(key, str):
            key = key.encode("latin1")
        if len(key) != 16:
            raise ValueError(f"AES key must be 16 bytes, got {len(key)}")

        self.key = key
        self._ecb_cipher = Cipher(
            algorithms.AES(key),
            modes.ECB(),
            backend=default_backend()
        )

    # =========================================================================
    # ECB MODE (Protocol 3.1-3.4)
    # =========================================================================

    def encrypt_ecb(self, plaintext: bytes, pad: bool = True) -> bytes:
        """Encrypt data using AES-ECB mode.

        Args:
            plaintext: Data to encrypt
            pad: Whether to apply PKCS7 padding (default True)

        Returns:
            Encrypted ciphertext
        """
        if pad:
            plaintext = self._pkcs7_pad(plaintext)

        encryptor = self._ecb_cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()

    def decrypt_ecb(self, ciphertext: bytes, unpad: bool = True) -> bytes:
        """Decrypt data using AES-ECB mode.

        Args:
            ciphertext: Data to decrypt
            unpad: Whether to remove PKCS7 padding (default True)

        Returns:
            Decrypted plaintext
        """
        decryptor = self._ecb_cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        if unpad:
            plaintext = self._pkcs7_unpad(plaintext)

        return plaintext

    def encrypt_ecb_base64(self, plaintext: bytes, pad: bool = True) -> bytes:
        """Encrypt and return base64-encoded result.

        Args:
            plaintext: Data to encrypt
            pad: Whether to apply PKCS7 padding

        Returns:
            Base64-encoded ciphertext
        """
        encrypted = self.encrypt_ecb(plaintext, pad)
        return base64.b64encode(encrypted)

    def decrypt_ecb_base64(self, ciphertext: bytes, unpad: bool = True) -> bytes:
        """Decrypt base64-encoded data.

        Args:
            ciphertext: Base64-encoded data to decrypt
            unpad: Whether to remove PKCS7 padding

        Returns:
            Decrypted plaintext
        """
        decoded = base64.b64decode(ciphertext)
        return self.decrypt_ecb(decoded, unpad)

    # =========================================================================
    # GCM MODE (Protocol 3.5)
    # =========================================================================

    def encrypt_gcm(
        self,
        plaintext: bytes,
        nonce: bytes,
        aad: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """Encrypt data using AES-GCM mode.

        Args:
            plaintext: Data to encrypt
            nonce: 12-byte nonce/IV for GCM
            aad: Additional authenticated data (optional)

        Returns:
            Tuple of (ciphertext, tag)
        """
        if len(nonce) != GCM_NONCE_SIZE:
            raise ValueError(f"GCM nonce must be {GCM_NONCE_SIZE} bytes, got {len(nonce)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()

        if aad:
            encryptor.authenticate_additional_data(aad)

        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return ciphertext, encryptor.tag

    def decrypt_gcm(
        self,
        ciphertext: bytes,
        nonce: bytes,
        tag: bytes,
        aad: Optional[bytes] = None
    ) -> bytes:
        """Decrypt data using AES-GCM mode with authentication.

        Args:
            ciphertext: Data to decrypt
            nonce: 12-byte nonce/IV used for encryption
            tag: 16-byte GCM authentication tag
            aad: Additional authenticated data (optional)

        Returns:
            Decrypted plaintext

        Raises:
            InvalidTag: If authentication fails
        """
        if len(nonce) != GCM_NONCE_SIZE:
            raise ValueError(f"GCM nonce must be {GCM_NONCE_SIZE} bytes, got {len(nonce)}")
        if len(tag) != GCM_TAG_SIZE:
            raise ValueError(f"GCM tag must be {GCM_TAG_SIZE} bytes, got {len(tag)}")

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        if aad:
            decryptor.authenticate_additional_data(aad)

        return decryptor.update(ciphertext) + decryptor.finalize()

    def decrypt_gcm_noauth(
        self,
        ciphertext: bytes,
        nonce: bytes
    ) -> bytes:
        """Decrypt data using AES-CTR mode (GCM without authentication).

        This is a fallback for when GCM authentication fails.
        Uses CTR mode which is the underlying cipher for GCM.

        Args:
            ciphertext: Data to decrypt
            nonce: 12-byte nonce/IV

        Returns:
            Decrypted plaintext (NOT authenticated!)
        """
        if len(nonce) != GCM_NONCE_SIZE:
            raise ValueError(f"Nonce must be {GCM_NONCE_SIZE} bytes, got {len(nonce)}")

        # CTR counter starts at 2 for GCM (0 and 1 are used for auth)
        counter = nonce + b"\x00\x00\x00\x02"

        cipher = Cipher(
            algorithms.AES(self.key),
            modes.CTR(counter),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()

        return decryptor.update(ciphertext) + decryptor.finalize()

    # =========================================================================
    # PADDING
    # =========================================================================

    def _pkcs7_pad(self, data: bytes) -> bytes:
        """Apply PKCS7 padding to data."""
        pad_len = AES_BLOCK_SIZE - (len(data) % AES_BLOCK_SIZE)
        return data + bytes([pad_len] * pad_len)

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        """Remove PKCS7 padding from data."""
        if not data:
            return data
        pad_len = data[-1]
        if pad_len > AES_BLOCK_SIZE or pad_len == 0:
            return data  # Invalid padding, return as-is
        # Verify padding bytes
        if data[-pad_len:] != bytes([pad_len] * pad_len):
            return data  # Invalid padding
        return data[:-pad_len]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def encrypt_udp(data: bytes) -> bytes:
    """Encrypt UDP broadcast data using shared UDP key.

    Args:
        data: Data to encrypt

    Returns:
        Encrypted data
    """
    from .constants import UDP_KEY
    cipher = AESCipher(UDP_KEY)
    return cipher.encrypt_ecb(data, pad=True)


def decrypt_udp(data: bytes) -> bytes:
    """Decrypt UDP broadcast data using shared UDP key.

    Args:
        data: Encrypted data

    Returns:
        Decrypted data
    """
    from .constants import UDP_KEY
    cipher = AESCipher(UDP_KEY)
    return cipher.decrypt_ecb(data, unpad=True)
