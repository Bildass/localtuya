# PyTuya Module - Refactored
# -*- coding: utf-8 -*-
"""
Python module to interface with Tuya WiFi smart devices.

This is the public API module that re-exports components from submodules.
The implementation is split across multiple files for better maintainability:
- constants.py: Protocol constants and error codes
- cipher.py: AES encryption (ECB/GCM)
- message.py: Message structures and payload generation
- protocol.py: Message packing/unpacking
- session.py: Session key negotiation
- transport.py: Async TCP transport and TuyaProtocol

Author: clach04, postlund
Maintained by: rospogrigio, BildaSystem.cz
"""

import logging

# =============================================================================
# Version Info
# =============================================================================

from .constants import VERSION, VERSION_STRING, VERSION_TUPLE

version_tuple = VERSION_TUPLE
version = version_string = __version__ = VERSION_STRING
__author__ = "rospogrigio"

# =============================================================================
# Re-export from constants
# =============================================================================

from .constants import (
    # Error codes
    ERR_CLOUD,
    ERR_CLOUDKEY,
    ERR_CLOUDRESP,
    ERR_CLOUDTOKEN,
    ERR_CONNECT,
    ERR_DEVTYPE,
    ERR_FUNCTION,
    ERR_JSON,
    ERR_OFFLINE,
    ERR_PARAMS,
    ERR_PAYLOAD,
    ERR_RANGE,
    ERR_STATE,
    ERR_TIMEOUT,
    ERROR_CODES,
    # Commands
    AP_CONFIG,
    AP_CONFIG_NEW,
    ACTIVE,
    BOARDCAST_LPV34,
    CONTROL,
    CONTROL_NEW,
    DP_QUERY,
    DP_QUERY_NEW,
    ENABLE_WIFI,
    HEART_BEAT,
    LAN_EXT_STREAM,
    QUERY_WIFI,
    SCENE_EXECUTE,
    SESS_KEY_NEG_FINISH,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_START,
    STATUS,
    TOKEN_BIND,
    UNBIND,
    UDP_NEW,
    UPDATEDPS,
    WIFI_INFO,
    # Protocol headers
    MESSAGE_END_FMT,
    MESSAGE_END_FMT_6699,
    MESSAGE_END_FMT_HMAC,
    MESSAGE_HEADER_FMT,
    MESSAGE_HEADER_FMT_6699,
    MESSAGE_RECV_HEADER_FMT,
    MESSAGE_RETCODE_FMT,
    NO_PROTOCOL_HEADER_CMDS,
    PAYLOAD_DICT,
    PREFIX_55AA_BIN,
    PREFIX_55AA_VALUE,
    PREFIX_6699_BIN,
    PREFIX_6699_VALUE,
    PREFIX_BIN,
    PREFIX_VALUE,
    PROTOCOL_33_HEADER,
    PROTOCOL_34_HEADER,
    PROTOCOL_35_HEADER,
    PROTOCOL_3x_HEADER,
    PROTOCOL_VERSION_BYTES_31,
    PROTOCOL_VERSION_BYTES_33,
    PROTOCOL_VERSION_BYTES_34,
    PROTOCOL_VERSION_BYTES_35,
    SUFFIX_55AA_BIN,
    SUFFIX_55AA_VALUE,
    SUFFIX_6699_BIN,
    SUFFIX_6699_VALUE,
    SUFFIX_BIN,
    SUFFIX_VALUE,
    # Other constants
    HEARTBEAT_INTERVAL,
    UPDATE_DPS_WHITELIST,
    # Exceptions
    DecodeError,
    HMACVerificationError,
    SessionKeyError,
    SessionKeyInvalidError,
    # Named tuples (backward compat - also in message.py as dataclasses)
    MessagePayload as MessagePayloadTuple,
    TuyaHeader as TuyaHeaderTuple,
    TuyaMessage as TuyaMessageTuple,
)

# Backward compatibility alias
payload_dict = PAYLOAD_DICT
error_codes = ERROR_CODES

# =============================================================================
# Re-export from cipher
# =============================================================================

