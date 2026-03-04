"""Euronext Equities sensor platform.

Per equity, up to three sensors are created:
  • EuronextPriceSensor    — current price               (always)
  • EuronextSharesSensor   — number of shares owned      (only when shares > 0)
  • EuronextTotalSensor    — total portfolio value        (only when shares > 0)

All entities for the same equity share a DeviceInfo so HA groups them
together as one device. The refresh button (button.py) uses the same
DeviceInfo to appear in the same device card.
"""
import asyncio
import datetime
import logging

import aiohttp
import async_timeout
from lxml import html

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_EQUITIES,
    CONF_MARKET_HOURS_ONLY,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHARES_OWNED,
    DEFAULT_MARKET_HOURS_ONLY,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _within_market_hours() -> bool:
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t_open  = now.replace(hour=MARKET_OPEN_HOUR,  minute=MARKET_OPEN_MINUTE,  second=0, microsecond=0)
    t_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    return t_open <= now <= t_close


def _make_device_info(equity: str, name: str) -> DeviceInfo:
    """One DeviceInfo per equity — shared by all its entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, equity.lower())},
        name=name,
        manufacturer="Euronext",
        model=equity.upper(),
        configuration_url=f"https://live.euronext.com/nb/product/equities/{equity.lower()}",
    )


async def async_api_call(session, equity: str):
    url = f"https://live.euronext.com/en/ajax/getDetailedQuote/{equity}"
    try:
        async with async_timeout.timeout(10):
            async with session.post(
                url,
                data="theme_name=euronext_live",
                headers={"content-type": "application/x-www-form-urlencoded; charset=UTF-8"},
            ) as response:
                return html.fromstring(await response.text())
    except (asyncio.TimeoutError, aiohttp.ClientError):
        _LOGGER.warning("Unable to reach Euronext for %s", equity)
        return None


async def async_get_process_data(session, equity: str) -> dict | None:
    tree = await async_api_call(session, equity.upper())
    if tree is None:
        return None
    try:
        name      = tree.xpath("//strong/text()")[0]
        price_raw = tree.xpath("//span[@id='header-instrument-price']/text()")[0]
        price     = float(price_raw.replace(" ", "").replace(",", "."))
        unit      = tree.xpath("//span[@id='header-instrument-currency']/text()")[0].strip()
        date      = tree.xpath("//div[contains(@class, 'last-price-date-time')]/text()")[1].replace("/", ".").strip()
        day       = float(tree.xpath("//span[@class='text-ui-grey-1 mr-2']/text()")[0][1:-2])
        icon = (
            "mdi:trending-up"     if day > 0 else
            "mdi:trending-down"   if day < 0 else
            "mdi:trending-neutral"
        )
        return {"name": name, "unit": unit, "price": price,
                "unique": equity.lower(), "icon": icon, "date": date, "day": day}
    except (IndexError, AttributeError, ValueError) as err:
        _LOGGER.warning("Unable to parse data for %s: %s", equity, err)
        return None


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    cfg             = {**entry.data, **entry.options}
    equities        = cfg.get(CONF_EQUITIES, [])
    interval_min    = cfg.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)
    market_hrs_only = cfg.get(CONF_MARKET_HOURS_ONLY, DEFAULT_MARKET_HOURS_ONLY)
    shares_owned    = cfg.get(CONF_SHARES_OWNED, {})
    scan_interval   = datetime.timedelta(minutes=interval_min)

    session = async_get_clientsession(hass)

    # price_sensors = the "master" sensors that own fetching logic
    # all_entities  = everything to register with HA (price + shares + total)
    price_sensors: list[EuronextPriceSensor] = []
    all_entities: list[SensorEntity] = []

    for equity in equities:
        data = await async_get_process_data(session, equity)
        if not data:
            _LOGGER.error("Failed initial fetch for %s — skipping", equity)
            continue

        shares = int(shares_owned.get(equity.upper(), 0))
        device = _make_device_info(equity, data["name"])

        price_sensor = EuronextPriceSensor(hass, data, equity, data["unit"], device)
        price_sensors.append(price_sensor)
        all_entities.append(price_sensor)

        if shares > 0:
            shares_sensor = EuronextSharesSensor(equity, data["name"], shares, device)
            total_sensor  = EuronextTotalSensor(hass, equity, data, shares, data["unit"], device)
            # Cross-link so price updates cascade to total
            price_sensor.register_dependents(shares_sensor, total_sensor)
            all_entities += [shares_sensor, total_sensor]

        _LOGGER.info("Set up device for %s (%d shares)", data["name"], shares)

    # Store price sensors for button.py — must happen before async_add_entities
    hass.data[DOMAIN][entry.entry_id]["sensors"] = price_sensors
    async_add_entities(all_entities)

    # Scheduled polling — HA never auto-polls (_attr_should_poll = False)
    async def _scheduled_update(_now: datetime.datetime) -> None:
        if market_hrs_only and not _within_market_hours():
            _LOGGER.debug("Outside market hours — skipping")
            return
        for ps in price_sensors:
            await ps.async_fetch_and_apply()

    entry.async_on_unload(
        async_track_time_interval(hass, _scheduled_update, scan_interval)
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_update))


async def _async_reload_on_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


# ---------------------------------------------------------------------------
# Entity classes
# ---------------------------------------------------------------------------

class EuronextPriceSensor(SensorEntity):
    """Current stock price. This entity owns the fetch logic for its device."""

    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        data: dict,
        equity: str,
        unit: str,
        device: DeviceInfo,
    ) -> None:
        self.hass = hass
        self._equity = equity
        self._unit   = unit
        self._attr_device_info = device
        self._attr_unique_id   = data["unique"]            # e.g. no0013536151-xosl
        self._shares_sensor: EuronextSharesSensor | None = None
        self._total_sensor:  EuronextTotalSensor  | None = None
        self._apply_data(data)

    def register_dependents(
        self,
        shares_sensor: "EuronextSharesSensor",
        total_sensor:  "EuronextTotalSensor",
    ) -> None:
        self._shares_sensor = shares_sensor
        self._total_sensor  = total_sensor

    def _apply_data(self, data: dict) -> None:
        self._attr_name  = data["name"]
        self._attr_icon  = data["icon"]
        self._attr_native_unit_of_measurement = self._unit
        self._attr_native_value = data["price"]
        self._attr_extra_state_attributes = {
            ATTR_ATTRIBUTION: "Data provided by Euronext",
            "Dato":  data["date"],
            "1 dag": f"{data['day']} %",
        }
        self._last_data = data

    async def async_fetch_and_apply(self) -> None:
        """Fetch from Euronext, update self and any dependent sensors."""
        session = async_get_clientsession(self.hass)
        data = await async_get_process_data(session, self._equity)
        if data is None:
            _LOGGER.warning("Fetch failed for %s — keeping last value", self._equity)
            return
        self._apply_data(data)
        self.async_write_ha_state()

        if self._total_sensor:
            self._total_sensor.update_price(data["price"])
            self._total_sensor.async_write_ha_state()

        _LOGGER.info("Updated %s → %s %s", self._attr_name, self._attr_native_value, self._unit)

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def name(self) -> str:
        return self._attr_name


class EuronextSharesSensor(SensorEntity):
    """Static sensor showing the number of shares owned. Never needs to fetch."""

    _attr_should_poll = False
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        equity: str,
        stock_name: str,
        shares: int,
        device: DeviceInfo,
    ) -> None:
        self._attr_device_info  = device
        self._attr_unique_id    = f"{equity.lower()}_shares"
        self._attr_name         = f"{stock_name} Antall aksjer"
        self._attr_native_value = shares
        self._attr_native_unit_of_measurement = "stk"


class EuronextTotalSensor(SensorEntity):
    """Sensor showing total portfolio value (price × shares)."""

    _attr_should_poll = False
    _attr_icon = "mdi:cash-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        equity: str,
        data: dict,
        shares: int,
        unit: str,
        device: DeviceInfo,
    ) -> None:
        self.hass = hass
        self._shares = shares
        self._attr_device_info  = device
        self._attr_unique_id    = f"{equity.lower()}_total"
        self._attr_name         = f"{data['name']} Total verdi"
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = round(data["price"] * shares, 2)

    def update_price(self, price: float) -> None:
        self._attr_native_value = round(price * self._shares, 2)
