**Euronext Equities sensor for Home Assistant**

<img src="https://raw.githubusercontent.com/gohlas/hass_euronext/main/custom_components/euronext_equities/brand/logo.png" width="200">

The euronext_equities integration uses the Euronext website to track live stock (equity) prices. It is fully configured through the Home Assistant UI — no configuration.yaml editing required.

Replaces the original euronext fund sensor. This integration tracks equities (stocks) identified by their ISIN-MIC code, and adds portfolio value tracking, market-hours filtering, and per-stock refresh buttons.


Features

Live stock price sensor per equity
Optional shares owned sensor (number of shares you hold)
Optional total portfolio value sensor (price × shares, in the stock's currency)
Refresh button per stock — fetch the latest price on demand
Configurable polling interval (default: 60 minutes)
Market hours filter — optionally restrict automatic updates to Mon–Fri 09:00–16:30
Full UI configuration via Settings → Integrations (no YAML needed)
All entities grouped under a single device per stock


**Requirements**

Home Assistant 2026.3 or newer (for local brand image support)
Internet access to live.euronext.com


**Installation**
HACS (recommended)
Mostrar Imagem

Click the button above, or open HACS → Integrations → ⋮ → Custom repositories
Add https://github.com/gohlas/hass_euronext as an Integration
Search for Euronext Equities and install it
Restart Home Assistant

**Manual**

Download the latest release from GitHub
Copy the euronext_equities folder into your config/custom_components/ directory:

_   config/
   └── custom_components/
       └── euronext_equities/
           ├── __init__.py
           ├── sensor.py
           ├── button.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── strings.json
           ├── brand/
           │   ├── icon.png
           │   └── logo.png
           └── translations/
               └── en.json_

Restart Home Assistant


**Add to Home Assistant**
Mostrar Imagem
Or go to Settings → Devices & Services → Add Integration and search for Euronext Equities.

Configuration
Setup is done entirely through the UI in two steps.
Step 1 — Equities & settings
FieldDescriptionDefaultEquities (ISIN-MIC)One or more stock identifiers, one per line or comma-separated—Polling interval (minutes)How often to automatically fetch prices60Market hours onlyOnly poll automatically Mon–Fri 09:00–16:30enabled
Finding the ISIN-MIC for a stock
Open the stock's page on live.euronext.com. The ISIN-MIC is the last segment of the URL:
https://live.euronext.com/nb/product/equities/NO0013536151-XOSL
                                                ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                use this part
You can enter multiple equities, one per line:
NO0013536151-XOSL
NO0010208051-XOSL
IE00BZ12WP82-XMSM
Step 2 — Shares owned (optional)
For each equity you entered, you will see a number field. Enter how many shares you own. Set to 0 to skip portfolio tracking for that stock.
When shares are set, two additional sensors are created per stock:

Antall aksjer — number of shares owned
Total verdi — total value in the stock's currency (price × shares)


Entities
For each stock, the following entities are created under a single device:
EntityTypeDescriptionsensor.<name>SensorCurrent stock pricesensor.<name>_antall_aksjerSensorShares owned (stk) — only if shares > 0sensor.<name>_total_verdiSensorTotal portfolio value — only if shares > 0button.<name>_refreshButtonFetch the latest price immediately
All entities are grouped under a single device per stock in Settings → Devices & Services.

Reconfiguring
To change equities, the polling interval, market hours setting, or shares owned:

Go to Settings → Devices & Services → Euronext Equities
Click Configure
Update your settings across the two steps and save

The integration reloads automatically when you save.

Notes

The Refresh button always fetches immediately regardless of the market-hours setting — it is never blocked
Price data is scraped from the Euronext website. If the page layout changes, the sensor may stop updating. Please open an issue if this happens
Brand images (integration icon) require Home Assistant 2026.3+ and are served via the new local brands proxy API (/api/brands/integration/euronext_equities/icon.png)


Credits
Based on the original euronext fund sensor by @hulkhaugen.
Maintained by @gohlas.
