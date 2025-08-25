from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data
from typing import Any

from . import TecnosystemiConfigEntry

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    config_data = entry.data

    TO_REDACT = { "password" }

    api_data = entry.runtime_data.device_state
    for device_id in api_data:
        TO_REDACT.add(f"{api_data[device_id]['Device'].Serial}_pin")
        api_data[device_id]["Device"] = api_data[device_id]["Device"].to_dict()
        api_data[device_id]["Plant"] = api_data[device_id]["Plant"].to_dict()
        del api_data[device_id]["DeviceInfo"]

    return {
        "config": async_redact_data(config_data, TO_REDACT),
        "api-state": api_data
    }