from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from aiohttp import web
from homeassistant.components import frontend, webhook
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .button import async_apply_defaults
from .const import DATA_RUNTIME, DOMAIN, PANEL_ICON, PANEL_TITLE, PANEL_URL, get_package_version
from .installation import (
    clear_mixed_notification,
    is_manual_hpvc_entity,
    manual_hpvc_entities,
    notify_mixed_installation,
)
from .nodered import async_auto_install_if_enabled
from .update_manager import async_update_monitor, disk_fingerprints

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["switch", "text", "select", "number", "button", "sensor", "binary_sensor"]
WEBHOOK_ID = "hpvc_report_viewed_141"


async def _call(hass, domain, service, entity_id, **data):
    await hass.services.async_call(
        domain, service, {"entity_id": entity_id, **data}, blocking=True
    )


async def _set_switch(hass, entity_id, on):
    await _call(hass, "switch", "turn_on" if on else "turn_off", entity_id)


async def _first_install(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await asyncio.sleep(10)
    if hass.states.is_state("switch.hpvc_defaults_applied", "off"):
        await _set_switch(hass, "switch.hpvc_notifications", True)
        await _set_switch(hass, "switch.hpvc_negative_price_hbc_charge", True)
        await _set_switch(hass, "switch.hpvc_enabled", False)
        await _set_switch(hass, "switch.hpvc_control_hbc_strategy", False)
        await _set_switch(hass, "switch.hpvc_onboarding_complete", False)
        await _set_switch(hass, "switch.hpvc_auto_resume_pending", False)
        await async_apply_defaults(hass)
        await _set_switch(
            hass, "switch.hpvc_negative_price_hbc_charge_default_applied", True
        )
        await _set_switch(hass, "switch.hpvc_defaults_applied", True)
    await _evaluate(hass, entry)


async def _evaluate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if not hass.states.is_state("switch.hpvc_defaults_applied", "on"):
        return

    config_ok = hass.states.is_state("binary_sensor.hpvc_configuration_valid", "on")
    inputs_ok = hass.states.is_state("binary_sensor.hpvc_required_inputs_ready", "on")
    onboard = hass.states.is_state("switch.hpvc_onboarding_complete", "on")
    enabled = hass.states.is_state("switch.hpvc_enabled", "on")
    pending = hass.states.is_state("switch.hpvc_auto_resume_pending", "on")

    if config_ok and inputs_ok and not onboard:
        await _set_switch(hass, "switch.hpvc_notifications", True)
        await _set_switch(hass, "switch.hpvc_onboarding_complete", True)
        await _set_switch(hass, "switch.hpvc_auto_resume_pending", False)
        await _set_switch(hass, "switch.hpvc_enabled", True)
        return

    if onboard and enabled and not inputs_ok:
        await _set_switch(hass, "switch.hpvc_auto_resume_pending", True)
        await _set_switch(hass, "switch.hpvc_enabled", False)
        return

    if onboard and pending and config_ok and inputs_ok:

        async def resume() -> None:
            await asyncio.sleep(5)
            if (
                hass.states.is_state("binary_sensor.hpvc_configuration_valid", "on")
                and hass.states.is_state("binary_sensor.hpvc_required_inputs_ready", "on")
                and hass.states.is_state("switch.hpvc_auto_resume_pending", "on")
            ):
                await _set_switch(hass, "switch.hpvc_enabled", True)
                await _set_switch(hass, "switch.hpvc_auto_resume_pending", False)

        entry.async_create_background_task(
            hass, resume(), "hpvc-delayed-auto-resume"
        )


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _ensure_frontend_registered(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Register the HPVC sidebar/frontend, including mixed-install migration mode."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    static_dir = Path(__file__).parent / "frontend"

    if not domain_data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/hpvc_static", str(static_dir), False)]
        )
        domain_data["static_registered"] = True

    if not frontend.async_panel_exists(hass, PANEL_URL):
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            frontend_url_path=PANEL_URL,
            config={
                "_panel_custom": {
                    "name": "hpvc-panel",
                    "embed_iframe": False,
                    "trust_external": False,
                    "entry_id": entry.entry_id,
                    "js_url": f"/hpvc_static/hpvc-panel.js?v={get_package_version()}-{disk_fingerprints()['dashboard'][:10]}",
                }
            },
            require_admin=False,
        )


