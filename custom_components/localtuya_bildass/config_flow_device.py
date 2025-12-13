"""Device operations mixin for LocalTuya 2.0 config flow."""
import logging
import time

import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .const import (
    ATTR_UPDATED_AT,
    CONF_DEVICE_ACTION,
    CONF_DPS_STRINGS,
    CONF_EDIT_ENTITIES,
    CONF_ENABLE_DEBUG,
    CONF_FORCE_ADD,
    CONF_SKIP_CONNECT,
    CONF_FULL_EDIT,
    CONF_LOCAL_KEY,
    CONF_MANUAL_DPS,
    CONF_MODEL,
    CONF_PRODUCT_NAME,
    CONF_PROTOCOL_VERSION,
    CONF_QUICK_EDIT,
    CONF_RESET_DPIDS,
    CONF_DELETE_DEVICE,
    CONF_ENABLE_ADD_ENTITIES,
    DATA_CLOUD,
    DATA_DISCOVERY,
    DOMAIN,
)
from .config_flow_helpers import (
    QUICK_EDIT_SCHEMA,
    DEVICE_SCHEMA,
    DEVICE_ACTIONS,
    CUSTOM_DEVICE,
    SELECTED_DEVICE,
    CONF_USE_TEMPLATE,
    devices_schema,
    options_schema,
    schema_defaults,
    gen_dps_strings,
    validate_input,
)
from .discovery import discover
from .exceptions import CannotConnect, InvalidAuth, EmptyDpsList
from . import device_library

_LOGGER = logging.getLogger(__name__)


