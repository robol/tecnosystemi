"""Support for the Airzone Cloud climate."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import CONF_PIN, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TecnosystemiConfigEntry
from .api import TecnosystemiAPI
from .coordinator import TecnosystemiCoordinator, TecnosystemiCoordinatorEntity, TecnosystemiCoordinatorZoneEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TecnosystemiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Tecnosystemi climate entities from a config entry."""
    coordinator: TecnosystemiCoordinator = entry.runtime_data
    api = coordinator.api

    entities: list[TecnosystemiClimateEntity | TecnosystemiMasterClimateEntity] = []
    for device_id in coordinator.data:
        device_serial = coordinator.data[device_id]["Device"].Serial

        master = TecnosystemiMasterClimateEntity(
            device_id=device_id,
            device_state=coordinator.data[device_id],
            coordinator=coordinator,
            api=api,
            pin=entry.data[f"{device_serial}_{CONF_PIN}"],
        )
        entities.append(master)

        # Create a climate entity for each zone
        zone_ids = [ zone["ZoneId"] for zone in coordinator.data[device_id].get("Zones", []) ]
        for zone_id in zone_ids:
            entity = TecnosystemiClimateEntity(
                device_id=device_id,
                device_state=coordinator.data[device_id],
                zone_id=zone_id,
                coordinator=coordinator,
                api=api,
                pin=entry.data[f"{device_serial}_{CONF_PIN}"],
            )
            entities.append(entity)

    async_add_entities(entities)


