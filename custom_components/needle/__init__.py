"""
Custom integration to integrate needle with Home Assistant.

For more details about this integration, please refer to
https://github.com/naritanara/hass_needle
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration

from .data import NeedleData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NeedleConfigEntry

PLATFORMS: list[Platform] = [Platform.CONVERSATION]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeedleConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    entry.runtime_data = NeedleData(
        integration=async_get_loaded_integration(hass, entry.domain),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: NeedleConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
