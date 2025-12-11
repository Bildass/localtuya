# PyTuya Constants
# -*- coding: utf-8 -*-
"""
Constants for Tuya WiFi protocol implementation.

Extracted from pytuya for better code organization.
Reference: https://github.com/tuya/tuya-iotos-embeded-sdk-wifi-ble-bk7231n/blob/master/sdk/include/lan_protocol.h
"""

from collections import namedtuple

# Version info
VERSION_TUPLE = (10, 0, 0)
VERSION = VERSION_STRING = "%d.%d.%d" % VERSION_TUPLE

# =============================================================================
# Tuya Packet Format - Named Tuples
# =============================================================================

TuyaHeader = namedtuple("TuyaHeader", "prefix seqno cmd length total_length")
MessagePayload = namedtuple("MessagePayload", "cmd payload")

try:
    TuyaMessage = namedtuple(
        "TuyaMessage",
        "seqno cmd retcode payload crc crc_good prefix iv",
        defaults=(True, 0x000055AA, None)  # prefix defaults to 55AA, iv defaults to None
    )
except TypeError:
    # Python < 3.7 compatibility
    TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc crc_good prefix iv")


# =============================================================================
# Error Codes (TinyTuya compatible)
# =============================================================================

ERR_JSON = 900
ERR_CONNECT = 901
ERR_TIMEOUT = 902
ERR_RANGE = 903
ERR_PAYLOAD = 904
ERR_OFFLINE = 905
ERR_STATE = 906
ERR_FUNCTION = 907
ERR_DEVTYPE = 908
ERR_CLOUDKEY = 909
ERR_CLOUDRESP = 910
ERR_CLOUDTOKEN = 911
ERR_PARAMS = 912
ERR_CLOUD = 913

ERROR_CODES = {
    ERR_JSON: "Invalid JSON Response from Device",
    ERR_CONNECT: "Network Error: Unable to Connect",
    ERR_TIMEOUT: "Timeout Waiting for Device",
    ERR_RANGE: "Specified Value Out of Range",
    ERR_PAYLOAD: "Unexpected Payload from Device",
    ERR_OFFLINE: "Network Error: Device Unreachable",
    ERR_STATE: "Device in Unknown State",
    ERR_FUNCTION: "Function Not Supported by Device",
    ERR_DEVTYPE: "Device22 Detected: Retry Command",
    ERR_CLOUDKEY: "Missing Tuya Cloud Key and Secret",
    ERR_CLOUDRESP: "Invalid JSON Response from Cloud",
    ERR_CLOUDTOKEN: "Unable to Get Cloud Token",
    ERR_PARAMS: "Missing Function Parameters",
    ERR_CLOUD: "Error Response from Tuya Cloud",
    None: "Unknown Error",
}


# =============================================================================
# Tuya Command Types
# =============================================================================

AP_CONFIG = 0x01            # FRM_TP_CFG_WF - only used for ap 3.0 network config
ACTIVE = 0x02               # FRM_TP_ACTV (discard) - WORK_MODE_CMD
SESS_KEY_NEG_START = 0x03   # FRM_SECURITY_TYPE3 - negotiate session key
SESS_KEY_NEG_RESP = 0x04    # FRM_SECURITY_TYPE4 - negotiate session key response
SESS_KEY_NEG_FINISH = 0x05  # FRM_SECURITY_TYPE5 - finalize session key negotiation
UNBIND = 0x06               # FRM_TP_UNBIND_DEV - DATA_QUERT_CMD - issue command
CONTROL = 0x07              # FRM_TP_CMD - STATE_UPLOAD_CMD
STATUS = 0x08               # FRM_TP_STAT_REPORT - STATE_QUERY_CMD
HEART_BEAT = 0x09           # FRM_TP_HB
DP_QUERY = 0x0A             # 10 - FRM_QUERY_STAT - UPDATE_START_CMD - get data points
QUERY_WIFI = 0x0B           # 11 - FRM_SSID_QUERY (discard) - UPDATE_TRANS_CMD
TOKEN_BIND = 0x0C           # 12 - FRM_USER_BIND_REQ - GET_ONLINE_TIME_CMD
CONTROL_NEW = 0x0D          # 13 - FRM_TP_NEW_CMD - FACTORY_MODE_CMD
ENABLE_WIFI = 0x0E          # 14 - FRM_ADD_SUB_DEV_CMD - WIFI_TEST_CMD
WIFI_INFO = 0x0F            # 15 - FRM_CFG_WIFI_INFO
DP_QUERY_NEW = 0x10         # 16 - FRM_QUERY_STAT_NEW
SCENE_EXECUTE = 0x11        # 17 - FRM_SCENE_EXEC
UPDATEDPS = 0x12            # 18 - FRM_LAN_QUERY_DP - Request refresh of DPS
UDP_NEW = 0x13              # 19 - FR_TYPE_ENCRYPTION
AP_CONFIG_NEW = 0x14        # 20 - FRM_AP_CFG_WF_V40
BOARDCAST_LPV34 = 0x23      # 35 - FR_TYPE_BOARDCAST_LPV34
LAN_EXT_STREAM = 0x40       # 64 - FRM_LAN_EXT_STREAM


# =============================================================================
# Protocol Version Headers
# =============================================================================

PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_VERSION_BYTES_34 = b"3.4"
PROTOCOL_VERSION_BYTES_35 = b"3.5"

