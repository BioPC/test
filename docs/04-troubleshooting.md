# Troubleshooting

## Installation
- Configuration remains invalid.
- Required entities are unavailable.
- Dashboard or Restore Defaults button does not work after installation.

## PV control
- PV does not limit when expected.
- PV does not restore.
- Import while PV is limited.
- Night restore behaviour.

## Hidden PV Reveal

If Hidden PV Reveal never activates, verify:

- HBC Control is enabled.
- The selected HBC strategy supports Reveal.
- At least one battery is charging.
- The battery has remaining charge headroom.
- Hidden PV is available.
- Reveal is not paused.
- Cooldown is inactive.
- The grid is close enough to Target Export for a safe reveal.

## Dashboard
- Insights are empty.
- Configuration card reports invalid.

## Node-RED
- Entity not found errors.
- Write warnings or failed confirmations.


## Entities are unavailable after upgrading to v1.3.0

Check whether the dashboard or Node-RED flow still references legacy `pv_ems_*` or `sensor.hpvc_debug_*` entities while the package creates `hpvc_*` and `sensor.hpvc_diag_*` entities. Replace all three shipped runtime files together. Then restart/reload Home Assistant and deploy the new flow. Re-enter the configured entity IDs and numeric values because old helper states are not automatically copied to the renamed helpers.

## Restore button does not appear or cannot run

Confirm that the v1.3.0-or-newer package is loaded and that `script.hpvc_restore_defaults` exists in Developer Tools → States. The dashboard tile depends on that script, which directly reapplies the recommended configurable values. Reload scripts/automations or restart Home Assistant after replacing the package.

# Troubleshooting

## PV does not limit

Check:

- Home PV Control Enabled is on
- Market/export price is at or below PV Limiting Price
- Grid power is more negative than Export Start Threshold
- PV power is above Min PV for control
- Cooldown has passed
- PV inverter helpers is valid
- Limit entities are writable `number` entities

## PV restores to full at night

This is intended.

If night restore does not occur, check the active detection path. With `sun.sun` available, it must remain `below_horizon` for 120 seconds. Without `sun.sun`, total PV power must remain below the displayed fallback threshold for 120 seconds.

HPVC prefers `sun.sun` and restores after it remains `below_horizon` for 120 seconds. Only when `sun.sun` is unavailable does HPVC use the Night Restore PV Fallback Threshold. The dashboard hides that fallback input while the Sun entity is available.

## Import happens while PV is limited

Small import is allowed by design.

PV only recalculates upward when import rises above Import Recalculation Threshold.

Lower that threshold if you want more aggressive correction.

## Node-RED says entity not found

Check exact entity IDs in:

- sensor helpers
- HBC strategy entity helper
- PV inverter helpers

## Inverter targets look wrong

Check:

- full_power values
- minimum_power values
- configured inverter count and inverter entity helpers
- PVx Full Limit helper values
- PVx Low Limit helper values

## HBC strategy changes unexpectedly

Turn off:

```text
input_boolean.hpvc_control_hbc_strategy
```

Then Home PV Control only controls PV limits and leaves HBC strategy untouched.

## Insights card is empty

Check that `input_text.hpvc_insight_1` through `input_text.hpvc_insight_20` exist, then deploy the supplied Node-RED flow and wait for the next HPVC evaluation.

The current-day log is stored in Node-RED flow context. Without file-backed context storage, restarting Node-RED clears the accumulated Insight history.

## No Write warning Insight appears

Every inverter command records the requested entity/value pair in flow context. Verification runs on a later evaluation after at least the cooldown period. Successful writes are confirmed internally and do not create routine Insights. When a newer HPVC target replaces a pending write, the previous request is treated as superseded and does not create a warning. A **Write warning** is logged only when a request remains unconfirmed after the verification timeout without being replaced by a newer HPVC write. Confirm that the flow has been fully redeployed and that the configured number entities report their applied values.

## Settings error: invalid power thresholds

HPVC requires `Export Start < Target Export <= 0 W` and `Import Restore >= 0 W`. With the normal negative-export sign convention, Export Start must be more negative than Target Export. HPVC blocks inverter writes until the values are corrected.

## Import restore does not appear to respect Min PV

This is intentional: Min PV for control blocks new export limiting only. When PV is already limited and grid import exceeds Import Restore, HPVC may raise the inverter limits even if measured PV is below Min PV, because the low measured production may be caused by the active limit.
## Multiple HBC batteries still have charge headroom

HPVC sums the remaining charge headroom of all batteries that are actively charging. For each active battery it uses `Max Charge − current charging power`. Idle, unavailable, or non-charging batteries are excluded until HBC starts charging them.

If PV is still reduced while several batteries are charging, check the exported report's per-battery **Status**, **Current reveal allowance**, **Telemetry**, and **Reason** fields, plus the **Effective active-battery headroom** value. For inverter issues, check **Current limit**, **Requested target**, **Difference**, **At min/max**, and **Last verification**., Target Export margin, remaining hidden PV, the internal 800 W cap, and reveal-response/taper messages. A nearly full battery does not by itself cap reveal when another actively charging battery still has useful headroom.



## Price-zone graph is empty

Check that `sensor.hbc_energy_prices_data` has recent `prices` or `marks` data and valid timestamps. HPVC places points and matches the current interval using the timestamps and interval information provided by the sensor; 15 minutes is used only when no interval can be determined. The price-column width is visually inferred from timestamp spacing.

