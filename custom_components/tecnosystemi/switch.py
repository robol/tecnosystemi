"""Tecnosystemi sensor platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_PIN
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

    entities: list[TecnosystemiSwitchEntity] = []
    for device_id in coordinator.data:
        if coordinator.data[device_id]["IsMaster"]:
            device_serial = coordinator.data[device_id]["Device"].Serial
            master_switch_entity = TecnosystemiMasterSwitchEntity(
                device_id=device_id,
                zone=coordinator.data[device_id],
                coordinator=coordinator,
                api=api,
                pin=entry.data[f"{device_serial}_{CONF_PIN}"],
            )
            entities.append(master_switch_entity)

    async_add_entities(entities)


class TecnosystemiSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Minimal Switch entity for Tecnosystemi integration."""

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
        self._attr_device_info = zone["DeviceInfo"]

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


class TecnosystemiMasterSwitchEntity(TecnosystemiSwitchEntity):
    """Master Switch for the Climate system."""

    _attr_is_on = False

    def __init__(
        self,
        device_id: str,
        zone: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize data structures for the master switch."""
        TecnosystemiSwitchEntity.__init__(self, device_id, zone, coordinator, api, pin)
        self._attr_unique_id = device_id + "_master_switch"
        self._attr_name = zone["Device"].Name
        self.coordinator = coordinator
        self.api = api
        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update the Home Assistant attributes after an update from the coordinator."""
        if self.zone_state["DeviceState"]["IsOFF"]:
            self._attr_is_on = False
        else:
            self._attr_is_on = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the master switch using the API."""
        cmd = {
            "is_off": 1,
            "is_cool": self.zone_state["DeviceState"]["IsCooling"],
            "cool_mod": self.zone_state["DeviceState"]["OperatingModeCooling"],
            "t_can": int(self.zone_state["DeviceState"]["TempCan"]),
        }

        await self.api.updateCUState(
            self.zone_state["Device"],
            self.pin,
            cmd,
        )

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the master switch using the API."""
        cmd = {
            "is_off": 0,
            "is_cool": self.zone_state["DeviceState"]["IsCooling"],
            "cool_mod": self.zone_state["DeviceState"]["OperatingModeCooling"],
            "t_can": int(self.zone_state["DeviceState"]["TempCan"]),
        }

        await self.api.updateCUState(
            self.zone_state["Device"],
            self.pin,
            cmd,
        )

        await self.coordinator.async_request_refresh()
