"""Tests for the Nature Remo diagnostics platform."""


from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import CONF_LOCAL_IP, DOMAIN
from custom_components.nature_remo.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_returns_masked_data(
    hass, setup_integration, coordinator_data, mock_api
):
    """Test diagnostics returns masked config and coordinator data."""
    entry = await setup_integration(
        devices=coordinator_data["devices"],
        appliances=coordinator_data["appliances"],
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert "config_entry" in diagnostics
    assert diagnostics["config_entry"]["api_key"] == "***"
    assert "options" in diagnostics
    assert "devices" in diagnostics
    assert "appliances" in diagnostics
    assert "motion_sensors" in diagnostics
    assert "entity_map" in diagnostics

    # Check PII masking in devices
    for device in diagnostics["devices"].values():
        assert device["name"] == "***"
        assert device["device_id"] == "***"
        assert device["serial_number"] == "***"
        assert device["mac_address"] == "***"

    # Check appliances are masked
    aircons = diagnostics["appliances"]["aircons"]
    assert "ac-1" in aircons
    assert aircons["ac-1"]["appliance_id"] == "***"
    assert aircons["ac-1"]["name"] == "***"

    # Check nested device fields inside appliances are also masked
    assert aircons["ac-1"]["device"]["name"] == "***"
    assert aircons["ac-1"]["device"]["device_id"] == "***"
    assert aircons["ac-1"]["device"]["serial_number"] == "***"
    assert aircons["ac-1"]["device"]["mac_address"] == "***"


async def test_diagnostics_no_coordinator(hass):
    """Test diagnostics handles missing coordinator gracefully."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="diag-entry",
    )
    entry.add_to_hass(hass)

    # Set up empty domain data so coordinator is missing
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["config_entry"]["api_key"] == "***"
    assert "devices" not in diagnostics


async def test_diagnostics_redacts_local_ip(hass):
    """Test that local_ip is redacted in diagnostics options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="diag-local-ip",
        options={CONF_LOCAL_IP: "192.168.1.50"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"][CONF_LOCAL_IP] == "***"


async def test_diagnostics_safe_when_domain_data_missing(hass):
    """Test diagnostics works when hass.data[DOMAIN] is absent."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="diag-missing-domain",
    )
    entry.add_to_hass(hass)

    hass.data.pop(DOMAIN, None)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert "config_entry" in diagnostics
    assert diagnostics["config_entry"]["api_key"] == "***"
    assert "devices" not in diagnostics
