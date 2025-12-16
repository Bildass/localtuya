"""Helper functions and schemas for LocalTuya 2.0 config flow."""
import logging
from importlib import import_module

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import core
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

from .cloud_api import TuyaCloudApi, TUYA_REGION_NAMES
from .common import pytuya
from .const import (
    CONF_ACTION,
    CONF_ADD_DEVICE,
    CONF_DELETE_DEVICE,
    CONF_DPS_STRINGS,
    CONF_EDIT_DEVICE,
    CONF_EDIT_ENTITIES,
    CONF_ENABLE_DEBUG,
    CONF_ENTITY_PREFIX,
    CONF_FORCE_ADD,
    CONF_SKIP_CONNECT,
    CONF_FULL_EDIT,
    CONF_LOCAL_KEY,
    CONF_MANUAL_DPS,
    CONF_NO_CLOUD,
    CONF_PROTOCOL_VERSION,
    CONF_QUICK_EDIT,
    CONF_RESET_DPIDS,
    CONF_SETUP_CLOUD,
    CONF_SYNC_CLOUD,
    CONF_USER_ID,
    CONF_ENABLE_ADD_ENTITIES,
    CONF_QR_AUTH,
    DOMAIN,
    PLATFORMS,
)
from .exceptions import CannotConnect, InvalidAuth, EmptyDpsList

_LOGGER = logging.getLogger(__name__)

# Constants for config flow
ENTRIES_VERSION = 2
PLATFORM_TO_ADD = "platform_to_add"
NO_ADDITIONAL_ENTITIES = "no_additional_entities"
SELECTED_DEVICE = "selected_device"
CUSTOM_DEVICE = "..."
USE_LIBRARY_TEMPLATE = "use_library_template"
CONF_USE_TEMPLATE = "use_template"

# Action menu options
CONF_ACTIONS = {
    CONF_ADD_DEVICE: "Add a new device",
    CONF_EDIT_DEVICE: "Edit a device",
    CONF_SYNC_CLOUD: "Sync local keys from cloud",
    CONF_SETUP_CLOUD: "Reconfigure Cloud API account",
    CONF_QR_AUTH: "🔐 QR Code Authentication (Easy!)",
}

# Device action submenu options
DEVICE_ACTIONS = {
    CONF_QUICK_EDIT: "Quick edit (host, key, protocol)",
    CONF_EDIT_ENTITIES: "Edit entities",
    CONF_FULL_EDIT: "Full configuration",
    CONF_DELETE_DEVICE: "Delete device",
}

# ============================================================================
# SCHEMAS
# ============================================================================

QUICK_EDIT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(
            ["3.1", "3.2", "3.3", "3.4", "3.5"]
        ),
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Required(CONF_ENABLE_DEBUG, default=False): bool,
    }
)

CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACTION, default=CONF_ADD_DEVICE): vol.In(CONF_ACTIONS),
    }
)

CLOUD_SETUP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION, default="eu"): vol.In(TUYA_REGION_NAMES),
        vol.Optional(CONF_CLIENT_ID): cv.string,
        vol.Optional(CONF_CLIENT_SECRET): cv.string,
        vol.Optional(CONF_USER_ID): cv.string,
        vol.Optional(CONF_USERNAME, default=DOMAIN): cv.string,
        vol.Required(CONF_NO_CLOUD, default=False): bool,
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_FRIENDLY_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(
            ["3.1", "3.2", "3.3", "3.4", "3.5"]
        ),
        vol.Required(CONF_ENABLE_DEBUG, default=False): bool,
        vol.Optional(CONF_ENTITY_PREFIX): cv.string,  # Prefix for entity names
        vol.Optional(CONF_SCAN_INTERVAL): int,
        vol.Optional(CONF_MANUAL_DPS): cv.string,
        vol.Optional(CONF_RESET_DPIDS): str,
        vol.Optional(CONF_FORCE_ADD, default=False): bool,
        vol.Optional(CONF_SKIP_CONNECT, default=False): bool,
    }
)

PICK_ENTITY_SCHEMA = vol.Schema(
    {vol.Required(PLATFORM_TO_ADD, default="switch"): vol.In(PLATFORMS)}
)



# ============================================================================
# SCHEMA BUILDER FUNCTIONS
# ============================================================================

