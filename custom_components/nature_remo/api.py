import asyncio
import logging
from datetime import datetime

from aiohttp import ClientError

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
NATURE_REMO_CLOUD_URL = "https://api.nature.global/1"


class NatureRemoAuthError(ClientError):
    """Raised when the API returns 401 Unauthorized."""


class NatureRemoAPI:

    def __init__(self, hass, token, local_ip: str | None = None) -> None:
        self._token = token
        self._session = async_get_clientsession(hass)
        self._local_ip = local_ip

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

    async def _get(self, path: str):
        headers = {"Authorization": f"Bearer {self._token}"}
        # Data fetching always uses the cloud API; local IP is only for IR control
        url = f"{NATURE_REMO_CLOUD_URL}{path}"
        max_retries = 3

        for attempt in range(max_retries + 1):
            try:
                async with self._session.get(url, headers=headers) as response:
                    self._log_rate_limits(response)

                    if response.status == 429:
                        _LOGGER.warning("API rate limit hit (429)")
                        if attempt < max_retries:
                            delay = 2 ** attempt
                            retry_after = response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    delay = int(retry_after)
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

                    if response.status >= 500:
                        _LOGGER.warning("Server error (%s)", response.status)
                        if attempt < max_retries:
                            delay = 2 ** attempt
                            _LOGGER.warning("Retrying in %d seconds...", delay)
                            await asyncio.sleep(delay)
                            continue
                        else:
                            _LOGGER.error("Failed to fetch request: %s", response.status)
                            raise ClientError(
                                f"API request failed with status {response.status}"
                            )

                    if response.status == 401:
                        _LOGGER.error("Authentication failed: invalid API token")
                        raise NatureRemoAuthError(
                            "API request failed with status 401 (Unauthorized)"
                        )

                    if response.status == 200:
                        data = await response.json()
                        if not isinstance(data, (list, dict)):
                            _LOGGER.error(
                                "Unexpected response type from API: %s (expected list or dict)",
                                type(data),
                            )
                            raise ValueError(
                                f"Unexpected API response type: {type(data)}"
                            )
                        return data

                    _LOGGER.error("Failed to fetch request: %s", response.status)
                    raise ClientError(
                        f"API request failed with status {response.status}"
                    )
            except (ClientError, TimeoutError):
                if attempt < max_retries:
                    delay = 2 ** attempt
                    _LOGGER.warning("Retrying in %d seconds...", delay)
                    await asyncio.sleep(delay)
                    continue
                raise

    async def get_appliances(self):
        return await self._get("/appliances")

    async def get_devices(self):
        return await self._get("/devices")

    async def send_command_climate(self, payload, appliance_id):
        _LOGGER.info("Setting payload: %s", payload)
        headers = {"Authorization": f"Bearer {self._token}"}
        api_url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/aircon_settings"

        try:
            async with self._session.post(
                api_url, headers=headers, data=payload
            ) as response:
                self._log_rate_limits(response)

                if response.status == 200:
                    response_json = await response.json()
                    _LOGGER.info("Climate command succeeded: %s", response_json)
                    return response_json

                text = await response.text()
                _LOGGER.error(
                    "Climate command failed: %s - %s", response.status, text
                )
                raise ClientError(f"Climate command failed: {response.status}")
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Climate command failed: %s", err)
            raise ClientError(f"Climate command failed: {err}") from err

    async def send_light_command(self, appliance_id: str, command: str):
        _LOGGER.info(
            "Send Light appliance_id: %s command: %s", appliance_id, command
        )
        url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/light"
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"button": command}

        try:
            async with self._session.post(
                url, headers=headers, data=payload
            ) as response:
                self._log_rate_limits(response)

                if response.status == 200:
                    response_json = await response.json()
                    _LOGGER.info("Light command succeeded: %s", response_json)
                    return response_json

                text = await response.text()
                _LOGGER.error(
                    "Nature Remo API Error: %s - %s", response.status, text
                )
                raise ClientError(f"Light command failed: {response.status}")
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Light command failed: %s", err)
            raise ClientError(f"Light command failed: {err}") from err

    async def learn_signal(self, appliance_id: str) -> dict:
        api_url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/IR"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.post(api_url, headers=headers) as response:
                self._log_rate_limits(response)

                if response.status == 200:
                    response_json = await response.json()
                    _LOGGER.info("Signal learned successfully: %s", appliance_id)
                    return response_json

                text = await response.text()
                _LOGGER.error(
                    "Signal learn failed for %s: %s - %s",
                    appliance_id,
                    response.status,
                    text,
                )
                raise ClientError(f"Signal learn failed: {response.status}")
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
        api_url = f"{NATURE_REMO_CLOUD_URL}/signals/{signal_id}/send"
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.post(api_url, headers=headers) as response:
                self._log_rate_limits(response)
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to send signal %s: %s", signal_id, text)
                    raise ClientError(
                        f"Signal send failed: {response.status}"
                    )
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Signal send failed: %s", err)
            raise ClientError(f"Signal send failed: {err}") from err

    async def send_local_ir_message(self, freq: int, data: list[int]) -> dict:
        _LOGGER.info("Sending local IR message: freq=%s data_length=%s", freq, len(data))
        base_url = self._get_base_url()
        url = f"{base_url}/messages"
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"freq": freq, "data": data, "format": "us"}

        try:
            async with self._session.post(
                url, headers=headers, json=payload
            ) as response:
                self._log_rate_limits(response)

                if response.status == 200:
                    response_json = await response.json()
                    _LOGGER.info("Local IR message sent successfully: %s", response_json)
                    return response_json

                text = await response.text()
                _LOGGER.error(
                    "Failed to send local IR message: %s - %s", response.status, text
                )
                raise ClientError(f"Local IR message failed: {response.status}")
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Local IR message failed: %s", err)
            raise ClientError(f"Local IR message failed: {err}") from err
