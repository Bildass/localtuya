"""Config flow for LocalTuya 2.0 integration.

This module provides the main config flow classes for LocalTuya.
The implementation is split into multiple mixin classes for better maintainability:

- config_flow_helpers.py: Schema builders and validation functions
- config_flow_cloud.py: CloudOperationsMixin (cloud setup, sync, QR auth)
- config_flow_device.py: DeviceOperationsMixin (add/edit/delete devices)
- config_flow_entity.py: EntityOperationsMixin (add/edit/delete entities)
- exceptions.py: Custom exception classes
"""
import logging

from homeassistant import config_entries
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICES,
    CONF_USERNAME,
)
from homeassistant.core import callback

from .const import (
    CONF_ACTION,
    CONF_ADD_DEVICE,
    CONF_EDIT_DEVICE,
    CONF_NO_CLOUD,
    CONF_SETUP_CLOUD,
    CONF_SYNC_CLOUD,
    CONF_QR_AUTH,
    CONF_USER_ID,
    DOMAIN,
    VERSION,
)

# Import helpers (re-export for backwards compatibility with __init__.py)
from .config_flow_helpers import (
    ENTRIES_VERSION,
    CONFIGURE_SCHEMA,
    CLOUD_SETUP_SCHEMA,
    schema_defaults,
    attempt_cloud_connection,
    config_schema,
)

# Import mixins
from .config_flow_cloud import CloudOperationsMixin
from .config_flow_device import DeviceOperationsMixin
from .config_flow_entity import EntityOperationsMixin

# Import exceptions for backwards compatibility
from .exceptions import CannotConnect, InvalidAuth, EmptyDpsList

_LOGGER = logging.getLogger(__name__)


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


class LocalTuyaOptionsFlowHandler(
    CloudOperationsMixin,
    DeviceOperationsMixin,
    EntityOperationsMixin,
    config_entries.OptionsFlow
):
    """Handle options flow for LocalTuya integration.

    This class uses multiple mixin classes to organize functionality:
    - CloudOperationsMixin: Cloud setup, sync, QR authentication
    - DeviceOperationsMixin: Add, edit, delete devices
    - EntityOperationsMixin: Add, edit, delete entities
    """

    def __init__(self, config_entry=None):
        """Initialize localtuya options flow.

        Note: In HA 2025.x, config_entry is automatically set by parent class
        AFTER __init__ completes. We must NOT access self.config_entry during
        __init__ as it raises ValueError.

        For backwards compatibility with older HA versions (<2025.x), we store
        the parameter and set it later if needed.
        """
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
            return self.config_entry
        except (AttributeError, ValueError):
            return self._config_entry_param

    async def async_step_init(self, user_input=None):
        """Manage basic options - main menu."""
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
            if action == CONF_QR_AUTH:
                return await self.async_step_qr_auth()

        device_count = len(self._get_config_entry().data.get(CONF_DEVICES, {}))

        return self.async_show_form(
            step_id="init",
            data_schema=CONFIGURE_SCHEMA,
            description_placeholders={
                "version": VERSION,
                "device_count": str(device_count),
            },
        )

    async def async_step_yaml_import(self, user_input=None):
        """Manage YAML imports (deprecated)."""
        _LOGGER.error(
            "Configuration via YAML file is no longer supported by this integration."
        )
