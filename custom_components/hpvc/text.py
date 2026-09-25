from __future__ import annotations
from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([HPVCText(x["key"],x["config"]) for x in hass.data[DOMAIN][DATA_RUNTIME]["helpers"]["text"]])
class HPVCText(HPVCEntityMixin, RestoreEntity, TextEntity):
    _attr_native_min=0; _attr_mode=TextMode.TEXT
    def __init__(self,key,cfg):
        self._cfg=cfg; self.entity_id=f"text.{key}"; self._attr_unique_id=f"hpvc_native_{key}"; self._attr_name=cfg.get("name",key); self._attr_icon=cfg.get("icon")
        self._attr_native_max=int(cfg.get("max",255)); self._attr_native_value=str(cfg.get("initial", ""))
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last:=await self.async_get_last_state()) is not None and last.state not in ("unknown","unavailable"): self._attr_native_value=last.state
    async def async_set_value(self,value): self._attr_native_value=str(value); self.async_write_ha_state()
