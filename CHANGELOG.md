# Changelog

## v1.4.0

### Control timing and defaults

- Changed runtime evaluation and the independent journal/midnight check from 15 seconds to **10 seconds**.
- Changed cooldown to **10–300 seconds** in 10-second steps.
- Changed the shipped and Restore Defaults cooldown from 60 seconds to **30 seconds**.
- Changed the shipped, first-install, and Restore Defaults Target Export from **-25 W** to **0 W**.

### Safety and sensor handling

- Fixed Night Restore safety parity between Node-RED and Home Assistant: while status is `Night Restore`, expected PV-power/inverter-limit disappearance no longer drives `hpvc_required_inputs_ready` off or auto-disables HPVC; grid and price inputs remain required.
- Prevented unavailable/unknown PV telemetry from being converted into a false Night Restore trigger: entry and recovery require a genuinely valid numeric PV state.
- Night Restore now restores inverter limits once and then suspends normal PV calculations until usable PV returns. Recovery uses hysteresis: with the default 10 W entry threshold, measured PV must remain above 25 W for 30 continuous seconds before normal PV calculations resume. During active Night Restore, PV total-power and inverter-limit availability checks are suppressed because those DTU states may disappear after sunset; other safety inputs remain monitored.
- Clarified required-input wording so `stale` is reserved for the battery telemetry freshness model rather than implied for core grid/PV/price/limit validation.
- Fixed false battery-SOC telemetry warnings during long stable periods: a fresh AC-power update now cross-confirms an unchanged numeric SOC beyond its normal two-hour state-age window, while both channels becoming stale still suspends HBC-dependent Charge Priority.
- Added stricter required-input, inverter, entity-uniqueness, and threshold validation before writes.
- Paused the complete inverter group when any configured inverter limit is invalid or unavailable.
- Added tiered battery telemetry freshness and cutoff-idle grace for full batteries whose entities stop updating.
- Paused battery-capacity transition tracking while HPVC/HBC control or HBC safety is inactive, preventing false recovery Insights across disable, startup, and redeploy.
- Prevented false `Usable HBC battery charging capacity became available again` Insights during HPVC disable/startup or Node-RED redeploy sensor settling.
- Battery capacity now uses confirmed `full`, `available`, and `unknown` states; unavailable telemetry and zero-headroom taper states no longer count as recovered capacity.
- A full-to-available transition must remain valid for 60 seconds before it is logged.
- Kept the normal unchanged-SOC state-age allowance at **two hours**, while allowing older unchanged numeric SOC to remain trusted when genuinely fresh AC-power telemetry or a real device heartbeat confirms the battery is still reporting; dual-stale telemetry still fails safety validation.
- Capped cutoff-idle AC-power freshness at **30 minutes** and SOC freshness at its independent **two-hour** limit; reaching a configured cutoff no longer acts as freshness evidence by itself.

### Negative all-in-price override

- Added a persisted, confirmed state machine for all-in price `<= 0`.
- Saved and restored the original HBC strategy and charge goal.
- Forced HBC Charge and locked each inverter to its configured minimum until all-in price becomes greater than zero.
- Added atomic persistence barriers, retries, service-error reporting, timeout faulting, drift detection, and recovery acknowledgement.
- Closed the final negative-price entry persistence race: when HBC entities recover after initially being unavailable, HPVC now republishes and acknowledges the newly captured original strategy and charge goal before any forced `Charge` write.

### HBC Charge Priority and batteries

