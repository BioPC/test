# How it works

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)

## Control overview

HPVC follows this execution order:

1. Capture one Home Assistant state snapshot.
2. Validate static configuration and runtime input readiness.
3. Evaluate usable HBC batteries and Charge Priority.
4. Determine price, import-recovery, cooldown, night, and negative-price modes.
5. Calculate and distribute inverter targets.
6. Make one authoritative minimum, restore, adjust, or hold decision.
7. Build inverter writes and publish status, Insights, diagnostics, and accuracy.
8. Generate reports only when the user presses Generate report.

Home PV Control calculates a target total PV limit and then distributes that target over all configured inverters.

The flow evaluates every 10 seconds and once at startup. Configuration-helper changes trigger an immediate evaluation; live grid, price, PV, battery, and inverter states are used on the next evaluation cycle.

## Input validation and startup safety

HPVC separates **configuration validity** from **live input readiness**.

- A missing or malformed entity ID in an HPVC helper is a configuration problem. HPVC allows up to 90 seconds after a Home Assistant restart for helpers to restore; if the problem remains, the status becomes **Configuration error**.
- A correctly configured grid, market/export-price, all-in-price, PV-power, or active inverter-limit entity that reports `unknown`, `unavailable`, an empty state, or a non-numeric value is a live-input outage. Home Assistant switches off the HPVC master toggle immediately when HPVC was running, and Node-RED sends no inverter writes.
- Node-RED may still report **Waiting for inputs** during the initial recovery window and **Inputs unavailable** for a longer outage, but the master toggle itself remains off while required inputs are invalid.
- When configuration validity and every required input have remained healthy for 5 continuous seconds, HPVC switches on automatically only when it had been switched off by the automatic safety automation. It then resumes normal evaluation and records the usual restored-input status and Insight.

During normal control, HPVC never substitutes `0 W` for unavailable grid/PV measurements and never substitutes the configured full limit for an unavailable inverter-limit state. This prevents restart-time or integration-outage decisions from being made with invented values. The deliberate nighttime exception applies to an active Night Restore and to a bounded `Night Restore pending` transition that was started by a valid low-PV measurement. During those states, the PV total-power and non-persistent inverter-limit entities may disappear without immediately disabling HPVC. Grid and price safety inputs are still checked.

If any configured inverter limit is unavailable, the complete inverter-write stage is paused. HPVC does not distribute a total-plant target across only the remaining inverters because the unavailable inverter may still be producing.

## Negative-price and Charge Priority completion behavior

The configured all-in-price sensor controls a dedicated negative-price override independently of the normal market/export-price hysteresis.

### Negative all-in-price state machine

- **Inactive:** a valid all-in price `<= 0` creates and persists an override object containing the original HBC strategy and charge goal.
- **Entering strategy:** HPVC requests `input_select.house_battery_strategy = Charge` and waits for state confirmation.
- **Entering goal:** after `Charge` is confirmed, HPVC requests `input_select.house_battery_strategy_charge_goal = batteries are full` and waits for confirmation.
- **Active:** every inverter is held at its own configured minimum, HPVC Charge Priority is off, and other PV control paths cannot change the limits.
- **Invalid-sensor hold:** if the all-in sensor becomes `unknown` or `unavailable`, the active phase and minimum lock are retained.
- **Restoring goal:** at a valid all-in price `> 0`, HPVC restores and confirms the saved charge goal.
- **Restoring strategy:** HPVC then restores and confirms the saved strategy.
- **Resumed:** only after both confirmations is the lock removed and the current normal market/export-price decision evaluated. No automatic full-PV step is inserted.

The required options are validated before service calls. Every inverter is compared independently with its own minimum using a 1 W lock tolerance. Ordinary Charge Priority still permits downward `Charge + Limit` correction to remove surplus that batteries do not absorb.

## Dynamic limiting conditions

Normal export limiting is allowed when:

- market/export price is at or below the PV limiting price
- PV production is above Min PV for control
- grid power is more negative than Export Start
- cooldown has passed
- the combined total target differs from the current combined limit by at least the deadband

Import recovery and HBC battery charge priority may raise limits even when measured PV is below Min PV for control. This is intentional because an active inverter limit can itself suppress the measured PV value.

### Import recalculation

When PV is already limited and grid import rises above Import Restore, HPVC recalculates upward instead of blindly restoring every inverter to full. For this recovery calculation it uses at least the current combined inverter limit as the available-PV baseline, so low measured PV does not prevent recovery.

