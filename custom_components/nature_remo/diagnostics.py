"""Diagnostics support for Nature Remo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_LOCAL_IP, DOMAIN

_SENSITIVE_KEYS = {
    "serial_number",
    "mac_address",
    "name",
    "nickname",
    "id",
    "device_id",
    "appliance_id",
}


def _mask_device_data(data: dict) -> dict:
    """Return a copy of device/appliance data with PII masked recursively."""
    masked: dict[str, Any] = {}
    for key, value in data.items():
        if key in _SENSITIVE_KEYS:
            masked[key] = "***"
        elif isinstance(value, dict):
            masked[key] = _mask_device_data(value)
        elif isinstance(value, list):
            masked[key] = [
                _mask_device_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    return masked


def _mask_devices(devices: dict) -> dict:
    return {k: _mask_device_data(v) for k, v in devices.items()}


def _mask_appliances(appliances: dict) -> dict:
    return {app_id: _mask_device_data(app) for app_id, app in appliances.items()}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    config_entry_data = dict(config_entry.data)
    if "api_key" in config_entry_data:
        config_entry_data["api_key"] = "***"

    options = dict(config_entry.options)
    if CONF_LOCAL_IP in options:
        options[CONF_LOCAL_IP] = "***"

    diagnostics: dict[str, Any] = {
        "config_entry": config_entry_data,
        "options": options,
    }

    if coordinator is not None:
        diagnostics["devices"] = _mask_devices(coordinator.devices)
        diagnostics["appliances"] = {
            "aircons": _mask_appliances(coordinator.aircons),
            "lights": _mask_appliances(coordinator.lights),
            "smart_meters": _mask_appliances(coordinator.smart_meters),
            "ir_remotes": _mask_appliances(coordinator.ir_remotes),
        }
        diagnostics["motion_sensors"] = _mask_devices(coordinator.motion_sensors)
        diagnostics["entity_map"] = list(coordinator.entity_map.keys())

    return diagnostics