class TecnosystemiMasterClimateEntity(TecnosystemiCoordinatorEntity, ClimateEntity):
    """Master Climate that controls the temperature of the A/C machine and the operating mode of the system."""

    _attr_has_entity_name = False
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY]
    _attr_hvac_mode = HVACMode.OFF
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 1.0
    _attr_max_temp = 31.0
    _attr_min_temp = 16.0

    def __init__(
        self,
        device_id: str,
        device_state: dict,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the climate entity."""
        TecnosystemiCoordinatorEntity.__init__(self, device_id, device_state, coordinator, api, pin)
        self._attr_unique_id = (
            str(device_state["Plant"].LVPL_Id) + "_" + str(device_state["Device"].Serial)
        )
        self._attr_name = device_state["Device"].Name

        # self._handle_coordinator_update()
        self.update_attrs_from_state()

    def update_attrs_from_state(self):
        """Update the variables in the entity after receiving an update from the coordinator."""
        if not self.device_state["IsCooling"]:
            self._attr_hvac_mode = HVACMode.HEAT
        elif self.device_state["OperatingModeCooling"] == 1:
            self._attr_hvac_mode = HVACMode.COOL
        elif self.device_state["OperatingModeCooling"] == 2:
            self._attr_hvac_mode = HVACMode.DRY
        elif self.device_state["OperatingModeCooling"] == 3:
            self._attr_hvac_mode = HVACMode.FAN_ONLY
        else:
            _LOGGER.warning("Unsupported mode in Tecnosystemi integration")

        self._attr_target_temperature = (
            float(self.device_state["TempCan"]) / 10.0
        )

    async def async_send_command(self, cmd: dict):
        """Send a command to the Tecnosystemi API."""
        await self.api.updateCUState(
            self.device_state["Device"],
            self.pin,
            cmd,
        )

        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._attr_hvac_mode = hvac_mode

        if hvac_mode == HVACMode.HEAT:
            is_cool = 0
            cool_mod = self.device_state["OperatingModeCooling"]
        else:
            is_cool = 1
            if hvac_mode == HVACMode.COOL:
                cool_mod = 1
            elif hvac_mode == HVACMode.DRY:
                cool_mod = 2
            elif hvac_mode == HVACMode.FAN_ONLY:
                cool_mod = 3
            else:
                _LOGGER.warning("Unsupported mode received in Tecnosystemi API")

        cmd = {
            "is_off": 1 if self.device_state["IsOFF"] else 0,
            "is_cool": is_cool,
            "cool_mod": cool_mod,
            "t_can": int(self.device_state["TempCan"]),
        }
        await self.async_send_command(cmd)

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        cmd = {
            "is_off": 1 if self.device_state["IsOFF"] else 0,
            "is_cool": 1 if self.device_state["IsCooling"] else 0,
            "cool_mod": self.device_state["OperatingModeCooling"],
            "t_can": int(kwargs["temperature"] * 10),
        }
        await self.async_send_command(cmd)


class TecnosystemiClimateEntity(TecnosystemiCoordinatorZoneEntity, ClimateEntity):
    """Minimal Climate entity for Tecnosystemi integration."""

    _attr_has_entity_name = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO]
    _attr_hvac_mode = HVACMode.OFF
    _attr_hvac_action = None
    _attr_fan_modes = [FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_LOW]
    _attr_fan_mode = FAN_AUTO
    _attr_max_temp = 31.0
    _attr_min_temp = 16.0
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        device_id: str,
        device_state: dict,
        zone_id: int,
        coordinator: TecnosystemiCoordinator,
        api: TecnosystemiAPI,
        pin: str,
    ) -> None:
        """Initialize the climate entity."""
        TecnosystemiCoordinatorZoneEntity.__init__(self, device_id, device_state, zone_id, coordinator, api, pin)
        self._attr_unique_id = device_id + "_" + str(zone_id)
        self._attr_name = self.zone_state["Name"] + " - " + device_state["Device"].Name

    def update_attrs_from_state(self):
        """Update attributes from the current state."""
        zone_state = self.get_zone_state()

        self._attr_hvac_mode = (
            HVACMode.OFF if zone_state["IsOFF"] else HVACMode.AUTO
        )
        self._attr_current_temperature = float(zone_state["Temp"]) / 10.0
        self._attr_target_temperature = float(zone_state["SetTemp"]) / 10.0
        self._attr_current_humidity = float(zone_state.get("Umd", 0)) / 10.0

        fan_mode = zone_state.get("SerrandaSet")
        if fan_mode == 0 or fan_mode >= 16:
            self._attr_fan_mode = FAN_AUTO
        elif fan_mode == 1:
            self._attr_fan_mode = FAN_LOW
        elif fan_mode == 2:
            self._attr_fan_mode = FAN_MEDIUM
        elif fan_mode == 3:
            self._attr_fan_mode = FAN_HIGH

    async def async_send_command(self, cmd: dict):
        """Send a command to the Tecnosystemi API."""
        await self.api.updateDeviceState(
            self.device_state["Device"],
            self.pin,
            int(self.zone_id),
            cmd,
        )

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        zone_state = self.get_zone_state()
        cmd = {
            "is_off": 1 if self._attr_hvac_mode == HVACMode.OFF else 0,
            "t_set": str(int(kwargs["temperature"] * 10)),
            "name": zone_state["Name"],
        }
        await self.async_send_command(cmd)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if self._attr_target_temperature is None:
            return

        zone_state = self.get_zone_state()

        cmd = {
            "is_off": 1 if hvac_mode == HVACMode.OFF else 0,
            "t_set": str(int(self._attr_target_temperature * 10)),
            "name": zone_state["Name"],
            "shu_set": self.get_serranda_set(),
            "fan_set": self.get_serranda_set(),
        }
        await self.async_send_command(cmd)

    def get_serranda_set(self):
        """Get the serranda set value based on the current fan mode."""
        if self._attr_fan_mode == FAN_AUTO:
            return 16
        if self._attr_fan_mode == FAN_LOW:
            return 1
        if self._attr_fan_mode == FAN_MEDIUM:
            return 2
        if self._attr_fan_mode == FAN_HIGH:
            return 3
        return 0

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        if self._attr_target_temperature is None:
            return

        if fan_mode == FAN_AUTO:
            serranda_set = 16
        elif fan_mode == FAN_LOW:
            serranda_set = 1
        elif fan_mode == FAN_MEDIUM:
            serranda_set = 2
        elif fan_mode == FAN_HIGH:
            serranda_set = 3
        else:
            serranda_set = 0

        zone_state = self.get_zone_state()

        cmd = {
            "shu_set": serranda_set,
            "fan_set": serranda_set,
            "name": zone_state["Name"],
            "t_set": str(int(self._attr_target_temperature * 10)),
            "is_off": 1 if self._attr_hvac_mode == HVACMode.OFF else 0,
        }
        await self.async_send_command(cmd)
