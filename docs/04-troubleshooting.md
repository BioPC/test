# Troubleshooting

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)

Use the generated support report first. **Executive summary**, **Decision evaluation**, **Sensor health**, **Inverters**, and **Today’s Insights** usually identify the blocking condition quickly.


## Start here

1. Confirm **Configuration status** is valid.
2. Check **Sensor health** for unavailable or invalid required inputs.
3. Check the current **Decision evaluation** and **Current action**.
4. Check **Today’s Insights** for a transition, write warning, or override fault.
5. Generate a fresh report before changing settings.

## Negative all-in-price override problems

HPVC saves the original `input_select.house_battery_strategy` and `input_select.house_battery_strategy_charge_goal` only when the override begins. It then confirms `Charge`, confirms `batteries are full`, and locks every inverter at its configured minimum. A valid all-in price `> 0` starts restoration without hysteresis; the charge goal is restored first and the strategy second.

Check the following when entry or restoration does not complete:

- both input-select entities are available;
- their option lists contain the exact values required or previously saved;
- `/config/hpvc-data/` is writable from Node-RED through a supported Home Assistant mount;
- `runtime-history.json` is valid JSON;
- the dashboard fault helper `input_boolean.hpvc_negative_override_fault` and the persistent notification show the current stuck phase.

After five minutes in an unconfirmed non-active phase, HPVC raises the fault helper and fixed-ID notification while keeping PV locked. The helper and notification are reasserted when Home Assistant restarts, and explicit service-call failures appear as `lastCallError` in diagnostics and reports. An unavailable all-in sensor deliberately holds the current override; it never counts as an exit.

For `recovery_unknown_previous`, use this exact manual recovery sequence:

1. Select the intended HBC strategy and charge goal manually.
2. Confirm both entities show valid values and neither is still the forced value (`Charge` for strategy or `batteries are full` for charge goal).
3. Turn off `input_boolean.hpvc_negative_override_fault`.
4. Wait for the next HPVC evaluation. HPVC treats the off action as explicit acknowledgement, clears the durable recovery object and notification, unlocks PV, and resumes normal control.

Turning off the helper before both HBC values are non-forced does not clear the recovery; HPVC reasserts the fault. Do not edit `runtime-history.json` manually unless the supported recovery path cannot run.

## HPVC turned itself off after a sensor outage

This is expected in the current v1.4.0 package. If a required configuration value or live grid, PV, market/export-price, all-in-price, or inverter-limit value becomes invalid, `HPVC - Disable when required inputs are invalid` switches off the master toggle and sets an automatic-resume flag. After configuration validity and all required inputs have remained valid for 5 continuous seconds, `HPVC - Resume when required inputs recover` switches HPVC on again and only then clears the pending flag. This happens only when HPVC was running before the fault. If HPVC had already been switched off manually, it remains off after recovery.

### Identify which required sensor failed

When HPVC pauses because a configured required input becomes invalid, **Today’s Insights** records the exact entity ID and validation reason. Identical faults are de-duplicated. During active Night Restore, expected nighttime loss of PV-power and inverter-limit telemetry is not logged as a fault.

## One inverter is unavailable

During normal daytime control, HPVC pauses all inverter writes when any configured inverter limit state is unavailable. This avoids allocating a total-plant target only across the remaining inverters. During an already-active Night Restore, PV total-power and inverter-limit states are intentionally exempt because OpenDTU/DTU entities may disappear after sunset; HPVC keeps PV calculations suspended instead of producing repeated availability errors. Grid and price safety inputs remain monitored. Restore an unavailable limit entity or temporarily reduce the configured inverter count only when the inverter is intentionally removed from service during normal control.


## Installation and configuration

### Entities are unavailable after upgrading to v1.3.0

Replace the Home Assistant package, Node-RED flow, and dashboard together. Version 1.3.0 uses `hpvc_*` entity IDs; old `pv_ems_*` helpers are not migrated automatically.

### Restore defaults does not appear or cannot run

Confirm that `script.hpvc_restore_defaults` exists and that the current dashboard YAML is loaded. Reload packages or restart Home Assistant after replacing `hpvc_config.yaml`.

### Configuration error: invalid power thresholds

HPVC requires `Export Start < Target Export <= 0 W` and `Import Restore >= 0 W`. Writes remain blocked until corrected.

### Node-RED says entity not found

Check the exact entity IDs configured for grid power, prices, PV power, inverter limits, and the optional HBC strategy entity. Empty or invalid IDs are intentionally treated as configuration errors.