## PV target calculation

```text
target_total = pv_power + grid_power - target_grid_power
```

Example:

```text
PV power = 2500 W
Grid power = -600 W
Target export = 0 W

target_total = 2500 - 600 - 0 = 1900 W
```

## Inverter target distribution

The requested total is allocated from the live inverter limits in one direction only. For an increase, no inverter target may decrease; for a reduction, no inverter target may increase. The allocator uses proportional weighted water-filling based on each inverter's configured maximum power, redistributing only when an inverter reaches a minimum or maximum bound. The deadband is evaluated for the combined plant change, so meaningful total changes are not lost merely because one proportional inverter share is smaller than the deadband. Integer-W systems remain integer; decimal live limits are reconciled at milliwatt precision to avoid ceil/floor residuals. Exact-deadband and exact minimum/full-boundary actions are treated as meaningful.

Example:

```text
PV1 full = 2000 W
PV2 full = 1000 W
Total full = 3000 W
```

PV1 gets 2/3 of the target, PV2 gets 1/3.

If another user has:

```text
PV1 = 1500 W
PV2 = 1500 W
```

both get 50%.

### Per-inverter minimum power

Every inverter has its own `minimum_power`.

HPVC never sets an inverter below this value.

### Plant-level deadband and proportional shares
The deadband is evaluated for the combined plant decision. Once a total change is meaningful, HPVC preserves the exact proportional target even when one or more individual inverter shares are smaller than the deadband. Those shares are marked as deadband overrides for diagnostics rather than discarded.

## Restore and recovery

PV is restored to full power when:

- market/export price rises above the PV limiting price plus the configured exit hysteresis; or
- measured PV remains at or below the Night restore PV threshold for 120 continuous seconds.

`sun.sun` is still used as the preferred diagnostic signal when it agrees with the low-PV condition, but actual PV is authoritative for recovery. The low-PV path remains active even when `sun.sun` exists, so an incorrect Home Assistant location cannot prevent Night Restore. Conversely, if `sun.sun` incorrectly reports `below_horizon` while measured PV is above the entry threshold, HPVC does not enter Night Restore.

After the 120-second condition is confirmed, HPVC restores all configured inverter limits to full power while their live states are available. Once the limits are confirmed full, normal PV target/control calculations are suspended while Night Restore remains active. If the PV total-power sensor or inverter-limit states then become unavailable after sunset, HPVC treats that as expected nighttime telemetry loss: those two checks no longer generate input/inverter availability errors and PV calculations stay suspended. Grid power, prices, configuration, HBC/battery telemetry, diagnostics, reports, and the recovery path continue to run. If limit telemetry is already unavailable when Night Restore is active, HPVC suspends control rather than repeatedly erroring or inventing limit values. Recovery is deliberately hysteretic and waits for PV telemetry to return: PV must remain above `max(25 W, Night restore PV threshold + 15 W)` for 30 continuous seconds before Night Restore ends. With the default 10 W entry threshold, this means recovery requires more than 25 W for 30 seconds. Any dip back to or below the recovery threshold resets the recovery timer.

Night Restore entry starts only from a genuinely valid numeric low-PV measurement. If PV telemetry disappears after that timer has already started, HPVC exposes `Night Restore pending` and preserves the bounded 120-second confirmation window instead of immediately falling back to the daytime shutdown path. An unavailable PV value can complete that pending transition only when `sun.sun` also reports `below_horizon`; otherwise the pending window expires and strict daytime validation returns. Recovery still requires genuinely valid PV telemetry above the hysteretic recovery threshold for 30 continuous seconds. The internal numeric fallback used for display compatibility can neither start Night Restore nor satisfy recovery. While `input_text.hpvc_status` is `Night Restore` or `Night Restore pending`, `binary_sensor.hpvc_required_inputs_ready` mirrors the Node-RED nighttime exemption for only the PV total-power and inverter-limit states. Grid and price inputs remain mandatory. Core required-input validation checks missing, unavailable, unknown, empty, and non-numeric states; timestamp-based stale handling is intentionally specific to battery telemetry, where explicit freshness windows are defined.

Confirmed Night Restore state is persisted in `hpvc-data/runtime-history.json`. On restart it is restored before normal runtime evaluation, so an OpenDTU that is already asleep does not force HPVC back through the daytime required-input shutdown path. A partially completed recovery timer is intentionally not restored: recovery must be proven again with 30 continuous seconds of fresh valid PV telemetry.

