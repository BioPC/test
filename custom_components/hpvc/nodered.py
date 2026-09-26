from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientError, ClientResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .installation import manual_hpvc_entities

from .const import (
    CONF_NODE_RED_AUTO_INSTALL,
    CONF_NODE_RED_PASSWORD,
    CONF_NODE_RED_URL,
    CONF_NODE_RED_USERNAME,
    DATA_NODE_RED,
    DOMAIN,
    get_package_version,
)

_LOGGER = logging.getLogger(__name__)
_EVENT = "hpvc_nodered_installer_updated"

_ROLES = ("Inputs", "Engine", "Outputs", "Reports")
_TAB_RE = re.compile(r"^HPVC (Inputs|Engine|Outputs|Reports)(?:\s|$)", re.IGNORECASE)
_MARKER_RE = re.compile(r"(?mi)^HPVC_MANAGED=1\s*$")
_ROLE_RE = re.compile(r"(?mi)^HPVC_ROLE=(Inputs|Engine|Outputs|Reports)\s*$")
_VERSION_RE = re.compile(r"(?mi)^HPVC_VERSION=([^\s]+)\s*$")

ADDON_NODE_RED_URL = "http://a0d7b954-nodered:1880"
DEFAULT_NODE_RED_URLS = (ADDON_NODE_RED_URL,)


def _entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    if key in entry.options:
        return entry.options.get(key, default)
    return entry.data.get(key, default)


