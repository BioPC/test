# Settings

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)

The Settings tab contains entity selection, inverter setup, control thresholds, optional HBC controls, and tuning options. Operational status, graphs, accuracy, and Insights remain on the Main tab.


The Settings tab contains entity selection, inverter setup, control thresholds, optional HBC controls, and tuning options. Operational status, graphs, accuracy, and Insights remain on the Main tab.

## Entity configuration

Entity helpers are plain `input_text` fields. Paste the complete Home Assistant entity ID; HPVC reports an invalid or empty field as a configuration error instead of guessing.

### Grid power sensor

Expected sign convention:

```text
negative = export
positive = import
```

Example: `sensor.p1_meter_power`

### Market/export price sensor

This sensor is used for PV limiting decisions. It may contain either a raw market price or the true net value of exported electricity.

> **PV limiting price guidance:** Use €0.00/kWh with a net export-price sensor. For a raw market-price sensor, adjust for fees, compensation, and local rules.


### All-in import price sensor

Used for negative-price protection. When this all-in import price is zero or negative, HPVC immediately forces every configured inverter to its user-configured minimum and locks those limits until the all-in price becomes greater than zero. HPVC also stores the current HBC strategy and charge goal, sets `input_select.house_battery_strategy` to `Charge`, then sets `input_select.house_battery_strategy_charge_goal` to the exact option `batteries are full`. On exit, it restores the saved charge goal first and the saved strategy second. No all-in-price hysteresis is used.

### Total PV power sensor

Current total PV production in watts.

### HBC integration

The dashboard exposes HBC's native `input_select.house_battery_strategy` for the user and reads `input_text.house_battery_strategy_active_sub_strategy`. HPVC normally does not write or select HBC strategies. The sole exception is negative all-in-price mode, where it temporarily forces `Charge` and restores the previously selected strategy on exit. The historical **HBC Strategy Control** toggle enables or disables HPVC's read-only HBC execution tracking and Charge Priority.

## PV inverter setup

Each inverter requires:

- **Limit entity** — writable Home Assistant `number` entity used to set the inverter limit.
- **Full power** — normal maximum limit in watts.
- **Minimum power** — lowest value HPVC may request. It must be zero or positive and lower than Full power.

Invalid inverter limits block writes and produce a configuration error.

## Control relationships

HPVC requires:

- `Export Start < Target Export <= 0 W`
- `Import Restore >= 0 W`

Invalid combinations block inverter writes. A gap of roughly `75–100 W` between Export Start and Target Export is a practical starting point for smooth control.

### Min PV for control

Blocks new export-limiting actions when measured PV production is already low. It does not block Import Restore or HBC battery charge priority.

### Cooldown

Minimum time between inverter writes. The allowed range is 10–300 seconds (10 seconds to 5 minutes) in 10-second steps. The shipped and Restore Defaults value is 30 seconds. HPVC continues its 10-second evaluation cycle during cooldown but sends no new limit command.

### Deadband

Minimum requested combined plant-power change before HPVC writes a new target. Once the total change reaches the deadband, proportional per-inverter shares may be smaller than the deadband and are still retained.

## Shipped defaults

These values are safe starting points, not universal recommendations. Review them for your inverter, sensor definitions, electricity contract, and local rules.

| Setting | Shipped default |
|---|---:|
| Home PV Control Enabled | Off until setup is complete |
| Notifications | On |
| HBC integration / Charge Priority | Off |
| Settings visibility | Off |
| Number of PV Inverters | 1 |
| PV limiting price | `0.00 €/kWh` |
| PV price exit hysteresis | `0.02 €/kWh` |
| Export start | `-150 W` |
| Target export | `0 W` |
| Import restore | `150 W` |
| Min PV for control | `100 W` |
| Night restore PV threshold | `10 W` |