## HBC battery charge priority

When HBC is executing `Charge` or `Charge PV`, that executing sub-strategy is the primary strategy signal. Charge Priority engages only inside the remembered normal PV-limiting price zone. Negative all-in-price mode uses a separate fixed-minimum and forced-grid-charging override, so Charge Priority remains off in that mode. Inside the normal limiting zone, battery charging takes priority over PV reduction. If at least one usable battery has known useful headroom, HPVC releases PV in bounded capacity-scaled steps and does not require measured charging to start first. From 90% upward, it uses a per-battery learned taper ceiling. A battery already charging contributes measured taper headroom; an idle battery may receive one small SOC-scaled startup probe so PV limiting cannot prevent charging from beginning. After a real Charge Priority write, each tapering battery is scored against its own proportional expected share of that increase; one battery absorbing well cannot incorrectly train another battery that did not absorb its share. Increased grid export remains a global safety signal for all affected taper profiles.

Below 90% SOC, each usable battery contributes its remaining normal charge headroom: configured maximum charge power minus current charging power. From 90% upward, each battery contributes only its own confirmed or controlled taper allowance. HPVC sums the normal and taper contributions, subtracts current grid export, and caps the final increase by remaining inverter capacity and the plant-level Charge Priority step. The taper portion is additionally capped per battery from that battery’s configured maximum charge power: **15% at 90–94%**, **10% at 94–98%**, and **5% at 98–100%**. A tapering battery awaiting confirmation contributes zero additional taper allowance, while another battery below 90% retains its normal contribution.

For multiple batteries, HPVC evaluates each battery independently. While HPVC is in a restricting context, a single usable battery below 90% with known useful headroom places bounded HBC Charge Priority in **Waiting** when the battery is idle. The state becomes **Active** only after measured charging is confirmed; the HBC sub-strategy is treated as a request, not proof of charging. Outside the limiting zone, PV is already unrestricted and this HPVC intervention remains off. Negative all-in-price mode also keeps Charge Priority off because HBC grid charging is forced separately. Stale, unavailable, full, maximum-power, or unknown-capacity batteries are excluded and cannot cancel priority for another battery. From 90% to 100%, learning is separated into five SOC bands per battery. A charging battery becomes eligible for a small probe after 60 seconds of stable power. An idle high-SOC battery may receive one conservative startup probe. Only real inverter writes are evaluated, and HPVC waits until each battery power sensor has a newer timestamp than the pre-write sample before training that battery's band. Absorption is evaluated per battery; increased grid export remains a global safety signal.

Once aggregate usable battery headroom is exhausted, HPVC resumes normal PV limiting according to market/export price and grid-flow thresholds. Charge Priority may still display **Active** while charging remains confirmed; the important distinction is that it no longer suppresses normal export limiting. Remembered maximum charge power expires after 30 minutes without a live value. Each unused SOC band expires independently after 48 hours, so activity in one band cannot keep another stale band alive indefinitely. Negative all-in-price mode remains the highest-priority fixed-minimum override. It disables HPVC Charge Priority and forces HBC grid charging until the all-in price becomes greater than zero.

### Battery eligibility

For HBC 4.15.0, a battery contributes Charge Priority headroom only when its required power, SOC, maximum-charge-power, and RS485-control entities are valid. `select.marstek_mN_rs485_control_mode` must be `enable`. A battery can be excluded individually without blocking other eligible batteries.

## Per-battery taper-only Charge Priority

HPVC evaluates every HBC battery independently. Batteries below 90% SOC keep the existing normal headroom calculation. A battery at 90% or above contributes only a controlled taper allowance derived from its own learned SOC-band ceiling and a per-battery capacity-scaled step cap.

The initial internal step caps are 15% of that battery's configured maximum charge power at 90–94%, 10% at 94–98%, and 5% at 98–100%. The allowance is also bounded by remaining learned headroom and the inverter/grid constraints. After a taper share is written, that battery contributes no additional unconfirmed taper increase until its own power sensor supplies a newer sample.

In mixed systems, a tapering battery never reduces the normal headroom of another battery below 90%. Taper-probe learning is attributed only to the taper share of the combined PV increase.

A failed taper probe removes that battery's unconfirmed taper allowance and keeps only its already demonstrated charging level. New probes for that battery are paused for 30 seconds after the first consecutive failure, 60 seconds after the second, and 5 minutes after the third. After three consecutive failures, probing remains blocked until that battery's measured charging power recovers by a meaningful amount. A successful probe resets the failure state. These states are stored per battery and per SOC band, so another battery below 90% or another healthy tapering battery continues contributing independently. When a battery reaches its configured charging cutoff, any pending probe for that battery is cancelled and its additional taper allowance becomes zero.

