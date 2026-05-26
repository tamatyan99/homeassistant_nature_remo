import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import ConfigEntryAuthFailed

from .api import NatureRemoAPI
from .const import (
    CONF_LOCAL_IP,
    DEFAULT_MOTION_THRESHOLD_MINUTES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import NatureRemoCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    "climate",
    "light",
    "sensor",
    "remote",
    "switch",
    "binary_sensor",
    "event",
    "button",
    "select",
]


def _entity_ids_from_service_call(call: ServiceCall) -> list[str]:
    """Resolve entity IDs from service data (includes UI target fields)."""
    entity_ids = call.data.get("entity_id")
    if isinstance(entity_ids, str):
        return [entity_ids]
    if entity_ids:
        return list(entity_ids)
    return []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Nature Remo integration entry")

    hass.data.setdefault(DOMAIN, {})

    local_ip = entry.options.get(CONF_LOCAL_IP, "")
    api = NatureRemoAPI(hass, entry.data["api_key"], local_ip=local_ip if local_ip else None)

    min_update_interval = 10
    update_interval = max(
        min_update_interval,
        int(entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)),
    )
    coordinator = NatureRemoCoordinator(hass, api, update_interval)

    motion_threshold = int(
        entry.options.get("motion_threshold_minutes", DEFAULT_MOTION_THRESHOLD_MINUTES)
    )
    if motion_threshold < 1:
        motion_threshold = 1
    coordinator.motion_threshold_minutes = motion_threshold

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        await entry.async_start_reauth(hass)
        return False

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    async def handle_send_light_mode(call: ServiceCall):
        entity_ids = _entity_ids_from_service_call(call)
        if not entity_ids:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entity_id_required",
            )
        entity_id = entity_ids[0]
        mode = call.data.get("mode", "on")

        target_entry_data = None
        light_entity = None
        for entry_data in hass.data[DOMAIN].values():
            entry_coordinator = entry_data["coordinator"]
            light_entity = entry_coordinator.entity_map.get(entity_id)
            if light_entity is not None:
                target_entry_data = entry_data
                break
        else:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entity_not_found",
                translation_placeholders={"entity_id": entity_id},
            )

        if mode not in light_entity.supported_effects:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unsupported_effect",
                translation_placeholders={"mode": mode},
            )

        entry_api = target_entry_data["api"]
        await entry_api.send_light_command(light_entity.appliance_id, mode)
        light_entity.set_mode(mode)

        return {"status": "success", "appliance_id": light_entity.appliance_id}

    async def handle_learn_signal(call: ServiceCall):
        appliance_id = call.data.get("appliance_id")

        if not appliance_id:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="appliance_id_required",
            )

        target_api = None
        for entry_data in hass.data[DOMAIN].values():
            entry_coordinator = entry_data["coordinator"]
            if (
                appliance_id in entry_coordinator.aircons
                or appliance_id in entry_coordinator.lights
                or appliance_id in entry_coordinator.ir_remotes
            ):
                target_api = entry_data["api"]
                break

        if target_api is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="appliance_not_found",
                translation_placeholders={"appliance_id": appliance_id},
            )

        result = await target_api.learn_signal(appliance_id)
        return result

    if not hass.services.has_service(DOMAIN, "send_light_mode"):
        hass.services.async_register(
            DOMAIN,
            "send_light_mode",
            handle_send_light_mode,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, "learn_signal"):
        hass.services.async_register(
            DOMAIN,
            "learn_signal",
            handle_learn_signal,
            supports_response=SupportsResponse.OPTIONAL,
        )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: NatureRemoCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "send_light_mode")
            hass.services.async_remove(DOMAIN, "learn_signal")
            hass.data.pop(DOMAIN, None)
    return unload_ok
