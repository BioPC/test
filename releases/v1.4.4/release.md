# Home PV Control v1.4.4

Home PV Control v1.4.4 is a documentation and compatibility-classification maintenance release. The v1.4.3 control policy and Watt/Percent inverter-write behavior are intentionally unchanged.

## Inverter compatibility documentation

- Added `docs/05-inverter-compatibility.md`.
- Added four compatibility statuses: **Confirmed direct**, **Compatible by design**, **Bridge / action required**, and **Not confirmed / not suitable**.
- Added a conservative brand/integration matrix explaining why each integration is placed in its status.
- Clarified that HPVC compatibility depends on the Home Assistant integration/entity, not only the inverter brand.
- Clarified that a site/grid export-limit entity is not automatically equivalent to the inverter active-power limit HPVC expects.
- Linked the compatibility guide from the README, configuration guide and troubleshooting guide.

## Control behavior

No intentional PV-control, HBC, safety, threshold, rate-limiter, Watt/Percent conversion or write-verification behavior changes are included in v1.4.4.

## Upgrade

Replace the Home Assistant package, dashboard and Node-RED flow from the same v1.4.4 package so displayed/report version labels remain aligned. Existing v1.4.3 settings remain compatible.
