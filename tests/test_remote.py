"""Tests for the remote platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.nature_remo.remote import NatureRemoRemoteEntity


def _make_remote_entity(signals: list[dict]) -> NatureRemoRemoteEntity:
    coordinator = MagicMock()
    coordinator.ir_remotes = {}
    api = AsyncMock()
    remote_info = {
        "appliance_id": "remote-1",
        "device": {
            "device_id": "dev-1",
            "name": "Living Room",
            "firmware_version": "1.0",
            "serial_number": "SN001",
            "mac_address": "AA:BB:CC:DD:EE:FF",
        },
        "signals": signals,
    }
    return NatureRemoRemoteEntity(
        coordinator=coordinator, api=api, remote_info=remote_info
    )


class TestNatureRemoRemoteEntity:
    async def test_send_command_case_insensitive(self):
        entity = _make_remote_entity(
            [{"name": "Power On", "id": "sig-on"}, {"name": "Power Off", "id": "sig-off"}]
        )

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_send_command(["Power On"])

        entity._api.send_command_signal.assert_awaited_once_with("sig-on")

    async def test_send_command_lowercase_lookup(self):
        entity = _make_remote_entity([{"name": "volume up", "id": "sig-vol"}])

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_send_command(["Volume Up"])

        entity._api.send_command_signal.assert_awaited_once_with("sig-vol")

    async def test_send_command_reports_failed_commands(self):
        entity = _make_remote_entity([{"name": "on", "id": "sig-on"}])
        entity._api.send_command_signal = AsyncMock(side_effect=TimeoutError("timeout"))

        with pytest.raises(ServiceValidationError, match="Failed to send commands: on"):
            await entity.async_send_command(["on"])

    async def test_turn_on_uses_power_on_signal(self):
        entity = _make_remote_entity(
            [{"name": "on", "id": "sig-on"}, {"name": "off", "id": "sig-off"}]
        )

        with patch.object(entity, "async_write_ha_state"):
            await entity.async_turn_on()

        entity._api.send_command_signal.assert_awaited_once_with("sig-on")
        assert entity._attr_state == "on"

    async def test_turn_on_raises_when_no_power_signal(self):
        entity = _make_remote_entity([{"name": "volume", "id": "sig-vol"}])

        with pytest.raises(HomeAssistantError, match="Power ON command not available"):
            await entity.async_turn_on()
