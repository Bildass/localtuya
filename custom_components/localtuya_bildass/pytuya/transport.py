# PyTuya Transport Layer
# -*- coding: utf-8 -*-
"""
Async transport layer for Tuya device communication.

Implements asyncio.Protocol for TCP communication with Tuya devices.
Handles session key negotiation, heartbeat, and message dispatching.
"""

import asyncio
import logging
import time
import weakref
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

from .cipher import AESCipher
from .constants import (
    CONTROL,
    CONTROL_NEW,
    DP_QUERY,
    DP_QUERY_NEW,
    DecodeError,
    HEART_BEAT,
    HEARTBEAT_INTERVAL,
    PAYLOAD_DICT,
    PREFIX_6699_VALUE,
    PROTOCOL_33_HEADER,
    PROTOCOL_34_HEADER,
    PROTOCOL_35_HEADER,
    SESS_KEY_NEG_FINISH,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_START,
    SessionKeyError,
    SessionKeyInvalidError,
    STATUS,
    UPDATE_DPS_WHITELIST,
    UPDATEDPS,
)
from .message import (
    MessagePayload,
    TuyaMessage,
    create_heartbeat_payload,
    parse_status_response,
)
from .protocol import (
    extract_messages,
    pack_message,
    parse_header,
    unpack_message,
)
from .session import SessionKeyNegotiator

_LOGGER = logging.getLogger(__name__)

# Sequence number for session key negotiation
SESS_KEY_SEQNO = -102

# Default timeouts
DEFAULT_TIMEOUT = 5.0
RECV_RETRIES = 2


# =============================================================================
# Listener Interface
# =============================================================================

class TuyaListener(ABC):
    """
    Abstract base class for Tuya device event listeners.

    Implement this class to receive status updates and disconnection events.
    """

    @abstractmethod
    def status_updated(self, status: Dict[str, Any]) -> None:
        """
        Called when device status is updated.

        Args:
            status: Dictionary containing DPS values
        """
        pass

    @abstractmethod
    def disconnected(self) -> None:
        """Called when connection to device is lost."""
        pass


class EmptyListener(TuyaListener):
    """No-op listener for when no listener is needed."""

    def status_updated(self, status: Dict[str, Any]) -> None:
        pass

    def disconnected(self) -> None:
        pass


# =============================================================================
# Message Dispatcher
# =============================================================================

