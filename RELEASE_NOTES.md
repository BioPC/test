# Home PV Control v1.3.0 — Release Notes

## Entity migration
- Target Accuracy keeps its four existing factors—Control response, House load changes, PV availability, and Other—but now classifies expected control holds and inverter-response effects under Control response. House-load movement is estimated independently from PV movement, leaving Other as a true fallback.
- Renamed all runtime entities to the `hpvc_*` prefix.
- Renamed diagnostic entities to `sensor.hpvc_diag_*`.
- Renamed the Settings helper to `input_boolean.hpvc_config`.
- Existing installations must update external references.
- Review migrated helper values before enabling HPVC.

## Charge Priority
- Batteries are evaluated independently using SOC, charging power, telemetry validity, and charge headroom.
- One unavailable or tapering battery no longer blocks another.
- Stable telemetry remains usable during unchanged values.
- Eligible idle batteries can start charging automatically.
- Maximum charge power is retained through temporary telemetry loss.
- Inverters are controlled independently with post-clamp balancing and write verification.

## Hidden PV Reveal
- Daily Reveal Accuracy is watt-weighted, so larger probes count more than tiny probes.
- Expected response is capped by an independent pre-reveal PV-availability estimate, so a weak observed response cannot make itself appear fully successful.
- Stale grid/PV telemetry and unsettled inverter-limit writes are excluded from scoring.
- Reveal allowance is summed across all eligible HBC batteries.
- Below **90% SOC**, allowance follows available charger headroom.
- Probe limits are **200 W (90–94%)**, **100 W (95–96%)**, **50 W (97–98%)**, **25 W (99%)**, and **0 W (100%)**.
- Every probe is verified before another reveal is allowed.
- Final reveal is limited by Target Export margin, remaining hidden PV, and the internal **800 W** safety cap.
- Batteries are managed independently; tapering one battery does not pause the others.
- Stale grid telemetry now creates a Reveal Insight instead of affecting Reveal Accuracy.

## Reliability and safety
- HPVC now validates required inputs before controlling inverter limits.
- Missing telemetry pauses control safely until recovery.
- Improved restart handling, cooldown logic, validation, and `sun.sun` night restore.
- Fixed `rememberedMaxChargePowers is not defined`.
- Fixed HBC status output batching.
- Fixed Reveal Accuracy attribution.
- Report failures now reset report helpers and create a persistent notification.

## Diagnostics and reports
- HTML and TXT reports now use the same data model.
- Expanded inverter, battery, Reveal, and Sensor Health diagnostics.
- Improved report accuracy and consistency.
- Target Accuracy now samples only during active limiting.
- Genuine **0%** accuracy remains valid.
- Reports are generated only on demand.
- Report workflow is **Generate → Generating → View**.

## Dashboard
- Reorganized Main, Settings, Diagnostics, Accuracy, Graphs, and Insights.
- Renamed **Restore recommended settings** to **Restore defaults**.
- Improved badge layout and conditional HBC visibility.
- Added native history graphs and current-day accuracy tiles.
- Improved report tile workflow and layout.
- Reorganized the Node-RED canvas without changing functionality.

## Documentation
- Updated installation, configuration, operation, troubleshooting, migration, and upgrade guides.
- Removed obsolete references to automatic report generation.
- Standardized all v1.3.0 documentation.

## Upgrade notes
- Replace `home assistant/hpvc_config.yaml`.
- Replace `home assistant/hpvc_dashboard.yaml`.
- Re-import `node-red/hpvc_flow.json`.
- Update automations, dashboards, scripts, and external references using old entity names.
- Review renamed helper values before enabling HPVC.
- Generate and open a new report to verify the three-state report workflow.
