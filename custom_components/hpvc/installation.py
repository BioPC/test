from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

MANUAL_HELPER_DOMAINS = {
    "input_boolean",
    "input_button",
    "input_number",
    "input_select",
    "input_text",
}
MIXED_NOTIFICATION_ID = "hpvc_mixed_installation"


def manual_hpvc_entities(hass: HomeAssistant) -> list[str]:
    """Return legacy/manual HPVC helper entities that are currently loaded."""
    matches: list[str] = []
    for state in hass.states.async_all():
        entity_id = state.entity_id
        domain, _, object_id = entity_id.partition(".")
        if domain in MANUAL_HELPER_DOMAINS and object_id.startswith("hpvc_"):
            matches.append(entity_id)
    return sorted(matches)


def is_manual_hpvc_entity(entity_id: str | None) -> bool:
    if not entity_id or "." not in entity_id:
        return False
    domain, object_id = entity_id.split(".", 1)
    return domain in MANUAL_HELPER_DOMAINS and object_id.startswith("hpvc_")


def mixed_installation_message(manual_entities: list[str]) -> str:
    sample = ", ".join(manual_entities[:6])
    if len(manual_entities) > 6:
        sample += f", +{len(manual_entities) - 6} more"
    return (
        "Home PV Control detected both the legacy/manual YAML installation and the HACS-native integration. "
        "Running both control stacks at the same time is blocked for safety.\n\n"
        "The HACS-native HPVC entities, dashboard control runtime, and automatic Node-RED installer have NOT been started. "
        "Any already-running HACS-native HPVC control switch is turned off before the integration reloads into protection mode.\n\n"
        "Choose one installation method:\n"
        "• Keep Manual: remove/disable the HACS HPVC integration.\n"
        "• Migrate to HACS-native: remove the HPVC manual package (for example /config/packages/hpvc_config.yaml), "
        "restart Home Assistant, then reload/add Home PV Control.\n\n"
        f"Detected manual HPVC entities: {sample or 'unknown'}"
    )


def notify_mixed_installation(hass: HomeAssistant, manual_entities: list[str]) -> None:
    persistent_notification.async_create(
        hass,
        mixed_installation_message(manual_entities),
        title="Home PV Control: mixed installation blocked",
        notification_id=MIXED_NOTIFICATION_ID,
    )


def clear_mixed_notification(hass: HomeAssistant) -> None:
    persistent_notification.async_dismiss(hass, MIXED_NOTIFICATION_ID)