from .cipher import AESCipher, decrypt_udp_broadcast, decrypt_udp_broadcast_35

# =============================================================================
# Re-export from message
# =============================================================================

from .message import (
    MessagePayload,
    TuyaHeader,
    TuyaMessage,
    PayloadGenerator,
    create_control_payload,
    create_dp_query_payload,
    create_heartbeat_payload,
    create_session_finish_payload,
    create_session_start_payload,
    create_status_payload,
    parse_status_response,
)

# =============================================================================
# Re-export from protocol
# =============================================================================

from .protocol import (
    extract_messages,
    find_message_in_buffer,
    pack_message,
    pack_message_55aa,
    pack_message_6699,
    parse_header,
    unpack_message,
    unpack_message_55aa,
    unpack_message_6699,
)

# =============================================================================
# Re-export from session
# =============================================================================

from .session import (
    SessionKeyNegotiator,
    create_finish_hmac,
    negotiate_session_key,
    verify_device_hmac,
)

# =============================================================================
# Re-export from transport
# =============================================================================

from .transport import (
    EmptyListener,
    MessageDispatcher,
    TuyaListener,
    TuyaProtocol,
    connect,
)

# =============================================================================
# Logging Helpers (kept here for backward compatibility)
# =============================================================================

_LOGGER = logging.getLogger(__name__)


class TuyaLoggingAdapter(logging.LoggerAdapter):
    """Adapter that adds device id to all log points."""

    def process(self, msg, kwargs):
        """Process log point and return output."""
        dev_id = self.extra["device_id"]
        return f"[{dev_id[0:3]}...{dev_id[-3:]}] {msg}", kwargs


class ContextualLogger:
    """
    Contextual logger adding device id to log points.

    Used by TuyaDevice and LocalTuyaEntity for consistent logging.
    """

    def __init__(self):
        """Initialize a new ContextualLogger."""
        self._logger = None
        self._enable_debug = False

    def set_logger(self, logger, device_id, enable_debug=False):
        """Set base logger to use."""
        self._enable_debug = enable_debug
        self._logger = TuyaLoggingAdapter(logger, {"device_id": device_id})

    def debug(self, msg, *args):
        """Debug level log."""
        if not self._enable_debug:
            return
        return self._logger.log(logging.DEBUG, msg, *args)

    def info(self, msg, *args):
        """Info level log."""
        return self._logger.log(logging.INFO, msg, *args)

    def warning(self, msg, *args):
        """Warning method log."""
        return self._logger.log(logging.WARNING, msg, *args)

    def error(self, msg, *args):
        """Error level log."""
        return self._logger.log(logging.ERROR, msg, *args)

    def exception(self, msg, *args):
        """Exception level log."""
        return self._logger.exception(msg, *args)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "version",
    "version_string",
    "version_tuple",
    "__version__",
    # Main classes
    "TuyaProtocol",
    "TuyaListener",
    "EmptyListener",
    "AESCipher",
    "SessionKeyNegotiator",
    "PayloadGenerator",
    "MessageDispatcher",
    # Connection
    "connect",
    # Message types
    "TuyaMessage",
    "TuyaHeader",
    "MessagePayload",
    # Protocol functions
    "pack_message",
    "unpack_message",
    "parse_header",
    # Session functions
    "negotiate_session_key",
    "verify_device_hmac",
    "create_finish_hmac",
    # Helper functions
    "create_heartbeat_payload",
    "create_status_payload",
    "create_dp_query_payload",
    "create_control_payload",
    "parse_status_response",
    # Logging
    "ContextualLogger",
    "TuyaLoggingAdapter",
    # Exceptions
    "DecodeError",
    "SessionKeyError",
    "SessionKeyInvalidError",
    "HMACVerificationError",
    # Constants (commonly used)
    "CONTROL",
    "STATUS",
    "DP_QUERY",
    "HEART_BEAT",
    "PREFIX_VALUE",
    "PREFIX_6699_VALUE",
    "PAYLOAD_DICT",
    "payload_dict",
    "ERROR_CODES",
    "error_codes",
]
