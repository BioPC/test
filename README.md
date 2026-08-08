<p align="center">
  <img src="assets/banner.png" alt="Home PV Control banner">
</p>

<p align="center">
  <a href="releases/v1.4.0/release.md"><img src="https://img.shields.io/badge/release-v1.4.0-blue" alt="Release v1.4.0"></a>
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

Home PV Control (HPVC) dynamically limits and restores PV inverter output in Home Assistant using Node-RED. It supports dynamic electricity prices, multiple inverters, optional Home Battery Control integration, and multi-battery HBC charging priority.

- Prevent unwanted or uneconomic PV export
- Preserve useful PV for household consumption
- Restore inverter output automatically when conditions improve
- Operate independently or alongside Home Battery Control


> [!IMPORTANT]
> HPVC requires at least one writable inverter power-limit entity exposed to Home Assistant. It does not communicate directly with an inverter; compatibility depends on the Home Assistant integration providing readable PV power and writable limit entities.

<p align="center">
  <a href="assets/screenshots/main.png">
    <img src="assets/screenshots/main.png" alt="Home PV Control main dashboard" width="60%" title="Click to view full size">
  </a>
</p>

## Contents

- [Quick install](#quick-install)
- [Features](#features)
- [Requirements](#requirements)
- [Architecture](#architecture)
- [Shipped defaults](#shipped-defaults)
- [How it evaluates](#how-it-evaluates)
- [Upgrading](#upgrading)
- [Documentation](#documentation)
- [Screenshots](#screenshots)
- [Support](#support)
- [Support the project](#support-the-project)
- [Repository structure](#repository-structure)
- [License](#license)

## Quick install

1. Confirm that Home Assistant packages are enabled in `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy [`home assistant/hpvc_config.yaml`](home%20assistant/hpvc_config.yaml) to:

   ```text
   /config/packages/hpvc_config.yaml
   ```

3. Reload the supported YAML configuration, or restart Home Assistant.

4. Import [`node-red/hpvc_flow.json`](node-red/hpvc_flow.json) into Node-RED and deploy it.

5. Add [`home assistant/hpvc_dashboard.yaml`](home%20assistant/hpvc_dashboard.yaml) as a separate YAML dashboard or view.

6. Configure the grid-power, Market/export-price, all-in-price, PV-power, and inverter-limit entities in the dashboard.

7. Enable Home PV Control.

See the full [installation guide](docs/01-installation.md), including ApexCharts setup and first-run verification.

## Features

| Feature | Status |
|---|---:|
| Separate HPVC Node-RED flow, independent of HBC | ✅ |
| Home Assistant package helpers | ✅ |
| Ready-to-import Home Assistant dashboard | ✅ |
| Multi-inverter support | ✅ |
| Per-inverter minimum and maximum limits | ✅ |
| Direction-preserving multi-inverter target distribution | ✅ |
| Dynamic export limiting and import recovery | ✅ |
| Negative all-in-price override: minimum-PV lock with confirmed HBC grid charging | ✅ |
| `sun.sun` night restore with PV fallback | ✅ |
| Optional HBC execution tracking and Charge Priority | ✅ |
| Multi-battery HBC charging priority in PV-restricting contexts | ✅ |
| On-demand HTML and TXT support reports | ✅ |
| HBC files remain untouched | ✅ |

## Requirements

- Home Assistant
- Node-RED with `node-red-contrib-home-assistant-websocket` **0.80.3 or newer**
- One or more PV inverters with writable power-limit entities
- ApexCharts Card for the supplied dashboard graphs
- Home Battery Control only for optional HBC execution tracking and battery Charge Priority

## Architecture

```mermaid
flowchart LR
    HBC[Home Battery Control<br/>Battery strategies]
    BAT[Battery status and power]
    PRICE[Market / all-in price]
    GRID[Grid power sensor]
    PV[PV power sensor]
    HPVC[Home PV Control<br/>Node-RED flow]
    LIMITS[PV inverter limits]

    HBC --> BAT
    HBC -->|Selected and executing strategy| HPVC

    PRICE --> HPVC
    GRID --> HPVC
    PV --> HPVC
    BAT --> HPVC

    HPVC --> LIMITS
```

## Shipped defaults

These values are safe starting points, not universal recommendations. Review them for your inverter, sensor definitions, electricity contract, and local rules.

| Setting | Shipped default |
|---|---:|
| PV limiting price | `0.00 €/kWh` |
| Price hysteresis | `0.02 €/kWh` |
| Export start | `-150 W` |
| Target export | `0 W` |
| Import restore | `150 W` |
| Min PV for control | `100 W` |
| Night restore PV threshold | `10 W` |
| Cooldown | `30 s` |
| Deadband | `25 W` |

> **PV limiting price guidance:** Use €0.00/kWh with a net export-price sensor. For a raw market-price sensor, adjust for fees, compensation, and local rules.

See [Settings](docs/02-configuration.md#marketexport-price-sensor) for sensor guidance and examples.

## How it evaluates

HPVC evaluates:

- every 10 seconds for limiting, restore, negative-price mode, and HBC Charge Priority;
- once immediately after deploy or startup;
- once when relevant HPVC settings change.

## Upgrading

When upgrading from an older release, keep the Home Assistant package, Node-RED flow, and dashboard on the same version. Review:

- entity-name migration;
- dashboard entity references;
- Node-RED flow replacement;
- restored-default behaviour;
- release-specific compatibility notes.

See the [v1.4.0 release notes](releases/v1.4.0/release.md).

## Documentation

- [Installation](docs/01-installation.md)
- [Settings](docs/02-configuration.md)
- [How it works](docs/03-how-it-works.md)
- [Troubleshooting](docs/04-troubleshooting.md)
- [Changelog](CHANGELOG.md)

For Home Battery Control itself, see the [HBC documentation](https://docs.homebatterycontrol.com/).

## Screenshots

### Settings dashboard

<p align="center">
  <a href="assets/screenshots/settings.png">
    <img src="assets/screenshots/settings.png" alt="Home PV Control settings dashboard" width="50%" title="Click to view full size">
  </a>
</p>

### Support report

The report preview is split into four equal-height parts. Click any part to open it at full resolution.

<p align="center">
  <a href="assets/screenshots/report_part_1.png"><img src="assets/screenshots/report_part_1.png" alt="HPVC support report — part 1" width="20%" title="Click to view full size"></a>
  <a href="assets/screenshots/report_part_2.png"><img src="assets/screenshots/report_part_2.png" alt="HPVC support report — part 2" width="20%" title="Click to view full size"></a>
  <a href="assets/screenshots/report_part_3.png"><img src="assets/screenshots/report_part_3.png" alt="HPVC support report — part 3" width="20%" title="Click to view full size"></a>
  <a href="assets/screenshots/report_part_4.png"><img src="assets/screenshots/report_part_4.png" alt="HPVC support report — part 4" width="20%" title="Click to view full size"></a>
</p>

### Node-RED architecture overview

<p align="center">
  <a href="assets/screenshots/node_red_flow.png">
    <img src="assets/screenshots/node_red_flow.png" alt="Home PV Control Node-RED architecture overview" width="60%" title="Click to view full size">
  </a>
</p>

## Support

The report contains telemetry and entity IDs and is published at `/local/hpvc/support-report.html`.

Before opening an issue:

1. Generate an HPVC support report.
2. Remove private entity names or data you do not want to share.
3. Include the HPVC, Home Assistant, and Node-RED versions.
4. Describe the expected behaviour and what actually happened.

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
  hpvc_flow.json        # Importable Node-RED flow with four v1.4.0 tabs

examples/
  hoymiles-opendtu-2-inverters.reference.json

assets/
  banner.png
  logo.svg
  screenshots/          # Current Dashboard, Report and Node-RED architecture images

docs/
  01-installation.md
  02-configuration.md
  03-how-it-works.md
  04-troubleshooting.md
  README.md             # Documentation index

releases/
  v1.3.0/
  v1.4.0/
```

## Installation format

HPVC is distributed as a manual GitHub release ZIP, not as a HACS custom integration, plugin, theme, or template repository. The package therefore intentionally contains no `hacs.json`; install the Home Assistant package, Node-RED flow, and dashboard manually as described above.

## Credits

Inspired by the Home Assistant and Node-RED workflow of [Home Battery Control](https://github.com/gitcodebob/marstek-venus-rs485-node-red).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Disclaimer

Home PV Control modifies PV inverter power limits through Home Assistant and Node-RED integrations.

By using this software, you acknowledge that:

- You are responsible for verifying that your inverter, Home Assistant, and Node-RED configuration are compatible and correctly configured.
- Incorrect configuration may reduce solar production, produce unexpected inverter behaviour, or fail to achieve the intended energy-management strategy.
- The software is provided “as is” without warranty of any kind.
- Always verify configuration changes safely before using them in a production energy system.
- The author is not responsible for financial loss, equipment damage, data loss, regulatory issues, or other consequences resulting from use of this project.

Use this project at your own risk.