PROTOCOL_3x_HEADER = 12 * b"\x00"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + PROTOCOL_3x_HEADER
PROTOCOL_34_HEADER = PROTOCOL_VERSION_BYTES_34 + PROTOCOL_3x_HEADER
PROTOCOL_35_HEADER = PROTOCOL_VERSION_BYTES_35 + PROTOCOL_3x_HEADER


# =============================================================================
# Message Format Structures
# =============================================================================

# Standard 55AA format (Protocol 3.1-3.4)
MESSAGE_HEADER_FMT = ">4I"          # 4*uint32: prefix, seqno, cmd, length
MESSAGE_RECV_HEADER_FMT = ">5I"     # 5*uint32: prefix, seqno, cmd, length, retcode

# Protocol 3.5 6699 format
MESSAGE_HEADER_FMT_6699 = ">IHIII"  # prefix(4), unknown(2), seqno(4), cmd(4), length(4)

# Message endings
MESSAGE_RETCODE_FMT = ">I"          # retcode for received messages
MESSAGE_END_FMT = ">2I"             # 2*uint32: crc, suffix
MESSAGE_END_FMT_HMAC = ">32sI"      # 32s:hmac, uint32:suffix
MESSAGE_END_FMT_6699 = ">16sI"      # 16s:tag, uint32:suffix (for GCM)


# =============================================================================
# Prefix/Suffix Values
# =============================================================================

# Standard 55AA format (Protocol 3.1-3.4)
PREFIX_55AA_VALUE = 0x000055AA
PREFIX_55AA_BIN = b"\x00\x00U\xaa"
SUFFIX_55AA_VALUE = 0x0000AA55
SUFFIX_55AA_BIN = b"\x00\x00\xaaU"

# Protocol 3.5 6699 format
PREFIX_6699_VALUE = 0x00006699
PREFIX_6699_BIN = b"\x00\x00\x66\x99"
SUFFIX_6699_VALUE = 0x00009966
SUFFIX_6699_BIN = b"\x00\x00\x99\x66"

# Aliases for backward compatibility
PREFIX_VALUE = PREFIX_55AA_VALUE
PREFIX_BIN = PREFIX_55AA_BIN
SUFFIX_VALUE = SUFFIX_55AA_VALUE
SUFFIX_BIN = SUFFIX_55AA_BIN


# =============================================================================
# Protocol Behavior Constants
# =============================================================================

# Commands that don't include protocol version header in payload
NO_PROTOCOL_HEADER_CMDS = [
    DP_QUERY,
    DP_QUERY_NEW,
    UPDATEDPS,
    HEART_BEAT,
    SESS_KEY_NEG_START,
    SESS_KEY_NEG_RESP,
    SESS_KEY_NEG_FINISH,
]

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 10

# Session key negotiation sequence number
SESS_KEY_SEQNO = -102

# Connection timeouts
DEFAULT_TIMEOUT = 5.0
HEARTBEAT_TIMEOUT = 10.0

# DPS that are known to be safe to use with update_dps (0x12) command
UPDATE_DPS_WHITELIST = [18, 19, 20]  # Socket (Wi-Fi)


# =============================================================================
# Device Type Payload Dictionaries
# =============================================================================

# Tuya Device Dictionary - Command and Payload Overrides
# This is intended to match requests.json payload at https://github.com/codetheweb/tuyapi
#
# 'type_0a' devices require the 0a command for the DP_QUERY request
# 'type_0d' devices require the 0d command for the DP_QUERY request and a list of
#            dps used set to Null in the request payload

PAYLOAD_DICT = {
    # Default Device (type_0a)
    "type_0a": {
        AP_CONFIG: {
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        STATUS: {
            "command": {"gwId": "", "devId": ""},
        },
        HEART_BEAT: {
            "command": {"gwId": "", "devId": ""},
        },
        DP_QUERY: {
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL_NEW: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        DP_QUERY_NEW: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        UPDATEDPS: {
            "command": {"dpId": [18, 19, 20]},
        },
    },
    # Special Case Device "0d"
    # Requires the 0d command as the DP_QUERY status request
    "type_0d": {
        DP_QUERY: {
            "command_override": CONTROL_NEW,
            "command": {"devId": "", "uid": "", "t": ""},
        },
    },
    # Protocol 3.4 overrides
    "v3.4": {
        CONTROL: {
            "command_override": CONTROL_NEW,
            "command": {"protocol": 5, "t": "int", "data": ""},
        },
        DP_QUERY: {
            "command_override": DP_QUERY_NEW,
        },
    },
    # Protocol 3.5 overrides
    "v3.5": {
        CONTROL: {
            "command_override": CONTROL_NEW,
            "command": {"protocol": 5, "t": "int", "data": ""},
        },
        DP_QUERY: {
            "command_override": DP_QUERY_NEW,
            "command": {"devId": "", "uid": "", "t": ""},  # v3.5 doesn't use gwId
        },
    },
}

# Backward compatibility alias
payload_dict = PAYLOAD_DICT


# =============================================================================
# Custom Exceptions
# =============================================================================

class DecodeError(Exception):
    """Exception raised when message decoding fails."""
    pass


class SessionKeyError(Exception):
    """Exception raised when session key negotiation fails."""
    pass


class HMACVerificationError(SessionKeyError):
    """Exception raised when HMAC verification fails."""
    pass


class SessionKeyInvalidError(SessionKeyError):
    """Exception raised when session key is invalid (e.g., starts with 0x00)."""
    pass