Night Restore enters after 120 continuous seconds at or below the configured threshold. It exits only after valid PV remains above `max(25 W, threshold + 15 W)` for 30 seconds. See [How it works](03-how-it-works.md#restore-and-recovery) for restart and offline-telemetry behavior.

| Cooldown | `30 s` |
| Deadband | `25 W` |
| PV1–PV10 full limit | `0 W` until configured |
| PV1–PV10 minimum limit | `0 W` until configured |

HPVC no longer maintains separate Charge, Balanced, or Expensive strategy helpers. The dashboard exposes HBC's own `input_select.house_battery_strategy`, including every option supplied by HBC, but HPVC leaves that select untouched during normal operation. During negative all-in-price mode only, it temporarily selects `Charge` and restores the saved value when the all-in price becomes greater than zero. HPVC reads `input_text.house_battery_strategy_active_sub_strategy` to follow the strategy HBC is actually executing. If either native HBC entity becomes unavailable, HBC-dependent Charge Priority pauses while normal PV control continues.

## HBC battery charge priority

When HBC is enabled and its active sub-strategy is `Charge` or `Charge PV`, that executing sub-strategy is the start signal for Charge Priority. If at least one usable battery has known useful headroom, HPVC suspends normal price-based PV limiting and releases PV in bounded steps; it does not wait for the battery-power sensor to show charging first. From 90% to 100%, HPVC uses controlled taper-aware increases and learns each battery's accepted power separately in five SOC bands (90–92, 92–94, 94–96, 96–98, and 98–100%).

### Exact battery entity names

For each configured battery `N`, HPVC expects:

- `sensor.marstek_mN_ac_power`
- `sensor.marstek_mN_battery_state_of_charge`
- `number.marstek_mN_max_charge_power`
- `select.marstek_mN_rs485_control_mode`

Set the battery count with `input_number.house_battery_count`. HBC 4.15.0 supports **1–6 batteries**. Each battery is evaluated independently; unavailable, full, maximum-power, or RS485-disabled batteries are excluded without blocking other eligible batteries. HPVC follows HBC's configured priority order while combining usable headroom across eligible batteries.

### Charge Priority states and state entity

The report and Insights use these presentation states:

- **Off** — Charge Priority is not applicable or cannot usefully act, including when all usable batteries are full, at maximum charging power, or have no remaining normal or controlled taper headroom.
- **Requested** — HBC requests Charge/Charge PV, but usable-battery eligibility is unresolved because required battery telemetry is unavailable or uncertain.
- **Waiting** — HBC requests `Charge` or `Charge PV` and usable headroom exists, but measured charging is not yet confirmed or no usable PV increase can currently be applied.
- **Active** — HPVC is preserving or releasing PV for confirmed battery charging headroom.

`binary_sensor.hpvc_charge_priority_active` is on only while HPVC has confirmed the **Active** state. It can be used in dashboards and history graphs. During this state, new export-based PV reductions are blocked, although `binary_sensor.hpvc_pv_limited` may remain on temporarily while previously reduced limits are being raised.

### Negative all-in-price override

This mode requires these existing HBC entities and exact options:

- `input_select.house_battery_strategy` with option `Charge`
- `input_select.house_battery_strategy_charge_goal` with option `batteries are full`

At a valid all-in price `<= 0`, HPVC stores the current values, confirms `Charge`, confirms `batteries are full`, and locks every inverter at its configured minimum. HPVC Charge Priority is off during the override. Exit occurs immediately at a valid all-in price `> 0`; no all-in-price hysteresis is applied. The saved charge goal is restored and confirmed before the saved strategy.

The override object is persisted in `/config/hpvc-data/runtime-history.json`, schema-validated, and restored before runtime evaluation. The first forced HBC write is blocked until atomic journal publication confirms the original HBC selections are durable. The helper `input_boolean.hpvc_negative_override_fault` is turned on after five minutes in an unconfirmed entry or restore phase, and HPVC creates a fixed-ID persistent notification. Durable faults are reasserted after a Home Assistant restart. PV remains locked until restoration or the explicit unknown-previous recovery workflow is confirmed.

## Restore defaults

The **Restore defaults** tile reapplies shipped configurable values after confirmation. It preserves:

- configured sensor entity IDs;
- inverter limit entity selections;
- active inverter count;
- the current HBC Strategy Control on/off state.

It does not populate installation-specific sensor or inverter entities. Verify all entities, maximum and minimum powers, inverter count, and optional HBC strategy entity afterward.




## Next steps

- [Understand the control sequence](03-how-it-works.md)
- [Troubleshoot unexpected behavior](04-troubleshooting.md)

[← README](../README.md) · [Installation](01-installation.md) · [Settings](02-configuration.md) · [How it works](03-how-it-works.md) · [Troubleshooting](04-troubleshooting.md)
