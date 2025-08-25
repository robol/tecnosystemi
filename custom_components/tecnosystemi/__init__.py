"""The Tecnosystemi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import TecnosystemiAPI
from .coordinator import TecnosystemiCoordinator

_PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]

type TecnosystemiConfigEntry = ConfigEntry[TecnosystemiCoordinator]

async def async_setup_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Set up Tecnosystemi from a config entry."""

    device_id = entry.data["device_id"]

    api = TecnosystemiAPI(
        username=entry.data["username"],
        password=entry.data["password"],
        device_id=device_id,
    )

    entry.runtime_data = TecnosystemiCoordinator(
        hass=hass,
        config_entry=entry,
        api=api,
    )

    try:
        await api.login()
    except RuntimeError:
        raise ConfigEntryNotReady(
            "Tecnosystemi API is not ready due to login problems. Please check your configuration."
        ) from None

    await entry.runtime_data.async_config_entry_first_refresh()
    if not entry.runtime_data.data:
        raise ConfigEntryNotReady(
            "Tecnosystemi API did not return any data. Please check your configuration."
        )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TecnosystemiConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
