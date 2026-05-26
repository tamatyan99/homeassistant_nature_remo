"""Shared entity helpers for Nature Remo integration."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def get_device_info(device: dict) -> DeviceInfo:
    """Build Home Assistant device_info dict from Nature Remo device data."""
    device_id = (
        device.get("device_id")
        or device.get("serial_number")
        or device.get("mac_address")
        or device.get("name", "unknown")
    )

    info = DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=device["name"],
        manufacturer="Nature",
        model=device.get("model", "Nature Remo"),
        sw_version=device.get("firmware_version", ""),
    )
    serial = device.get("serial_number")
    if serial:
        info["serial_number"] = serial
    mac = device.get("mac_address")
    if mac:
        info["connections"] = {("mac", mac)}
    return info
