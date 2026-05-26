"""Tests for shared air conditioner helpers."""

import pytest
from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import HomeAssistantError

from custom_components.nature_remo.ac_helpers import (
    build_clear_preset_payload,
    build_eco_preset_payload,
    preset_option_from_settings,
)


def test_build_eco_preset_payload():
    assert build_eco_preset_payload() == {"button": "eco", "temperature": "26"}


def test_build_clear_preset_payload():
    payload = build_clear_preset_payload(HVACMode.COOL, 24)
    assert payload == {"operation_mode": "cool", "temperature": "24"}


def test_build_clear_preset_payload_invalid_mode():
    with pytest.raises(HomeAssistantError, match="Invalid HVAC mode"):
        build_clear_preset_payload(HVACMode.OFF, 24)


def test_preset_option_from_settings():
    assert preset_option_from_settings({"button": "eco"}) == "eco"
    assert preset_option_from_settings({"button": "power-off"}) == "none"
