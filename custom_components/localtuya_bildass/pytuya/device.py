# -*- coding: utf-8 -*-
"""
Tuya Device communication module.

Provides asyncio-based communication with Tuya devices.
Supports Protocol versions 3.1, 3.2, 3.3, 3.4, and 3.5.
"""

import asyncio
import hmac
import json
import logging
import os
import time
import weakref
from abc import ABC, abstractmethod
from hashlib import sha256
from typing import Any, Callable, Dict, Optional

from .cipher import AESCipher
from .constants import (
    # Commands
    CMD_CONTROL, CMD_CONTROL_NEW, CMD_DP_QUERY, CMD_DP_QUERY_NEW,
    CMD_HEART_BEAT, CMD_STATUS, CMD_UPDATE_DPS,
    CMD_SESS_KEY_NEG_START, CMD_SESS_KEY_NEG_RESP, CMD_SESS_KEY_NEG_FINISH,
    # Protocol
    PREFIX_55AA, PREFIX_6699,
    VERSION_31, VERSION_33, VERSION_34, VERSION_35,
    PROTOCOL_3X_HEADER_PAD,
    NO_PROTOCOL_HEADER_CMDS, SESSION_KEY_CMDS,
    # Payload
    PAYLOAD_DICT, DEVICE_TYPE_0A, DEVICE_TYPE_0D, DEVICE_TYPE_V34, DEVICE_TYPE_V35,
    # Timing
    HEARTBEAT_INTERVAL, DEFAULT_TIMEOUT,
    UPDATE_DPS_WHITELIST,
    # Errors
    ERR_JSON, ERR_PAYLOAD, ERROR_MESSAGES,
)
from .message import (
    TuyaMessage, MessagePayload, DeviceStatus,
    DecodeError, SessionKeyError, TimeoutError as TuyaTimeoutError
)
from .protocol import (
    parse_header, pack_message, unpack_message,
    HEADER_SIZE_55AA, HEADER_SIZE_6699,
)

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# LOGGING ADAPTER
# =============================================================================

class TuyaLoggingAdapter(logging.LoggerAdapter):
    """Adapter that adds device ID to log messages."""

    def process(self, msg, kwargs):
        dev_id = self.extra.get("device_id", "???")
        # Show first and last 3 chars of device ID
        short_id = f"{dev_id[:3]}...{dev_id[-3:]}" if len(dev_id) > 6 else dev_id
        return f"[{short_id}] {msg}", kwargs


class ContextualLogger:
    """Contextual logger that can be used as a mixin.

    Provides logging methods that include device ID in messages.
    Used by common.py for TuyaDevice and LocalTuyaEntity classes.
    """

    def __init__(self):
        """Initialize logger."""
        self._logger = None
        self._enable_debug = False

    def set_logger(self, logger, device_id, enable_debug=False):
        """Set the base logger to use.

        Args:
            logger: Base logger instance
            device_id: Device ID for log messages
            enable_debug: Whether to enable debug logging
        """
        self._enable_debug = enable_debug
        self._logger = TuyaLoggingAdapter(logger, {"device_id": device_id})

    def debug(self, msg, *args):
        """Log debug message (only if debug enabled)."""
        if self._enable_debug and self._logger:
            self._logger.debug(msg, *args)

    def info(self, msg, *args):
        """Log info message."""
        if self._logger:
            self._logger.info(msg, *args)

    def warning(self, msg, *args):
        """Log warning message."""
        if self._logger:
            self._logger.warning(msg, *args)

    def error(self, msg, *args):
        """Log error message."""
        if self._logger:
            self._logger.error(msg, *args)

    def exception(self, msg, *args):
        """Log exception with traceback."""
        if self._logger:
            self._logger.exception(msg, *args)


# =============================================================================
# LISTENER INTERFACE
# =============================================================================

class TuyaListener(ABC):
    """Abstract base class for device status listeners."""

    @abstractmethod
    def status_updated(self, status: Dict[str, Any]) -> None:
        """Called when device status is updated.

        Args:
            status: Dictionary of data points {dp_id: value}
        """
        pass

    @abstractmethod
    def disconnected(self) -> None:
        """Called when connection to device is lost."""
        pass


