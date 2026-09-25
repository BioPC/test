from __future__ import annotations
import re
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
from .const import DOMAIN, VERSION, DATA_RUNTIME, INSTALLATION_MODE
from .entity import HPVCEntityMixin

def _coerce(value):
    if value is None: return None
    s=str(value).strip()
    if re.fullmatch(r"[-+]?\d+",s):
        try:return int(s)
        except ValueError:pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][-+]?\d+)?",s):
        try:return float(s)
        except ValueError:pass
    return s

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    ents=[HPVCTemplateSensor(x) for x in hass.data[DOMAIN][DATA_RUNTIME]["templates"]["sensor"]]
    ents += [HPVCStaticSensor("integration_version","HPVC Integration Version",VERSION,"mdi:package-variant-closed"),
             HPVCNodeRedVersionSensor(),HPVCNodeRedStatusSensor(),HPVCStaticSensor("installation_mode","HPVC Installation Mode",INSTALLATION_MODE,"mdi:home-assistant")]
    async_add_entities(ents)

class HPVCStaticSensor(HPVCEntityMixin, SensorEntity):
    def __init__(self,key,name,value,icon=None): self.entity_id=f"sensor.hpvc_{key}"; self._attr_unique_id=f"hpvc_{key}"; self._attr_name=name; self._attr_native_value=value; self._attr_icon=icon
class HPVCNodeRedVersionSensor(HPVCStaticSensor):
    def __init__(self): super().__init__("nodered_version","HPVC Node-RED Version","Not detected","mdi:source-branch")
    @property
    def native_value(self):
        s=self.hass.states.get("text.hpvc_nodered_version") if self.hass else None
        return s.state if s and s.state not in ("unknown","unavailable","") else "Not detected"
    async def async_added_to_hass(self):
        await super().async_added_to_hass(); self.async_on_remove(self.hass.bus.async_listen("state_changed",self._evt))
    @callback
    def _evt(self,e):
        if e.data.get("entity_id")=="text.hpvc_nodered_version": self.async_write_ha_state()
class HPVCNodeRedStatusSensor(HPVCNodeRedVersionSensor):
    def __init__(self): HPVCStaticSensor.__init__(self,"nodered_status","HPVC Node-RED Status","Not detected","mdi:lan-connect")
    @property
    def native_value(self):
        s=self.hass.states.get("text.hpvc_nodered_version") if self.hass else None
        if not s or s.state in ("unknown","unavailable",""): return "Not detected"
        return "Connected" if s.state==VERSION else "Update required"
    @property
    def extra_state_attributes(self):
        s=self.hass.states.get("text.hpvc_nodered_version") if self.hass else None
        return {"required_version":VERSION,"detected_version":None if not s else s.state}

class HPVCTemplateSensor(HPVCEntityMixin, SensorEntity):
    def __init__(self,cfg):
        self.cfg=cfg; uid=cfg.get("unique_id") or re.sub(r"[^a-z0-9_]+","_",cfg.get("name","").lower())
        self.entity_id=cfg.get("default_entity_id") or f"sensor.{uid}"; self._attr_unique_id=uid; self._attr_name=cfg.get("name"); self._attr_icon=cfg.get("icon")
        self._state_src=cfg.get("state",""); self._avail_src=cfg.get("availability"); self._attr_src=cfg.get("attributes") or {}
        self._state_t=None; self._avail_t=None; self._attr_templates={}; self._attr_native_value=None; self._attrs={}; self._attr_available=True
        self._attr_native_unit_of_measurement=cfg.get("unit_of_measurement")
        dc=cfg.get("device_class"); sc=cfg.get("state_class")
        if dc:
            try:self._attr_device_class=SensorDeviceClass(dc)
            except ValueError:pass
        if sc:
            try:self._attr_state_class=SensorStateClass(sc)
            except ValueError:pass
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._state_t=Template(self._state_src,self.hass); self._avail_t=Template(self._avail_src,self.hass) if self._avail_src else None; self._attr_templates={k:Template(v,self.hass) for k,v in self._attr_src.items()}
        temps=[TrackTemplate(self._state_t,{})]
        if self._avail_t: temps.append(TrackTemplate(self._avail_t,{}))
        temps += [TrackTemplate(t,{}) for t in self._attr_templates.values()]
        info=async_track_template_result(self.hass,temps,self._changed); self.async_on_remove(info.async_remove); info.async_refresh()
    @callback
    def _changed(self,event,updates):
        for u in updates:
            if isinstance(u.result,TemplateError): continue
            if u.template is self._state_t: self._attr_native_value=_coerce(u.result)
            elif self._avail_t is not None and u.template is self._avail_t: self._attr_available=str(u.result).strip().lower() in ("true","on","yes","1")
            else:
                for k,t in self._attr_templates.items():
                    if u.template is t:self._attrs[k]=_coerce(u.result)
        self.async_write_ha_state()
    @property
    def extra_state_attributes(self): return self._attrs
