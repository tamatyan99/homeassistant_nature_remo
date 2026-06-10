import contextlib
import logging

from aiohttp import ClientError
from homeassistant.components.climate import HVACMode
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .climate import async_apply_ac_preset
from .const import DOMAIN, REMO_MODE_TO_HA_MODE
from .coordinator import NatureRemoCoordinator
from .entity import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    _LOGGER.debug("Nature Remo Select: async_setup_entry called")

    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []

    for appliance in coordinator.lights.values():
        entities.append(
            NatureRemoLightSelect(
                coordinator=coordinator,
                appliance=appliance,
                device=appliance["device"],
                api=api,
            )
        )

    for appliance in coordinator.aircons.values():
        entities.append(
            NatureRemoAcPresetSelect(
                coordinator=coordinator,
                appliance=appliance,
                device=appliance["device"],
                api=api,
            )
        )

    if not entities:
        _LOGGER.warning("No select appliances matched selected IDs.")

    async_add_entities(entities, True)


class NatureRemoLightSelect(CoordinatorEntity[NatureRemoCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, appliance, device, api) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_light_select_{appliance['appliance_id']}"
        self._attr_name = "Mode"
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._api = api
        self._attr_options: list[str] = []
        self._attr_current_option: str | None = None

    @property
    def device_info(self):
        return get_device_info(self._device)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is None:
            return
        appliance = self.coordinator.data.get(self._appliance_id, {})
        if appliance and "light" in appliance:
            effect_buttons = appliance["light"].get("buttons", [])
            self._attr_options = [btn["name"] for btn in effect_buttons]
            state = appliance["light"].get("state", {})
            self._attr_current_option = state.get("last_button")
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise HomeAssistantError(f"Invalid option: {option}")

        prev_option = self._attr_current_option
        try:
            await self._api.send_light_command(self._appliance_id, option)
            self._attr_current_option = option
        except (ClientError, TimeoutError):
            self._attr_current_option = prev_option
            self.async_write_ha_state()
            raise
        self.async_write_ha_state()


class NatureRemoAcPresetSelect(CoordinatorEntity[NatureRemoCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, appliance, device, api) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_ac_preset_{appliance['appliance_id']}"
        self._attr_name = "Preset"
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._api = api
        self._attr_options = ["none", "eco"]
        self._attr_current_option = "none"
        self._hvac_mode = HVACMode.OFF

    @property
    def device_info(self):
        return get_device_info(self._device)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is None:
            return
        appliance = self.coordinator.data.get(self._appliance_id, {})
        if appliance and "settings" in appliance:
            settings = appliance["settings"]
            if settings.get("button") == "eco":
                self._attr_current_option = "eco"
            else:
                self._attr_current_option = "none"
            remo_mode = settings.get("mode", "")
            ha_mode_str = REMO_MODE_TO_HA_MODE.get(remo_mode)
            if ha_mode_str is not None:
                with contextlib.suppress(ValueError):
                    self._hvac_mode = HVACMode(ha_mode_str)
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise HomeAssistantError(f"Invalid option: {option}")

        if option == "eco":
            target_temp = 26
        else:
            appliance = self.coordinator.data.get(self._appliance_id, {})
            target_temp = appliance.get("settings", {}).get("temp", "25") if appliance else "25"

        prev_option = self._attr_current_option
        try:
            await async_apply_ac_preset(
                self._api,
                self._appliance_id,
                option,
                self._hvac_mode,
                target_temp,
            )
            self._attr_current_option = option
        except (ClientError, TimeoutError):
            self._attr_current_option = prev_option
            self.async_write_ha_state()
            raise
        self.async_write_ha_state()
