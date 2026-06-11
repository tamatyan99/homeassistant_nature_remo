"""Tests for NatureRemoAPI."""


import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError

from custom_components.nature_remo.api import (
    NATURE_REMO_CLOUD_URL,
    NatureRemoAPI,
    NatureRemoAuthError,
)


@pytest.fixture(autouse=True)
def mock_api_sleep():
    """Patch asyncio.sleep in api.py to keep tests fast."""
    with patch("custom_components.nature_remo.api.asyncio.sleep"):
        yield


def _mock_response(status=200, json_data=None, text=None):
    response = MagicMock()
    response.status = status
    response.ok = 200 <= status < 300
    response.headers = {}
    response.json = AsyncMock(return_value=json_data)
    if text is None and json_data is not None:
        text = json.dumps(json_data)
    response.text = AsyncMock(return_value=text or "")
    return response


def _mock_context_manager(mock_resp):
    class _Ctx:
        async def __aenter__(self):
            return mock_resp
        async def __aexit__(self, *args):
            return False
    return _Ctx()


def _mock_session_method(mock_resp):
    """Return a MagicMock session.request that yields the given response context."""
    mock = MagicMock()
    mock.return_value = _mock_context_manager(mock_resp)
    return mock


@pytest.fixture
async def api():
    mock_hass = MagicMock()
    mock_hass.data = {}
    mock_session = MagicMock()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "custom_components.nature_remo.api.async_get_clientsession",
            lambda hass: mock_session,
        )
        yield NatureRemoAPI(mock_hass, "test-token")


@pytest.fixture
async def api_with_local_ip():
    mock_hass = MagicMock()
    mock_hass.data = {}
    mock_session = MagicMock()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(
            "custom_components.nature_remo.api.async_get_clientsession",
            lambda hass: mock_session,
        )
        yield NatureRemoAPI(mock_hass, "test-token", local_ip="192.168.1.100")