## Charge Priority degraded operation and diagnostics

- A battery with unavailable or stale power/SOC telemetry is excluded independently. Charge Priority continues with the remaining healthy batteries, or is suspended when none remain. A transition-only Insight is written when a battery is excluded and when it recovers.
- If any configured inverter limit entity is unavailable or non-numeric, HPVC pauses all inverter writes. A transition-only Insight identifies the affected inverter, and a recovery Insight is written after the complete inverter group is valid again.
- Charge Priority now exposes two separate states: whether Charge Priority is active and whether a PV increase is currently possible.
- The exact state/end reason is retained, including no headroom, export already consuming headroom, deadband, inverter maximum, full batteries, unsafe telemetry, or HBC no longer executing Charge/Charge PV.
- The support report includes a Charge Priority decision table and per-battery eligibility, SOC mode, headroom contribution, and exclusion reason.

The 90% SOC threshold changes headroom calculation from normal to taper-aware. It does not directly start or end Charge Priority.

### HBC battery charge order

For multi-battery HBC, HPVC reads `input_number.house_battery_control_prioritize_battery` and `input_select.house_battery_control_priority_change_interval` when those native HBC helpers are available. It rotates battery-capacity evaluation into the same order HBC uses; for example, priority 2 with three batteries becomes M2 → M3 → M1. HBC assigns charging demand sequentially through that rotated list and spills any remaining demand into later batteries in the same pass, so HPVC retains combined usable headroom while preserving the correct priority order for per-battery evaluation and diagnostics. Older HBC versions without these helpers fall back to M1-first order.

## HBC Charge Priority coordination

HBC remains the fast grid-balancing controller during Charge Priority, while HPVC manages the available PV ceiling. After HPVC raises inverter limits for Charge Priority, it starts a **15-second response window**. During this window, normal HPVC export limiting is suppressed so HBC can adjust battery charging from live grid-power feedback without HPVC issuing an immediate opposite correction.

Outside the response window, export limiting remains suppressed while Charge Priority is engaged, confirmed battery charging headroom remains greater than the HPVC deadband, and the persistent-export fallback has not activated. If grid export stays beyond **Export Start** continuously for **30 seconds** while usable headroom still exists, the fallback activates and HPVC may reduce PV. The timer resets as soon as export returns above the Export Start threshold or Charge Priority/headroom is no longer applicable.

The support report exposes the response-window state, persistent-export age, fallback state, and export-limiting suppression state explicitly under **HBC & Battery Diagnostics**.

### Charge Priority state entity

`binary_sensor.hpvc_charge_priority_active` is on only while HPVC has confirmed HBC Charge Priority is active. It can be used in dashboards and history graphs. During this state, new export-based PV reductions are blocked, although `binary_sensor.hpvc_pv_limited` may remain on temporarily while previously reduced limits are being raised.

Presentation-state semantics distinguish charging state from control influence: **Off** means Charge Priority is not applicable or no eligible charging request is active; **Requested** is reserved for unresolved usable-battery telemetry; **Waiting** means HBC requests charging and usable headroom exists, but measured charging is not yet confirmed or no currently usable PV increase exists; **Active** requires confirmed charging operation. **Active may remain displayed after usable headroom reaches zero while charging continues.** In that case `HPVC export limiting suppressed` is `No`, normal PV limiting resumes, and the accuracy model may score eligible samples again.

### Tiered battery telemetry freshness
Battery telemetry no longer relies on Home Assistant state age alone. Unknown, unavailable, non-numeric, or implausible values remain invalid. A recognized device heartbeat confirms freshness. Valid non-zero battery power with valid SOC is treated as a steady active value even when Home Assistant does not update `last_updated` while the value is unchanged. A genuinely recent AC-power update also corroborates an unchanged numeric SOC value, so a battery may remain usable when its integer SOC percentage is unchanged for more than two hours while live power telemetry continues normally. Idle or near-zero power remains strict when both channels stop updating. At a configured SOC cutoff, the AC-power state-age limit may use the bounded 30-minute cutoff-idle grace, but that extended grace alone does not extend SOC trust; only AC power inside the normal two-minute window or a real heartbeat can corroborate older SOC. Safety recovery still requires 60 seconds of healthy usable telemetry.

