# Settings

The dashboard Settings tab contains the sensor setup, inverter setup, control thresholds, HBC settings, and tuning controls that were previously shown on Main. Press **Settings** in PV Master Control to show or hide all cards on this tab. The tab and button both use a cog icon.

Operational cards such as Live Inputs, accuracy, graphs, and Insights are now on Main and do not depend on the Settings toggle. Their HPVC- and HBC-specific visibility rules still apply.

## Entity helpers

Configure these helpers first.

### Grid Power Sensor

Expected sign convention:

```text
negative = export
positive = import
```

Example:

```text
sensor.p1_meter_power
```

### Market/export Price Sensor

Used for PV limiting decisions. Select either a raw market-price sensor or a net export-price sensor. The existing helper name is retained for compatibility.

Use `€0.00/kWh` as a neutral starting point. With a net export-price sensor, zero normally represents the financial break-even point. With a raw market-price sensor, adjust the PV limit threshold for supplier fees, compensation, taxes, saldering/net-metering, and other local rules. If HBC Price Zones must convert raw market forecasts to estimated all-in prices, a raw market-price sensor is recommended; a net export-price sensor remains valid for PV limiting but may make that optional graph conversion uncertain.

### All-in Import Price Sensor

Used only for optional HBC strategy switching.

### Total PV Power Sensor

Total current PV production in watts.

### HBC Strategy Entity

Disable `Home PV Control Controls HBC Strategy` if you only want PV limiting.

## PV inverter limits

Each inverter needs:

`limit_entity`  
Writable Home Assistant `number` entity used to set the inverter power limit.

`full_power`  
Normal maximum/full limit in watts.

`minimum_power`  
Lowest limit Home PV Control may set for this inverter. Must be zero or positive and lower than `full_power`; a negative value is reported as a configuration error rather than being silently ignored.

## Default values

These are the recommended defaults applied once by the first-run Home Assistant automation. They're a reasonable, tested starting point — adjust to your own setup once things are running.

| Setting | Default |
|---|---:|
| Home PV Control Enabled | On |
| Notifications | On |
| HBC Strategy Control | Off (starts disabled; enable manually once HBC is configured) |
| Settings | Off |
| Number of PV Inverters | 1 |
| PV Limiting Price | 0.00 €/kWh |
| Battery Charge All-in Price | 0.10 €/kWh |
| Expensive All-in Price | 0.35 €/kWh |
| Battery Price Hysteresis | 0.02 €/kWh |
| Export Start Threshold | -150 W |
| Target Export Power | -25 W |
| Import Restore Threshold | 150 W |
| Min PV for Control | 100 W |
| Night Restore PV Fallback Threshold | 10 W |
| PV Cooldown | 60 sec |
| PV Adjustment Deadband | 25 W |
| PV1–PV10 Full Limit | 0 W (must be set per inverter) |
| PV1–PV10 Low Limit | 0 W (must be set per inverter) |
| Balanced Strategy | Dynamic 2 |
| Expensive Strategy | Sell |
| Battery Strategy Entity | `input_select.house_battery_strategy` |

> **Price guidance:** `0.00 €/kWh` is the neutral shipped default. It is normally the break-even threshold for a correctly calculated net export-price sensor. A raw market-price sensor may require a positive or negative threshold depending on supplier fees, compensation, taxes, saldering/net-metering, and local rules.

### Netherlands example

The package does not calculate Dutch taxes, saldering, or supplier fees. The following values are examples for a **raw market-price sensor excluding VAT**, not universal defaults:

| Situation | Example PV limit price |
|---|---:|
| Remaining annual saldering allowance in 2026 | approximately `-0.09 €/kWh` |
| No remaining saldering allowance / annual net surplus | approximately `+0.02 €/kWh` |
| From 1 January 2027, without saldering | supplier-specific; for about 2.48 eurocents/kWh export fees, approximately `+0.02 €/kWh` |
| Correctly calculated net export-price sensor | `0.00 €/kWh` |

