"""Tecnosystemi sensor platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_PIN, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TecnosystemiConfigEntry
from .api import TecnosystemiAPI
from .coordinator import TecnosystemiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TecnosystemiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tecnosystemi climate entities from a config entry."""
    coordinator: TecnosystemiCoordinator = entry.runtime_data
    api = coordinator.api

    entities: list[TecnosystemiSensorEntity] = []
    for device_id in coordinator.data:
        temperature_entity = TecnosystemiTemperatureSensorEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[CONF_PIN],
        )
        entities.append(temperature_entity)

        humidity_entity = TecnosystemiHumiditySensorEntity(
            device_id=device_id,
            zone=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[CONF_PIN],
        )
        entities.append(humidity_entity)

    async_add_entities(entities)


class TecnosystemiSensorEntity(CoordinatorEntity, SensorEntity):
    """Minimal Temperature Sensor entity for Tecnosystemi integration."""

    def __init__(
        self,
        device_id: str,
        zone: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the sensor entity."""
        CoordinatorEntity.__init__(self, coordinator)
        self.device_id = device_id
        self.zone = zone
        self.api = api
        self.pin = pin
        self.zone_state = zone
        self.coordinator = coordinator

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        raise NotImplementedError(
            "Please overload this function in the specific sensor entity."
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.zone_state = self.coordinator.data[self.device_id]

        self.update_attrs_from_state()
        self.async_write_ha_state()


class TecnosystemiTemperatureSensorEntity(TecnosystemiSensorEntity):
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
        TecnosystemiSensorEntity.__init__(self, device_id, zone, coordinator, api, pin)

        self._attr_unique_id = device_id + "_temperature"
        self._attr_name = "Temperature of " + zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = zone["DeviceInfo"]

        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        self._attr_native_value = float(self.zone_state["Temp"]) / 10.0


class TecnosystemiHumiditySensorEntity(TecnosystemiSensorEntity):
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
        TecnosystemiSensorEntity.__init__(self, device_id, zone, coordinator, api, pin)

        self._attr_unique_id = device_id + "_humidity"
        self._attr_name = "Humidity of " + zone["Name"] + " - " + zone["Device"].Name
        self._attr_device_info = self._attr_device_info = zone["DeviceInfo"]

        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        self._attr_native_value = float(self.zone_state["Umd"]) / 10.0
