"""Constants for Euronext Equities."""

DOMAIN = "euronext_equities"

CONF_EQUITIES               = "equities"
CONF_SCAN_INTERVAL_MINUTES  = "scan_interval_minutes"
CONF_MARKET_HOURS_ONLY      = "market_hours_only"
CONF_SHARES_OWNED           = "shares_owned"

DEFAULT_SCAN_INTERVAL_MINUTES = 60
MIN_SCAN_INTERVAL_MINUTES     = 1
MAX_SCAN_INTERVAL_MINUTES     = 1440
DEFAULT_MARKET_HOURS_ONLY     = True

MARKET_OPEN_HOUR    = 9
MARKET_OPEN_MINUTE  = 0
MARKET_CLOSE_HOUR   = 16
MARKET_CLOSE_MINUTE = 30
