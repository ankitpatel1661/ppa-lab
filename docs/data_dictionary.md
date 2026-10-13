# Data dictionary

Every dataset in `ppa-lab`, what each column means, its unit and its conventions.
Update this page whenever a dataset or column is added (part of the definition of done).

**Contents:** [Conventions](#conventions-that-apply-everywhere) ·
[Layers](#data-layers) · [prices_native](#prices_nativeparquet) ·
[prices_hourly](#prices_hourlyparquet) · [power_15min / power_hourly](#power_15minparquet-and-power_hourlyparquet) ·
[Reference data](#reference-data) · [Derived tables](#derived-tables-computed-in-code-not-stored) (capture, contracts, back-test) ·
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
| Raw (weather) | `data/raw/open_meteo/weather_<park>/<YYYY>.parquet` + `.json` manifest | No | `ppa-lab weather` | ERA5 weather per site and year exactly as Open-Meteo labels it, with the ERA5 grid point used |
| Processed | `data/processed/*.parquet` | No | `ppa-lab build`, `ppa-lab weather` | Cleaned, de-duplicated, restricted to the configured range (files below) |
| Reference | `data/reference/*.csv` | **Yes** | by hand, with provenance in the file header | Small published datasets used for reconciliation |

Rebuild everything with `make all` (first download of prices about 10-15 minutes and of
32 weather years per site about 5 minutes; afterwards seconds).

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

## `weather_<park>.parquet` (Day 4)

ERA5 reanalysis weather at the park's site, hourly, **interval beginning** (converted from
the API's labels). One file per park: `weather_solar_park.parquet`,
`weather_wind_park.parquet`. **278,303 hours**, 1 Jan 1995 to 30 Sep 2026.

| Column | Unit | Meaning | Converted from |
|---|---|---|---|
| `ghi_w_m2` | W/m² | Global horizontal irradiance, mean over the hour | API value labelled at the END of the hour, moved back 1 h |
| `dni_w_m2` | W/m² | Direct normal irradiance, mean over the hour | as above |
| `dhi_w_m2` | W/m² | Diffuse horizontal irradiance, mean over the hour | as above |
| `temp_air_c` | °C | Air temperature at 2 m | mean of the instants at t and t + 1 h |
| `wind_speed_10m_ms` | m/s | Wind speed at 10 m | mean of the instants at t and t + 1 h |
| `wind_speed_100m_ms` | m/s | Wind speed at 100 m | mean of the instants at t and t + 1 h |

Notes:
- ERA5 is a ~0.25° grid (about 28 × 16 km here); Open-Meteo snaps to the nearest grid point,
  recorded in the raw manifest (`grid`). Solar site: 51.75 N, 14.25 E, 68 m; wind site:
  54.50 N, 9.25 E, 30 m.
- Data-quality check on every build: irradiance must match the clear-sky sun at
  **mid-interval** (+30 min); otherwise `ppa-lab weather` stops with an error.
- Licence: CC BY 4.0 Open-Meteo.com; contains modified Copernicus Climate Change Service
  information (ERA5).

## `generation_<park>.parquet` (Day 4)

Modelled output of each illustrative park, hourly, interval beginning, same index as the
weather file.

| Column | Unit | Meaning |
|---|---|---|
| `mw` | MW | Mean AC output over the hour = **MWh produced in that hour** |

| Park | Site | Model (from `config/project.toml`) |
|---|---|---|
| `solar_park` | Lusatia, Brandenburg | pvlib: 50 MWp DC, fixed tilt 25° south, DC/AC 1.2 (41.7 MW AC), 10% losses, Faiman cell temperature, PVWatts DC/inverter |
| `wind_park` | North Frisia, Schleswig-Holstein | windpowerlib: Vestas V126-3.45 power curve scaled to 30 MW, hub height 137 m (shear from 10/100 m), 12% losses |

No grid curtailment, outages or degradation are modelled (potential output).

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

### Contract cash flows (`ppa_lab.pricing.contracts`)

Every function returns **EUR per interval to the producer**, in the shape of its inputs
(a Series with the same index, or an array of shape `(scenarios, intervals)`).
Inputs: `prices` in EUR/MWh and `volumes` in MWh per interval, on the same time grid.

| Function | Cash flow per interval |
|---|---|
| `merchant(prices, volumes)` | P · q |
| `pay_as_produced(prices, volumes, strike, pay_at_negative_prices=True)` | K · q (0 where P < 0 if the clause applies) |
| `cfd(prices, volumes, strike)` | P · q + (K − P) · q |
| `collar(prices, volumes, floor=None, cap=None)` | q · clip(P, F, C) |
| `baseload(prices, volumes, strike, band_mwh)` | K_B · B + (q − B) · P |

Fair prices (`fair_pay_as_produced_price`, `fair_baseload_price`) return one number in
EUR/MWh; `discount_factors(times, valuation, rate)` returns one factor per timestamp.

### Back-test tables (`ppa_lab.pricing.backtest`)

`backtest(prices, energy, tz, delivery_years, floor)` returns three tables:

| Table | Index | Columns |
|---|---|---|
| cash flows | `ts_utc` (delivery years) | `merchant`, `pay_as_produced`, `pap_negative_clause`, `baseload`, `merchant_with_floor` (EUR per interval) |
| strikes | `year` | `pay_as_produced_strike`, `baseload_strike` (EUR/MWh), `band_mw` (MW) |
| plan | `year` | one column per structure: expected EUR/MWh at signing |

`summarise(cash, energy, tz, plan)`: index `(year, structure)`, columns `revenue_eur_m`,
`revenue_eur_per_mwh`, `vs_merchant_eur_per_mwh`, `plan_eur_per_mwh`,
`vs_plan_eur_per_mwh` (the surprise), `worst_month_eur_k`.

`park_energy(national_mw, capacity_mw, full_load_hours, tz, years)`: MWh per interval
of an illustrative park with the national profile shape, scaled per local year.

### Volume statistics (`ppa_lab.weather.yields`, `ppa_lab.analysis.generation`)

| Function | Returns |
|---|---|
| `annual_energy(mw, tz)` | MWh per complete local year (years with at least 99.9% of their hours) |
| `p_values(annual)` | `years`, `mean`, `p50`, `std`, `cov`, `p90_1y`, `p90_10y`, `min`/`min_year`, `max`/`max_year` |
| `yield_trend(annual)` | `per_decade` (MWh), `per_decade_pct` (%) from a linear fit |
| `monthly_shares(mw, tz, years)` | share of annual energy per calendar month (1-12) |
| `site_vs_national(site, national, prices, tz, years)` | per year: `correlation`, `base_eur_mwh`, site and national capture price and rate |

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
