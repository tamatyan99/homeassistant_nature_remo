from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NatureRemoCoordinator
from .entity import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities: list[BinarySensorEntity] = []

    for device_id, data in coordinator.motion_sensors.items():
        entities.append(
            NatureRemoMotionBinarySensor(
                coordinator,
                device_id,
                {
                    "device_id": data["device_id"],
                    "name": data["name"],
                    "firmware_version": data["firmware_version"],
                    "serial_number": data.get("serial_number", ""),
                    "mac_address": data.get("mac_address", ""),
                },
            )
        )

    async_add_entities(entities, True)


class NatureRemoMotionBinarySensor(
    CoordinatorEntity[NatureRemoCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "motion"

    def __init__(
        self,
        coordinator: NatureRemoCoordinator,
        device_id: str,
        device: dict,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._device_id = device_id
        self._attr_unique_id = f"nature_remo_{device_id}_motion"
        self._attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def device_info(self) -> DeviceInfo:
        return get_device_info(self._device)

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.motion_sensors

    @property
    def is_on(self):
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion:
            return motion.get("is_active", False)
        return False
