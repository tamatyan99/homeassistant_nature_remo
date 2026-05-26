"""Tests for the remote platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError
from homeassistant.exceptions import ServiceValidationError

from custom_components.nature_remo.remote import NatureRemoRemoteEntity


@pytest.fixture
def remote_entity(hass):
    coordinator = MagicMock()
    coordinator.ir_remotes = {}
    api = AsyncMock()
    remote_info = {
        "appliance_id": "app-1",
        "device": {
            "device_id": "dev-1",
            "name": "Living",
            "firmware_version": "1.0",
        },
        "signals": [
            {"name": "Power On", "id": "sig-power-on"},
            {"name": "on", "id": "sig-on"},
            {"name": "off", "id": "sig-off"},
        ],
    }
    entity = NatureRemoRemoteEntity(coordinator, api, remote_info)
    entity.hass = hass
    entity.entity_id = "remote.living_room"
    return entity, api


async def test_send_command_case_insensitive(remote_entity):
    entity, api = remote_entity
    await entity.async_send_command(["Power On"])
    api.send_command_signal.assert_awaited_once_with("sig-power-on")


async def test_send_command_unknown_raises(remote_entity):
    entity, _api = remote_entity
    with pytest.raises(ServiceValidationError, match="Unknown commands"):
        await entity.async_send_command(["missing"])


async def test_send_command_api_error_raises(remote_entity):
    entity, api = remote_entity
    api.send_command_signal = AsyncMock(side_effect=ClientError("network"))
    with pytest.raises(ServiceValidationError, match="Failed to send commands"):
        await entity.async_send_command(["off"])


async def test_turn_on_uses_power_on_signal(remote_entity):
    entity, api = remote_entity
    await entity.async_turn_on()
    api.send_command_signal.assert_awaited_once_with("sig-on")
    assert entity._attr_state == "on"
