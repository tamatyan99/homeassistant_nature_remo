from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAPI
from .const import DOMAIN, OFF_COMMANDS, ON_COMMANDS
from .entity import get_device_info
from .coordinator import NatureRemoCoordinator

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

    entities = [
        NatureRemoRemoteEntity(
            coordinator=coordinator, api=api, remote_info=remote_info
        )
        for remote_info in coordinator.ir_remotes.values()
    ]

    async_add_entities(entities, True)


class NatureRemoRemoteEntity(CoordinatorEntity[NatureRemoCoordinator], RemoteEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        api: NatureRemoAPI,
        remote_info: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_remote_{remote_info['appliance_id']}"
        self._attr_name = None
        self._api = api
        self._device = remote_info["device"]
        self._appliance_id = remote_info["appliance_id"]
        self._remote_info = remote_info
        self._commands = {s["name"].lower(): s["id"] for s in remote_info["signals"]}

        self._attr_state = "off"
        self._power_on_id = next(
            (self._commands[c] for c in ON_COMMANDS if c in self._commands), None
        )
        self._power_off_id = next(
            (self._commands[c] for c in OFF_COMMANDS if c in self._commands), None
        )

    @property
    def device_info(self):
        return get_device_info(self._device)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "available_commands": list(self._commands.keys()),
            "command": self._attr_state,
        }

    @property
    def available(self) -> bool:
        return super().available and bool(self._commands)

    async def async_send_command(self, command: list[str], **kwargs: Any) -> None:
        failed = []
        for cmd in command:
            signal_id = self._commands.get(cmd)
            if signal_id:
                try:
                    await self._api.send_command_signal(signal_id)
                except Exception as err:
                    failed.append(cmd)
                    _LOGGER.error("Failed to send command '%s': %s", cmd, err)
        if failed:
            raise ServiceValidationError(f"Failed to send commands: {', '.join(failed)}")
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        if self._power_on_id:
            try:
                await self._api.send_command_signal(self._power_on_id)
                self._attr_state = "on"
                self.async_write_ha_state()
            except (ClientError, TimeoutError):
                _LOGGER.error("Failed to send power ON command")
                raise HomeAssistantError(
                    f"Power ON command failed for {self.name}"
                )
        else:
            raise HomeAssistantError(f"Power ON command not available for {self.name}")

    async def async_turn_off(self) -> None:
        if self._power_off_id:
            try:
                await self._api.send_command_signal(self._power_off_id)
                self._attr_state = "off"
                self.async_write_ha_state()
            except (ClientError, TimeoutError):
                _LOGGER.error("Failed to send power OFF command")
                raise HomeAssistantError(
                    f"Power OFF command failed for {self.name}"
                )
        else:
            raise HomeAssistantError(
                f"Power OFF command not available for {self.name}"
            )
