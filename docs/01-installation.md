[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md) · [Inverter compatibility](05-inverter-compatibility.md)

# Installation

## Installation methods in v1.5.2

HPVC supports two installation paths. **HACS is the convenience path; manual installation remains supported exactly as a separate workflow.**

# HACS installation

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BioPC&repository=home-pv-control&category=integration)

1. Install HPVC through HACS and restart Home Assistant.
2. Add **Home PV Control** under **Settings → Devices & services**. During setup, leave the Node-RED URL empty to discover the Home Assistant Node-RED add-on, or enter a direct/external Admin API URL and credentials. A direct/external Node-RED runtime must already have a Home Assistant server configuration that HPVC can reuse.
3. Choose whether to enable **Automatically install/update HPVC Node-RED flow**. This is an explicit opt-in and defaults Off.
4. HPVC creates its required switches, text fields, selects, numbers, buttons and diagnostic entities natively and registers the bundled **Home PV Control** dashboard in the sidebar.
5. If automatic Node-RED management is enabled, HPVC manages only its marked HPVC tabs through the per-flow Node-RED Admin API. If it is disabled, use **Install / update Node-RED flow** once from HPVC Settings.
6. Configure HPVC from the sidebar **Settings** tab.

**No `configuration.yaml` change is required for HACS installation.** HACS mode does not use `/config/packages/hpvc_config.yaml`.

#### Updating after HACS installation

The first HACS installation requires a Home Assistant restart because the custom integration Python modules must be imported. For later HACS updates, HPVC fingerprints the loaded integration files and periodically compares them with the files installed on disk.

- `button.hpvc_check_installed_update` checks immediately instead of waiting for the periodic monitor.
- `sensor.hpvc_update_status` reports **Up to date**, **Quick reload available**, **Restart required**, **Applying update**, **Reloading HPVC** or an error state.
- If no `.py` file changed, HPVC reports **Quick reload available**. Confirm **Apply installed update** in the HPVC Settings tab. If the bundled Node-RED flow changed, HPVC updates the four managed HPVC tabs first using the per-flow Node-RED Admin API (`POST /flow` and `PUT /flow/:id`), then reloads only the Home PV Control config entry. Home Assistant itself is not restarted.
- If any HPVC `.py` file changed, HPVC reports **Restart required** and deliberately blocks quick reload so Home Assistant can load the updated Python modules during a full restart.
- The running Node-RED flow publishes its version to `text.hpvc_nodered_version`.

A config-entry reload is not used as a substitute for loading changed Python code, and HPVC never posts the complete Node-RED configuration during this update path.

## Switching between Manual and HACS-native

Do not enable both installation methods at the same time. v1.5.2 includes a mixed-install safety interlock.

- **Manual → HACS-native:** remove the manual HPVC package, restart Home Assistant so the legacy `input_*` HPVC helpers are gone, then add/reload the Home PV Control integration. After the native entities are present, install/update the HACS Node-RED flow from HPVC Settings.
- **HACS-native → Manual:** turn HPVC Off, remove/disable the Home PV Control integration, then install the package, manual Node-RED flow and YAML dashboard together.

If legacy manual HPVC helpers are detected while the HACS integration is present, native HPVC control and Node-RED management stay blocked until one installation method is removed. HPVC never deletes or edits the manual YAML package automatically.

# Manual installation

Continue with the steps below. The original package, Node-RED flow and YAML dashboard remain first-class supported files.
Home PV Control can run independently or alongside Home Battery Control. Use Steps 1–6 for a fresh installation. Existing installations should also read the upgrade section before replacing files.

## Requirements

- Home Assistant Core **2025.12 or newer** (documented support baseline; package configuration is required only for manual installation)
- Local HPVC brand artwork is cosmetic and is shown by Home Assistant versions that support local custom-integration branding (HA 2026.3+).
- Node-RED with `node-red-contrib-home-assistant-websocket` version **0.80.3 or newer**
- At least one inverter control path: either a writable Home Assistant `number` power-limit entity or a stable Home Assistant action/service adapter; limits may represent Watts or Percent
- ApexCharts Card for the supplied dashboard graphs

The supplied dashboard requires **ApexCharts Card**. It does not require card-mod, Button Card, or Config Template Card.
- The standard Home Assistant `sun.sun` entity is recommended as supporting Night Restore context. Valid PV power is authoritative; `sun.sun` is used only to corroborate a pending Night Restore transition if PV telemetry disappears after the low-PV timer has already started.
- Home Battery Control only for optional HBC execution tracking and multi-battery Charge Priority

## Step 1 — Install the Home Assistant package

Copy [`home assistant/hpvc_config.yaml`](../home%20assistant/hpvc_config.yaml) to:

```text
/config/packages/hpvc_config.yaml
```