- Charge Priority now mirrors HBC 4.15.0 per-battery RS485 eligibility: a battery contributes charging headroom only when `select.marstek_mN_rs485_control_mode` is exactly `enable`; disabled/unavailable batteries are excluded and reported.
- HBC 4.15.0 compatibility is explicitly limited to **1–6 batteries**; HPVC no longer treats 7–10 batteries as supported native-HBC configurations.
- HTML/TXT reports now expose HBC prioritized battery, effective battery order, cycle mode, priority validity, and per-battery RS485 control state for multi-battery troubleshooting.
- Replaced Hidden PV Reveal with bounded HBC Charge Priority.
- Aggregated multi-battery headroom without allowing tapering batteries to reduce normal headroom from batteries below their taper zone.
- Standardized Charge Priority states as Off, Requested, Waiting, and Active.
- Corrected no-headroom behavior so unresolved telemetry is not confused with a healthy zero-headroom condition. Charge Priority can remain **Active** while charging is confirmed; once usable headroom is exhausted, normal HPVC export limiting resumes.
- Reserved Requested for unresolved usable-battery telemetry.
- Removed the false Charge Priority unavailable warning for healthy batteries with no headroom.
- Added per-battery taper zones, learned ceilings, bounded probes, post-write confirmation, escalating lockouts, recovery requirements, and cutoff cancellation.
- Improved HBC Charge Priority coordination: HPVC releases combined battery headroom quickly, temporarily yields grid balancing to the independent HBC integration through a 15-second response window, and only falls back to PV export correction after 30 seconds of persistent unabsorbed export; the calculation remains aggregate across any configured inverter count and the **1–6 batteries supported by HBC 4.15.0**.
- Exposed response-window, persistent-export, fallback, and export-suppression states as explicit HTML/TXT report diagnostics.
- Treats both HBC `Charge` and `Charge PV` as charging requests rather than proof that the battery is charging.
- Added request/confirmation handling with **50 W** to enter confirmed Active and **25 W** to remain confirmed.
- Added a **20-second exit hold** for brief charging interruptions; the hold is refreshed only by confirmed charging and does not block normal export correction.
- Returns from the held state to **Waiting** while a charge request remains but charging is no longer confirmed, instead of flapping directly to Off.
- Prevented HBC Charge from appearing operationally active merely because all configured inverter limits are already fully released.
- Fixed **Charge Priority Active with no headroom/charging** reason consistency so an Active state with confirmed charging no longer reports charging as unconfirmed.

### PV allocation and inverter control

- Added direction-preserving proportional multi-inverter allocation with bound-aware water-filling.
- Preserved meaningful plant-level changes across per-inverter deadband fragments.
- Supported exact minimum/full boundary writes and decimal live limits.
- Coordinated export limiting, import restore, Night Restore, minimum-PV blocking, hysteresis, cooldown, and verification through one final target calculation.

### Insights, accuracy, and Power Control

- Insights now identify the exact configured required entity and failure reason when live-input validation pauses control; Night Restore-tolerated PV/limit entities remain excluded from nighttime fault noise.
- Fixed Daily Target Accuracy persistence schema parity after the Charge Priority headroom eligibility update: restore, journal persistence, and live accuracy calculation now all use schema **8**, preventing saved/current-day accuracy from being reset by the journal loop.
- Standardized Insight node names and prevented false full/capacity transition messages during startup or disabled states.
- Standardized Power Control modes and renamed the report column from Action to **Event**.
- Clarified inverter-limit increase/reduction event wording and normalized capitalization.
- Corrected Daily Target Accuracy factor attribution so passive `Monitoring low price` does not pre-empt House load changes or PV availability.
- Increased the accuracy eligibility schema to 7.
- Fixed Daily Target Accuracy so Charge Priority no longer causes a blanket exclusion: accuracy resumes when normal export limiting is active again, including when batteries are already at their charge ceilings with no usable headroom. HBC response-window, export-suppression, and Charge Priority PV-increase intervals remain excluded. The eligibility schema is now 8.

### Reports and dashboard

- Rendered HTML and TXT from one shared fresh snapshot and expanded parity validation.
- Reorganized HBC & Battery Status and added detailed override, headroom, taper, and battery diagnostics.
- Added atomic report publication, generation locks, stale-lock cleanup, watchdog recovery, and publication confirmation.
- Added floating Collapse and Top controls and fixed their mobile visibility after restored scrolling and viewport changes.
- Changed both Power Flow cards to a rolling six-hour window ending at the current time.
- Improved tooltip transparency, narrow-screen wrapping, Insight helper synchronization, and Daily Target Accuracy sample display.
- Kept the existing report sections and section order while aligning visible HTML and TXT content.
- Aligned inverter presentation in HTML with TXT and added inverter diagnostics that were previously TXT-only.
- Aligned HBC/Battery presentation so Batteries precede HBC & Battery Diagnostics in both formats.
- Added per-battery taper fields to TXT and strengthened runtime/decision warning parity.
- Split report collection into core diagnostics, history/accuracy, and shared-model stages; split HTML generation into preparation and assembly stages without changing report output semantics.

