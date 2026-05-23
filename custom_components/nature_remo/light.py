import logging

from aiohttp import ClientError
from homeassistant.components.light import LightEntity, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    _LOGGER.debug("Nature Remo Light: async_setup_entry called")

    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    for appliance in coordinator.lights.values():
        entity = NatureRemoLight(
            coordinator=coordinator,
            appliance=appliance,
            device=appliance["device"],
            api=api,
        )
        entities.append(entity)

    if not entities:
        _LOGGER.warning("No light appliances matched selected IDs.")

    async_add_entities(entities, True)


class NatureRemoLight(LightEntity):

    def __init__(self, coordinator, appliance, device, api) -> None:
        self._attr_unique_id = f"nature_remo_light_{appliance['appliance_id']}"
        self._attr_name = f"Nature Remo {appliance['name']}"
        self._coordinator = coordinator
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._is_on = False
        self._last_mode = "on"
        self._supported_effects: list[str] = []
        self._api = api

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    @property
    def supported_effects(self) -> list[str]:
        return self._supported_effects

    @property
    def appliance_id(self) -> str:
        return self._appliance_id

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
    def supported_color_modes(self):
        return self._attr_supported_color_modes

    @property
    def color_mode(self):
        return ColorMode.ONOFF

    @property
    def is_on(self):
        return self._is_on

    @property
    def extra_state_attributes(self):
        return {"remo_light_mode": self._last_mode}

    def set_mode(self, mode: str) -> None:
        self._last_mode = mode
        self._is_on = mode != "off"
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        _LOGGER.debug(
            "[%s] async_added_to_hass: Light entity complete setup", self._attr_name
        )
        self.async_on_remove(self._coordinator.async_add_listener(self.update_status))
        self.update_status()
        self._coordinator.entity_map[self.entity_id] = self

    async def async_will_remove_from_hass(self):
        self._coordinator.entity_map.pop(self.entity_id, None)

    def update_status(self) -> None:
        _LOGGER.debug("[%s] Start update_status.", self._attr_name)
        appliance = self._coordinator.data.get(self._appliance_id, {})

        if appliance and "light" in appliance:
            _LOGGER.debug("Nature Remo Settings: %s", appliance["light"])

            state = appliance["light"].get("state", {})
            self._is_on = state.get("power") == "on"
            self._last_mode = state.get("last_button", "on")

            effect_buttons = appliance["light"].get("buttons", [])
            self._supported_effects = [btn["name"] for btn in effect_buttons]
            _LOGGER.debug(
                "[%s] 有効ボタン: %s", self._attr_name, self._supported_effects
            )

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("kwargs: %s", kwargs)
        mode = kwargs.get("remo_light_mode", "on")

        if mode not in self._supported_effects:
            raise HomeAssistantError(f"Effect '{mode}' is not supported by this light")

        try:
            response = await self._api.send_light_command(self._appliance_id, mode)
            _LOGGER.debug(
                "[%s] send_light_command response: %s", self._attr_name, response
            )
            self._is_on = mode != "off"
            self._last_mode = mode
        except (ClientError, TimeoutError):
            _LOGGER.error("Failed to turn on light")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        try:
            await self._api.send_light_command(self._appliance_id, "off")
            self._is_on = False
            self._last_mode = "off"
        except (ClientError, TimeoutError):
            _LOGGER.error("Failed to turn off light")
        self.async_write_ha_state()