class DeviceOperationsMixin:
    """Mixin for device operations in OptionsFlowHandler."""

    async def async_step_add_device(self, user_input=None):
        """Handle adding a new device."""
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
                pass

        # Step 2: Get cloud device list
        cloud_api = self.hass.data[DOMAIN][DATA_CLOUD]
        refresh_result = await cloud_api.async_get_devices_list(force_refresh=True)
        if refresh_result != "ok":
            _LOGGER.warning("Failed to refresh cloud device list: %s", refresh_result)
            errors["base"] = "cloud_api_failed"

        # Get already configured device IDs
        configured_ids = set(self._get_config_entry().data[CONF_DEVICES].keys())

        # Step 3: Get MAC addresses for devices not in discovery
        missing_device_ids = [
            dev_id for dev_id in cloud_api.device_list.keys()
            if dev_id not in configured_ids and dev_id not in self.discovered_devices
        ]

        mac_to_ip_map = {}
        if missing_device_ids:
            _LOGGER.debug(
                "Getting MAC addresses for %d devices not in UDP discovery",
                len(missing_device_ids)
            )
            mac_addresses = await cloud_api.async_get_devices_mac_batch(missing_device_ids)
            for dev_id, mac in mac_addresses.items():
                local_ip = cloud_api.find_ip_by_mac(mac)
                if local_ip:
                    mac_to_ip_map[dev_id] = local_ip
                    _LOGGER.info(
                        "Found IP %s for device %s via MAC %s",
                        local_ip, dev_id, mac
                    )

        # Step 4: Build device list
        devices = {}
        for dev_id, dev_info in cloud_api.device_list.items():
            if dev_id not in configured_ids:
                if dev_id in self.discovered_devices:
                    dev_ip = self.discovered_devices[dev_id].get("ip", "unknown")
                elif dev_id in mac_to_ip_map:
                    dev_ip = mac_to_ip_map[dev_id]
                    self.discovered_devices[dev_id] = {
                        "ip": dev_ip,
                        "gwId": dev_id,
                        "from_mac": True
                    }
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
            new_data = self._get_config_entry().data.copy()
            dev_conf = new_data[CONF_DEVICES][self.selected_device]

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

        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        defaults = {
            CONF_HOST: dev_conf.get(CONF_HOST, ""),
            CONF_LOCAL_KEY: dev_conf.get(CONF_LOCAL_KEY, ""),
            CONF_PROTOCOL_VERSION: dev_conf.get(CONF_PROTOCOL_VERSION, "3.3"),
            CONF_FRIENDLY_NAME: dev_conf.get(CONF_FRIENDLY_NAME, ""),
            CONF_ENABLE_DEBUG: dev_conf.get(CONF_ENABLE_DEBUG, False),
        }

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

    async def async_step_delete_device(self, user_input=None):
        """Handle device deletion confirmation."""
        if user_input is not None:
            if user_input.get("confirm_delete"):
                new_data = self._get_config_entry().data.copy()
                del new_data[CONF_DEVICES][self.selected_device]
                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))

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

    async def async_step_configure_device(self, user_input=None):
        """Handle input of basic info."""
        errors = {}
        dev_id = self.selected_device

        if user_input is not None:
            try:
                self.device_data = user_input.copy()
                if dev_id is not None:
                    cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list
                    if dev_id in cloud_devs:
                        self.device_data[CONF_MODEL] = cloud_devs[dev_id].get(
                            CONF_PRODUCT_NAME
                        )

                if self.editing_device:
                    if user_input[CONF_ENABLE_ADD_ENTITIES]:
                        self.editing_device = False
                        user_input[CONF_DEVICE_ID] = dev_id
                        self.device_data.update({
                            CONF_DEVICE_ID: dev_id,
                            CONF_DPS_STRINGS: self.dps_strings,
                        })
                        return await self.async_step_pick_entity_type()

                    self.device_data.update({
                        CONF_DEVICE_ID: dev_id,
                        CONF_DPS_STRINGS: self.dps_strings,
                        CONF_ENTITIES: [],
                    })

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
                return await self.async_step_check_library_template()

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
                cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list

                if dev_id in self.discovered_devices:
                    device = self.discovered_devices[dev_id]
                    defaults[CONF_HOST] = device.get("ip", "")
                    defaults[CONF_DEVICE_ID] = device.get("gwId", dev_id)
                    defaults[CONF_PROTOCOL_VERSION] = device.get("version", "3.3")
                else:
                    defaults[CONF_DEVICE_ID] = dev_id

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

    async def async_step_check_library_template(self, user_input=None):
        """Check if device has a template in library and offer to use it."""
        dev_id = self.selected_device

        product_key = None
        try:
            cloud_devs = self.hass.data[DOMAIN][DATA_CLOUD].device_list
            if dev_id in cloud_devs:
                dev_data = cloud_devs[dev_id]
                product_key = (
                    dev_data.get("product_id") or
                    dev_data.get("productKey") or
                    dev_data.get("product_key")
                )
        except Exception:
            pass

        template = None
        if product_key:
            template = device_library.get_device_config(product_key)

        if template and user_input is None:
            template_name = template.get("name", "Unknown")
            manufacturer = template.get("manufacturer", "Unknown")
            entity_count = len(template.get("entities", []))

            return self.async_show_form(
                step_id="check_library_template",
                data_schema=vol.Schema({
                    vol.Required(CONF_USE_TEMPLATE, default="use"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value="use",
                                    label=f"✅ Use: {template_name} ({entity_count} entities)"
                                ),
                                SelectOptionDict(
                                    value="skip",
                                    label="⏭️ Skip template, configure manually"
                                ),
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }),
                description_placeholders={
                    "device_name": template_name,
                    "manufacturer": manufacturer,
                    "entity_count": str(entity_count),
                },
            )

        if user_input is not None and user_input.get(CONF_USE_TEMPLATE) == "use" and product_key:
            template = device_library.get_device_config(product_key)
            if template:
                self.entities = []
                for entity_def in template.get("entities", []):
                    entity = {
                        CONF_ID: entity_def["id"],
                        CONF_FRIENDLY_NAME: entity_def["friendly_name"],
                        CONF_PLATFORM: entity_def["platform"],
                    }
                    for key, value in entity_def.items():
                        if key not in ["id", "friendly_name", "platform"]:
                            entity[key] = value
                    self.entities.append(entity)

                config = {
                    **self.device_data,
                    CONF_DEVICE_ID: dev_id,
                    CONF_DPS_STRINGS: self.dps_strings,
                    CONF_ENTITIES: self.entities,
                }

                new_data = self._get_config_entry().data.copy()
                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                new_data[CONF_DEVICES].update({dev_id: config})

                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )
                return self.async_create_entry(title="", data={})

        return await self.async_step_pick_entity_type()