def devices_schema(discovered_devices, cloud_devices_list, add_custom_device=True):
    """Create schema for devices step."""
    devices = {}
    for dev_id, dev_host in discovered_devices.items():
        dev_name = dev_id
        if dev_id in cloud_devices_list.keys():
            dev_name = cloud_devices_list[dev_id][CONF_NAME]
        devices[dev_id] = f"{dev_name} ({dev_host})"

    if add_custom_device:
        devices.update({CUSTOM_DEVICE: CUSTOM_DEVICE})

    return vol.Schema({vol.Required(SELECTED_DEVICE): vol.In(devices)})


def options_schema(entities):
    """Create schema for options."""
    entity_names = [
        f"{entity[CONF_ID]}: {entity[CONF_FRIENDLY_NAME]}" for entity in entities
    ]
    return vol.Schema(
        {
            vol.Required(CONF_FRIENDLY_NAME): cv.string,
            vol.Required(CONF_HOST): cv.string,
            vol.Required(CONF_LOCAL_KEY): cv.string,
            vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(
                ["3.1", "3.2", "3.3", "3.4", "3.5"]
            ),
            vol.Required(CONF_ENABLE_DEBUG, default=False): bool,
            vol.Optional(CONF_ENTITY_PREFIX): cv.string,  # Prefix for entity names
            vol.Optional(CONF_SCAN_INTERVAL): int,
            vol.Optional(CONF_MANUAL_DPS): cv.string,
            vol.Optional(CONF_RESET_DPIDS): cv.string,
            vol.Optional(CONF_FORCE_ADD, default=False): bool,
            vol.Optional(CONF_SKIP_CONNECT, default=False): bool,
            vol.Required(
                CONF_ENTITIES, description={"suggested_value": entity_names}
            ): cv.multi_select(entity_names),
            vol.Required(CONF_ENABLE_ADD_ENTITIES, default=True): bool,
        }
    )


def schema_defaults(schema, dps_list=None, **defaults):
    """Create a new schema with default values filled in."""
    copy = schema.extend({})
    for field, field_type in copy.schema.items():
        if isinstance(field_type, vol.In):
            value = None
            for dps in dps_list or []:
                if dps.startswith(f"{defaults.get(field)} "):
                    value = dps
                    break

            if value in field_type.container:
                field.default = vol.default_factory(value)
                continue

        if field.schema in defaults:
            field.default = vol.default_factory(defaults[field])
    return copy


def platform_schema(platform, dps_strings, allow_id=True, yaml=False):
    """Generate input validation schema for a platform."""
    schema = {}
    if yaml:
        # In YAML mode we force the specified platform to match flow schema
        schema[vol.Required(CONF_PLATFORM)] = vol.In([platform])
    if allow_id:
        schema[vol.Required(CONF_ID)] = vol.In(dps_strings)
    schema[vol.Required(CONF_FRIENDLY_NAME)] = str
    return vol.Schema(schema).extend(flow_schema(platform, dps_strings))


def flow_schema(platform, dps_strings):
    """Return flow schema for a specific platform."""
    integration_module = ".".join(__name__.split(".")[:-1])
    return import_module("." + platform, integration_module).flow_schema(dps_strings)


def config_schema():
    """Build schema used for setting up component."""
    entity_schemas = [
        platform_schema(platform, range(1, 256), yaml=True) for platform in PLATFORMS
    ]
    return vol.Schema(
        {
            DOMAIN: vol.All(
                cv.ensure_list,
                [
                    DEVICE_SCHEMA.extend(
                        {vol.Required(CONF_ENTITIES): [vol.Any(*entity_schemas)]}
                    )
                ],
            )
        },
        extra=vol.ALLOW_EXTRA,
    )


# ============================================================================
# DPS UTILITY FUNCTIONS
# ============================================================================

def dps_string_list(dps_data):
    """Return list of friendly DPS values."""
    return [f"{id} (value: {value})" for id, value in dps_data.items()]


def gen_dps_strings():
    """Generate list of DPS values."""
    return [f"{dp} (value: ?)" for dp in range(1, 256)]


