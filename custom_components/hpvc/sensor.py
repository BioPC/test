from __future__ import annotations
import re
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import TrackTemplate, async_track_template_result
from homeassistant.helpers.template import Template
from homeassistant.exceptions import TemplateError
from .const import DOMAIN, DATA_RUNTIME, INSTALLATION_MODE, get_package_version
from .nodered import get_installer_state
from .update_manager import get_update_state
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
    ents += [HPVCInstalledVersionSensor(),
             HPVCNodeRedVersionSensor(),HPVCNodeRedStatusSensor(),HPVCNodeRedInstallerStatusSensor(entry),HPVCUpdateStatusSensor(entry),HPVCStaticSensor("installation_mode","HPVC Installation Mode",INSTALLATION_MODE,"mdi:home-assistant")]
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
        return "Connected" if s.state==get_package_version() else "Update required"
    @property
    def extra_state_attributes(self):
        s=self.hass.states.get("text.hpvc_nodered_version") if self.hass else None
        return {"required_version":get_package_version(),"detected_version":None if not s else s.state}

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
        temps=[TrackTemplate(self._state_t,None)]
        if self._avail_t: temps.append(TrackTemplate(self._avail_t,None))
        temps += [TrackTemplate(t,None) for t in self._attr_templates.values()]
        info=async_track_template_result(self.hass,temps,self._changed); self.async_on_remove(info.async_remove); self.hass.loop.call_soon(info.async_refresh)
    @callback
    def _changed(self,event,updates):
        for u in updates:
            if isinstance(u.result,TemplateError): continue
            if u.template == self._state_t: self._attr_native_value=_coerce(u.result)
            elif self._avail_t is not None and u.template == self._avail_t: self._attr_available=str(u.result).strip().lower() in ("true","on","yes","1")
            else:
                for k,t in self._attr_templates.items():
                    if u.template == t:self._attrs[k]=_coerce(u.result)
        self.async_write_ha_state()
    @property
    def extra_state_attributes(self): return self._attrs

class HPVCNodeRedInstallerStatusSensor(HPVCStaticSensor):
    def __init__(self, entry):
        self.entry = entry
        super().__init__("nodered_installer_status","HPVC Node-RED Installer Status","Not checked","mdi:source-branch-sync")
    @property
    def native_value(self):
        return get_installer_state(self.hass, self.entry).get("status", "Not checked") if self.hass else "Not checked"
    @property
    def extra_state_attributes(self):
        state = get_installer_state(self.hass, self.entry) if self.hass else {}
        return {
            "detail": state.get("detail"),
            "node_red_url": state.get("url"),
            "last_action": state.get("last_action"),
            "last_backup": state.get("last_backup"),
            "bundled_version": get_package_version(),
        }
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen("hpvc_nodered_installer_updated", self._evt))
    @callback
    def _evt(self, event):
        if event.data.get("entry_id") == self.entry.entry_id:
            self.async_write_ha_state()


class HPVCInstalledVersionSensor(HPVCStaticSensor):
    def __init__(self):
        super().__init__("integration_version","HPVC Integration Version",get_package_version(),"mdi:package-variant-closed")
    @property
    def native_value(self):
        return get_package_version()

class HPVCUpdateStatusSensor(HPVCStaticSensor):
    def __init__(self, entry):
        self.entry = entry
        super().__init__("update_status","HPVC Installed Update Status","Up to date","mdi:update")
    @property
    def native_value(self):
        return get_update_state(self.hass, self.entry).get("status", "Up to date") if self.hass else "Up to date"
    @property
    def extra_state_attributes(self):
        state = get_update_state(self.hass, self.entry) if self.hass else {}
        changes = state.get("changes") or {}
        return {
            "detail": state.get("detail"),
            "loaded_version": state.get("loaded_version"),
            "installed_version": state.get("disk_version"),
            "python_changed": changes.get("python", False),
            "dashboard_changed": changes.get("dashboard", False),
            "nodered_changed": changes.get("nodered", False),
            "runtime_config_changed": changes.get("runtime", False),
            "other_reload_files_changed": changes.get("reload_files", False),
        }
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen("hpvc_update_state_changed", self._evt))
    @callback
    def _evt(self, event):
        if event.data.get("entry_id") == self.entry.entry_id:
            self.async_write_ha_state()
