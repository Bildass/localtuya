# -*- coding: utf-8 -*-
"""
PyTuya - Python module for Tuya WiFi smart devices.

Supports Protocol versions 3.1, 3.2, 3.3, 3.4, and 3.5.

Based on:
- TinyTuya (https://github.com/jasonacox/tinytuya)
- Original PyTuya by clach04
"""

__version__ = "2.0.0"
__author__ = "BildaSystem"

# =============================================================================
# PUBLIC API
# =============================================================================

# Connection
from .device import connect, TuyaProtocol, TuyaListener, EmptyListener, ContextualLogger

# Message types
from .message import (
    TuyaMessage,
    TuyaHeader,
    MessagePayload,
    DeviceStatus,
)

# Exceptions
from .message import (
    TuyaError,
    DecodeError,
    EncryptionError,
    SessionKeyError,
)
# Note: ConnectionError and TimeoutError shadow builtins, use TuyaError subclasses

# Protocol functions (for advanced use)
from .protocol import (
    parse_header,
    pack_message,
    unpack_message,
)

# Cipher (for advanced use)
from .cipher import (
    AESCipher,
    encrypt_udp,
    decrypt_udp,
)

# Constants
from .constants import (
    # Prefixes (new names)
    PREFIX_55AA,
    PREFIX_55AA_BIN,
    SUFFIX_55AA,
    SUFFIX_55AA_BIN,
    PREFIX_6699,
    PREFIX_6699_BIN,
    SUFFIX_6699,
    SUFFIX_6699_BIN,
    # Commands (new names)
    CMD_AP_CONFIG,
    CMD_ACTIVE,
    CMD_SESS_KEY_NEG_START,
    CMD_SESS_KEY_NEG_RESP,
    CMD_SESS_KEY_NEG_FINISH,
    CMD_UNBIND,
    CMD_CONTROL,
    CMD_STATUS,
    CMD_HEART_BEAT,
    CMD_DP_QUERY,
    CMD_QUERY_WIFI,
    CMD_TOKEN_BIND,
    CMD_CONTROL_NEW,
    CMD_ENABLE_WIFI,
    CMD_WIFI_INFO,
    CMD_DP_QUERY_NEW,
    CMD_SCENE_EXECUTE,
    CMD_UPDATE_DPS,
    CMD_UDP_NEW,
    CMD_AP_CONFIG_NEW,
    CMD_BROADCAST_LPV34,
    CMD_LAN_EXT_STREAM,
    # Protocol
    HEARTBEAT_INTERVAL,
    # Errors
    ERR_JSON,
    ERR_CONNECT,
    ERR_TIMEOUT,
    ERR_RANGE,
    ERR_PAYLOAD,
    ERR_OFFLINE,
    ERR_STATE,
    ERR_FUNCTION,
    ERR_DEVTYPE,
    ERR_CLOUDKEY,
    ERR_CLOUDRESP,
    ERR_CLOUDTOKEN,
    ERR_PARAMS,
    ERR_CLOUD,
    ERR_KEY,
    ERROR_MESSAGES,
    # UDP key
    UDP_KEY,
)


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# Prefix aliases (old names)
PREFIX_VALUE = PREFIX_55AA
PREFIX_BIN = PREFIX_55AA_BIN
SUFFIX_VALUE = SUFFIX_55AA
SUFFIX_BIN = SUFFIX_55AA_BIN
PREFIX_6699_VALUE = PREFIX_6699

# Command aliases (old names)
AP_CONFIG = CMD_AP_CONFIG
ACTIVE = CMD_ACTIVE
SESS_KEY_NEG_START = CMD_SESS_KEY_NEG_START
SESS_KEY_NEG_RESP = CMD_SESS_KEY_NEG_RESP
SESS_KEY_NEG_FINISH = CMD_SESS_KEY_NEG_FINISH
UNBIND = CMD_UNBIND
CONTROL = CMD_CONTROL
STATUS = CMD_STATUS
HEART_BEAT = CMD_HEART_BEAT
DP_QUERY = CMD_DP_QUERY
QUERY_WIFI = CMD_QUERY_WIFI
TOKEN_BIND = CMD_TOKEN_BIND
CONTROL_NEW = CMD_CONTROL_NEW
ENABLE_WIFI = CMD_ENABLE_WIFI
WIFI_INFO = CMD_WIFI_INFO
DP_QUERY_NEW = CMD_DP_QUERY_NEW
SCENE_EXECUTE = CMD_SCENE_EXECUTE
UPDATEDPS = CMD_UPDATE_DPS
UDP_NEW = CMD_UDP_NEW
AP_CONFIG_NEW = CMD_AP_CONFIG_NEW
BOARDCAST_LPV34 = CMD_BROADCAST_LPV34
LAN_EXT_STREAM = CMD_LAN_EXT_STREAM

