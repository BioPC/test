# Home PV Control v1.4.0

Home PV Control v1.4.0 replaces Hidden PV Reveal with bounded HBC Charge Priority, introduces a modular four-tab Node-RED architecture, strengthens sensor and battery safety, and expands persistent diagnostics and reporting.

## Contents

- [Control timing and defaults](#control-timing-and-defaults)
- [Safety and recovery](#safety-and-recovery)
- [HBC Charge Priority](#hbc-charge-priority)
- [Battery telemetry and taper control](#battery-telemetry-and-taper-control)
- [PV allocation and inverter control](#pv-allocation-and-inverter-control)
- [Insights, accuracy, and Power Control](#insights-accuracy-and-power-control)
- [Reports and dashboard](#reports-and-dashboard)
- [Persistence and architecture](#persistence-and-architecture)
- [Upgrade instructions](#upgrade-instructions)
- [Compatibility](#compatibility)

## Control timing and defaults

- Runtime evaluation now runs every **10 seconds**.
- The independent runtime-history persistence and midnight check also run every **10 seconds**.
- Cooldown accepts **10–300 seconds** in 10-second steps.
- The shipped default and Restore Defaults value is **30 seconds**.
- The shipped, first-install, and Restore Defaults Target Export is **0 W**.
- Normal market/export-price limiting retains the configured hysteresis, while the negative all-in-price override uses no hysteresis and exits only when the all-in price becomes greater than zero.

## Safety and recovery

- During Night Restore, expected PV-power and inverter-limit disappearance no longer marks required inputs unavailable or auto-disables HPVC; grid and price inputs remain required.
- Night Restore entry and recovery require genuinely valid numeric PV telemetry, so `unknown` or `unavailable` PV cannot be interpreted as zero production.
- Night Restore recovery uses hysteresis: after the 120-second low-PV entry condition, normal PV calculations resume only after PV remains above `max(25 W, entry threshold + 15 W)` for 30 continuous seconds.
- Required-input wording now reserves `stale` for the battery telemetry freshness model; core grid/PV/price/limit inputs are described by their actual validity state.
- Fixed false battery-SOC telemetry warnings during long stable periods: a fresh AC-power update now cross-confirms an unchanged numeric SOC beyond its normal two-hour state-age window, while both channels becoming stale still suspends HBC-dependent Charge Priority.

- Required numeric sensors, inverter entities, entity uniqueness, and threshold relationships are validated before any write.
- A missing or invalid configured inverter pauses the complete inverter group instead of controlling only a partial plant.
- Automatic fault recovery requires continuously healthy inputs before writes resume.
- HBC-dependent Charge Priority is suspended when battery telemetry is uncertain, while normal PV control can continue.
- Capacity recovery tracking is paused while HPVC or HBC control is disabled, or while HBC safety is paused/recovering. This prevents long disabled periods from generating false **charging capacity became available again** Insights.
- A genuine recovery from a confirmed full state requires real charging headroom to remain available for **60 seconds**.
- Unchanged integer battery SOC values keep the normal **two-hour** state-age allowance, and can remain trusted beyond it while genuinely fresh AC-power telemetry or a real device heartbeat confirms the battery is still reporting; this avoids false stale-SOC classification during long stable periods without masking dual-stale telemetry.

### Negative all-in-price override

- At a valid all-in price `<= 0`, HPVC persists the original HBC strategy and charge goal, confirms HBC `Charge`, and locks each inverter to its configured minimum.
- The override remains active until the all-in price is valid and `> 0`.
- Saved charge goal and strategy are restored and confirmed in sequence before normal control resumes.
- Override state is persisted in `hpvc-data/runtime-history.json` and protected by atomic publication barriers.
- Service-call errors, retry state, timeout faults, drift, and recovery acknowledgement are exposed in diagnostics and reports.

## HBC Charge Priority

- Charge Priority now mirrors HBC 4.15.0 per-battery RS485 eligibility: a battery contributes charging headroom only when `select.marstek_mN_rs485_control_mode` is exactly `enable`; disabled/unavailable batteries are excluded and reported.
- HBC 4.15.0 compatibility is explicitly limited to **1–6 batteries**; HPVC no longer treats 7–10 batteries as supported native-HBC configurations.
- HTML/TXT reports now expose HBC prioritized battery, effective battery order, cycle mode, priority validity, and per-battery RS485 control state for multi-battery troubleshooting.

- Charge Priority follows HBC's executing `Charge` or `Charge PV` sub-strategy only in a PV-restricting context.
- It releases PV only within verified battery headroom, inverter capacity, grid conditions, step limits, and cooldown/deadband rules.
- Multi-battery capacity is aggregated without allowing a tapering battery to reduce the normal headroom of another battery below its taper zone.
- Charge Priority state meanings are now consistent:
  - **Off** — not applicable, disabled, outside the limiting price zone, full, maximum-power limited, taper-saturated, or no confirmed headroom.
  - **Requested** — HBC requests charging, but usable-battery eligibility is unresolved because telemetry is unavailable or uncertain.
  - **Waiting** — HBC requests `Charge` or `Charge PV` and usable headroom exists, but measured charging is not yet confirmed or no usable PV increase can currently be applied.
  - **Active** — measured battery charging is confirmed and Charge Priority is preserving or increasing PV within verified capacity.
- Healthy batteries with no remaining headroom no longer create a false **Charge Priority unavailable** warning.
- HPVC now treats HBC as the fast grid-balancing controller during Charge Priority: after an upward PV release, a **15-second response window** suppresses opposite export corrections, while a **30-second persistent-export fallback** restores PV limiting when HBC cannot absorb the surplus.
- HTML and TXT reports expose the internal Charge Priority state, 50 W enter threshold, 25 W remain threshold, measured charge power, charging confirmation, response-window state, persistent-export age, fallback state, and export-limiting suppression state.
- Both HBC `Charge` and `Charge PV` are treated as requests, not automatic proof of charging.
- Charge Priority enters confirmed **Active** at **50 W** measured charging and remains confirmed down to **25 W**.
- A **20-second exit hold** prevents brief charging interruptions from causing Active/Off flapping; only confirmed charging refreshes the hold, and normal HPVC export correction remains available during it.
- When charging becomes unconfirmed while the request remains, Charge Priority returns to **Waiting** rather than remaining falsely Active.
- An all-inverter-full condition alone no longer makes HBC Charge appear operationally active.
- Fixed **Charge Priority Active with no headroom/charging** reason consistency: confirmed Active charging is no longer described as unconfirmed.

## Battery telemetry and taper control

- Tiered telemetry freshness uses heartbeat, active-power, SOC-update, cross-sensor, and configured-cutoff idle evidence.
- Full batteries can remain valid through cutoff-idle grace even when their power and SOC entities stop updating.
- Batteries below 90% use normal charge-power headroom.
- Batteries in taper zones use per-battery learned SOC-band ceilings, bounded step caps, and post-write confirmation.
- Initial taper caps are 15% of configured maximum charge power at 90–94%, 10% at 94–98%, and 5% at 98–100%.
- Failed probes remove unconfirmed allowance and apply escalating lockouts; repeated failures require demonstrated charging-power recovery before probing resumes.
- Pending probes are cancelled when the battery reaches its configured charging cutoff.
- Taper Insights now explain when a battery response was observed but rejected because grid export worsened.

## PV allocation and inverter control

- A direction-preserving proportional allocator distributes the final plant target across multiple inverters and redistributes only at configured bounds.
- Meaningful plant-level changes are preserved even when proportional per-inverter fragments would fall below individual write deadbands.
- Exact minimum and full-power boundary writes are supported.
- Integer and decimal live inverter limits are handled without reversing the requested direction.
- Every real inverter write starts the shared cooldown.
- Export limiting, import restore, Night Restore, minimum-PV blocking, price hysteresis, and write verification remain coordinated through one final target calculation.

## Insights, accuracy, and Power Control

### Today’s Insights

- Required-input fault Insights name the exact configured entity and validation reason; expected Night Restore PV/limit telemetry loss remains excluded.
- Insight node names are standardized as **Charge Priority**, **Battery capacity**, **Battery telemetry**, **HBC safety**, **HBC substrategy**, and **Taper control**.
- Full/no-headroom states use informational capacity messages rather than unavailable warnings.
- Temporary unknown telemetry during startup, disable, redeploy, or safety recovery does not create false capacity transitions.
- Consecutive identical entries use one normalized grouping rule and display an occurrence count.
- Existing current-day rows are normalized for report display without changing their timestamps or factual measurements.

### Daily Target Accuracy

- Factor values represent shares of accuracy loss, not event frequency; therefore all factors correctly remain `0.0%` when accuracy is 100%.
- Passive `Monitoring low price` no longer forces non-perfect samples into **Control response**.
- Attribution order now distinguishes direct control response, dominant house-load changes, PV-availability movement, passive controller/plant holds, and Other.
- Accuracy eligibility schema **7** prevents old and corrected factor data from being mixed.
- Factor entities remain unavailable until valid diagnostics have been collected or restored.

### Power Control activity

- Modes are standardized as **Normal**, **PV Limited**, **PV Restore**, **Charge Priority**, **Charge Priority + PV Limited**, and **Paused/Fault**.
- The report column is named **Event** because it can contain a control write, state transition, or telemetry observation.
- Ambiguous events such as `Inverter limit -533 W` are rendered as `Inverter limit reduced by 533 W` or `increased by ...`.
- Power Control report activity is limited to the remembered market/export PV-limiting zone.
- Mode definitions remain in documentation and TXT output.

## Reports and dashboard

### Reports

- HTML and TXT are rendered from one fresh snapshot and one shared report model.
- HBC & Battery Status is ordered as Current HBC State, Negative All-In Override, Charge Priority Capacity, Batteries, and Diagnostics.
- TXT/HTML parity covers all required override, headroom, taper, battery, and diagnostics fields.
- Report publication uses an atomic temporary-file rename, generation lock, scoped failure cleanup, and watchdog recovery.
- Floating **Collapse** and **Top** controls were added to HTML.
- Mobile navigation visibility is re-evaluated after page restoration, restored scrolling, orientation/viewport changes, and returning to the tab.
- Existing report sections and section order are unchanged, while HTML and TXT now present the same inverter and HBC/Battery information in the same subsection order.
- HTML now includes the inverter diagnostics that were previously TXT-only; TXT includes the per-battery taper fields already visible in HTML.
- Runtime/decision warning parity and Charge Priority diagnostic parity were strengthened.
- Report collection is staged as core diagnostics → history/accuracy → shared report model, with HTML preparation and assembly separated for maintainability.

### Dashboard

- Both Power Flow cards use a true rolling **6-hour** window ending at the current time.
- Charge Priority history uses `binary_sensor.hpvc_charge_priority_active`.
- Price and Power Flow tooltips use theme-aware translucent backgrounds.
- Dashboard Insights merge restored current-day history with live history, publish newest first, clear unused helpers, and wrap safely on narrow screens.
- Daily Target Accuracy shows its valid sample count.

## Persistence and architecture

- Insights, Power Control activity, Daily Target Accuracy, and negative-override state share the private current-day runtime journal.
- Cross-tab runtime state that must be shared between Inputs, Engine, Outputs, and Reports now uses Node-RED `global` context; this restores the 15-second HBC response window, same-day Daily Target Accuracy restart continuity, the midnight Power Control reset, and open price-zone interval reconstruction in reports.
- Current-day history resets after local midnight and restores only matching-date data.
- Atomic journal publication is acknowledged before dependent runtime actions continue.
- Clean installations initialize storage before reading, avoiding startup `ENOENT` errors.
- Runtime calculations and journal writes remain gated until current-day restoration completes.
- The Node-RED flow contains **4 tabs**, **55 Function nodes**, **22 labelled groups**, and **5 cross-tab Link routes**.
- Battery-capacity processing is staged as learning-state preparation → headroom calculation → diagnostics publication.
- Small pure helpers remain local to their consumer Function nodes for Node-RED context-store portability.
- The obsolete no-op journal-bootstrap Catch node with a dangling scope reference was removed.
- The obsolete empty Shared Pure Helpers pass-through subflow was removed, and runtime/report triggers are wired directly to their real processing stages.
- Refactored report and battery nodes remain visually enclosed in their labelled Node-RED groups; this layout cleanup changes no node positions, IDs, wiring, or runtime logic.


## Upgrade instructions

1. Back up the current Home Assistant package, dashboard, Node-RED flow, and `hpvc-data` runtime journal.
2. Replace the Home Assistant package with `home assistant/hpvc_config.yaml`.
3. Replace the complete HPVC Node-RED flow with `node-red/hpvc_flow.json`.
4. Replace or merge `home assistant/hpvc_dashboard.yaml`.
5. Restart Home Assistant after package changes and deploy Node-RED.
6. Verify all configured entities and inverter limits.
7. Generate a support report and confirm TXT/HTML parity succeeds.

Keep the Home Assistant package, Node-RED flow, dashboard, and documentation on the same release version.

## Compatibility

- Home Assistant with package support.
- Node-RED add-on with Home Assistant nodes.
- Writable inverter `number.*` entities.
- Optional Home Battery Control integration; HBC 4.15.0 natively supports **1–6 batteries**.
- Dashboard ApexCharts configuration targets `custom:apexcharts-card` **2.2.3**.
