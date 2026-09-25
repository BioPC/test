# Home PV Control v1.5.2

v1.5.2 adds a HACS-friendly installation and update layer around the existing HPVC architecture. The PV-control, HBC, safe-disable and external-release behavior from v1.5.1 is intentionally kept unchanged.

## Highlights

- HACS-ready Home Assistant custom integration under `custom_components/hpvc`.
- One-click **Open in HACS** link in the README and installation guide.
- Automatic **Home PV Control** sidebar panel for HACS installations using the bundled HPVC dashboard definition.
- Protected native-HACS installation: HACS can install/update its own `/config/packages/hpvc_config.yaml`, while an existing manual package is preserved.
- Matching Home Assistant package, dashboard and Node-RED flow bundled with the integration.
- Node-RED version handshake through `input_text.hpvc_nodered_version`.
- Home Assistant sensors expose the installed integration version, detected Node-RED version, Node-RED update status and package mode.
- The Node-RED step remains deliberately semi-automatic. HACS supplies the matching flow but does not silently replace a user's deployed flow.
- Manual installation remains fully supported as before.

## HACS installation

1. Install HPVC through HACS and restart Home Assistant.
2. Add **Home PV Control** from **Settings → Devices & services**.
3. HPVC registers its sidebar dashboard and installs the package if no manual package exists.
4. If HPVC installed/updated the native HACS configuration, restart Home Assistant once to load the YAML changes.
5. Import/deploy the bundled v1.5.2 Node-RED flow.
6. Configure HPVC from the sidebar Settings tab.

For later updates, update HPVC in HACS and restart Home Assistant. If the running Node-RED flow is older, `sensor.hpvc_nodered_status` reports **Update required**; import and deploy the updated bundled flow deliberately.

## Manual installation

The existing manual workflow is unchanged: replace/copy `hpvc_config.yaml`, import/deploy `hpvc_flow.json`, add `hpvc_dashboard.yaml`, and restart/reload as documented.

## Compatibility

- Home Assistant Core 2025.12+
- Node-RED with `node-red-contrib-home-assistant-websocket` 0.80.3+
- Existing v1.5.1 inverter Number entity / Action-service configuration remains compatible.
- Existing HBC, external release and safe-disable behavior remains compatible.

### Native HACS configuration

- HACS installations no longer require `homeassistant: packages:` or any edit to `configuration.yaml`.
- HPVC helpers and diagnostic template entities are provided natively by `custom_components/hpvc`.
- The HACS dashboard and bundled Node-RED flow use the native HPVC entities automatically.
- The traditional manual package/dashboard/Node-RED installation remains supported unchanged.
