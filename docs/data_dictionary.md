# Data dictionary

Every dataset in `ppa-lab`, what each column means, its unit and its conventions.
Update this page whenever a dataset or column is added (part of the definition of done).

**Contents:** [Conventions](#conventions-that-apply-everywhere) ·
[Layers](#data-layers) · [prices_native](#prices_nativeparquet) ·
[prices_hourly](#prices_hourlyparquet) · [power_15min / power_hourly](#power_15minparquet-and-power_hourlyparquet) ·
[Reference data](#reference-data) · [Derived tables](#derived-tables-computed-in-code-not-stored) ·
[Loading](#how-to-load-the-data)

---

## Conventions that apply everywhere

| Rule | Detail |
|---|---|
| Index | `ts_utc`: tz-aware timestamps in **UTC**, nanosecond precision (`datetime64[ns, UTC]`) |
| Interval convention | A timestamp marks the **start** of its delivery interval ("interval beginning") |
| Local time | Delivery days, months and years are **local** (`Europe/Berlin`): convert with `.tz_convert("Europe/Berlin")` before selecting a period |
| Daylight saving | Local days have 23, 24 or 25 hours; UTC has no gaps or repeats, so every row is unique |
| Power vs energy | Columns ending `_mw` are the **average power** over the interval. Energy (MWh) = MW x interval length in hours: x 1 in the hourly files, x 0.25 in the 15-minute files |
| Prices | EUR/MWh. 1 ct/kWh = 10 EUR/MWh |
| Coverage | Delivery days 1 Jan 2023 to 30 Sep 2026 (`config/project.toml`, `[market]`) |
| Missing values | Kept as NaN, never filled silently. Only `nuclear_mw` has NaNs (see below) |
| Licence | Prices and generation: CC BY 4.0, Bundesnetzagentur / SMARD.de, via Energy-Charts (Fraunhofer ISE) |

## Data layers

| Layer | Path | In git? | Built by | Content |
|---|---|---|---|---|
| Raw | `data/raw/energy_charts/<dataset>/<YYYY-MM>.parquet` + `.json` manifest | No | `ppa-lab fetch` | Exactly what the API returned, one file per month, with checksum, parameters and licence |
| Processed | `data/processed/*.parquet` | No | `ppa-lab build` | Cleaned, de-duplicated, restricted to the configured range (the four files below) |
| Reference | `data/reference/*.csv` | **Yes** | by hand, with provenance in the file header | Small published datasets used for reconciliation |

Rebuild everything with `make all` (first download 10-15 minutes, then seconds).

---

## `prices_native.parquet`

Day-ahead clearing prices for the DE-LU bidding zone at the resolution the market
published them. **59,135 rows.**

| Column | Type | Unit | Meaning |
|---|---|---|---|
| `price_eur_mwh` | float | EUR/MWh | Clearing price of the SDAC day-ahead auction for that interval |
| `interval_min` | float | minutes | Length of the interval: **60** until 30 Sep 2025, **15** from 1 Oct 2025 |

Notes:
- Mixed resolution: 24,095 hourly rows, then 35,040 quarter-hour rows. Any average must
  be **time-weighted** (weight = `interval_min`), never a plain mean of rows.
- Price limits (harmonised SDAC): −500 to +4,000 EUR/MWh, floor −600 from delivery day
  29 May 2026. Values outside the limit in force are data errors (checked by `ppa-lab check`).
- Known break: on 26 Jun 2024 (SDAC partial decoupling) the series carries the Nord Pool
  result (daily mean 103.01 EUR/MWh); the official spot price for that day is the
  volume-weighted average of all exchanges (about 450 EUR/MWh).

## `prices_hourly.parquet`

The same prices on an hourly grid. **32,855 rows.**

| Column | Type | Unit | Meaning |
|---|---|---|---|
| `price_eur_mwh` | float | EUR/MWh | Hourly price: the native price before 1 Oct 2025; the mean of the four quarter-hour prices after |
| `n_intervals` | int | count | Native prices in the hour: 1 (hourly era) or 4 (quarter-hour era) |

Use it for hourly analysis and the exercises. For capture prices after 1 Oct 2025 use
the native file: hourly averaging loses the intra-hour price shape.

## `power_15min.parquet` and `power_hourly.parquet`

Public net electricity generation by source, plus load and trade, for Germany.
`power_15min`: **131,420 rows** (15-minute grid throughout). `power_hourly`: **32,855
rows** (hourly means of the 15-minute values). Same 22 columns in both, all `float`.

### Generation by source (MW, ≥ 0)

| Column | Meaning | 2025 energy |
|---|---|---|
| `solar_mw` | Solar PV feed-in | 70.1 TWh |
| `wind_onshore_mw` | Onshore wind | 105.1 TWh |
| `wind_offshore_mw` | Offshore wind (North Sea and Baltic) | 26.1 TWh |
| `hydro_run_of_river_mw` | Run-of-river hydro | |
| `hydro_water_reservoir_mw` | Reservoir hydro | |
| `biomass_mw` | Biomass and biogas | |
| `geothermal_mw` | Geothermal (very small) | |
| `fossil_brown_coal_lignite_mw` | Lignite | |
| `fossil_hard_coal_mw` | Hard coal | |
| `fossil_gas_mw` | Natural gas | |
| `fossil_oil_mw` | Oil | |
| `fossil_coal_derived_gas_mw` | Coke-oven and blast-furnace gas | |
| `waste_mw` | Waste incineration (about half counts as renewable) | |
| `others_mw` | Other sources | |
| `nuclear_mw` | Nuclear. **NaN from 16 Apr 2023**: the last three reactors shut down on 15 Apr 2023 | |

### Storage, trade and demand

| Column | Unit | Sign convention | Meaning |
|---|---|---|---|
| `hydro_pumped_storage_mw` | MW | ≥ 0 | Pumped storage **generating** |
| `hydro_pumped_storage_consumption_mw` | MW | **≤ 0** | Pumped storage **pumping** (consumption shown as negative) |
| `cross_border_electricity_trading_mw` | MW | **+ = net import**, − = net export | Physical cross-border balance (Germany imported 21.9 TWh net in 2025) |
| `load_mw` | MW | ≥ 0 | Grid load (demand), about 28 to 78 GW |

### Derived columns (provided by the source)

| Column | Unit | Definition |
|---|---|---|
| `residual_load_mw` | MW | `load_mw − wind_onshore_mw − wind_offshore_mw − solar_mw`; can be negative (minimum −16 GW) |
| `renewable_share_of_load_pct` | % | Renewable generation / load; above 100 % when renewable surplus is exported (maximum 152 %) |
| `renewable_share_of_generation_pct` | % | Renewable generation / total generation |

Notes:
- "Public net" generation excludes part of industrial own generation, so on average
  `load_mw` is about 3 GW larger than generation + net import + pumping.
- Wind and solar are **measured feed-in after curtailment** (grid redispatch and
  negative-price shutdowns). The TSOs' official market values use an online
  extrapolation instead; see learning track Day 2, section 4.2.
- Physics check in `ppa-lab check`: no solar output at night (catches time-zone shifts).

---

## Reference data

### `data/reference/netztransparenz_market_values_monthly.csv`

Official monthly market values (Monatsmarktwerte) of the German TSOs, Jan 2023 to Aug
2026, retrieved 8 Oct 2026 from netztransparenz.de. Lines starting with `#` are
provenance comments. Index: `month` (`YYYY-MM`).

| Column | Unit | Meaning |
|---|---|---|
| `spot_ct_kwh` | ct/kWh | Monthly mean day-ahead price ("Spotmarktpreis") |
| `wind_onshore_ct_kwh` | ct/kWh | MW Wind an Land: official capture price of onshore wind |
| `wind_offshore_ct_kwh` | ct/kWh | MW Wind auf See: official capture price of offshore wind |
| `solar_ct_kwh` | ct/kWh | MW Solar: official capture price of solar (May 2026 = corrected value) |

Load with `ppa_lab.analysis.capture.load_market_values(path)`. Annual values and other
published figures live as `[[reconciliation]]` entries in `config/project.toml`.

---

## Derived tables (computed in code, not stored)

### `capture_table(prices, power, tz, freq)` (`ppa_lab.analysis.capture`)

Index `(period, technology)`: `period` is a local `Period` (`freq="M"` or `"Y"`),
`technology` is `solar`, `wind_onshore` or `wind_offshore`.

| Column | Unit | Definition |
|---|---|---|
| `base_price_eur_mwh` | EUR/MWh | Time-weighted mean price of the period (baseload) |
| `capture_price_eur_mwh` | EUR/MWh | sum(price x energy) / sum(energy), per quarter-hour |
| `capture_rate` | ratio | capture price / base price (value factor) |
| `energy_twh` | TWh | Energy produced in the period |
| `negative_price_share` | 0 to 1 | Share of that energy produced at a negative price |

### `annual_price_stats(prices, tz)` (`ppa_lab.analysis.reconcile`)

One row per local year: time-weighted mean price, min and max, three definitions of
negative hours, longest negative streak.

---

## How to load the data

```python
import pandas as pd
from ppa_lab.config import load_settings

s = load_settings()                       # paths and timezone from config/project.toml
prices = pd.read_parquet(s.processed_dir / "prices_native.parquet")
power = pd.read_parquet(s.processed_dir / "power_15min.parquet")

local = power.tz_convert(s.timezone)      # work in local time for periods
local.loc["2025-06", "solar_mw"].sum() * 0.25 / 1e6   # solar energy June 2025, TWh
```

Interactive exploration: `notebooks/ppa_lab_playground.ipynb` (`make notebook`).