The `-0.09 €/kWh` example assumes Dutch 2026 saldering value and a market sensor excluding VAT. The `+0.02 €/kWh` example is not a general Dutch tariff: it applies only when the effective export fee is close to 2.48 eurocents per kWh. From 2027, use the actual compensation and fees of your supplier. Verify whether your sensor includes VAT and whether your supplier applies different fees or compensation before using either value.

## Notes

The Node-RED flow reads the configured entity IDs from `input_text` helpers, so no Node-RED deploy-time entity discovery is needed. The flow runs on a 15-second timer plus an on-deploy/startup trigger; a separate `server-state-changed` node re-runs the flow immediately whenever one of the configuration helpers itself changes (for example, when you update an inverter limit entity or a threshold). Changes to the live grid/market/PV sensors are picked up on the next 15-second cycle rather than triggering an immediate run.

## Entity configuration

The grid power, prices, PV power, PV limit, and HBC strategy entities are plain `input_text` fields rather than dropdowns. Paste the entity ID directly into each field (for example `sensor.p1_meter_power` or `number.hms_2000_4t_limit_nonpersistent_absolute`). This avoids generating large dynamic dropdown option lists on installations with many entities. If a field is left empty or contains an invalid entity ID, Home PV Control treats that input as unconfigured and reports a configuration error rather than guessing.

## Hidden PV Reveal

Hidden PV Reveal uses the configured **Export Start**, **Target Export**, **Deadband**, **Cooldown**, and **Min PV for control** settings. When HBC Control is enabled, HPVC automatically calculates safe reveal amounts from available battery charging headroom. No additional Reveal setting is required.

**Export Start** determines when PV limiting begins. **Target Export** is the grid target HPVC tries to maintain and the upper edge of the Reveal recovery window. Hidden PV Reveal is allowed only after export has recovered to at least Export Start, preventing additional PV from being revealed while export remains excessive.

The required relationships are:

- `Export Start < Target Export <= 0 W`
- `Import Restore >= 0 W`

Invalid combinations produce a configuration error and block inverter writes until corrected. A 75–100 W gap between Export Start and Target Export is recommended for smooth control.

**Min PV for control** prevents new export-limiting actions when measured PV production is already low. It does not block Import Restore or Hidden PV Reveal.

**Cooldown** defines the minimum time between inverter-limit writes. During cooldown, HPVC continues monitoring but sends no new PV-limit command.

**Deadband** is the minimum power difference required before HPVC sends a new inverter limit. Normal control applies it per inverter. Hidden PV Reveal applies it once to the total reveal request before preserving the proportional inverter split.

## Entity-name change in v1.3.0

All helpers, template entities, dashboard references, and Node-RED references now use the `hpvc_*` prefix. Examples include:

- `input_boolean.pv_ems_enabled` → `input_boolean.hpvc_enabled`
- `input_text.pv_ems_grid_power_sensor` → `input_text.hpvc_grid_power_sensor`
- `input_number.pv_ems_export_start_threshold` → `input_number.hpvc_export_start_threshold`

This is an entity-ID rename, not only a display-name change. Existing settings under the old helpers are not transferred automatically. Replace the config, flow, and dashboard together, then copy or re-enter the values you want to keep.

## Restore defaults button

The **PV Master Control** dashboard includes a full-width **Restore defaults** tile. It calls `script.hpvc_restore_defaults`, which directly reapplies the recommended configurable values. A confirmation dialog is shown before the action runs. It preserves configured sensor entities, inverter limit entity selections, the active inverter count, and the user's current HBC Strategy Control on/off state.

The restore action resets the shipped HPVC defaults, but it does not populate installation-specific core sensor or inverter entity IDs. After restoring, verify the sensor entities, inverter limit entities, maximum powers, minimum powers, inverter count, and optional HBC strategy entity.

## First-run defaults and restart persistence

User-configurable Home PV Control helpers do not use `initial:` values in the shipped YAML, allowing Home Assistant to restore user-edited settings after a restart. The transient `hpvc_report_ready` and `hpvc_report_generating` helpers intentionally use `initial: false` so stale report states are not restored.

A Home Assistant first-run automation applies recommended defaults only when `input_boolean.hpvc_defaults_applied` is still off. After the defaults are applied, that flag is turned on and restored by Home Assistant on later restarts, so user changes are not overwritten.