Ensure packages are enabled in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Reload supported YAML configuration where possible, or restart Home Assistant.

## Step 2 — Import the Node-RED flow

Import [`node-red/hpvc_flow.json`](../node-red/hpvc_flow.json), confirm that the Home Assistant server selected in the nodes is correct, and deploy the flow.

The flow imports as four tabs: **Inputs**, **Engine**, **Outputs**, and **Reports**. Import the complete flow rather than individual tabs so the control and report paths remain synchronized. See [How it works](03-how-it-works.md#node-red-flow-architecture) for the high-level layout.

## Step 3 — Add the dashboard

Install **ApexCharts Card** through HACS, then add [`home assistant/hpvc_dashboard.yaml`](../home%20assistant/hpvc_dashboard.yaml) as a separate YAML dashboard or view.

Do not paste it into your existing HBC dashboard unless you intentionally want to combine them.

## Step 4 — Configure entities

Open the **Settings** tab and configure:

- Grid power sensor
- Market/export price sensor
- All-in import price sensor
- Total PV power sensor
- One or more inverter control paths: writable limit entities or Action/service adapters
- Optional HBC integration toggle; native HBC entities are detected automatically

See [Settings](02-configuration.md) for sign conventions, thresholds, and inverter limits.

## Step 5 — Start with the shipped defaults

Review these starting values during first-install setup. HPVC enables automatically once the required live inputs and control settings validate successfully:

| Setting | Shipped default |
|---|---:|
| HBC integration / Charge Priority | Off |
| Force charge at negative price | On by default; used only when HBC control is enabled |
| PV limiting price | `0.00 €/kWh` |
| Price hysteresis | `0.02 €/kWh` |
| Export start | `-150 W` |
| Target export | `0 W` |
| Import restore | `150 W` |
| Min PV for control | `100 W` |
| Night Restore threshold | `10 W` |
| Cooldown | `30 s` |
| Deadband | `25 W` |

> **HBC permission:** **Enable HBC** is the master permission for HPVC to control charging in HBC. If it is turned off during an active negative-price override, only the confirmed restore sequence is allowed afterward. The negative-price charging switch is subordinate to it; with HBC disabled, negative prices still reduce PV to the configured inverter minimums but never change the HBC strategy.

> **PV limiting price guidance:** Use €0.00/kWh with a net export-price sensor. For a raw market-price sensor, adjust for fees, compensation, and local rules.

## Step 6 — Verify installation

Confirm that:

- The dashboard loads without missing-card errors.
- Configuration status reports as valid.
- HPVC can be enabled.
- No **Configuration error** Insight appears.
- Each configured inverter control path responds to a safe verification.
- Generate report changes to View report after publication completes.

Continue with [Troubleshooting](04-troubleshooting.md) when any check fails.

## Upgrade from v1.2.0 or earlier

Version 1.3.0 renames active legacy helper entity IDs from `pv_ems_*` to `hpvc_*`. Upgrade the Home Assistant package, Node-RED flow, and dashboard together:

1. Replace [`home assistant/hpvc_config.yaml`](../home%20assistant/hpvc_config.yaml).
2. Import and replace the existing flow with [`node-red/hpvc_flow.json`](../node-red/hpvc_flow.json).
3. Replace or re-import [`home assistant/hpvc_dashboard.yaml`](../home%20assistant/hpvc_dashboard.yaml).
4. Review **Force charge at negative price**. HPVC seeds it **On** once on both fresh installations and upgrades. After that, a manual Off choice survives normal Home Assistant restarts and package/automation reloads. **Restore defaults** turns it On again.
5. Reload packages or restart Home Assistant, then deploy Node-RED.
6. Copy or re-enter your sensor entities, inverter entities, limits, thresholds, and HBC integration preference in the new `hpvc_*` helpers.

Do not mix v1.5.2 files with older runtime files. Home Assistant may keep obsolete `pv_ems_*` helpers visible until their old package definitions are removed and Home Assistant is restarted.

### Upgrading to v1.5.2

v1.5.2 adds HACS/custom-integration packaging, native HPVC configuration entities, automatic sidebar registration and Node-RED version detection. HACS installations no longer require `configuration.yaml` package setup. It does not change the v1.5.1 safe-disable or external-release control semantics.

- **HACS:** update HPVC in HACS. If `sensor.hpvc_update_status` says **Quick reload available**, press **Confirm & apply installed update** and HPVC reloads only itself. If it says **Restart required**, restart Home Assistant. No manual package update is involved.
- **Manual:** replace the Home Assistant package, Node-RED flow and dashboard together, then restart/deploy as before.

## Next steps

- [Configure sensors and thresholds](02-configuration.md)
- [Understand the control sequence](03-how-it-works.md)
- [Diagnose problems](04-troubleshooting.md)

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md) · [Inverter compatibility](05-inverter-compatibility.md)
