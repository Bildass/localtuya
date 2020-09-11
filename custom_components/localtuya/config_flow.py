"""Config flow for LocalTuya integration integration."""
import logging
from importlib import import_module

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_ID,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_FRIENDLY_NAME,
    CONF_PLATFORM,
    CONF_SWITCHES,
)

from . import pytuya
from .const import (  # pylint: disable=unused-import
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_TO_ADD = "platform_to_add"
NO_ADDITIONAL_PLATFORMS = "no_additional_platforms"

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_FRIENDLY_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(["3.1", "3.3"]),
    }
)

PICK_ENTITY_SCHEMA = vol.Schema(
    {vol.Required(PLATFORM_TO_ADD, default=PLATFORMS[0]): vol.In(PLATFORMS)}
)


def platform_schema(dps, additional_fields):
    """Generate input validation schema for a platform."""
    dps_list = vol.In([f"{id} (value: {value})" for id, value in dps.items()])
    return vol.Schema(
        {
            vol.Required(CONF_ID): dps_list,
            vol.Required(CONF_FRIENDLY_NAME): str,
        }
    ).extend({conf: dps_list for conf in additional_fields})


def strip_dps_values(user_input, fields):
    """Remove values and keep only index for DPS config items."""
    for field in [CONF_ID] + fields:
        user_input[field] = user_input[field].split(" ")[0]
    return user_input


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    pytuyadevice = pytuya.PytuyaDevice(
        data[CONF_DEVICE_ID], data[CONF_HOST], data[CONF_LOCAL_KEY], data[CONF_NAME]
    )
    pytuyadevice.set_version(float(data[CONF_PROTOCOL_VERSION]))
    pytuyadevice.set_dpsUsed({})
    try:
        data = await hass.async_add_executor_job(pytuyadevice.status)
    except (ConnectionRefusedError, ConnectionResetError):
        raise CannotConnect
    except ValueError:
        raise InvalidAuth
    return data["dps"]


class LocaltuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalTuya integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize a new LocaltuyaConfigFlow."""
        self.basic_info = None
        self.dps_data = None
        self.platform = None
        self.platform_dps_fields = None
        self.entities = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                self.basic_info = user_input
                self.dps_data = await validate_input(self.hass, user_input)
                return await self.async_step_pick_entity_type()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_pick_entity_type(self, user_input=None):
        """Handle asking if user wants to add another entity."""
        if user_input is not None:
            if user_input.get(NO_ADDITIONAL_PLATFORMS):
                config = {**self.basic_info, CONF_ENTITIES: self.entities}
                return self.async_create_entry(title=config[CONF_NAME], data=config)

            self._set_platform(user_input[PLATFORM_TO_ADD])
            return await self.async_step_add_entity()

        # Add a checkbox that allows bailing out from config flow iff at least one
        # entity has been added
        schema = PICK_ENTITY_SCHEMA
        if self.platform is not None:
            schema = schema.extend(
                {vol.Required(NO_ADDITIONAL_PLATFORMS, default=True): bool}
            )

        return self.async_show_form(step_id="pick_entity_type", data_schema=schema)

    async def async_step_add_entity(self, user_input=None):
        """Handle adding a new entity."""
        errors = {}
        if user_input is not None:
            already_configured = any(
                switch[CONF_ID] == user_input[CONF_ID] for switch in self.entities
            )
            if not already_configured:
                user_input[CONF_PLATFORM] = self.platform
                self.entities.append(
                    strip_dps_values(user_input, self.platform_dps_fields)
                )
                return await self.async_step_pick_entity_type()

            errors["base"] = "entity_already_configured"

        return self.async_show_form(
            step_id="add_entity",
            data_schema=platform_schema(self.dps_data, self.platform_dps_fields),
            errors=errors,
            description_placeholders={"platform": self.platform},
        )

    async def async_step_import(self, user_input):
        """Handle import from YAML."""

        def _convert_entity(conf):
            converted = {
                CONF_ID: conf[CONF_ID],
                CONF_FRIENDLY_NAME: conf[CONF_FRIENDLY_NAME],
                CONF_PLATFORM: self.platform,
            }
            for field in self.platform_dps_fields:
                converted[str(field)] = conf[field]
            return converted

        await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
        self._set_platform(user_input[CONF_PLATFORM])

        if len(user_input[CONF_SWITCHES]) > 0:
            for switch_conf in user_input[CONF_SWITCHES].values():
                self.entities.append(_convert_entity(switch_conf))
        else:
            self.entities.append(_convert_entity(user_input))

        #print('ENTITIES: [{}] '.format(self.entities))
        config = {
            CONF_NAME:  f"{user_input[CONF_FRIENDLY_NAME]} (YAML)",
            CONF_FRIENDLY_NAME: f"{user_input[CONF_FRIENDLY_NAME]} (YAML)",
            CONF_HOST: user_input[CONF_HOST],
            CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
            CONF_LOCAL_KEY: user_input[CONF_LOCAL_KEY],
            CONF_PROTOCOL_VERSION: user_input[CONF_PROTOCOL_VERSION],
            CONF_ENTITIES: self.entities,
        }
        self._abort_if_unique_id_configured(updates=config)
        return self.async_create_entry(title=config[CONF_NAME], data=config)

    def _set_platform(self, platform):
        integration_module = ".".join(__name__.split(".")[:-1])
        self.platform = platform
        self.platform_dps_fields = import_module("." + platform, integration_module).DPS_FIELDS


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
