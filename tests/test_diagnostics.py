"""Tests for diagnostics."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import DOMAIN
from custom_components.nature_remo.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_masks_api_key(hass):
    """Test that diagnostics masks sensitive config and device data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "secret-api-key"},
        entry_id="diag-entry",
        unique_id="unique-1",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.devices = {
        "dev-1": {
            "name": "Living Room",
            "device_id": "dev-1",
            "serial_number": "SN123",
            "mac_address": "AA:BB:CC:DD:EE:FF",
        }
    }
    coordinator.aircons = {}
    coordinator.lights = {}
    coordinator.smart_meters = {}
    coordinator.ir_remotes = {}
    coordinator.motion_sensors = {}
    coordinator.entity_map = {"climate.test": MagicMock()}

    hass.data[DOMAIN] = {
        entry.entry_id: {"coordinator": coordinator},
    }

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config_entry"]["api_key"] == "***"
    assert result["devices"]["dev-1"]["name"] == "***"
    assert result["devices"]["dev-1"]["serial_number"] == "***"
    assert result["devices"]["dev-1"]["mac_address"] == "***"
    assert "climate.test" in result["entity_map"]


async def test_diagnostics_without_coordinator(hass):
    """Test diagnostics when integration is not loaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "secret-api-key"},
        entry_id="diag-entry-2",
        unique_id="unique-2",
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config_entry"]["api_key"] == "***"
    assert "devices" not in result
