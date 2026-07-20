# Installation

Home PV Control is installed next to Home Battery Control. It does not modify HBC files.

## Requirements

- Home Assistant
- Node-RED add-on / integration
- Home Battery Control already installed if you want HBC strategy handoff
- PV inverter limit entities exposed in Home Assistant as writable `number` entities
- Home Assistant Sun integration with the standard `sun.sun` entity is recommended. If unavailable, HPVC automatically uses the PV fallback threshold.

## Upgrade from v1.2.0 or earlier

Version 1.3.0 changes active legacy Home Assistant helper entity IDs from `pv_ems_*` to `hpvc_*`. Upgrade all three runtime files as one set:

1. Replace `home assistant/hpvc_config.yaml`.
2. Import and replace the existing Node-RED flow with `node-red/hpvc_flow.json`.
3. Replace or re-import `home assistant/hpvc_dashboard.yaml`.
4. Reload packages or restart Home Assistant, then deploy Node-RED.
5. Re-enter or copy your previous sensor entities, inverter entities, limits, thresholds, and strategy selections into the new `hpvc_*` helpers.

Do not mix a v1.3.0-or-newer file with an older config, flow, or dashboard: the renamed entities must match across all three files. Home Assistant may leave the old `hpvc_*` helpers visible until the old package definitions are removed and Home Assistant is restarted.

## Step 1 - Copy Home Assistant package

Copy:

```text
home assistant/hpvc_config.yaml
```

to:

```text
/config/packages/hpvc_config.yaml
```

Make sure packages are enabled in Home Assistant:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Restart Home Assistant.

## Step 2 - Import Node-RED flow

Import:

```text
node-red/hpvc_flow.json
```

into Node-RED.

After import, check that the Home Assistant server selected in the nodes is correct.

Deploy Node-RED.

## Step 3 - Add dashboard

Import or copy:

```text
home assistant/hpvc_dashboard.yaml
```

as a separate dashboard/view.

Do not paste it into your existing HBC dashboard unless you explicitly want to modify HBC.

## Step 4 - Configure entities

Set these helpers from the dashboard:

- Grid power sensor
- Market/export price sensor
- All-in import price sensor
- Total PV power sensor
- PV inverter helpers

## Step 5 - Test

Start with conservative values:

- PV Limiting Price: `0.00`
- Start Limiting When Exporting More Than: `-200 W`
- Target Export Power: `-25 W`
- Import Recalculation Threshold: `200 W`
- Minimum Minutes Between PV Changes: `1`
- Deadband: `25 W`


### Dashboard dependency

Install **ApexCharts Card** through HACS before using the supplied dashboard. The dashboard references `custom:apexcharts-card` for the price charts.


## Step 5 - Verify installation

After completing the configuration, verify that:

- The Home PV Control dashboard loads without errors.
- HPVC can be enabled.
- Configuration status reports as valid.
- No Configuration error Insight appears.
- The configured inverter limit entities respond when tested.

If any of these checks fail, continue with **04-troubleshooting.md**.
