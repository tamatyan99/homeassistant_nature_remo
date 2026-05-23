"""Tests for NatureRemoAPI."""

import aiohttp
import pytest
from aiohttp import ClientError
from unittest.mock import AsyncMock, MagicMock

from custom_components.nature_remo.api import NATURE_REMO_CLOUD_URL, NatureRemoAPI


def _mock_response(status=200, json_data=None, text=None):
    response = MagicMock()
    response.status = status
    response.headers = {}
    response.json = AsyncMock(return_value=json_data)
    response.text = AsyncMock(return_value=text or "")
    return response


def _mock_session_method(mock_resp):
    mock = MagicMock()
    mock.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
    mock.return_value.__aexit__ = AsyncMock(return_value=False)
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
        api._session.get = _mock_session_method(mock_resp)
        result = await api._get("/devices")
        assert result == [{"id": "dev-1"}]

    async def test_get_returns_dict(self, api):
        mock_resp = _mock_response(status=200, json_data={"key": "value"})
        api._session.get = _mock_session_method(mock_resp)
        result = await api._get("/test")
        assert result == {"key": "value"}

    async def test_get_raises_value_error_on_string(self, api):
        mock_resp = _mock_response(status=200, json_data="invalid")
        api._session.get = _mock_session_method(mock_resp)
        with pytest.raises(ValueError, match="Unexpected API response type"):
            await api._get("/test")

    async def test_get_devices(self, api):
        mock_resp = _mock_response(
            status=200, json_data=[{"id": "dev-1", "name": "Remo"}]
        )
        api._session.get = _mock_session_method(mock_resp)
        result = await api.get_devices()
        assert result == [{"id": "dev-1", "name": "Remo"}]
        api._session.get.assert_called_once()
        call_args = api._session.get.call_args
        assert call_args[0][0] == f"{NATURE_REMO_CLOUD_URL}/devices"

    async def test_get_appliances(self, api):
        mock_resp = _mock_response(
            status=200, json_data=[{"id": "app-1", "type": "AC"}]
        )
        api._session.get = _mock_session_method(mock_resp)
        result = await api.get_appliances()
        assert result == [{"id": "app-1", "type": "AC"}]
        api._session.get.assert_called_once()
        call_args = api._session.get.call_args
        assert call_args[0][0] == f"{NATURE_REMO_CLOUD_URL}/appliances"

    async def test_send_command_climate(self, api):
        mock_resp = _mock_response(status=200, json_data={"status": "ok"})
        api._session.post = _mock_session_method(mock_resp)
        payload = {"temperature": "25"}
        result = await api.send_command_climate(payload, "app-1")
        assert result == {"status": "ok"}
        api._session.post.assert_called_once()
        call_args = api._session.post.call_args
        assert (
            call_args[0][0]
            == f"{NATURE_REMO_CLOUD_URL}/appliances/app-1/aircon_settings"
        )
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    async def test_send_command_climate_failure(self, api):
        mock_resp = _mock_response(status=500, text="Internal Server Error")
        api._session.post = _mock_session_method(mock_resp)
        with pytest.raises(ClientError, match="Climate command failed"):
            await api.send_command_climate({}, "app-1")

    async def test_send_local_ir_message_uses_cloud_by_default(self, api):
        mock_resp = _mock_response(status=200, json_data={"status": "sent"})
        api._session.post = _mock_session_method(mock_resp)
        result = await api.send_local_ir_message(38, [100, 200])
        assert result == {"status": "sent"}
        call_args = api._session.post.call_args
        assert call_args[0][0] == f"{NATURE_REMO_CLOUD_URL}/messages"

    async def test_send_local_ir_message_uses_local_ip(self, api_with_local_ip):
        mock_resp = _mock_response(status=200, json_data={"status": "sent"})
        api_with_local_ip._session.post = _mock_session_method(mock_resp)
        result = await api_with_local_ip.send_local_ir_message(38, [100, 200])
        assert result == {"status": "sent"}
        call_args = api_with_local_ip._session.post.call_args
        assert call_args[0][0] == "http://192.168.1.100/messages"
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"
