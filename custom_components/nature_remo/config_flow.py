from __future__ import annotations

import hashlib
import logging

import voluptuous as vol
from aiohttp import ClientError
from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import NatureRemoAPI
from .const import DOMAIN
from .options_flow import NatureRemoOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

API_SCHEMA = vol.Schema(
    {vol.Optional("name", default="Nature Remo"): str, vol.Required("api_key"): str}
)


class NatureRemoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        self.api_key: str = ""
        self.appliances: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
        if user_input is not None:
            self.api_key = user_input["api_key"]
            self.name = user_input.get("name", "Nature Remo")

            unique_id = hashlib.sha256(self.api_key.encode()).hexdigest()[:32]
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                api = NatureRemoAPI(self.hass, self.api_key)
                devices = await api.get_devices()
                if not isinstance(devices, list):
                    _LOGGER.error(
                        "Unexpected devices response type: %s", type(devices)
                    )
                    raise ValueError("Unexpected devices response type")
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except (ClientError, ValueError):
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=self.name, data={"api_key": self.api_key}
                )

        return self.async_show_form(
            step_id="user", data_schema=API_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            api_key = user_input["api_key"]

            try:
                api = NatureRemoAPI(self.hass, api_key)
                devices = await api.get_devices()
                if not isinstance(devices, list):
                    raise ValueError("Unexpected devices response type")
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except (ClientError, ValueError):
                errors["base"] = "invalid_auth"
            else:
                self.hass.config_entries.async_update_entry(
                    reauth_entry, data={**reauth_entry.data, "api_key": api_key}
                )
                await self.hass.config_entries.async_reload(reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({vol.Required("api_key"): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NatureRemoOptionsFlowHandler()