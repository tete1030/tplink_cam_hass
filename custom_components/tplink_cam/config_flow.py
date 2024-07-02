"""Config flow for TPLink Camera integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv, selector

from .lib.camera import AuthenticationError, TPLinkIPCam44AW, TPLinkIPCamError
from .const import CONF_API_URL, DOMAIN

LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
        vol.Required(CONF_API_URL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
        ),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class TPLinkCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for TPLink Camera integration."""

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle a user step in the config flow."""
        return await self._async_reconfig(user_input)

    async def _async_reconfig(
        self,
        user_input: Mapping[str, Any] | None = None,
        entry: config_entries.ConfigEntry | None = None,
    ) -> data_entry_flow.FlowResult:
        """Handle a user step in the config flow."""
        errors = {}
        suggest_values = {}

        if user_input is not None:
            user_input[CONF_API_URL] = user_input[CONF_API_URL].strip().rstrip("/")
            suggest_values.update(user_input)
        elif entry is not None:
            suggest_values.update(entry.data)

        if user_input is not None:
            try:
                cv.url_no_path(user_input[CONF_API_URL])
            except vol.Invalid:
                errors[CONF_API_URL] = "invalid_url"
                return self.async_show_form(
                    step_id="user" if entry is None else "reconfigure",
                    data_schema=self.add_suggested_values_to_schema(
                        data_schema=CONFIG_SCHEMA, suggested_values=suggest_values
                    ),
                    errors=errors,
                )

            try:
                device = TPLinkIPCam44AW(
                    user_input[CONF_API_URL],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                await self.hass.async_add_executor_job(device.login)
                await self.hass.async_add_executor_job(device.update_info)
            except AuthenticationError:
                errors["base"] = "auth_fail"
            except TPLinkIPCamError as e:
                errors["base"] = "cannot_connect"
                LOGGER.error(e)
            else:
                _found_entry = await self.async_set_unique_id(device.info["mac"])
                if entry is None:
                    self._abort_if_unique_id_configured(
                        {
                            CONF_API_URL: user_input[CONF_API_URL],
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                        },
                        error="already_configured",
                    )
                    self._async_abort_entries_match(
                        {CONF_API_URL: user_input[CONF_API_URL]}
                    )
                else:
                    if (
                        _found_entry is not None
                        and _found_entry.entry_id != entry.entry_id
                    ):
                        return self.async_abort(reason="already_configured")
                    self.hass.config_entries.async_update_entry(
                        entry,
                        title=f"{user_input.get(CONF_NAME, None) or device.info['device_alias']}",
                        data=user_input,
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")
                return self.async_create_entry(
                    title=f"{user_input.get(CONF_NAME, None) or device.info['device_alias']}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user" if entry is None else "reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                data_schema=CONFIG_SCHEMA, suggested_values=suggest_values
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: Mapping[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle a reconfigure step in the config flow."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None, "Entry not found"
        return await self._async_reconfig(
            user_input=user_input,
            entry=entry,
        )
