import logging

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class NatureRemoOptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):

        device_registry = async_get_device_registry(self.hass)
        devices = [
            dev
            for dev in device_registry.devices.values()
            if dev.config_entries and self.config_entry.entry_id in dev.config_entries
        ]

        options = self.config_entry.options
        lang = self.hass.config.language

        if lang == "ja":
            interval_label = "更新間隔（秒）"
            motion_threshold_label = "モーション検出閾値（分）"
            local_ip_label = "Nature Remo ローカルIPアドレス"
            ext_temp_label_suffix = "：外部温度センサー"
            ext_humidity_label_suffix = "：外部湿度センサー"
        else:
            interval_label = "Update Interval (seconds)"
            motion_threshold_label = "Motion Detection Threshold (minutes)"
            local_ip_label = "Nature Remo Local IP Address"
            ext_temp_label_suffix = ": External Temperature Sensor"
            ext_humidity_label_suffix = ": External Humidity Sensor"

        special_key_map = {interval_label: "update_interval", motion_threshold_label: "motion_threshold_minutes"}
        label_key_map = {}

        interval_default = options.get("update_interval", 60)
        motion_threshold_default = options.get("motion_threshold_minutes", 5)
        local_ip_default = options.get("local_ip", "")
        data_schema = {
            vol.Optional(interval_label, default=interval_default): vol.In(
                [30, 60, 90]
            ),
            vol.Optional(motion_threshold_label, default=motion_threshold_default): vol.In(
                [1, 3, 5, 10, 15]
            ),
            vol.Optional(local_ip_label, default=local_ip_default): str,
        }

        for device in devices:
            name = device.name_by_user or device.name or "Unknown Device"

            nature_remo_device_id = next(
                (
                    identifier_id
                    for domain, identifier_id in device.identifiers
                    if domain == DOMAIN
                ),
                None,
            )

            if nature_remo_device_id is None:
                _LOGGER.warning(
                    "デバイス '%s' のNature Remo device IDが見つかりません。スキップします。"
                    " / Nature Remo device ID not found for device '%s'. Skipping.",
                    name,
                    name,
                )
                continue

            _LOGGER.debug(
                "デバイス '%s' のNature Remo device ID: %s"
                " / Nature Remo device ID for '%s': %s",
                name,
                nature_remo_device_id,
                name,
                nature_remo_device_id,
            )

            ext_temp_label = f"{name} {ext_temp_label_suffix}"
            ext_temp_key = f"external_temperature_{nature_remo_device_id}"
            label_key_map[ext_temp_label] = ext_temp_key
            data_schema[
                vol.Optional(
                    ext_temp_label,
                    description={"suggested_value": options.get(ext_temp_key)},
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    multiple=False,
                )
            )

            ext_humidity_label = f"{name} {ext_humidity_label_suffix}"
            ext_humidity_key = f"external_humidity_{nature_remo_device_id}"
            label_key_map[ext_humidity_label] = ext_humidity_key
            data_schema[
                vol.Optional(
                    ext_humidity_label,
                    description={"suggested_value": options.get(ext_humidity_key)},
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.HUMIDITY,
                    multiple=False,
                )
            )

        if user_input is not None:
            result = {}

            for label, value in user_input.items():
                if label in special_key_map:
                    result[special_key_map[label]] = value
                elif label in label_key_map:
                    result[label_key_map[label]] = value

            return self.async_create_entry(title="", data=result)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
        )