### Persistence and architecture

- Unified Insights, Power Control, Daily Target Accuracy, and override state in the persistent current-day journal.
- Corrected four cross-tab context states to use shared `global` context instead of tab-local `flow` context: the HBC response-window release timestamp, Daily Target Accuracy accumulator, Power Control midnight-reset state, and current price-limiting-zone state used by reports.
- Added current-day restore, midnight rollover, atomic publication acknowledgement, clean-install initialization, and legacy migration.
- Split the runtime into four Node-RED tabs with 55 Function nodes, 22 labelled groups, and five cross-tab Link routes.
- Split battery-capacity processing into learning-state preparation, headroom calculation, and diagnostics publication while preserving the canonical battery summary and taper-learning stores.
- Kept small pure helpers local to their consumer Function nodes for context-store portability; removed the obsolete Shared Pure Helpers pass-through subflow.
- Repaired runtime and report trigger paths after removing the empty shared-helper subflow and restored direct trigger wiring.
- Enlarged the affected Node-RED group rectangles so the refactored battery and report stages are visibly enclosed without changing node positions, IDs, wiring, or runtime logic.
- Removed the obsolete no-op `Bootstrap when journal is absent` Catch node whose scope referenced a deleted node.
- The refactored flow contains **129 Node-RED nodes** and **55 Function nodes**.

### Documentation and packaging

- Expanded the Node-RED architecture table to list all 55 Function nodes and completed the repository structure documentation.
- Losslessly recompressed large documentation PNG assets without changing their dimensions.

## v1.3.0

### Entity renaming and migration
- Renamed all active runtime entities from `pv_ems_*` to `hpvc_*`.
- Renamed diagnostic entities to `sensor.hpvc_diag_*`.
- Migrated `sensor.hpvc_diag_market_price` to `sensor.hpvc_diag_market_export_price` and added an explicit fresh-install entity ID.
- Renamed the Settings helper to `input_boolean.hpvc_config`.
- Added migration and upgrade guidance for renamed helpers, dashboards, automations, and external references.

### Latest fixes

- Prevented duplicate HBC-options pause Insights while the configured HBC entity or option list remains unavailable; only availability transitions are logged.
- Added live HBC strategy-option synchronization. HPVC refreshes the HBC option list automatically at startup, after entity changes, and once per minute. The read-only Charge strategy always prefers `Charge` when available; Balanced prefers `Dynamic` and Expensive prefers `Self-consumption`; both preserve valid selections and skip invalid writes. If the HBC entity or its options are unavailable, the user's HBC toggle remains unchanged; only HBC strategy control and battery-assisted reveal pause while normal PV control continues. When HBC is not detected and the toggle is off, periodic checks skip the option-update script while retaining automatic later detection.
- Isolated optional HBC availability from core PV validation: an unavailable strategy entity or empty option list no longer blocks PV limiting/restore or forces the user's HBC toggle off.
- Removed the repeated system-log warning from the minute option synchronizer; Node-RED now reports availability transitions without log spam.
- Removed the obsolete hard-coded HBC strategy-name assumption. The Charge-zone strategy is now automatically managed and read-only, always preferring `Charge` when available; Balanced and Expensive remain user-selectable.
- Corrected multi-battery Hidden PV Reveal documentation so eligible idle batteries are described as SOC-capped bootstrap contributors.
- Removed an unused missing-sensor accumulator from support-report generation.
- Reordered Decision evaluation so **PV currently limited** appears immediately before **Negative-price mode** in both HTML and TXT reports.
- Removed the duplicate `/docs/wiki` content and consolidated all user documentation under `/docs`.
- Reorganized installation, settings, How it works, and troubleshooting pages with consistent navigation, terminology, symptom-based troubleshooting, and current v1.3.0 behavior.
- Clarified report decision evaluation by separating the export-limiting condition from the actual current PV-limited state.
- Corrected the high-SOC Reveal documentation and source comments to match the implemented 200/100/50/25 W SOC bands.
- Enforced the documented 1,000-entry cap on the current-day Node-RED Insights log while preserving the newest entries.
- Aligned the Node-RED Export Start and Import Restore safety fallbacks with the shipped `−150 W` and `150 W` defaults.
- Cached one Home Assistant state snapshot per Node-RED evaluation for consistent reads and fewer global-context lookups.
- Restored change-only publishing for status, reason, last action, and accuracy diagnostics to reduce unnecessary Home Assistant state writes.
- Fixed `input_text.hpvc_last_action` change detection so repeated control adjustments with the same broad status still refresh when the reason or target changes.
- Removed unused diagnostic and report calculations that had no runtime effect.
- Fixed the support-report status dot so it reflects the actual HPVC enabled state.
- Removed obsolete report parsing and unused HBC diagnostic context writes.
- Fixed HTML support-report generation after the cleanup left the report header referencing the removed `reportLines` array.
- Improved Target Accuracy attribution while retaining the existing four-factor structure.

