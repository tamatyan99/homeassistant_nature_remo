"""Shared air conditioner helpers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import HomeAssistantError

from .const import HA_MODE_TO_REMO_MODE

ECO_TARGET_TEMPERATURE = 26


def build_eco_preset_payload() -> dict[str, Any]:
    """Build API payload to enable eco preset."""
    return {"button": "eco", "temperature": str(ECO_TARGET_TEMPERATURE)}


def build_clear_preset_payload(
    hvac_mode: HVACMode, target_temperature: float | int
) -> dict[str, Any]:
    """Build API payload to clear eco preset while keeping HVAC mode."""
    operation_mode = HA_MODE_TO_REMO_MODE.get(hvac_mode.value)
    if operation_mode is None:
        raise HomeAssistantError(f"Invalid HVAC mode: {hvac_mode}")
    return {
        "operation_mode": operation_mode,
        "temperature": str(target_temperature),
    }


def preset_option_from_settings(settings: dict[str, Any]) -> str:
    """Map Nature Remo AC settings to select preset option."""
    return "eco" if settings.get("button") == "eco" else "none"
