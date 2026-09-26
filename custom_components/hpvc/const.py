from __future__ import annotations

import json
from pathlib import Path

DOMAIN = "hpvc"
# Compatibility fallback only. Runtime version reporting reads manifest.json so a
# metadata/dashboard/Node-RED-only release can be applied without re-importing Python.
VERSION = "1.5.2"
PANEL_URL = "home-pv-control"
PANEL_TITLE = "Home PV Control"
PANEL_ICON = "mdi:solar-power-variant"
DATA_RUNTIME = "runtime_config"
INSTALLATION_MODE = "HACS native"
DATA_NODE_RED = "nodered_manager"
CONF_NODE_RED_URL = "node_red_url"
CONF_NODE_RED_USERNAME = "node_red_username"
CONF_NODE_RED_PASSWORD = "node_red_password"
CONF_NODE_RED_AUTO_INSTALL = "node_red_auto_install"


def get_package_version() -> str:
    """Read the installed package version from disk without re-importing Python."""
    try:
        data = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))
        value = str(data.get("version") or "").strip()
        return value or VERSION
    except (OSError, ValueError, TypeError):
        return VERSION
