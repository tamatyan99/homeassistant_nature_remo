from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAPI
from .const import DOMAIN, OFF_COMMANDS, ON_COMMANDS
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

    entities = []
    for remote_info in coordinator.ir_remotes.values():
        commands = {s["name"].lower(): s["id"] for s in remote_info["signals"]}
        has_on = any(c in commands for c in ON_COMMANDS)
        has_off = any(c in commands for c in OFF_COMMANDS)
        if has_on or has_off:
            entities.append(
                NatureRemoSwitchEntity(
                    coordinator=coordinator, api=api, remote_info=remote_info
                )
            )

    async_add_entities(entities)


class NatureRemoSwitchEntity(CoordinatorEntity[NatureRemoCoordinator], SwitchEntity):
    _attr_icon = "mdi:remote"
    _attr_has_entity_name = True

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
        self._commands = {s["name"].lower(): s["id"] for s in remote_info["signals"]}
        self._power_on_id = next(
            (self._commands[c] for c in ON_COMMANDS if c in self._commands), None
        )
        self._power_off_id = next(
            (self._commands[c] for c in OFF_COMMANDS if c in self._commands), None
        )

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._device["device_id"])},
            "name": self._device["name"],
            "manufacturer": "Nature",
            "model": self._device.get("firmware_version") or "Nature Remo",
            "sw_version": self._device.get("firmware_version", ""),
        }
        mac = self._device.get("mac_address")
        if mac:
            info["connections"] = {("mac", mac)}
        return info

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self) -> None:
        if self._power_on_id:
            try:
                await self._api.send_command_signal(self._power_on_id)
                self._is_on = True
                self.async_write_ha_state()
            except (ClientError, TimeoutError):
                _LOGGER.error("Failed to send power ON command")
                raise HomeAssistantError(
                    "Power ON command failed for %s" % self.name
                )
        else:
            raise HomeAssistantError(
                "Power ON command not available for %s" % self.name
            )

    async def async_turn_off(self) -> None:
        if self._power_off_id:
            try:
                await self._api.send_command_signal(self._power_off_id)
                self._is_on = False
                self.async_write_ha_state()
            except (ClientError, TimeoutError):
                _LOGGER.error("Failed to send power OFF command")
                raise HomeAssistantError(
                    "Power OFF command failed for %s" % self.name
                )
        else:
            raise HomeAssistantError(
                "Power OFF command not available for %s" % self.name
            )
