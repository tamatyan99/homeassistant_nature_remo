"""Diagnostics support for Nature Remo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


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
    }

    if coordinator is not None:
        diagnostics["devices"] = coordinator.devices
        diagnostics["appliances"] = {
            "aircons": coordinator.aircons,
            "lights": coordinator.lights,
            "smart_meters": coordinator.smart_meters,
            "ir_remotes": coordinator.ir_remotes,
        }
        diagnostics["motion_sensors"] = coordinator.motion_sensors
        diagnostics["entity_map"] = list(coordinator.entity_map.keys())

    return diagnostics