### Upgrade notes
- Replace the Home Assistant package, dashboard, and Node-RED flow together.
- Update external references that still use `pv_ems_*`, `sensor.hpvc_debug_*`, or `input_boolean.hpvc_debug`.
- Review renamed helper values before enabling HPVC.
- Generate a new report after upgrading to verify the final three-state report workflow.

### Reliability and control safety
- Fixed **Restore defaults** so it preserves the user's current HBC Strategy Control on/off state instead of forcing HBC control off.
- Separated configuration validation from temporary live-input readiness.
- Required numeric grid, price, PV, and active inverter-limit values before control can run.
- Prevented inverter writes while required live inputs are unavailable.
- Resumed control automatically after all required values recover.
- Preserved the intended priority of negative-price mode, Import Restore, export limiting, cooldown, and `sun.sun` night restore.
- Improved restart handling, validation, cooldown behavior, and safe state cleanup.
- Fixed the `rememberedMaxChargePowers is not defined` runtime error that stopped battery processing, inverter writes, and Insights.
- Flattened multi-message output batching for the HBC detection/status port so Node-RED always receives a valid one-level message array.
- Corrected Reveal Accuracy attribution to use the real `adjust` action instead of the unreachable `limit` action.
- Added report build/write error handling that resets report-state helpers and creates a persistent notification.
- Initialized report-state helpers to off after Home Assistant restart or reload, preventing stale View or Generating states.

### Charge Priority and multi-battery control
- Added per-battery Charge Priority using each battery's SOC, charging power, and known charge headroom.
- Added SOC hysteresis, adaptive high-SOC taper handling, and independent startup and telemetry recovery per battery.
- Excluded unavailable or nonnumeric battery telemetry individually without blocking remaining valid batteries.
- Kept stable numeric SOC and power values eligible even when unchanged; post-reveal response credit still requires a new power sample after a probe.
- Treated fresh battery-power telemetry as the authoritative freshness signal while allowing slower SOC updates.
- Retained the last valid maximum charge-power setting through temporary entity unavailability.
- Calculated and summed reveal allowance independently for every eligible battery.
- Added SOC-based reveal probes: 200 W at 90–94%, 100 W at 95–96%, 50 W at 97–98%, 25 W at 99%, and 0 W at 100%.
- Allowed eligible idle batteries to start charging with an SOC-capped first probe when the request exceeds the inverter deadband.
- Excluded batteries with unknown maximum charge power from Reveal headroom.
- Prevented unrestricted PV release when available headroom is small or uncertain.
- Earlier v1.3.0 behavior allowed independent inverter availability; v1.4.0 now pauses all writes when any configured inverter limit is unavailable to avoid incorrect total-plant allocation.
- Added 5 W per-inverter write suppression, post-clamp target rebalancing, and per-inverter verification diagnostics.