### Marstek cutoff-aware battery telemetry

HPVC reads `input_number.marstek_mX_charging_cutoff_capacity` and `input_number.marstek_mX_discharging_cutoff_capacity` independently for every configured battery. A battery at or above its charging cutoff is treated as full and contributes no HBC Charge Priority headroom. When a battery is at either configured cutoff and its AC power is within the HPVC deadband, the AC-power state-age allowance is extended from 2 to 30 minutes to avoid false stale warnings while the BMS intentionally rests. The cutoff condition itself is not treated as freshness evidence: AC power must still be within that 30-minute cap (or have a fresh device heartbeat). SOC normally has a 2-hour state-age allowance, but a genuinely recent AC-power update inside the normal 2-minute window (or a fresh device heartbeat) can corroborate an older unchanged numeric SOC value. The special 30-minute cutoff-idle AC-power grace by itself cannot extend SOC trust. Between cutoffs, the normal AC-power state-age allowance is 2 minutes; recent AC power and recent SOC can corroborate the slower-changing companion signal.

## Battery charge-priority diagnostics and safeguards

For each configured battery, HPVC requires numeric AC power and SOC between 0 and 100%, and HBC 4.15.0 control eligibility additionally requires `select.marstek_mN_rs485_control_mode` to be exactly `enable`. A negative AC-power value means charging. Maximum charge power must be available live or remembered from the last valid value. Invalid power/SOC excludes only that battery. If no usable battery remains, HBC Charge Priority pauses and resumes only after at least one battery has remained usable for 60 seconds.

## Control boundaries and validation

HPVC requires `Export Start < Target Export <= 0 W`, `Import Restore >= 0 W`, and each inverter minimum to be lower than its full power. Invalid static configuration or a required live-input outage switches off the HPVC master toggle and blocks writes. When configuration validity and all required inputs remain healthy for 5 continuous seconds, HPVC resumes automatically only if it was running before the fault. Any unavailable configured inverter limit therefore stops all inverter writes.

## Cooldown and deadband

Every inverter write starts the configured cooldown. No new PV write is allowed until it expires, although HPVC continues evaluating. The configured deadband is evaluated at plant/combined-total level and also defines the accepted target range for accuracy scoring. Once the combined change is meaningful, smaller proportional per-inverter shares are retained rather than discarded. HBC Charge Priority has no sub-deadband full-restore exception.

## Persistence and safeguards

User-configurable Home Assistant helpers omit `initial:` values so Home Assistant restores user changes after restart. Transient report-ready and report-generating helpers use `initial: false` to avoid stale report state. First-run defaults are applied only while `input_boolean.hpvc_defaults_applied` is off.

The v1.3.0 diagnostic price sensor is `sensor.hpvc_diag_market_export_price`. Existing installations that previously used `sensor.hpvc_diag_market_price` must update dashboard or external references and may remove the old entity from the Home Assistant entity registry after confirming the new sensor is available.

User-configurable Home PV Control helpers do not use `initial:` values in the shipped YAML, allowing Home Assistant to restore user-edited settings after a restart. The transient `hpvc_report_ready` and `hpvc_report_generating` helpers intentionally use `initial: false`, and `hpvc_report_url` uses an empty initial value, so stale report state is not restored.

A Home Assistant first-run automation applies the shipped defaults only when `input_boolean.hpvc_defaults_applied` is still off. After the defaults are applied, that flag is turned on and restored by Home Assistant on later restarts, so user changes are not overwritten.

### Persistent current-day journal

Insights, Power Control activity, Daily Target Accuracy, and the safety-critical negative-price override share one private journal at `/config/hpvc-data/runtime-history.json`. Node-RED automatically selects the supported `/homeassistant` or `/homeassistant_config` mount. Daily datasets reset on the first persistence check after local midnight; an active override is restored regardless of date.

Runtime evaluation remains gated until the journal has been read. Restored override objects are schema- and content-validated before use. Invalid or incomplete records are converted to the visible `recovery_unknown_previous` safety state rather than being accepted as a normal active or restoring override. The override record includes its phase, phase-start time, original strategy and charge goal, retry count, latest service-call step/time/error, fault state, and an entry token.

On initial entry, the entry token forms a persistence barrier: HPVC first writes the original strategy and goal to the temporary journal, atomically renames it to `runtime-history.json`, and receives a publication acknowledgement. Only a later Engine evaluation with the acknowledged token may issue `input_select.select_option` for `Charge`. Every later phase change requests another immediate atomic journal update, while the independent 10-second journal writer remains a fallback.

