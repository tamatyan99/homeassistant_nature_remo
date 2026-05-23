import logging
from datetime import datetime

from aiohttp import ClientError

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)
NATURE_REMO_CLOUD_URL = "https://api.nature.global/1"


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
        base_url = self._get_base_url()
        url = f"{base_url}{path}"
        async with self._session.get(url, headers=headers) as response:
            if response.status == 429:
                _LOGGER.warning("API制限に達しました! 429 Too Many Requests.")

            self._log_rate_limits(response)

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

    async def get_appliances(self):
        return await self._get("/appliances")

    async def get_devices(self):
        return await self._get("/devices")

    async def send_command_climate(self, payload, appliance_id):
        _LOGGER.info("Setting payload: %s", payload)
        headers = {"Authorization": f"Bearer {self._token}"}
        api_url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/aircon_settings"

        async with self._session.post(
            api_url, headers=headers, data=payload
        ) as response:
            self._log_rate_limits(response)

            if response.status == 200:
                response_json = await response.json()
                _LOGGER.info("エアコンの操作に成功しました: %s", response_json)
                return response_json

            text = await response.text()
            _LOGGER.error(
                "エアコンの操作に失敗しました: %s - %s", response.status, text
            )
            raise ClientError(f"Climate command failed: {response.status}")

    async def send_light_command(self, appliance_id: str, command: str):
        _LOGGER.info(
            "Send Light appliance_id: %s command: %s", appliance_id, command
        )
        url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/light"
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"button": command}

        async with self._session.post(
            url, headers=headers, data=payload
        ) as response:
            self._log_rate_limits(response)

            if response.status == 200:
                response_json = await response.json()
                _LOGGER.info("照明の操作に成功しました: %s", response_json)
                return response_json

            text = await response.text()
            _LOGGER.error(
                "Nature Remo API Error: %s - %s", response.status, text
            )
            raise ClientError(f"Light command failed: {response.status}")

    async def send_echonetlite_refresh(
        self, appliance_id: str, epcs: list[str] | None = None
    ) -> dict:
        api_url = f"{NATURE_REMO_CLOUD_URL}/echonetlite/appliances/{appliance_id}/refresh"
        headers = {"Authorization": f"Bearer {self._token}"}
        data = {}
        if epcs:
            data["epc"] = ",".join(epcs)

        async with self._session.post(
            api_url, headers=headers, data=data
        ) as response:
            self._log_rate_limits(response)

            if response.status == 202:
                _LOGGER.info("EPC refresh request accepted: %s", appliance_id)
                return {"status": "accepted", "appliance_id": appliance_id}

            text = await response.text()
            _LOGGER.error(
                "EPC refresh failed for %s: %s - %s",
                appliance_id,
                response.status,
                text,
            )
            raise ClientError(f"EPC refresh failed: {response.status}")

    async def learn_signal(self, appliance_id: str) -> dict:
        api_url = f"{NATURE_REMO_CLOUD_URL}/appliances/{appliance_id}/IR"
        headers = {"Authorization": f"Bearer {self._token}"}

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

    def parse_smart_meter_properties(self, properties: list[dict]) -> dict:
        coefficient = 1
        unit_power = 0
        buy_power_raw = 0
        sold_power_raw = 0
        instant_power = 0

        for prop in properties:
            epc = int(prop.get("epc"))
            val_str = prop.get("val", "0")
            try:
                val = int(val_str)
            except ValueError:
                val = 0

            if epc == 211:
                coefficient = val
            elif epc == 215:
                continue
            elif epc == 224:
                buy_power_raw = val
            elif epc == 225:
                unit_power = val
            elif epc == 227:
                sold_power_raw = val
            elif epc == 231:
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

        async with self._session.post(api_url, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Failed to send signal %s: %s", signal_id, text)
                raise ClientError(
                    f"Signal send failed: {response.status}"
                )

    async def send_local_ir_message(self, freq: int, data: list[int]) -> dict:
        _LOGGER.info("Sending local IR message: freq=%s data_length=%s", freq, len(data))
        base_url = self._get_base_url()
        url = f"{base_url}/messages"
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"freq": freq, "data": data, "format": "us"}

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