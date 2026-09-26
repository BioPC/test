from __future__ import annotations
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, get_package_version

class HPVCEntityMixin:
    _attr_has_entity_name = True
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, "hpvc")}, name="Home PV Control",
            manufacturer="HPVC", model="Home PV Control", sw_version=get_package_version(),
        )