A non-active phase that remains unconfirmed for five minutes turns on `input_boolean.hpvc_negative_override_fault` and creates a fixed-ID persistent notification. The live helper is compared with the durable fault on every evaluation, so an HA restart cannot hide an existing fault. Explicit Home Assistant service-call errors are recorded in the override journal and report. PV remains locked at every inverter minimum while the fault is active.

If the journal is missing, invalid, or cannot prove the previous values, HPVC refuses to treat `Charge` / `batteries are full` as the originals and enters `recovery_unknown_previous`. HPVC never infers replacement values automatically. The user must restore both intended HBC selections to valid non-forced values and then turn off `input_boolean.hpvc_negative_override_fault`. That off action is the explicit acknowledgement; HPVC clears the durable recovery object only after all conditions are confirmed.

### Daily history and accuracy restoration

- Today’s Insights and Power Control activity are scoped to the local calendar day.
- The journal survives Home Assistant restarts, Node-RED restarts/deploys, and re-importing or reinstalling the HPVC flow.
- Daily Target Accuracy is restored from the same journal before normal calculations and journal writes resume.
- Yesterday’s entries and accuracy are never restored after midnight.
- Startup initialization creates the journal before the first read, preventing a clean-installation `ENOENT` message.

### Insight deduplication and grouping

Battery telemetry and HBC safety warnings are transition-based. A changing age value does not create a new warning. The same active fault remains represented by one Insight until telemetry has been continuously healthy for 60 seconds, at which point a single recovery Insight is recorded.

The dashboard and generated HTML/TXT reports use the same consecutive grouping rule. Identical activities that occur directly after one another are shown once with an occurrence count such as `×5`. Any different Insight between matching activities closes the run, so later repetitions start a separate entry.


The original HBC strategy and charge goal are persisted before the first forced HBC write. If either entity was initially unavailable, the values captured after recovery receive a new persistence token and a second acknowledged journal write before forcing can continue.

## Runtime diagnostics

`input_text.hpvc_last_targets_json` stores the compact latest-calculation JSON used by diagnostics and support reports.

### Power Control timeline

The Power Control timeline is evaluated inside the same 10-second runtime cycle as the HPVC calculation. It is an event-driven view of physical power flow, not a second control loop.

In generated HTML and TXT reports, Power Control is intentionally filtered to the periods beginning when the remembered Market/export price enters the PV-limiting zone and ending when it exits above the restore threshold (`PV limit price + price hysteresis`). The complete current-day activity journal remains available internally; only out-of-zone rows are omitted from the report.

A row is retained when HPVC is actively limiting/restoring PV or HBC is measurably charging and grid, PV, or battery power changes by at least 50 W. Inverter-limit writes, mode transitions, charging start/stop, and control-pause/recovery transitions are retained immediately. A stable active period receives a repeating heartbeat every 10 minutes. Inactive 10-second samples are not stored.

The displayed **Charge Priority + PV Limited** mode (internally retained as the legacy `Charge + Limit` classification for journal compatibility) contributes to both Charge Priority and PV-limiting duration, session, grid, and energy estimates. Fault/control-pause rows are produced when inverter-limit availability or HBC telemetry safety pauses start and end. Report energy and duration values remain estimates reconstructed from retained event intervals.

When a configured required live input fails validation, HPVC records a single **Sensor health** Insight naming the exact entity ID and the observed reason (for example `unavailable`, `unknown`, missing, or non-numeric). Repeated identical faults are de-duplicated. PV-power and inverter-limit entities intentionally tolerated during active Night Restore are excluded from these fault Insights.
## Sensor Health thresholds

Grid power, PV power, market/export price, all-in price, `sun.sun`, inverter-limit entities, and HPVC output states use availability and value validation rather than timestamp-age staleness checks, because unchanged state age is not a reliable failure signal for those entities. Battery sensors use the tiered freshness model described under HBC Charge Priority.

### Operational Insights

Transition-only Insights cover night restore start/end, HBC executing substrategy changes, tiered battery freshness reasons, taper-probe start/result/timeout, and support-report success, failure, or watchdog timeout. Routine evaluations remain silent.

## Accuracy and factor attribution

