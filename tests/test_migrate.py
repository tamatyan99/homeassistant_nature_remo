"""Tests for config entry migration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo import async_migrate_entry
from custom_components.nature_remo.const import DOMAIN


async def test_migrate_entry_bumps_minor_version(hass):
    """Test migration from minor version 1 to 2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        version=1,
        minor_version=1,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == 2


async def test_migrate_entry_skips_when_already_current(hass):
    """Test migration is a no-op when already at latest minor version."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.minor_version == 2
