# ppa-lab: Renewable PPA Pricing & Risk Engine

[![CI](https://github.com/ankitpatel1661/ppa-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/ankitpatel1661/ppa-lab/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Licence MIT](https://img.shields.io/badge/licence-MIT-green)
[![Open the dashboard](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://ppa-lab.streamlit.app)

**What fixed price should a renewable producer offer an industrial buyer for ten years of
solar or wind output, and how much risk is left in that deal?**

`ppa-lab` answers that question with public data and transparent, tested methods: German
day-ahead prices and generation, 31 years of ERA5 weather at two real sites, a stochastic
price model, prices and weather simulated together, and the standard PPA structures priced
with their market, shape and volume risks.

## The answer

> *For a 10-year pay-as-produced PPA (2027-2036) from Encavis's 114 MWp solar park in Borrentin
> (Mecklenburg-Western Pomerania), the fair price before risk premia is **55.5 EUR/MWh** (first
> year: forward 141.0 × expected capture rate 0.61 = 86.0; later years follow the falling
> forward curve and a capture rate that falls 1 percentage point a year). After a profile and
> volume risk premium of 8.3 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the
> indicative price is **44.7 EUR/MWh**. Expected annual energy is 120.9 GWh (P50, matching the
> published ~121 GWh; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk
> falls from EUR 3.68 m (merchant) to EUR 0.77 m per year.*

**The parks** are two Encavis parks, modelled from public data only: the **Borrentin** solar
park (114 MWp, grid-connected December 2024, about 121 GWh a year, PPA with Allego) and the
**Everswinkel** wind park (28.5 MW, 4 Nordex N149 + 1 N163, about 64 GWh a year, EEG tariff),
as described in Encavis press releases. Site details that are not published are stated
assumptions, and the site models are calibrated to the published annual yields. The results
are illustrative and say nothing about the parks' actual contracts: Borrentin already sells its
output to Allego under a 10-year PPA that started in December 2024, so the PPA priced here
(2027-2036) is a hypothetical re-pricing at today's market, and Everswinkel is paid under the
EEG, so its PPA price is a what-if.

**Forward:** the EEX German Power Cal-27 base quote of 9 Oct 2026, **140.21 EUR/MWh**, with
each quarter at the market's seasonal shape (Q1 185, Q2 118, Q3 124, Q4 134 EUR/MWh); later
years follow the curve (Cal-28 104.75, Cal-29 87.58, then held flat)
([what changed](docs/learning_track/step08_hedging.md#46-update-v11-the-forward-is-now-the-markets)).

![From the forward price to an indicative PPA price, solar and wind](reports/figures/step07_price_stack.png)

| EUR/MWh | Borrentin solar (114 MWp) | Everswinkel wind (28.5 MW) |
|---|---|---|
| Forward 2027 (scenario average) | 141.0 | 141.0 |
| Fair pay-as-produced price 2027 | 86.0 | 129.3 |
| Buyer's risk premium after a baseload hedge (without hedge) | 8.3 (28.9) | 5.5 (35.0) |
| of which profile / volume | 7.5 / 0.8 | 1.9 / 3.7 |
| Fair price, 10 years along the forward curve | 55.5 | 88.5 |
| **Indicative price, 10 years** (after premium, balancing and credit costs) | **44.7** | **80.0** |
| Producer's CFaR95 in 2027: merchant → pay-as-produced | EUR 3.68 m → 0.77 m | EUR 2.16 m → 0.96 m |

- **The curve matters as much as the level:** 2027 trades at 141, but the discount- and
  energy-weighted forward over ten years is 97 EUR/MWh, so the ten-year price sits far below
  the first year's.
- **The market's winter premium hurts solar and helps wind:** solar produces in the cheaper
  Q2 and Q3 (capture rate 0.61), wind in the expensive winter (0.92).
- **Most of the buyer's risk is hedgeable:** a baseload forward removes 71-84% of it. Solar's
  residual risk is profile, wind's is volume.
- **Prices must see the weather:** simulated independently of it, the wind park would earn
  almost the baseload price (fair price 148 instead of 129 EUR/MWh in Step 6).
- **The biggest levers are the forward and the view on cannibalisation:** the forward curve
  (±5.5 EUR/MWh for ±10%), whether the capture rate rises with the price level as the model
  says (−7.2 if it stays at the recent level's), which historical days represent 2027 (+5.8
  with the whole 2024-2026 window), the capture-rate trend (±3.5 per pp per year).
- **Hedging the unsold output:** Cal base futures for 84% (solar) and 90% (wind) of the average
  output cut the merchant cash flow at risk by 75% and 51% (Step 8).

**Read more:** [one-page management memo](reports/step09_memo.md) ([PDF](reports/step09_memo.pdf))
· [methodology](METHODOLOGY.md) · [Step 7 report](reports/step07_ppa_pricing.md) ·
[Step 8 hedging report](reports/step08_hedging.md) ·
**try your own assumptions** in the [live dashboard](https://ppa-lab.streamlit.app) (or locally:
`make app`).

## How it works, in nine steps

| Step | Question | Key result | Report | Learn |
|---|---|---|---|---|
| 1 | Can we trust the market data? | Mean prices 2021-2025 match the published values, incl. 235.45 EUR/MWh in 2022 | [report](reports/step01_market_data.md) | [page](docs/learning_track/step01_market_data_foundation.md) |
| 2 | What do solar and wind really earn? | Solar capture rate 0.94 in the 2022 gas crisis → 0.51 in 2025, matches official market values | [report](reports/step02_capture_prices.md) | [page](docs/learning_track/step02_capture_prices.md) |
| 3 | How does each PPA structure move risk? | Pay-as-produced removes price surprise; baseload leaves shape risk | [report](reports/step03_ppa_structures.md) | [page](docs/learning_track/step03_ppa_structures.md) |
| 4 | How much do the parks produce? | Borrentin P50 121 GWh, Everswinkel 64 GWh (calibrated to the published yields); P90 −6 to −9% | [report](reports/step04_generation.md) | [page](docs/learning_track/step04_weather_to_power.md) |
| 5 | Which price years are plausible? | Prices forget in about a day; validated against history | [report](reports/step05_price_model.md) | [page](docs/learning_track/step05_price_model.md) |
| 6 | How do weather and prices move together? | Windy days are cheap days: wind fair price 148 → 129 EUR/MWh | [report](reports/step06_joint_scenarios.md) | [page](docs/learning_track/step06_joint_scenarios.md) |
| 7 | What price, and how much risk is left? | 44.7 EUR/MWh indicative over ten years; CFaR −79% with the PPA | [report](reports/step07_ppa_pricing.md) | [page](docs/learning_track/step07_ppa_pricing.md) |
| 8 | How much to sell forward, and is our forward right? | Cal base at 84% of output cuts merchant CFaR by 75% (solar); the forward is now the market's curve and seasonal shape | [report](reports/step08_hedging.md) | [page](docs/learning_track/step08_hedging.md) |
| 9 | How do we tell management? | One-page memo and a dashboard with live assumptions | [memo](reports/step09_memo.md) | [page](docs/learning_track/step09_memo_dashboard.md) |

Every step has tests, a report, a learning-track page, a notebook section and exercises.

## Run it yourself

```bash
make setup     # create .venv and install the project with dev tools
make test      # 240 offline tests, about 30 seconds
make all       # download data and weather, build datasets, check quality, write all reports
make app       # the dashboard (reads the committed results; no download needed)
```

Explore the data interactively in the playground notebook (one section per step):

```bash
make notebook       # opens notebooks/ppa_lab_playground.ipynb in JupyterLab
```

Every dataset and column is described in the [data dictionary](docs/data_dictionary.md).

Or step by step with the command-line tool:

```bash
.venv/bin/ppa-lab fetch     # download monthly raw files (cached, rate-limit aware)
.venv/bin/ppa-lab build     # build processed Parquet datasets
.venv/bin/ppa-lab check     # data-quality checks; exit code 1 on failure
.venv/bin/ppa-lab report    # reports/step01_market_data.md + figures
.venv/bin/ppa-lab capture   # reports/step02_capture_prices.md + figures
.venv/bin/ppa-lab ppa       # reports/step03_ppa_structures.md + figures
.venv/bin/ppa-lab weather   # ERA5 weather -> park generation -> reports/step04_generation.md
.venv/bin/ppa-lab prices    # price model: fit, validate, simulate -> reports/step05_price_model.md
.venv/bin/ppa-lab scenarios # weather x price scenarios -> reports/step06_joint_scenarios.md
.venv/bin/ppa-lab pricing   # PPA prices, risk premia, CFaR -> reports/step07_ppa_pricing.md
.venv/bin/ppa-lab hedging   # futures hedges, buyer's hedge, market check -> reports/step08_hedging.md
.venv/bin/ppa-lab memo      # one-page memo + reports/results.json for the dashboard
```

The first download takes 10 to 15 minutes because the free API is rate limited;
later runs use the local cache and finish in seconds.

## Project structure

```
config/project.toml          every assumption in one place (market, dates, limits, references)
src/ppa_lab/
  config.py                  typed settings
  timeutils.py               UTC, daylight saving, mixed 60/15-minute resolution
  data/energy_charts.py      API client (timeouts, retries, Retry-After) + pure parsers
  data/store.py              raw cache: monthly Parquet + manifest (checksum, licence)
  data/pipeline.py           fetch months, build processed datasets
  data/quality.py            data-quality checks (DST-aware completeness, price limits, physics)
  analysis/reconcile.py      annual statistics and tie-out against published figures
  analysis/step01_report.py   Step 1 report and charts
  analysis/capture.py        capture prices and rates, official market-value comparison
  analysis/step02_report.py   Step 2 report and charts
  analysis/plotting.py       shared chart style
  analysis/step03_report.py   Step 3 report and charts
  pricing/contracts.py       cash flows of every PPA structure, fair prices, discounting
  pricing/backtest.py        historical back-test: parks, prior-year strikes, plan and surprise
  data/http.py               shared JSON client: timeouts, retries, Retry-After
  data/open_meteo.py         ERA5 weather client; end-of-hour -> interval-beginning conversion
  data/weather_pipeline.py   weather per site and year (raw cache) -> park generation
  weather/pv.py, wind.py     pvlib solar park, windpowerlib wind park
  weather/yields.py          annual energy per weather year, P50/P90
  analysis/generation.py     trend and checks against national data
  analysis/step04_report.py   Step 4 report and charts
  prices/calendar.py         local hour, season, day type, German holidays (Easter computed)
  prices/model.py            arcsinh price model: fit, simulate, calibrate the level to a forward
  prices/validation.py       simulated vs historical statistics
  analysis/step05_report.py   Step 5 report and charts
  scenarios/weather.py       daily weather features, day x hour generation, calendar mapping
  scenarios/link.py          weather-price link: response per season + analog days
  scenarios/generator.py     weather years x price paths, fair price
  analysis/step06_report.py   Step 6 report and charts
  pricing/risk.py            structures on scenarios, CFaR, risk premia, ten-year price
  analysis/step07_report.py   Step 7 report and charts
  hedging/products.py        EEX products: Cal base and peak, quarters, months (local time)
  hedging/hedge.py           hedge payoffs, minimum-variance hedges, strategies, back-test
  analysis/step08_report.py   Step 8 report, charts and market check
  analysis/step09_memo.py    one-page memo and the dashboard's results file
  dashboard.py               dashboard logic (tested): an offer for any assumptions
  cli.py                     `ppa-lab` command
app/streamlit_app.py         the dashboard (`make app`; app/requirements.txt for Streamlit Cloud)
tests/                       offline tests with real API fixtures
notebooks/                   ppa_lab_playground.ipynb: interactive, one section per step
data/reference/              small published reference data (official market values)
exercises/                   hands-on exercises with automatic checks
METHODOLOGY.md               the pricing maths, conventions, assumptions and limitations
docs/decisions/              architecture decision records (ADRs)
docs/learning_track/         step-by-step explanations of what was built and why
reports/                     generated reports and figures
scripts/build_docs.py        learning-track Markdown -> PDF (`make docs`)
```

## Results by step

### Step 8 results: how much to sell forward

The parks' output sold at spot in 2027 (496 scenarios), and with EEX futures sold at the
model's forward. Hedge ratio = MW sold / average output.

| 2027, merchant output | Borrentin solar (114 MWp) | Everswinkel wind (28.5 MW) |
|---|---|---|
| CFaR95, no hedge | EUR 3.68 m | EUR 2.16 m |
| Cal base, 100% of average output | EUR 1.29 m | EUR 1.12 m |
| **Cal base, minimum-variance** | **EUR 0.94 m** (11.5 MW, 84%) | **EUR 1.05 m** (6.5 MW, 90%) |
| Months, minimum-variance | EUR 0.74 m | EUR 0.70 m |
| PPA buyer's premium: full band → minimum-variance band | 8.30 → 5.32 EUR/MWh | 5.50 → 5.26 EUR/MWh |

- **One product does most of the work:** Cal base at 84-90% of the average output. Wind keeps
  more risk after the hedge (−51%): its volume varies more (P90 −9%).
  Monthly hedges from 496 scenarios mostly fit noise (some months even negative).
- **Judge a hedge by the risk it removes:** back-tested at the previous year's average price,
  the solar hedge earned EUR +1.69 m in 2024 and lost EUR 1.09 m in 2025.
- **Market check, and a decision:** published Cal-27 base quotes rose from 104.24 EUR/MWh
  (31 Jul 2026) to 140.21 (9 Oct) against the 85 the model assumed. Since v1.1 the model's
  forward is the market's, along the curve (Cal-28 104.75, Cal-29 87.58), and since v1.2 each
  quarter follows the market's seasonal shape (Q1-27 179.47 vs Q2-27 114.04 on 14 Sep, scaled
  to the Cal level).

Full report: [`reports/step08_hedging.md`](reports/step08_hedging.md).

### Step 6 results: prices that see the weather

Every weather year 1995-2025 is paired with 16 price paths for 2027 (496 scenarios). Prices
are simulated **for** that weather: the daily level responds to solar, wind and temperature
anomalies (a regression per season), and the hourly shape comes from historical days with
similar weather (analog days).

| 2027, Cal-27 forward 140.21 EUR/MWh, market quarter shape | Borrentin solar (114 MWp) | Everswinkel wind (28.5 MW) |
|---|---|---|
| Fair pay-as-produced price, prices independent of weather (Step 5) | 97.64 EUR/MWh | 148.31 EUR/MWh |
| Fair pay-as-produced price, **prices linked to weather (Step 6)** | **94.45 EUR/MWh** | **129.46 EUR/MWh** |
| Capture rate 5/50/95%, linked | 0.61 / 0.67 / 0.72 | 0.87 / 0.92 / 0.95 |

- **Ignoring the link is a gift to the seller:** 19 EUR/MWh (13%) for wind, 3 EUR/MWh for
  solar. Within a month, Everswinkel's wind and the daily price correlate at −0.69 (2025); the
  Step 5 model, which ignores the weather, has no such link.
- **The biggest open assumption** is which historical days represent 2027: with analogs from
  the last 12 months only, the solar price drops from 94.5 to 86.0 EUR/MWh (deeper midday dips
  as solar capacity grows). Step 7 uses the last 12 months.
- Capture rates are higher than in 2025 (solar 0.555) partly because of the level: in this
  model the capture rate rises with the price level (see the Step 8 update).

Full report: [`reports/step06_joint_scenarios.md`](reports/step06_joint_scenarios.md).

### Step 5 results: thousands of plausible price years

An hourly model of German day-ahead prices, fitted on 2024-01 to 2026-09 (24,095 hours):
arcsinh-transformed prices = monthly level + daily shape (season x day type x hour, with
the nine nationwide holidays) + a daily factor that reverts like an Ornstein-Uhlenbeck
process + intraday patterns resampled as whole historical days.

| | |
|---|---|
| Memory of the daily factor | phi = 0.521 per day, **half-life 1.06 days** |
| Validation (history inside the 5-95% range of 200 simulated paths) | **7 of 11** statistics: mean, spread, 5/50/95/99% quantiles, weekly autocorrelation |
| Still outside | 1% quantile and negative hours (6.2% in history, 4.9% in the model), autocorrelation at 1 and 24 hours |
| 2027 at the Cal-27 forward of 140.21 EUR/MWh (500 paths) | annual average 5% / 50% / 95%: 104.9 / 139.3 / 181.3 EUR/MWh; 1.3% negative hours |
| Solar capture rate, 2025 weather | **0.719** with simulated 2027 prices vs **0.555** with the real 2025 prices (at 89 EUR/MWh: part of the gap is the level) |

- **Validation changed the model twice.** A textbook hourly AR(1) forgot yesterday within
  ten hours (24-hour autocorrelation 0.38-0.54 vs 0.70) and was replaced by the two-factor
  version; a wider search of the transform's scale moved it from 80 to 120 EUR/MWh
  (5 to 7 statistics inside).
- **The gap that matters:** within a month, sunnier days have cheaper middays (correlation
  −0.30 in 2025); in the model it is 0.00. Independent prices overstate what solar earns.
  Step 6 links weather and prices.

Full report: [`reports/step05_price_model.md`](reports/step05_price_model.md).

### Step 4 results: how much the parks produce, and how much that varies

The two Encavis parks, modelled hour by hour from ERA5 reanalysis weather (1995-2025) with
pvlib and windpowerlib:

| | Borrentin solar (114 MWp) | Everswinkel wind (28.5 MW) |
|---|---|---|
| P50 annual energy | 120.9 GWh = 1,061 kWh/kWp (published: ~121) | 64.0 GWh = 2,245 full-load hours (published: ~64) |
| Year-to-year variability (CoV) | 4.6% | 7.2% |
| P90, one year / 10-year average | −5.9% / −1.9% vs mean | −9.2% / −2.9% vs mean |
| Worst / best weather year | 1998: −8.9% / 2018: +10.1% | 2010: −13.5% / 1998: +13.6% |
| Trend 1995-2025 | +2.1% per decade (brightening) | −1.7% per decade |
| Hourly correlation with the national fleet | 0.91-0.93 | 0.86-0.88 |

- **Calibrated to the published yields:** the physical models gave 124.3 GWh for solar
  (+2.8%) and 76.5 GWh for wind (+19.5%). As a pricing desk combines a yield assessment (the
  level) with reanalysis data (variability and hourly shape), the losses are calibrated so that
  the P50 matches. The wind gap covers what the model cannot see: sound-reduced night operation
  and bat curtailment, common in NRW, a stand-in power curve (no Nordex N149 curve in the
  library) and ERA5 winds extrapolated to a 164 m hub.
- **Checked against national data** and priced like Step 2: site capture rates close to the
  national ones in every year 2021-2025, the 2022 crisis included (average: solar 0.731 vs
  0.718, wind 0.805 vs 0.812).
- **A trap found and fixed:** ERA5 radiation from Open-Meteo is labelled at the end of its
  hour (shifted, and verified against the sun's position on every build).

Full report: [`reports/step04_generation.md`](reports/step04_generation.md).

### Step 3 results: what each PPA structure would have earned

The Borrentin solar park (114 MWp) and the Everswinkel wind park (28.5 MW), here with the
national generation profiles of their technology scaled to their published yields, sign each
contract at the end of the previous year at last year's fair price, and deliver in 2024 and
2025.
Revenue per MWh produced; cash flows to the producer:

| EUR/MWh | Merchant | Pay-as-produced | PaP, no pay at negative prices | Baseload | Merchant + floor 0 |
|---|---|---|---|---|---|
| Solar 2024 | 46.48 | **72.25** | 59.04 | 63.14 | 49.26 |
| Solar 2025 | 45.95 | 46.48 | 35.22 | **35.14** | 49.25 |
| Wind 2024 | 64.54 | 78.44 | 73.50 | **81.20** | 65.03 |
| Wind 2025 | **77.27** | 64.54 | 59.63 | 66.46 | 77.71 |

- **A pay-as-produced PPA removes all price surprise** (realised minus the expectation at
  signing is 0.00 in every case); whether it beats merchant is hindsight.
- **A baseload PPA hedges the price level, not the shape:** on the solar park in 2025 it
  fell 11.34 EUR/MWh short of plan, worse than merchant, and produced a negative month.
- **A negative-price clause cost solar 11.26 EUR/MWh in 2025** (24% of the energy unpaid);
  the right to curtail at negative prices was worth 3.30 EUR/MWh.
- **With each park's own profile** (Step 4 site models instead of the national shape):
  Borrentin earned 48.38 EUR/MWh merchant in 2025 (national solar shape 45.95), Everswinkel
  76.34 (national onshore shape 77.27); the structures rank the same way.

Full report: [`reports/step03_ppa_structures.md`](reports/step03_ppa_structures.md);
the maths: [`METHODOLOGY.md`](METHODOLOGY.md).

### Step 2 results: what solar and wind really earn

The capture price is the energy-weighted price a technology earns:
sum(price x energy) / sum(energy) per quarter-hour. The capture rate divides it by the
baseload price.

| Capture rate (capture price, EUR/MWh) | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|---|---|---|
| Baseload price | 96.85 | 235.45 | 95.18 | 78.51 | 89.32 | 107.72 |
| Solar | 0.79 (75.99) | 0.94 (220.99) | 0.76 (72.25) | 0.59 (46.48) | 0.51 (45.95) | 0.52 (55.68) |
| Wind onshore | 0.83 (80.74) | 0.71 (168.31) | 0.82 (78.44) | 0.82 (64.54) | 0.87 (77.27) | 0.89 (95.37) |
| Wind offshore | 0.95 (92.36) | 0.83 (194.47) | 0.91 (86.56) | 0.91 (71.40) | 0.96 (85.53) | 0.94 (101.65) |
| Solar energy sold at negative prices | 4.2% | 1.6% | 8.3% | 18.3% | 24.2% | 22.8% |

- **Solar cannibalisation:** from 0.79 in 2021 to 0.51 in 2025 as capacity grew. In 2025
  German solar earned EUR 3.0 billion less than the same energy at baseload.
- **The 2022 gas crisis turned it around for a year:** with gas setting the price, midday
  hours were expensive too and solar's capture rate rose to 0.94, while wind's fell to 0.71
  (the most expensive months were the calm summer ones). That history is the test bed for
  how capture rates move with the price level (backlog PPA-8d).
- **Reconciliation with the official market values** (netztransparenz.de, legally the
  same formula): solar matches within 0.05 ct/kWh in 2021 and 2023-2024 and 0.09 ct/kWh in
  2025 (tolerance ±0.10, fixed in advance). 2022 differs by −0.21: every month matches, but
  the official monthly weights (the TSOs' extrapolated solar output) differ from the measured
  feed-in, which shows when monthly prices range from 12 to 40 ct/kWh. The spot price matches
  in 67 of 68 months; the exception is June 2024, caused by the SDAC partial decoupling on
  26 June 2024.
- **Open investigation:** wind capture prices are 0.16 to 1.10 ct/kWh above the official
  values in every year (largest in 2022). The evidence points to curtailment in the measured
  generation data versus the TSOs' online extrapolation. These references are deliberately
  left outside tolerance until that is tested (backlog PPA-2b).

![Capture rate by month](reports/figures/step02_capture_rate_monthly.png)

Full report: [`reports/step02_capture_prices.md`](reports/step02_capture_prices.md).
How it was built and investigated:
[learning track, Step 2](docs/learning_track/step02_capture_prices.md).

### Step 1 results

| DE-LU day-ahead | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|---|---|---|
| Mean price (EUR/MWh, time-weighted) | 96.85 | 235.45 | 95.18 | 78.51 | 89.32 | 107.72 |
| Hours with negative prices | 139 | 69 | 301 | 457 | 576 | 471 |
| Longest negative streak (hours) | 17 | 8 | 36 | 18 | 20 | 18 |
| Lowest / highest price (EUR/MWh) | -69.00 / 620.00 | -19.04 / 871.00 | -500.00 / 524.27 | -135.45 / 936.28 | -250.32 / 583.40 | -499.99 / 747.10 |

Reconciliation: the 2021, 2022, 2023 and 2025 mean prices match the official values exactly
(2024 differs by −0.95 EUR/MWh, fully explained by the 26 June 2024 decoupling), and the
negative-hour counts match published figures within 2 hours. Data quality: 23 checks pass,
1 warning (one real interval at the -500 EUR/MWh floor), 0 failures; all 2,099 delivery
days complete, checked against the exchange's price limits in force on each day (+3,000
EUR/MWh until 10 May 2022, then +4,000).

The full numbers, the data-quality report and four charts are in
[`reports/step01_market_data.md`](reports/step01_market_data.md).

## Data sources and licence

- Day-ahead prices and generation: **CC BY 4.0, Bundesnetzagentur | SMARD.de, via
  [Energy-Charts](https://energy-charts.info) (Fraunhofer ISE)**.
- Weather: **ERA5 reanalysis** (ECMWF / Copernicus Climate Change Service) via the
  [Open-Meteo](https://open-meteo.com) archive API, CC BY 4.0 (contains modified Copernicus
  Climate Change Service information).
- Official market values (Marktwerte): the German TSOs, published on
  [netztransparenz.de](https://www.netztransparenz.de), stored in
  `data/reference/` for reconciliation.
- Forward curve and market check (Steps 7-8): published EEX German Power Cal-27, Cal-28 and
  Cal-29 base quotes from [tacto.ai](https://www.tacto.ai/en/energy/electricity-price) and
  [power2market](https://www.power2market.com/de/markets/de/termin), with date and URL in
  `config/project.toml` (secondary sources, not EEX settlement files).
- Code: MIT licence (see `LICENSE`). The licence does not cover downloaded data.

## Methodology notes

- Timestamps are stored in UTC at the start of each delivery interval
  ([ADR 0002](docs/decisions/0002-utc-storage-native-resolution.md)).
- Day-ahead prices are hourly until 30 Sep 2025 and quarter-hourly from 1 Oct 2025;
  averages are time-weighted across both.
- "Negative hours" means hours whose average price is below zero; two alternative
  definitions are reported because publishers differ.

## Status

Version 1.3.0: Steps 1-9 are done; the price level is the market's forward curve (v1.1) with
the market's seasonal shape and a solar cannibalisation trend (v1.2), for two Encavis parks
(v1.3). Candidates for a version 2
(capture rate vs price level on 2021-2022 data, a monthly curve, constrained hedges,
out-of-sample validation) are in the [backlog](docs/BACKLOG.md); see also the
[changelog](CHANGELOG.md).
