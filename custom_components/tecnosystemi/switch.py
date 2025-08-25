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
        master_switch_entity = TecnosystemiMasterSwitchEntity(
            device_id=device_id,
            device_state=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[f"{device_serial}_{CONF_PIN}"],
        )
        entities.append(master_switch_entity)

    async_add_entities(entities)

class TecnosystemiMasterSwitchEntity(TecnosystemiCoordinatorEntity, SwitchEntity):
    """Master Switch for the Climate system."""

    _attr_is_on = False

    def __init__(
        self,
        device_id: str,
        device_state: Any,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize data structures for the master switch."""
        TecnosystemiCoordinatorEntity.__init__(self, device_id, device_state, coordinator, api, pin)
        self._attr_unique_id = device_id + "_1_master_switch"
        self._attr_name = device_state["Device"].Name

    def update_attrs_from_state(self):
        """Update the Home Assistant attributes after an update from the coordinator."""
        if self.device_state["IsOFF"]:
            self._attr_is_on = False
        else:
            self._attr_is_on = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the master switch using the API."""
        cmd = {
            "is_off": 1,
            "is_cool": 1 if self.device_state["IsCooling"] else 0,
            "cool_mod": self.device_state["OperatingModeCooling"],
            "t_can": int(self.device_state["TempCan"]),
        }

        await self.api.updateCUState(
            self.device_state["Device"],
            self.pin,
            cmd,
        )

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the master switch using the API."""
        cmd = {
            "is_off": 0,
            "is_cool": 1 if self.device_state["IsCooling"] else 0,
            "cool_mod": self.device_state["OperatingModeCooling"],
            "t_can": int(self.device_state["TempCan"]),
        }

        await self.api.updateCUState(
            self.device_state["Device"],
            self.pin,
            cmd,
        )

        await self.coordinator.async_request_refresh()
