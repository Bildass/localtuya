"""Config flow for LocalTuya integration integration."""
import errno
import logging
import time
from importlib import import_module

import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICES,
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
from homeassistant.core import callback

from .cloud_api import TuyaCloudApi
from .common import pytuya
from .const import (
    ATTR_UPDATED_AT,
    BILDASYSTEM_NAME,
    CONF_ACTION,
    CONF_ADD_DEVICE,
    CONF_ADD_NEW_ENTITY,
    CONF_DELETE_DEVICE,
    CONF_DELETE_ENTITY,
    CONF_DEVICE_ACTION,
    CONF_DPS_STRINGS,
    CONF_EDIT_DEVICE,
    CONF_EDIT_ENTITIES,
    CONF_ENABLE_DEBUG,
    CONF_FORCE_ADD,
    CONF_SKIP_CONNECT,
    CONF_FULL_EDIT,
    CONF_LOCAL_KEY,
    CONF_MANUAL_DPS,
    CONF_MODEL,
    CONF_NO_CLOUD,
    CONF_PRODUCT_NAME,
    CONF_PROTOCOL_VERSION,
    CONF_QUICK_EDIT,
    CONF_RESET_DPIDS,
    CONF_SELECTED_ENTITY,
    CONF_SETUP_CLOUD,
    CONF_SYNC_CLOUD,
    CONF_USER_ID,
    CONF_ENABLE_ADD_ENTITIES,
    DATA_CLOUD,
    DATA_DISCOVERY,
    DOMAIN,
    PLATFORMS,
    VERSION,
)
from .discovery import discover

_LOGGER = logging.getLogger(__name__)

ENTRIES_VERSION = 2

PLATFORM_TO_ADD = "platform_to_add"
NO_ADDITIONAL_ENTITIES = "no_additional_entities"
SELECTED_DEVICE = "selected_device"

CUSTOM_DEVICE = "..."

CONF_ACTIONS = {
    CONF_ADD_DEVICE: "Add a new device",
    CONF_EDIT_DEVICE: "Edit a device",
    CONF_SYNC_CLOUD: "Sync local keys from cloud",
    CONF_SETUP_CLOUD: "Reconfigure Cloud API account",
}

# Device action submenu options
DEVICE_ACTIONS = {
    CONF_QUICK_EDIT: "Quick edit (host, key, protocol)",
    CONF_EDIT_ENTITIES: "Edit entities",
    CONF_FULL_EDIT: "Full configuration",
    CONF_DELETE_DEVICE: "Delete device",
}

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
        vol.Required(CONF_REGION, default="eu"): vol.In(["eu", "us", "cn", "in"]),
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

    # devices.update(
    #     {
    #         ent.data[CONF_DEVICE_ID]: ent.data[CONF_FRIENDLY_NAME]
    #         for ent in entries
    #     }
    # )
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


def dps_string_list(dps_data):
    """Return list of friendly DPS values."""
    return [f"{id} (value: {value})" for id, value in dps_data.items()]


def gen_dps_strings():
    """Generate list of DPS values."""
    return [f"{dp} (value: ?)" for dp in range(1, 256)]


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


def strip_dps_values(user_input, dps_strings):
    """Remove values and keep only index for DPS config items."""
    stripped = {}
    for field, value in user_input.items():
        if value in dps_strings:
            stripped[field] = int(user_input[field].split(" ")[0])
        else:
            stripped[field] = user_input[field]
    return stripped


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


class LocaltuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalTuya integration."""

    VERSION = ENTRIES_VERSION
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for this handler."""
        return LocalTuyaOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize a new LocaltuyaConfigFlow."""
        self._username = DOMAIN

    async def async_step_user(self, user_input=None):
        """Handle the initial step - go directly to cloud credentials."""
        return await self.async_step_cloud_credentials()

    async def async_step_cloud_credentials(self, user_input=None):
        """Handle the cloud credentials step."""
        errors = {}
        placeholders = {}
        if user_input is not None:
            if user_input.get(CONF_NO_CLOUD):
                for i in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
                    user_input[i] = ""
                user_input[CONF_USERNAME] = self._username
                return await self._create_entry(user_input)

            cloud_api, res = await attempt_cloud_connection(self.hass, user_input)

            if not res:
                user_input[CONF_USERNAME] = self._username
                return await self._create_entry(user_input)
            errors["base"] = res["reason"]
            placeholders = {"msg": res["msg"]}

        defaults = {}
        defaults.update(user_input or {})

        return self.async_show_form(
            step_id="cloud_credentials",
            data_schema=schema_defaults(CLOUD_SETUP_SCHEMA, **defaults),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _create_entry(self, user_input):
        """Register new entry."""
        # if self._async_current_entries():
        #     return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(user_input.get(CONF_USER_ID))
        user_input[CONF_DEVICES] = {}

        return self.async_create_entry(
            title=user_input.get(CONF_USERNAME),
            data=user_input,
        )

    async def async_step_import(self, user_input):
        """Handle import from YAML."""
        _LOGGER.error(
            "Configuration via YAML file is no longer supported by this integration."
        )


class LocalTuyaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for LocalTuya integration."""

    def __init__(self, config_entry=None):
        """Initialize localtuya options flow.

        Note: In HA 2025.x, config_entry is automatically set by parent class
        AFTER __init__ completes. We must NOT access self.config_entry during
        __init__ as it raises ValueError.

        For backwards compatibility with older HA versions (<2025.x), we store
        the parameter and set it later if needed.
        """
        # Store parameter for backwards compatibility with older HA versions
        # DO NOT access self.config_entry here - it's not available yet in HA 2025.x
        self._config_entry_param = config_entry
        self.selected_device = None
        self.editing_device = False
        self.device_data = None
        self.dps_strings = []
        self.selected_platform = None
        self.discovered_devices = {}
        self.entities = []

    def _get_config_entry(self):
        """Get config_entry, handling both old and new HA versions."""
        try:
            # HA 2025.x - config_entry is set by parent class
            return self.config_entry
        except (AttributeError, ValueError):
            # Older HA versions - use stored parameter
            return self._config_entry_param

    async def async_step_init(self, user_input=None):
        """Manage basic options."""
        if user_input is not None:
            action = user_input.get(CONF_ACTION)
            if action == CONF_SETUP_CLOUD:
                return await self.async_step_cloud_setup()
            if action == CONF_ADD_DEVICE:
                return await self.async_step_add_device()
            if action == CONF_EDIT_DEVICE:
                return await self.async_step_edit_device()
            if action == CONF_SYNC_CLOUD:
                return await self.async_step_sync_from_cloud()

        # Count configured devices for display
        device_count = len(self._get_config_entry().data.get(CONF_DEVICES, {}))

        return self.async_show_form(
            step_id="init",
            data_schema=CONFIGURE_SCHEMA,
            description_placeholders={
                "version": VERSION,
                "device_count": str(device_count),
            },
        )

    async def async_step_cloud_setup(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        placeholders = {}
        if user_input is not None:
            if user_input.get(CONF_NO_CLOUD):
                new_data = self._get_config_entry().data.copy()
                new_data.update(user_input)
                for i in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_USER_ID]:
                    new_data[i] = ""
                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                return self.async_create_entry(
                    title=new_data.get(CONF_USERNAME), data={}
                )

            cloud_api, res = await attempt_cloud_connection(self.hass, user_input)

            if not res:
                new_data = self._get_config_entry().data.copy()
                new_data.update(user_input)
                cloud_devs = cloud_api.device_list
                for dev_id, dev in new_data[CONF_DEVICES].items():
                    if CONF_MODEL not in dev and dev_id in cloud_devs:
                        model = cloud_devs[dev_id].get(CONF_PRODUCT_NAME)
                        new_data[CONF_DEVICES][dev_id][CONF_MODEL] = model
                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                return self.async_create_entry(
                    title=new_data.get(CONF_USERNAME), data={}
                )
            errors["base"] = res["reason"]
            placeholders = {"msg": res["msg"]}

        defaults = self._get_config_entry().data.copy()
        defaults.update(user_input or {})
        defaults[CONF_NO_CLOUD] = False

        return self.async_show_form(
            step_id="cloud_setup",
            data_schema=schema_defaults(CLOUD_SETUP_SCHEMA, **defaults),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_add_device(self, user_input=None):
        """Handle adding a new device."""
        # Use cloud device list + UDP discovery for local IPs
        self.editing_device = False
        self.selected_device = None
        errors = {}
        if user_input is not None:
            if user_input[SELECTED_DEVICE] != CUSTOM_DEVICE:
                self.selected_device = user_input[SELECTED_DEVICE]

            return await self.async_step_configure_device()

        # Step 1: Try UDP discovery for local IPs
        self.discovered_devices = {}
        data = self.hass.data.get(DOMAIN)

        if data and DATA_DISCOVERY in data:
            self.discovered_devices = data[DATA_DISCOVERY].devices
        else:
            try:
                self.discovered_devices = await discover()
            except Exception:
                pass  # Discovery failed, continue with cloud-only

        # Step 2: Get cloud device list
        cloud_api = self.hass.data[DOMAIN][DATA_CLOUD]
        refresh_result = await cloud_api.async_get_devices_list(force_refresh=True)
        if refresh_result != "ok":
            _LOGGER.warning("Failed to refresh cloud device list: %s", refresh_result)
            errors["base"] = "cloud_api_failed"

        # Get already configured device IDs
        configured_ids = set(self._get_config_entry().data[CONF_DEVICES].keys())

        # Step 3: Get MAC addresses for devices not in discovery
        # This helps find local IP for devices that do not broadcast UDP
        missing_device_ids = [
            dev_id for dev_id in cloud_api.device_list.keys()
            if dev_id not in configured_ids and dev_id not in self.discovered_devices
        ]

        mac_to_ip_map = {}
        if missing_device_ids:
            _LOGGER.debug("Getting MAC addresses for %d devices not in UDP discovery", len(missing_device_ids))
            mac_addresses = await cloud_api.async_get_devices_mac_batch(missing_device_ids)
            for dev_id, mac in mac_addresses.items():
                local_ip = cloud_api.find_ip_by_mac(mac)
                if local_ip:
                    mac_to_ip_map[dev_id] = local_ip
                    _LOGGER.info("Found IP %s for device %s via MAC %s", local_ip, dev_id, mac)

        # Step 4: Build device list - cloud devices with local IPs from discovery or MAC lookup
        devices = {}
        for dev_id, dev_info in cloud_api.device_list.items():
            if dev_id not in configured_ids:
                # Priority: 1) UDP discovery, 2) MAC-to-IP lookup, 3) show device name
                if dev_id in self.discovered_devices:
                    dev_ip = self.discovered_devices[dev_id].get("ip", "unknown")
                elif dev_id in mac_to_ip_map:
                    dev_ip = mac_to_ip_map[dev_id]
                    # Store in discovered_devices for later use in configure_device
                    self.discovered_devices[dev_id] = {"ip": dev_ip, "gwId": dev_id, "from_mac": True}
                else:
                    dev_ip = dev_info.get("name", "no-local-ip")
                devices[dev_id] = dev_ip

        return self.async_show_form(
            step_id="add_device",
            data_schema=devices_schema(
                devices, self.hass.data[DOMAIN][DATA_CLOUD].device_list
            ),
            errors=errors,
        )

    async def async_step_edit_device(self, user_input=None):
        """Handle selecting a device to edit."""
        errors = {}
        if user_input is not None:
            self.selected_device = user_input[SELECTED_DEVICE]
            dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
            self.dps_strings = dev_conf.get(CONF_DPS_STRINGS, gen_dps_strings())
            self.entities = dev_conf[CONF_ENTITIES]
            # Go to device action menu instead of directly to configure
            return await self.async_step_device_action()

        devices = {}
        for dev_id, configured_dev in self._get_config_entry().data[CONF_DEVICES].items():
            devices[dev_id] = configured_dev[CONF_HOST]

        return self.async_show_form(
            step_id="edit_device",
            data_schema=devices_schema(
                devices, self.hass.data[DOMAIN][DATA_CLOUD].device_list, False
            ),
            errors=errors,
        )

    async def async_step_device_action(self, user_input=None):
        """Handle device action selection (quick edit, edit entities, full edit, delete)."""
        if user_input is not None:
            action = user_input.get(CONF_DEVICE_ACTION)
            if action == CONF_QUICK_EDIT:
                return await self.async_step_quick_edit()
            if action == CONF_EDIT_ENTITIES:
                return await self.async_step_entity_list()
            if action == CONF_FULL_EDIT:
                self.editing_device = True
                return await self.async_step_configure_device()
            if action == CONF_DELETE_DEVICE:
                return await self.async_step_delete_device()

        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        device_name = dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device)
        entity_count = len(dev_conf.get(CONF_ENTITIES, []))

        return self.async_show_form(
            step_id="device_action",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ACTION, default=CONF_QUICK_EDIT): vol.In(DEVICE_ACTIONS),
            }),
            description_placeholders={
                "device_name": device_name,
                "device_id": self.selected_device,
                "entity_count": str(entity_count),
            },
        )

    async def async_step_quick_edit(self, user_input=None):
        """Handle quick edit of device (host, key, protocol only)."""
        errors = {}
        if user_input is not None:
            # Save only connection parameters without touching entities
            new_data = self._get_config_entry().data.copy()
            dev_conf = new_data[CONF_DEVICES][self.selected_device]

            # Update only the quick edit fields
            dev_conf[CONF_HOST] = user_input[CONF_HOST]
            dev_conf[CONF_LOCAL_KEY] = user_input[CONF_LOCAL_KEY]
            dev_conf[CONF_PROTOCOL_VERSION] = user_input[CONF_PROTOCOL_VERSION]
            dev_conf[CONF_ENABLE_DEBUG] = user_input.get(CONF_ENABLE_DEBUG, False)
            if user_input.get(CONF_FRIENDLY_NAME):
                dev_conf[CONF_FRIENDLY_NAME] = user_input[CONF_FRIENDLY_NAME]

            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            self.hass.config_entries.async_update_entry(
                self._get_config_entry(),
                data=new_data,
            )
            return self.async_create_entry(title="", data={})

        # Pre-fill with current values
        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        defaults = {
            CONF_HOST: dev_conf.get(CONF_HOST, ""),
            CONF_LOCAL_KEY: dev_conf.get(CONF_LOCAL_KEY, ""),
            CONF_PROTOCOL_VERSION: dev_conf.get(CONF_PROTOCOL_VERSION, "3.3"),
            CONF_FRIENDLY_NAME: dev_conf.get(CONF_FRIENDLY_NAME, ""),
            CONF_ENABLE_DEBUG: dev_conf.get(CONF_ENABLE_DEBUG, False),
        }

        # Check if cloud has newer local_key
        cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list
        cloud_note = ""
        if self.selected_device in cloud_devs:
            cloud_key = cloud_devs[self.selected_device].get(CONF_LOCAL_KEY, "")
            if cloud_key and cloud_key != defaults[CONF_LOCAL_KEY]:
                defaults[CONF_LOCAL_KEY] = cloud_key
                cloud_note = "\n\n**Note:** A new local_key was detected from cloud!"

        return self.async_show_form(
            step_id="quick_edit",
            data_schema=schema_defaults(QUICK_EDIT_SCHEMA, **defaults),
            errors=errors,
            description_placeholders={
                "device_name": dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device),
                "device_id": self.selected_device,
                "cloud_note": cloud_note,
            },
        )

    async def async_step_entity_list(self, user_input=None):
        """Handle entity list for selecting one to edit or delete."""
        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_ENTITY)
            if selected == CONF_ADD_NEW_ENTITY:
                # Add new entity - go to pick entity type
                self.editing_device = False
                dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
                self.device_data = dev_conf.copy()
                self.device_data[CONF_DEVICE_ID] = self.selected_device
                return await self.async_step_pick_entity_type()
            else:
                # Entity selected - go to entity action menu
                entity_id = int(selected.split(":")[0])
                self._selected_entity_id = entity_id
                return await self.async_step_entity_action()

        # Build entity list
        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        entities = dev_conf.get(CONF_ENTITIES, [])

        entity_options = {
            f"{ent[CONF_ID]}: {ent.get(CONF_FRIENDLY_NAME, 'Unknown')} ({ent.get(CONF_PLATFORM, 'unknown')})": f"{ent[CONF_ID]}: {ent.get(CONF_FRIENDLY_NAME, 'Unknown')}"
            for ent in entities
        }
        entity_options[CONF_ADD_NEW_ENTITY] = "➕ Add new entity"

        return self.async_show_form(
            step_id="entity_list",
            data_schema=vol.Schema({
                vol.Required(CONF_SELECTED_ENTITY): vol.In(entity_options),
            }),
            description_placeholders={
                "device_name": dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device),
                "entity_count": str(len(entities)),
            },
        )

    async def async_step_entity_action(self, user_input=None):
        """Handle entity action selection (edit or delete)."""
        if user_input is not None:
            action = user_input.get("entity_action")
            if action == "edit":
                return await self.async_step_edit_single_entity()
            elif action == "delete":
                return await self.async_step_delete_entity()

        # Find entity info
        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        entity_info = None
        for ent in dev_conf.get(CONF_ENTITIES, []):
            if ent[CONF_ID] == self._selected_entity_id:
                entity_info = ent
                break

        if entity_info is None:
            return self.async_abort(reason="entity_not_found")

        entity_actions = {
            "edit": "✏️ Edit entity",
            "delete": "🗑️ Delete entity",
        }

        return self.async_show_form(
            step_id="entity_action",
            data_schema=vol.Schema({
                vol.Required("entity_action", default="edit"): vol.In(entity_actions),
            }),
            description_placeholders={
                "entity_name": entity_info.get(CONF_FRIENDLY_NAME, "Unknown"),
                "entity_id": str(self._selected_entity_id),
                "platform": entity_info.get(CONF_PLATFORM, "unknown"),
                "device_name": dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device),
            },
        )

    async def async_step_edit_single_entity(self, user_input=None):
        """Handle editing a single entity."""
        errors = {}

        # Use _selected_entity_id which was set in entity_action step
        entity_id_to_edit = getattr(self, '_selected_entity_id', None)

        if user_input is not None and entity_id_to_edit is not None:
            # Save the edited entity
            new_data = self._get_config_entry().data.copy()
            dev_conf = new_data[CONF_DEVICES][self.selected_device]

            # Find and update the entity
            for i, ent in enumerate(dev_conf[CONF_ENTITIES]):
                if int(ent[CONF_ID]) == int(entity_id_to_edit):
                    updated_entity = strip_dps_values(user_input, self.dps_strings)
                    updated_entity[CONF_ID] = entity_id_to_edit
                    updated_entity[CONF_PLATFORM] = ent[CONF_PLATFORM]
                    dev_conf[CONF_ENTITIES][i] = updated_entity
                    break

            new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
            self.hass.config_entries.async_update_entry(
                self._get_config_entry(),
                data=new_data,
            )
            return self.async_create_entry(title="", data={})

        if entity_id_to_edit is None:
            return self.async_abort(reason="entity_not_found")

        # Find the entity to edit
        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        current_entity = None
        for ent in dev_conf.get(CONF_ENTITIES, []):
            if int(ent[CONF_ID]) == int(entity_id_to_edit):
                current_entity = ent
                break

        if current_entity is None:
            return self.async_abort(reason="entity_not_found")

        schema = platform_schema(
            current_entity[CONF_PLATFORM], self.dps_strings, allow_id=False
        )

        return self.async_show_form(
            step_id="edit_single_entity",
            data_schema=schema_defaults(schema, self.dps_strings, **current_entity),
            errors=errors,
            description_placeholders={
                "entity_name": current_entity.get(CONF_FRIENDLY_NAME, "Unknown"),
                "entity_id": str(entity_id_to_edit),
                "platform": current_entity.get(CONF_PLATFORM, "unknown"),
            },
        )

    async def async_step_delete_entity(self, user_input=None):
        """Handle deleting a single entity."""
        # Use _selected_entity_id which was set in entity_action step
        entity_id_to_delete = getattr(self, '_selected_entity_id', None)

        if user_input is not None:
            if user_input.get("confirm_delete") and entity_id_to_delete is not None:
                # Delete the entity
                new_data = self._get_config_entry().data.copy()
                dev_conf = new_data[CONF_DEVICES][self.selected_device]

                # Find and remove the entity from config
                entity_to_delete = None
                for i, ent in enumerate(dev_conf[CONF_ENTITIES]):
                    # Compare as integers to handle both string and int IDs
                    if int(ent[CONF_ID]) == int(entity_id_to_delete):
                        entity_to_delete = dev_conf[CONF_ENTITIES].pop(i)
                        break

                # Remove from entity registry
                if entity_to_delete:
                    ent_reg = er.async_get(self.hass)
                    entry_id = self._get_config_entry().entry_id
                    # Find entity by exact unique_id: local_{device_id}_{dp_id}
                    expected_unique_id = f"local_{self.selected_device}_{entity_id_to_delete}"
                    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry_id):
                        if reg_entry.unique_id == expected_unique_id:
                            ent_reg.async_remove(reg_entry.entity_id)
                            _LOGGER.info(f"Removed entity {reg_entry.entity_id} from registry")
                            break

                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                # Return to init (success)
                return self.async_create_entry(title="", data={})
            else:
                # User cancelled - go back to entity list
                return await self.async_step_entity_list()

        # Find the entity info for confirmation dialog
        if entity_id_to_delete is None:
            return self.async_abort(reason="entity_not_found")

        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        entity_info = None
        for ent in dev_conf.get(CONF_ENTITIES, []):
            # Compare as integers to handle both string and int IDs
            if int(ent[CONF_ID]) == int(entity_id_to_delete):
                entity_info = ent
                break

        if entity_info is None:
            return self.async_abort(reason="entity_not_found")

        return self.async_show_form(
            step_id="delete_entity",
            data_schema=vol.Schema({
                vol.Required("confirm_delete", default=False): bool,
            }),
            description_placeholders={
                "entity_name": entity_info.get(CONF_FRIENDLY_NAME, "Unknown"),
                "entity_id": str(entity_id_to_delete),
                "platform": entity_info.get(CONF_PLATFORM, "unknown"),
                "device_name": dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device),
            },
        )

    async def async_step_delete_device(self, user_input=None):
        """Handle device deletion confirmation."""
        if user_input is not None:
            if user_input.get("confirm_delete"):
                # Delete the device
                new_data = self._get_config_entry().data.copy()
                del new_data[CONF_DEVICES][self.selected_device]
                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

                # Remove entities from registry
                ent_reg = er.async_get(self.hass)
                entry_id = self._get_config_entry().entry_id
                reg_entities = {
                    ent.unique_id: ent.entity_id
                    for ent in er.async_entries_for_config_entry(ent_reg, entry_id)
                    if self.selected_device in ent.unique_id
                }
                for entity_id in reg_entities.values():
                    ent_reg.async_remove(entity_id)

                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                return self.async_create_entry(title="", data={})
            else:
                # User cancelled - go back to init
                return await self.async_step_init()

        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        device_name = dev_conf.get(CONF_FRIENDLY_NAME, self.selected_device)
        entity_count = len(dev_conf.get(CONF_ENTITIES, []))

        return self.async_show_form(
            step_id="delete_device",
            data_schema=vol.Schema({
                vol.Required("confirm_delete", default=False): bool,
            }),
            description_placeholders={
                "device_name": device_name,
                "device_id": self.selected_device,
                "entity_count": str(entity_count),
            },
        )

    async def async_step_sync_from_cloud(self, user_input=None):
        """Handle syncing local keys from cloud with smart verification.

        This function now verifies keys before syncing:
        - If current key works, it WON'T be overwritten (even if cloud has different key)
        - Only updates keys where current key is broken AND cloud key works
        - Shows detailed status for each device
        """
        errors = {}

        cloud_api = self.hass.data[DOMAIN][DATA_CLOUD]
        no_cloud = self._get_config_entry().data.get(CONF_NO_CLOUD, True)

        if no_cloud:
            return self.async_abort(
                reason="no_cloud_configured",
                description_placeholders={},
            )

        if user_input is not None:
            if user_input.get("apply_changes"):
                # Apply only verified changes (recommendation == "update")
                new_data = self._get_config_entry().data.copy()
                sync_result = await cloud_api.async_sync_local_keys(
                    new_data[CONF_DEVICES], verify_keys=True
                )

                updated_count = 0
                for dev_id, info in sync_result.items():
                    # Only update if recommendation is "update" (verified that new key works)
                    if info.get("recommendation") == "update" and info["found"]:
                        new_data[CONF_DEVICES][dev_id][CONF_LOCAL_KEY] = info["new_key"]
                        updated_count += 1

                if updated_count > 0:
                    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                    self.hass.config_entries.async_update_entry(
                        self._get_config_entry(),
                        data=new_data,
                    )

                return self.async_create_entry(title="", data={})
            else:
                return await self.async_step_init()

        # Get sync preview with key verification
        configured_devices = self._get_config_entry().data.get(CONF_DEVICES, {})
        sync_result = await cloud_api.async_sync_local_keys(
            configured_devices, verify_keys=True
        )

        # Count by recommendation
        total_devices = len(sync_result)
        update_count = sum(1 for info in sync_result.values() if info.get("recommendation") == "update")
        keep_count = sum(1 for info in sync_result.values() if info.get("recommendation") == "keep")
        manual_count = sum(1 for info in sync_result.values() if info.get("recommendation") == "manual")
        not_found = sum(1 for info in sync_result.values() if not info["found"])

        # Build detailed description
        changes_list = []
        for dev_id, info in sync_result.items():
            recommendation = info.get("recommendation", "keep")
            old_works = info.get("old_key_works")
            new_works = info.get("new_key_works")

            if recommendation == "update":
                # Current broken, cloud works - will update
                changes_list.append(f"🔄 **{info['name']}** - will UPDATE (current key broken, cloud key works)")
            elif recommendation == "manual":
                # Both broken - needs manual fix
                changes_list.append(f"⚠️ **{info['name']}** - NEEDS MANUAL FIX (both keys broken)")
            elif recommendation == "keep":
                if not info["found"]:
                    changes_list.append(f"❌ {info['name']} - not found in cloud")
                elif old_works is True:
                    changes_list.append(f"✅ {info['name']} - current key works, keeping")
                elif info["old_key"] == info["new_key"]:
                    changes_list.append(f"✅ {info['name']} - keys match")
                else:
                    changes_list.append(f"✅ {info['name']} - unchanged")

        changes_text = "\n".join(changes_list[:15])  # Show more items
        if len(changes_list) > 15:
            changes_text += f"\n... and {len(changes_list) - 15} more"

        # Add summary
        summary = f"\n\n**Summary:** {update_count} to update, {keep_count} working, {manual_count} need manual fix, {not_found} not in cloud"
        changes_text += summary

        return self.async_show_form(
            step_id="sync_from_cloud",
            data_schema=vol.Schema({
                vol.Required("apply_changes", default=update_count > 0): bool,
            }),
            errors=errors,
            description_placeholders={
                "total_devices": str(total_devices),
                "changed_count": str(update_count),
                "not_found": str(not_found),
                "changes_list": changes_text,
            },
        )

    async def async_step_configure_device(self, user_input=None):
        """Handle input of basic info."""
        errors = {}
        dev_id = self.selected_device
        if user_input is not None:
            try:
                self.device_data = user_input.copy()
                if dev_id is not None:
                    # self.device_data[CONF_PRODUCT_KEY] = self.devices[
                    #     self.selected_device
                    # ]["productKey"]
                    cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list
                    if dev_id in cloud_devs:
                        self.device_data[CONF_MODEL] = cloud_devs[dev_id].get(
                            CONF_PRODUCT_NAME
                        )
                if self.editing_device:
                    if user_input[CONF_ENABLE_ADD_ENTITIES]:
                        self.editing_device = False
                        user_input[CONF_DEVICE_ID] = dev_id
                        self.device_data.update(
                            {
                                CONF_DEVICE_ID: dev_id,
                                CONF_DPS_STRINGS: self.dps_strings,
                            }
                        )
                        return await self.async_step_pick_entity_type()

                    self.device_data.update(
                        {
                            CONF_DEVICE_ID: dev_id,
                            CONF_DPS_STRINGS: self.dps_strings,
                            CONF_ENTITIES: [],
                        }
                    )
                    if len(user_input[CONF_ENTITIES]) == 0:
                        return self.async_abort(
                            reason="no_entities",
                            description_placeholders={},
                        )
                    if user_input[CONF_ENTITIES]:
                        entity_ids = [
                            int(entity.split(":")[0])
                            for entity in user_input[CONF_ENTITIES]
                        ]
                        device_config = self._get_config_entry().data[CONF_DEVICES][dev_id]
                        self.entities = [
                            entity
                            for entity in device_config[CONF_ENTITIES]
                            if entity[CONF_ID] in entity_ids
                        ]
                        return await self.async_step_configure_entity()

                self.dps_strings = await validate_input(self.hass, user_input)
                return await self.async_step_pick_entity_type()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except EmptyDpsList:
                errors["base"] = "empty_dps"
            except Exception as ex:
                _LOGGER.exception("Unexpected exception: %s", ex)
                errors["base"] = "unknown"

        defaults = {}
        if self.editing_device:
            # If selected device exists as a config entry, load config from it
            defaults = self._get_config_entry().data[CONF_DEVICES][dev_id].copy()
            cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list
            placeholders = {"for_device": f" for device `{dev_id}`"}
            if dev_id in cloud_devs:
                cloud_local_key = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
                if defaults[CONF_LOCAL_KEY] != cloud_local_key:
                    _LOGGER.info(
                        "New local_key detected: new %s vs old %s",
                        cloud_local_key,
                        defaults[CONF_LOCAL_KEY],
                    )
                    defaults[CONF_LOCAL_KEY] = cloud_devs[dev_id].get(CONF_LOCAL_KEY)
                    note = "\nNOTE: a new local_key has been retrieved using cloud API"
                    placeholders = {"for_device": f" for device `{dev_id}`.{note}"}
            defaults[CONF_ENABLE_ADD_ENTITIES] = True
            schema = schema_defaults(options_schema(self.entities), **defaults)
        else:
            defaults[CONF_PROTOCOL_VERSION] = "3.3"
            defaults[CONF_HOST] = ""
            defaults[CONF_DEVICE_ID] = ""
            defaults[CONF_LOCAL_KEY] = ""
            defaults[CONF_FRIENDLY_NAME] = ""
            if dev_id is not None:
                # Insert default values from discovery and/or cloud
                cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list

                # Try discovery first for local IP
                if dev_id in self.discovered_devices:
                    device = self.discovered_devices[dev_id]
                    defaults[CONF_HOST] = device.get("ip", "")
                    defaults[CONF_DEVICE_ID] = device.get("gwId", dev_id)
                    defaults[CONF_PROTOCOL_VERSION] = device.get("version", "3.3")
                else:
                    # No discovery - use device ID, user must enter IP manually
                    defaults[CONF_DEVICE_ID] = dev_id

                # Always try cloud for local_key and name
                if dev_id in cloud_devs:
                    defaults[CONF_LOCAL_KEY] = cloud_devs[dev_id].get(CONF_LOCAL_KEY, "")
                    defaults[CONF_FRIENDLY_NAME] = cloud_devs[dev_id].get(CONF_NAME, "")
            schema = schema_defaults(DEVICE_SCHEMA, **defaults)

            placeholders = {"for_device": ""}

        return self.async_show_form(
            step_id="configure_device",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_pick_entity_type(self, user_input=None):
        """Handle asking if user wants to add another entity."""
        if user_input is not None:
            if user_input.get(NO_ADDITIONAL_ENTITIES):
                config = {
                    **self.device_data,
                    CONF_DPS_STRINGS: self.dps_strings,
                    CONF_ENTITIES: self.entities,
                }

                dev_id = self.device_data.get(CONF_DEVICE_ID)

                new_data = self._get_config_entry().data.copy()
                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                new_data[CONF_DEVICES].update({dev_id: config})

                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                return self.async_create_entry(title="", data={})

            self.selected_platform = user_input[PLATFORM_TO_ADD]
            return await self.async_step_configure_entity()

        # Add a checkbox that allows bailing out from config flow if at least one
        # entity has been added
        schema = PICK_ENTITY_SCHEMA
        if self.selected_platform is not None:
            schema = schema.extend(
                {vol.Required(NO_ADDITIONAL_ENTITIES, default=True): bool}
            )

        return self.async_show_form(step_id="pick_entity_type", data_schema=schema)

    def available_dps_strings(self):
        """Return list of DPs use by the device's entities."""
        available_dps = []
        used_dps = [str(entity[CONF_ID]) for entity in self.entities]
        for dp_string in self.dps_strings:
            dp = dp_string.split(" ")[0]
            if dp not in used_dps:
                available_dps.append(dp_string)
        return available_dps

    async def async_step_entity(self, user_input=None):
        """Manage entity settings."""
        errors = {}
        if user_input is not None:
            entity = strip_dps_values(user_input, self.dps_strings)
            entity[CONF_ID] = self.current_entity[CONF_ID]
            entity[CONF_PLATFORM] = self.current_entity[CONF_PLATFORM]
            self.device_data[CONF_ENTITIES].append(entity)

            if len(self.entities) == len(self.device_data[CONF_ENTITIES]):
                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    title=self.device_data[CONF_FRIENDLY_NAME],
                    data=self.device_data,
                )
                return self.async_create_entry(title="", data={})

        schema = platform_schema(
            self.current_entity[CONF_PLATFORM], self.dps_strings, allow_id=False
        )
        return self.async_show_form(
            step_id="entity",
            errors=errors,
            data_schema=schema_defaults(
                schema, self.dps_strings, **self.current_entity
            ),
            description_placeholders={
                "id": self.current_entity[CONF_ID],
                "platform": self.current_entity[CONF_PLATFORM],
            },
        )

    async def async_step_configure_entity(self, user_input=None):
        """Manage entity settings."""
        errors = {}
        if user_input is not None:
            if self.editing_device:
                entity = strip_dps_values(user_input, self.dps_strings)
                entity[CONF_ID] = self.current_entity[CONF_ID]
                entity[CONF_PLATFORM] = self.current_entity[CONF_PLATFORM]
                self.device_data[CONF_ENTITIES].append(entity)

                if len(self.entities) == len(self.device_data[CONF_ENTITIES]):
                    # finished editing device. Let's store the new config entry....
                    dev_id = self.device_data[CONF_DEVICE_ID]
                    new_data = self._get_config_entry().data.copy()
                    entry_id = self._get_config_entry().entry_id
                    # removing entities from registry (they will be recreated)
                    ent_reg = er.async_get(self.hass)
                    reg_entities = {
                        ent.unique_id: ent.entity_id
                        for ent in er.async_entries_for_config_entry(ent_reg, entry_id)
                        if dev_id in ent.unique_id
                    }
                    for entity_id in reg_entities.values():
                        ent_reg.async_remove(entity_id)

                    new_data[CONF_DEVICES][dev_id] = self.device_data
                    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                    self.hass.config_entries.async_update_entry(
                        self._get_config_entry(),
                        data=new_data,
                    )
                    return self.async_create_entry(title="", data={})
            else:
                user_input[CONF_PLATFORM] = self.selected_platform
                self.entities.append(strip_dps_values(user_input, self.dps_strings))
                # new entity added. Let's check if there are more left...
                user_input = None
                if len(self.available_dps_strings()) == 0:
                    user_input = {NO_ADDITIONAL_ENTITIES: True}
                return await self.async_step_pick_entity_type(user_input)

        if self.editing_device:
            schema = platform_schema(
                self.current_entity[CONF_PLATFORM], self.dps_strings, allow_id=False
            )
            schema = schema_defaults(schema, self.dps_strings, **self.current_entity)
            placeholders = {
                "entity": f"entity with DP {self.current_entity[CONF_ID]}",
                "platform": self.current_entity[CONF_PLATFORM],
            }
        else:
            available_dps = self.available_dps_strings()
            schema = platform_schema(self.selected_platform, available_dps)
            placeholders = {
                "entity": "an entity",
                "platform": self.selected_platform,
            }

        return self.async_show_form(
            step_id="configure_entity",
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_yaml_import(self, user_input=None):
        """Manage YAML imports."""
        _LOGGER.error(
            "Configuration via YAML file is no longer supported by this integration."
        )
        # if user_input is not None:
        #     return self.async_create_entry(title="", data={})
        # return self.async_show_form(step_id="yaml_import")

    @property
    def current_entity(self):
        """Existing configuration for entity currently being edited."""
        return self.entities[len(self.device_data[CONF_ENTITIES])]


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class EmptyDpsList(exceptions.HomeAssistantError):
    """Error to indicate no datapoints found."""