### Hidden PV Reveal
- Weighted Daily Reveal Accuracy by requested reveal watts, so larger probes contribute more than tiny probes.
- Based Reveal penalties on an independently estimated achievable PV increase captured before each probe; the observed response can no longer reduce its own scoring denominator.
- Excluded evaluations with stale grid/PV telemetry or unsettled inverter-limit writes from Reveal Accuracy and stability scoring.
- Made Hidden PV Reveal fully automatic and adaptive across multiple batteries.
- Improved reveal sizing from grid target, measured battery response, available headroom, and high-SOC limits.
- Added stronger response detection, pause and recovery behavior, and stability handling.
- Required two consecutive poor responses before entering a low-stability pause.
- Increased response settling time to reduce false telemetry penalties.
- Added a Reveal Insight when fresh grid telemetry does not arrive before the evaluation timeout; the skipped probe is not scored.
- Prevented additional PV from being revealed when it mainly becomes unnecessary export.
- Kept normal export limiting and Import Restore active whenever HBC Charge Priority has no useful headroom.
- Corrected Reveal Insights to show `Grid → Target` without reversed above/below wording.
- Tracked the actual Reveal pause reason so recovery Insights match the original cause.
- Changed Reveal Accuracy to measure movement toward Target Export.
- Counted overshoot only after grid power passes beyond Target Export and deadband.
- Recorded Reveal Accuracy only when `revealEffectiveness` is finite; inactive cycles remain unavailable instead of being counted as 0%.

### Price-source guidance
- Renamed the configured **Market price** display label to **Market/export price** without changing `input_text.hpvc_market_price_sensor`.
- Clarified that the same helper may contain either a raw market-price sensor or a net export-price sensor.
- Standardized the shipped PV limiting price and Node-RED fallback at `€0.00/kWh`.
- Added sensor-type-aware guidance for raw market-price and net export-price sensors.

### Diagnostics and reports
- Rebuilt the HTML and TXT support reports around one shared data model so labels, values, and ordering remain synchronized.
- Added executive status, decision-trigger evaluation, directional grid power, expanded inverter and battery diagnostics, Reveal blocking reasons, sensor health, and existing Insights.
- Added per-battery status, telemetry age, reason, raw charger headroom, and current Reveal allowance.
- Added configured inverter maximum and minimum power to both report formats.
- Displayed requested inverter target only when a write is pending; otherwise the report shows an em dash.
- Fixed inverter diagnostics so calculated targets are not reported as requested writes when no action is allowed.
- Fixed Control settings showing `unavailable` because the HTML renderer searched obsolete TXT labels.
- Fixed the Reveal diagnostics extractor for **Reveal stability score**, **Response guard**, and **PV recovery detected**.
- Fixed TXT **Response evaluation** so it matches the HTML report (`Pending` or `Inactive`).
- Fixed Daily Target Accuracy so samples are collected only when active inverter limits are physically binding; low solar availability no longer lowers accuracy.
- Added availability handling so missing accuracy samples remain unavailable while a genuine measured 0% remains numeric.
- Removed inverter entity IDs from the HTML inverter table and retained only inverter names and values.
- Made the HTML report responsive with stacked mobile cards, reflowed Sensor Health, a compact header, collapsible sections, and quick navigation.
- Kept all report diagnostics limited to existing entities, runtime state, flow context, and already-calculated HPVC values.
- Replaced background report refresh with an on-demand three-state workflow: **Generate report**, **Generating…**, and **View report**.
- Added `input_boolean.hpvc_report_ready` and `input_boolean.hpvc_report_generating`.
- Removed startup, periodic, telemetry-driven, and event-driven report generation.
- Prevented report rewrites from following the 15-second control cycle so an open report remains stable while being read.
- Added one-time no-cache revalidation when viewing a generated report so mobile browsers do not show an older cached snapshot.
- Added automatic reset to **Generate report** through a same-origin Home Assistant webhook after the report is opened.
- Kept the report workflow free of browser token handling and exposed Node-RED ports.

