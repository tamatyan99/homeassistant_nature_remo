"""Tests for NatureRemoCoordinator."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.nature_remo.coordinator import NatureRemoCoordinator


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.parse_smart_meter_properties = MagicMock(
        return_value={"buy_power": 0, "sold_power": 0, "instant_power": 0}
    )
    return api


class TestNatureRemoCoordinator:
    async def test_async_update_data_parses_devices(self, hass, mock_api):
        mock_api.get_devices = AsyncMock(
            return_value=[
                {
                    "id": "dev-1",
                    "name": "Living Room",
                    "newest_events": {},
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                }
            ]
        )
        mock_api.get_appliances = AsyncMock(return_value=[])

        coordinator = NatureRemoCoordinator(hass, mock_api, update_interval=60)
        result = await coordinator._async_update_data()

        assert coordinator.devices == {
            "dev-1": {
                "name": "Living Room",
                "device_id": "dev-1",
                "events": {},
                "firmware_version": "1.0",
                "serial_number": "SN001",
                "mac_address": "AA:BB:CC:DD:EE:FF",
            }
        }
        assert result == {}

    async def test_async_update_data_raises_update_failed_on_bad_devices(
        self, hass, mock_api
    ):
        mock_api.get_devices = AsyncMock(return_value="bad")
        mock_api.get_appliances = AsyncMock(return_value=[])

        coordinator = NatureRemoCoordinator(hass, mock_api, update_interval=60)
        with pytest.raises(UpdateFailed, match="Unexpected devices response from API"):
            await coordinator._async_update_data()

    async def test_async_update_data_raises_update_failed_on_bad_appliances(
        self, hass, mock_api
    ):
        mock_api.get_devices = AsyncMock(return_value=[])
        mock_api.get_appliances = AsyncMock(return_value="bad")

        coordinator = NatureRemoCoordinator(hass, mock_api, update_interval=60)
        with pytest.raises(
            UpdateFailed, match="Unexpected appliances response from API"
        ):
            await coordinator._async_update_data()

    async def test_motion_sensor_active(self, hass, mock_api):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(minutes=2)
        created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_api.get_devices = AsyncMock(
            return_value=[
                {
                    "id": "dev-1",
                    "name": "Sensor",
                    "newest_events": {"mo": {"created_at": created_at_str}},
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                }
            ]
        )
        mock_api.get_appliances = AsyncMock(return_value=[])

        coordinator = NatureRemoCoordinator(hass, mock_api, update_interval=60)
        await coordinator._async_update_data()

        assert "dev-1" in coordinator.motion_sensors
        assert coordinator.motion_sensors["dev-1"]["is_active"] is True
        assert coordinator.motion_sensors["dev-1"]["name"] == "Sensor"

    async def test_motion_sensor_inactive(self, hass, mock_api):
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(minutes=10)
        created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        mock_api.get_devices = AsyncMock(
            return_value=[
                {
                    "id": "dev-1",
                    "name": "Sensor",
                    "newest_events": {"mo": {"created_at": created_at_str}},
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                }
            ]
        )
        mock_api.get_appliances = AsyncMock(return_value=[])

        coordinator = NatureRemoCoordinator(hass, mock_api, update_interval=60)
        await coordinator._async_update_data()

        assert "dev-1" in coordinator.motion_sensors
        assert coordinator.motion_sensors["dev-1"]["is_active"] is False
        assert coordinator.motion_sensors["dev-1"]["name"] == "Sensor"
