"""Euronext Equities integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Euronext Equities.

    Platforms are forwarded one at a time so sensor finishes populating
    hass.data[DOMAIN][entry_id]["sensors"] before button.py runs.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"sensors": []}

    # Sequential: sensor first, button second — order is guaranteed
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    await hass.config_entries.async_forward_entry_setups(entry, ["button"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "button"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
