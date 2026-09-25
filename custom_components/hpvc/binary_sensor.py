from __future__ import annotations
import re
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([HPVCTemplateBinarySensor(x) for x in hass.data[DOMAIN][DATA_RUNTIME]["templates"]["binary_sensor"]])
class HPVCTemplateBinarySensor(HPVCEntityMixin, BinarySensorEntity):
    def __init__(self,cfg):
        self.cfg=cfg; uid=cfg.get("unique_id") or re.sub(r"[^a-z0-9_]+","_",cfg.get("name","").lower())
        self.entity_id=f"binary_sensor.{uid}"; self._attr_unique_id=uid; self._attr_name=cfg.get("name"); self._attr_icon=cfg.get("icon"); self._attr_is_on=False; self._attr_available=True
        self._state_src=cfg.get("state",""); self._avail_src=cfg.get("availability"); self._state_t=None; self._avail_t=None
    async def async_added_to_hass(self):
        await super().async_added_to_hass(); self._state_t=Template(self._state_src,self.hass); self._avail_t=Template(self._avail_src,self.hass) if self._avail_src else None; temps=[TrackTemplate(self._state_t,{})]+([TrackTemplate(self._avail_t,{})] if self._avail_t else [])
        info=async_track_template_result(self.hass,temps,self._changed); self.async_on_remove(info.async_remove); info.async_refresh()
    @callback
    def _changed(self,event,updates):
        for u in updates:
            if isinstance(u.result,TemplateError): continue
            b=str(u.result).strip().lower() in ("true","on","yes","1")
            if u.template is self._state_t:self._attr_is_on=b
            elif self._avail_t is not None and u.template is self._avail_t:self._attr_available=b
        self.async_write_ha_state()
