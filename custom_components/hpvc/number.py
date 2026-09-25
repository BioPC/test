from __future__ import annotations
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    async_add_entities([HPVCNumber(x["key"],x["config"]) for x in hass.data[DOMAIN][DATA_RUNTIME]["helpers"]["number"]])
class HPVCNumber(HPVCEntityMixin, RestoreEntity, NumberEntity):
    def __init__(self,key,cfg):
        self._cfg=cfg; self.entity_id=f"number.{key}"; self._attr_unique_id=f"hpvc_native_{key}"; self._attr_name=cfg.get("name",key); self._attr_icon=cfg.get("icon")
        self._attr_native_min_value=float(cfg.get("min",0)); self._attr_native_max_value=float(cfg.get("max",100)); self._attr_native_step=float(cfg.get("step",1)); self._attr_mode=NumberMode.BOX if cfg.get("mode")=="box" else NumberMode.AUTO
        self._attr_native_unit_of_measurement=cfg.get("unit_of_measurement"); self._attr_native_value=float(cfg.get("initial",self._attr_native_min_value))
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if (last:=await self.async_get_last_state()) is not None:
            try: self._attr_native_value=float(last.state)
            except (ValueError,TypeError): pass
    async def async_set_native_value(self,value): self._attr_native_value=float(value); self.async_write_ha_state()
