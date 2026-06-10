import asyncio
import json
import logging
from typing import Any
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
NATURE_REMO_CLOUD_URL = "https://api.nature.global/1"


class NatureRemoAuthError(Exception):
    """Raised when the API returns 401 Unauthorized."""


class NatureRemoAPI:

    def __init__(self, hass: HomeAssistant, token: str, local_ip: str | None = None) -> None:
        self._token = token
        self._session = async_get_clientsession(hass)
        self._local_ip = local_ip
        self._headers = {"Authorization": f"Bearer {token}"}
        self._cloud_request_lock = asyncio.Lock()

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

    @staticmethod
    def _parse_retry_after(value: str | None, fallback: int) -> int:
        """Parse Retry-After header per RFC 7231 (seconds or HTTP-date)."""
        if not value:
            return fallback
        try:
            return max(0, int(value))
        except ValueError:
            try:
                dt = parsedate_to_datetime(value)
                return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError):
                return fallback

    async def _call_api(
        self,
        method: str,
        path: str,
        *,
        data: dict | None = None,
        json_payload: dict | None = None,
        use_local: bool = False,
        max_retries: int = 2,
    ) -> dict | list:
        """Send an HTTP request to the Nature Remo Cloud API with retry logic."""
        base_url = self._get_base_url() if use_local else NATURE_REMO_CLOUD_URL
        url = f"{base_url}{path}"
        timeout = ClientTimeout(total=30, connect=10)

        # Serialize cloud requests to avoid rate limit bursts
        if not use_local:
            async with self._cloud_request_lock:
                return await self._execute_request(
                    method, url, data, json_payload, timeout, max_retries
                )
        return await self._execute_request(
            method, url, data, json_payload, timeout, max_retries
        )

    async def _execute_request(
        self,
        method: str,
        url: str,
        data: dict | None,
        json_payload: dict | None,
        timeout: ClientTimeout,
        max_retries: int,
    ) -> dict | list:
        for attempt in range(max_retries + 1):
            try:
                async with self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    data=data,
                    json=json_payload,
                    timeout=timeout,
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
                            fallback = 60
                            reset_ts = response.headers.get("X-Rate-Limit-Reset")
                            if reset_ts:
                                try:
                                    fallback = max(0, int(int(reset_ts) - datetime.now(timezone.utc).timestamp()))
                                except (ValueError, TypeError):
                                    pass
                            retry_after = response.headers.get("Retry-After")
                            delay = self._parse_retry_after(retry_after, fallback)
                            _LOGGER.warning("Rate limited. Retrying in %d seconds...", delay)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            body = await response.text()
                            _LOGGER.error("Rate limit exceeded after retries: %s", body[:500])
                            raise ClientError(
                                f"API rate limit exceeded (429). Response: {body[:200]}"
                            )

                    if response.ok:
                        try:
                            data_resp = await response.json()
                        except json.JSONDecodeError as err:
                            text = await response.text()
                            _LOGGER.error("Invalid JSON response: %s", text[:500])
                            raise ClientError(f"Invalid JSON response: {err}") from err
                        if not isinstance(data_resp, (list, dict)):
                            _LOGGER.error(
                                "Unexpected response type from API: %s (expected list or dict)",
                                type(data_resp),
                            )
                            raise ValueError(
                                f"Unexpected API response type: {type(data_resp)}"
                            )
                        return data_resp

                    body = await response.text()
                    _LOGGER.error("API request failed: %s - %s", response.status, body[:500])
                    raise ClientError(
                        f"API request failed with status {response.status}: {body[:200]}"
                    )
            except NatureRemoAuthError:
                raise
            except TimeoutError:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    _LOGGER.warning("Request timed out. Retrying in %d seconds...", delay)
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
        except NatureRemoAuthError:
            raise
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
        except NatureRemoAuthError:
            raise
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Light command failed: %s", err)
            raise ClientError(f"Light command failed: {err}") from err

    async def learn_signal(self, appliance_id: str) -> dict:
        path = f"/appliances/{appliance_id}/IR"
        try:
            result = await self._call_api("POST", path)
            _LOGGER.debug("Signal learned successfully: %s", appliance_id)
            return result
        except NatureRemoAuthError:
            raise
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

    async def send_command_signal(self, signal_id: str) -> dict:
        path = f"/signals/{signal_id}/send"
        try:
            result = await self._call_api("POST", path)
            return result
        except NatureRemoAuthError:
            raise
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Signal send failed: %s", err)
            raise ClientError(f"Signal send failed: {err}") from err

    async def send_local_ir_message(self, freq: int, data: list[int]) -> dict:
        _LOGGER.debug("Sending local IR message: freq=%s data_length=%s", freq, len(data))
        path = "/messages"
        payload = {"freq": freq, "data": data, "format": "us"}
        try:
            result = await self._call_api("POST", path, json_payload=payload, use_local=True)
            _LOGGER.debug("Local IR message sent successfully: %s", result)
            return result
        except NatureRemoAuthError:
            raise
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Local IR message failed: %s", err)
            raise ClientError(f"Local IR message failed: {err}") from err
