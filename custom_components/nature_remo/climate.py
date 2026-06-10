import contextlib
import logging
from collections.abc import Callable

from aiohttp import ClientError
from homeassistant.components.climate import (
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAPI, NatureRemoAuthError
from .const import DOMAIN, HA_MODE_TO_REMO_MODE, REMO_MODE_TO_HA_MODE
from .coordinator import NatureRemoCoordinator
from .entity import get_device_info

_LOGGER = logging.getLogger(__name__)

TEMPERATURE_UNIT_CELSIUS = "c"


def _build_climate_payload(**kwargs) -> dict:
    """Build a climate command payload, always including the temperature unit."""
    payload = dict(kwargs)
    if "temperature" in payload or "operation_mode" in payload:
        payload.setdefault("temperature_unit", TEMPERATURE_UNIT_CELSIUS)
    return payload


async def async_apply_ac_preset(
    api: NatureRemoAPI,
    appliance_id: str,
    preset_mode: str,
    hvac_mode: HVACMode,
    target_temperature: float | int | str,
) -> dict:
    """Build the AC preset payload and send it via the API."""
    if preset_mode == "eco":
        payload = _build_climate_payload(button="eco", temperature="26")
    else:
        operation_mode = HA_MODE_TO_REMO_MODE.get(hvac_mode.value)
        if operation_mode is None:
            raise HomeAssistantError(f"Invalid HVAC mode: {hvac_mode}")
        payload = _build_climate_payload(
            operation_mode=operation_mode,
            temperature=str(target_temperature),
        )
    return await api.send_command_climate(payload, appliance_id)


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


class NatureRemoClimate(CoordinatorEntity[NatureRemoCoordinator], ClimateEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        appliance,
        device,
        api,
        entry_id: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_climate_{appliance['appliance_id']}"
        self._attr_name = None
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
        self._preset_mode = PRESET_NONE

    @property
    def device_info(self):
        return get_device_info(self._device)

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
        return [PRESET_NONE, "eco"]

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

    async def _apply_climate_command(
        self,
        payload: dict,
        *,
        state_updates: dict,
        rollback: dict,
        post_success: Callable | None = None,
    ) -> dict:
        """Send a climate command and apply optimistic updates with rollback on network error."""
        previous = {name: getattr(self, name) for name in rollback}
        try:
            response = await self._api.send_command_climate(payload, self._appliance_id)
            for name, value in state_updates.items():
                setattr(self, name, value)
            if post_success is not None:
                post_success(response)
            return response
        except NatureRemoAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (ClientError, TimeoutError):
            for name, value in previous.items():
                setattr(self, name, value)
            self.async_write_ha_state()
            raise

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self.preset_modes:
            raise HomeAssistantError(f"Invalid preset mode: {preset_mode}")
        target_temp = 26 if preset_mode == "eco" else self._target_temperature
        prev_preset = self._preset_mode
        prev_temp = self._target_temperature
        prev_button = self._button
        try:
            response = await async_apply_ac_preset(
                self._api,
                self._appliance_id,
                preset_mode,
                self._hvac_mode,
                target_temp,
            )
            self._preset_mode = preset_mode if preset_mode == "eco" else PRESET_NONE
            self._target_temperature = target_temp
            self._button = ""
            self._update_from_response(response)
            self.async_write_ha_state()
        except HomeAssistantError:
            self._preset_mode = prev_preset
            self._target_temperature = prev_temp
            self._button = prev_button
            self.async_write_ha_state()
            raise
        except NatureRemoAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (ClientError, TimeoutError):
            self._preset_mode = prev_preset
            self._target_temperature = prev_temp
            self._button = prev_button
            self.async_write_ha_state()
            raise

    @property
    def target_temperature_step(self) -> float:
        temp_list = self._get_temp_list()
        if not temp_list:
            return 1.0

        differences = [
            temp_list[i + 1] - temp_list[i] for i in range(len(temp_list) - 1)
        ]

        step = 1.0
        if len(set(differences)) == 1:
            step = differences[0]
        return step

    @property
    def min_temp(self):
        temp_list = self._get_temp_list()
        if not temp_list:
            return 16.0
        return min(temp_list)

    @property
    def max_temp(self):
        temp_list = self._get_temp_list()
        if not temp_list:
            return 30.0
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
        remo_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
        return self._aircon_range_modes.get(remo_mode, {}).get("vol", [])

    @property
    def swing_modes(self) -> list[str] | None:
        remo_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
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

    def _get_temp_list(self) -> list[float]:
        """Return parsed temperature list for current HVAC mode."""
        remo_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
        temp_list = self._aircon_range_modes.get(remo_mode, {}).get("temp", [])
        try:
            temp_list = list(map(float, filter(None, temp_list)))
        except (ValueError, TypeError):
            return []
        return temp_list

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
            self._attr_unique_id,
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

    def _update_external_sensors(self) -> None:
        external_temperature = self._get_external_sensor_value("temperature")
        if external_temperature is not None:
            self._temperature = external_temperature

        external_humidity = self._get_external_sensor_value("humidity")
        if external_humidity is not None:
            self._humidity = external_humidity

    def _update_device_events(self) -> None:
        device_id = self._device["device_id"]
        device_data = self.coordinator.devices.get(device_id)
        if device_data is None:
            _LOGGER.warning(
                "Device '%s' not found in coordinator devices.", device_id
            )
            return

        device_events = device_data.get("events", {})
        if self._temperature is None and "te" in device_events:
            self._temperature = device_events["te"].get("val")
        if self._humidity is None and "hu" in device_events:
            self._humidity = device_events["hu"].get("val")

    def _update_aircon_state(self, appliance: dict) -> None:
        if appliance and "settings" in appliance:
            hvac_mode = self.get_remo_mode_to_hvac_mode(
                appliance["settings"].get("mode", "")
            )
            if hvac_mode is not None:
                self._hvac_mode = hvac_mode

            self._button = appliance["settings"].get("button", "")
            self._preset_mode = "eco" if self._button == "eco" else PRESET_NONE

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
                if self._aircon_range_modes.get(HA_MODE_TO_REMO_MODE.get(HVACMode.COOL.value), {}):
                    set_range_modes.append(HVACMode.COOL)
                if self._aircon_range_modes.get(HA_MODE_TO_REMO_MODE.get(HVACMode.DRY.value), {}):
                    set_range_modes.append(HVACMode.DRY)
                if self._aircon_range_modes.get(HA_MODE_TO_REMO_MODE.get(HVACMode.HEAT.value), {}):
                    set_range_modes.append(HVACMode.HEAT)
                if self._aircon_range_modes.get(HA_MODE_TO_REMO_MODE.get(HVACMode.FAN_ONLY.value), {}):
                    set_range_modes.append(HVACMode.FAN_ONLY)
                if self._aircon_range_modes.get(HA_MODE_TO_REMO_MODE.get(HVACMode.AUTO.value), {}):
                    set_range_modes.append(HVACMode.AUTO)
                self._hvac_modes = set_range_modes

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("[%s] Start _handle_coordinator_update.", self._attr_unique_id)
        if self.coordinator.data is None:
            _LOGGER.debug("[%s] Coordinator data is None, skipping update.", self._attr_unique_id)
            return
        appliance = self.coordinator.data.get(self._appliance_id, {})

        # Reset external sensor values so unavailable sensors fall back to device events
        self._temperature = None
        self._humidity = None
        self._update_external_sensors()
        self._update_device_events()
        self._update_aircon_state(appliance)

        self.async_write_ha_state()

    def get_remo_mode_to_hvac_mode(self, remo_mode) -> HVACMode | None:
        ha_mode_str = REMO_MODE_TO_HA_MODE.get(remo_mode)
        if ha_mode_str is None:
            return None
        try:
            return HVACMode(ha_mode_str)
        except ValueError:
            return None

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

    async def _on_external_sensor_state_changed(self, event) -> None:
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
        self._handle_coordinator_update()

    async def async_added_to_hass(self):
        _LOGGER.debug("[%s] async_added_to_hass: Climate entity complete setup", self._attr_unique_id)
        await super().async_added_to_hass()

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

        self._handle_coordinator_update()

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.info("Setting HVAC mode: %s", hvac_mode)
        if hvac_mode not in self.hvac_modes:
            raise HomeAssistantError(f"Unsupported HVAC mode: {hvac_mode}")

        if hvac_mode == HVACMode.OFF:
            payload = _build_climate_payload(button="power-off")
        else:
            operation_mode = HA_MODE_TO_REMO_MODE.get(hvac_mode.value)
            payload = _build_climate_payload(
                operation_mode=operation_mode,
                temperature=self.format_temperature(self._target_temperature),
            )

        def _post_success(response):
            self._preset_mode = PRESET_NONE
            self._button = ""
            self._update_from_response(response)
            if hvac_mode == HVACMode.OFF:
                self._button = "power-off"
            elif self._button == "power-off":
                self._button = ""

        await self._apply_climate_command(
            payload,
            state_updates={},
            rollback={"_button": self._button, "_hvac_mode": self._hvac_mode},
            post_success=_post_success,
        )
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            raise HomeAssistantError("Temperature not specified")

        operation_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
        if operation_mode is None:
            raise HomeAssistantError(f"Invalid HVAC mode: {self._hvac_mode}")

        _LOGGER.debug("Setting temperature to: %s", temperature)

        set_temperature = self.format_temperature(temperature)
        payload = _build_climate_payload(
            operation_mode=operation_mode,
            temperature=set_temperature,
        )

        await self._apply_climate_command(
            payload,
            state_updates={"_target_temperature": temperature, "_button": ""},
            rollback={"_target_temperature": self._target_temperature, "_button": self._button},
        )
        self.async_write_ha_state()

    def _update_from_response(self, response: dict) -> None:
        """Update entity state from API response."""
        if not isinstance(response, dict):
            _LOGGER.warning("Unexpected response type: %s", type(response))
            return
        hvac_mode_result = self.get_remo_mode_to_hvac_mode(response.get("mode", ""))
        if hvac_mode_result is not None:
            self._hvac_mode = hvac_mode_result
        temp = "0.0" if self._hvac_mode == HVACMode.FAN_ONLY else response.get("temp", "25.0")
        with contextlib.suppress(ValueError, TypeError):
            self._target_temperature = float(temp)
        self._fan_mode = response.get("vol", self._fan_mode)
        self._swing_mode = response.get("dir", self._swing_mode)
        self._button = response.get("button", "")

    def format_temperature(self, value: float) -> str:
        try:
            if float(value).is_integer():
                return str(int(value))
        except (TypeError, ValueError):
            pass
        return str(value)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        operation_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
        if operation_mode is None:
            raise HomeAssistantError(f"Invalid HVAC mode: {self._hvac_mode}")

        payload = _build_climate_payload(
            operation_mode=operation_mode,
            air_volume=fan_mode,
        )

        await self._apply_climate_command(
            payload,
            state_updates={"_fan_mode": fan_mode, "_button": ""},
            rollback={"_fan_mode": self._fan_mode, "_button": self._button},
        )
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        operation_mode = HA_MODE_TO_REMO_MODE.get(self._hvac_mode.value)
        if operation_mode is None:
            raise HomeAssistantError(f"Invalid HVAC mode: {self._hvac_mode}")

        payload = _build_climate_payload(
            operation_mode=operation_mode,
            air_direction=swing_mode,
        )

        await self._apply_climate_command(
            payload,
            state_updates={"_swing_mode": swing_mode, "_button": ""},
            rollback={"_swing_mode": self._swing_mode, "_button": self._button},
        )
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the climate device on."""
        if self.hvac_mode != HVACMode.OFF:
            return
        # Default to COOL if available, otherwise first non-OFF mode
        target_mode = HVACMode.COOL
        if target_mode not in self.hvac_modes:
            for mode in self.hvac_modes:
                if mode != HVACMode.OFF:
                    target_mode = mode
                    break
        if target_mode == HVACMode.OFF:
            raise HomeAssistantError("No HVAC mode available to turn on")
        await self.async_set_hvac_mode(target_mode)

    async def async_turn_off(self) -> None:
        """Turn the climate device off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
