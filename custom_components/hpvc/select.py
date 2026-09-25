from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([HPVCSelect(x["key"],x["config"]) for x in hass.data[DOMAIN][DATA_RUNTIME]["helpers"]["select"]])
class HPVCSelect(HPVCEntityMixin, RestoreEntity, SelectEntity):
    def __init__(self,key,cfg):
        self._cfg=cfg; self.entity_id=f"select.{key}"; self._attr_unique_id=f"hpvc_native_{key}"; self._attr_name=cfg.get("name",key); self._attr_icon=cfg.get("icon")
        self._attr_options=[str(x) for x in cfg.get("options",[])]; self._attr_current_option=self._attr_options[0] if self._attr_options else None
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last:=await self.async_get_last_state()) is not None and last.state in self._attr_options: self._attr_current_option=last.state
    async def async_select_option(self,option):
        if option not in self._attr_options: raise ValueError(f"Invalid option: {option}")
        self._attr_current_option=option; self.async_write_ha_state()
