"""Config flow for Euronext Equities.

Step 1 (user / init):  equities list, scan interval, market-hours toggle
Step 2 (shares):       one integer number field per equity for shares owned
"""
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_EQUITIES,
    CONF_MARKET_HOURS_ONLY,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SHARES_OWNED,
    DEFAULT_MARKET_HOURS_ONLY,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

ISIN_MIC_RE = re.compile(r"^[A-Z0-9]{12}-[A-Z]{4}$")


def _parse_equities(raw: str) -> list[str]:
    items = [e.strip().upper() for e in raw.replace(",", "\n").splitlines() if e.strip()]
    if not items:
        raise vol.Invalid("no_equities")
    for item in items:
        if not ISIN_MIC_RE.match(item):
            raise vol.Invalid("invalid_isin_mic")
    return items


def _step1_schema(default_equities: str, default_interval: int, default_mh: bool) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_EQUITIES, default=default_equities): str,
        vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=default_interval): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL_MINUTES, max=MAX_SCAN_INTERVAL_MINUTES),
        ),
        vol.Required(CONF_MARKET_HOURS_ONLY, default=default_mh): bool,
    })


def _shares_schema(equities: list[str], current_shares: dict) -> vol.Schema:
    """Build a schema with one integer number field per equity."""
    fields = {}
    for equity in equities:
        default = int(current_shares.get(equity.upper(), 0))
        fields[vol.Optional(equity.upper(), default=default)] = vol.All(
            vol.Coerce(int), vol.Range(min=0)
        )
    return vol.Schema(fields)


# ---------------------------------------------------------------------------
# Initial config flow
# ---------------------------------------------------------------------------

class EuronextEquitiesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step setup: (1) equities + settings, (2) shares owned per equity."""

    VERSION = 1

    def __init__(self) -> None:
        self._equities: list[str] = []
        self._interval: int = DEFAULT_SCAN_INTERVAL_MINUTES
        self._market_hours: bool = DEFAULT_MARKET_HOURS_ONLY

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._equities = _parse_equities(user_input[CONF_EQUITIES])
                self._interval = user_input[CONF_SCAN_INTERVAL_MINUTES]
                self._market_hours = user_input[CONF_MARKET_HOURS_ONLY]
                return await self.async_step_shares()
            except vol.Invalid as exc:
                errors[CONF_EQUITIES] = str(exc)

        return self.async_show_form(
            step_id="user",
            data_schema=_step1_schema("NO0013536151-XOSL", DEFAULT_SCAN_INTERVAL_MINUTES, DEFAULT_MARKET_HOURS_ONLY),
            errors=errors,
        )

    async def async_step_shares(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            shares = {eq: user_input.get(eq, 0) for eq in self._equities}
            return self.async_create_entry(
                title="Euronext Equities",
                data={
                    CONF_EQUITIES: self._equities,
                    CONF_SCAN_INTERVAL_MINUTES: self._interval,
                    CONF_MARKET_HOURS_ONLY: self._market_hours,
                    CONF_SHARES_OWNED: shares,
                },
            )

        return self.async_show_form(
            step_id="shares",
            data_schema=_shares_schema(self._equities, {}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return EuronextEquitiesOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow (reconfigure)
# ---------------------------------------------------------------------------

class EuronextEquitiesOptionsFlow(config_entries.OptionsFlow):
    """Two-step options: (1) equities + settings, (2) shares owned per equity."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry_id = config_entry.entry_id
        self._equities: list[str] = []
        self._interval: int = DEFAULT_SCAN_INTERVAL_MINUTES
        self._market_hours: bool = DEFAULT_MARKET_HOURS_ONLY

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        cfg = {**entry.data, **(entry.options or {})}
        current_equities = "\n".join(cfg.get(CONF_EQUITIES, []))
        current_interval = cfg.get(CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES)
        current_mh       = cfg.get(CONF_MARKET_HOURS_ONLY, DEFAULT_MARKET_HOURS_ONLY)
        # Store for use in step 2
        self._current_shares = cfg.get(CONF_SHARES_OWNED, {})

        if user_input is not None:
            try:
                self._equities     = _parse_equities(user_input[CONF_EQUITIES])
                self._interval     = user_input[CONF_SCAN_INTERVAL_MINUTES]
                self._market_hours = user_input[CONF_MARKET_HOURS_ONLY]
                return await self.async_step_shares()
            except vol.Invalid as exc:
                errors[CONF_EQUITIES] = str(exc)

        return self.async_show_form(
            step_id="init",
            data_schema=_step1_schema(current_equities, current_interval, current_mh),
            errors=errors,
        )

    async def async_step_shares(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            shares = {eq: user_input.get(eq, 0) for eq in self._equities}
            return self.async_create_entry(
                title="",
                data={
                    CONF_EQUITIES: self._equities,
                    CONF_SCAN_INTERVAL_MINUTES: self._interval,
                    CONF_MARKET_HOURS_ONLY: self._market_hours,
                    CONF_SHARES_OWNED: shares,
                },
            )

        return self.async_show_form(
            step_id="shares",
            data_schema=_shares_schema(self._equities, self._current_shares),
        )