The HBC forecast values are interpreted as eurocents per kWh and converted to euros for the graph. A raw value of `5` must therefore appear as `0.050 €/kWh`, not `5.000 €/kWh`. HPVC then detects whether the current HBC point matches the configured Market or All-in sensor. Market data uses the learned `market × multiplier + fixed component` estimate when ready; during startup or initial learning, HPVC uses the current `All-in − Market` difference as a fallback. All-in data is unchanged. If the graph shows **Price type uncertain**, verify that both configured price sensors and the current HBC interval are available and synchronized. The 12-hour learning progress survives a normal Node-RED restart through the internal `input_text.hpvc_hbc_price_learning_json` helper. If the graph still shows euro-scale spikes after updating, reload the dashboard resources and clear the browser cache.

- HPVC first checks the configured All-in price sensor, then the Market/export price sensor, for forecast attributes. The automatic Market → estimated all-in conversion is most reliable when the configured Market/export sensor is a raw market-price sensor; a net export-price sensor can make the detected forecast type uncertain.

- The source must expose timestamps and prices through `marks`, `prices` plus `start`, `today` / `tomorrow`, or a forecast/rates attribute.
- The graph is displayed when `input_boolean.hpvc_control_hbc_strategy` is on. It is operational content on Main and no longer depends on `input_boolean.hpvc_config`. The selected HBC strategy does not affect graph data.

### Price Zones remains on Loading

- Verify that HBC is running and that `sensor.hbc_energy_prices_data` contains current forecast attributes. Some HBC strategies may not publish or refresh this data.

## Advanced diagnostic data is invalid or truncated

`input_text.hpvc_last_targets_json` must always contain valid JSON and is limited by Home Assistant to 255 characters.

In v1.3.0 the payload uses abbreviated keys to stay below that limit. If an unexpected future change makes it too long, HPVC stores a smaller valid JSON object with `err: "diagnostic_payload_reduced"` instead of cutting the JSON mid-field.

## Live Inputs does not show inverter 6–10

The Main-tab **Live Inputs** card supports PV1 through PV10. A row is shown only when `input_number.hpvc_inverter_count` includes that slot.

### Excess export while HBC is in Charge

HPVC evaluates and tracks every battery independently. Full PV remains available only when at least one battery has meaningful below-high-SOC headroom and a valid maximum-charge-power value. Small margins or missing maximum-power data use bounded Reveal instead. High-SOC mode enters at 90% and clears below 89%; the 95% band clears below 94%. Startup and telemetry grace are per battery (60 and 30 seconds), so one charging battery cannot hide another. If SOC is unavailable, startup fallback is limited to 15 seconds. Verify each configured battery power, SOC, and maximum-charge-power entity when the behavior differs from this.

A battery is not excluded merely because its numeric SOC or power value has not changed for more than 120 seconds. Home Assistant timestamps indicate value changes, not necessarily lost connectivity. Unavailable or nonnumeric telemetry is excluded. After a reveal, battery-response credit still requires a new power sample; otherwise HPVC uses PV and grid response. If maximum charge power briefly becomes unavailable, HPVC retains the last valid value; `unknown` should appear only when no valid value has ever been read.

The interim battery-eligibility package could raise `ReferenceError: rememberedMaxChargePowers is not defined`. Use the corrected package, where this map is initialized before battery processing.


### Why is Current reveal allowance much lower than Raw charger headroom?

**Raw charger headroom** is the theoretical unused charging capacity: maximum charge power minus the battery’s current charging power. **Current reveal allowance** is the smaller amount HPVC is willing to test at that moment. It is not fixed and it is not limited to the battery's current charging power. From 90% SOC onward, HPVC uses conservative probe ceilings: 200 W at 90–94%, 100 W at 95–96%, 50 W at 97–98%, 25 W at 99%, and 0 W at 100%. Target Export margin can make the actual reveal smaller. After each reveal, the response guard checks whether battery charging increased without unsafe export. A safe response allows another probe; weak absorption with export leakage is treated as real tapering and pauses further probes. The status **charging (high SOC)** by itself does not claim that tapering has been detected.

The HTML support report is generated only when **Generate report** is pressed. Wait for the same tile to change to **View report**, which confirms the file write completed. No background refresh is performed. Opening **View report** automatically resets the tile before the next fresh snapshot. The matching TXT snapshot is downloaded from the **Download report** button inside the generated HTML.


- **Poor-response pause: Active** means HPVC paused further reveal probes after an ineffective or unsafe response.
- **Response evaluation: Pending** means a previous reveal is still inside its settling/evaluation cycle.
- The inverter diagnostics card is derived from existing runtime values; no extra entities are needed.

## Reading the redesigned report

Start with **Executive status** and **Decision evaluation**. These sections show the active control mode, the reason for the decision, whether the export-limiting or import-restore condition is met, whether PV is currently limited, and whether cooldown, deadband, minimum-PV, reveal response, or another guard prevented a write. Use **Sensor health** to identify missing, unavailable, or stable numeric inputs.
### The report time did not change

The generated time changes only after **Generate report** is pressed and the new file is written. After the report opens, the tile automatically resets. Return to the dashboard and press **Generate report** for a new current snapshot.
### Generate or View report state appears stuck

Report generation now blocks overlapping button presses and automatically clears its generation lock on success or failure. Build, file publication, and report-state service errors all enter the same cleanup path. The View report webhook also retries after network errors and non-success HTTP responses.