async def _activate_mixed_protection(
    hass: HomeAssistant, entry: ConfigEntry, manual_entities: list[str]
) -> None:
    """Stop the native control stack and reload into mixed-install protection mode."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    state = domain_data.get(entry.entry_id)
    if isinstance(state, dict) and state.get("mixed_protection_pending"):
        return
    if isinstance(state, dict):
        state["mixed_protection_pending"] = True

    if hass.states.get("switch.hpvc_enabled") is not None:
        try:
            await _set_switch(hass, "switch.hpvc_enabled", False)
        except Exception as exc:
            _LOGGER.warning(
                "Could not disable HPVC before mixed-install reload: %s", exc
            )

    notify_mixed_installation(hass, manual_entities)
    _LOGGER.error(
        "Mixed HPVC installation detected; native control is being blocked: %s",
        ", ".join(manual_entities),
    )
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})
    entry.async_on_unload(entry.add_update_listener(_options_updated))

    # Keep the HPVC sidebar available in mixed-install protection mode so the
    # user can run the explicit legacy-helper migration/cleanup tool.
    await _ensure_frontend_registered(hass, entry)

    manual_entities = manual_hpvc_entities(hass)
    if manual_entities:
        notify_mixed_installation(hass, manual_entities)
        domain_data[entry.entry_id] = {
            "native_runtime": False,
            "mixed_installation": True,
            "manual_entities": manual_entities,
        }
        _LOGGER.error(
            "Mixed HPVC installation blocked: %s", ", ".join(manual_entities)
        )
        return True

    clear_mixed_notification(hass)
    # Reload runtime_config.json on every config-entry setup so a non-Python
    # HACS update can be applied with a quick HPVC reload.
    domain_data[DATA_RUNTIME] = json.loads(
        (Path(__file__).parent / "runtime_config.json").read_text(encoding="utf-8")
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _report_webhook(hass, webhook_id, request):
        await _set_switch(hass, "switch.hpvc_report_ready", False)
        return web.Response(status=200)

    try:
        webhook.async_register(
            hass,
            DOMAIN,
            "HPVC report viewed",
            WEBHOOK_ID,
            _report_webhook,
            local_only=False,
            allowed_methods=["POST"],
        )
    except ValueError:
        pass

    @callback
    def changed(event):
        entity_id = event.data.get("entity_id")
        if entity_id == "switch.hpvc_enabled":
            new_state = event.data.get("new_state")
            if (
                new_state
                and new_state.state == "off"
                and new_state.context.user_id is not None
            ):
                entry.async_create_task(
                    hass,
                    _set_switch(hass, "switch.hpvc_auto_resume_pending", False),
                    "hpvc-clear-auto-resume-pending",
                )
        entry.async_create_task(hass, _evaluate(hass, entry), "hpvc-evaluate-state")

    tracked = [
        "binary_sensor.hpvc_configuration_valid",
        "binary_sensor.hpvc_required_inputs_ready",
        "switch.hpvc_defaults_applied",
        "switch.hpvc_onboarding_complete",
        "switch.hpvc_auto_resume_pending",
        "switch.hpvc_enabled",
    ]
    entry.async_on_unload(async_track_state_change_event(hass, tracked, changed))

    @callback
    def manual_entity_changed(event):
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        if new_state is None or not is_manual_hpvc_entity(entity_id):
            return
        entities = manual_hpvc_entities(hass)
        if entities:
            entry.async_create_background_task(
                hass,
                _activate_mixed_protection(hass, entry, entities),
                "hpvc-activate-mixed-install-protection",
            )

    entry.async_on_unload(hass.bus.async_listen("state_changed", manual_entity_changed))
    loaded_fingerprints = disk_fingerprints()
    domain_data[entry.entry_id] = {
        "native_runtime": True,
        "mixed_installation": False,
        "update_manager": {
            "status": "Up to date",
            "detail": "No installed update detected",
            "loaded_version": get_package_version(),
            "disk_version": get_package_version(),
            "loaded_fingerprints": loaded_fingerprints,
            "changes": {},
            "candidate": None,
            "candidate_count": 0,
        },
    }

    entry.async_create_background_task(
        hass, _first_install(hass, entry), "hpvc-first-install"
    )
    entry.async_create_background_task(
        hass,
        async_auto_install_if_enabled(hass, entry),
        "hpvc-node-red-auto-install-check",
    )
    entry.async_create_background_task(
        hass, async_update_monitor(hass, entry), "hpvc-installed-update-monitor"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_state = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    if isinstance(entry_state, dict) and entry_state.get("mixed_installation"):
        if frontend.async_panel_exists(hass, PANEL_URL):
            frontend.async_remove_panel(hass, PANEL_URL)
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        return True

    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if frontend.async_panel_exists(hass, PANEL_URL):
        frontend.async_remove_panel(hass, PANEL_URL)
    try:
        webhook.async_unregister(hass, WEBHOOK_ID)
    except ValueError:
        pass
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return ok
