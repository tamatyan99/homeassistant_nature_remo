"""Shared entity helpers for Nature Remo integration."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def get_device_info(device: dict) -> DeviceInfo:
    """Build Home Assistant device_info dict from Nature Remo device data."""
    model = device.get("model") or "Nature Remo"
    info = DeviceInfo(
        identifiers={(DOMAIN, device["device_id"])},
        name=device["name"],
        manufacturer="Nature",
        model=model,
        sw_version=device.get("firmware_version", ""),
    )
    serial = device.get("serial_number")
    if serial:
        info["serial_number"] = serial
    mac = device.get("mac_address")
    if mac:
        info["connections"] = {("mac", mac)}
    return info
