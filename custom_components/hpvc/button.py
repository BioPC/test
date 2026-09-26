from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin
from .nodered import async_check_nodered, async_install_update_nodered
from .update_manager import async_apply_installed_update, async_check_installed_update

DEFAULTS={
 "number.hpvc_pv_limiting_price":0.0,"number.hpvc_battery_price_hysteresis":0.02,"number.hpvc_export_start_threshold":-150,
 "number.hpvc_export_stop_threshold":0,"number.hpvc_import_restore_threshold":150,"number.hpvc_pv_min_power_for_control":100,
 "number.hpvc_pv_night_restore_power":10,"number.hpvc_cooldown_seconds":30,"number.hpvc_pv_adjust_deadband":25,
}
async def async_apply_defaults(hass):
    for entity_id,value in DEFAULTS.items(): await hass.services.async_call("number","set_value",{"entity_id":entity_id,"value":value},blocking=True)
    await hass.services.async_call("switch","turn_on",{"entity_id":"switch.hpvc_negative_price_hbc_charge"},blocking=True)
    if hass.states.get("button.hpvc_defaults_restored_event"):
        await hass.services.async_call("button","press",{"entity_id":"button.hpvc_defaults_restored_event"},blocking=True)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    ents=[HPVCButton(x["key"],x["config"]) for x in hass.data[DOMAIN][DATA_RUNTIME]["helpers"]["button"]]
    ents.append(HPVCRestoreDefaultsButton())
    ents.append(HPVCNodeRedInstallUpdateButton(entry))
    ents.append(HPVCNodeRedCheckButton(entry))
    ents.append(HPVCApplyInstalledUpdateButton(entry))
    ents.append(HPVCCheckInstalledUpdateButton(entry))
    async_add_entities(ents)
class HPVCButton(HPVCEntityMixin, ButtonEntity):
    def __init__(self,key,cfg): self.entity_id=f"button.{key}"; self._attr_unique_id=f"hpvc_native_{key}"; self._attr_name=cfg.get("name",key); self._attr_icon=cfg.get("icon")
    async def async_press(self): return
class HPVCRestoreDefaultsButton(HPVCEntityMixin, ButtonEntity):
    entity_id="button.hpvc_restore_defaults"; _attr_unique_id="hpvc_native_restore_defaults"; _attr_name="Restore defaults"; _attr_icon="mdi:backup-restore"
    async def async_press(self): await async_apply_defaults(self.hass)

class HPVCNodeRedInstallUpdateButton(HPVCEntityMixin, ButtonEntity):
    entity_id="button.hpvc_install_update_nodered_flow"
    _attr_unique_id="hpvc_native_install_update_nodered_flow"
    _attr_name="Install / update Node-RED flow"
    _attr_icon="mdi:source-branch-sync"
    def __init__(self, entry): self.entry = entry
    async def async_press(self): await async_install_update_nodered(self.hass, self.entry, force=True)

class HPVCNodeRedCheckButton(HPVCEntityMixin, ButtonEntity):
    entity_id="button.hpvc_check_nodered_connection"
    _attr_unique_id="hpvc_native_check_nodered_connection"
    _attr_name="Check Node-RED connection"
    _attr_icon="mdi:lan-check"
    def __init__(self, entry): self.entry = entry
    async def async_press(self): await async_check_nodered(self.hass, self.entry)


class HPVCApplyInstalledUpdateButton(HPVCEntityMixin, ButtonEntity):
    entity_id="button.hpvc_apply_installed_update"
    _attr_unique_id="hpvc_native_apply_installed_update"
    _attr_name="Apply installed update"
    _attr_icon="mdi:update"
    def __init__(self, entry): self.entry = entry
    async def async_press(self): await async_apply_installed_update(self.hass, self.entry)

class HPVCCheckInstalledUpdateButton(HPVCEntityMixin, ButtonEntity):
    entity_id="button.hpvc_check_installed_update"
    _attr_unique_id="hpvc_native_check_installed_update"
    _attr_name="Check installed update"
    _attr_icon="mdi:refresh-circle"
    def __init__(self, entry): self.entry = entry
    async def async_press(self): await async_check_installed_update(self.hass, self.entry, notify=True)