### Dashboard and onboarding
- Fixed the HBC Price Zones tooltip marker so it uses the selected column’s actual zone colour and displays as a rounded dot.
- Kept the original single-series HBC Price Zones presentation, including the horizontal **Now** annotation, original spacing, automatic Y-axis and per-column zone colours.
- Added a one-minute chart refresh so the custom current-time annotation does not remain stale between 15-minute HBC price updates.
- Preserved the 48-hour forecast and market-to-all-in conversion: a valid sensor-owned learned model is preferred, with the current `all-in − market` difference used as fallback while learning or relearning.
- Synchronized the dynamic price-type indicator with the graph by using the same cents/euros normalization and the same finite-coefficient validation before reporting a learned conversion.
- Kept the JavaScript generator in a literal YAML block (`|`) so line boundaries remain intact and the graph does not hang on **Loading…**.
- Improved HBC Price Zones source handling: forecast values are normalized to €/kWh, the current timestamped interval is preferred, invalid or stale sources fall back safely, and exact zero prices remain valid.
- Detected Market forecasts use a restart-safe learned all-in formula after at least 12 hours, eight distinct prices and €0.05/kWh spread; the graph stays live with the current `all-in − market` fallback while learning or relearning.
- Learning uses averaged repeated values and the four lowest/highest distinct prices, preserves exact sensor ownership, and validates monthly with three aligned pairs; graph status, Insights and support-report diagnostics remain synchronized.
- Reorganized Main, Settings, diagnostics, graphs, accuracy, and Insights.
- Renamed the **Restore recommended settings** dashboard action to **Restore defaults** without changing its behavior.
- Added guided first-install onboarding while keeping HBC optional.
- Kept Main dashboard content hidden until onboarding is complete.
- Restored native top badges in the order Status, Inverters, HBC strategy, and Batteries.
- Hid HBC strategy and battery status when HBC control is off.
- Used broadly supported icons for HBC strategy and battery status.
- Restored the native Home Assistant Power Flow history graph and omitted HBC-only series when HBC control is off.
- Simplified the Debug accuracy area to two current-day native accuracy tiles.
- Used tile-card availability behavior so missing accuracy samples show unavailable while valid 0–100% values remain visible.
- Added a compact 6-column report control with amber Generate, orange Generating, and green View states.
- Ensured tapping either the View tile body or icon opens the generated report.
- Reorganized the Node-RED canvas into labeled control-trigger, control-output, dashboard/diagnostics, and on-demand report sections without changing runtime wiring.

### Documentation
- Updated installation, configuration, How it Works, and troubleshooting documentation.
- Updated entity migration and upgrade instructions.
- Synchronized the README, changelog, release notes, and v1.3.0 release page.
- Removed obsolete references to periodic, automatic, event-driven, or token-based report generation.

## v1.2.0

> v1.1.2 was never released. All work that was temporarily staged as v1.1.2 is included in this v1.2.0 public release. Users can upgrade directly from v1.1.1 to v1.2.0.

### Final documentation and HACS metadata cleanup
- Fixed `hacs.json` so it is valid JSON instead of YAML.
- Updated configuration docs to describe first-run default seeding instead of removed `initial:` values.
- Added v1.2.0 Hidden PV Reveal, stability score, sun recovery, negative-price and final-restore behavior to the how-it-works documentation.
- Fixed troubleshooting references to removed or nonexistent entities.
- Removed the redundant `anyBelowFull` alias in the Node-RED flow.

### Cooldown debug sensor fix
- Added compact `cd` cooldown flag to the last-calculation JSON.
- Updated `binary_sensor.hpvc_cooldown_active` to read the compact cooldown flag so the dashboard Cooldown active indicator works again.

### Reveal deadband handling
- Hidden PV Reveal now applies the PV Adjustment Deadband to the total reveal request instead of each inverter share.
- Proportional inverter distribution is preserved for small reveal steps.
- Every proportional inverter change is applied once the total reveal exceeds the deadband.

### First-run defaults persistence fix
- Removed Node-RED flow-context default initialization.
- Added `input_boolean.hpvc_defaults_applied` as a Home Assistant first-run marker.
- Added a Home Assistant startup automation that applies recommended defaults only once on a new install.
- Helpers still have no `initial:` values, so user-edited values restore normally after Home Assistant restarts.

### Default seeding cleanup
- First-run default seeding now uses a 30 second cooldown to match the README recommended default.

### Adaptive Hidden PV Reveal foundation
- Added Adaptive Hidden PV Reveal for grid-following batteries.
- Reveal can restore hidden PV while PV is limited and an HBC battery is charging.
- Added mixed-inverter support so reveal works when one inverter is already closer to full than another.
- Added HBC battery-count handling using `input_number.house_battery_count`.
- Added safe fallback to one battery when `input_number.house_battery_count` is missing.
- Honored explicit `input_number.house_battery_count = 0`; fallback is used only when the helper is missing.
- Ignored missing HBC battery power sensors instead of treating them as idle `0 W` batteries.
- Added HBC max-charge awareness using `number.marstek_mX_max_charge_power`.
- Used the effective active charging-battery headroom instead of summing all battery headroom, matching HBC behavior where only one battery charges at a time.