- Target accuracy is sampled every 10-second evaluation only while HPVC is enabled, inputs are valid, PV is actively limited for normal target tracking, cooldown is inactive, and neither negative-price minimum mode nor night restore is active.
- Daily averages weight each eligible sample equally.
- Diagnostic percentages are estimated contributing factors inferred from structured controller events and Insights. They are not direct physical measurements. The complete loss is distributed across the four published factors for that accuracy metric; no additional residual factor is created.
- HBC 4.15.0 supports **1–6 configured batteries**. HPVC follows that native limit for HBC Charge Priority, report, and dashboard battery diagnostics.

For battery eligibility, HPVC uses fresh live power telemetry as the authoritative signal. SOC is still required to be numerically available, but its timestamp may be older because SOC naturally changes slowly. HPVC remembers the last valid maximum charge-power setting for up to 30 minutes when that entity is temporarily unavailable; after that TTL the battery is excluded until a live maximum returns.

### Decision and response diagnostics

HPVC stores compact latest-calculation data, per-inverter calculated/requested targets, pending write verification, and current-day accuracy factors. Successful writes are confirmed internally; warnings are emitted only after an unsuperseded request exceeds the verification timeout.

### Unified HTML and TXT model

HPVC builds one internal report model and renders it as HTML and TXT. This prevents fields from appearing in only one format. Diagnostic values are read from existing helpers, configured entities, runtime debug state, inverter calculations, battery diagnostics, write-verification context, and Insights.

### Target Accuracy factors

Target Accuracy continues to use four factors:

- **Control response**: recent inverter writes, inverter minimum/maximum boundaries, threshold or deadband holding, and stable off-target operation while a limit is physically binding.
- **House load changes**: a meaningful change in estimated house load (`PV power + grid power`) that dominates the simultaneous PV movement.
- **PV availability**: meaningful PV movement while inverter limits and estimated house load remain comparatively stable.
- **Other**: only samples that cannot be explained by the three categories above.

This changes factor attribution only. It does not change the Target Accuracy score, PV control decisions, thresholds, cooldown, inverter writes, HBC, or HBC battery charge priority.

The classifier first recognizes direct controller actions. It then checks dominant estimated house-load movement and PV movement with stable inverter limits before applying passive control-response or plant-boundary explanations. The passive status `Monitoring low price` is not itself evidence of a controller response. Factor values represent shares of recorded accuracy loss, so every factor is expected to read `0.0%` when Daily Target Accuracy is `100%`. The corrected attribution model uses eligibility schema 8; older accumulated factor data is not mixed into it.

## Report generation and diagnostics
The HTML report provides floating **Collapse** and **Top** controls for long expanded Insights and Power Control sections. The Collapse control appears only while an expandable section is open; Top appears after scrolling down.
On mobile browsers, visibility is recalculated after `load`, `pageshow`, restored scroll position, viewport/orientation changes, tab visibility changes, and delayed layout completion so the controls do not require a manual refresh.

Today’s Insights use standardized node names: **Charge Priority**, **Battery capacity**, **Battery telemetry**, **HBC safety**, **HBC substrategy**, and **Taper control**. Power Control uses **Normal**, **PV Limited**, **PV Restore**, **Charge Priority**, **Charge Priority + PV Limited**, and **Paused/Fault**. Its final column is **Event**, and inverter-limit deltas are written explicitly as “reduced by” or “increased by”. Existing current-day journal entries are normalized for report display without changing timestamps or measured values.


```text
Generate report pressed
        │
        ▼
Ready OFF → Generating ON
        │
        ▼
Capture current values → build HTML → write file
        │
        ▼
Generating OFF → Ready ON → View report
        │
        ▼
Random report link → one-hour expiry → file, URL helper and Ready state cleared
```

The only generation trigger is `input_button.hpvc_export_report`. The report is not built by the 10-second evaluation, settings changes, telemetry changes, or Insights. Each generated report replaces the fixed local file `/local/hpvc/support-report.html`. The dashboard adds a cache-busting query value so a newly generated snapshot is reloaded. A deploy/startup cleanup does not generate a report; it clears temporary generation state and removes an unfinished temporary file.

A write/build error is caught by Node-RED. Both report-state helpers are turned off and Home Assistant receives a persistent error notification. Generating or viewing the report never changes HPVC settings, inverter limits, or HBC behaviour.

The report includes executive status, live inputs, decision evaluation, daily accuracy, inverter diagnostics, HBC/battery diagnostics, settings, sensor health, and all current-day Insights. The **Download report** button creates the matching TXT snapshot in the browser.

### Insight retention and source

