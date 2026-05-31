import asyncio
import logging
from typing import Any
from datetime import datetime

from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
NATURE_REMO_CLOUD_URL = "https://api.nature.global/1"
SAFE_RETRY_METHODS = {"GET"}
REQUEST_TIMEOUT = ClientTimeout(total=10)


class NatureRemoAuthError(ClientError):
    """Raised when the API returns 401 Unauthorized."""


class NatureRemoAPI:

    def __init__(self, hass: HomeAssistant, token: str, local_ip: str | None = None) -> None:
        self._token = token
        self._session = async_get_clientsession(hass)
        self._local_ip = local_ip
        self._headers = {"Authorization": f"Bearer {token}"}

    def _get_base_url(self) -> str:
        if self._local_ip:
            return f"http://{self._local_ip}"
        return NATURE_REMO_CLOUD_URL

    def _log_rate_limits(self, response) -> None:
        rate_limit = response.headers.get("X-Rate-Limit-Limit")
        rate_remaining = response.headers.get("X-Rate-Limit-Remaining")
        rate_reset = response.headers.get("X-Rate-Limit-Reset")

        if rate_reset is not None:
            try:
                reset_time = datetime.fromtimestamp(int(rate_reset))
            except (ValueError, TypeError):
                reset_time = "unknown"
        else:
            reset_time = "unknown"

        _LOGGER.debug(
            "NatureRemo RateLimit → Limit: %s, Remaining: %s, Reset: %s",
            rate_limit,
            rate_remaining,
            reset_time,
        )

    async def _call_api(
        self,
        method: str,
        path: str,
        *,
        data: dict | None = None,
        json_payload: dict | None = None,
        use_local: bool = False,
        max_retries: int | None = None,
    ) -> dict | list:
        """Send an HTTP request to the Nature Remo Cloud API with retry logic."""
        method = method.upper()
        if max_retries is None:
            max_retries = 1 if method in SAFE_RETRY_METHODS else 0

        base_url = self._get_base_url() if use_local else NATURE_REMO_CLOUD_URL
        url = f"{base_url}{path}"

        for attempt in range(max_retries + 1):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    data=data,
                    json=json_payload,
                    timeout=REQUEST_TIMEOUT,
                ) as response:
                    self._log_rate_limits(response)

                    if response.status == 401:
                        _LOGGER.error("Authentication failed: invalid API token")
                        raise NatureRemoAuthError(
                            "API request failed with status 401 (Unauthorized)"
                        )

                    if response.status == 429:
                        _LOGGER.warning("API rate limit hit (429)")
                        if attempt < max_retries:
                            delay = max(5, 2 ** attempt)
                            retry_after = response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    delay = max(5, int(retry_after))
                                except ValueError:
                                    pass
                            _LOGGER.warning("Retrying in %d seconds...", delay)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            _LOGGER.error("Failed to fetch request: %s", response.status)
                            raise ClientError(
                                f"API request failed with status {response.status}"
                            )

                    if response.ok:
                        data_resp = await response.json()
                        if not isinstance(data_resp, (list, dict)):
                            _LOGGER.error(
                                "Unexpected response type from API: %s (expected list or dict)",
                                type(data_resp),
                            )
                            raise ValueError(
                                f"Unexpected API response type: {type(data_resp)}"
                            )
                        return data_resp

                    _LOGGER.error("Failed to fetch request: %s", response.status)
                    raise ClientError(
                        f"API request failed with status {response.status}"
                    )
            except NatureRemoAuthError:
                raise
            except TimeoutError:
                if attempt < max_retries:
                    delay = max(5, 2 ** attempt)
                    _LOGGER.warning("Retrying in %d seconds...", delay)
                    await asyncio.sleep(delay)
                    continue
                raise

    async def _get(self, path: str) -> dict | list:
        return await self._call_api("GET", path)

    async def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        json_payload: dict | None = None,
        use_local: bool = False,
    ) -> dict | list:
        return await self._call_api(method, path, data=data, json_payload=json_payload, use_local=use_local)

    async def get_appliances(self) -> list[dict[str, Any]]:
        return await self._get("/appliances")

    async def get_devices(self) -> list[dict[str, Any]]:
        return await self._get("/devices")

    async def send_command_climate(self, payload: dict[str, Any], appliance_id: str) -> dict:
        _LOGGER.debug("Setting payload: %s", payload)
        path = f"/appliances/{appliance_id}/aircon_settings"
        try:
            result = await self._call_api("POST", path, data=payload)
            _LOGGER.debug("Climate command succeeded: %s", result)
            return result
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Climate command failed: %s", err)
            raise ClientError(f"Climate command failed: {err}") from err

    async def send_light_command(self, appliance_id: str, command: str) -> dict:
        _LOGGER.debug(
            "Send Light appliance_id: %s command: %s", appliance_id, command
        )
        path = f"/appliances/{appliance_id}/light"
        payload = {"button": command}
        try:
            result = await self._call_api("POST", path, data=payload)
            _LOGGER.debug("Light command succeeded: %s", result)
            return result
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Light command failed: %s", err)
            raise ClientError(f"Light command failed: {err}") from err

    async def learn_signal(self, appliance_id: str) -> dict:
        path = f"/appliances/{appliance_id}/IR"
        try:
            result = await self._call_api("POST", path)
            _LOGGER.debug("Signal learned successfully: %s", appliance_id)
            return result
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Signal learn failed: %s", err)
            raise ClientError(f"Signal learn failed: {err}") from err

    def parse_smart_meter_properties(self, properties: list[dict]) -> dict:
        from .const import (
            SMART_METER_EPC_COEFFICIENT,
            SMART_METER_EPC_UNIT,
            SMART_METER_EPC_BUY_POWER,
            SMART_METER_EPC_SOLD_POWER,
            SMART_METER_EPC_INSTANT_POWER,
        )

        coefficient = 1
        unit_power = 0
        buy_power_raw = 0
        sold_power_raw = 0
        instant_power = 0

        for prop in properties:
            epc_val = prop.get("epc")
            if epc_val is None:
                continue
            try:
                epc = int(epc_val)
            except (ValueError, TypeError):
                continue
            val_str = prop.get("val", "0")
            if val_str is None:
                val_str = "0"
            try:
                val = int(val_str)
            except (ValueError, TypeError):
                val = 0

            if epc == SMART_METER_EPC_COEFFICIENT:
                coefficient = val
            elif epc == SMART_METER_EPC_UNIT:
                unit_power = val
            elif epc == SMART_METER_EPC_BUY_POWER:
                buy_power_raw = val
            elif epc == SMART_METER_EPC_SOLD_POWER:
                sold_power_raw = val
            elif epc == SMART_METER_EPC_INSTANT_POWER:
                instant_power = val

        unit_table = {
            0x00: 1,
            0x01: 0.1,
            0x02: 0.01,
            0x03: 0.001,
            0x04: 0.0001,
            0x0A: 10,
            0x0B: 100,
            0x0C: 1000,
            0x0D: 10000,
        }

        factor = coefficient * unit_table.get(unit_power, 1)
        buy_power = buy_power_raw * factor
        sold_power = sold_power_raw * factor

        return {
            "buy_power": buy_power,
            "sold_power": sold_power,
            "instant_power": instant_power,
        }

    async def send_command_signal(self, signal_id: str) -> None:
        path = f"/signals/{signal_id}/send"
        try:
            await self._call_api("POST", path)
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Signal send failed: %s", err)
            raise ClientError(f"Signal send failed: {err}") from err

    async def send_local_ir_message(self, freq: int, data: list[int]) -> dict:
        _LOGGER.debug("Sending local IR message: freq=%s data_length=%s", freq, len(data))
        base_url = self._get_base_url()
        url = f"{base_url}/messages"
        payload = {"freq": freq, "data": data, "format": "us"}

        async with self._session.post(
            url, headers=self._headers, json=payload
        ) as response:
            if response.status == 200:
                response_json = await response.json()
                _LOGGER.debug("Local IR message sent successfully: %s", response_json)
                return response_json

            text = await response.text()
            _LOGGER.error("Failed to send local IR message: %s - %s", response.status, text)
            raise ClientError(f"Local IR message failed: {response.status}")