### Automatic Adaptive Hidden PV Reveal
- Removed the old user-configurable Hidden PV Reveal step / Maximum Hidden PV Reveal Step helper before public release.
- Removed Recommended Values sensors and the Apply Recommended Values UI before public release.
- Removed the export-gap warning card, helper sensor, binary sensor, and auto-fix script before public release.
- Hidden PV Reveal is now fully automatic with no user-configured reveal power.
- Added an internal non-configurable **800 W safety cap**.
- Balanced reveal amount is calculated from:
  - effective active charging-battery headroom,
  - Target Export margin plus dynamic tolerance,
  - remaining hidden PV,
  - internal 800 W safety cap.
- Dynamic tolerance is calculated as:
  - `min(max(deadband × 2, active battery headroom × 0.25), 150 W)`.
- Export Start decides when PV limiting begins.
- Target Export decides the reveal recovery window.

### Reveal stability and solar response
- After each reveal, HPVC verifies that actual PV production increased enough.
- If raising inverter limits does not increase real PV production, HPVC pauses further reveal instead of repeatedly increasing limits when the sun cannot produce more.
- Added reveal accuracy history so one noisy sample does not immediately pause reveal.
  - good response raises the score,
  - weak response lowers it slightly,
  - poor response lowers it strongly,
  - reveal pauses below 40%.
- Added sun-recovery detection so reveal can resume when PV production rises again or export increases.

### Restore and import behavior
- Added final exact restore after Hidden PV Reveal completes.
- If one inverter is still slightly below its configured full limit, HPVC sends one final per-inverter restore command.
- Fixed import recalculation so high grid import no longer lowers PV limits when all inverters are already restored to full.
- Kept the normal PV Adjustment Deadband for regular control decisions.

### Diagnostics and dashboard
- Added improved Insights for reveal pause, resume and completion decisions.
- Pause Insights now include measured PV response, required PV response and stability score.
- Added compact diagnostics JSON fields for reveal diagnostics.
- Kept diagnostics JSON compact so it fits the Home Assistant input-text length limit.

### Runtime and packaging fixes
- Fixed Node-RED function scope issues so debug fields cannot crash the function node.

## v1.1.1

- Maintenance release based on v1.1.0.
- Updated `hpvc_config.yaml`, `hpvc_dashboard.yaml`, and `node-red/hpvc_flow.json` with the latest uploaded fixes.
- Keeps the v1.1.x helper names compatible while improving input-text based entity configuration.
- Changed recommended `initial:` values to all Home Assistant helpers.
- Minor dashboard fixes and cleanup.
- Added `input_text.hpvc_battery_strategy_entity` to the settings-changed watch list so editing the HBC strategy entity re-runs the flow immediately instead of waiting up to 15s.
- Added explicit validation for a negative inverter minimum power (`low_limit`); it is now reported as a configuration error instead of silently dropping the inverter from control.
- Aligned `hpvc_config.yaml` default values, the documentation's default-values table, and the `hacs.json` domain list; added the required `binary_sensor` domain while retaining `automation` for the included Home Assistant automations.

## v1.1.0

> v1.0.7 was never released. All planned v1.0.7 work has been merged into this v1.1.0 release. Users can upgrade directly from v1.0.6 to v1.1.0.

### Timeline of changes

#### Debug and dashboard polish
- Expanded Insights from 10 to 20 items.
- Removed repetitive cooldown-finished entries from Insights so the history stays focused on useful events.
- Fixed cooldown insight time formatting to use 24-hour `HH:MM:SS` format.
- Added a 48-hour HBC strategy price graph using all-in prices in €/kWh.
- Added graph zone colors based on the configured Charge and Expensive price thresholds.
- Added a compact price-zone legend for Charge, Balanced and Expensive HBC strategy zones.
- Updated dashboard text for Hidden PV Reveal and v1.1.0 behavior.

#### Cooldown and PV recalculation behavior
- Allowed PV decisions immediately after cooldown expires instead of blocking the first post-cooldown evaluation.
- Fixed hidden-PV reveal so heavy grid import uses the normal fast import-recalculation path.
- Fixed mixed-inverter reveal behavior by only using Hidden PV Reveal when all configured inverters are below full output.
- Fixed PV recalculation to avoid losing recovery speed during significant import while PV is limited.

