# Home PV Control v1.5.0

v1.5.0 expands inverter compatibility with a generic per-inverter adapter layer.

## Highlights

- Fixed support-report inverter health validation for both `number.*` and sensor/readback entities.
- Fixed Settings conditional helpers so inverter-slot and range-warning cards use the expected `binary_sensor.*` domains.
- Fixed cross-stage runtime/diagnostic context handling and inverter target diagnostics.

- New **Control method: Number entity / Action/service** per inverter.
- Generic action/service writes with dynamic Watt/Percent target injection.
- Optional fixed data, Home Assistant target data, sequential stop-on-failure pre/post actions, command step and refresh/heartbeat interval.
- Adapter configuration changes force a safe resynchronization, and command-step quantization now applies in both Watts and Percent modes.
- Failed Action/service calls invalidate the optimistic command cache and are retried on a later eligible cycle instead of being silently treated as applied.
- Optional numeric readback entity for write verification.
- Initial Action/service synchronization after a fresh command cache, plus optional heartbeat refresh that bypasses stable-cycle skipping when due.
- Existing writable-number integrations remain fully supported and are still the default.
- HPVC continues to calculate and distribute all control targets internally in Watts.

See `docs/02-configuration.md` and `docs/05-inverter-compatibility.md`.


### Final audit fixes

- Fixed control-key write-settle confirmation for Number entity and Action/service adapters.
- Physical Daily Control Accuracy attribution now supports Action/service adapters when a real readback entity is available; adapters without readback remain excluded from physical attribution while headline accuracy continues normally.

> **Upgrade note — sensor → binary_sensor migration:** v1.5.0 corrects several HPVC helper domains (`hpvc_show_inverter_slot_2`…`_10`, inverter limit-range warnings and the export-threshold warning) from `sensor.*` to `binary_sensor.*`. If an earlier installed package created the old `sensor.*` registry entries, Home Assistant may leave those old entities orphaned. They can be removed from the entity registry after confirming the new `binary_sensor.*` entities are present.

- Daily Control Accuracy command attribution now resolves pending inverter writes by `pvN` control key and compares them against Watt-normalized real readback, fixing missed Control attribution after confirmed writes.
