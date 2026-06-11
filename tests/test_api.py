"""Tests for NatureRemoAPI."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.nature_remo.api import NatureRemoAPI


def _mock_response(status: int = 200, json_data: dict | list | None = None):
    response = MagicMock()
    response.status = status
    response.headers = {}
    response.json = AsyncMock(return_value=json_data if json_data is not None else {})
    response.text = AsyncMock(return_value="")
    return response


def _mock_session_method(response):
    """Return a MagicMock session whose context manager yields response."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = MagicMock(return_value=_mock_context_manager(response))
    session.post = MagicMock(return_value=_mock_context_manager(response))
    return session


def _mock_context_manager(mock_resp):
    class _Ctx:
        async def __aenter__(self):
            return mock_resp

        async def __aexit__(self, *args):
            return False

    return _Ctx()


@pytest.fixture
async def api():
    return NatureRemoAPI("test-token")


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("asyncio.sleep"):
        yield


async def test_get_devices_success(api):
    mock_resp = _mock_response(
        status=200, json_data=[{"id": "dev-1", "name": "Living Room"}]
    )
    session = _mock_session_method(mock_resp)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await api.get_devices()
    assert result == [{"id": "dev-1", "name": "Living Room"}]


async def test_get_appliances_success(api):
    mock_resp = _mock_response(status=200, json_data=[{"id": "app-1", "type": "AC"}])
    session = _mock_session_method(mock_resp)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await api.get_appliances()
    assert result == [{"id": "app-1", "type": "AC"}]


async def test_send_command_climate_success(api):
    mock_resp = _mock_response(status=200, json_data={"mode": "cool", "temp": "25"})
    session = _mock_session_method(mock_resp)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await api.send_command_climate({"operation_mode": "cool"}, "app-1")
    assert result == {"mode": "cool", "temp": "25"}


async def test_send_light_command_success(api):
    mock_resp = _mock_response(status=200, json_data={"status": "ok"})
    session = _mock_session_method(mock_resp)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await api.send_light_command("app-1", "on")
    assert result == {"status": "ok"}


async def test_send_command_signal_success(api):
    mock_resp = _mock_response(status=200, json_data={"status": "ok"})
    session = _mock_session_method(mock_resp)
    with patch("aiohttp.ClientSession", return_value=session):
        result = await api.send_command_signal("sig-1")
    assert result is None


def test_parse_smart_meter_properties_basic():
    api = NatureRemoAPI("test-token")
    properties = [
        {"epc": 211, "val": "1"},    # coefficient
        {"epc": 224, "val": "100"},  # buy power
        {"epc": 225, "val": "0x0A"}, # unit (10)
        {"epc": 227, "val": "50"},   # sold power
        {"epc": 231, "val": "500"},  # instant power
    ]
    result = api.parse_smart_meter_properties(properties)
    assert result["buy_power"] == 1000.0
    assert result["sold_power"] == 500.0
    assert result["instant_power"] == 500
