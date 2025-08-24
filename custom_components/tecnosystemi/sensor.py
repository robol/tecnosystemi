"""Tecnosystemi sensor platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_PIN, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TecnosystemiConfigEntry
from .api import TecnosystemiAPI
from .coordinator import TecnosystemiCoordinator, TecnosystemiCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TecnosystemiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tecnosystemi climate entities from a config entry."""
    coordinator: TecnosystemiCoordinator = entry.runtime_data
    api = coordinator.api

    entities: list[TecnosystemiCoordinatorEntity] = []
    for device_id in coordinator.data:
        device_serial = coordinator.data[device_id]["Device"].Serial
        temperature_entity = TecnosystemiTemperatureSensorEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[f"{device_serial}_{CONF_PIN}"],
        )
        entities.append(temperature_entity)

        humidity_entity = TecnosystemiHumiditySensorEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[f"{device_serial}_{CONF_PIN}"],
        )
        entities.append(humidity_entity)

        shutter_entity = TecnosystemiShutterSensorEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[f"{device_serial}_{CONF_PIN}"],
        )
        entities.append(shutter_entity)

    async_add_entities(entities)

class TecnosystemiTemperatureSensorEntity(TecnosystemiCoordinatorEntity, SensorEntity):
    """Temperature Sensor entity for Tecnosystemi integration."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        device_id: str,
        zone: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the temperature sensor entity."""
        TecnosystemiCoordinatorEntity.__init__(self, device_id, zone, coordinator, api, pin)

        self._attr_unique_id = device_id + "_temperature"
        self._attr_name = "Temperature of " + zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = zone["DeviceInfo"]

        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        self._attr_native_value = float(self.zone_state["Temp"]) / 10.0


class TecnosystemiHumiditySensorEntity(TecnosystemiCoordinatorEntity, SensorEntity):
    """Humidity Sensor entity for Tecnosystemi integration."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        device_id: str,
        zone: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the temperature sensor entity."""
        TecnosystemiCoordinatorEntity.__init__(self, device_id, zone, coordinator, api, pin)

        self._attr_unique_id = device_id + "_humidity"
        self._attr_name = "Humidity of " + zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = self._attr_device_info = zone["DeviceInfo"]

        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        self._attr_native_value = float(self.zone_state["Umd"]) / 10.0

class TecnosystemiShutterSensorEntity(TecnosystemiCoordinatorEntity, SensorEntity):
    """Shutter Sensor entity for Tecnosystemi integration."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.POWER_FACTOR
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        device_id: str,
        zone: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the shutter sensor entity."""
        TecnosystemiCoordinatorEntity.__init__(self, device_id, zone, coordinator, api, pin)

        self._attr_unique_id = device_id + "_shutter"
        self._attr_name = "Shutter Position of " + zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = zone["DeviceInfo"]

        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        value = int(self.zone_state["Serranda"])

        # Ignore the bit in position 5, that signals that the
        # shutter is in auto mode. The value is in the range [0, 3],
        # and we rescale it to [0, 100].
        value = value & 0x0F
        value = value * 100.0 / 3.0

        self._attr_native_value = value