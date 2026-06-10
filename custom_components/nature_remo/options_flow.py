import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class NatureRemoOptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None) -> FlowResult:
        device_registry = async_get_device_registry(self.hass)
        devices = [
            dev
            for dev in device_registry.devices.values()
            if dev.config_entries and self.config_entry.entry_id in dev.config_entries
        ]

        options = self.config_entry.options

        interval_default = options.get("update_interval", 60)
        motion_threshold_default = options.get("motion_threshold_minutes", 5)
        local_ip_default = options.get("local_ip", "")
        data_schema = {
            vol.Optional("update_interval", default=interval_default): vol.In(
                [30, 60, 90]
            ),
            vol.Optional("motion_threshold_minutes", default=motion_threshold_default): vol.In(
                [1, 3, 5, 10, 15]
            ),
            vol.Optional("local_ip", default=local_ip_default): vol.Any(
                "",
                vol.Match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
            ),
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

            ext_temp_key = f"external_temperature_{nature_remo_device_id}"
            data_schema[
                vol.Optional(
                    ext_temp_key,
                    default=options.get(ext_temp_key) or "",
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.TEMPERATURE,
                    multiple=False,
                )
            )

            ext_humidity_key = f"external_humidity_{nature_remo_device_id}"
            data_schema[
                vol.Optional(
                    ext_humidity_key,
                    default=options.get(ext_humidity_key) or "",
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class=SensorDeviceClass.HUMIDITY,
                    multiple=False,
                )
            )

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(data_schema),
        )
