from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .installation import manual_hpvc_entities

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

        if not getattr(self, "_legacy_migration_acknowledged", False):
            legacy_entities = manual_hpvc_entities(self.hass)
            if legacy_entities:
                self._legacy_entities = legacy_entities
                return await self.async_step_legacy_migration()

        if user_input is not None:
            return self.async_create_entry(title="Home PV Control", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    async def async_step_legacy_migration(self, user_input=None):
        """Confirm that setup may continue into legacy-helper migration mode."""
        errors = {}
        if user_input is not None:
            if user_input.get("confirm_migration"):
                self._legacy_migration_acknowledged = True
                return self.async_show_form(step_id="user", data_schema=_schema())
            errors["base"] = "confirm_required"

        legacy_entities = getattr(self, "_legacy_entities", manual_hpvc_entities(self.hass))
        return self.async_show_form(
            step_id="legacy_migration",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_migration", default=False): selector.BooleanSelector(),
                }
            ),
            errors=errors,
            description_placeholders={
                "count": str(len(legacy_entities)),
            },
        )

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