# Error codes alias
error_codes = ERROR_MESSAGES

# Version info
version_tuple = tuple(int(x) for x in __version__.split("."))
version = version_string = __version__


# =============================================================================
# __all__ - Exported symbols
# =============================================================================

__all__ = [
    # Version
    "__version__",
    "version",
    "version_tuple",
    # Connection
    "connect",
    "TuyaProtocol",
    "TuyaListener",
    "EmptyListener",
    "ContextualLogger",
    # Messages
    "TuyaMessage",
    "TuyaHeader",
    "MessagePayload",
    "DeviceStatus",
    # Exceptions
    "TuyaError",
    "DecodeError",
    "EncryptionError",
    "SessionKeyError",
    # Protocol
    "parse_header",
    "pack_message",
    "unpack_message",
    # Cipher
    "AESCipher",
    "encrypt_udp",
    "decrypt_udp",
    # Constants - prefixes (new)
    "PREFIX_55AA",
    "PREFIX_55AA_BIN",
    "SUFFIX_55AA",
    "SUFFIX_55AA_BIN",
    "PREFIX_6699",
    "PREFIX_6699_BIN",
    "SUFFIX_6699",
    "SUFFIX_6699_BIN",
    # Backward compat prefixes
    "PREFIX_VALUE",
    "PREFIX_BIN",
    "SUFFIX_VALUE",
    "SUFFIX_BIN",
    "PREFIX_6699_VALUE",
    # Commands (new names)
    "CMD_AP_CONFIG",
    "CMD_ACTIVE",
    "CMD_SESS_KEY_NEG_START",
    "CMD_SESS_KEY_NEG_RESP",
    "CMD_SESS_KEY_NEG_FINISH",
    "CMD_UNBIND",
    "CMD_CONTROL",
    "CMD_STATUS",
    "CMD_HEART_BEAT",
    "CMD_DP_QUERY",
    "CMD_QUERY_WIFI",
    "CMD_TOKEN_BIND",
    "CMD_CONTROL_NEW",
    "CMD_ENABLE_WIFI",
    "CMD_WIFI_INFO",
    "CMD_DP_QUERY_NEW",
    "CMD_SCENE_EXECUTE",
    "CMD_UPDATE_DPS",
    "CMD_UDP_NEW",
    "CMD_AP_CONFIG_NEW",
    "CMD_BROADCAST_LPV34",
    "CMD_LAN_EXT_STREAM",
    # Commands (old names for backward compat)
    "AP_CONFIG",
    "ACTIVE",
    "SESS_KEY_NEG_START",
    "SESS_KEY_NEG_RESP",
    "SESS_KEY_NEG_FINISH",
    "UNBIND",
    "CONTROL",
    "STATUS",
    "HEART_BEAT",
    "DP_QUERY",
    "QUERY_WIFI",
    "TOKEN_BIND",
    "CONTROL_NEW",
    "ENABLE_WIFI",
    "WIFI_INFO",
    "DP_QUERY_NEW",
    "SCENE_EXECUTE",
    "UPDATEDPS",
    "UDP_NEW",
    "AP_CONFIG_NEW",
    "BOARDCAST_LPV34",
    "LAN_EXT_STREAM",
    # Timing
    "HEARTBEAT_INTERVAL",
    # Errors
    "ERR_JSON",
    "ERR_CONNECT",
    "ERR_TIMEOUT",
    "ERR_RANGE",
    "ERR_PAYLOAD",
    "ERR_OFFLINE",
    "ERR_STATE",
    "ERR_FUNCTION",
    "ERR_DEVTYPE",
    "ERR_CLOUDKEY",
    "ERR_CLOUDRESP",
    "ERR_CLOUDTOKEN",
    "ERR_PARAMS",
    "ERR_CLOUD",
    "ERR_KEY",
    "ERROR_MESSAGES",
    "error_codes",
    # UDP
    "UDP_KEY",
]
