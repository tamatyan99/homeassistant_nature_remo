import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MODE_MAP = {
    HVACMode.COOL: "cool",
    HVACMode.HEAT: "warm",
    HVACMode.DRY: "dry",
    HVACMode.FAN_ONLY: "blow",
    HVACMode.AUTO: "auto",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    _LOGGER.debug("Nature Remo Climate: async_setup_entry called")

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: NatureRemoCoordinator = data["coordinator"]
    api = data["api"]

    entities = []

    for appliance in coordinator.aircons.values():
        entity = NatureRemoClimate(
            coordinator=coordinator,
            appliance=appliance,
            device=appliance["device"],
            api=api,
            entry_id=entry.entry_id,
        )
        entities.append(entity)

    if not entities:
        _LOGGER.warning("No climate appliances matched selected IDs.")

    async_add_entities(entities, True)


class NatureRemoClimate(ClimateEntity):

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        appliance,
        device,
        api,
        entry_id: str | None = None,
    ) -> None:
        self._attr_unique_id = f"nature_remo_climate_{appliance['appliance_id']}"
        self._attr_name = f"Nature Remo {appliance['name']}"
        self._coordinator = coordinator
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._temperature = None
        self._humidity = None
        self._hvac_modes = [HVACMode.OFF]
        self._hvac_mode = HVACMode.OFF
        self._button = "power-off"
        self._api = api
        self._target_temperature = 25
        self._fan_mode = "auto"
        self._swing_mode = "auto"
        self._aircon_range_modes = {}
        self._entry_id = entry_id
        self._preset_mode = "none"

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def device_info(self):
        di = {
            "identifiers": {(DOMAIN, self._device["device_id"])},
            "name": self._device["name"],
            "manufacturer": "Nature",
            "model": self._device.get("firmware_version", "Nature Remo"),
        }
        if self._device.get("serial_number"):
            di["serial_number"] = self._device["serial_number"]
        if self._device.get("mac_address"):
            di["hw_version"] = self._device["mac_address"]
        return di

    @property
    def supported_features(self) -> int:
        support_feature = (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )
        if self.min_temp != 0.0 and self.max_temp != 0.0:
            support_feature = support_feature | ClimateEntityFeature.TARGET_TEMPERATURE
        if self.fan_modes:
            support_feature = support_feature | ClimateEntityFeature.FAN_MODE
        if self.swing_modes:
            support_feature = support_feature | ClimateEntityFeature.SWING_MODE
        support_feature = support_feature | ClimateEntityFeature.PRESET_MODE
        return support_feature

    @property
    def preset_modes(self) -> list[str] | None:
        return ["none", "eco"]

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == "eco":
            operation_mode = MODE_MAP.get(self._hvac_mode)
            if operation_mode is None:
                return
            payload = {"operation_mode": operation_mode, "temperature": "26"}
            try:
                await self._api.send_command_climate(payload, self._appliance_id)
                self._target_temperature = 26
                self._preset_mode = "eco"
            except Exception:
                _LOGGER.error("Failed to set preset mode")
        else:
            self._preset_mode = "none"
        self.async_write_ha_state()

    @property
    def target_temperature_step(self) -> float:
        remo_mode = MODE_MAP.get(self._hvac_mode)
        temp_list = self._aircon_range_modes.get(remo_mode, {}).get("temp", [])
        temp_list = list(map(float, filter(None, temp_list)))

        if not temp_list:
            return 0.0

        differences = [
            temp_list[i + 1] - temp_list[i] for i in range(len(temp_list) - 1)
        ]

        step = 1.0
        if len(set(differences)) == 1:
            step = differences[0]
        return step

    @property
    def min_temp(self):
        remo_mode = MODE_MAP.get(self._hvac_mode)
        temp_list = self._aircon_range_modes.get(remo_mode, {}).get("temp", [])
        temp_list = list(map(float, filter(None, temp_list)))
        if not temp_list:
            return 0.0
        return min(temp_list)

    @property
    def max_temp(self):
        remo_mode = MODE_MAP.get(self._hvac_mode)
        temp_list = self._aircon_range_modes.get(remo_mode, {}).get("temp", [])
        temp_list = list(map(float, filter(None, temp_list)))
        if not temp_list:
            return 0.0
        return max(temp_list)

    @property
    def current_temperature(self) -> float | None:
        return self._temperature

    @property
    def current_humidity(self) -> int | None:
        return self._humidity

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self):
        if self._button == "power-off":
            return HVACMode.OFF
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return self._hvac_modes

    @property
    def fan_modes(self) -> list[str] | None:
        remo_mode = MODE_MAP.get(self._hvac_mode)
        return self._aircon_range_modes.get(remo_mode, {}).get("vol", [])

    @property
    def swing_modes(self) -> list[str] | None:
        remo_mode = MODE_MAP.get(self._hvac_mode)
        return self._aircon_range_modes.get(remo_mode, {}).get("dir", [])

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def fan_mode(self) -> str | None:
        return self._fan_mode

    @property
    def swing_mode(self) -> str | None:
        return self._swing_mode

    def _get_external_sensor_value(self, sensor_type: str) -> float | None:
        if self.hass is None or self._entry_id is None:
            return None

        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            _LOGGER.warning(
                "ConfigEntry not found for entry_id '%s'.", self._entry_id
            )
            return None

        device_id = self._device["device_id"]
        option_key = f"external_{sensor_type}_{device_id}"
        entity_id = entry.options.get(option_key)

        _LOGGER.debug(
            "[%s] [%s] device_id='%s', option_key='%s', entity_id='%s'",
            self._attr_name,
            sensor_type,
            device_id,
            option_key,
            entity_id,
        )

        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.debug(
                "External %s sensor '%s' state not found.", sensor_type, entity_id
            )
            return None

        try:
            value = float(state.state)
            _LOGGER.debug(
                "Got %s value %s from external sensor '%s'",
                sensor_type,
                value,
                entity_id,
            )
            return value
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid %s value from external sensor '%s': %s",
                sensor_type,
                entity_id,
                state.state,
            )
            return None

    def update_status(self) -> None:
        _LOGGER.debug("[%s] Start update_status.", self._attr_name)
        appliance = self._coordinator.data.get(self._appliance_id, {})

        external_temperature = self._get_external_sensor_value("temperature")
        if external_temperature is not None:
            self._temperature = external_temperature

        external_humidity = self._get_external_sensor_value("humidity")
        if external_humidity is not None:
            self._humidity = external_humidity

        device_id = self._device["device_id"]
        device_data = self._coordinator.devices.get(device_id)
        if device_data is None:
            _LOGGER.warning(
                "Device '%s' not found in coordinator devices.", device_id
            )
        else:
            device_events = device_data.get("events", {})
            if external_temperature is None:
                if "te" in device_events:
                    self._temperature = device_events["te"].get("val")
            if external_humidity is None:
                if "hu" in device_events:
                    self._humidity = device_events["hu"].get("val")

        if appliance and "settings" in appliance:
            hvac_mode = self.get_remo_mode_to_hvac_mode(
                appliance["settings"].get("mode", "")
            )
            if hvac_mode is not None:
                self._hvac_mode = hvac_mode

            self._button = appliance["settings"].get("button", "")

            temp = appliance["settings"].get("temp", "20.0")
            try:
                self._target_temperature = float(temp)
            except (ValueError, TypeError):
                self._target_temperature = 0.0

            self._fan_mode = appliance["settings"].get("vol", "auto")
            self._swing_mode = appliance["settings"].get("dir", "auto")

        if appliance and "aircon" in appliance:
            self._aircon_range_modes = (
                appliance["aircon"].get("range", {}).get("modes", {})
            )
            if self._aircon_range_modes:
                set_range_modes = [HVACMode.OFF]
                if self._aircon_range_modes.get("cool", {}):
                    set_range_modes.append(HVACMode.COOL)
                if self._aircon_range_modes.get("dry", {}):
                    set_range_modes.append(HVACMode.DRY)
                if self._aircon_range_modes.get("warm", {}):
                    set_range_modes.append(HVACMode.HEAT)
                if self._aircon_range_modes.get("blow", {}):
                    set_range_modes.append(HVACMode.FAN_ONLY)
                if self._aircon_range_modes.get("auto", {}):
                    set_range_modes.append(HVACMode.AUTO)
                self._hvac_modes = set_range_modes

        self.async_write_ha_state()

    def get_remo_mode_to_hvac_mode(self, remo_mode) -> HVACMode | None:
        return next(
            (key for key, value in MODE_MAP.items() if value == remo_mode),
            None,
        )

    def _get_external_sensor_entity_ids(self) -> list[str]:
        if self.hass is None or self._entry_id is None:
            return []

        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return []

        device_id = self._device["device_id"]
        entity_ids = []

        for sensor_type in ("temperature", "humidity"):
            option_key = f"external_{sensor_type}_{device_id}"
            entity_id = entry.options.get(option_key)
            if entity_id:
                entity_ids.append(entity_id)

        return entity_ids

    def _on_external_sensor_state_changed(self, event) -> None:
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")

        if new_state is None:
            _LOGGER.debug(
                "External sensor '%s' new state is None. Skipping.", entity_id
            )
            return

        _LOGGER.debug(
            "External sensor '%s' state changed: %s", entity_id, new_state.state
        )
        self.update_status()

    async def async_added_to_hass(self):
        _LOGGER.debug("[%s] async_added_to_hass: Climate entity complete setup", self._attr_name)
        self.async_on_remove(self._coordinator.async_add_listener(self.update_status))

        external_entity_ids = self._get_external_sensor_entity_ids()
        if external_entity_ids:
            _LOGGER.debug(
                "Registering state change listeners for: %s", external_entity_ids
            )
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    external_entity_ids,
                    self._on_external_sensor_state_changed,
                )
            )

        self.update_status()

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info("Setting HVAC mode: %s", hvac_mode)
        if hvac_mode not in self.hvac_modes:
            _LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return

        if hvac_mode == HVACMode.OFF:
            payload = {"button": "power-off"}
            self._button = "power-off"
        else:
            operation_mode = MODE_MAP.get(hvac_mode)
            payload = {"operation_mode": operation_mode}
            self._button = ""
            self._hvac_mode = hvac_mode

        try:
            response = await self._api.send_command_climate(payload, self._appliance_id)
        except Exception:
            _LOGGER.error("Failed to set HVAC mode")
            self.async_write_ha_state()
            return

        _LOGGER.info("Set HVACMode: %s", response)
        hvac_mode_result = self.get_remo_mode_to_hvac_mode(response.get("mode", ""))
        if hvac_mode_result is not None:
            self._hvac_mode = hvac_mode_result
        if self._hvac_mode == HVACMode.FAN_ONLY:
            temp = "0.0"
        else:
            temp = response.get("temp", "25.0")
        self._target_temperature = float(temp)
        self._fan_mode = response.get("vol", "auto")
        self._swing_mode = response.get("dir", "auto")
        self._button = response.get("button", "")

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.warning("温度が指定されていません！")
            return

        operation_mode = MODE_MAP.get(self._hvac_mode)
        if operation_mode is None:
            _LOGGER.error("Invalid HVAC mode: %s", self._hvac_mode)
            return

        _LOGGER.debug("Setting temperature to: %s", temperature)

        set_temperature = self.format_temperature(temperature)
        payload = {
            "operation_mode": operation_mode,
            "temperature": set_temperature,
        }

        try:
            await self._api.send_command_climate(payload, self._appliance_id)
            self._target_temperature = temperature
            self._button = ""
        except Exception:
            _LOGGER.error("Failed to set temperature")

        self.async_write_ha_state()

    def format_temperature(self, value: float) -> str:
        if value.is_integer():
            return str(int(value))
        else:
            return str(value)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        operation_mode = MODE_MAP.get(self._hvac_mode)
        if operation_mode is None:
            _LOGGER.error("Invalid HVAC mode: %s", self._hvac_mode)
            return

        payload = {
            "operation_mode": operation_mode,
            "air_volume": fan_mode,
        }

        try:
            await self._api.send_command_climate(payload, self._appliance_id)
            self._fan_mode = fan_mode
            self._button = ""
        except Exception:
            _LOGGER.error("Failed to set fan mode")

        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        operation_mode = MODE_MAP.get(self._hvac_mode)
        if operation_mode is None:
            _LOGGER.error("Invalid HVAC mode: %s", self._hvac_mode)
            return

        payload = {
            "operation_mode": operation_mode,
            "air_direction": swing_mode,
        }

        try:
            await self._api.send_command_climate(payload, self._appliance_id)
            self._swing_mode = swing_mode
            self._button = ""
        except Exception:
            _LOGGER.error("Failed to set swing mode")

        self.async_write_ha_state()
