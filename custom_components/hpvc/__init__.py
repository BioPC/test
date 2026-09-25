from __future__ import annotations
from pathlib import Path
import json, logging, asyncio
from aiohttp import web
from homeassistant.components import frontend, webhook
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, VERSION, PANEL_URL, PANEL_TITLE, PANEL_ICON, DATA_RUNTIME
from .button import async_apply_defaults

_LOGGER=logging.getLogger(__name__)
PLATFORMS=["switch","text","select","number","button","sensor","binary_sensor"]
WEBHOOK_ID="hpvc_report_viewed_141"

async def _call(hass,domain,service,entity_id,**data):
    await hass.services.async_call(domain,service,{"entity_id":entity_id,**data},blocking=True)
async def _set_switch(hass,e,on): await _call(hass,"switch","turn_on" if on else "turn_off",e)

async def _first_install(hass):
    await asyncio.sleep(10)
    if hass.states.is_state("switch.hpvc_defaults_applied","off"):
        await _set_switch(hass,"switch.hpvc_notifications",True); await _set_switch(hass,"switch.hpvc_negative_price_hbc_charge",True)
        await _set_switch(hass,"switch.hpvc_enabled",False); await _set_switch(hass,"switch.hpvc_control_hbc_strategy",False)
        await _set_switch(hass,"switch.hpvc_onboarding_complete",False); await _set_switch(hass,"switch.hpvc_auto_resume_pending",False)
        await async_apply_defaults(hass)
        await _set_switch(hass,"switch.hpvc_negative_price_hbc_charge_default_applied",True); await _set_switch(hass,"switch.hpvc_defaults_applied",True)
    await _evaluate(hass)

async def _evaluate(hass):
    if not hass.states.is_state("switch.hpvc_defaults_applied","on"): return
    config_ok=hass.states.is_state("binary_sensor.hpvc_configuration_valid","on")
    inputs_ok=hass.states.is_state("binary_sensor.hpvc_required_inputs_ready","on")
    onboard=hass.states.is_state("switch.hpvc_onboarding_complete","on")
    enabled=hass.states.is_state("switch.hpvc_enabled","on")
    pending=hass.states.is_state("switch.hpvc_auto_resume_pending","on")
    if config_ok and inputs_ok and not onboard:
        await _set_switch(hass,"switch.hpvc_notifications",True); await _set_switch(hass,"switch.hpvc_onboarding_complete",True); await _set_switch(hass,"switch.hpvc_auto_resume_pending",False); await _set_switch(hass,"switch.hpvc_enabled",True); return
    if onboard and enabled and not inputs_ok:
        await _set_switch(hass,"switch.hpvc_auto_resume_pending",True); await _set_switch(hass,"switch.hpvc_enabled",False); return
    if onboard and pending and config_ok and inputs_ok:
        async def resume():
            await asyncio.sleep(5)
            if hass.states.is_state("binary_sensor.hpvc_configuration_valid","on") and hass.states.is_state("binary_sensor.hpvc_required_inputs_ready","on") and hass.states.is_state("switch.hpvc_auto_resume_pending","on"):
                await _set_switch(hass,"switch.hpvc_enabled",True); await _set_switch(hass,"switch.hpvc_auto_resume_pending",False)
        hass.async_create_task(resume())

async def async_setup_entry(hass:HomeAssistant, entry:ConfigEntry)->bool:
    domain_data=hass.data.setdefault(DOMAIN,{})
    if DATA_RUNTIME not in domain_data:
        domain_data[DATA_RUNTIME]=json.loads((Path(__file__).parent/"runtime_config.json").read_text(encoding="utf-8"))
    static_dir=Path(__file__).parent/"frontend"
    if not domain_data.get("static_registered"):
        await hass.http.async_register_static_paths([StaticPathConfig("/hpvc_static",str(static_dir),False)]); domain_data["static_registered"]=True
    if not frontend.async_panel_exists(hass,PANEL_URL):
        frontend.async_register_built_in_panel(hass,component_name="custom",sidebar_title=PANEL_TITLE,sidebar_icon=PANEL_ICON,frontend_url_path=PANEL_URL,
            config={"_panel_custom":{"name":"hpvc-panel","embed_iframe":False,"trust_external":False,"js_url":f"/hpvc_static/hpvc-panel.js?v={VERSION}"}},require_admin=False)
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    async def _report_webhook(hass, webhook_id, request):
        await _set_switch(hass,"switch.hpvc_report_ready",False); return web.Response(status=200)
    try: webhook.async_register(hass,DOMAIN,"HPVC report viewed",WEBHOOK_ID,_report_webhook,local_only=False,allowed_methods=["POST"])
    except ValueError: pass
    @callback
    def changed(event):
        eid=event.data.get("entity_id")
        if eid=="switch.hpvc_enabled":
            ns=event.data.get("new_state")
            if ns and ns.state=="off" and ns.context.user_id is not None: hass.async_create_task(_set_switch(hass,"switch.hpvc_auto_resume_pending",False))
        hass.async_create_task(_evaluate(hass))
    tracked=["binary_sensor.hpvc_configuration_valid","binary_sensor.hpvc_required_inputs_ready","switch.hpvc_defaults_applied","switch.hpvc_onboarding_complete","switch.hpvc_auto_resume_pending","switch.hpvc_enabled"]
    entry.async_on_unload(async_track_state_change_event(hass,tracked,changed))
    hass.async_create_task(_first_install(hass))
    domain_data[entry.entry_id]={"native_runtime":True}
    return True

async def async_unload_entry(hass:HomeAssistant, entry:ConfigEntry)->bool:
    ok=await hass.config_entries.async_unload_platforms(entry,PLATFORMS)
    if frontend.async_panel_exists(hass,PANEL_URL): frontend.async_remove_panel(hass,PANEL_URL)
    try:webhook.async_unregister(hass,WEBHOOK_ID)
    except ValueError:pass
    hass.data.get(DOMAIN,{}).pop(entry.entry_id,None)
    return ok
