"""Shared entity helpers for Nature Remo integration."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def get_device_info(device: dict) -> DeviceInfo:
    """Build Home Assistant device_info dict from Nature Remo device data."""
    info = {
        "identifiers": {(DOMAIN, device["device_id"])},
        "name": device["name"],
        "manufacturer": "Nature",
        "model": device.get("firmware_version") or "Nature Remo",
        "sw_version": device.get("firmware_version", ""),
    }
    mac = device.get("mac_address")
    if mac:
        info["connections"] = {("mac", mac)}
    return info
