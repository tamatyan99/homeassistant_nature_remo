"""Tests for Nature Remo remote platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.const import DOMAIN
from custom_components.nature_remo.remote import NatureRemoRemoteEntity


@pytest.fixture
def remote_entity(hass):
    coordinator = MagicMock()
    coordinator.ir_remotes = {
        "app-1": {
            "appliance_id": "app-1",
            "name": "Living Room TV",
            "device": {
                "device_id": "dev-1",
                "name": "Remo",
                "firmware_version": "1.0",
                "serial_number": "SN001",
                "mac_address": "AA:BB:CC:DD:EE:FF",
            },
            "signals": [
                {"name": "Power On", "id": "sig-on"},
                {"name": "Volume Up", "id": "sig-vol"},
            ],
        }
    }
    api = AsyncMock()
    entity = NatureRemoRemoteEntity(
        coordinator=coordinator,
        api=api,
        remote_info=coordinator.ir_remotes["app-1"],
    )
    entity.hass = hass
    entity.entity_id = "remote.living_room_tv"
    return entity, api


async def test_send_command_case_insensitive(remote_entity):
    """Test that signal lookup is case-insensitive."""
    entity, api = remote_entity
    await entity.async_send_command(["Power On"])
    api.send_command_signal.assert_awaited_once_with("sig-on")


async def test_send_command_unknown_raises(remote_entity):
    """Test that unknown commands raise ServiceValidationError."""
    entity, api = remote_entity
    with pytest.raises(ServiceValidationError) as exc_info:
        await entity.async_send_command(["Unknown Command"])
    assert exc_info.value.translation_key == "send_command_failed"
    api.send_command_signal.assert_not_called()


async def test_turn_on_sets_is_on(remote_entity):
    """Test that async_turn_on updates is_on state."""
    entity, api = remote_entity
    await entity.async_turn_on()
    assert entity.is_on is True
    api.send_command_signal.assert_awaited_once_with("sig-on")
