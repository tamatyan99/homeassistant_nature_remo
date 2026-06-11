"""Shared fixtures for Nature Remo tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nature_remo.api import NatureRemoAPI
from custom_components.nature_remo.const import DOMAIN


def _options_flow_init(self, config_entry):
    """Stub OptionsFlow.__init__ for test environments without config_entry support."""
    self.config_entry = config_entry


@pytest.fixture(scope="session", autouse=True)
def _patch_options_flow_init():
    """Patch OptionsFlow.__init__ so integrations can call super().__init__(entry)."""
    from homeassistant import config_entries

    original = config_entries.OptionsFlow.__dict__.get("__init__")
    config_entries.OptionsFlow.__init__ = _options_flow_init
    yield
    if original is None:
        del config_entries.OptionsFlow.__init__
    else:
        config_entries.OptionsFlow.__init__ = original


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def mock_async_resolver():
    """Prevent aiodns/pycares from starting a background thread."""
    with patch(
        "homeassistant.helpers.aiohttp_client.AsyncResolver", return_value=Mock()
    ):
        yield


@pytest.fixture
def mock_api():
    """Return a mocked NatureRemoAPI with explicit AsyncMock specs."""
    api = MagicMock(spec=NatureRemoAPI)
    api.get_devices = AsyncMock(return_value=[])
    api.get_appliances = AsyncMock(return_value=[])
    api.send_command_climate = AsyncMock(return_value={})
    api.send_light_command = AsyncMock(return_value={})
    api.send_command_signal = AsyncMock(return_value={})
    api.learn_signal = AsyncMock(return_value={"id": "signal-1"})
    api.send_local_ir_message = AsyncMock(return_value={})
    api.parse_smart_meter_properties = MagicMock(
        return_value={"buy_power": 0, "sold_power": 0, "instant_power": 0}
    )
    return api


@pytest.fixture
def coordinator_data():
    """Return a sample coordinator data dict."""
    now = datetime.now(UTC)
    created_at = now - timedelta(minutes=2)
    created_at_str = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "devices": [
            {
                "id": "dev-1",
                "name": "Living Room",
                "newest_events": {
                    "te": {"val": 22.5},
                    "hu": {"val": 55.0},
                    "il": {"val": 100.0},
                    "pr": {"val": 1013.0},
                },
                "firmware_version": "1.0",
                "serial_number": "SN001",
                "mac_address": "AA:BB:CC:DD:EE:FF",
            },
            {
                "id": "dev-2",
                "name": "Bedroom Sensor",
                "newest_events": {"mo": {"created_at": created_at_str}},
                "firmware_version": "1.0",
                "serial_number": "SN002",
                "mac_address": "AA:BB:CC:DD:EE:00",
            },
        ],
        "appliances": [
            {
                "id": "ac-1",
                "type": "AC",
                "nickname": "Living AC",
                "device": {
                    "id": "dev-1",
                    "name": "Living Room",
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                },
                "settings": {
                    "mode": "cool",
                    "temp": "25.0",
                    "vol": "auto",
                    "dir": "auto",
                    "dirh": "auto",
                    "button": "",
                },
                "aircon": {
                    "range": {
                        "modes": {
                            "cool": {
                                "temp": ["18", "25", "30"],
                                "vol": ["1", "2", "3", "auto"],
                                "dir": ["auto"],
                                "dirh": ["auto", "left"],
                            },
                            "warm": {
                                "temp": ["18", "25", "30"],
                                "vol": ["1", "2", "3", "auto"],
                                "dir": ["auto"],
                                "dirh": ["auto", "left"],
                            },
                            "dry": {
                                "temp": ["18", "25", "30"],
                                "vol": ["1", "2", "3", "auto"],
                                "dir": ["auto"],
                                "dirh": ["auto", "left"],
                            },
                            "blow": {
                                "temp": ["-"],
                                "vol": ["1", "2", "3", "auto"],
                                "dir": ["auto"],
                                "dirh": ["auto", "left"],
                            },
                            "auto": {
                                "temp": ["18", "25", "30"],
                                "vol": ["1", "2", "3", "auto"],
                                "dir": ["auto"],
                                "dirh": ["auto", "left"],
                            },
                        }
                    }
                },
            },
            {
                "id": "light-1",
                "type": "LIGHT",
                "nickname": "Ceiling Light",
                "device": {
                    "id": "dev-1",
                    "name": "Living Room",
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                },
                "light": {
                    "state": {"power": "on", "last_button": "on"},
                    "buttons": [
                        {"name": "on"},
                        {"name": "off"},
                        {"name": "night"},
                    ],
                },
            },
            {
                "id": "sm-1",
                "type": "EL_SMART_METER",
                "nickname": "Smart Meter",
                "device": {
                    "id": "dev-1",
                    "name": "Living Room",
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                },
                "smart_meter": {"echonetlite_properties": []},
            },
            {
                "id": "remote-1",
                "type": "IR",
                "nickname": "TV Remote",
                "device": {
                    "id": "dev-1",
                    "name": "Living Room",
                    "firmware_version": "1.0",
                    "serial_number": "SN001",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                },
                "signals": [
                    {"id": "sig-on", "name": "on"},
                    {"id": "sig-off", "name": "off"},
                    {"id": "sig-vol-up", "name": "volume up"},
                ],
            },
        ],
    }


@pytest.fixture
def setup_integration(hass, mock_api):
    """Set up the integration with mocked API and real coordinator logic."""

    async def _setup(devices=None, appliances=None, options=None):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"api_key": "test_key"},
            entry_id="test-entry",
            options=options or {},
        )
        entry.add_to_hass(hass)

        devices = devices if devices is not None else []
        appliances = appliances if appliances is not None else []

        mock_api.get_devices = AsyncMock(return_value=devices)
        mock_api.get_appliances = AsyncMock(return_value=appliances)

        with patch(
            "custom_components.nature_remo.NatureRemoAPI",
            return_value=mock_api,
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        return entry

    return _setup
