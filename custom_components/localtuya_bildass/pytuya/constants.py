# -*- coding: utf-8 -*-
"""
Tuya Protocol Constants.

Based on TinyTuya (https://github.com/jasonacox/tinytuya)
and Tuya protocol documentation.

Protocol versions:
- 3.1, 3.2, 3.3: Use 55AA prefix, ECB encryption, CRC32 checksum
- 3.4: Use 55AA prefix, ECB encryption, HMAC-SHA256
- 3.5: Use 6699 prefix, GCM encryption, GCM tag for auth
"""

# =============================================================================
# MESSAGE PREFIXES AND SUFFIXES
# =============================================================================

# Protocol 3.1-3.4: Standard 55AA format
PREFIX_55AA = 0x000055AA
PREFIX_55AA_BIN = b"\x00\x00\x55\xaa"
SUFFIX_55AA = 0x0000AA55
SUFFIX_55AA_BIN = b"\x00\x00\xaa\x55"

# Protocol 3.5: New 6699 format
PREFIX_6699 = 0x00006699
PREFIX_6699_BIN = b"\x00\x00\x66\x99"
SUFFIX_6699 = 0x00009966
SUFFIX_6699_BIN = b"\x00\x00\x99\x66"

# =============================================================================
# TUYA COMMAND TYPES
# Reference: https://github.com/tuya/tuya-iotos-embeded-sdk-wifi-ble-bk7231n
# =============================================================================

# Network configuration
CMD_AP_CONFIG = 0x01          # FRM_TP_CFG_WF - AP 3.0 network config
CMD_ACTIVE = 0x02             # FRM_TP_ACTV - Work mode command

# Session key negotiation (Protocol 3.4+)
CMD_SESS_KEY_NEG_START = 0x03   # FRM_SECURITY_TYPE3 - Start negotiation
CMD_SESS_KEY_NEG_RESP = 0x04    # FRM_SECURITY_TYPE4 - Response with device nonce
CMD_SESS_KEY_NEG_FINISH = 0x05  # FRM_SECURITY_TYPE5 - Finish negotiation

# Device control
CMD_UNBIND = 0x06             # FRM_TP_UNBIND_DEV - Unbind device
CMD_CONTROL = 0x07            # FRM_TP_CMD - Set control values
CMD_STATUS = 0x08             # FRM_TP_STAT_REPORT - Status report
CMD_HEART_BEAT = 0x09         # FRM_TP_HB - Heartbeat
CMD_DP_QUERY = 0x0A           # FRM_QUERY_STAT - Query data points (10)
CMD_QUERY_WIFI = 0x0B         # FRM_SSID_QUERY - Query WiFi (11)
CMD_TOKEN_BIND = 0x0C         # FRM_USER_BIND_REQ - Token bind (12)
CMD_CONTROL_NEW = 0x0D        # FRM_TP_NEW_CMD - New control command (13)
CMD_ENABLE_WIFI = 0x0E        # FRM_ADD_SUB_DEV_CMD - Enable WiFi (14)
CMD_WIFI_INFO = 0x0F          # FRM_CFG_WIFI_INFO - WiFi info (15)
CMD_DP_QUERY_NEW = 0x10       # FRM_QUERY_STAT_NEW - New DP query (16)
CMD_SCENE_EXECUTE = 0x11      # FRM_SCENE_EXEC - Execute scene (17)
CMD_UPDATE_DPS = 0x12         # FRM_LAN_QUERY_DP - Request DPS refresh (18)
CMD_UDP_NEW = 0x13            # FR_TYPE_ENCRYPTION - UDP new (19)
CMD_AP_CONFIG_NEW = 0x14      # FRM_AP_CFG_WF_V40 - AP config new (20)
CMD_BROADCAST_LPV34 = 0x23    # FR_TYPE_BOARDCAST_LPV34 - Broadcast (35)
CMD_LAN_EXT_STREAM = 0x40     # FRM_LAN_EXT_STREAM - LAN stream (64)

# Commands that don't need protocol version header
NO_PROTOCOL_HEADER_CMDS = frozenset([
    CMD_DP_QUERY,
    CMD_DP_QUERY_NEW,
    CMD_UPDATE_DPS,
    CMD_HEART_BEAT,
    CMD_SESS_KEY_NEG_START,
    CMD_SESS_KEY_NEG_RESP,
    CMD_SESS_KEY_NEG_FINISH,
])

# Session key negotiation commands
SESSION_KEY_CMDS = frozenset([
    CMD_SESS_KEY_NEG_START,
    CMD_SESS_KEY_NEG_RESP,
    CMD_SESS_KEY_NEG_FINISH,
])

# =============================================================================
# PROTOCOL VERSION HEADERS
# =============================================================================

# Version bytes
VERSION_31 = b"3.1"
VERSION_32 = b"3.2"
VERSION_33 = b"3.3"
VERSION_34 = b"3.4"
VERSION_35 = b"3.5"