class TestNatureRemoAPI:
    async def test_get_returns_list(self, api):
        mock_resp = _mock_response(status=200, json_data=[{"id": "dev-1"}])
        api._session.request = _mock_session_method(mock_resp)
        result = await api._get("/devices")
        assert result == [{"id": "dev-1"}]

    async def test_get_returns_dict(self, api):
        mock_resp = _mock_response(status=200, json_data={"key": "value"})
        api._session.request = _mock_session_method(mock_resp)
        result = await api._get("/test")
        assert result == {"key": "value"}

    async def test_get_raises_value_error_on_string(self, api):
        mock_resp = _mock_response(status=200, json_data="invalid")
        api._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ValueError, match="Unexpected API response type"):
            await api._get("/test")

    async def test_get_devices(self, api):
        mock_resp = _mock_response(
            status=200, json_data=[{"id": "dev-1", "name": "Remo"}]
        )
        api._session.request = _mock_session_method(mock_resp)
        result = await api.get_devices()
        assert result == [{"id": "dev-1", "name": "Remo"}]
        api._session.request.assert_called_once()
        call_args = api._session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{NATURE_REMO_CLOUD_URL}/devices"

    async def test_get_appliances(self, api):
        mock_resp = _mock_response(
            status=200, json_data=[{"id": "app-1", "type": "AC"}]
        )
        api._session.request = _mock_session_method(mock_resp)
        result = await api.get_appliances()
        assert result == [{"id": "app-1", "type": "AC"}]
        api._session.request.assert_called_once()
        call_args = api._session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{NATURE_REMO_CLOUD_URL}/appliances"

    async def test_send_command_climate(self, api):
        mock_resp = _mock_response(status=200, json_data={"status": "ok"})
        api._session.request = _mock_session_method(mock_resp)
        payload = {"temperature": "25"}
        result = await api.send_command_climate(payload, "app-1")
        assert result == {"status": "ok"}
        api._session.request.assert_called_once()
        call_args = api._session.request.call_args
        assert call_args[0][0] == "POST"
        assert (
            call_args[0][1]
            == f"{NATURE_REMO_CLOUD_URL}/appliances/app-1/aircon_settings"
        )
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    async def test_send_command_climate_failure(self, api):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="API request failed with status 500"):
            await api.send_command_climate({}, "app-1")

    async def test_send_local_ir_message_raises_without_local_ip(self, api):
        with pytest.raises(ValueError, match="local_ip is required for local IR messaging"):
            await api.send_local_ir_message(38, [100, 200])
        api._session.request.assert_not_called()

    async def test_send_local_ir_message_uses_local_ip(self, api_with_local_ip):
        mock_resp = _mock_response(status=200, json_data={"status": "sent"})
        api_with_local_ip._session.request = _mock_session_method(mock_resp)
        result = await api_with_local_ip.send_local_ir_message(38, [100, 200])
        assert result == {"status": "sent"}
        call_args = api_with_local_ip._session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "http://192.168.1.100/messages"
        # Local API must include X-Requested-With and must NOT send the cloud token.
        assert call_args[1]["headers"]["X-Requested-With"] == "homeassistant"
        assert "Authorization" not in call_args[1]["headers"]

    async def test_get_retries_on_429_then_succeeds(self, api):
        resp_429 = _mock_response(status=429)
        resp_200 = _mock_response(status=200, json_data=[{"id": "dev-1"}])
        responses = [resp_429, resp_200]

        api._session.request = MagicMock(
            side_effect=lambda *a, **k: _mock_context_manager(responses.pop(0))
        )
        result = await api._get("/devices")
        assert result == [{"id": "dev-1"}]
        assert api._session.request.call_count == 2

    async def test_get_raises_after_max_retries_on_429(self, api):
        resp_429 = _mock_response(status=429)
        responses = [resp_429, resp_429, resp_429]

        api._session.request = MagicMock(
            side_effect=lambda *a, **k: _mock_context_manager(responses.pop(0))
        )
        with pytest.raises(ClientError, match="API rate limit exceeded"):
            await api._get("/devices")
        assert api._session.request.call_count == 3

    async def test_get_uses_retry_after_header(self, api):
        resp_429 = _mock_response(status=429)
        resp_429.headers = {"Retry-After": "2"}
        resp_200 = _mock_response(status=200, json_data=[{"id": "dev-1"}])
        responses = [resp_429, resp_200]

        api._session.request = MagicMock(
            side_effect=lambda *a, **k: _mock_context_manager(responses.pop(0))
        )
        result = await api._get("/devices")
        assert result == [{"id": "dev-1"}]
        assert api._session.request.call_count == 2

    async def test_get_does_not_retry_on_401(self, api):
        resp_401 = _mock_response(status=401)
        api._session.request = _mock_session_method(resp_401)
        with pytest.raises(NatureRemoAuthError):
            await api._get("/devices")
        assert api._session.request.call_count == 1

    async def test_call_api_does_not_retry_on_500(self, api):
        resp_500 = _mock_response(status=500)

        api._session.request = MagicMock(
            side_effect=lambda *a, **k: _mock_context_manager(resp_500)
        )
        with pytest.raises(ClientError, match="API request failed with status 500"):
            await api._call_api("GET", "/devices")
        assert api._session.request.call_count == 1

    async def test_call_api_retries_on_timeout_then_succeeds(self, api):
        resp_200 = _mock_response(status=200, json_data={"status": "ok"})

        class TimeoutCtx:
            async def __aenter__(self):
                raise TimeoutError()
            async def __aexit__(self, *args):
                return False

        responses = [TimeoutCtx(), _mock_context_manager(resp_200)]
        api._session.request = MagicMock(side_effect=lambda *a, **k: responses.pop(0))
        result = await api._call_api("GET", "/devices")
        assert result == {"status": "ok"}
        assert api._session.request.call_count == 2

    async def test_call_api_does_not_retry_429_for_post(self, api):
        resp_429 = _mock_response(status=429)
        resp_429.headers = {"Retry-After": "1"}
        api._session.request = _mock_session_method(resp_429)
        with pytest.raises(ClientError, match="API rate limit exceeded"):
            await api._call_api("POST", "/signals/sig-1/send")
        assert api._session.request.call_count == 1

    async def test_send_light_command_failure(self, api):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="Light command failed"):
            await api.send_light_command("app-1", "on")

    async def test_send_command_signal_success(self, api):
        mock_resp = _mock_response(status=200, json_data={"status": "ok"})
        api._session.request = _mock_session_method(mock_resp)
        result = await api.send_command_signal("sig-1")
        assert result == {"status": "ok"}
        api._session.request.assert_called_once()
        call_args = api._session.request.call_args
        assert call_args[1]["data"] == {}

    async def test_send_command_signal_failure(self, api):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="Signal send failed"):
            await api.send_command_signal("sig-1")

    async def test_send_command_climate_turn_off_includes_temperature_unit(self, api):
        mock_resp = _mock_response(status=200, json_data={"button": "power-off"})
        api._session.request = _mock_session_method(mock_resp)
        payload = {"button": "power-off", "temperature_unit": "c"}
        result = await api.send_command_climate(payload, "app-1")
        assert result == {"button": "power-off"}
        api._session.request.assert_called_once()
        call_args = api._session.request.call_args
        assert call_args[1]["data"] == payload

    async def test_learn_signal_failure(self, api):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="Signal learn failed"):
            await api.learn_signal("app-1")

    async def test_send_local_ir_message_failure(self, api_with_local_ip):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api_with_local_ip._session.request = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="Local IR message failed"):
            await api_with_local_ip.send_local_ir_message(38, [100, 200])

    async def test_parse_smart_meter_properties(self, api):
        properties = [
            {"epc": 211, "val": "1"},
            {"epc": 225, "val": "0"},
            {"epc": 231, "val": "500"},
        ]
        result = api.parse_smart_meter_properties(properties)
        assert result["instant_power"] == 500
        assert result["buy_power"] == 0.0
