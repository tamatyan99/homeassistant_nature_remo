"""Shared entity helpers for Nature Remo integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NatureRemoCoordinator


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


class NatureRemoBaseEntity(CoordinatorEntity[NatureRemoCoordinator]):
    """Base entity for Nature Remo."""

    _attr_should_poll = False

    def __init__(self, coordinator: NatureRemoCoordinator, appliance_id: str) -> None:
        super().__init__(coordinator)
        self.appliance_id = appliance_id
        self._attr_unique_id = f"nature_remo_{appliance_id}"
