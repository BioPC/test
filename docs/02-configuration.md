# Configuration

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

### Market / Export Price Sensor

Used for PV limiting decisions.

Usually this should be the market price without taxes.

### All-in Import Price Sensor

Used only for optional HBC strategy switching.

### Total PV Power Sensor

Total current PV production in watts.

### HBC Strategy Entity

Usually:

```text
input_select.house_battery_strategy
```

Disable `Home PV Control Controls HBC Strategy` if you only want PV limiting.

## PV inverter helpers

Each inverter needs:

```json
{
  "name": "PV1",
  "limit_entity": "number.inverter1_limit",
  "full_power": 2000,
  "minimum_power": 100,
  "enabled": true
}
```

### Fields

`name`  
Friendly name shown in debug output.

`limit_entity`  
Writable Home Assistant `number` entity used to set the inverter power limit.

`full_power`  
Normal maximum/full limit in watts.

`minimum_power`  
Lowest limit Home PV Control may set for this inverter.

`enabled`  
Set to `false` to temporarily ignore this inverter.

## Recommended values

| Setting | Recommended |
|---|---:|
| PV Limiting Price | 0.00 €/kWh |
| Start Limiting Export | -300 W |
| Target Export | -25 W |
| Import Recalculation | 200 W |
| Minimum PV Power | 100 W |
| Night Restore | 10 W |
| Minimum PV Change | 1 min |
| Deadband | 25 W |

## Notes

The Node-RED flow reads the configured entity IDs from helpers. The two wake-up event nodes still default to common sensor names. If you use different grid/market sensors, either edit those trigger nodes or rely on the 1-minute timer.


Note: Home Assistant input_text has a 255-character limit. Use compact inverter keys: `n` name, `e` limit entity, `f` full power, `m` minimum power, `en` enabled. The Node-RED flow also still accepts the long key names for imported JSON.


## Entity dropdowns

The grid power, price, PV power and HBC strategy helpers are dropdowns, not text fields. After importing the Node-RED flow, deploy it once or click **Refresh entity dropdowns**. Node-RED will populate the dropdowns from Home Assistant entities so you can select instead of typing.