## PV limiting and restore

### PV does not limit

Check:

- HPVC is enabled;
- configuration status is valid;
- the Market/export price is at or below the configured PV limiting price;
- grid export is more negative than Export Start;
- measured PV is above Min PV for control;
- cooldown is inactive;
- the requested change exceeds Deadband;
- inverter entities are writable and their full/minimum powers are correct.

### PV restores to full at night

This is expected. HPVC confirms Night Restore after measured PV remains at or below the configured Night restore PV threshold for 120 seconds. `sun.sun` is used as supporting diagnostic context, but the low-PV fallback also works when the Sun entity exists with a wrong location. If PV telemetry disappears after a valid low-PV sample has already started that timer, HPVC shows `Night Restore pending` and preserves the bounded confirmation window; missing PV may complete the transition only when `sun.sun` also reports `below_horizon`. Otherwise the pending state expires and normal strict sensor safety returns. After Night Restore activates, normal PV calculations are suspended. If the PV total-power sensor or inverter-limit entities disappear after sunset, HPVC ignores those nighttime-only availability checks and does not generate repeated errors. Recovery waits for PV telemetry to return and remain above `max(25 W, Night restore PV threshold + 15 W)` for 30 continuous seconds, so the default 10 W entry threshold recovers only after PV stays above 25 W for 30 seconds.

During Night Restore, the Home Assistant `HPVC Required Inputs Ready` safety sensor uses the published `Night Restore` status to exempt only the PV total-power and inverter-limit entities. Therefore their expected nighttime disappearance does not trigger the automatic master-switch shutdown. A missing/unknown PV state also cannot start Night Restore because the low-PV timer requires a genuinely valid numeric measurement.

### Import happens while PV is limited

Import Restore can raise the inverter limits even when measured PV is below Min PV for control. Low measured production may itself be caused by the active inverter limit.

### Inverter targets look wrong

Check inverter count, entity assignment, Full power, Minimum power, current limit, requested target, and Difference from target in the report. HPVC uses a direction-preserving proportional allocator and clamps every inverter to its configured minimum and maximum. A total increase must never reduce an individual inverter, and a total decrease must never raise one.

## HBC battery charge priority

If HPVC limits PV while a battery should still be charging, check the following for every configured battery:

- the battery power sensor is negative while charging;
- the SOC sensor is numeric; below 90% the executing `Charge`/`Charge PV` sub-strategy may place bounded Charge Priority in **Waiting**, but **Active** requires measured charging confirmation, while 90–100% also uses the learned taper profile;
- the maximum charge power entity is numeric and greater than 0;
- `input_number.house_battery_count` matches the actual number of batteries;
- HBC is executing `Charge` or `Charge PV`;
- HPVC HBC control is enabled.

In a multi-battery installation, one usable battery with known headroom is enough to activate HBC Charge Priority. A full, stale, unavailable, maximum-power, or taper-saturated battery must not block another battery that still has headroom. The diagnostics show each battery's status, SOC, actual power, maximum charge power, effective learned ceiling, SOC band, stable time, headroom, and reason.

## Why is Charge Priority off outside the PV-limiting price zone?

This is expected. Outside the remembered Market/export-price limiting zone, and when negative-price curtailment is not active, HPVC is not restricting PV. The inverters are already free to produce normally, so HBC can charge from available solar without an HPVC Charge Priority intervention. Charge Priority is reserved for the normal remembered Market/export-price limiting zone. Negative all-in-price mode uses a separate forced-grid-charging override and keeps Charge Priority off.

During negative all-in-price mode, HPVC immediately locks every inverter at its configured minimum, sets HBC strategy to `Charge`, and sets the charge goal to `batteries are full`. Charge Priority is off for the entire mode.

## HBC strategy changes unexpectedly

HPVC v1.4.0 normally does not write `input_select.house_battery_strategy`. The exception is negative all-in-price mode: HPVC saves the current strategy, selects `Charge`, and restores the saved strategy after the all-in price becomes greater than zero. Turn off `input_boolean.hpvc_control_hbc_strategy` only when HPVC should ignore HBC execution state and Charge Priority.

## Dashboard and graphs

### Insights card is empty

Confirm that `input_text.hpvc_insight_1` through `input_text.hpvc_insight_20` exist, deploy the supplied flow, and wait for the next evaluation. The latest 20 helpers should repopulate after deployment. The complete current-day journal is restored from `hpvc-data/runtime-history.json` when either supported Home Assistant configuration mount is writable.

