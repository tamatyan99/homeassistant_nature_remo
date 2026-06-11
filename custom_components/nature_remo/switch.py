from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAPI, NatureRemoAuthError
from .const import DOMAIN
from .coordinator import NatureRemoCoordinator
from .entity import build_ir_commands, get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    api: NatureRemoAPI = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    for remote_info in coordinator.ir_remotes.values():
        commands, power_on_id, power_off_id = build_ir_commands(remote_info)
        if power_on_id or power_off_id:
            entities.append(
                NatureRemoSwitchEntity(
                    coordinator=coordinator, api=api, remote_info=remote_info
                )
            )

    async_add_entities(entities, True)


class NatureRemoSwitchEntity(CoordinatorEntity[NatureRemoCoordinator], SwitchEntity):
    _attr_icon = "mdi:remote"
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        api: NatureRemoAPI,
        remote_info: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_switch_{remote_info['appliance_id']}"
        self._attr_name = None
        self._api = api
        self._device = remote_info["device"]
        self._appliance_id = remote_info["appliance_id"]
        self._is_on = False
        self._commands, self._power_on_id, self._power_off_id = build_ir_commands(
            remote_info
        )

    @property
    def device_info(self):
        return get_device_info(self._device)

    @callback
    def _handle_coordinator_update(self) -> None:
        remote_info = self.coordinator.ir_remotes.get(self._appliance_id)
        if remote_info:
            self._commands, self._power_on_id, self._power_off_id = build_ir_commands(
                remote_info
            )
        else:
            self._commands, self._power_on_id, self._power_off_id = {}, None, None
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        return super().available and bool(self._commands)

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self) -> None:
        if self._power_on_id:
            previous_is_on = self._is_on
            try:
                await self._api.send_command_signal(self._power_on_id)
                self._is_on = True
                self.async_write_ha_state()
            except NatureRemoAuthError as err:
                self._is_on = previous_is_on
                self.async_write_ha_state()
                raise HomeAssistantError(f"Authentication failed: {err}") from err
            except ClientError as err:
                self._is_on = previous_is_on
                self.async_write_ha_state()
                _LOGGER.error("Failed to send power ON command")
                raise HomeAssistantError(
                    f"Power ON command failed for {self.name}"
                ) from err
        else:
            raise HomeAssistantError(
                f"Power ON command not available for {self.name}"
            )

    async def async_turn_off(self) -> None:
        if self._power_off_id:
            previous_is_on = self._is_on
            try:
                await self._api.send_command_signal(self._power_off_id)
                self._is_on = False
                self.async_write_ha_state()
            except NatureRemoAuthError as err:
                self._is_on = previous_is_on
                self.async_write_ha_state()
                raise HomeAssistantError(f"Authentication failed: {err}") from err
            except ClientError as err:
                self._is_on = previous_is_on
                self.async_write_ha_state()
                _LOGGER.error("Failed to send power OFF command")
                raise HomeAssistantError(
                    f"Power OFF command failed for {self.name}"
                ) from err
        else:
            raise HomeAssistantError(
                f"Power OFF command not available for {self.name}"
            )
