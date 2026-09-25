from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, DATA_RUNTIME
from .entity import HPVCEntityMixin

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    cfg=hass.data[DOMAIN][DATA_RUNTIME]["helpers"]["switch"]
    async_add_entities([HPVCSwitch(x["key"],x["config"]) for x in cfg])

class HPVCSwitch(HPVCEntityMixin, RestoreEntity, SwitchEntity):
    def __init__(self,key,cfg):
        self._key=key; self._cfg=cfg; self.entity_id=f"switch.{key}"
        self._attr_unique_id=f"hpvc_native_{key}"; self._attr_name=cfg.get("name",key); self._attr_icon=cfg.get("icon")
        self._attr_is_on=bool(cfg.get("initial",False))
    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if "initial" not in self._cfg:
            if (last:=await self.async_get_last_state()) is not None: self._attr_is_on=last.state=="on"
    async def async_turn_on(self, **kwargs): self._attr_is_on=True; self.async_write_ha_state()
    async def async_turn_off(self, **kwargs): self._attr_is_on=False; self.async_write_ha_state()