class MessageDispatcher:
    """
    Handles dispatching of incoming messages to waiting coroutines.

    Manages sequence numbers and provides async wait mechanism.
    """

    def __init__(
        self,
        dev_id: str,
        listener: TuyaListener,
        protocol_version: float,
        local_key: bytes,
        enable_debug: bool = False,
    ):
        self.dev_id = dev_id
        self.listener = listener
        self.version = protocol_version
        self.local_key = local_key
        self.enable_debug = enable_debug

        self._buffer = b""
        self._pending: Dict[int, asyncio.Future] = {}
        self._abort = False

    def debug(self, msg: str, *args):
        """Log debug message with device ID prefix."""
        if self.enable_debug:
            prefix = f"[{self.dev_id[:3]}...{self.dev_id[-3:]}]"
            _LOGGER.debug(f"{prefix} {msg}", *args)

    def abort(self):
        """Abort all pending waits."""
        self._abort = True
        for seqno, future in self._pending.items():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def wait_for(
        self,
        seqno: int,
        cmd: int,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Optional[TuyaMessage]:
        """
        Wait for a message with specific sequence number.

        Args:
            seqno: Sequence number to wait for
            cmd: Expected command type
            timeout: Timeout in seconds

        Returns:
            TuyaMessage if received, None on timeout
        """
        if self._abort:
            return None

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending[seqno] = future

        try:
            result = await asyncio.wait_for(future, timeout)
            return result
        except asyncio.TimeoutError:
            self.debug("Timeout waiting for seqno %d (cmd %d)", seqno, cmd)
            return None
        except asyncio.CancelledError:
            return None
        finally:
            self._pending.pop(seqno, None)

    def add_data(self, data: bytes):
        """
        Add received data to buffer and process complete messages.

        Args:
            data: Raw bytes received from transport
        """
        self._buffer += data

        # Extract and process complete messages
        messages, self._buffer = extract_messages(self._buffer)

        for msg_data in messages:
            try:
                self._process_message(msg_data)
            except Exception as ex:
                _LOGGER.warning("Error processing message: %s", ex)

    def _process_message(self, data: bytes):
        """Process a single complete message."""
        try:
            header = parse_header(data)

            # Determine key based on message type
            if header.cmd in (SESS_KEY_NEG_START, SESS_KEY_NEG_RESP, SESS_KEY_NEG_FINISH):
                # Session negotiation uses original device key
                key = self.local_key
            else:
                # Normal messages use session key (which is local_key after negotiation)
                key = self.local_key

            msg = unpack_message(data, self.version, key, header)

            self.debug(
                "Received: cmd=%d, seqno=%d, retcode=%d, payload_len=%d",
                msg.cmd, msg.seqno, msg.retcode, len(msg.payload)
            )

            # Dispatch to waiting coroutine or listener
            self._dispatch(msg)

        except DecodeError as ex:
            self.debug("Failed to decode message: %s", ex)

    def _dispatch(self, msg: TuyaMessage):
        """Dispatch message to appropriate handler."""
        # Check for pending wait
        if msg.seqno in self._pending:
            future = self._pending[msg.seqno]
            if not future.done():
                future.set_result(msg)
            return

        # Check for session key negotiation response
        if SESS_KEY_SEQNO in self._pending and msg.cmd == SESS_KEY_NEG_RESP:
            future = self._pending[SESS_KEY_SEQNO]
            if not future.done():
                future.set_result(msg)
            return

        # Handle unsolicited status updates
        if msg.cmd in (STATUS, DP_QUERY, DP_QUERY_NEW, CONTROL, CONTROL_NEW):
            status = parse_status_response(msg.payload)
            if status:
                self.listener.status_updated(status)


# =============================================================================
# Tuya Protocol Implementation
# =============================================================================

class TuyaProtocol(asyncio.Protocol):
    """
    Async protocol implementation for Tuya device communication.

    Handles:
    - TCP connection management
    - Session key negotiation (Protocol 3.4+)
    - Heartbeat mechanism
    - Message encoding/decoding
    - Command exchange
    """

    def __init__(
        self,
        dev_id: str,
        local_key: str,
        protocol_version: float,
        enable_debug: bool,
        on_connected: Callable,
        listener: Optional[TuyaListener] = None,
    ):
        """
        Initialize protocol handler.

        Args:
            dev_id: Device ID
            local_key: Device local key (16 characters)
            protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
            enable_debug: Enable debug logging
            on_connected: Callback when connection is established
            listener: Event listener for status updates
        """
        self.dev_id = dev_id
        self.real_local_key = local_key.encode('utf-8') if isinstance(local_key, str) else local_key
        self.local_key = self.real_local_key
        self.version = protocol_version
        self.enable_debug = enable_debug
        self._on_connected = on_connected
        self.listener = listener or EmptyListener()

        # Transport and dispatcher
        self.transport: Optional[asyncio.Transport] = None
        self.dispatcher = MessageDispatcher(
            dev_id, self.listener, protocol_version, self.local_key, enable_debug
        )

        # Session state
        self.session_negotiator: Optional[SessionKeyNegotiator] = None
        self.session_negotiated = False

        # Heartbeat
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._seqno = 0

        # Device type (some devices need different commands)
        self.dev_type = "type_0a"

        # DPS tracking
        self.dps_to_request: Dict[str, Any] = {}
        self.dps_cache: Dict[str, Any] = {}

    def debug(self, msg: str, *args):
        """Log debug message with device ID prefix."""
        if self.enable_debug:
            prefix = f"[{self.dev_id[:3]}...{self.dev_id[-3:]}]"
            _LOGGER.debug(f"{prefix} {msg}", *args)

    # =========================================================================
    # Protocol Version Management
    # =========================================================================

    def set_version(self, version: float):
        """Set protocol version."""
        self.version = version
        self.dispatcher.version = version

    # =========================================================================
    # asyncio.Protocol Implementation
    # =========================================================================

    def connection_made(self, transport: asyncio.Transport):
        """Called when connection is established."""
        self.transport = transport
        self.debug("Connection established")

        # Reset session state
        self.local_key = self.real_local_key
        self.dispatcher.local_key = self.real_local_key
        self.session_negotiated = False

        # Notify callback
        if self._on_connected:
            self._on_connected()

    def connection_lost(self, exc: Optional[Exception]):
        """Called when connection is lost."""
        self.debug("Connection lost: %s", exc)
        self.dispatcher.abort()

        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        # Notify listener
        self.listener.disconnected()

    def data_received(self, data: bytes):
        """Called when data is received."""
        self.debug("Received %d bytes", len(data))
        self.dispatcher.add_data(data)

    # =========================================================================
    # Heartbeat Management
    # =========================================================================

    def start_heartbeat(self):
        """Start the heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if self.transport and not self.transport.is_closing():
                    await self.heartbeat()
        except asyncio.CancelledError:
            pass
        except Exception as ex:
            self.debug("Heartbeat error: %s", ex)

    async def heartbeat(self) -> Optional[TuyaMessage]:
        """Send heartbeat and wait for response."""
        payload = create_heartbeat_payload(self.dev_id)
        return await self.exchange(payload)

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def close(self):
        """Close the connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        if self.transport:
            self.transport.close()
            self.transport = None

    # =========================================================================
    # Message Exchange
    # =========================================================================

    def _next_seqno(self) -> int:
        """Get next sequence number."""
        self._seqno += 1
        return self._seqno

    async def exchange(
        self,
        msg: MessagePayload,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> Optional[TuyaMessage]:
        """
        Send a message and wait for response.

        Handles session key negotiation if needed.

        Args:
            msg: Message to send
            timeout: Response timeout in seconds

        Returns:
            TuyaMessage response, or None on timeout
        """
        # Negotiate session key if needed
        if self.version >= 3.4 and not self.session_negotiated:
            if self.local_key == self.real_local_key:
                success = await self._negotiate_session_key()
                if not success:
                    self.debug("Session key negotiation failed")
                    return None

        # Send message and wait for response
        seqno = self._next_seqno()
        return await self._exchange_impl(msg, seqno, timeout)

    async def _exchange_impl(
        self,
        msg: MessagePayload,
        seqno: int,
        timeout: float,
    ) -> Optional[TuyaMessage]:
        """Internal message exchange implementation."""
        # Encode and send message
        encoded = self._encode_message(msg, seqno)
        self.debug("Sending: cmd=%d, seqno=%d, %d bytes", msg.cmd, seqno, len(encoded))

        if not self.transport:
            self.debug("Transport not available")
            return None

        self.transport.write(encoded)

        # Wait for response
        return await self.dispatcher.wait_for(seqno, msg.cmd, timeout)

    def _encode_message(self, msg: MessagePayload, seqno: int) -> bytes:
        """Encode a message for sending."""
        # Prepare payload with protocol header if needed
        payload = self._prepare_payload(msg)
        msg_with_payload = MessagePayload(cmd=msg.cmd, payload=payload)

        # Encrypt and pack
        return pack_message(
            msg_with_payload,
            seqno,
            self.version,
            self.local_key,
        )

    def _prepare_payload(self, msg: MessagePayload) -> bytes:
        """Prepare payload with encryption and protocol header."""
        payload = msg.payload

        # Skip header for certain commands
        from .constants import NO_PROTOCOL_HEADER_CMDS
        if msg.cmd in NO_PROTOCOL_HEADER_CMDS:
            return payload

        # Add protocol version header
        if self.version >= 3.5:
            header = PROTOCOL_35_HEADER
        elif self.version >= 3.4:
            header = PROTOCOL_34_HEADER
        elif self.version >= 3.3:
            header = PROTOCOL_33_HEADER
        else:
            # Protocol 3.1 - no header for most commands
            return payload

        # Encrypt payload (for 3.4+, payload is encrypted before adding header)
        if self.version >= 3.4:
            cipher = AESCipher(self.local_key)
            if self.version >= 3.5:
                # GCM encryption is handled in pack_message
                return header + payload
            else:
                # ECB encryption
                encrypted = cipher.encrypt_ecb(payload)
                return header + encrypted

        return header + payload

    # =========================================================================
    # Session Key Negotiation
    # =========================================================================

    async def _negotiate_session_key(self) -> bool:
        """
        Perform session key negotiation.

        Returns:
            True if successful, False otherwise
        """
        self.debug("Starting session key negotiation (v%.1f)", self.version)

        # Create negotiator
        self.session_negotiator = SessionKeyNegotiator(
            self.real_local_key,
            self.version,
            strict_hmac=False,  # Some devices have broken HMAC
        )

        max_retries = SessionKeyNegotiator.MAX_RETRIES

        for attempt in range(max_retries):
            try:
                # Step 1: Send local nonce
                step1_msg = self.session_negotiator.create_step1_payload()
                encoded = pack_message(
                    step1_msg,
                    SESS_KEY_SEQNO,
                    self.version,
                    self.real_local_key,
                )

                self.debug("Sending SESS_KEY_NEG_START (attempt %d/%d)", attempt + 1, max_retries)
                self.transport.write(encoded)

                # Wait for response
                response = await self.dispatcher.wait_for(
                    SESS_KEY_SEQNO, SESS_KEY_NEG_RESP, DEFAULT_TIMEOUT
                )

                if not response:
                    self.debug("No response to SESS_KEY_NEG_START")
                    continue

                if response.cmd != SESS_KEY_NEG_RESP:
                    self.debug("Unexpected response cmd: %d", response.cmd)
                    continue

                # Step 2: Process response
                try:
                    self.session_negotiator.process_step2_response(response.payload)
                except Exception as ex:
                    self.debug("Failed to process step 2 response: %s", ex)
                    continue

                # Calculate session key
                try:
                    session_key = self.session_negotiator.calculate_session_key()
                except SessionKeyInvalidError as ex:
                    self.debug("Session key invalid, retrying: %s", ex)
                    self.session_negotiator.reset()
                    continue

                # Step 3: Send finish
                step3_msg = self.session_negotiator.create_step3_payload()
                encoded = pack_message(
                    step3_msg,
                    self._next_seqno(),
                    self.version,
                    self.real_local_key,
                )

                self.debug("Sending SESS_KEY_NEG_FINISH")
                self.transport.write(encoded)

                # Update keys
                self.local_key = session_key
                self.dispatcher.local_key = session_key
                self.session_negotiated = True

                self.debug("Session key negotiation success! Key: %s", session_key.hex())

                # For v3.5, send heartbeat to verify session key works
                if self.version >= 3.5:
                    self.debug("Sending verification heartbeat")
                    hb_response = await self.heartbeat()
                    if hb_response is None:
                        self.debug("Heartbeat failed after session negotiation")
                        # Don't fail - some devices just don't respond to first heartbeat
                    else:
                        self.debug("Heartbeat OK - session key verified")

                return True

            except SessionKeyError as ex:
                self.debug("Session key error: %s", ex)
                self.session_negotiator.reset()
                continue

        self.debug("Session key negotiation failed after %d attempts", max_retries)
        return False

    # =========================================================================
    # High-Level Commands
    # =========================================================================

    async def status(self) -> Optional[Dict[str, Any]]:
        """
        Query device status.

        Returns:
            Dictionary with 'dps' key containing DPS values, or None on error
        """
        from .message import create_dp_query_payload
        msg = create_dp_query_payload(self.dev_id, self.version)
        response = await self.exchange(msg)

        if response is None:
            return None

        return parse_status_response(response.payload)

    async def set_dp(self, value: Any, dp_index: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Set a datapoint value.

        Args:
            value: Value to set
            dp_index: Datapoint index

        Returns:
            Updated status, or None on error
        """
        from .message import create_control_payload
        dps = {str(dp_index): value}
        msg = create_control_payload(self.dev_id, dps, self.version)
        response = await self.exchange(msg)

        if response is None:
            return None

        return parse_status_response(response.payload)

    async def set_dps(self, dps: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Set multiple datapoint values at once.

        Args:
            dps: Dictionary mapping dp_index to value

        Returns:
            Updated status, or None on error
        """
        from .message import create_control_payload
        msg = create_control_payload(self.dev_id, dps, self.version)
        response = await self.exchange(msg)

        if response is None:
            return None

        return parse_status_response(response.payload)

    def add_dps_to_request(self, dp_indicies):
        """Add datapoint(s) to be included in requests."""
        if isinstance(dp_indicies, int):
            self.dps_to_request[str(dp_indicies)] = None
        elif isinstance(dp_indicies, dict):
            self.dps_to_request.update({str(k): v for k, v in dp_indicies.items()})
        else:
            self.dps_to_request.update({str(index): None for index in dp_indicies})

    async def reset(self, dpIds=None):
        """Send a reset message (3.3 only)."""
        if self.version == 3.3:
            self.dev_type = "type_0a"
            self.debug("reset switching to dev_type %s", self.dev_type)
            msg = MessagePayload(
                cmd=UPDATEDPS,
                payload=f'{{"dpId":{dpIds}}}'.encode('utf-8') if dpIds else b'{}'
            )
            response = await self.exchange(msg)
            return response is not None
        return True

    async def update_dps(self, dps=None):
        """
        Request device to update index.

        Args:
            dps: List of dps to update, default=detected&whitelisted
        """
        if self.version in [3.2, 3.3, 3.4, 3.5]:
            if dps is None:
                if not self.dps_cache:
                    detected = await self.detect_available_dps()
                    self.dps_cache.update(detected)
                if self.dps_cache:
                    dps = [int(dp) for dp in self.dps_cache]
                    # Filter to whitelist
                    dps = list(set(dps).intersection(set(UPDATE_DPS_WHITELIST)))

            self.debug("update_dps() entry (dps %s, dps_cache %s)", dps, self.dps_cache)

            if dps:
                msg = MessagePayload(
                    cmd=UPDATEDPS,
                    payload=f'{{"dpId":{dps}}}'.encode('utf-8')
                )
                try:
                    response = await self.exchange(msg, timeout=2.0)
                    if response:
                        result = parse_status_response(response.payload)
                        if result and "dps" in result:
                            self.dps_cache.update(result["dps"])
                except Exception as ex:
                    self.debug("update_dps failed: %s", ex)

    async def detect_available_dps(self) -> Dict[str, Any]:
        """
        Detect available datapoints.

        Sends queries to discover which DPS indices the device supports.

        Returns:
            Dictionary mapping DPS indices to their values
        """
        detected_dps = {}

        # First, try to wake up the device with heartbeat
        await self.heartbeat()

        # Query status
        status = await self.status()
        if status and "dps" in status:
            detected_dps.update(status["dps"])

        # Try additional DPS ranges
        dps_ranges = [
            list(range(1, 12)),
            list(range(11, 22)),
            list(range(21, 32)),
            list(range(100, 112)),
        ]

        for dps_range in dps_ranges:
            # Create UPDATEDPS payload
            msg = MessagePayload(
                cmd=UPDATEDPS,
                payload=f'{{"dpId":{dps_range}}}'.encode('utf-8')
            )

            try:
                response = await self.exchange(msg, timeout=2.0)
                if response:
                    result = parse_status_response(response.payload)
                    if result and "dps" in result:
                        detected_dps.update(result["dps"])
            except Exception:
                pass

        return detected_dps


# =============================================================================
# Connection Factory
# =============================================================================

async def connect(
    address: str,
    device_id: str,
    local_key: str,
    protocol_version: float = 3.3,
    enable_debug: bool = False,
    listener: Optional[TuyaListener] = None,
    port: int = 6668,
    timeout: float = 5.0,
) -> TuyaProtocol:
    """
    Connect to a Tuya device.

    Args:
        address: Device IP address
        device_id: Device ID
        local_key: Device local key
        protocol_version: Protocol version (3.1, 3.3, 3.4, 3.5)
        enable_debug: Enable debug logging
        listener: Event listener for status updates
        port: Device port (default 6668)
        timeout: Connection timeout

    Returns:
        Connected TuyaProtocol instance

    Raises:
        ConnectionError: If connection fails
    """
    loop = asyncio.get_event_loop()
    connected = asyncio.Event()

    def on_connected():
        connected.set()

    protocol = TuyaProtocol(
        device_id,
        local_key,
        protocol_version,
        enable_debug,
        on_connected,
        listener,
    )

    try:
        transport, _ = await asyncio.wait_for(
            loop.create_connection(lambda: protocol, address, port),
            timeout,
        )

        # Wait for connection_made callback
        await asyncio.wait_for(connected.wait(), timeout)

        return protocol

    except asyncio.TimeoutError:
        raise ConnectionError(f"Connection to {address}:{port} timed out")
    except OSError as ex:
        raise ConnectionError(f"Failed to connect to {address}:{port}: {ex}")
