"""Config flow for LocalTuya integration integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_SWITCHES,
    CONF_ID,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_FRIENDLY_NAME,
)
import homeassistant.helpers.config_validation as cv

from . import pytuya
from .const import (  # pylint: disable=unused-import
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    CONF_CURRENT,
    CONF_CURRENT_CONSUMPTION,
    CONF_VOLTAGE,
    DOMAIN,
    DEVICE_TYPE_POWER_OUTLET,
)

_LOGGER = logging.getLogger(__name__)

ADD_ANOTHER_SWITCH = "add_another_switch"

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
        vol.Required(CONF_PROTOCOL_VERSION, default="3.3"): vol.In(["3.1", "3.3"]),
        vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_POWER_OUTLET): vol.In(
            [DEVICE_TYPE_POWER_OUTLET]
        ),
    }
)

POWER_OUTLET_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID, default=1): int,
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_FRIENDLY_NAME): str,
        vol.Required(CONF_CURRENT, default=18): int,
        vol.Required(CONF_CURRENT_CONSUMPTION, default=19): int,
        vol.Required(CONF_VOLTAGE, default=20): int,
        vol.Required(ADD_ANOTHER_SWITCH, default=False): bool,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    pytuyadevice = pytuya.OutletDevice(
        data[CONF_DEVICE_ID], data[CONF_HOST], data[CONF_LOCAL_KEY]
    )
    pytuyadevice.set_version(float(data[CONF_PROTOCOL_VERSION]))
    pytuyadevice.set_dpsUsed({"1": None})
    try:
        await hass.async_add_executor_job(pytuyadevice.status)
    except ConnectionRefusedError:
        raise CannotConnect
    except ValueError:
        raise InvalidAuth
    return data


class LocaltuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LocalTuya integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize a new LocaltuyaConfigFlow."""
        self.basic_info = None
        self.switches = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            try:
                self.basic_info = await validate_input(self.hass, user_input)
                if self.basic_info[CONF_DEVICE_TYPE] == "Power Outlet":
                    return await self.async_step_power_outlet()

                return self.async_abort(reason="unsupported_device_type")
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

    async def async_step_power_outlet(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            already_configured = any(
                switch[CONF_ID] == user_input[CONF_ID] for switch in self.switches
            )
            if not already_configured:
                add_another_switch = user_input.pop(ADD_ANOTHER_SWITCH)
                self.switches.append(user_input)
                if not add_another_switch:
                    config = {**self.basic_info, CONF_SWITCHES: self.switches}
                    return self.async_create_entry(title=config[CONF_NAME], data=config)
            else:
                errors["base"] = "switch_already_configured"

        return self.async_show_form(
            step_id="power_outlet",
            data_schema=POWER_OUTLET_SCHEMA,
            errors=errors,
            description_placeholders={"number": len(self.switches) + 1},
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
