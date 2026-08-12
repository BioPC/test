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

Home PV Control (HPVC) dynamically limits and restores PV inverter output in Home Assistant through Node-RED. It is designed for dynamic electricity contracts and can run as a standalone PV controller or integrate with Home Battery Control (HBC).

- Reduce unwanted or uneconomic PV export.
- Preserve useful PV for household consumption.
- Restore inverter output automatically when conditions improve.
- Coordinate available PV with optional HBC battery charging.
- Protect against negative all-in prices with minimum-PV control and optional HBC grid charging.

> [!IMPORTANT]
> HPVC requires at least one writable inverter power-limit entity exposed to Home Assistant. It does not communicate directly with an inverter.

<p align="center">
  <a href="assets/screenshots/main.png">
    <img src="assets/screenshots/main.png" alt="Home PV Control main dashboard" width="60%" title="Click to view full size">
  </a>
</p>

## Quick install

1. Enable Home Assistant packages:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy [`home assistant/hpvc_config.yaml`](home%20assistant/hpvc_config.yaml) to `/config/packages/hpvc_config.yaml`.
3. Restart Home Assistant or reload the supported YAML configuration.
4. Import [`node-red/hpvc_flow.json`](node-red/hpvc_flow.json) into Node-RED and deploy it.
5. Add [`home assistant/hpvc_dashboard.yaml`](home%20assistant/hpvc_dashboard.yaml) as a YAML dashboard or view.
6. Configure the grid-power, market/export-price, all-in-price, PV-power and inverter-limit entities.
7. Enable HPVC.

See the full [installation guide](docs/01-installation.md) for dependencies and first-run verification.

## Main features

| Feature | Status |
|---|---:|
| Standalone PV export control | ✅ |
| Dynamic export limiting and import recovery | ✅ |
| Multi-inverter support with per-inverter minimum/maximum limits | ✅ |
| Negative all-in-price minimum-PV protection | ✅ |
| Optional HBC grid charging during negative prices | ✅ |
| Optional HBC Charge Priority for `Charge` / `Charge PV` | ✅ |
| HBC 4.15.0 multi-battery support (1–6 batteries) | ✅ |
| Night Restore with PV recovery hysteresis | ✅ |
| Today’s Insights and Power Control history | ✅ |
| Daily Control Accuracy with four loss factors | ✅ |
| On-demand HTML and TXT support reports | ✅ |
| Ready-to-import Home Assistant dashboard | ✅ |

### HBC permissions

**Enable HBC** is the master permission for HPVC to modify HBC. The separate **Charge batteries at negative price** option only applies while HBC control is enabled.

At a valid all-in price `<= 0`:

- PV is always locked to the configured inverter minimums.
- HBC is forced to **Charge** only when both HBC permissions are enabled.
- With either HBC permission off, HPVC remains in PV-only negative-price protection.

## Requirements

- Home Assistant with package support.
- Node-RED with `node-red-contrib-home-assistant-websocket` **0.80.3 or newer**.
- One or more PV inverters with writable power-limit `number.*` entities.
- ApexCharts Card for the supplied dashboard graphs.
- Home Battery Control only for optional HBC integration and Charge Priority.

## Shipped defaults

These are starting values; review them for your inverter, electricity contract and local rules.

| Setting | Default |
|---|---:|
| HBC integration / Charge Priority | Off |
| Charge batteries at negative price | On, effective only with HBC enabled |
| PV limiting price | `0.00 €/kWh` |
| Price hysteresis | `0.02 €/kWh` |
| Export start | `-150 W` |
| Target export | `0 W` |
| Import restore | `150 W` |
| Min PV for control | `100 W` |
| Night restore PV threshold | `10 W` |
| Cooldown | `30 s` |
| Deadband | `25 W` |

HPVC requires `Export Start < Target Export < Import Restore`. Current v1.4.0 ranges include **Export Start -5000..0 W**, **Target Export -5000..+500 W** and **Cooldown 10..60 s**.

> **Price-source guidance:** use `0.00 €/kWh` with a net export-price sensor. If you use a raw market-price sensor, account for fees, compensation and local rules.

See [Settings](docs/02-configuration.md) for full configuration guidance.

## How HPVC works

HPVC evaluates the current grid power, PV production, electricity prices, inverter limits and optional HBC/battery state. Normal runtime evaluation occurs every **10 seconds**, plus startup and relevant settings changes.

The main control paths are:

1. **Normal price** — limit PV when export exceeds the configured threshold and restore output when import or price conditions allow it.
2. **Negative all-in price** — lock PV to configured minimums; optionally force HBC charging when permitted.
3. **HBC Charge Priority** — release useful PV within verified battery charging headroom while HBC is executing a charging strategy.
4. **Night Restore** — restore inverter limits once solar production has ended and wait for stable PV recovery before resuming daytime control.

Daily Control Accuracy uses continuity-aware target tracking and attributes estimated headline loss to **Control response, House load changes, PV availability,** or **Other**. Detailed attribution diagnostics are available in the support report rather than the main dashboard.

## Documentation

- [Installation](docs/01-installation.md)
- [Settings](docs/02-configuration.md)
- [How it works](docs/03-how-it-works.md)
- [Troubleshooting](docs/04-troubleshooting.md)
- [v1.4.0 release notes](releases/v1.4.0/release.md)
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

## Upgrading

Keep the Home Assistant package, Node-RED flow and dashboard on the same release version. For v1.4.0:

1. Back up the current package, dashboard, flow and `hpvc-data` journal.
2. Replace the package and complete Node-RED flow.
3. Replace or merge the dashboard.
4. Restart Home Assistant and deploy Node-RED.
5. Verify configured sensors and inverter limits.
6. Review **Charge batteries at negative price**.
7. Generate a support report and confirm the installation is healthy.

See the [v1.4.0 release notes](releases/v1.4.0/release.md) for the release-specific changes.

## Support

The generated report contains telemetry and entity IDs and is published at `/local/hpvc/support-report.html`.

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
  hpvc_config.yaml
  hpvc_dashboard.yaml

node-red/
  hpvc_flow.json

examples/
  hoymiles-opendtu-2-inverters.reference.json

assets/
  banner.png
  logo.svg
  screenshots/

docs/
  01-installation.md
  02-configuration.md
  03-how-it-works.md
  04-troubleshooting.md
  README.md

releases/
  v1.3.0/
  v1.4.0/
```

## Installation format

HPVC is distributed as a manual GitHub release ZIP, not as a HACS custom integration, plugin, theme or template repository.

## Credits

Inspired by the Home Assistant and Node-RED workflow of [Home Battery Control](https://github.com/gitcodebob/marstek-venus-rs485-node-red).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Disclaimer

Home PV Control modifies PV inverter power limits through Home Assistant and Node-RED integrations. You are responsible for verifying that your inverter, Home Assistant and Node-RED configuration are compatible and correctly configured. Incorrect configuration can reduce solar production or cause unexpected control behavior.

The software is provided “as is” without warranty. The author is not responsible for financial loss, equipment damage, data loss, regulatory issues or other consequences resulting from use of this project. Use it at your own risk.
