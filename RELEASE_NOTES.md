# Home PV Control v1.5.2

### Final release hardening

- Removed a redundant duplicate Node-RED final verification read after the four managed tabs are written; the same final safety check is retained with one `GET /flows` instead of two.
- Bound HPVC-owned background and delayed tasks to the Home Assistant config-entry lifecycle so unload/reload cancels stale work safely.
- Node-RED Home Assistant server selection no longer guesses from reference counts when multiple HA server configs exist; ambiguous setups are blocked with a clear error.
- Added transaction-style Node-RED flow protection: HPVC pauses control, snapshots all managed tabs, verifies all four writes, and automatically rolls back after a partial failure. HPVC remains disabled if rollback cannot be proven complete.
- Removed stale RC4 frontend/troubleshooting labels and internal RC audit files from the release package.
- Replaced the README Mermaid block with HACS-safe Markdown so the HACS repository page no longer shows raw Mermaid source.


v1.5.2 adds a HACS-native installation and update layer around the existing HPVC architecture. PV control, HBC coordination, safe-disable restoration and the external PV-release handshake from v1.5.1 remain unchanged.

## Highlights

- Added a HACS-ready Home Assistant custom integration under `custom_components/hpvc`.
- HACS/native installations create the HPVC configuration and diagnostic entities directly; they do **not** require `configuration.yaml` package setup or `/config/packages/hpvc_config.yaml`.
- Added the automatic **Home PV Control** sidebar panel using the bundled native dashboard definition.
- Added native equivalents of the manual HPVC helpers/templates and a matching HACS Node-RED flow variant.
- Added HPVC integration, Node-RED version/status, installer-status and installation-mode sensors.
- Added Node-RED Admin API integration for installing and updating the four HPVC-managed tabs.
  - Uses the official per-flow endpoints (`POST /flow`, `PUT /flow/:id`, `DELETE /flow/:id`) instead of replacing the complete Node-RED configuration.
  - HPVC tab ownership/version is identified by persistent machine-readable markers stored in each HPVC tab description, with the old tab labels used only as a migration fallback.
  - Existing HPVC tabs are backed up under `/config/hpvc-data/nodered-backups/` before replacement.
  - Automatic Node-RED writes are **opt-in**. If disabled, HPVC only checks status until the user presses **Install / update Node-RED flow**.
  - Leaving the URL empty discovers the Home Assistant Node-RED add-on. A direct/external Node-RED URL is supported only when that runtime already has a Home Assistant server configuration that HPVC can reuse.
- Added **Check Node-RED connection** and **Install / update Node-RED flow** buttons.
- Manual package + Node-RED + YAML-dashboard installation remains fully supported.

## HACS installation

1. Install HPVC through HACS and restart Home Assistant.
2. Add **Home PV Control** under **Settings → Devices & services**.
3. Leave the Node-RED URL empty for Home Assistant Node-RED add-on discovery, or enter a direct Admin API URL and credentials.
4. Enable **Automatically install/update HPVC Node-RED flow** only if you want HPVC to perform Node-RED writes automatically after startup. It is Off by default.
5. If automatic management is Off, open the HPVC **Settings** tab and press **Install / update Node-RED flow** once.
6. Configure the required grid, price, PV and inverter control entities from the HPVC Settings tab.

No `configuration.yaml` edit is required for HACS/native installation.

### Mixed-install protection

Manual and HACS-native HPVC must not run at the same time. v1.5.2 checks for legacy/manual HPVC helpers in the `input_boolean`, `input_number`, `input_text`, `input_select` and `input_button` domains. When they are detected, the HACS integration enters protection mode: it does not create the native HPVC control entities and does not run the Node-RED installer/updater. The HPVC sidebar remains available as a protected migration surface.

For Manual → HACS-native migration, administrators can use **Delete legacy HPVC helpers & migrate**. The tool deletes only storage-backed legacy `input_*.hpvc_*` helpers through Home Assistant's helper API. For the standard legacy package path `/config/packages/hpvc_config.yaml`, administrators can explicitly choose **Back up & remove legacy HPVC package**; HPVC creates a timestamped backup under `/config/hpvc-data/migration-backups/` and removes only that exact file. Other YAML files are never deleted automatically. Home Assistant must then be restarted so YAML/runtime helpers unload, after which HPVC rescans automatically. It never edits `.storage` files directly, never deletes the manual YAML file automatically, and never removes `hpvc-data/runtime-history.json`.

If a manual HPVC package is loaded after HACS-native HPVC is already running, HPVC turns off `switch.hpvc_enabled` first and reloads the integration into protection mode.

## HACS updates

After a HACS update, HPVC compares fingerprints of the loaded integration with the files installed on disk. When no Python file changed, `sensor.hpvc_update_status` reports **Quick reload available**; the user confirms **Apply installed update**, HPVC applies any bundled Node-RED change and reloads only its own config entry. When Python changed, the status is **Restart required** and the quick reload is blocked. The first HACS installation still requires one Home Assistant restart to load the custom integration Python code.

HPVC never writes the complete Node-RED flow configuration through `POST /flows` in this build.

## Manual installation

The traditional workflow is unchanged:

1. enable Home Assistant packages;
2. copy `home assistant/hpvc_config.yaml` to `/config/packages/hpvc_config.yaml`;
3. import/deploy `node-red/hpvc_flow.json`;
4. add `home assistant/hpvc_dashboard.yaml`;
5. restart/reload and configure HPVC as documented.

## Compatibility

- Home Assistant Core 2025.12+ for HPVC functionality.
- Local custom-integration brand images are cosmetic and require Home Assistant 2026.3+.
- Node-RED with `node-red-contrib-home-assistant-websocket` 0.80.3+.
- Existing v1.5.1 inverter Number entity / Action-service configuration remains compatible.
- Existing HBC, external-release and safe-disable behavior remains compatible.
- Restored HACS dashboard rendering through Home Assistant's native Lovelace root so the v1.5.2 sidebar dashboard follows the same header/tab/section rendering model as the v1.5.1 YAML dashboard.
- Fixed reactive native template tracking: HPVC template sensors and binary sensors now use Home Assistant-compatible template equality/refresh handling, so HBC availability and PV inverter-slot visibility update immediately when their source entities change.
- HBC availability now treats an empty active sub-strategy as valid when the HBC strategy selector and sub-strategy entity are present, preventing false "HBC unavailable" status while HBC is idle.
- Added explicit regression checks for inverter-slot visibility from PV1 through PV10.
- Synchronized installation/configuration/troubleshooting documentation for HACS/native and manual entity domains, mixed-install recovery, HBC availability, and Node-RED installer status. The PV2–PV10 visibility regression remains documented in the release history rather than as an expected troubleshooting case.

- Fixed `hpvc.backup_remove_legacy_package` compatibility with Home Assistant's admin-service API; the migration button now invokes the backend handler correctly.
