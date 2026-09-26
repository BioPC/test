from __future__ import annotations

import re

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template

from .const import DATA_RUNTIME, DOMAIN
from .entity import HPVCEntityMixin

_TRUE_VALUES = {"true", "on", "yes", "1"}


def _as_bool(value) -> bool:
    return str(value).strip().lower() in _TRUE_VALUES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            HPVCTemplateBinarySensor(x)
            for x in hass.data[DOMAIN][DATA_RUNTIME]["templates"]["binary_sensor"]
        ]
    )


class HPVCTemplateBinarySensor(HPVCEntityMixin, BinarySensorEntity):
    """Reactive HPVC binary sensor backed by a Home Assistant template.

    Keep the state and availability trackers separate.  This avoids relying on
    object identity for TrackTemplateResult.template; Home Assistant compares
    Template instances by equality and the object returned in an update is not
    guaranteed to be the identical Python object supplied at registration.
    """

    _attr_should_poll = False

    def __init__(self, cfg):
        self.cfg = cfg
        uid = cfg.get("unique_id") or re.sub(
            r"[^a-z0-9_]+", "_", cfg.get("name", "").lower()
        )
        self.entity_id = f"binary_sensor.{uid}"
        self._attr_unique_id = uid
        self._attr_name = cfg.get("name")
        self._attr_icon = cfg.get("icon")
        self._attr_is_on = False
        self._attr_available = True
        self._state_src = cfg.get("state", "")
        self._avail_src = cfg.get("availability")
        self._state_t = None
        self._avail_t = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        self._state_t = Template(self._state_src, self.hass)
        state_info = async_track_template_result(
            self.hass,
            [TrackTemplate(self._state_t, None)],
            self._state_changed,
        )
        self.async_on_remove(state_info.async_remove)
        # Home Assistant itself schedules initial template refreshes this way.
        self.hass.loop.call_soon(state_info.async_refresh)

        if self._avail_src:
            self._avail_t = Template(self._avail_src, self.hass)
            avail_info = async_track_template_result(
                self.hass,
                [TrackTemplate(self._avail_t, None)],
                self._availability_changed,
            )
            self.async_on_remove(avail_info.async_remove)
            self.hass.loop.call_soon(avail_info.async_refresh)

    @callback
    def _state_changed(self, event, updates) -> None:
        for update in updates:
            if isinstance(update.result, TemplateError):
                continue
            self._attr_is_on = _as_bool(update.result)
        self.async_write_ha_state()

    @callback
    def _availability_changed(self, event, updates) -> None:
        for update in updates:
            if isinstance(update.result, TemplateError):
                self._attr_available = False
                continue
            self._attr_available = _as_bool(update.result)
        self.async_write_ha_state()
