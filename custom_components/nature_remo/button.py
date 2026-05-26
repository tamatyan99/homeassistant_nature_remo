from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import NatureRemoAPI
from .const import DOMAIN
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

    entities: list[ButtonEntity] = []

    for remote_info in coordinator.ir_remotes.values():
        entities.append(
            NatureRemoLearnSignalButton(
                coordinator=coordinator,
                api=api,
                remote_info=remote_info,
            )
        )

    for device_info in coordinator.devices.values():
        entities.append(
            NatureRemoRefreshDataButton(
                coordinator=coordinator,
                device_info=device_info,
            )
        )

    async_add_entities(entities)


class NatureRemoLearnSignalButton(CoordinatorEntity[NatureRemoCoordinator], ButtonEntity):
    """Button to learn a new IR signal for an appliance."""

    _attr_icon = "mdi:remote"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        api: NatureRemoAPI,
        remote_info: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_learn_signal_{remote_info['appliance_id']}"
        self._attr_name = "Learn Signal"
        self._api = api
        self._device = remote_info["device"]
        self._appliance_id = remote_info["appliance_id"]

    @property
    def device_info(self):
        return get_device_info(self._device)

    async def async_press(self) -> None:
        try:
            await self._api.learn_signal(self._appliance_id)
        except (ClientError, TimeoutError) as err:
            _LOGGER.error("Failed to learn signal for %s: %s", self._appliance_id, err)
            raise HomeAssistantError(
                f"Learn signal failed for {self.name}"
            ) from err


class NatureRemoRefreshDataButton(CoordinatorEntity[NatureRemoCoordinator], ButtonEntity):
    """Button to manually refresh coordinator data."""

    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        device_info: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"nature_remo_refresh_{device_info['device_id']}"
        self._attr_name = "Refresh Data"
        self._device = device_info

    @property
    def device_info(self):
        return get_device_info(self._device)

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
