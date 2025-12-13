"""Entity operations mixin for LocalTuya 2.0 config flow."""
import logging
import time

import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant.const import (
    CONF_DEVICES,
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_ID,
    CONF_PLATFORM,
)

from .const import (
    ATTR_UPDATED_AT,
    CONF_ADD_NEW_ENTITY,
    CONF_DPS_STRINGS,
    CONF_ENABLE_ADD_ENTITIES,
    CONF_SELECTED_ENTITY,
    PLATFORMS,
)
from .config_flow_helpers import (
    PICK_ENTITY_SCHEMA,
    PLATFORM_TO_ADD,
    NO_ADDITIONAL_ENTITIES,
    platform_schema,
    schema_defaults,
    strip_dps_values,
)

_LOGGER = logging.getLogger(__name__)


class EntityOperationsMixin:
    """Mixin for entity operations in OptionsFlowHandler."""

    async def async_step_entity_list(self, user_input=None):
        """Handle entity list for selecting one to edit or delete."""
        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_ENTITY)
            if selected == CONF_ADD_NEW_ENTITY:
                # Add new entity - go to pick entity type
                self.editing_device = False
                dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
                self.device_data = dev_conf.copy()
                self.device_data["device_id"] = self.selected_device
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

        entity_id_to_edit = getattr(self, '_selected_entity_id', None)

        if user_input is not None and entity_id_to_edit is not None:
            new_data = self._get_config_entry().data.copy()
            dev_conf = new_data[CONF_DEVICES][self.selected_device]

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
        schema = schema_defaults(schema, self.dps_strings, **current_entity)

        return self.async_show_form(
            step_id="edit_single_entity",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "entity_name": current_entity.get(CONF_FRIENDLY_NAME, "Unknown"),
                "entity_id": str(entity_id_to_edit),
                "platform": current_entity.get(CONF_PLATFORM, "unknown"),
            },
        )

    async def async_step_delete_entity(self, user_input=None):
        """Handle entity deletion confirmation."""
        if user_input is not None:
            if user_input.get("confirm_delete"):
                new_data = self._get_config_entry().data.copy()
                dev_conf = new_data[CONF_DEVICES][self.selected_device]

                # Remove entity from config
                dev_conf[CONF_ENTITIES] = [
                    ent for ent in dev_conf[CONF_ENTITIES]
                    if int(ent[CONF_ID]) != int(self._selected_entity_id)
                ]

                # Remove from entity registry
                ent_reg = er.async_get(self.hass)
                unique_id = f"local_{self.selected_device}_{self._selected_entity_id}"
                entity_entry = ent_reg.async_get_entity_id(
                    domain=None, platform="localtuya_bildass", unique_id=unique_id
                )
                if entity_entry:
                    ent_reg.async_remove(entity_entry)

                new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                self.hass.config_entries.async_update_entry(
                    self._get_config_entry(),
                    data=new_data,
                )

            return self.async_create_entry(title="", data={})

        # Find entity info for confirmation
        dev_conf = self._get_config_entry().data[CONF_DEVICES][self.selected_device]
        entity_info = None
        for ent in dev_conf.get(CONF_ENTITIES, []):
            if ent[CONF_ID] == self._selected_entity_id:
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
                "entity_id": str(self._selected_entity_id),
                "platform": entity_info.get(CONF_PLATFORM, "unknown"),
            },
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

                dev_id = self.device_data.get("device_id")

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

        schema = PICK_ENTITY_SCHEMA
        if self.selected_platform is not None:
            schema = schema.extend(
                {vol.Required(NO_ADDITIONAL_ENTITIES, default=True): bool}
            )

        return self.async_show_form(step_id="pick_entity_type", data_schema=schema)

    async def async_step_entity(self, user_input=None):
        """Manage entity settings (legacy)."""
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
                    dev_id = self.device_data["device_id"]
                    new_data = self._get_config_entry().data.copy()
                    entry_id = self._get_config_entry().entry_id

                    # Remove entities from registry (they will be recreated)
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

    def available_dps_strings(self):
        """Return list of DPs not used by the device's entities."""
        available_dps = []
        used_dps = [str(entity[CONF_ID]) for entity in self.entities]
        for dp_string in self.dps_strings:
            dp = dp_string.split(" ")[0]
            if dp not in used_dps:
                available_dps.append(dp_string)
        return available_dps

    @property
    def current_entity(self):
        """Existing configuration for entity currently being edited."""
        return self.entities[len(self.device_data[CONF_ENTITIES])]
