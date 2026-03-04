"""Euronext Equities – refresh button platform.

One button per equity, sharing the same DeviceInfo as the price/shares/total
sensors so it appears inside the same device card in the HA UI.
"""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one refresh button per price sensor (= per equity)."""
    price_sensors = hass.data[DOMAIN][entry.entry_id].get("sensors", [])
    if not price_sensors:
        _LOGGER.warning("No sensors found for entry %s — no buttons created", entry.entry_id)
    async_add_entities(
        [EuronextRefreshButton(hass, ps) for ps in price_sensors]
    )


class EuronextRefreshButton(ButtonEntity):
    """Button that triggers an immediate price fetch for the paired equity."""

    _attr_should_poll = False
    _attr_icon = "mdi:refresh"

    def __init__(self, hass: HomeAssistant, price_sensor) -> None:
        self.hass = hass
        self._price_sensor = price_sensor
        # Must share the same DeviceInfo as the sensors
        self._attr_device_info = price_sensor._attr_device_info
        self._attr_unique_id   = f"{price_sensor.unique_id}_refresh"
        self._attr_name        = f"{price_sensor.name} Refresh"

    async def async_press(self) -> None:
        """Fetch immediately — bypasses market-hours check."""
        _LOGGER.info("Manual refresh for %s", self._price_sensor.name)
        await self._price_sensor.async_fetch_and_apply()
