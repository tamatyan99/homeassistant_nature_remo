"""Tests for __init__.py and platform imports."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import ConfigEntryAuthFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import DOMAIN


def test_switch_imports():
    """Test switch platform imports do not fail."""
    from custom_components.nature_remo.switch import ON_COMMANDS, OFF_COMMANDS

    assert "on" in ON_COMMANDS
    assert "off" in OFF_COMMANDS


def test_remote_imports():
    """Test remote platform imports do not fail."""
    from custom_components.nature_remo.remote import ON_COMMANDS, OFF_COMMANDS

    assert "on" in ON_COMMANDS
    assert "off" in OFF_COMMANDS


async def test_setup_entry_starts_reauth_on_auth_failure(hass):
    """Test that async_setup_entry triggers reauth when first refresh fails with auth error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "bad_key"},
        entry_id="test-entry-1",
    )
    entry.add_to_hass(hass)

    entry.async_start_reauth = MagicMock()

    with patch(
        "custom_components.nature_remo.coordinator.NatureRemoCoordinator._async_update_data",
        side_effect=ConfigEntryAuthFailed("401"),
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is False
    entry.async_start_reauth.assert_called_once_with(hass)


async def test_unload_entry_shuts_down_coordinator(hass):
    """Test that async_unload_entry calls coordinator.async_shutdown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="test-entry-2",
    )
    entry.add_to_hass(hass)

    api_mock = AsyncMock()
    api_mock.get_devices = AsyncMock(return_value=[])
    api_mock.get_appliances = AsyncMock(return_value=[])

    with patch(
        "custom_components.nature_remo.coordinator.NatureRemoCoordinator._async_update_data",
        return_value={},
    ), patch(
        "custom_components.nature_remo.NatureRemoAPI",
        return_value=api_mock,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Replace the coordinator with our mock after setup
        coordinator_mock = MagicMock()
        coordinator_mock.async_shutdown = AsyncMock()
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator_mock

        result = await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    coordinator_mock.async_shutdown.assert_awaited_once()


async def test_unload_entry_keeps_coordinator_running_when_platform_unload_fails(
    hass, monkeypatch
):
    """Test that a failed platform unload does not leave a stopped coordinator."""
    from custom_components.nature_remo import PLATFORMS, async_unload_entry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="test-entry-unload-fails",
    )
    entry.add_to_hass(hass)

    coordinator_mock = MagicMock()
    coordinator_mock.async_shutdown = AsyncMock()
    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": coordinator_mock,
            "api": AsyncMock(),
        }
    }

    async_unload_platforms = AsyncMock(return_value=False)
    monkeypatch.setattr(
        hass.config_entries,
        "async_unload_platforms",
        async_unload_platforms,
    )

    result = await async_unload_entry(hass, entry)

    assert result is False
    async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)
    coordinator_mock.async_shutdown.assert_not_awaited()
    assert hass.data[DOMAIN][entry.entry_id]["coordinator"] is coordinator_mock


async def test_send_light_mode_service(hass):
    """Test send_light_mode service with entity_id in data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="test-entry-3",
    )
    entry.add_to_hass(hass)

    light_entity = MagicMock()
    light_entity.supported_effects = ["on", "night"]
    light_entity.appliance_id = "light-1"
    light_entity.set_mode = MagicMock()

    coordinator_mock = MagicMock()
    coordinator_mock.entity_map = {"light.test_light": light_entity}

    api_mock = AsyncMock()
    api_mock.get_devices = AsyncMock(return_value=[])
    api_mock.get_appliances = AsyncMock(return_value=[])
    api_mock.send_light_command = AsyncMock()

    with patch(
        "custom_components.nature_remo.NatureRemoAPI",
        return_value=api_mock,
    ), patch(
        "custom_components.nature_remo.coordinator.NatureRemoCoordinator._async_update_data",
        return_value={},
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Replace coordinator entity_map with our mock
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator_mock
        hass.data[DOMAIN][entry.entry_id]["api"] = api_mock

        await hass.services.async_call(
            DOMAIN,
            "send_light_mode",
            {"entity_id": "light.test_light", "mode": "night"},
            blocking=True,
        )

    api_mock.send_light_command.assert_awaited_once_with("light-1", "night")
    light_entity.set_mode.assert_called_once_with("night")


async def test_send_light_mode_missing_entity_id(hass):
    """Test send_light_mode service raises error when entity_id is missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="test-entry-4",
    )
    entry.add_to_hass(hass)

    api_mock = AsyncMock()
    api_mock.get_devices = AsyncMock(return_value=[])
    api_mock.get_appliances = AsyncMock(return_value=[])

    with patch(
        "custom_components.nature_remo.NatureRemoAPI",
        return_value=api_mock,
    ), patch(
        "custom_components.nature_remo.coordinator.NatureRemoCoordinator._async_update_data",
        return_value={},
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError, match="entity_id is required"):
        await hass.services.async_call(
            DOMAIN,
            "send_light_mode",
            {"mode": "on"},
            blocking=True,
        )


async def test_learn_signal_service(hass):
    """Test learn_signal service."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"api_key": "test_key"},
        entry_id="test-entry-5",
    )
    entry.add_to_hass(hass)

    api_mock = AsyncMock()
    api_mock.get_devices = AsyncMock(return_value=[])
    api_mock.get_appliances = AsyncMock(return_value=[])
    api_mock.learn_signal = AsyncMock(return_value={"id": "signal-1"})

    coordinator_mock = MagicMock()
    coordinator_mock.aircons = {}
    coordinator_mock.lights = {}
    coordinator_mock.ir_remotes = {"app-1": {}}

    with patch(
        "custom_components.nature_remo.NatureRemoAPI",
        return_value=api_mock,
    ), patch(
        "custom_components.nature_remo.coordinator.NatureRemoCoordinator._async_update_data",
        return_value={},
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Replace coordinator and api with mocks
        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator_mock
        hass.data[DOMAIN][entry.entry_id]["api"] = api_mock

        result = await hass.services.async_call(
            DOMAIN,
            "learn_signal",
            {"appliance_id": "app-1"},
            blocking=True,
            return_response=True,
        )

    api_mock.learn_signal.assert_awaited_once_with("app-1")
    assert result == {"id": "signal-1"}
