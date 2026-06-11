import logging

from aiohttp import ClientError
from homeassistant.components.light import ColorMode, LightEntity, LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAuthError
from .const import DOMAIN
from .coordinator import NatureRemoCoordinator
from .entity import get_device_info

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


class NatureRemoLight(CoordinatorEntity[NatureRemoCoordinator], LightEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, coordinator, appliance, device, api) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_light_{appliance['appliance_id']}"
        self._attr_name = None
        self._appliance = appliance
        self._device = device
        self._appliance_id = appliance["appliance_id"]
        self._is_on = False
        self._last_mode = "on"
        self._attr_effect_list: list[str] = []
        self._api = api

    @property
    def supported_effects(self) -> list[str]:
        return self._attr_effect_list

    @property
    def appliance_id(self) -> str:
        return self._appliance_id

    @property
    def device_info(self):
        return get_device_info(self._device)

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
        await super().async_added_to_hass()
        self.coordinator.entity_map[self.entity_id] = self
        self._handle_coordinator_update()

    async def async_will_remove_from_hass(self):
        self.coordinator.entity_map.pop(self.entity_id, None)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("[%s] Start _handle_coordinator_update.", self._attr_name)
        if self.coordinator.data is None:
            return
        appliance = self.coordinator.data.get(self._appliance_id, {})

        if appliance:
            light_data = appliance.get("light")
            if light_data is not None:
                _LOGGER.debug("Nature Remo Settings: %s", light_data)

                state = light_data.get("state") or {}
                self._is_on = state.get("power") == "on"
                self._last_mode = state.get("last_button", "on")

                effect_buttons = light_data.get("buttons") or []
                self._attr_effect_list = [btn["name"] for btn in effect_buttons]
                _LOGGER.debug(
                    "[%s] Available buttons: %s", self._attr_name, self._attr_effect_list
                )

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("kwargs: %s", kwargs)
        unsupported = set(kwargs) - {"effect", "transition"}
        if unsupported:
            _LOGGER.warning(
                "[%s] Unsupported kwargs ignored: %s",
                self._attr_unique_id,
                unsupported,
            )
        effect = kwargs.get("effect", "on")

        # Allow "on" even if effect list is empty (startup edge case)
        if effect != "on" and effect not in self._attr_effect_list:
            raise HomeAssistantError(f"Effect '{effect}' is not supported by this light")

        prev_is_on = self._is_on
        prev_mode = self._last_mode
        try:
            response = await self._api.send_light_command(self._appliance_id, effect)
            _LOGGER.debug(
                "[%s] send_light_command response: %s", self._attr_name, response
            )
            self._is_on = effect != "off"
            self._last_mode = effect
        except NatureRemoAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (ClientError, TimeoutError):
            self._is_on = prev_is_on
            self._last_mode = prev_mode
            self.async_write_ha_state()
            raise
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        prev_is_on = self._is_on
        prev_mode = self._last_mode
        try:
            await self._api.send_light_command(self._appliance_id, "off")
            self._is_on = False
            self._last_mode = "off"
        except NatureRemoAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except (ClientError, TimeoutError):
            self._is_on = prev_is_on
            self._last_mode = prev_mode
            self.async_write_ha_state()
            raise
        self.async_write_ha_state()