def strip_dps_values(user_input, dps_strings):
    """Remove values and keep only index for DPS config items."""
    stripped = {}
    for field, value in user_input.items():
        if value in dps_strings:
            stripped[field] = int(user_input[field].split(" ")[0])
        else:
            stripped[field] = user_input[field]
    return stripped


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    detected_dps = {}

    # Skip connection check entirely if requested
    if data.get(CONF_SKIP_CONNECT):
        _LOGGER.warning(
            "Skip connection check enabled - using manual DPS only. "
            "Device connectivity will be verified after setup."
        )
        if CONF_MANUAL_DPS in data and data[CONF_MANUAL_DPS]:
            manual_dps_list = [dps.strip() for dps in data[CONF_MANUAL_DPS].split(",")]
            for dps in manual_dps_list:
                detected_dps[dps] = -1
        else:
            detected_dps["1"] = -1  # Default to DPS 1
        _LOGGER.debug("Skip connect - using DPS: %s", detected_dps)
        return dps_string_list(detected_dps)

    interface = None

    reset_ids = None
    try:
        interface = await pytuya.connect(
            data[CONF_HOST],
            data[CONF_DEVICE_ID],
            data[CONF_LOCAL_KEY],
            float(data[CONF_PROTOCOL_VERSION]),
            data[CONF_ENABLE_DEBUG],
        )
        if CONF_RESET_DPIDS in data:
            reset_ids_str = data[CONF_RESET_DPIDS].split(",")
            reset_ids = []
            for reset_id in reset_ids_str:
                reset_ids.append(int(reset_id.strip()))
            _LOGGER.debug(
                "Reset DPIDs configured: %s (%s)",
                data[CONF_RESET_DPIDS],
                reset_ids,
            )
        try:
            detected_dps = await interface.detect_available_dps()
        except Exception as ex:
            try:
                _LOGGER.debug(
                    "Initial state update failed (%s), trying reset command", ex
                )
                if len(reset_ids) > 0:
                    await interface.reset(reset_ids)
                    detected_dps = await interface.detect_available_dps()
            except Exception as ex:
                _LOGGER.debug("No DPS able to be detected: %s", ex)
                detected_dps = {}

        # if manual DPs are set, merge these.
        _LOGGER.debug("Detected DPS: %s", detected_dps)
        if CONF_MANUAL_DPS in data:
            manual_dps_list = [dps.strip() for dps in data[CONF_MANUAL_DPS].split(",")]
            _LOGGER.debug(
                "Manual DPS Setting: %s (%s)", data[CONF_MANUAL_DPS], manual_dps_list
            )
            # merge the lists
            for new_dps in manual_dps_list + (reset_ids or []):
                # If the DPS not in the detected dps list, then add with a
                # default value indicating that it has been manually added
                if str(new_dps) not in detected_dps:
                    detected_dps[new_dps] = -1

    except (ConnectionRefusedError, ConnectionResetError) as ex:
        raise CannotConnect from ex
    except ValueError as ex:
        raise InvalidAuth from ex
    finally:
        if interface:
            await interface.close()

    # Indicate an error if no datapoints found as the rest of the flow
    # won't work in this case - unless force_add is enabled
    if not detected_dps:
        if data.get(CONF_FORCE_ADD):
            _LOGGER.warning(
                "No DPS detected but force_add is enabled. "
                "Using manual DPS or default DPS 1."
            )
            # If manual DPS was provided, use those; otherwise create default DPS 1
            if CONF_MANUAL_DPS in data and data[CONF_MANUAL_DPS]:
                manual_dps_list = [dps.strip() for dps in data[CONF_MANUAL_DPS].split(",")]
                for dps in manual_dps_list:
                    detected_dps[dps] = -1
            else:
                detected_dps["1"] = -1  # Default to DPS 1
        else:
            raise EmptyDpsList

    _LOGGER.debug("Total DPS: %s", detected_dps)

    return dps_string_list(detected_dps)


async def attempt_cloud_connection(hass, user_input):
    """Create device."""
    cloud_api = TuyaCloudApi(
        hass,
        user_input.get(CONF_REGION),
        user_input.get(CONF_CLIENT_ID),
        user_input.get(CONF_CLIENT_SECRET),
        user_input.get(CONF_USER_ID),
    )

    res = await cloud_api.async_get_access_token()
    if res != "ok":
        _LOGGER.error("Cloud API connection failed: %s", res)
        return cloud_api, {"reason": "authentication_failed", "msg": res}

    res = await cloud_api.async_get_devices_list()
    if res != "ok":
        _LOGGER.error("Cloud API get_devices_list failed: %s", res)
        return cloud_api, {"reason": "device_list_failed", "msg": res}
    _LOGGER.info("Cloud API connection succeeded.")

    return cloud_api, {}
