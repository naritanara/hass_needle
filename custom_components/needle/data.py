"""Custom types for needle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration


type NeedleConfigEntry = ConfigEntry[NeedleData]


@dataclass
class NeedleData:
    """Data for the Needle integration."""

    integration: Integration