def _runtime(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    root = hass.data.setdefault(DOMAIN, {}).setdefault(DATA_NODE_RED, {})
    return root.setdefault(
        entry.entry_id,
        {
            "status": "Not checked",
            "detail": None,
            "url": None,
            "last_action": None,
            "last_backup": None,
        },
    )


def _publish(hass: HomeAssistant, entry: ConfigEntry, **changes: Any) -> None:
    state = _runtime(hass, entry)
    state.update(changes)
    hass.bus.async_fire(_EVENT, {"entry_id": entry.entry_id})


def get_installer_state(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    return dict(_runtime(hass, entry))


def _normalise_url(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        value = "http://" + value
    return value.rstrip("/")


def _configured_url(entry: ConfigEntry) -> str | None:
    return _normalise_url(_entry_value(entry, CONF_NODE_RED_URL, ""))


def _candidate_urls(entry: ConfigEntry) -> list[str]:
    configured = _configured_url(entry)
    if configured:
        return [configured]
    return list(DEFAULT_NODE_RED_URLS)


def _is_ha_addon_url(base_url: str) -> bool:
    host = (urlparse(base_url).hostname or "").lower()
    return host == "a0d7b954-nodered"


async def _json_or_text(resp: ClientResponse) -> Any:
    try:
        return await resp.json(content_type=None)
    except Exception:
        return await resp.text()


async def _authenticate(hass: HomeAssistant, entry: ConfigEntry, base_url: str) -> dict[str, str]:
    session = async_get_clientsession(hass)
    async with asyncio.timeout(8):
        async with session.get(f"{base_url}/auth/login") as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Node-RED /auth/login returned HTTP {resp.status}")
            auth = await _json_or_text(resp)

    if not isinstance(auth, dict) or not auth:
        return {}

    if auth.get("type") != "credentials":
        raise RuntimeError(f"Unsupported Node-RED authentication type: {auth.get('type', 'unknown')}")

    username = str(_entry_value(entry, CONF_NODE_RED_USERNAME, "") or "")
    password = str(_entry_value(entry, CONF_NODE_RED_PASSWORD, "") or "")
    if not username or not password:
        raise RuntimeError("Node-RED requires credentials; configure them in HPVC options")

    payload = {
        "client_id": "node-red-admin",
        "grant_type": "password",
        "scope": "*",
        "username": username,
        "password": password,
    }
    async with asyncio.timeout(8):
        async with session.post(f"{base_url}/auth/token", data=payload) as resp:
            data = await _json_or_text(resp)
            if resp.status != 200 or not isinstance(data, dict) or not data.get("access_token"):
                raise RuntimeError(f"Node-RED authentication failed (HTTP {resp.status})")
    return {"Authorization": f"Bearer {data['access_token']}"}


async def _connect(hass: HomeAssistant, entry: ConfigEntry) -> tuple[str, dict[str, str]]:
    errors: list[str] = []
    for base_url in _candidate_urls(entry):
        try:
            headers = await _authenticate(hass, entry, base_url)
            return base_url, headers
        except (TimeoutError, ClientError, OSError, RuntimeError) as exc:
            errors.append(f"{base_url}: {exc}")
    detail = "; ".join(errors[-2:]) if errors else "No Node-RED URL available"
    raise RuntimeError(f"Node-RED Admin API not reachable. {detail}")


async def _get_flows(
    hass: HomeAssistant, base_url: str, auth_headers: dict[str, str]
) -> list[dict[str, Any]]:
    """Read the complete configuration for discovery only; never write it back."""
    session = async_get_clientsession(hass)
    headers = {**auth_headers, "Node-RED-API-Version": "v2"}
    async with asyncio.timeout(12):
        async with session.get(f"{base_url}/flows", headers=headers) as resp:
            data = await _json_or_text(resp)
            if resp.status != 200:
                raise RuntimeError(f"GET /flows returned HTTP {resp.status}")
    if not isinstance(data, dict) or not isinstance(data.get("flows"), list):
        raise RuntimeError("Node-RED returned an unexpected /flows response")
    return data["flows"]


async def _get_single_flow(
    hass: HomeAssistant, base_url: str, auth_headers: dict[str, str], flow_id: str
) -> dict[str, Any]:
    session = async_get_clientsession(hass)
    async with asyncio.timeout(12):
        async with session.get(f"{base_url}/flow/{flow_id}", headers=auth_headers) as resp:
            data = await _json_or_text(resp)
            if resp.status != 200 or not isinstance(data, dict):
                raise RuntimeError(f"GET /flow/{flow_id} returned HTTP {resp.status}")
    return data


async def _put_single_flow(
    hass: HomeAssistant,
    base_url: str,
    auth_headers: dict[str, str],
    flow_id: str,
    flow: dict[str, Any],
) -> None:
    session = async_get_clientsession(hass)
    headers = {**auth_headers, "Content-Type": "application/json"}
    async with asyncio.timeout(20):
        async with session.put(f"{base_url}/flow/{flow_id}", headers=headers, json=flow) as resp:
            body = await _json_or_text(resp)
            if resp.status not in (200, 204):
                raise RuntimeError(f"PUT /flow/{flow_id} returned HTTP {resp.status}: {body}")


async def _post_single_flow(
    hass: HomeAssistant,
    base_url: str,
    auth_headers: dict[str, str],
    flow: dict[str, Any],
) -> str:
    session = async_get_clientsession(hass)
    headers = {**auth_headers, "Content-Type": "application/json"}
    async with asyncio.timeout(20):
        async with session.post(f"{base_url}/flow", headers=headers, json=flow) as resp:
            body = await _json_or_text(resp)
            if resp.status not in (200, 204):
                raise RuntimeError(f"POST /flow returned HTTP {resp.status}: {body}")
    if isinstance(body, dict) and body.get("id"):
        return str(body["id"])
    # Some runtimes return 204. Re-discovery after install verifies the result.
    return ""


async def _delete_single_flow(
    hass: HomeAssistant, base_url: str, auth_headers: dict[str, str], flow_id: str
) -> None:
    session = async_get_clientsession(hass)
    async with asyncio.timeout(12):
        async with session.delete(f"{base_url}/flow/{flow_id}", headers=auth_headers) as resp:
            body = await _json_or_text(resp)
            if resp.status not in (200, 204, 404):
                raise RuntimeError(f"DELETE /flow/{flow_id} returned HTTP {resp.status}: {body}")


def _load_bundled_flow() -> list[dict[str, Any]]:
    path = Path(__file__).parent / "frontend" / "hpvc_flow.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("Bundled hpvc_flow.json is not a Node-RED flow array")
    return data


def _tab_marker_role(tab: dict[str, Any]) -> str | None:
    info = str(tab.get("info", ""))
    if not _MARKER_RE.search(info):
        return None
    match = _ROLE_RE.search(info)
    return match.group(1).title() if match else None


def _legacy_tab_role(tab: dict[str, Any]) -> str | None:
    match = _TAB_RE.match(str(tab.get("label", "")))
    return match.group(1).title() if match else None


def _managed_tabs(flows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    tabs = [x for x in flows if x.get("type") == "tab" and x.get("id")]
    marked: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for tab in tabs:
        role = _tab_marker_role(tab)
        if not role:
            continue
        if role in marked:
            extras.append(tab)
        else:
            marked[role] = tab

    # Migration fallback: accept human labels only when the full legacy four-tab set exists.
    legacy_candidates: dict[str, list[dict[str, Any]]] = {role: [] for role in _ROLES}
    for tab in tabs:
        role = _legacy_tab_role(tab)
        if role:
            legacy_candidates.setdefault(role, []).append(tab)
    if all(legacy_candidates.get(role) for role in _ROLES):
        for role in _ROLES:
            if role not in marked:
                marked[role] = legacy_candidates[role][0]
            extras.extend(x for x in legacy_candidates[role][1:] if x not in extras)

    return marked, extras


def _installed_version(flows: list[dict[str, Any]]) -> str | None:
    roles, _extras = _managed_tabs(flows)
    if any(role not in roles for role in _ROLES):
        return None
    versions: set[str] = set()
    for role in _ROLES:
        tab = roles[role]
        info = str(tab.get("info", ""))
        marker = _VERSION_RE.search(info)
        if marker:
            versions.add(marker.group(1))
            continue
        label_match = re.search(r"\bv(\d+\.\d+\.\d+(?:[-._a-zA-Z0-9]*)?)\b", str(tab.get("label", "")))
        if label_match:
            versions.add(label_match.group(1))
    return versions.pop() if len(versions) == 1 else "unknown"


def _replace_exact(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {k: _replace_exact(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_exact(v, old, new) for v in value]
    if value == old:
        return new
    return value


def _select_existing_ha_server(
    flows: list[dict[str, Any]], base_url: str
) -> dict[str, Any] | None:
    """Select a Home Assistant server config without guessing between multiple HA instances."""
    servers = [
        x for x in flows if x.get("type") == "server" and x.get("id")
    ]
    if not servers:
        return None

    if _is_ha_addon_url(base_url):
        addon_servers = [x for x in servers if x.get("addon") is True]
        if len(addon_servers) == 1:
            return addon_servers[0]
        if len(addon_servers) > 1:
            raise RuntimeError(
                "Multiple Node-RED Home Assistant add-on server configurations were found. "
                "Keep one add-on server configuration or configure Node-RED explicitly before retrying."
            )
        if len(servers) == 1:
            return servers[0]
        raise RuntimeError(
            "Multiple Home Assistant server configurations were found in Node-RED and none "
            "is uniquely marked as the add-on server. HPVC will not guess which HA instance to use."
        )

    if len(servers) == 1:
        return servers[0]
    raise RuntimeError(
        "Multiple Home Assistant server configurations were found in external Node-RED. "
        "HPVC will not guess which HA instance to use; leave only the intended server "
        "configuration available or use the Home Assistant Node-RED add-on."
    )


def _prepare_bundled_for_runtime(
    current: list[dict[str, Any]], bundled: list[dict[str, Any]], base_url: str
) -> list[dict[str, Any]]:
    bundled = deepcopy(bundled)

    bundled_server = next((x for x in bundled if x.get("type") == "server" and x.get("id")), None)
    existing_server = _select_existing_ha_server(current, base_url)
    if bundled_server and existing_server:
        old_id = str(bundled_server["id"])
        new_id = str(existing_server["id"])
        bundled = [_replace_exact(x, old_id, new_id) for x in bundled if x is not bundled_server]
    elif bundled_server and not _is_ha_addon_url(base_url):
        raise RuntimeError(
            "External/direct Node-RED requires an existing Home Assistant server configuration. "
            "Configure node-red-contrib-home-assistant-websocket in Node-RED first, then retry."
        )

    bundled_global = next((x for x in bundled if x.get("type") == "global-config" and x.get("id")), None)
    existing_global = next((x for x in current if x.get("type") == "global-config" and x.get("id")), None)
    if bundled_global and existing_global:
        old_id = str(bundled_global["id"])
        new_id = str(existing_global["id"])
        bundled = [_replace_exact(x, old_id, new_id) for x in bundled if x is not bundled_global]

    return bundled


def _flow_templates(bundled: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    tabs: dict[str, dict[str, Any]] = {}
    tab_ids: dict[str, str] = {}
    for item in bundled:
        if item.get("type") != "tab" or not item.get("id"):
            continue
        role = _tab_marker_role(item) or _legacy_tab_role(item)
        if role in _ROLES:
            tabs[role] = deepcopy(item)
            tab_ids[role] = str(item["id"])

    if any(role not in tabs for role in _ROLES):
        raise RuntimeError("Bundled HPVC flow does not contain all four managed tabs")

    config_nodes = [
        deepcopy(x)
        for x in bundled
        if x.get("type") not in ("tab", "group") and x.get("z") in (None, "") and not ("x" in x or "y" in x)
    ]
    config_ids = {str(x.get("id")) for x in config_nodes if x.get("id")}

    templates: dict[str, dict[str, Any]] = {}
    for role in _ROLES:
        tab = tabs[role]
        tab_id = tab_ids[role]
        nodes = [deepcopy(x) for x in bundled if str(x.get("z", "")) == tab_id]
        flow_obj = {k: deepcopy(v) for k, v in tab.items() if k != "type"}
        flow_obj["nodes"] = nodes
        # Config nodes are globally reusable. Create them only with the first HPVC tab.
        flow_obj["configs"] = deepcopy(config_nodes) if role == "Inputs" else []
        templates[role] = flow_obj

    # Sanity: config nodes must not accidentally be included as ordinary nodes.
    for flow_obj in templates.values():
        if any(str(n.get("id")) in config_ids for n in flow_obj["nodes"] if n.get("id")):
            raise RuntimeError("Bundled HPVC config node was incorrectly attached as a normal flow node")

    return templates, config_nodes


def _mapped_flow(template: dict[str, Any], target_id: str | None) -> dict[str, Any]:
    result = deepcopy(template)
    source_id = str(result.get("id", ""))
    if target_id:
        result = _replace_exact(result, source_id, target_id)
        result["id"] = target_id
    return result


def _guard_id_collisions(
    current: list[dict[str, Any]], bundled: list[dict[str, Any]], managed_tabs: dict[str, dict[str, Any]]
) -> None:
    managed_tab_ids = {str(x["id"]) for x in managed_tabs.values() if x.get("id")}
    managed_ids = {
        str(x.get("id"))
        for x in current
        if x.get("id") and (str(x.get("id")) in managed_tab_ids or str(x.get("z", "")) in managed_tab_ids)
    }
    current_unmanaged_ids = {
        str(x.get("id"))
        for x in current
        if x.get("id") and str(x.get("id")) not in managed_ids
    }

    collisions = sorted(
        {
            str(x.get("id"))
            for x in bundled
            if x.get("id")
            and x.get("type") != "tab"
            and str(x.get("id")) in current_unmanaged_ids
        }
    )
    if collisions:
        raise RuntimeError("Node-RED ID collision with a non-HPVC node: " + ", ".join(collisions[:5]))


async def _write_backup(hass: HomeAssistant, payload: dict[str, Any]) -> str | None:
    flows = payload.get("flows") if isinstance(payload, dict) else None
    if not flows:
        return None
    folder = Path(hass.config.path("hpvc-data", "nodered-backups"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"hpvc-flow-backup-{stamp}.json"

    def _write() -> None:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    await hass.async_add_executor_job(_write)
    return str(path)


async def _snapshot_managed_flows(
    hass: HomeAssistant,
    base_url: str,
    auth: dict[str, str],
    managed_tabs: dict[str, dict[str, Any]],
    extras: list[dict[str, Any]],
) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """Capture every existing HPVC flow before mutation and persist the same snapshot."""
    ids: list[str] = []
    for tab in [*managed_tabs.values(), *extras]:
        tab_id = str(tab.get("id", ""))
        if tab_id and tab_id not in ids:
            ids.append(tab_id)

    snapshots: dict[str, dict[str, Any]] = {}
    for flow_id in ids:
        snapshots[flow_id] = await _get_single_flow(
            hass, base_url, auth, flow_id
        )

    backup = await _write_backup(
        hass,
        {
            "hpvc_backup_format": 3,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "flows": list(snapshots.values()),
        },
    )
    return backup, snapshots


async def _rollback_managed_flows(
    hass: HomeAssistant,
    base_url: str,
    auth: dict[str, str],
    snapshots: dict[str, dict[str, Any]],
) -> list[str]:
    """Best-effort transaction rollback for a partially failed HPVC flow update."""
    errors: list[str] = []
    original_ids = set(snapshots)

    # Rediscover after failure so even a POST that succeeded but timed out can be undone.
    try:
        current = await _get_flows(hass, base_url, auth)
        managed_now, extras_now = _managed_tabs(current)
        current_hpvc_ids = {
            str(tab.get("id"))
            for tab in [*managed_now.values(), *extras_now]
            if tab.get("id")
        }
        for flow_id in sorted(current_hpvc_ids - original_ids):
            try:
                await _delete_single_flow(hass, base_url, auth, flow_id)
            except Exception as exc:
                errors.append(f"delete new {flow_id}: {exc}")
    except Exception as exc:
        errors.append(f"rediscover partial update: {exc}")

    # Restore all original managed HPVC tabs by their original ids.
    for flow_id, snapshot in snapshots.items():
        try:
            await _put_single_flow(hass, base_url, auth, flow_id, snapshot)
        except Exception as exc:
            errors.append(f"restore {flow_id}: {exc}")

    return errors


async def _set_native_control_enabled(
    hass: HomeAssistant, enabled: bool
) -> None:
    """Pause/resume native HPVC control around a Node-RED transaction."""
    if hass.states.get("switch.hpvc_enabled") is None:
        return
    await hass.services.async_call(
        "switch",
        "turn_on" if enabled else "turn_off",
        {"entity_id": "switch.hpvc_enabled"},
        blocking=True,
    )


async def async_check_nodered(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    manual_entities = manual_hpvc_entities(hass)
    if manual_entities:
        detail = "Mixed installation detected; Node-RED management is blocked while manual HPVC helpers are loaded"
        _publish(hass, entry, status="Blocked: mixed installation", detail=detail, last_action="check")
        return get_installer_state(hass, entry)
    _publish(hass, entry, status="Checking", detail=None, last_action="check")
    try:
        base_url, auth = await _connect(hass, entry)
        flows = await _get_flows(hass, base_url, auth)
        detected = _installed_version(flows)
        if detected == get_package_version():
            status = "Up to date"
            detail = f"HPVC Node-RED flow v{get_package_version()} detected"
        elif detected:
            status = "Update required"
            detail = f"Detected HPVC Node-RED flow v{detected}; bundled version is v{get_package_version()}"
        else:
            status = "Not installed"
            detail = "No complete HPVC Node-RED flow detected"
        _publish(hass, entry, status=status, detail=detail, url=base_url, last_action="check")
    except Exception as exc:  # setup must remain available even if Node-RED is offline
        _LOGGER.warning("HPVC Node-RED check failed: %s", exc)
        _publish(hass, entry, status="Connection failed", detail=str(exc), last_action="check")
    return get_installer_state(hass, entry)


async def async_install_update_nodered(
    hass: HomeAssistant, entry: ConfigEntry, *, force: bool = False
) -> dict[str, Any]:
    manual_entities = manual_hpvc_entities(hass)
    if manual_entities:
        detail = (
            "Mixed installation detected; Node-RED install/update is blocked "
            "while manual HPVC helpers are loaded"
        )
        _publish(
            hass,
            entry,
            status="Blocked: mixed installation",
            detail=detail,
            last_action="install/update",
        )
        return get_installer_state(hass, entry)

    _publish(
        hass, entry, status="Installing", detail=None, last_action="install/update"
    )

    base_url = ""
    auth: dict[str, str] = {}
    snapshots: dict[str, dict[str, Any]] = {}
    backup: str | None = None
    control_was_enabled = hass.states.is_state("switch.hpvc_enabled", "on")
    mutation_started = False

    try:
        base_url, auth = await _connect(hass, entry)
        current = await _get_flows(hass, base_url, auth)
        detected = _installed_version(current)
        if detected == get_package_version() and not force:
            _publish(
                hass,
                entry,
                status="Up to date",
                detail=f"HPVC Node-RED flow v{get_package_version()} is already installed",
                url=base_url,
                last_action="install/update",
            )
            return get_installer_state(hass, entry)

        managed_tabs, extras = _managed_tabs(current)
        if extras:
            extra_labels = ", ".join(
                str(x.get("label") or x.get("id") or "unknown") for x in extras[:4]
            )
            raise RuntimeError(
                "Duplicate/obsolete HPVC Node-RED tabs were detected. "
                "For safety HPVC will not delete flow tabs automatically. "
                f"Remove the duplicate HPVC tabs in Node-RED first: {extra_labels}"
            )

        bundled = _prepare_bundled_for_runtime(
            current, _load_bundled_flow(), base_url
        )
        _guard_id_collisions(current, bundled, managed_tabs)
        templates, _configs = _flow_templates(bundled)

        backup, snapshots = await _snapshot_managed_flows(
            hass, base_url, auth, managed_tabs, extras
        )

        await _set_native_control_enabled(hass, False)
        mutation_started = True

        for role in _ROLES:
            existing = managed_tabs.get(role)
            if existing:
                target_id = str(existing["id"])
                flow_obj = _mapped_flow(templates[role], target_id)
                await _put_single_flow(
                    hass, base_url, auth, target_id, flow_obj
                )
            else:
                flow_obj = _mapped_flow(templates[role], None)
                await _post_single_flow(hass, base_url, auth, flow_obj)

        # One final read confirms the active configuration after all four writes.
        verified = await _get_flows(hass, base_url, auth)
        installed = _installed_version(verified)
        if installed != get_package_version():
            raise RuntimeError(
                f"HPVC v{get_package_version()} failed final verification "
                f"(detected: {installed or 'none'})"
            )

        if control_was_enabled:
            await _set_native_control_enabled(hass, True)

        action = "Updated" if detected else "Installed"
        detail = (
            f"HPVC Node-RED flow v{get_package_version()} {action.lower()} successfully using "
            "transaction-protected per-flow Admin API operations"
        )
        if backup:
            detail += "; previous HPVC flow backed up"
        _publish(
            hass,
            entry,
            status=action,
            detail=detail,
            url=base_url,
            last_action="install/update",
            last_backup=backup,
        )

    except Exception as exc:
        rollback_errors: list[str] = []
        if mutation_started and base_url:
            _LOGGER.error(
                "HPVC Node-RED install/update failed; attempting rollback: %s", exc
            )
            rollback_errors = await _rollback_managed_flows(
                hass,
                base_url,
                auth,
                snapshots,
            )

        if mutation_started and not rollback_errors and control_was_enabled:
            try:
                await _set_native_control_enabled(hass, True)
            except Exception as resume_exc:
                rollback_errors.append(f"resume HPVC control: {resume_exc}")

        if rollback_errors:
            try:
                await _set_native_control_enabled(hass, False)
            except Exception:
                pass
            detail = (
                f"{exc}. Automatic rollback was incomplete; HPVC control remains disabled. "
                f"Rollback errors: {'; '.join(rollback_errors[:4])}"
            )
            status = "Rollback failed"
        elif mutation_started:
            detail = f"{exc}. Previous HPVC Node-RED flow was restored automatically."
            status = "Install failed - rolled back"
        else:
            detail = str(exc)
            status = "Install failed"

        _LOGGER.error("HPVC Node-RED install/update failed: %s", detail)
        _publish(
            hass,
            entry,
            status=status,
            detail=detail,
            url=base_url or None,
            last_action="install/update",
            last_backup=backup,
        )

    return get_installer_state(hass, entry)


async def async_auto_install_if_enabled(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if not bool(_entry_value(entry, CONF_NODE_RED_AUTO_INSTALL, False)):
        await async_check_nodered(hass, entry)
        return
    # Automatic writes are explicit opt-in in the HPVC setup/options flow.
    # Give Home Assistant entities and the Node-RED add-on time to become available after restart.
    await asyncio.sleep(8)
    await async_install_update_nodered(hass, entry)
