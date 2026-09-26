![Home PV Control banner](https://raw.githubusercontent.com/BioPC/home-pv-control/main/assets/banner.png)

<p align="center">
  <a href="releases/v1.5.2/release.md"><img src="https://img.shields.io/badge/release-v1.5.2-blue" alt="Release v1.5.2"></a>
  <a href="https://www.home-assistant.io/"><img src="https://img.shields.io/badge/Home%20Assistant-ready-41BDF5" alt="Home Assistant ready"></a>
  <a href="https://nodered.org/"><img src="https://img.shields.io/badge/Node--RED-flow-8F0000" alt="Node-RED flow"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--or--later-blue" alt="GPL-3.0-or-later"></a>
  <a href="https://github.com/BioPC/home-pv-control/stargazers"><img src="https://img.shields.io/github/stars/BioPC/home-pv-control?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://ko-fi.com/mperez"><img src="https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a>
  <a href="https://paypal.me/MPerezCabrera"><img src="https://img.shields.io/badge/PayPal-Support%20me-003087?logo=paypal&logoColor=white" alt="Support with PayPal"></a>
</p>

# Home PV Control

Home PV Control (HPVC) dynamically controls, limits and restores PV inverter output in Home Assistant through Node-RED. It is designed for dynamic electricity contracts and can run as a standalone PV controller or integrate with Home Battery Control (HBC).

- Reduce unwanted or uneconomic PV export.
- Preserve useful PV for household consumption.
- Restore inverter output automatically when conditions improve.
- Coordinate available PV with optional HBC battery charging.
- Protect against negative all-in prices with minimum-PV control and optional HBC grid charging.

> [!IMPORTANT]
> HPVC requires at least one configured inverter control path: either a writable Home Assistant `number` entity or a stable Home Assistant action/service adapter. Limits can use Watts or Percent. HPVC controls through Home Assistant integrations; it does not communicate with inverter hardware directly.

See [Inverter compatibility](docs/05-inverter-compatibility.md) and [Configuration](docs/02-configuration.md) for the four compatibility statuses, current brand/integration matrix and configuration.

<p align="center">
  <img src="https://raw.githubusercontent.com/BioPC/home-pv-control/main/assets/screenshots/dashboard_main.png" alt="Home PV Control dashboard" width="60%">
</p>

## Contents

- [Requirements](#requirements)
- [Quick install](#quick-install)
- [Main features](#main-features)
- [How HPVC works](#how-hpvc-works)
- [Shipped defaults](#shipped-defaults)
- [HBC permissions](#hbc-permissions)
- [Safety and recovery](#safety-and-recovery)
- [Accuracy, Insights and reports](#accuracy-insights-and-reports)
- [Architecture and persistence](#architecture-and-persistence)
- [Updating HPVC](#updating-hpvc)
- [Documentation](#documentation)
- [Screenshots](#screenshots)
- [Support](#support)
- [Repository structure](#repository-structure)
- [Credits](#credits)
- [License](#license)
- [Disclaimer](#disclaimer)
  
## Requirements

- Home Assistant Core **2025.12 or newer**. HACS/native installation does not require Home Assistant package configuration; package support is needed only for the manual installation path.
  Local HPVC brand artwork is shown by Home Assistant versions that support custom-integration local branding (HA 2026.3+); this is cosmetic and does not change the functional 2025.12 minimum.
- Node-RED with `node-red-contrib-home-assistant-websocket` **0.80.3 or newer**.
- One or more PV inverters with either a writable `number.*` active-power limit or a stable Home Assistant action/service that can apply an active-power limit.
- A valid grid-power sensor, market/export-price sensor, all-in-price sensor and PV-power sensor.
- ApexCharts Card for the supplied dashboard graphs.
- Home Battery Control only for optional HBC execution tracking and Charge Priority.

## Quick install

HPVC v1.5.2 supports both **HACS** and the existing **manual installation** method. Manual installation remains fully supported.

### Option 1 — HACS

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BioPC&repository=home-pv-control&category=integration)

1. Open the button above and install **Home PV Control** as a HACS custom integration.
2. Restart Home Assistant so the new custom integration becomes available.
3. Go to **Settings → Devices & services → Add integration → Home PV Control** and add it.
4. HPVC creates its required configuration/diagnostic entities natively and registers **Home PV Control** in the Home Assistant sidebar. **No `configuration.yaml` edit and no `/config/packages` setup are required.**
5. During integration setup, leave the Node-RED URL empty to try automatic discovery, or enter the direct Node-RED Admin API URL and credentials if your Node-RED editor is protected. **Automatically install/update HPVC Node-RED flow** is an explicit opt-in. Leave it Off to use the manual install/update button.
6. When automatic Node-RED management is enabled—or when you press the manual **Install / update Node-RED flow** button—HPVC installs or updates its managed Node-RED tabs through the official per-flow Node-RED Admin API (`POST /flow` and `PUT /flow/:id`); it never posts the complete Node-RED configuration. Before replacing an existing HPVC flow it saves a backup under `/config/hpvc-data/nodered-backups/`. If Node-RED cannot be reached, Home Assistant setup still completes and the flow can be installed later from the HPVC **Settings** tab.
   For an external/direct Node-RED URL, configure an existing Home Assistant server in `node-red-contrib-home-assistant-websocket` first; HPVC reuses that server configuration instead of creating an add-on-specific one.
7. Configure HPVC from the sidebar **Settings** tab.

For update behavior after installation, see [Updating HPVC](#updating-hpvc).

### Option 2 — Manual installation

The traditional package + Node-RED + YAML-dashboard workflow is unchanged.

> This section applies only to the manual installation method. HACS users do not need to enable Home Assistant packages or edit `configuration.yaml`.

1. Enable Home Assistant packages in `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy [`home assistant/hpvc_config.yaml`](home%20assistant/hpvc_config.yaml) to `/config/packages/hpvc_config.yaml`.
3. Restart Home Assistant or reload the supported YAML configuration.
4. Import [`node-red/hpvc_flow.json`](node-red/hpvc_flow.json) into Node-RED and deploy it.
5. Add [`home assistant/hpvc_dashboard.yaml`](home%20assistant/hpvc_dashboard.yaml) as a YAML dashboard or view.
6. Configure the required sensors and inverter control paths from **Settings**.

See the full [installation guide](docs/01-installation.md) for dependencies, update behavior and first-run verification.

### Important — do not mix installation methods

> **Do not combine Manual and HACS-native HPVC.** v1.5.2 includes a mixed-install safety interlock. If legacy `input_boolean.hpvc_*`, `input_number.hpvc_*`, `input_text.hpvc_*`, `input_select.hpvc_*` or `input_button.hpvc_*` helpers are detected while the HACS integration is present, HPVC blocks the native control stack and Node-RED management and creates a persistent Home Assistant notification.
>
> For **Manual → HACS-native** migration, remove the old HPVC package/YAML definition if it is still present, then open **Home PV Control** in the sidebar. Protection mode provides **Delete legacy HPVC helpers & migrate** when storage-backed legacy helpers exist. If only YAML/runtime helpers remain, **Restart Home Assistant** becomes the primary migration action. With explicit administrator confirmation, HPVC deletes only storage-backed legacy `input_*.hpvc_*` helpers through Home Assistant's helper API. YAML/runtime helpers are never deleted by HPVC; remove their YAML/package source and restart Home Assistant. HPVC rescans automatically during startup and enters native mode when no legacy helpers remain. HPVC never edits Home Assistant `.storage` files directly and never deletes `hpvc-data/runtime-history.json`.
>
> If legacy YAML/runtime helpers remain, the migration screen can **Back up & remove legacy HPVC package** when the old package uses the standard `/config/packages/hpvc_config.yaml` path. HPVC creates a timestamped backup under `/config/hpvc-data/migration-backups/`, removes only that exact file after administrator confirmation, and then requires **Restart Home Assistant**. Other YAML files are never deleted automatically. HPVC rescans automatically during startup.

See [Installation → Switching between Manual and HACS-native](docs/01-installation.md#switching-between-manual-and-hacs-native) for the safe migration order.

## Main features

| Feature | Status |
|---|---:|
| Standalone PV export control | ✅ |
| Dynamic export limiting and import recovery | ✅ |
| Multi-inverter support with per-inverter minimum/maximum limits | ✅ |
| Per-inverter Watt or percentage limits | ✅ |
| Generic per-inverter Number entity / Action/service adapters | ✅ |
| Negative all-in-price minimum-PV protection | ✅ |
| Optional HBC grid charging during negative prices | ✅ |
| Optional HBC Charge Priority for `Charge` / `Charge PV` | ✅ |
| HBC multi-battery support (1–6 batteries) | ✅ |
| Night Restore with PV recovery hysteresis | ✅ |
| Today’s Insights and Power Control history | ✅ |
| Daily Control Accuracy with four loss factors | ✅ |
| On-demand HTML and TXT support reports | ✅ |
| Ready-to-import Home Assistant dashboard | ✅ |

## How HPVC works

HPVC evaluates:

- every **10 seconds**;
- immediately after deploy/startup;
- when relevant HPVC settings change.

Normal control follows a simple priority order:

1. Validate required inputs and configured inverter limits.
2. Apply negative-price protection when the all-in price is `<= 0`.
3. Handle Night Restore when PV production has effectively ended.
4. Coordinate available PV with HBC Charge Priority when HBC is enabled and eligible.
5. Limit export when price and grid conditions require it.
6. Restore PV when import or price recovery makes more output appropriate.
7. Respect cooldown and deadband so unnecessary writes are avoided.

## Shipped defaults

These are starting points, not universal recommendations. Review them for your inverter, sensor definitions, electricity contract and local rules.

| Setting | Shipped default |
|---|---:|
| HBC integration / Charge Priority | Off |
| Force charge at negative price | On by default; effective only while HBC control is enabled |
| PV limiting price | `0.00 €/kWh` |
| Price hysteresis | `0.02 €/kWh` |
| Export start | `-150 W` |
| Target export | `0 W` |
| Import restore | `150 W` |
| Min PV for control | `100 W` |
| Night restore PV threshold | `10 W` |
| Cooldown | `30 s` |
| Deadband | `25 W` |


> **PV limiting price guidance:** use €0.00/kWh with a net export-price sensor. For a raw market-price sensor, account for fees, compensation and local rules.

See [Settings](docs/02-configuration.md#marketexport-price-sensor) for sensor guidance and examples.

## HBC permissions

**Enable HBC** is the master permission for HPVC to control charging in HBC.

The separate **Force charge at negative price** option only applies while HBC control is enabled.

If HBC permission is removed during an already-active override, HPVC permits only the required restore sequence and then stops HBC writes.

### HBC Charge Priority

Charge Priority uses HBC execution state, measured battery power and verified battery headroom rather than assuming a selected strategy means charging is active.

- States: **Off, Requested, Waiting, Active**.
- Supports HBC battery order and RS485 eligibility for **1–6 batteries**.
- Multi-battery headroom and taper learning prevent one tapering/full battery from unnecessarily reducing available headroom from another battery.
- A short HBC response window allows HBC to absorb newly released PV before HPVC applies opposite export corrections.
- If confirmed battery charging drops into Waiting, a bounded transition-settle window lets the independent battery controller change state before HPVC reacts to the full transient grid error.
- Small PV corrections remain immediate; large normal corrections and Charge Priority releases are plant-size-relative and staged, with extra damping on the first large reversal.
- Persistent unabsorbed export still falls back to normal PV limiting.

## Safety and recovery

- Required sensors, inverter entities, helper ranges, duplicate entities and threshold relationships are validated before writes.
- Any unavailable configured inverter pauses the complete inverter group.
- Night Restore tolerates expected overnight PV/inverter-limit disappearance but never treats `unknown`/`unavailable` PV as measured zero.
- Battery freshness uses multiple telemetry signals and configured charging/discharging cutoffs.
- Invalid live cutoff values are faults rather than silently replaced defaults.
- HBC-dependent Charge Priority suspends on uncertain battery telemetry while normal PV control can continue where safe.
- Negative-price override state is persisted and restored safely across restart/deploy.
- Recovery paths require confirmed healthy data before dependent control resumes.

## Accuracy, Insights and reports

### Daily Control Accuracy

Daily Control Accuracy measures how closely grid power follows the requested target and exposes four headline loss factors:

- **Control response**
- **House load changes**
- **PV availability**
- **Other**

The factor values represent estimated percentage contributions to the headline accuracy loss and reconcile to `100 − Daily Control Accuracy`.

HPVC uses a short physical-event reconciliation window so delayed PV, battery and inverter-limit telemetry can still be associated with the grid event that caused the loss without delaying control. Detailed raw attribution, continuity and engineering metrics remain available in the support report. For Action/service inverters, this physical attribution requires a real numeric readback entity; command-cache-only adapters still participate in control and headline accuracy, but their cached command is not treated as physical inverter-limit evidence.

### Today’s Insights and Power Control

- Insights focus on meaningful transitions, warnings, faults and recoveries.
- HBC-only safety pauses remain distinguishable from full HPVC control blocks.
- Power Control history records current-day control activity and retains enough rows for a full day at the 10-second cadence.

### Support reports

On-demand HTML/TXT reports include:

- current HPVC decision and control mode;
- inverter state and calculated targets;
- inverter adapter, control-method and readback diagnostics;
- required sensor health;
- HBC strategy/execution and Charge Priority state;
- battery eligibility, headroom and taper diagnostics;
- negative-price override state;
- Daily Control Accuracy and attribution diagnostics;
- Today’s Insights and Power Control history.

Reports are generated from one shared fresh model and published atomically. Non-structural parity warnings no longer block **View report**; structural/shared-model failures still do.

## Architecture and persistence

### Control architecture

HPVC uses Home Assistant as the integration layer and Node-RED as the control engine.

| Inputs | Controller | Outputs |
| --- | --- | --- |
| Market / all-in price | Home PV Control (Node-RED) | PV inverter limits |
| Grid power |  | Optional HBC strategy control |
| PV power |  |  |
| Battery telemetry |  |  |
| Optional HBC state |  |  |

Home Assistant provides the configured sensors, writable inverter controls and optional HBC entities.

The HPVC Node-RED flow evaluates these inputs and decides when PV output should be limited, restored or left unchanged.

HBC integration is optional. When enabled, HPVC can read HBC state and request supported HBC strategy changes. HPVC remains responsible for PV control; HBC remains responsible for battery control.

### Runtime persistence

HPVC stores current-day runtime history in:

`hpvc-data/runtime-history.json`

This journal is shared by:

- Today's Insights
- Power Control history
- Daily Control Accuracy
- negative-price override state

Journal writes are serialized to prevent overlapping or stale writes.

After Home Assistant or Node-RED restarts, HPVC restores the current-day runtime state before dependent control actions continue. This helps prevent startup or redeploy races and preserves the active day's control history.

## Updating HPVC

Keep all HPVC runtime components on the same release version, but follow the update path for your installation mode.

### HACS/native updates

Update **Home PV Control** in HACS. HPVC v1.5.2 then distinguishes an installed update that changes Python from one that changes only reload-safe files. The running integration fingerprints its installed files and periodically checks the on-disk installation for changes.

- **No Python change:** `sensor.hpvc_update_status` becomes **Quick reload available**. Press `button.hpvc_apply_installed_update` (shown as **Confirm & apply installed update** in HPVC Settings). If the bundled Node-RED flow also changed, HPVC updates it first and then reloads only the Home PV Control config entry. Home Assistant is not restarted.
- **Python changed:** the status becomes **Restart required**. Quick reload is blocked because Python modules already imported by Home Assistant cannot be safely replaced with a config-entry reload. Restart Home Assistant to load the updated Python code.
- **Dashboard only:** the HPVC reload re-registers the sidebar panel with a new content fingerprint so the updated frontend is fetched.
- **Runtime configuration:** `runtime_config.json` is re-read on every HPVC config-entry setup.

Manual **Install / update Node-RED flow** and connection-check buttons remain available. HACS mode does not create or update `hpvc_config.yaml`, and no `configuration.yaml` change is required for an update.

### Manual updates

1. Back up the current package, dashboard, Node-RED flow and `hpvc-data` journal.
2. Replace the Home Assistant package.
3. Replace the complete manual Node-RED flow.
4. Replace or merge the manual dashboard.
5. Restart Home Assistant and deploy Node-RED.
6. Verify configured sensors and inverter limits.
7. Review **Force charge at negative price**. It is seeded **On** once on fresh installs and upgrades. After that, a manual Off choice survives normal Home Assistant restarts and package/automation reloads. **Restore defaults** turns it On again.
8. Generate a support report to confirm the installation is healthy.

Do not switch installation modes by layering one on top of the other. See [Installation → Switching between Manual and HACS-native](docs/01-installation.md#switching-between-manual-and-hacs-native) for the safe migration order and mixed-install protection behavior.

See the [v1.5.2 release notes](releases/v1.5.2/release.md) for the full release summary.

## Documentation

- [Installation](docs/01-installation.md)
- [Settings](docs/02-configuration.md)
- [How it works](docs/03-how-it-works.md)
- [Troubleshooting](docs/04-troubleshooting.md)
- [Inverter compatibility](docs/05-inverter-compatibility.md)
- [Documentation index](docs/README.md)
- [Changelog](CHANGELOG.md)
- [v1.5.2 release notes](releases/v1.5.2/release.md)

For Home Battery Control itself, see the [HBC documentation](https://docs.homebatterycontrol.com/).

## Screenshots

The bundled screenshots are retained for orientation and may show an earlier HPVC version. The shipped v1.5.2 HACS integration, YAML and Node-RED flow are authoritative.

### Settings

<p align="center">
  <img src="https://raw.githubusercontent.com/BioPC/home-pv-control/main/assets/screenshots/dashboard_settings.png" alt="Home PV Control settings" width="60%">
</p>

### Report

<p align="center">
  <img src="https://raw.githubusercontent.com/BioPC/home-pv-control/main/assets/screenshots/hpvc_report.png" alt="HPVC report" width="60%">
</p>

### Node-RED flow

Reference Node-RED architecture screenshot.

<p align="center">
  <img src="https://raw.githubusercontent.com/BioPC/home-pv-control/main/assets/screenshots/node_red_flow.png" alt="Home PV Control Node-RED flow" width="80%">
</p>

## Support

The HTML support report is published at `/local/hpvc/support-report.html`.

Before opening an issue:

1. Generate an HPVC support report.
2. Remove private entity names or data you do not want to share.
3. Include the HPVC, Home Assistant and Node-RED versions.
4. Describe the expected behavior and what actually happened.

Use [GitHub Issues](https://github.com/BioPC/home-pv-control/issues) for reproducible bugs and feature requests.

## Support the project

Home PV Control is free and open source. If you find it useful, you can support continued development.

<p align="left">
  <a href="https://ko-fi.com/mperez"><img src="https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a>
  <a href="https://paypal.me/MPerezCabrera"><img src="https://img.shields.io/badge/PayPal-Support%20me-003087?logo=paypal&logoColor=white" alt="Support with PayPal"></a>
</p>

## Repository structure

```text
home assistant/
  hpvc_config.yaml      # Home Assistant package and helpers
  hpvc_dashboard.yaml   # Separate Home Assistant dashboard

node-red/
  hpvc_flow.json        # Importable Node-RED flow with four functional tabs

examples/
  hoymiles-opendtu-2-inverters.reference.json

assets/
  banner.png
  logo.png
  screenshots/
    dashboard_main.png
    dashboard_settings.png
    hpvc_report.png
    node_red_flow.png

docs/
  01-installation.md
  02-configuration.md
  03-how-it-works.md
  04-troubleshooting.md
  05-inverter-compatibility.md
  README.md

custom_components/
  hpvc/                 # HACS companion integration and bundled runtime files

hacs.json               # HACS repository metadata

releases/
  v1.0.0/
  ...
  v1.5.2/
```

## Credits

Inspired by the Home Assistant and Node-RED workflow of [Home Battery Control](https://github.com/gitcodebob/marstek-venus-rs485-node-red).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Disclaimer

Home PV Control modifies PV inverter power limits through Home Assistant and Node-RED integrations.

By using this software, you acknowledge that:

- You are responsible for verifying that your inverter, Home Assistant and Node-RED configuration are compatible and correctly configured.
- Incorrect configuration may reduce solar production, produce unexpected inverter behavior or fail to achieve the intended energy-management strategy.
- The software is provided “as is” without warranty of any kind.
- Always verify configuration changes safely before using them in a production energy system.
- The author is not responsible for financial loss, equipment damage, data loss, regulatory issues or other consequences resulting from use of this project.

Use this project at your own risk.
