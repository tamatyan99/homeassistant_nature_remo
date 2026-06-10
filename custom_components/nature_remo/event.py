from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import NatureRemoCoordinator
from .const import DOMAIN
from .entity import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    entities = []

    for device_id, data in coordinator.motion_sensors.items():
        entities.append(
            NatureRemoMotionEvent(
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


class NatureRemoMotionEvent(CoordinatorEntity[NatureRemoCoordinator], EventEntity):
    _attr_has_entity_name = True
    _attr_event_types = ["motion_detected"]
    _attr_should_poll = False

    def __init__(self, coordinator, device_id, device):
        super().__init__(coordinator)
        self._device = device
        self._device_id = device_id
        self._attr_name = "Motion Event"
        self._attr_unique_id = f"nature_remo_{device_id}_motion_event"
        self._last_motion = None

    @property
    def device_info(self):
        return get_device_info(self._device)

    @callback
    def _handle_coordinator_update(self) -> None:
        motion = self.coordinator.motion_sensors.get(self._device_id)
        if motion:
            last_motion = motion.get("last_motion")
            if last_motion is not None:
                if self._last_motion is None:
                    # Initialize without firing event on startup
                    self._last_motion = last_motion
                elif last_motion != self._last_motion:
                    self._last_motion = last_motion
                    self._trigger_event(
                        "motion_detected",
                        {
                            "device_id": self._device_id,
                            "last_motion": last_motion.isoformat(),
                        },
                    )
        super()._handle_coordinator_update()
