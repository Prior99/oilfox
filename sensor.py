"""Oilfox metering."""

from pickle import TRUE
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, VOLUME_LITERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .oilfox import OilfoxDevice, OilfoxHub


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""\
    
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]
    
    await coordinator.hub.authenticate(config.data["email"], config.data["password"]);

    devices = await coordinator.hub.list_devices()

    entities = []

    for device in devices:
        entities.append(OilfoxSensorFillLevelQuantity(coordinator, device))
        entities.append(OilfoxSensorFillLevelPercentage(coordinator, device))
        entities.append(OilfoxSensorBatteryPercentage(coordinator, device))
        entities.append(OilfoxSensorNextMeasurement(coordinator, device))
        entities.append(OilfoxSensorLastMeasurement(coordinator, device))
        entities.append(OilfoxSensorError(coordinator, device))
    

    async_add_entities(entities, update_before_add=True)


class OilfoxSensor(CoordinatorEntity, SensorEntity):
    hub: OilfoxHub
    device: OilfoxDevice

    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator)

        self.device = device

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.device.hwid)},
            "name": f"Oilfox {self.device.hwid}",
            "manufacturer": "FoxInsights",
        }

    def _update_device_from_coordinator(self) -> None:
        for device in self.coordinator.data:
            if device.hwid == self.device.hwid:
                self.device = device
                return

class OilfoxSensorFillLevelQuantity(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Fill Level Quantity"
        self._attr_unique_id = f"{self.device.hwid}_fill_level_quantity"
        self._attr_native_unit_of_measurement = self.device.quantityUnit
        self._attr_device_class = SensorDeviceClass.VOLUME if self.device.quantityUnit == VOLUME_LITERS else SensorDeviceClass.WEIGHT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:barrel"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.fillLevelQuantity

class OilfoxSensorFillLevelPercentage(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Fill Level Percentage"
        self._attr_unique_id = f"{self.device.hwid}_fill_level_percentage"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.VOLUME if self.device.quantityUnit == VOLUME_LITERS else SensorDeviceClass.WEIGHT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.fillLevelPercent

class OilfoxSensorBatteryPercentage(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Battery Percentage"
        self._attr_unique_id = f"{self.device.hwid}_battery_percentage"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.batteryLevel

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:battery-unknown"
        
        self._update_device_from_coordinator()

        if self.device.batteryLevel == 100:
            return "mdi:battery"

        if self.device.batteryLevel == 10:
            return "mdi:battery-alert-variant-outline"

        return f"mdi:battery-{self.device.batteryLevel}"

class OilfoxSensorLastMeasurement(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Last Measurement"
        self._attr_unique_id = f"{self.device.hwid}_last_measurement"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:clock"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.currentMeteringAt

class OilfoxSensorNextMeasurement(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Next Measurement"
        self._attr_unique_id = f"{self.device.hwid}_next_measurement"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:clock"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.nextMeteringAt

class OilfoxSensorError(OilfoxSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, device: OilfoxDevice) -> None:
        super().__init__(coordinator, device)

        self._attr_name = f"Oilfox {self.device.hwid} Error"
        self._attr_unique_id = f"{self.device.hwid}_error"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.device.error

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:help-circle"
        
        self._update_device_from_coordinator()

        if self.device.error is None:
            return "mdi:check-circle"

        return "mdi:alert-circle"