#### HBC strategy selection
- Improved HBC strategy notification wording during price hysteresis so entry and exit threshold messages are factually correct.
- Kept HBC strategy control optional; HPVC still works as a standalone PV controller when HBC is unavailable.

#### Hidden PV Reveal
- Added Hidden PV Reveal for grid-following batteries: when PV is limited and export is small, HPVC can gradually reveal extra PV so an HBC battery can see more available solar power.
- Added configurable Hidden PV Reveal step in the PV Export Control section.
- Set Hidden PV Reveal step range to 50–800 W with 100 W default.
- Improved the reveal allocator so small reveal steps are preserved across multi-inverter setups instead of being lost to per-inverter deadband.
- Added HBC battery-charging gate: reveal only runs when HBC strategy control is enabled and at least one active HBC battery is charging.
- Added HBC battery-count handling using `input_number.house_battery_count`.
- Added safe fallback to one battery when `input_number.house_battery_count` is missing.
- Honored an explicit `input_number.house_battery_count = 0`; fallback to one battery is used only when the helper is missing.
- Ignored missing HBC battery power sensors instead of treating them as idle `0 W` batteries.
- Added HBC Batteries max-charge awareness using `number.marstek_mX_max_charge_power`.
- Paused Hidden PV Reveal when active batteries are already at or near their configured maximum charge power.
- Added one-time pause and resume Insights for Hidden PV Reveal battery-charge availability.
- Added one-time completion Insight when Hidden PV Reveal fully restores PV output.
- Added clear reason text when Hidden PV Reveal is active but the calculated increase is below the PV deadband.
- Stopped repeat logging of Hidden PV Reveal pause messages; pause/resume/completion events now log only on state changes.

#### Startup and diagnostics
- Added a startup Insight when Home Assistant inputs finish restoring and HPVC resumes control.
- Added compact diagnostics JSON fields for battery power, battery charging state, charge headroom and max-charge state.
- Added compact `at_max_chg` diagnostics JSON field for max-charge reveal diagnostics.
- Fixed Hidden PV Reveal scope so startup or waiting states cannot throw `revealHiddenPv is not defined`.

#### Internal cleanup
- Removed unused battery detail variables from the Node-RED flow.
- Removed unused active battery summary string building.
- Cleaned and reorganized release documentation so all unreleased v1.0.7 work is documented under v1.1.0.

## v1.0.6

- Updated default threshold values for new installations.
- Removed unused legacy configuration components.
- Reduced unnecessary background processing.
- Internal cleanup and maintenance improvements.
- Updated badges.
- Fixed insight log source labels.
- Aligned expensive price fallback.
- Minor internal logic cleanup.
- Improved entity picker persistence after Home Assistant restart or reload.
- Replaced obsolete inverter count template reference with the existing inverter count helper.
- Removed phantom battery picker dropdown refresh calls.
- Removed redundant PV adjust guard conditions.
- Removed forced startup defaults from user-configurable helpers so user settings persist after restart or reload.
- Added startup restore wait to avoid temporary missing-entity warnings while Home Assistant inputs restore.

## v1.0.5

- Fixed configuration validation for missing entities.
- Fixed negative-price mode forcing PV minimum output.
- Fixed PV minimum insight logging.
- Fixed export threshold fallback consistency.
- Improved entity ID compatibility after rebranding.
- Dashboard renamed to "Home PV Control".
- Added documentation that Home PV Control is optimized for dynamic energy contracts.
- Improved diagnostics and configuration feedback.
- Removed unused functions and variables.
- Removed duplicate example JSON file.
- Simplified internal logic and improved readability.

## v1.0.4

- Fixed template entity ID mismatch on clean Home Assistant installs.
- Fixed missing dashboard entities after rebrand.

## v1.0.3

- Rebranded from HPVC to Home PV Control.
- Updated banner and logo.
- Improved HBC integration.
- Dashboard improvements and cleanup.

## v1.0.2

- UI improvements.
- Dashboard fixes.
- Stability improvements.

## v1.0.1

- Dropdown persistence fixes.
- Configurable cooldown.
- Faster evaluation cycle.
- HBC battery power support.

## v1.0.0

- Initial public release.
