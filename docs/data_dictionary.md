# Data dictionary

Every dataset in `ppa-lab`, what each column means, its unit and its conventions.
Update this page whenever a dataset or column is added (part of the definition of done).

**Contents:** [Conventions](#conventions-that-apply-everywhere) ·
[Layers](#data-layers) · [prices_native](#prices_nativeparquet) ·
[prices_hourly](#prices_hourlyparquet) · [power_15min / power_hourly](#power_15minparquet-and-power_hourlyparquet) ·
[weather / generation](#weather_parkparquet-step-4) · [price_model.json](#price_modeljson-step-5) ·
[scenarios_2027](#scenarios_yearparquet-step-6) · [ppa_pricing.json / results.json](#ppa_pricingjson-step-7-and-reportsresultsjson-step-9) ·
[hedging.json](#hedgingjson-step-8) ·
[Reference data](#reference-data) · [Derived tables](#derived-tables-computed-in-code-not-stored) (capture, contracts, back-test, volumes, price paths, hedging) ·
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
| Coverage | Delivery days 1 Jan 2021 to 30 Sep 2026 (`config/project.toml`, `[market]`; from 2021 since v1.4, to include the 2022 gas crisis) |
| Missing values | Kept as NaN, never filled silently. Only `nuclear_mw` has NaNs (see below) |
| Licence | Prices and generation: CC BY 4.0, Bundesnetzagentur / SMARD.de, via Energy-Charts (Fraunhofer ISE) |

## Data layers

| Layer | Path | In git? | Built by | Content |
|---|---|---|---|---|
| Raw | `data/raw/energy_charts/<dataset>/<YYYY-MM>.parquet` + `.json` manifest | No | `ppa-lab fetch` | Exactly what the API returned, one file per month, with checksum, parameters and licence |
| Raw (weather) | `data/raw/open_meteo/weather_<park>/<YYYY>.parquet` + `.json` manifest | No | `ppa-lab weather` | ERA5 weather per site and year exactly as Open-Meteo labels it, with the ERA5 grid point used |
| Processed | `data/processed/*.parquet`, `price_model.json`, `ppa_pricing.json`, `hedging.json` | No | `ppa-lab build`, `weather`, `prices`, `scenarios`, `pricing`, `hedging` | Cleaned, de-duplicated, restricted to the configured range; calibrated model parameters; scenario, pricing and hedging results (files below) |
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
  extrapolation instead; see learning track Step 2, section 4.2.
- Physics check in `ppa-lab check`: no solar output at night (catches time-zone shifts).

## `weather_<park>.parquet` (Step 4)

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

## `generation_<park>.parquet` (Step 4)

Modelled output of each illustrative park, hourly, interval beginning, same index as the
weather file.

| Column | Unit | Meaning |
|---|---|---|
| `mw` | MW | Mean AC output over the hour = **MWh produced in that hour** |

| Park | Site | Model (from `config/project.toml`) |
|---|---|---|
| `solar_park` | Borrentin, Mecklenburg-Western Pomerania (53.81 N, 12.98 E; Encavis park, 114 MW, published as about 121 GWh a year) | pvlib: 114 MWp DC, fixed tilt 25° south, DC/AC 1.2 (95 MW AC; layout assumed), 10% losses, Faiman cell temperature, PVWatts DC/inverter |
| `wind_park` | Everswinkel, North Rhine-Westphalia (51.93 N, 7.84 E; Encavis park, 28.5 MW: 4 Nordex N149 + 1 N163, published as about 64 GWh a year) | windpowerlib: Enercon E-126 EP4 4.2 MW curve (stand-in for the N149, similar specific power) scaled to 28.5 MW, hub height 164 m (assumed; shear from 10/100 m), 12% losses |

No grid curtailment, outages or degradation are modelled (potential output).

---

## `price_model.json` (Step 5)

The calibrated stochastic price model (`ppa_lab.prices.model.PriceModel`), written by
`ppa-lab prices` and read back with `PriceModel.load(path)`. Plain JSON, about 0.3 MB. All
values except `scale` and `negative_scale` are in **transformed units** y = arcsinh(P / scale)
(for negative prices y = −a arcsinh(|P| / negative_scale)), not EUR/MWh.

| Key | Type | Meaning |
|---|---|---|
| `scale` | number, EUR/MWh | s of the arcsinh transform (120) |
| `negative_scale` | number or null, EUR/MWh | Since v1.6: b, the scale of negative prices (15); null = symmetric (files before v1.6 have no key) |
| `phi` | number | AR(1) coefficient of the daily factor, per day (half-life = ln 2 / −ln phi days) |
| `calibration` | [start, end] | First and last local day of the calibration window |
| `sigma` | {season: number} | Standard deviation of the daily shocks per season (`winter`, `spring`, `summer`, `autumn`) |
| `profile` | list of [season, daytype, hour, value] | Daily shape S: 4 seasons x 3 day types (`weekday`, `saturday`, `holiday` = Sunday or nationwide holiday) x 24 local hours = 288 rows |
| `month_shape` | {month 1-12: number} | Average monthly level minus the annual level (used for future years) |
| `levels` | {"YYYY-MM": number} | Fitted level L of each month of the calibration window |
| `pool_season` | list of strings | Season of each historical day in the resampling pool (998 days) |
| `pool_z` | list of numbers | That day's standardised daily shock z (mean about 0, sd about 1) |
| `pool_u` | list of 24-number lists | That day's intraday pattern u: deviation of each local hour from the day's level |
| `pool_days` | list of dates | Since v1.7: the local date of each pool day (to move it to the simulated day) |
| `intraday_trend` | {season: 24 numbers} | Since v1.7, when `[price_model] intraday_trend` is on: tau, the change per year of the hourly deviation from the day's mean (transformed units per year) |

Only complete 24-hour local days enter the pool (days with a daylight-saving change have 23
or 25 hours and are left out).

---

## `scenarios_<year>.parquet` (Step 6)

Joint weather x price scenarios for the delivery year of `[price_model]`, written by
`ppa-lab scenarios`; input for Step 7. One row per scenario, twice: once with prices linked to
the weather, once with prices independent of it (Step 5 model). Default: 31 weather years x
16 paths = 496 scenarios per variant.

| Column | Unit | Meaning |
|---|---|---|
| `scenario` (index) | – | 0 .. S-1 within each variant; scenarios of one weather year are consecutive |
| `prices` | text | `linked` (Step 6) or `independent` (Step 5) |
| `weather_year` | year | Weather year whose output and (if linked) weather the scenario uses |
| `base_price` | EUR/MWh | Time-weighted average price of the delivery year in this scenario |
| `<park>_mwh` | MWh | Energy of the park in the delivery year (`solar_park`, `wind_park`) |
| `<park>_revenue_eur` | EUR | Merchant revenue: sum over hours of MWh x price |
| `<park>_capture_price` | EUR/MWh | `revenue / mwh` |
| `<park>_capture_rate` | – | `capture_price / base_price` |

Fair pay-as-produced price over all scenarios: `sum(revenue) / sum(mwh)`, not the mean of
the capture prices (`ppa_lab.scenarios.generator.fair_price`). Hourly prices are not stored
(496 x 8,760 values); rebuild them with `build_scenarios` and the same seed.

---

## `out_of_sample.json` (Step 6, v1.6)

The out-of-sample test written by `ppa-lab scenarios` when `[scenarios] out_of_sample_years`
is set; Step 7 reads `bias`.

| Key | Meaning |
|---|---|
| `train_start` | First day of every fit |
| `years[]` | Per test year: `year`, `test` (first and last local day), `trend` (whether the fit could estimate a build-out trend), `inside` of `statistics` (statistics with history inside the 5-95% range), `table` (per statistic: `history`, `simulated_mean`, `simulated_p05`, `simulated_p95`); since v1.7 `inside_no_trend` |
| `years[].parks.<park>` | Out of sample: `capture_rate` and `negative_output_share` (output share at negative prices), each with `history`, `p05`, `p50`, `p95` over the paths |
| `years[].seen.<park>` | The same for the model that has seen the test year |
| `years[].no_trend.<park>` | Since v1.7: the same for the model without the build-out trend |
| `bias.<park>` | `capture_rate`: mean of median minus history over the test `years` fitted like the delivery year (with a trend when one is configured); `all_years`, `min`, `max` over all test years; `seen` and `no_trend`: the means of those variants |

---

## `ppa_pricing.json` (Step 7) and `reports/results.json` (Step 9)

Key pricing results, written by `ppa-lab pricing`; input for Step 9. `ppa-lab memo` copies
them to `reports/results.json` (committed, plus `ppa_lab_version` and, if present, the Step 8
`hedging` results), which the dashboard reads.
Strict JSON: missing values are `null`. All prices in EUR/MWh,
revenues in EUR, energies in MWh, for the first delivery year unless stated.

| Key | Meaning |
|---|---|
| `delivery_year`, `tenor_years` | First delivery year and contract length |
| `analog_pool_start` | First historical day used for intraday patterns (the configured base case) |
| `scenarios` | Number of joint scenarios |
| `forward` | The delivery year's Cal base forward: `price_eur_mwh`, `date` (trading day of the quote) and `source` (URL); `date` and `source` are null for an assumed forward. Since v1.2 also `quarters` (quarter `"1"`..`"4"` → forward, EUR/MWh: the market's seasonal shape at the Cal level) and `quarters_date`. Results before v1.1 have `forward_assumption` (85.0) instead |
| `forward_curve` | Cal base forwards of later contract years, `{"2028": ..., "2029": ...}` (EUR/MWh); years after the last one keep it |
| `recent_level_eur_mwh` | Average day-ahead price of the analog pool (the recent regime) |
| `level_grid` | Since v1.5: per forward at which the scenarios were rebuilt, `forward` (configured), `average` (the scenarios' average price) and `capture_rate` per park |
| `level_effect` | Since v1.5: `start_year` of the history regression, `first_year` and `last_year` of the data |
| `parks.<park>.premia_eur_mwh` | `fair_price`, `unhedged`, `joint` (after the baseload hedge), `profile`, `volume` |
| `parks.<park>.stack_eur_mwh` | `forward` (scenario average), `shape`, `fair_price`, `risk_premium`, `balancing`, `credit`, `indicative` |
| `parks.<park>.structures.<structure>` | `fair_price_eur_mwh`, `expected_revenue_eur`, `p05_revenue_eur`, `cfar_eur`, `cfar_share`, `floor_value_eur_mwh` for `merchant`, `pay_as_produced`, `pay_as_produced_clause`, `merchant_floor`, `baseload` |
| `parks.<park>.energy_mwh_expected`, `p50_mwh`, `p90_1y_mwh` | Expected energy over the scenarios; P50 and one-year P90 over the weather years (Step 4) |
| `parks.<park>.tenor` | `years`, `fair_price` and `indicative` for the tenor (along the forward curve), and `sensitivity` (one row per case; the forward cases shift the whole curve and move the capture rate with it) |
| `parks.<park>.level_response` | Since v1.5: `level` (scenario average prices, increasing) and `capture_rate`: the model's capture rate by price level, read linearly in ln(level) by `level_shift` |
| `parks.<park>.level_effect` | Since v1.5: `ref_level`, `ref_rate` (the recent level and its capture rate), `slope_recent` and `slope_tenor` (the model's slope per unit of ln level), `history` and `history_all_years` (regression: `coef`, `se`, `t`, `ci_low`, `ci_high`, `share_coef`, `r2`, `n`; null without power data), `history_years`, `share_pace` (`from`, `to`, `per_year`), `tenor_fair_without_level_effect`; since v1.6 `out_of_sample_error` (Step 6's mean capture-rate error, null without `out_of_sample.json`); since v1.7 `trend_implied_drift` (capture-rate change if the build-out trend ran one more year, at the same forward) |
| `parks.<park>.whole_window` | `fair_price` and `premium` with analog days from the whole calibration window |
| `parks.<park>.assumptions` | `balancing_eur_mwh`, `credit_eur_mwh`, `capture_rate_drift`, `degradation` (from `[ppa.parks.*]`) |
| `discount_rate` | annual discount rate of the tenor price |

---

## `hedging.json` (Step 8)

Written by `ppa-lab hedging`; `ppa-lab memo` copies it into `reports/results.json` as `hedging`.
Strict JSON. Same scenarios as `ppa_pricing.json`. Prices EUR/MWh, revenues EUR, amounts MW
(year average).

| Key | Meaning |
|---|---|
| `delivery_year` | Delivery year of the scenarios |
| `model_forwards` | `cal_base`, `cal_peak`, `Q1`..`Q4`: mean scenario price over the product's hours |
| `market_quotes` | List of `product`, `delivery_year`, `price_eur_mwh`, `date`, `source` (URL) from `[hedging.market_quotes]` |
| `parks.<park>.average_mw`, `p50_mw` | Expected output over the scenarios / P50 historical output, as average MW |
| `parks.<park>.strategies.<strategy>` | `hedge_mw`, `hedge_ratio`, `expected_eur`, `cfar_eur`, `cfar_reduction`, `effectiveness` for `none`, `cal_base_50`, `cal_base_100`, `cal_base_min_variance`, `quarters_min_variance`, `months_min_variance` |
| `parks.<park>.quarters_min_variance_mw`, `months_min_variance_mw` | MW per product of the multi-product minimum-variance hedges (can be negative) |
| `parks.<park>.buyer` | `band_mw` (Step 7 band), `min_variance_mw`, `min_variance_ratio`, `premium_full_band`, `premium_min_variance` (EUR/MWh) |
| `parks.<park>.backtest.<year>` | `forward_proxy` (previous year's average), `realised_base`, `merchant_revenue_eur`, `hedge_pnl_eur`, `hedged_revenue_eur` |
| `parks.<park>.market_check` | `quote`, `date` (latest Cal base quote), `model_forward`, `indicative_model`, `indicative_market` (EUR/MWh) |

---

## Reference data

### `data/reference/netztransparenz_market_values_monthly.csv`

Official monthly market values (Monatsmarktwerte) of the German TSOs, Jan 2021 to Aug
2026, retrieved 8 Oct 2026 (2021-2022: 15 Oct 2026) from netztransparenz.de. Lines starting with `#` are
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

`park_energy(national_mw, capacity_mw, full_load_hours, tz, years)` scales a national profile to a park; `site_energy(generation_mw, grid)` puts a park's hourly Step 4 output on the price grid (each quarter-hour gets the hour's MW × 0.25 h). `backtest(prices, energy, tz, delivery_years, floor)` returns three tables:

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

### Price model outputs (`ppa_lab.prices`)

| Function | Returns |
|---|---|
| `calendar_features(index, tz)` | per timestamp: local `hour`, `month`, `season`, `daytype` (`weekday` / `saturday` / `holiday`), `year` |
| `german_holidays(year)` | set of the nine nationwide public holidays (dates) |
| `simulate(model, index, tz, n_paths, annual_level, seed, level_volatility)` | NumPy array **paths x hours**, EUR/MWh, columns in the order of `index` (UTC, interval beginning) |
| `simulate_daily_factor(...)` | array paths x local days: the daily factor D (transformed units) |
| `calibrate_level(model, index, tz, target_price, n_paths, seed)` | the annual level (transformed units) at which `simulate(..., seed=seed)` averages `target_price` |
| `price_statistics(prices)` | `mean`, `std`, `p01`, `p05`, `p50`, `p95`, `p99`, `negative_share` |
| `compare_with_history(history, paths)` | one row per statistic (above, plus `acf_1h`, `acf_24h`, `acf_168h`): `history`, `simulated_mean`, `simulated_p05`, `simulated_p95`, `inside_range` |

The same `seed` always gives the same paths. A simulated row is one possible delivery year,
not a forecast of a particular hour.

### Joint scenarios (`ppa_lab.scenarios`)

| Function | Returns |
|---|---|
| `daily_features(solar_mw, wind_mw, temp_c, ...)` | per local day: `solar`, `wind` (capacity factors, 0-1), `temp` (°C) |
| `day_hour_matrix(mw, tz)` | local day x 24 local hours (25-hour days averaged, 23-hour days interpolated) |
| `monthly_climatology(features, first, last)` | month (1-12) x feature: average weather over the weather years |
| `fit_link(model, prices, features, climatology, tz, window_days, k)` | `WeatherLink`: `beta` (season x const/solar/wind/temp, transformed units per unit of feature), `r_squared`, `phi`, `sigma`, analog pool (`pool_days`, `pool_features`, `pool_xi`, `pool_u`) |
| `analog_days(link, day, weather_row, exclude_days)` | pool indices of the k nearest days within ±window of the date |
| `simulate_linked(model, link, index, tz, weather, n_paths, annual_level, seed, ...)` | paths x hours, EUR/MWh, for the given daily weather |
| `out_of_sample(prices, features, generation, climatology, tz, scale, train_start, test_start, test_end, ..., negative_scale, seen)` | v1.6: fit on the days before the test period (or including it, `seen=True`), simulate it with its real weather and each quarter at its realised mean: `statistics` (as `compare_with_history`), per park capture rate and output share at negative prices (history, p05, p50, p95), `paths` |
| `park_statistics(prices, volumes)` | per price path: a park's capture rate and its output share at negative prices |
| `build_scenarios(...)` | `Scenarios`: `prices` (S x hours), `generation` (weather years x hours per park), `weather_years`, `year_row`, `level`, `linked` |
| `scenario_table(scenarios, parks)` | the columns of `scenarios_<year>.parquet` |

### Pricing and risk (`ppa_lab.pricing.risk`)

| Function | Returns |
|---|---|
| `cash_flow_at_risk(cash, quantile)` | expected cash flow minus its quantile (EUR) |
| `premium(values, energy, quantile)` | (expected value − quantile) / expected energy (EUR/MWh) |
| `buyer_value(prices, volumes, strike, forward, band_mw)` | per scenario: Σ q (P − K), plus a baseload hedge B Σ (F − P) if given |
| `risk_premia(prices, volumes, quantile)` | `fair_price`, `unhedged`, `joint`, `profile`, `volume` (EUR/MWh) |
| `structure_revenues(prices, volumes, floor)` | structure → (strike, annual revenue per scenario) |
| `structure_table(prices, volumes, floor, quantile)` | per structure: fair price, expected and P5 revenue, CFaR, CFaR share, floor value |
| `tenor_price(fair_price, forward, energy_mwh, start_year, years, discount_rate, ..., forward_curve, level_response)` | per year: forward (first year, then the curve, flat after its last year), capture rate (moved along `level_response` when given), fair price, energy, discount factor; tenor price in `.attrs["price"]` |
| `level_shift(response, level_from, level_to)`, `capture_rate_at(response, level)` | change of the capture rate between two price levels, and the capture rate at one level, from a level response (linear in ln level, flat beyond its ends) |

### Hedging (`ppa_lab.hedging`)

| Function | Returns |
|---|---|
| `product_masks(index, tz)` | product → boolean mask over the hours: `cal_base`, `cal_peak` (Mon-Fri 08-20 local), `Q1`..`Q4`, `M01`..`M12` |
| `model_forwards(prices, masks)` | product → mean scenario price over its hours (EUR/MWh) |
| `hedge_payoffs(prices, masks, forwards, products)` | array (scenarios, products): Σ over the product's hours of (F − P), EUR per MW sold |
| `min_variance_hedge(cash, payoffs)` | MW per product minimising Var(cash + payoffs · h) |
| `hedge_strategies(cash, prices, masks, forwards, average_mw, quantile)` | per strategy: MW, hedge ratio, expected revenue, CFaR, CFaR reduction, effectiveness, MW per product |
| `buyer_hedge(prices, volumes, quantile)` | the PPA buyer's full and minimum-variance band and premia |
| `backtest_hedge(prices, mw, tz, years, hedge_mw)` | per year: forward proxy, realised base, merchant revenue, hedge P&L, hedged revenue |

### `annual_price_stats(prices, tz)` (`ppa_lab.analysis.reconcile`)

One row per local year: time-weighted mean price, min and max, three definitions of
negative hours, longest negative streak.

### Capture rate vs price level (`ppa_lab.analysis.level_effect`, v1.5)

| Function | Returns |
|---|---|
| `monthly_panel(prices, power, tz, columns)` | per local month: `base` (mean price) and per technology `capture_rate_<tech>` and `share_<tech>` (generation over load); months with missing hours dropped |
| `level_regression(panel, tech, start_year)` | OLS of the capture rate on ln(base) and the share of load with month effects, HC1: `coef`, `se`, `t`, `ci_low`, `ci_high`, `share_coef`, `r2`, `n`; None when the data cannot separate the effects |
| `share_pace(power, tz, column, first_year)` | growth of a technology's share of load per year, from `first_year` − 1 to the last complete year: `from`, `to`, `per_year` |

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
