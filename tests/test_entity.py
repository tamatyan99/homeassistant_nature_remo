"""Tests for shared entity helpers."""

from custom_components.nature_remo.const import DOMAIN
from custom_components.nature_remo.entity import get_device_info


def test_get_device_info_includes_serial_and_mac():
    device = {
        "device_id": "dev-1",
        "name": "Living Room",
        "firmware_version": "2.0.0",
        "serial_number": "SN123",
        "mac_address": "AA:BB:CC:DD:EE:FF",
    }
    info = get_device_info(device)

    assert info["identifiers"] == {(DOMAIN, "dev-1")}
    assert info["name"] == "Living Room"
    assert info["serial_number"] == "SN123"
    assert ("mac", "AA:BB:CC:DD:EE:FF") in info["connections"]
