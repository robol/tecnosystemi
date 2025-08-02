"""Coordinator for Tecnosystemi integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.const import CONF_PIN
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TecnosystemiCoordinator(DataUpdateCoordinator):
    """Coordinatore for Tecnosystemi integration."""

    def __init__(self, hass, config_entry, api):
        """Initialize the Tecnosystemi coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Tecnosystemi Climate Coordinator",
            config_entry=config_entry,
            update_interval=timedelta(seconds=60),
            always_update=True,
        )
        self.api = api
        self._plants = []

    async def _async_setup(self):
        """Set up the coordinator.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        self._plants = await self.api.GetPlants()

    async def _async_api_call(self):
        """Async API call that retrieves the updated status."""
        data = {}

        async with asyncio.timeout(30):
            for plant in self._plants:
                for device in plant.getDevices():
                    # To actually find the zone thermostats, we need to get the state;
                    # Then, we create single climate entities for each of them, with
                    # a single parent device (the Polaris controller).
                    state = await self.api.getDeviceState(
                        device, self.config_entry.data[CONF_PIN]
                    )

                    # Note that this call might fail in case the user has logged in with the
                    # same email using the Tecnosystemi app on his/her personal device. In that
                    # case, we force a new login and try again.
                    if state is None:
                        await self.api.login()
                        state = await self.api.getDeviceState(
                            device, self.config_entry.data[CONF_PIN]
                        )

                    for zone in state["Zones"]:
                        zone["Device"] = device
                        zone["Plant"] = plant
                        zone["DeviceState"] = {
                            "Errors": state["Errors"],
                            "Serial": state["Serial"],
                            "Name": state["Name"],
                            "FWVer": state["FWVer"],
                            "IsOFF": state["IsOFF"],
                            "IsCooling": state["IsCooling"],
                            "OperatingModeCooling": state["OperatingModeCooling"],
                            "LastConfigUpdate": state["LastConfigUpdate"],
                            "LastSyncUpdate": state["LastSyncUpdate"],
                            "NumErrors": state["NumErrors"],
                            "Icon": state["Icon"],
                            "IrPresent": data,
                            "TempCan": state["TempCan"],
                            "IP": state["IP"],
                            "FInv": state["FInv"],
                            "FEst": state["FEst"],
                        }
                        zone["DeviceInfo"] = DeviceInfo(
                            identifiers={(DOMAIN, zone["Device"].Serial)},
                            name=zone["Device"].Name,
                            manufacturer="Tecnosystemi",
                            model="ProAir",
                            serial_number=zone["Device"].Serial,
                            sw_version=zone["Device"].FWVer,
                        )
                        data[f"{plant.LVPL_Id}_{device.Serial}_{zone['ZoneId']}"] = zone

            return data

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            try:
                # This will call the API and get the data for all plants and devices.
                data = await self._async_api_call()
            except TimeoutError:
                # Try again, without catching the second timeout error. This hels with
                # the fact that sometimes the API is either slow or the call gets lost,
                # and retrying a second time usually works.
                _LOGGER.warning(
                    "Timeout while fetching Tecnosystemi API data, retrying a second time"
                )
                return await self._async_api_call()
            else:
                return data
        except RuntimeError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from None
