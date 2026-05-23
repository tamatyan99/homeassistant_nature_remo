import logging

from aiohttp import ClientError
from homeassistant.components.climate import HVACMode
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NatureRemoCoordinator

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

    def __init__(self, coordinator, appliance, device, api) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_light_select_{appliance['appliance_id']}"
        self._attr_name = f"Nature Remo {appliance['name']} Mode"
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._api = api
        self._attr_options: list[str] = []
        self._attr_current_option: str | None = None

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
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        appliance = self.coordinator.data.get(self._appliance_id, {})
        if appliance and "light" in appliance:
            effect_buttons = appliance["light"].get("buttons", [])
            self._attr_options = [btn["name"] for btn in effect_buttons]
            state = appliance["light"].get("state", {})
            self._attr_current_option = state.get("last_button")
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise ValueError(f"Option '{option}' is not supported by this light")

        try:
            await self._api.send_light_command(self._appliance_id, option)
            self._attr_current_option = option
        except (ClientError, TimeoutError):
            _LOGGER.error("Failed to set light mode")
        self.async_write_ha_state()


class NatureRemoAcPresetSelect(CoordinatorEntity[NatureRemoCoordinator], SelectEntity):

    def __init__(self, coordinator, appliance, device, api) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_ac_preset_{appliance['appliance_id']}"
        self._attr_name = f"Nature Remo {appliance['name']} Preset"
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._api = api
        self._attr_options = ["none", "eco"]
        self._attr_current_option = "none"
        self._hvac_mode = HVACMode.OFF

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
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        appliance = self.coordinator.data.get(self._appliance_id, {})
        if appliance and "settings" in appliance:
            remo_mode = appliance["settings"].get("mode", "")
            hvac_mode = next(
                (key for key, value in MODE_MAP.items() if value == remo_mode),
                None,
            )
            if hvac_mode is not None:
                self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option == "eco":
            operation_mode = MODE_MAP.get(self._hvac_mode)
            if operation_mode is None:
                return
            payload = {"operation_mode": operation_mode, "temperature": "26"}
            try:
                await self._api.send_command_climate(payload, self._appliance_id)
                self._attr_current_option = "eco"
            except (ClientError, TimeoutError):
                _LOGGER.error("Failed to set AC preset mode")
        else:
            self._attr_current_option = "none"
        self.async_write_ha_state()