The dashboard helpers expose the latest 20 Insights, while generated HTML and TXT reports read the complete current calendar day from the date-scoped Node-RED journal, up to 1000 entries. Helper rows are used only as a recovery fallback when no canonical current-day journal exists.

### Report semantics and parity
- The Negative All-In Override block is presented consistently in both HTML and TXT output, including saved values, persistence state, fault state, retry state, and inverter drift.

The report carries battery freshness mode and heartbeat diagnostics, labels unconfirmed telemetry as `Uncertain`, validates numeric sensor states and `sun.sun` semantics, and identifies the Insight-history source. Unreliable PV-released and net-constrained energy estimates were removed, and deadband reporting is labelled as activity-sample based.

HTML and TXT are rendered from one shared model and expose the same applicable house-level and per-battery fields, including normal battery headroom, controlled taper allowance, taper confirmation state, and per-battery taper caps.

### Report timestamps

Generated, inverter-write, and verification timestamps are formatted using Home Assistant’s configured time zone. This avoids UTC offsets when Node-RED runs in a container with a different host time zone.

### Report presentation

- **Download report** saves the current diagnostic report as a UTF-8 `.txt` file with a timestamped filename.
- The HTML report uses the same data as the downloaded TXT report.
- The report includes current status, inverter and battery tables, control settings, HBC/HBC battery charge priority information, and current-day Insights.
- Battery tables match the inverter table layout and hide entity IDs for cleaner presentation.
- HBC battery charge priority uses its own Insight type, while normal PV limiting and restore actions use `PV limit`.

## PV price hysteresis

PV limiting enters at or below the configured limiting price. Once active, it remains active until the market/export price rises above `limiting price + hysteresis`. If the market/export price becomes unavailable, HPVC follows the safe-pause policy and holds current inverter limits until the sensor recovers.

## HBC strategy integration

HBC is the sole battery-strategy controller. The Settings dashboard writes directly to `input_select.house_battery_strategy`, so every HBC option remains available to the user. HPVC does not select separate Charge, Balanced, or Expensive modes from its own price thresholds.

HPVC requires and reads `input_text.house_battery_strategy_active_sub_strategy` as the live execution state. When HBC executes `Charge` or `Charge PV`, HPVC uses that state as the strategy signal, but engages Charge Priority only inside the normal PV-limiting price zone. Negative all-in-price mode uses its own forced-grid-charging override and keeps Charge Priority off. Valid battery SOC, freshness, and known maximum charge power determine whether below-90 normal-headroom priority or 90–100% taper priority is available; measured charging power is not required to start below-90 priority. Outside both restricting contexts PV is already unrestricted, so Charge Priority remains off and HBC charges normally without HPVC intervention. Other execution states continue with normal PV control.

Battery AC-power state age is normally limited to **120 seconds**, because its sign determines whether the battery is charging. At a configured charging/discharging cutoff while power is within the idle deadband, that state-age allowance may extend to **1,800 seconds (30 minutes)**; the cutoff itself never makes stale telemetry fresh. Battery SOC has a normal **7,200-second (2-hour)** state-age allowance, but an older unchanged numeric SOC remains trusted while AC-power telemetry is genuinely fresh inside its normal 120-second window (or a real device heartbeat is fresh). The 30-minute cutoff-idle power grace cannot by itself extend SOC trust. Stale records are excluded per battery; a fresh healthy battery can still retain Charge Priority while another configured battery is stale or unavailable.

## Node-RED flow architecture

The supplied flow is split into four tabs:

| Tab | Purpose |
|---|---|
| **HPVC Inputs v1.4.0** | Reads Home Assistant state, validates configuration and live inputs, and restores persisted runtime state. |
| **HPVC Engine v1.4.0** | Evaluates prices, cooldown, Night Restore, battery eligibility, Charge Priority, and the total PV target. |
| **HPVC Outputs v1.4.0** | Distributes inverter targets, performs writes, verifies results, and publishes status, Insights, and accuracy. |
| **HPVC Reports v1.4.0** | Builds and publishes the on-demand HTML/TXT support report. |

Import the complete `hpvc_flow.json`; the tabs are designed to operate together.


## Report data timing

The report captures a fresh Home Assistant snapshot when generated. Decision, inverter-target, battery-headroom, and taper details come from the latest completed HPVC evaluation and show their timestamp and age. A notice appears when those runtime diagnostics are old or not yet available.

HTML and TXT use the same report model. Generate a new report whenever you need an up-to-date snapshot.

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)