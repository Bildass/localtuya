"""Cloud operations mixin for LocalTuya 2.0 config flow."""
import logging
import time

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICES,
    CONF_NAME,
    CONF_USERNAME,
)

from .const import (
    ATTR_UPDATED_AT,
    CONF_LOCAL_KEY,
    CONF_NO_CLOUD,
    CONF_USER_CODE,
    CONF_QR_SCHEMA,
    TUYA_HA_CLIENT_ID,
    TUYA_QR_SCHEMAS,
    DATA_CLOUD,
    DOMAIN,
)
from .config_flow_helpers import (
    CLOUD_SETUP_SCHEMA,
    schema_defaults,
    attempt_cloud_connection,
)

_LOGGER = logging.getLogger(__name__)

# QR Code selector - available in HA 2024.2+
try:
    from homeassistant.helpers.selector import QrCodeSelector, QrCodeSelectorConfig
    QR_SELECTOR_AVAILABLE = True
except ImportError:
    QR_SELECTOR_AVAILABLE = False

# QR Code Authentication imports
try:
    from tuya_sharing import LoginControl, Manager
    QR_AUTH_AVAILABLE = True
except ImportError:
    QR_AUTH_AVAILABLE = False
    _LOGGER.debug("tuya-device-sharing-sdk not installed, QR auth unavailable")


class CloudOperationsMixin:
    """Mixin for cloud operations in OptionsFlowHandler."""

    async def async_step_cloud_setup(self, user_input=None):
        """Handle cloud API configuration."""
        errors = {}
        placeholders = {}
        if user_input is not None:
            if user_input.get(CONF_NO_CLOUD):
                new_data = self._get_config_entry().data.copy()
                new_data.update(user_input)
                for i in [CONF_CLIENT_ID, CONF_CLIENT_SECRET, "user_id"]:
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
                    if "model" not in dev and dev_id in cloud_devs:
                        model = cloud_devs[dev_id].get("product_name")
                        new_data[CONF_DEVICES][dev_id]["model"] = model
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

    async def async_step_sync_from_cloud(self, user_input=None):
        """Handle syncing local keys from cloud with smart verification."""
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
                new_data = self._get_config_entry().data.copy()
                sync_result = await cloud_api.async_sync_local_keys(
                    new_data[CONF_DEVICES], verify_keys=True
                )

                updated_count = 0
                for dev_id, info in sync_result.items():
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

            if recommendation == "update":
                changes_list.append(f"🔄 **{info['name']}** - will UPDATE (current key broken, cloud key works)")
            elif recommendation == "manual":
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

        changes_text = "\n".join(changes_list[:15])
        if len(changes_list) > 15:
            changes_text += f"\n... and {len(changes_list) - 15} more"

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

    async def async_step_qr_auth(self, user_input=None):
        """Handle QR code authentication setup."""
        errors = {}

        if not QR_AUTH_AVAILABLE:
            return self.async_abort(
                reason="qr_auth_unavailable",
                description_placeholders={},
            )

        if user_input is not None:
            self._qr_user_code = user_input[CONF_USER_CODE]
            self._qr_schema = user_input[CONF_QR_SCHEMA]
            return await self.async_step_qr_scan()

        return self.async_show_form(
            step_id="qr_auth",
            data_schema=vol.Schema({
                vol.Required(CONF_USER_CODE): cv.string,
                vol.Required(CONF_QR_SCHEMA, default="smartlife"): vol.In(TUYA_QR_SCHEMAS),
            }),
            errors=errors,
            description_placeholders={},
        )

    async def async_step_qr_scan(self, user_input=None):
        """Handle QR code scanning and polling."""
        import asyncio

        errors = {}

        if user_input is not None:
            if hasattr(self, '_qr_login_data') and self._qr_login_data:
                try:
                    manager = Manager(
                        client_id=TUYA_HA_CLIENT_ID,
                        user_code=self._qr_user_code,
                        terminal_id=self._qr_login_data['terminal_id'],
                        end_point=self._qr_login_data['endpoint'],
                        token_response=self._qr_login_data
                    )

                    await self.hass.async_add_executor_job(manager.update_device_cache)

                    cloud_api = self.hass.data[DOMAIN][DATA_CLOUD]
                    devices_synced = 0

                    for device_id, device in manager.device_map.items():
                        # Tuya API may return local_key or localKey depending on endpoint
                        local_key = getattr(device, 'local_key', None) or getattr(device, 'localKey', '')
                        cloud_api.device_list[device_id] = {
                            CONF_NAME: device.name,
                            CONF_LOCAL_KEY: local_key,
                            "product_id": getattr(device, 'product_id', '') or getattr(device, 'productId', ''),
                            "category": getattr(device, 'category', ''),
                            "online": getattr(device, 'online', False),
                        }
                        devices_synced += 1

                    _LOGGER.info("QR Auth: Synced %d devices from cloud", devices_synced)

                    new_data = self._get_config_entry().data.copy()
                    new_data[CONF_NO_CLOUD] = False
                    new_data[ATTR_UPDATED_AT] = str(int(time.time() * 1000))
                    self.hass.config_entries.async_update_entry(
                        self._get_config_entry(),
                        data=new_data,
                    )

                    return self.async_create_entry(title="", data={})

                except Exception as ex:
                    _LOGGER.error("QR Auth device fetch failed: %s", ex)
                    errors["base"] = "qr_device_fetch_failed"
            else:
                errors["base"] = "qr_not_scanned"

        # Generate QR code token
        try:
            login = LoginControl()
            result = await self.hass.async_add_executor_job(
                login.qr_code,
                TUYA_HA_CLIENT_ID,
                self._qr_schema,
                self._qr_user_code
            )

            if not result.get("success"):
                _LOGGER.error("QR token generation failed: %s", result)
                return self.async_abort(reason="qr_token_failed")

            token = result.get("result", {}).get("qrcode")
            if not token:
                return self.async_abort(reason="qr_token_failed")

            self._qr_token = token
            qr_url = f"tuyaSmart--qrLogin?token={token}"

            async def poll_login():
                for _ in range(60):
                    await asyncio.sleep(2)
                    try:
                        success, login_data = await self.hass.async_add_executor_job(
                            login.login_result,
                            token,
                            TUYA_HA_CLIENT_ID,
                            self._qr_user_code
                        )
                        if success:
                            self._qr_login_data = login_data
                            _LOGGER.info("QR Auth: Login successful!")
                            return True
                    except Exception as ex:
                        _LOGGER.debug("QR polling error: %s", ex)
                return False

            self._qr_poll_task = self.hass.async_create_task(poll_login())
            self._qr_login_data = None

        except Exception as ex:
            _LOGGER.error("QR Auth error: %s", ex)
            return self.async_abort(reason="qr_auth_error")

        # Build schema with QR code if available
        if QR_SELECTOR_AVAILABLE:
            schema = vol.Schema({
                vol.Optional("qr_code"): QrCodeSelector(
                    QrCodeSelectorConfig(
                        data=qr_url,
                        scale=6,
                    )
                ),
                vol.Required("scanned", default=False): bool,
            })
        else:
            schema = vol.Schema({
                vol.Required("scanned", default=False): bool,
            })

        return self.async_show_form(
            step_id="qr_scan",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "qr_url": qr_url,
                "user_code": self._qr_user_code,
            },
        )
