"""Config flow for the Tecnosystemi integration."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_PIN, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector

from .api import TecnosystemiAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str
    }
)



class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self) -> None:
        """Initialize."""

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


def generate_random_hex_id() -> str:
    """Generate a random 16-character hexadecimal string."""
    return secrets.token_hex(8)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
    # )

    device_id = generate_random_hex_id()

    api = TecnosystemiAPI(
        username=data[CONF_USERNAME], password=data[CONF_PASSWORD], device_id=device_id
    )

    try:
        await api.login()
    except RuntimeError as e:
        _LOGGER.error("Failed to login to Tecnosystemi API: %s", e)
        raise InvalidAuth("Invalid username or password") from None
    
    plants = await api.GetPlants()

    return {
        "title": "Tecnosystemi",
        "username": data[CONF_USERNAME],
        "password": data[CONF_PASSWORD],
        "plants": plants,
        "device_id": device_id,
        "api": api
    }


class TecnosystemiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tecnosystemi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                user_input["device_id"] = info["device_id"]
                self.info = info
                self.user_input = user_input

                # Create a schema with a PIN for every device found
                self.devices = [ device for plant in info["plants"] for device in plant.getDevices() ]

                if len(self.devices) == 0:
                    # Show that no devices were found
                    return self.async_show_form(
                        step_id="user",
                        data_schema=STEP_USER_DATA_SCHEMA,
                        errors={"base": "no_devices"}
                    )
                else:                    
                    return await self.async_device_form()

        await self._async_handle_discovery_without_unique_id()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
    
    async def async_device_form(self, errors : dict[str, str] = {}) -> ConfigFlowResult:
        self.current_device = self.devices[0]
        device_name = self.current_device.Name

        return self.async_show_form(
            step_id = "device",
            data_schema = vol.Schema({
                vol.Required(CONF_PIN): str
            }),
            description_placeholders = {
                "import_device": device_name, 
            },
            errors = errors
        )
    
    async def async_step_device(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Handle discovered devices."""

        errors : dict[str, str] = {}

        device_id = self.current_device.Serial
        pin = user_input[CONF_PIN]
        self.user_input[f"{device_id}_{CONF_PIN}"] = pin

        # Check that the PIN is valid
        if await self.info["api"].getDeviceState(self.current_device, pin) is None:
            errors["base"] = "invalid_auth"
        else:
            self.devices.pop()

        if len(self.devices) > 0:
            return await self.async_device_form(errors)
        else:
            return self.async_create_entry(
                title=self.info["title"], 
                data=self.user_input
            )
        

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
