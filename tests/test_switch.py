"""Tests for the switch platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.nature_remo.switch import NatureRemoSwitchEntity


@pytest.fixture
def switch_entity(hass):
    coordinator = MagicMock()
    coordinator.ir_remotes = {}
    api = AsyncMock()
    remote_info = {
        "appliance_id": "app-1",
        "device": {
            "device_id": "dev-1",
            "name": "TV",
            "firmware_version": "1.0",
        },
        "signals": [
            {"name": "on", "id": "sig-on"},
            {"name": "off", "id": "sig-off"},
        ],
    }
    entity = NatureRemoSwitchEntity(coordinator, api, remote_info)
    entity.hass = hass
    entity.entity_id = "switch.tv"
    return entity, api


async def test_turn_on_sets_state(switch_entity):
    entity, api = switch_entity
    await entity.async_turn_on()
    api.send_command_signal.assert_awaited_once_with("sig-on")
    assert entity.is_on is True


async def test_turn_off_sets_state(switch_entity):
    entity, api = switch_entity
    entity._is_on = True
    await entity.async_turn_off()
    api.send_command_signal.assert_awaited_once_with("sig-off")
    assert entity.is_on is False


async def test_turn_on_without_signal_raises(hass):
    coordinator = MagicMock()
    api = AsyncMock()
    remote_info = {
        "appliance_id": "app-2",
        "device": {"device_id": "dev-2", "name": "Fan"},
        "signals": [{"name": "fan_speed", "id": "sig-fan"}],
    }
    entity = NatureRemoSwitchEntity(coordinator, api, remote_info)
    entity.hass = hass
    entity.entity_id = "switch.fan"
    entity._power_on_id = None

    with pytest.raises(HomeAssistantError, match="Power ON command not available"):
        await entity.async_turn_on()
