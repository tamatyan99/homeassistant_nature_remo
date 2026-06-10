"""Shared entity helpers for Nature Remo integration."""

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, OFF_COMMANDS, ON_COMMANDS


def get_device_info(device: dict) -> DeviceInfo:
    """Build Home Assistant device_info dict from Nature Remo device data."""
    info = DeviceInfo(
        identifiers={(DOMAIN, device["device_id"])},
        name=device["name"],
        manufacturer="Nature",
        model="Nature Remo",
        sw_version=device.get("firmware_version", ""),
    )
    mac = device.get("mac_address")
    if mac:
        info["connections"] = {("mac", mac)}
    return info


def build_ir_commands(remote_info: dict[str, Any]) -> tuple[dict[str, str], str | None, str | None]:
    """Build command map and power signal ids from IR remote appliance info."""
    commands = {s["name"].lower(): s["id"] for s in remote_info["signals"]}
    power_on_id = next((commands[c] for c in ON_COMMANDS if c in commands), None)
    power_off_id = next((commands[c] for c in OFF_COMMANDS if c in commands), None)
    return commands, power_on_id, power_off_id
