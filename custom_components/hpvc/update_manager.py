from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, get_package_version

_LOGGER = logging.getLogger(__name__)
_EVENT = "hpvc_update_state_changed"
_NOTIFICATION_ID = "hpvc_installed_update"
_CHECK_INTERVAL = 30


def _base_dir() -> Path:
    return Path(__file__).parent


def _hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(_base_dir()))):
        if not path.is_file():
            continue
        rel = str(path.relative_to(_base_dir())).replace("\\", "/")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _all_files() -> list[Path]:
    return [
        p
        for p in _base_dir().rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    ]


def disk_fingerprints() -> dict[str, str]:
    """Return stable fingerprints for reload/restart classification."""
    base = _base_dir()
    all_files = _all_files()
    python_files = [p for p in all_files if p.suffix == ".py"]
    nodered_files = [base / "frontend" / "hpvc_flow.json"]
    runtime_files = [base / "runtime_config.json"]
    dashboard_files = [
        base / "frontend" / "dashboard.json",
        base / "frontend" / "hpvc_dashboard.yaml",
        base / "frontend" / "hpvc-panel.js",
    ]

    classified = set(p.resolve() for p in python_files + nodered_files + runtime_files + dashboard_files if p.exists())
    reload_files = [p for p in all_files if p.resolve() not in classified]

    return {
        "python": _hash_files(python_files),
        "nodered": _hash_files([p for p in nodered_files if p.exists()]),
        "runtime": _hash_files([p for p in runtime_files if p.exists()]),
        "dashboard": _hash_files([p for p in dashboard_files if p.exists()]),
        "reload_files": _hash_files(reload_files),
    }


def _runtime(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    domain = hass.data.setdefault(DOMAIN, {})
    entry_state = domain.setdefault(entry.entry_id, {})
    return entry_state.setdefault(
        "update_manager",
        {
            "status": "Up to date",
            "detail": "No installed update detected",
            "loaded_version": get_package_version(),
            "disk_version": get_package_version(),
            "loaded_fingerprints": disk_fingerprints(),
            "changes": {},
            "candidate": None,
            "candidate_count": 0,
        },
    )


def get_update_state(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    return dict(_runtime(hass, entry))


def _publish(hass: HomeAssistant, entry: ConfigEntry, **changes: Any) -> None:
    state = _runtime(hass, entry)
    state.update(changes)
    hass.bus.async_fire(_EVENT, {"entry_id": entry.entry_id})


async def _notify(hass: HomeAssistant, title: str, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": title,
            "message": message,
            "notification_id": _NOTIFICATION_ID,
        },
        blocking=False,
    )


async def _dismiss_notification(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "dismiss",
        {"notification_id": _NOTIFICATION_ID},
        blocking=False,
    )


def _classify(state: dict[str, Any]) -> dict[str, bool]:
    loaded = state.get("loaded_fingerprints") or {}
    current = disk_fingerprints()
    return {key: loaded.get(key) != current.get(key) for key in current}


async def async_check_installed_update(
    hass: HomeAssistant, entry: ConfigEntry, *, notify: bool = True
) -> dict[str, Any]:
    state = _runtime(hass, entry)
    current = disk_fingerprints()
    changes = _classify(state)
    disk_version = get_package_version()

    if not any(changes.values()):
        _publish(
            hass,
            entry,
            status="Up to date",
            detail="No installed update detected",
            disk_version=disk_version,
            changes=changes,
        )
        return get_update_state(hass, entry)

    python_changed = changes.get("python", False)
    if python_changed:
        status = "Restart required"
        detail = (
            f"HPVC {disk_version} is installed on disk and contains Python changes. "
            "Restart Home Assistant to load the new Python code."
        )
        if notify:
            await _notify(
                hass,
                "HPVC update requires a Home Assistant restart",
                detail,
            )
    else:
        status = "Quick reload available"
        changed_names = [name for name, changed in changes.items() if changed]
        detail = (
            f"HPVC {disk_version} is installed on disk with no Python changes. "
            f"Changed components: {', '.join(changed_names)}. "
            "Press 'Apply installed update' to apply it and reload only Home PV Control."
        )
        if notify:
            await _notify(
                hass,
                "HPVC update ready for quick reload",
                detail,
            )

    _publish(
        hass,
        entry,
        status=status,
        detail=detail,
        disk_version=disk_version,
        changes=changes,
    )
    return get_update_state(hass, entry)


async def async_apply_installed_update(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Apply an on-disk update after explicit user confirmation."""
    state = await async_check_installed_update(hass, entry, notify=False)
    changes = state.get("changes") or {}

    if not any(changes.values()):
        return state

    if changes.get("python"):
        detail = (
            f"HPVC {state.get('disk_version') or get_package_version()} contains Python changes. "
            "A Home Assistant restart is required; a config-entry reload was not attempted."
        )
        _publish(hass, entry, status="Restart required", detail=detail)
        await _notify(hass, "HPVC restart required", detail)
        return get_update_state(hass, entry)

    _publish(
        hass,
        entry,
        status="Applying update",
        detail="Applying installed HPVC update before quick reload",
    )

    if changes.get("nodered"):
        # Explicit Apply is the user's confirmation, so update the managed flow even
        # when automatic Node-RED writes are disabled.
        from .nodered import async_install_update_nodered

        nr_state = await async_install_update_nodered(hass, entry, force=True)
        nr_status = str(nr_state.get("status") or "")
        if nr_status.startswith("Install failed") or nr_status in {
            "Rollback failed",
            "Connection failed",
            "Blocked: mixed installation",
        }:
            detail = (
                "The installed HPVC files were not reloaded because the Node-RED "
                f"update did not complete safely: {nr_state.get('detail') or nr_status}"
            )
            _publish(hass, entry, status="Apply failed", detail=detail)
            await _notify(hass, "HPVC update was not applied", detail)
            return get_update_state(hass, entry)

    await _dismiss_notification(hass)
    _publish(
        hass,
        entry,
        status="Reloading HPVC",
        detail="Reloading only the Home PV Control config entry; Home Assistant stays online",
    )
    await hass.config_entries.async_reload(entry.entry_id)
    return get_update_state(hass, entry)


async def async_update_monitor(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Watch the installed files for a HACS update without restarting Home Assistant."""
    state = _runtime(hass, entry)
    while True:
        await asyncio.sleep(_CHECK_INTERVAL)
        try:
            current = disk_fingerprints()
            loaded = state.get("loaded_fingerprints") or {}
            if current == loaded:
                state["candidate"] = None
                state["candidate_count"] = 0
                continue

            # Require the same changed fingerprint twice so we do not react while
            # HACS is still replacing files on disk.
            if state.get("candidate") == current:
                state["candidate_count"] = int(state.get("candidate_count", 0)) + 1
            else:
                state["candidate"] = current
                state["candidate_count"] = 1

            if state["candidate_count"] >= 2:
                await async_check_installed_update(hass, entry, notify=True)
                state["candidate_count"] = 0
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _LOGGER.warning("HPVC installed-update monitor failed: %s", exc)
