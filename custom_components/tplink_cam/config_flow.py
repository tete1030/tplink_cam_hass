"""Config flow for TPLink Camera integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
import logging

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import selector, config_validation as cv
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaFlowError,
)
from .camera import TPLinkIPCam44AW, AuthenticationError, TPLinkIPCamError

from .const import DOMAIN, CONF_API_URL

LOGGER = logging.getLogger(__name__)

class TPLinkCamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: Mapping[str, Any] = None) -> data_entry_flow.FlowResult:
        errors = {}
        suggest_values = {}
        if user_input is not None:
            user_input[CONF_API_URL] = user_input[CONF_API_URL].strip().rstrip("/")
            suggest_values.update(user_input)

        data_schema = {
            vol.Optional(CONF_NAME, description={"suggested_value": suggest_values.get(CONF_NAME, "")}): str,
            vol.Required(CONF_API_URL, description={"suggested_value": suggest_values.get(CONF_API_URL, "")}): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL)),
            vol.Required(CONF_USERNAME, description={"suggested_value": suggest_values.get(CONF_USERNAME, "")}): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        }

        if user_input is not None:
            try:
                cv.url_no_path(user_input[CONF_API_URL])
            except vol.Invalid:
                errors[CONF_API_URL] = "invalid_url"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(data_schema),
                    errors=errors,
                )

            try:
                device = TPLinkIPCam44AW(user_input[CONF_API_URL], user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                await self.hass.async_add_executor_job(device.login)
                await self.hass.async_add_executor_job(device.update_info)
            except AuthenticationError as e:
                errors["base"] = "auth_fail"
            except TPLinkIPCamError as e:
                errors["base"] = "cannot_connect"
                LOGGER.error("Error: " + str(e))
            else:
                await self.async_set_unique_id(device.info["mac"])
                self._abort_if_unique_id_configured({CONF_API_URL: user_input[CONF_API_URL], CONF_USERNAME: user_input[CONF_USERNAME], CONF_PASSWORD: user_input[CONF_PASSWORD]})
                self._async_abort_entries_match({CONF_API_URL: user_input[CONF_API_URL]})
                return self.async_create_entry(
                    title=f"{user_input.get(CONF_NAME, None) or device.info['device_alias']}",
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )
