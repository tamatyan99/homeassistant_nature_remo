from datetime import timedelta, datetime
import logging
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed


_LOGGER = logging.getLogger(__name__)


class NatureRemoCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, api, update_interval: int = 60) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Nature Remo Coordinator",
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.devices: dict[str, dict] = {}
        self.aircons: dict[str, dict] = {}
        self.lights: dict[str, dict] = {}
        self.ir_remotes: dict[str, dict] = {}
        self.smart_meters: dict[str, dict] = {}
        self.motion_sensors: dict[str, dict] = {}
        self.echonetlite_appliances: dict[str, dict] = {}
        self.entity_map: dict[str, Any] = {}
        self.motion_threshold_minutes: int = 5

    async def _async_update_data(self):
        _LOGGER.debug("NatureRemoCoordinator.async_update_data start.")
        try:
            new_devices = {}
            new_motion_sensors = {}

            devices = await self.api.get_devices()
            for device in devices:
                device_id = device.get("id")
                name = device.get("name", "Unnamed")
                newest_events = device.get("newest_events", {})
                serial_number = device.get("serial_number", "")
                mac_address = device.get("mac_address", "")

                motion_event = newest_events.get("mo")
                if motion_event:
                    created_at_str = motion_event.get("created_at")
                    if created_at_str:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                        now = datetime.now(created_at.tzinfo)
                        is_active = (now - created_at) < timedelta(
                            minutes=self.motion_threshold_minutes
                        )
                        new_motion_sensors[device_id] = {
                            "name": name,
                            "device_id": device_id,
                            "last_motion": created_at,
                            "is_active": is_active,
                            "firmware_version": device.get("firmware_version", ""),
                            "serial_number": serial_number,
                            "mac_address": mac_address,
                        }

                new_devices[device_id] = {
                    "name": name,
                    "device_id": device_id,
                    "events": newest_events,
                    "firmware_version": device.get("firmware_version", ""),
                    "serial_number": serial_number,
                    "mac_address": mac_address,
                }

            new_aircons = {}
            new_lights = {}
            new_smart_meters = {}
            new_ir_remotes = {}

            appliances = await self.api.get_appliances()

            for appliance in appliances:
                appliance_type = appliance.get("type")
                appliance_id = appliance.get("id")
                nickname = appliance.get("nickname", "Unnamed")
                device_info = {
                    "name": appliance.get("device", {}).get("name", "No Name"),
                    "device_id": appliance.get("device", {}).get("id", ""),
                    "firmware_version": appliance.get("device", {}).get(
                        "firmware_version", ""
                    ),
                    "serial_number": appliance.get("device", {}).get(
                        "serial_number", ""
                    ),
                    "mac_address": appliance.get("device", {}).get(
                        "mac_address", ""
                    ),
                }
                appliance_info = {
                    "name": nickname,
                    "appliance_id": appliance_id,
                    "device": device_info,
                }

                if appliance_type == "EL_SMART_METER":
                    properties = appliance.get("smart_meter", {}).get(
                        "echonetlite_properties", []
                    )
                    parsed = self.api.parse_smart_meter_properties(properties)

                    _LOGGER.debug(
                        "[%s] buy_power: %s, sold_power: %s, current_power: %s",
                        nickname,
                        parsed["buy_power"],
                        parsed["sold_power"],
                        parsed["instant_power"],
                    )
                    new_smart_meters[appliance_id] = {
                        "name": nickname,
                        "appliance_id": appliance_id,
                        "device": device_info,
                        "buy_power": parsed["buy_power"],
                        "sold_power": parsed["sold_power"],
                        "current_power": parsed["instant_power"],
                    }

                elif appliance_type == "AC":
                    new_aircons[appliance_id] = appliance_info
                    signals = appliance.get("signals", [])
                    if signals:
                        new_ir_remotes[appliance_id] = {
                            "name": nickname,
                            "appliance_id": appliance_id,
                            "device": device_info,
                            "signals": signals,
                        }

                elif appliance_type == "LIGHT":
                    new_lights[appliance_id] = appliance_info
                    signals = appliance.get("signals", [])
                    if signals:
                        new_ir_remotes[appliance_id] = {
                            "name": nickname,
                            "appliance_id": appliance_id,
                            "device": device_info,
                            "signals": signals,
                        }

                elif appliance_type == "IR":
                    signals = appliance.get("signals", [])
                    if signals:
                        new_ir_remotes[appliance_id] = {
                            "name": nickname,
                            "appliance_id": appliance_id,
                            "device": device_info,
                            "signals": signals,
                        }

            new_echonetlite = {}
            try:
                echonetlite_appliances = await self.api.get_echonetlite_appliances()
                for appliance in echonetlite_appliances:
                    el_id = appliance.get("id")
                    el_nickname = appliance.get("nickname", "Unnamed")
                    el_type = appliance.get("type", "")
                    el_device = {
                        "name": appliance.get("device", {}).get("name", "No Name"),
                        "device_id": appliance.get("device", {}).get("id", ""),
                        "firmware_version": appliance.get("device", {}).get(
                            "firmware_version", ""
                        ),
                        "serial_number": appliance.get("device", {}).get(
                            "serial_number", ""
                        ),
                        "mac_address": appliance.get("device", {}).get(
                            "mac_address", ""
                        ),
                    }
                    properties_raw = appliance.get("echonetlite_properties", [])
                    parsed_properties = self.api.parse_echonetlite_properties(
                        properties_raw, el_type
                    )
                    new_echonetlite[el_id] = {
                        "name": el_nickname,
                        "appliance_id": el_id,
                        "type": el_type,
                        "device": el_device,
                        "properties": parsed_properties,
                    }
                self.echonetlite_appliances = new_echonetlite
            except (ClientError, TimeoutError, ValueError) as err:
                _LOGGER.warning("ECHONET Lite data fetch skipped: %s", err)

            self.devices = new_devices
            self.aircons = new_aircons
            self.lights = new_lights
            self.smart_meters = new_smart_meters
            self.ir_remotes = new_ir_remotes
            self.motion_sensors = new_motion_sensors

            return {ac["id"]: ac for ac in appliances}
        except ClientError as err:
            raise UpdateFailed(f"通信エラー: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed("APIの応答がタイムアウトしました") from err
        except ValueError as err:
            raise UpdateFailed(f"JSONデータのパースエラー: {err}") from err