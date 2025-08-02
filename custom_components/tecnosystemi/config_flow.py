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

from .api import TecnosystemiAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_PIN): str,
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

    return {
        "title": "Tecnosystemi",
        "username": data[CONF_USERNAME],
        "password": data[CONF_PASSWORD],
        "pin": data[CONF_PIN],
        "device_id": device_id,
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
                return self.async_create_entry(title=info["title"], data=user_input)

        await self._async_handle_discovery_without_unique_id()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