# Protocol 3.x header: version + 12 zero bytes
# Format: 3.x[CRC32 4B][SEQNO 4B][SOURCE_ID 4B]
# For LAN: CRC32=0, SEQNO=incrementing, SOURCE_ID=0 or random
PROTOCOL_3X_HEADER_PAD = 12 * b"\x00"

# =============================================================================
# MESSAGE STRUCTURE FORMATS (struct module)
# =============================================================================

# 55AA format header: prefix(4) + seqno(4) + cmd(4) + length(4)
HEADER_FMT_55AA = ">4I"  # 4 x uint32 big-endian
HEADER_SIZE_55AA = 16

# 55AA format with retcode: prefix(4) + seqno(4) + cmd(4) + length(4) + retcode(4)
HEADER_FMT_55AA_RECV = ">5I"  # 5 x uint32 big-endian
HEADER_SIZE_55AA_RECV = 20

# 6699 format header: prefix(4) + version(1) + reserved(1) + seqno(4) + cmd(4) + length(4)
HEADER_FMT_6699 = ">IBBIII"  # uint32 + 2x uint8 + 3x uint32
HEADER_SIZE_6699 = 18

# Retcode format
RETCODE_FMT = ">I"
RETCODE_SIZE = 4

# 55AA footer with CRC32: crc(4) + suffix(4)
FOOTER_FMT_55AA_CRC = ">II"
FOOTER_SIZE_55AA_CRC = 8

# 55AA footer with HMAC: hmac(32) + suffix(4)
FOOTER_FMT_55AA_HMAC = ">32sI"
FOOTER_SIZE_55AA_HMAC = 36

# 6699 footer: tag(16) + suffix(4)
FOOTER_FMT_6699 = ">16sI"
FOOTER_SIZE_6699 = 20

# =============================================================================
# TIMING AND LIMITS
# =============================================================================

HEARTBEAT_INTERVAL = 10  # seconds
DEFAULT_TIMEOUT = 5  # seconds
MAX_PAYLOAD_SIZE = 2000  # bytes - sanity check

# DPS indices known to be safe for UPDATE_DPS command
UPDATE_DPS_WHITELIST = frozenset([18, 19, 20])

# =============================================================================
# ENCRYPTION
# =============================================================================

# UDP discovery key (MD5 of "yGAdlopoPVldABfn")
from hashlib import md5
UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()

# GCM parameters
GCM_NONCE_SIZE = 12  # 96 bits
GCM_TAG_SIZE = 16    # 128 bits

# AES block size
AES_BLOCK_SIZE = 16

# =============================================================================
# ERROR CODES
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
ERR_KEY = 914

ERROR_MESSAGES = {
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
    ERR_KEY: "Session Key Negotiation Failed",
    None: "Unknown Error",
}

# =============================================================================
# PAYLOAD TEMPLATES
# =============================================================================

# Device type determines which commands and payloads to use
DEVICE_TYPE_0A = "type_0a"  # Default device
DEVICE_TYPE_0D = "type_0d"  # Requires 0d command for DP_QUERY
DEVICE_TYPE_V34 = "v3.4"    # Protocol 3.4 device
DEVICE_TYPE_V35 = "v3.5"    # Protocol 3.5 device

# Payload templates per device type and command
PAYLOAD_DICT = {
    DEVICE_TYPE_0A: {
        CMD_AP_CONFIG: {
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CMD_CONTROL: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        CMD_STATUS: {
            "command": {"gwId": "", "devId": ""},
        },
        CMD_HEART_BEAT: {
            "command": {"gwId": "", "devId": ""},
        },
        CMD_DP_QUERY: {
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CMD_CONTROL_NEW: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        CMD_DP_QUERY_NEW: {
            "command": {"devId": "", "uid": "", "t": ""},
        },
        CMD_UPDATE_DPS: {
            "command": {"dpId": [18, 19, 20]},
        },
    },
    DEVICE_TYPE_0D: {
        CMD_DP_QUERY: {
            "command_override": CMD_CONTROL_NEW,
            "command": {"devId": "", "uid": "", "t": ""},
        },
    },
    DEVICE_TYPE_V34: {
        CMD_CONTROL: {
            "command_override": CMD_CONTROL_NEW,
            "command": {"protocol": 5, "t": "int", "data": ""},
        },
        CMD_DP_QUERY: {
            "command_override": CMD_DP_QUERY_NEW,
        },
    },
    DEVICE_TYPE_V35: {
        CMD_CONTROL: {
            "command_override": CMD_CONTROL_NEW,
            "command": {"protocol": 5, "t": "int", "data": ""},
        },
        CMD_DP_QUERY: {
            "command_override": CMD_DP_QUERY_NEW,
            "command": {"devId": "", "uid": "", "t": ""},
        },
    },
}
