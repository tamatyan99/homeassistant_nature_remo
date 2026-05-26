"""Diagnostics support for Nature Remo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _mask_device_data(data: dict) -> dict:
    """Return a copy of device data with PII masked."""
    masked = dict(data)
    for key in ("serial_number", "mac_address"):
        if key in masked:
            masked[key] = "***"
    return masked


def _mask_devices(devices: dict) -> dict:
    return {k: _mask_device_data(v) for k, v in devices.items()}


def _mask_appliances(appliances: dict) -> dict:
    result = {}
    for app_id, app in appliances.items():
        masked = dict(app)
        if "device" in masked:
            masked["device"] = _mask_device_data(masked["device"])
        result[app_id] = masked
    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    config_entry_data = dict(config_entry.data)
    if "api_key" in config_entry_data:
        config_entry_data["api_key"] = "***"

    diagnostics: dict[str, Any] = {
        "config_entry": config_entry_data,
        "options": dict(config_entry.options),
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