class EmptyListener(TuyaListener):
    """Default listener that does nothing."""

    def status_updated(self, status: Dict[str, Any]) -> None:
        pass

    def disconnected(self) -> None:
        pass


# =============================================================================
# MESSAGE DISPATCHER
# =============================================================================

class MessageDispatcher:
    """Buffers incoming data and dispatches messages to waiting handlers."""

    # Special sequence numbers for async responses
    HEARTBEAT_SEQNO = -100
    RESET_SEQNO = -101
    SESS_KEY_SEQNO = -102

    def __init__(
        self,
        device_id: str,
        protocol_version: float,
        device_key: bytes,
        status_callback: Callable[[TuyaMessage], None],
        enable_debug: bool = False
    ):
        """Initialize dispatcher.

        Args:
            device_id: Device ID for logging
            protocol_version: Protocol version
            device_key: Device local key
            status_callback: Callback for status update messages
            enable_debug: Enable debug logging
        """
        self.buffer = b""
        self.listeners: Dict[int, Any] = {}
        self.protocol_version = protocol_version
        self.device_key = device_key
        self.session_key: Optional[bytes] = None
        self.status_callback = status_callback
        self.enable_debug = enable_debug

        self._logger = TuyaLoggingAdapter(_LOGGER, {"device_id": device_id})

    def debug(self, msg: str, *args) -> None:
        """Log debug message if enabled."""
        if self.enable_debug:
            self._logger.debug(msg, *args)

    def warning(self, msg: str, *args) -> None:
        """Log warning message."""
        self._logger.warning(msg, *args)

    def set_session_key(self, key: bytes) -> None:
        """Set session key for decryption."""
        self.session_key = key

    def abort(self) -> None:
        """Abort all waiting listeners."""
        for seqno, item in list(self.listeners.items()):
            if isinstance(item, asyncio.Semaphore):
                self.listeners[seqno] = None
                item.release()

    async def wait_for(self, seqno: int, cmd: int, timeout: float = DEFAULT_TIMEOUT) -> Optional[TuyaMessage]:
        """Wait for response with given sequence number.

        Args:
            seqno: Sequence number to wait for
            cmd: Command type (for logging)
            timeout: Timeout in seconds

        Returns:
            TuyaMessage or None if aborted

        Raises:
            asyncio.TimeoutError: If timeout expires
        """
        if seqno in self.listeners:
            raise RuntimeError(f"Listener already exists for seqno {seqno}")

        self.debug("Waiting for seqno %d (cmd %d)", seqno, cmd)
        self.listeners[seqno] = asyncio.Semaphore(0)

        try:
            await asyncio.wait_for(self.listeners[seqno].acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.debug("Timeout waiting for seqno %d", seqno)
            del self.listeners[seqno]
            raise

        result = self.listeners.pop(seqno)
        return result if isinstance(result, TuyaMessage) else None

    def add_data(self, data: bytes) -> None:
        """Add received data to buffer and process messages."""
        self.buffer += data
        self._process_buffer()

    def _process_buffer(self) -> None:
        """Process buffered data and dispatch complete messages."""
        while self.buffer:
            # Determine header size based on prefix
            if self.buffer[:4] == b"\x00\x00\x66\x99":
                header_size = HEADER_SIZE_6699
            else:
                header_size = HEADER_SIZE_55AA

            # Need at least header to continue
            if len(self.buffer) < header_size:
                break

            # Parse header
            try:
                header = parse_header(self.buffer)
            except DecodeError as e:
                self.warning("Failed to parse header: %s, clearing buffer", e)
                self.buffer = b""
                break

            # Need complete message
            if len(self.buffer) < header.total_length:
                break

            # Determine decryption key
            # Session negotiation always uses device key
            if header.cmd in SESSION_KEY_CMDS:
                key = self.device_key
            else:
                key = self.session_key if self.session_key else self.device_key

            # Unpack message
            try:
                msg = unpack_message(
                    self.buffer,
                    key=key,
                    protocol_version=self.protocol_version,
                    header=header
                )
                self.buffer = self.buffer[header.total_length:]
                self._dispatch(msg)
            except DecodeError as e:
                self.warning("Failed to unpack message: %s", e)
                self.buffer = b""
                break

    def _dispatch(self, msg: TuyaMessage) -> None:
        """Dispatch message to appropriate handler."""
        self.debug("Dispatching msg: cmd=%d seqno=%d retcode=%d payload_len=%d",
                   msg.cmd, msg.seqno, msg.retcode, len(msg.payload))

        # Check if someone is waiting for this seqno
        if msg.seqno in self.listeners:
            sem = self.listeners[msg.seqno]
            if isinstance(sem, asyncio.Semaphore):
                self.listeners[msg.seqno] = msg
                sem.release()
            return

        # Handle special message types
        if msg.cmd == CMD_HEART_BEAT:
            self._dispatch_special(self.HEARTBEAT_SEQNO, msg)
        elif msg.cmd == CMD_SESS_KEY_NEG_RESP:
            self._dispatch_special(self.SESS_KEY_SEQNO, msg)
        elif msg.cmd in (CMD_UPDATE_DPS, CMD_STATUS):
            # Check for reset listener first
            if self.RESET_SEQNO in self.listeners:
                self._dispatch_special(self.RESET_SEQNO, msg)
            elif msg.cmd == CMD_STATUS:
                # Unsolicited status update
                self.status_callback(msg)
        elif msg.cmd == CMD_CONTROL_NEW:
            self.debug("ACK for cmd %d", msg.cmd)
        else:
            self.debug("Unhandled message: cmd=%d seqno=%d", msg.cmd, msg.seqno)

    def _dispatch_special(self, special_seqno: int, msg: TuyaMessage) -> None:
        """Dispatch to special sequence number listener."""
        if special_seqno in self.listeners:
            sem = self.listeners[special_seqno]
            if isinstance(sem, asyncio.Semaphore):
                self.listeners[special_seqno] = msg
                sem.release()


# =============================================================================
# TUYA PROTOCOL (asyncio.Protocol implementation)
# =============================================================================

class TuyaProtocol(asyncio.Protocol):
    """Asyncio protocol implementation for Tuya devices."""

    def __init__(
        self,
        device_id: str,
        local_key: str,
        protocol_version: float,
        enable_debug: bool,
        on_connected: asyncio.Future,
        listener: TuyaListener
    ):
        """Initialize protocol.

        Args:
            device_id: Device ID
            local_key: Device local key
            protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
            enable_debug: Enable debug logging
            on_connected: Future to set when connected
            listener: Status listener
        """
        self.device_id = device_id
        self.device_key = local_key.encode("latin1")
        self.session_key: Optional[bytes] = None
        self.protocol_version = protocol_version
        self.enable_debug = enable_debug

        self._logger = TuyaLoggingAdapter(_LOGGER, {"device_id": device_id})
        self.transport: Optional[asyncio.Transport] = None
        self.on_connected = on_connected
        self.listener = weakref.ref(listener)

        # Sequence number
        self.seqno = 1

        # Device type affects payload format
        self._set_device_type()

        # DPS tracking
        self.dps_cache: Dict[str, Any] = {}
        self.dps_to_request: Dict[str, None] = {}

        # Heartbeat task
        self.heartbeater: Optional[asyncio.Task] = None

        # Session key negotiation
        self.local_nonce = os.urandom(16)
        self.remote_nonce: Optional[bytes] = None

        # Message dispatcher
        self.dispatcher = MessageDispatcher(
            device_id=device_id,
            protocol_version=protocol_version,
            device_key=self.device_key,
            status_callback=self._handle_status_update,
            enable_debug=enable_debug
        )

    def _set_device_type(self) -> None:
        """Set device type based on protocol version."""
        if self.protocol_version >= 3.5:
            self.device_type = DEVICE_TYPE_V35
        elif self.protocol_version >= 3.4:
            self.device_type = DEVICE_TYPE_V34
        elif self.protocol_version == 3.2:
            self.device_type = DEVICE_TYPE_0D
        else:
            self.device_type = DEVICE_TYPE_0A

    def debug(self, msg: str, *args) -> None:
        """Log debug if enabled."""
        if self.enable_debug:
            self._logger.debug(msg, *args)

    # =========================================================================
    # asyncio.Protocol interface
    # =========================================================================

    def connection_made(self, transport: asyncio.Transport) -> None:
        """Called when connection is established."""
        self.transport = transport
        self.debug("Connection established")
        self.on_connected.set_result(True)

    def data_received(self, data: bytes) -> None:
        """Called when data is received."""
        self.dispatcher.add_data(data)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when connection is lost."""
        self.debug("Connection lost: %s", exc)
        self.session_key = None
        self.dispatcher.session_key = None

        listener = self.listener()
        if listener:
            try:
                listener.disconnected()
            except Exception:
                self._logger.exception("Error in disconnected callback")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def close(self) -> None:
        """Close connection and cleanup."""
        self.debug("Closing connection")

        # Cancel heartbeat
        if self.heartbeater:
            self.heartbeater.cancel()
            try:
                await self.heartbeater
            except asyncio.CancelledError:
                pass
            self.heartbeater = None

        # Abort pending listeners
        self.dispatcher.abort()

        # Close transport
        if self.transport:
            self.transport.close()
            self.transport = None

        # Clear session key
        self.session_key = None
        self.dispatcher.session_key = None

    def start_heartbeat(self) -> None:
        """Start heartbeat loop."""
        if self.heartbeater:
            return

        async def heartbeat_loop():
            self.debug("Heartbeat loop started")
            try:
                while True:
                    await self.heartbeat()
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                self.debug("Heartbeat loop cancelled")
                raise
            except asyncio.TimeoutError:
                self.debug("Heartbeat timeout, disconnecting")
            except Exception as e:
                self._logger.exception("Heartbeat error: %s", e)

            # Disconnect on error
            if self.transport:
                self.transport.close()

        loop = asyncio.get_running_loop()
        self.heartbeater = loop.create_task(heartbeat_loop())

    async def heartbeat(self) -> Optional[Dict]:
        """Send heartbeat."""
        return await self.exchange(CMD_HEART_BEAT)

    async def status(self) -> Optional[Dict]:
        """Query device status."""
        status = await self.exchange(CMD_DP_QUERY)
        if status and "dps" in status:
            self.dps_cache.update(status["dps"])
        return status

    async def set_dp(self, value: Any, dp_index: int) -> Optional[Dict]:
        """Set single data point value."""
        return await self.exchange(CMD_CONTROL, {str(dp_index): value})

    async def set_dps(self, dps: Dict[str, Any]) -> Optional[Dict]:
        """Set multiple data point values."""
        return await self.exchange(CMD_CONTROL, dps)

    async def update_dps(self, dps: Optional[list] = None) -> bool:
        """Request device to update specific DPS values (Protocol 3.2+)."""
        if self.protocol_version < 3.2:
            return True

        if dps is None:
            if not self.dps_cache:
                await self.detect_available_dps()
            if self.dps_cache:
                dps = [int(dp) for dp in self.dps_cache if int(dp) in UPDATE_DPS_WHITELIST]

        if dps:
            payload = self._generate_payload(CMD_UPDATE_DPS, dps)
            data = self._encode_message(payload)
            if self.transport:
                self.transport.write(data)

        return True

    async def reset(self, dpIds: Optional[list] = None) -> bool:
        """Send reset/update command (Protocol 3.3+).

        Args:
            dpIds: List of DP IDs to reset (optional)

        Returns:
            True on success
        """
        if self.protocol_version >= 3.3:
            self.device_type = DEVICE_TYPE_0A
            self.debug("Reset: switching to device_type %s", self.device_type)
            return await self.exchange(CMD_UPDATE_DPS, dpIds)
        return True

    async def detect_available_dps(self, retry_count: int = 3) -> Dict[str, Any]:
        """Detect available data points by querying ranges."""
        self.dps_cache = {}
        ranges = [(2, 11), (11, 21), (21, 31), (100, 111)]

        # Wake device with heartbeat
        for attempt in range(retry_count):
            try:
                await self.heartbeat()
                await asyncio.sleep(0.5)
                break
            except Exception as e:
                self.debug("Heartbeat attempt %d failed: %s", attempt + 1, e)
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)

        for dps_range in ranges:
            self.dps_to_request = {"1": None}
            for i in range(*dps_range):
                self.dps_to_request[str(i)] = None

            for attempt in range(retry_count):
                try:
                    data = await self.status()
                    if data and isinstance(data, dict) and "dps" in data:
                        self.dps_cache.update(data["dps"])
                        self.debug("Range %s: found DPS %s", dps_range, list(data["dps"].keys()))
                    break
                except Exception as e:
                    self.debug("Status attempt %d for range %s failed: %s", attempt + 1, dps_range, e)
                    if attempt < retry_count - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))

            # Early exit for type_0a devices
            if self.device_type == DEVICE_TYPE_0A and self.dps_cache:
                break

        self.debug("Detected DPS: %s", self.dps_cache)
        return self.dps_cache

    def add_dps_to_request(self, dp_indices) -> None:
        """Add DPS indices to request list."""
        if isinstance(dp_indices, int):
            self.dps_to_request[str(dp_indices)] = None
        else:
            for i in dp_indices:
                self.dps_to_request[str(i)] = None

    # =========================================================================
    # EXCHANGE (send command and wait for response)
    # =========================================================================

    async def exchange(self, command: int, dps: Optional[Dict] = None) -> Optional[Dict]:
        """Send command and wait for response.

        Args:
            command: Command type
            dps: Data points to send (optional)

        Returns:
            Parsed response or None
        """
        # Negotiate session key for 3.4+ if needed
        if self.protocol_version >= 3.4 and self.session_key is None:
            self.debug("Negotiating session key for v%.1f", self.protocol_version)
            success = await self._negotiate_session_key()
            if not success:
                self._logger.error("Session key negotiation failed")
                return None

        self.debug("Sending command %d (device_type=%s)", command, self.device_type)

        # Generate and encode payload
        payload = self._generate_payload(command, dps)
        data = self._encode_message(payload)

        if not self.transport:
            self._logger.error("No transport available")
            return None

        # Determine sequence number to wait for
        if payload.cmd == CMD_HEART_BEAT:
            wait_seqno = MessageDispatcher.HEARTBEAT_SEQNO
        elif payload.cmd == CMD_UPDATE_DPS:
            wait_seqno = MessageDispatcher.RESET_SEQNO
        else:
            wait_seqno = self.seqno - 1  # seqno was incremented in _encode_message

        # Send and wait
        self.transport.write(data)
        msg = await self.dispatcher.wait_for(wait_seqno, payload.cmd)

        if msg is None:
            return None

        # ACK responses have empty payload
        if payload.cmd in (CMD_HEART_BEAT, CMD_CONTROL, CMD_CONTROL_NEW) and len(msg.payload) == 0:
            self.debug("ACK received for cmd %d", payload.cmd)
            return None

        return self._decode_payload(msg.payload)

    async def _exchange_quick(self, cmd: int, payload: bytes, recv_retries: int = 2) -> Optional[TuyaMessage]:
        """Send message and wait for response without decoding.

        Used for session key negotiation.
        """
        if not self.transport:
            return None

        # Encode message
        key = self.device_key
        data = pack_message(
            seqno=self.seqno,
            cmd=cmd,
            payload=payload,
            key=key,
            protocol_version=self.protocol_version,
            encrypt=True
        )
        self.seqno += 1

        self.transport.write(data)

        while recv_retries > 0:
            try:
                msg = await self.dispatcher.wait_for(
                    MessageDispatcher.SESS_KEY_SEQNO, cmd, timeout=5
                )
                if msg and len(msg.payload) > 0:
                    # Update seqno from response
                    if msg.seqno > 0:
                        self.seqno = msg.seqno + 1
                    return msg
            except asyncio.TimeoutError:
                pass
            recv_retries -= 1

        return None

    # =========================================================================
    # SESSION KEY NEGOTIATION (Protocol 3.4+)
    # =========================================================================

    async def _negotiate_session_key(self) -> bool:
        """Negotiate session key with device.

        Protocol 3.4/3.5 three-way handshake:
        1. Client sends local_nonce
        2. Device responds with remote_nonce + HMAC(local_nonce)
        3. Client sends HMAC(remote_nonce)

        Session key = encrypt(XOR(local_nonce, remote_nonce))[:16]
        """
        self.debug("Starting session key negotiation")
        self.local_nonce = os.urandom(16)

        # Step 1: Send local nonce
        response = await self._exchange_quick(CMD_SESS_KEY_NEG_START, self.local_nonce)

        if not response:
            self.debug("No response to SESS_KEY_NEG_START")
            return False

        if response.cmd != CMD_SESS_KEY_NEG_RESP:
            self.debug("Unexpected response cmd: %d", response.cmd)
            return False

        payload = response.payload
        self.debug("SESS_KEY_NEG_RESP payload: %d bytes", len(payload))

        # For Protocol 3.5 with 6699 format, payload is already decrypted by GCM
        # For Protocol 3.4 with 55AA format, we need to decrypt with ECB
        if self.protocol_version < 3.5 or response.prefix != PREFIX_6699:
            try:
                cipher = AESCipher(self.device_key)
                payload = cipher.decrypt_ecb(payload, unpad=True)
            except Exception as e:
                self.debug("Failed to decrypt SESS_KEY_NEG_RESP: %s", e)
                return False

        # Skip retcode if present
        if len(payload) >= 4 and payload[:4] == b'\x00\x00\x00\x00':
            payload = payload[4:]

        if len(payload) < 48:
            self.debug("SESS_KEY_NEG_RESP payload too short: %d", len(payload))
            return False

        # Extract remote nonce and HMAC
        self.remote_nonce = payload[:16]
        received_hmac = payload[16:48]

        # Verify HMAC of our local nonce
        expected_hmac = hmac.new(self.device_key, self.local_nonce, sha256).digest()
        if not hmac.compare_digest(expected_hmac, received_hmac):
            self.debug("HMAC verification failed (may be ok for some devices)")
            # Continue anyway - some devices don't implement HMAC correctly

        # Calculate session key
        # XOR nonces
        xor_result = bytes(a ^ b for a, b in zip(self.local_nonce, self.remote_nonce))
        self.debug("Nonce XOR: %s", xor_result.hex())

        if self.protocol_version >= 3.5:
            # Protocol 3.5: AES-GCM encrypt, take ciphertext only
            # IV = first 12 bytes of local_nonce
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

            iv = self.local_nonce[:12]
            gcm_cipher = Cipher(
                algorithms.AES(self.device_key),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = gcm_cipher.encryptor()
            encrypted = encryptor.update(xor_result) + encryptor.finalize()
            session_key = encrypted[:16]

            # TinyTuya quirk: if first byte is 0x00, negotiation should be retried
            if session_key[0] == 0x00:
                self.debug("Session key starts with 0x00 - may need retry")
                # Don't fail, but log warning
        else:
            # Protocol 3.4: AES-ECB encrypt
            cipher = AESCipher(self.device_key)
            encrypted = cipher.encrypt_ecb(xor_result, pad=False)
            session_key = encrypted[:16]

        self.debug("Session key: %s", session_key.hex())

        # Step 3: Send HMAC of remote nonce
        response_hmac = hmac.new(self.device_key, self.remote_nonce, sha256).digest()
        await self._exchange_quick(CMD_SESS_KEY_NEG_FINISH, response_hmac)

        # Store session key
        self.session_key = session_key
        self.dispatcher.set_session_key(session_key)

        self.debug("Session key negotiation complete")
        return True

    # =========================================================================
    # PAYLOAD ENCODING/DECODING
    # =========================================================================

    def _encode_message(self, msg: MessagePayload) -> bytes:
        """Encode message for sending."""
        payload = msg.payload

        # Get encryption key
        key = self.session_key if self.session_key else self.device_key

        # Add version header for certain commands and protocols
        if msg.cmd not in NO_PROTOCOL_HEADER_CMDS:
            if self.protocol_version >= 3.5:
                version_header = VERSION_35 + PROTOCOL_3X_HEADER_PAD
                payload = version_header + payload
            elif self.protocol_version >= 3.4:
                version_header = VERSION_34 + PROTOCOL_3X_HEADER_PAD
                payload = version_header + payload
            elif self.protocol_version >= 3.3:
                version_header = VERSION_33 + PROTOCOL_3X_HEADER_PAD
                payload = version_header + payload

        # For Protocol 3.1-3.4, encrypt payload here
        # For Protocol 3.5, encryption happens in pack_message (GCM)
        if self.protocol_version < 3.5:
            if self.protocol_version >= 3.4:
                # v3.4: encrypt everything
                cipher = AESCipher(key)
                payload = cipher.encrypt_ecb(payload, pad=True)
            elif self.protocol_version >= 3.2:
                # v3.2-3.3: encrypt payload, add header after
                cipher = AESCipher(key)
                encrypted_payload = cipher.encrypt_ecb(msg.payload, pad=True)
                if msg.cmd not in NO_PROTOCOL_HEADER_CMDS:
                    version_header = VERSION_33 + PROTOCOL_3X_HEADER_PAD
                    payload = version_header + encrypted_payload
                else:
                    payload = encrypted_payload
            elif msg.cmd == CMD_CONTROL:
                # v3.1: only encrypt CONTROL commands with MD5 prefix
                cipher = AESCipher(key)
                encrypted = cipher.encrypt_ecb_base64(msg.payload, pad=True)
                from hashlib import md5
                pre_md5 = b"data=" + encrypted + b"||lpv=" + VERSION_31 + b"||" + key
                md5_hash = md5(pre_md5).hexdigest()
                payload = VERSION_31 + md5_hash[8:24].encode("latin1") + encrypted

        # Pack message
        seqno = self.seqno
        self.seqno += 1

        return pack_message(
            seqno=seqno,
            cmd=msg.cmd,
            payload=payload,
            key=key,
            protocol_version=self.protocol_version,
            encrypt=(self.protocol_version >= 3.5)  # GCM encryption in pack_message
        )

    def _decode_payload(self, payload: bytes) -> Optional[Dict]:
        """Decode payload from device response."""
        key = self.session_key if self.session_key else self.device_key

        # Protocol 3.4: payload is encrypted
        if self.protocol_version == 3.4:
            try:
                cipher = AESCipher(key)
                payload = cipher.decrypt_ecb(payload, unpad=True)
            except Exception as e:
                self.debug("Failed to decrypt v3.4 payload: %s", e)
                return self._error_json(ERR_PAYLOAD)

        # Remove version header if present
        version_bytes = str(self.protocol_version).encode("latin1")[:3]
        if payload.startswith(VERSION_31):
            # v3.1 encrypted format
            payload = payload[len(VERSION_31):]
            cipher = AESCipher(key)
            payload = cipher.decrypt_ecb_base64(payload[16:], unpad=True)
        elif payload.startswith(version_bytes):
            # v3.x header present
            payload = payload[len(version_bytes) + len(PROTOCOL_3X_HEADER_PAD):]

        # v3.2/3.3: decrypt if not already done
        if self.protocol_version in (3.2, 3.3) and not payload.startswith(b"{"):
            try:
                cipher = AESCipher(key)
                payload = cipher.decrypt_ecb(payload, unpad=True)
            except Exception as e:
                self.debug("Failed to decrypt v3.x payload: %s", e)
                return self._error_json(ERR_PAYLOAD)

        # Decode to string
        if isinstance(payload, bytes):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                self.debug("Failed to decode payload as UTF-8")
                return self._error_json(ERR_PAYLOAD)

        # Check for "data unvalid" error (type_0d device)
        if "data unvalid" in payload:
            self.device_type = DEVICE_TYPE_0D
            self.debug("Detected type_0d device")
            return None

        # Parse JSON
        self.debug("Decoded payload: %s", payload)
        try:
            json_payload = json.loads(payload)
        except json.JSONDecodeError as e:
            self.debug("Failed to parse JSON: %s", e)
            raise DecodeError(f"Invalid JSON: {e}")

        # Handle nested dps structure (v3.4+)
        if "dps" not in json_payload and "data" in json_payload:
            if "dps" in json_payload.get("data", {}):
                json_payload["dps"] = json_payload["data"]["dps"]

        return json_payload

    def _generate_payload(self, command: int, data: Optional[Dict] = None) -> MessagePayload:
        """Generate command payload."""
        json_data = None
        command_override = None

        # Get payload template
        if command in PAYLOAD_DICT.get(self.device_type, {}):
            template = PAYLOAD_DICT[self.device_type][command]
            json_data = template.get("command", {}).copy() if "command" in template else None
            command_override = template.get("command_override")

        # Fallback to type_0a template
        if json_data is None and self.device_type != DEVICE_TYPE_0A:
            if command in PAYLOAD_DICT.get(DEVICE_TYPE_0A, {}):
                template = PAYLOAD_DICT[DEVICE_TYPE_0A][command]
                json_data = template.get("command", {}).copy() if "command" in template else None
                if command_override is None:
                    command_override = template.get("command_override")

        # Default payload
        if json_data is None:
            json_data = {"gwId": "", "devId": "", "uid": "", "t": ""}

        # Fill in device info
        if "gwId" in json_data:
            json_data["gwId"] = self.device_id
        if "devId" in json_data:
            json_data["devId"] = self.device_id
        if "uid" in json_data:
            json_data["uid"] = self.device_id
        if "t" in json_data:
            if json_data["t"] == "int":
                json_data["t"] = int(time.time())
            else:
                json_data["t"] = str(int(time.time()))

        # Add data points
        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            elif "data" in json_data:
                json_data["data"] = {"dps": data}
            else:
                json_data["dps"] = data
        elif self.device_type == DEVICE_TYPE_0D and command == CMD_DP_QUERY:
            json_data["dps"] = self.dps_to_request

        # Convert to JSON bytes
        payload_str = json.dumps(json_data, separators=(",", ":"))
        payload = payload_str.encode("utf-8")

        self.debug("Payload: %s", payload_str)

        return MessagePayload(
            cmd=command_override if command_override else command,
            payload=payload
        )

    def _error_json(self, code: int) -> Dict:
        """Generate error response."""
        return {
            "Error": ERROR_MESSAGES.get(code, "Unknown Error"),
            "Err": str(code)
        }

    def _handle_status_update(self, msg: TuyaMessage) -> None:
        """Handle unsolicited status update."""
        if msg.seqno > 0:
            self.seqno = msg.seqno + 1

        try:
            decoded = self._decode_payload(msg.payload)
            if decoded and "dps" in decoded:
                self.dps_cache.update(decoded["dps"])

                listener = self.listener()
                if listener:
                    listener.status_updated(self.dps_cache)
        except Exception as e:
            self.debug("Failed to handle status update: %s", e)


# =============================================================================
# CONNECTION FUNCTION
# =============================================================================

async def connect(
    address: str,
    device_id: str,
    local_key: str,
    protocol_version: float,
    enable_debug: bool = False,
    listener: Optional[TuyaListener] = None,
    port: int = 6668,
    timeout: float = DEFAULT_TIMEOUT
) -> TuyaProtocol:
    """Connect to a Tuya device.

    Args:
        address: Device IP address
        device_id: Device ID
        local_key: Device local key
        protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
        enable_debug: Enable debug logging
        listener: Status listener (optional)
        port: Device port (default 6668)
        timeout: Connection timeout in seconds

    Returns:
        Connected TuyaProtocol instance
    """
    loop = asyncio.get_running_loop()
    on_connected = loop.create_future()

    _, protocol = await loop.create_connection(
        lambda: TuyaProtocol(
            device_id=device_id,
            local_key=local_key,
            protocol_version=protocol_version,
            enable_debug=enable_debug,
            on_connected=on_connected,
            listener=listener or EmptyListener()
        ),
        host=address,
        port=port
    )

    await asyncio.wait_for(on_connected, timeout=timeout)
    return protocol
