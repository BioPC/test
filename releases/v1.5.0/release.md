# Home PV Control v1.5.0

Generic inverter adapter release.

Adds per-inverter Number-entity and Action/service control methods, optional sequential stop-on-failure pre/post action sequences, dynamic target-field injection, and optional readback verification while preserving the existing Watt-based control engine.


Action/service failures clear the affected inverter command cache so HPVC can retry instead of silently treating a failed service call as applied. Adapter configuration changes invalidate cached command state and force resynchronization. Watt and Percent command steps are quantized before change detection. Pre/main/post calls execute sequentially and stop on the first failed Home Assistant action; use a Home Assistant script when a device requires timed waits between steps or a payload/sequence exceeds the 255-character helper limit.
Final release audit also fixes support-report entity validation, Settings binary-sensor helper domains, cross-tab diagnostic context scope, and inverter target diagnostics.

Final regression fixes also align pending-write confirmation with per-inverter `pvN` control keys and allow the Daily Control Accuracy physical-event detector to use Action/service adapters when a real readback entity is available. Action/service adapters without real readback remain excluded from physical attribution by design; headline accuracy and target-tracking continue normally.

Daily Control Accuracy command-application attribution now resolves pending writes through each inverter's `pvN` control key and compares the requested Watt target against the inverter's Watt-normalized real readback. This restores Control attribution for both Number-entity adapters and Percent adapters while continuing to reject command-cache-only state as physical evidence.