### Live Inputs does not show inverter 6–10

Rows appear only for slots included by `input_number.hpvc_inverter_count`.

### Price Zones in older or custom dashboards

The packaged dashboard includes the **HBC Price Intervals** graph. Its grid and tooltip styling is theme-aware for both Home Assistant light and dark mode.


## Charge Priority says Off while HBC is executing Charge

This can be correct. **Off** is used when every usable battery is full, already at maximum charging power, or has no remaining normal or controlled taper headroom. **Requested** is reserved for cases where HBC requests charging but usable-battery eligibility cannot yet be resolved from telemetry. **Waiting** means HBC requests `Charge` or `Charge PV` and usable headroom exists, but measured charging is not yet confirmed or no usable PV increase is currently possible. Check the per-battery reason and headroom fields in the support report before treating Off as a fault.

## House load changes and PV availability remain 0.0%

The factors are shares of Daily Target Accuracy loss, not counters of how often load or sunlight changed. When Daily Target Accuracy is 100%, all factor values correctly remain 0.0%. With non-zero loss, direct control actions are classified first, then dominant estimated house-load changes, then PV availability with stable inverter limits, followed by passive control/plant conditions and Other. Generate a fresh report after deploying the current flow so the current accuracy model is used.

## Mobile report navigation buttons appear only after refresh

Use the current v1.4.0 report flow. It rechecks the floating Collapse and Top controls after mobile page restoration, restored scrolling, viewport or orientation changes, returning to the tab, and delayed layout completion. Generate a new report after deploying the flow; an older already-published HTML file does not contain the updated script.

## Reports

### Generate report does not change to View report

Wait for report generation to finish. **View report** appears only after publication succeeds. If it does not appear, check the persistent notification and Node-RED error log, then try again.

### The report time did not change

The report is an on-demand snapshot. Press **Generate report** again and wait for **View report** before reopening it.

### Generate or View report state appears stuck

Reload the dashboard and check Node-RED for a report-generation error. A successful generation publishes `/local/hpvc/support-report.html` and enables **View report**. The report state expires after one hour; generate a new report for a fresh snapshot. Restart Node-RED only after saving any diagnostic information you need.

### Decision evaluation says Triggered while PV currently limited says No

This is valid. **Triggered** means the threshold condition is currently true. **PV currently limited** shows the actual control state. Cooldown, deadband, minimum PV, price mode, configuration errors, unavailable inputs, or another guard may prevent a new write.

### Current action says No inverter change

The report now shows the actual recorded action. It does not infer Reduce PV or Increase PV solely from a triggered condition.

### TXT export differs from HTML

Both formats use the same report model. Generate a fresh report, then download TXT from that HTML snapshot. If an older file remains open, refresh only after generating a new report.

### Report tile remains on Generating after a deploy

The report flow clears a stale internal report lock and turns off `input_boolean.hpvc_report_generating` two seconds after Node-RED starts. This restores the Generate report tile without deleting an already published report.

## Node-RED and diagnostics

### The flow imports as four tabs

This is expected. Always import the complete `hpvc_flow.json`; the Inputs, Engine, Outputs, and Reports tabs are designed to work together.

### No Write warning Insight appears

Successful writes do not create routine warning Insights. A warning appears only when a requested inverter value remains unconfirmed after the verification timeout and has not been superseded by a newer target.

### Advanced diagnostic data is invalid or truncated

`input_text.hpvc_last_targets_json` is limited to 255 characters. When necessary, HPVC stores a smaller valid diagnostic object instead of truncating JSON mid-field.

## Advanced diagnostics

### Report shows a runtime data notice

Live grid, PV, and price values are captured when the report is generated, while decision and taper diagnostics describe the latest completed HPVC evaluation. A notice means that evaluation is older than 120 seconds, diagnostic timestamps differ by more than 30 seconds, or no runtime evaluation has completed yet. It does not change control behavior.

### Repeated or truncated Battery telemetry Insights

The current flow records one Battery telemetry warning when a battery becomes unusable and one recovery after 60 seconds of continuous healthy telemetry. Truncated `input_text.hpvc_insight_*` values are startup fallback data only. Older duplicate rows are historical and disappear at the next local-midnight reset.

For the underlying telemetry, cutoff, freshness, Insight-retention, and report-semantics design, see [How it works](03-how-it-works.md).

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)
