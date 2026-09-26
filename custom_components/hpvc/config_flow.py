from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NODE_RED_AUTO_INSTALL,
    CONF_NODE_RED_PASSWORD,
    CONF_NODE_RED_URL,
    CONF_NODE_RED_USERNAME,
    DOMAIN,
)


def _schema(values=None):
    values = values or {}
    return vol.Schema(
        {
            vol.Optional(CONF_NODE_RED_URL, default=values.get(CONF_NODE_RED_URL, "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_NODE_RED_USERNAME, default=values.get(CONF_NODE_RED_USERNAME, "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_NODE_RED_PASSWORD, default=values.get(CONF_NODE_RED_PASSWORD, "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_NODE_RED_AUTO_INSTALL, default=values.get(CONF_NODE_RED_AUTO_INSTALL, False)): selector.BooleanSelector(),
        }
    )


class HPVCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the HPVC companion integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Home PV Control", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HPVCOptionsFlow(config_entry)


class HPVCOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        values = dict(self.config_entry.data)
        values.update(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_schema(values))
