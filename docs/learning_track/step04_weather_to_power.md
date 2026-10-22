# Step 4: Weather to power (ticket PPA-4)

> **The parks on this page.** Two Encavis parks, modelled from public data: the Borrentin
> solar park (114 MWp, Mecklenburg-Western Pomerania, about 121 GWh a year) and the
> Everswinkel wind park (28.5 MW onshore, four Nordex N149 and one N163, North
> Rhine-Westphalia, about 64 GWh a year). All numbers are from `reports/step04_generation.md`.

> **Time needed:** about 5 hours. Concepts take 90 minutes, code tour and findings
> 60 minutes, hands-on, notebook and exercises 2 hours, to-dos 30 minutes.
> **You will be able to:** explain where long-term weather data comes from, turn
> irradiance and wind into the hourly output of a real solar and wind park, compute
> P50 and P90 volumes, and check a model when no official number exists to tie it out to.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Findings](#4-four-real-findings) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-what-the-data-says) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-step-4) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Thursday. The buyer's bank joins the call:

> *"Your pay-as-produced price looks fine, but we lend against energy, not prices. What
> does this park produce in a normal year, what in a bad one, and how sure are you? We
> want P50 and P90, from your own site, not from a national average. Ticket PPA-4."*

Until now the parks were the national generation profile, scaled (Step 3). That was
good enough to compare contract structures, but it hides two things a lender and a
pricing analyst care about: the **site's own weather** (a single park is not the whole
fleet), and **how much a year can differ from another** (volume risk). Both need a long
weather record at the exact location and a model that turns weather into power.

**Ticket PPA-4: acceptance criteria (all met today)**

- [x] ERA5 weather for two real sites, 1995 to date, cached with provenance (grid point,
      licence, completeness).
- [x] The timestamp convention handled and verified against the sun's position (test and
      a check on every build).
- [x] A pvlib model of the Borrentin solar park (114 MWp) and a windpowerlib model of the
      Everswinkel wind park (28.5 MW), from configuration, calibrated to their published
      annual yields.
- [x] Annual energy per weather year, P50 and P90 (one year and ten years), trend.
- [x] Checks against national generation: hourly correlation, monthly shares, capture rate.
- [x] Report, learning page, notebook section, exercises.

---

## 1. Concepts you need today

### 1.1 Volume risk, the third risk

Step 2 and Step 3 were about **price** and **shape**. The third risk is **volume**: how much
energy the park produces. A pay-as-produced PPA moves price and shape risk to the buyer,
but the producer still sells *whatever the weather delivers*: a dull year means fewer MWh
at the same fixed price. Lenders size debt on a volume they are confident about (P90 or
P99), and a PPA offer with a delivery guarantee must be priced on it.

### 1.2 Where long-term weather data comes from: reanalysis

A park rarely has decades of on-site measurements. The industry standard is a
**reanalysis**: a weather model run backwards in time that continuously assimilates the
observations available (stations, satellites, radiosondes, aircraft). The result is a
physically consistent, gap-free record everywhere on Earth.

- **ERA5** (ECMWF, for the EU's Copernicus Climate Change Service) is the reference
  reanalysis: hourly, from 1940, on a grid of about 0.25° (here about 28 × 16 km).
- We use it through the **Open-Meteo archive API**: free, no key, CC BY 4.0. It snaps the
  request to the nearest grid point and tells you which one it used.
- A grid value is an **average over the cell**. Local effects (a hill, a forest edge, the
  coast) are smoothed out. Section 4.2 shows how much that matters.

> **Real-world note:** yield consultants combine a short on-site measurement campaign with
> 20-30 years of reanalysis: "measure, correlate, predict" (MCP). Encavis calls its
> long-term reference "standard weather" based on 30 years. That is exactly the role our
> 31 ERA5 years play.

### 1.3 Solar: from irradiance to AC power

Irradiance arrives as three components (all in W/m²):

| Component | Meaning |
|---|---|
| **GHI**, global horizontal | everything falling on a flat surface |
| **DNI**, direct normal | the beam from the sun's disc, on a surface facing the sun |
| **DHI**, diffuse horizontal | sky light scattered by clouds and air |

The chain in `weather/pv.py` (pvlib does each step):

1. **Sun position** for each hour, taken at **mid-interval** (an hourly mean of 10:00-11:00
   belongs to the sun at 10:30).
2. **Plane-of-array (POA) irradiance:** the panels are tilted 25° towards the south, so
   GHI/DNI/DHI are transposed onto that plane (Hay-Davies model).
3. **Cell temperature** (Faiman model): hot cells produce less, about **−0.35% per °C**.
4. **DC power** (PVWatts): proportional to POA irradiance, corrected for temperature.
5. **System losses** of 12.4%: soiling, mismatch, wiring, availability, plus site effects
   the model cannot see, calibrated so that the P50 matches Borrentin's published 121 GWh
   (section 4.2).
6. **Inverter** (96% efficiency) with a **DC/AC ratio of 1.2**: 114 MWp of panels on
   95 MW of inverters (tilt, orientation and DC/AC ratio are assumptions: the layout is not
   published). On the sunniest hours the inverter **clips** the output.

The result per year divided by the DC capacity is the **specific yield** (kWh per kWp).
German ground-mounted parks reach roughly 950-1,150 kWh/kWp; Borrentin's published
expectation, 121 GWh from 114 MWp, is 1,061 kWh/kWp.

### 1.4 Wind: from wind speed to MW

- **Wind shear:** wind gets stronger with height. ERA5 gives the speed at 10 m and at 100 m,
  so we can measure the shear each hour with the power law
  `alpha = ln(v100 / v10) / ln(100 / 10)` and extrapolate to the hub:
  `v_hub = v100 · (hub height / 100)^alpha`. Alpha is clipped to [0, 0.6].
- **Power curve:** a turbine produces nothing below the **cut-in** speed (about 3 m/s),
  rises roughly with the **cube** of wind speed, reaches **rated power** and shuts down
  above **cut-out**. windpowerlib has no curve for Everswinkel's Nordex N149 and N163, so
  the Enercon E-126 EP4 (4.2 MW, rated at about 14 m/s, cut-out 25 m/s) stands in: its
  specific power is similar (337 W/m² against 327 for the N149/5.7), and it is scaled to
  28.5 MW at a 164 m hub (the usual N149 height in Germany; not published).
- **The cube law means the mean wind speed is not enough.** Two sites with the same mean
  but a different distribution produce different energy. That is why we model every hour.
- **Losses** of 26.4%: the usual 12% (wake effects of turbines on each other ~7%,
  availability ~3%, electrical ~2%) plus what a reanalysis model cannot see at this site:
  sound-reduced night operation and bat curtailment (common in North Rhine-Westphalia), the
  stand-in curve, and ERA5 winds extrapolated to 164 m. Calibrated so that the P50 matches
  the published 64 GWh (section 4.2).
- Energy per year divided by capacity gives the **full-load hours**: how many hours at
  full power would produce the same energy. The German onshore fleet averages below 2,000;
  modern large-rotor turbines at good sites in the north reach 3,000 and more; Everswinkel,
  inland in the Münsterland, is expected at 2,246.

### 1.5 P50 and P90

From the annual energies of N weather years (mean μ, standard deviation σ):

```
P50          = the median year: exceeded in half of all years
P90 (1 year) = μ − 1.2816 σ        exceeded in 90% of years (normal approximation)
P90 (10 yr)  = μ − 1.2816 σ / √10   for the average over ten years
```

- 1.2816 is the 90% quantile of the standard normal distribution.
- The **10-year** P90 is much closer to the mean: good and bad years average out. A
  10-year PPA or loan cares about the 10-year number.
- It assumes **independent years**. If weather has trends (solar "brightening") or
  persistent periods, the true uncertainty is larger (exercise 4).
- Lenders often size debt on **P90 or P99**; the budget uses **P50**.

### 1.6 Checking a model with no official number

In Step 1 and Step 2 we reconciled against published figures. For a single park there is
at most one: Encavis publishes an expected annual yield (about 121 GWh for Borrentin, 64 GWh
for Everswinkel), nobody publishes its hourly output. So the model takes its **level** from
the published yield (section 4.2) and we check that everything else **behaves like
reality**:

1. **Benchmarks:** specific yield and full-load hours in the right range for the region
   and technology, before calibration as well as after.
2. **Pattern:** hourly correlation with the national fleet of the same technology (Step 1
   data). High for solar (everyone sees the same sun), lower for one wind site.
3. **Seasonality:** the share of annual energy per month should look like the fleet's.
4. **Economics:** the site's capture rate at real prices (Step 2) should be close to the
   national one, with explainable differences.
5. **Timestamps:** irradiance must line up with the sun (section 4.1).

---

## 2. What was built: architecture

```
Open-Meteo archive API (ERA5)                         config/project.toml
  GHI, DNI, DHI, T2m, wind 10/100 m, hourly           [pricing.parks.*] site + model
            │                                          [weather] first year, pause, licence
            ▼                                                     │
data/open_meteo.py   OpenMeteoClient.hourly() ─ parse_hourly_payload() (pure)
            │                                                     │
data/weather_pipeline.py  fetch_weather(): one raw file per site and year (+ manifest)
            │             build_generation(): to_interval_beginning() ─ sun check
            ▼
weather/pv.py (pvlib)          weather/wind.py (windpowerlib)
            └────────────┬───────────────┘
                         ▼
data/processed/weather_<park>.parquet · generation_<park>.parquet (mw = MWh per hour)
                         │
weather/yields.py  annual_energy, p_values      analysis/generation.py  trend, checks
                         ▼
analysis/step04_report.py → reports/step04_generation.md + 2 charts   (`ppa-lab weather`)
```

---

## 3. Code tour

### 3.1 `data/http.py`: one polite client for every source

The retry logic from Step 1 (timeouts, exponential back-off, obeying `Retry-After`) lived
inside the Energy-Charts client. A second source would have copied it, so it moved into
`JsonApiClient`; `EnergyChartsClient` and `OpenMeteoClient` are now ten-line subclasses
with their own base URL and error type. Step 1's client tests passed unchanged: that is
what makes a refactor safe.

### 3.2 `data/open_meteo.py`: parse, convert, verify

- `parse_hourly_payload` is pure: it checks units (forgetting `wind_speed_unit=ms` would
  give km/h, and the parser refuses it), keeps the API's own time labels (the **raw**
  layer stays what the source said) and returns the ERA5 grid point used.
- `to_interval_beginning` converts to the project convention: radiation labelled at the
  **end** of its hour moves back one hour; instantaneous wind and temperature become the
  mean of the two instants around the hour. It refuses an index with gaps.
- `radiation_timing_offset` compares irradiance with the clear-sky sun at −30, +30 and
  +90 minutes after the row label and returns the best fit. For correct data it is +30.

### 3.3 `data/weather_pipeline.py`: cache with provenance

One raw Parquet file per **site and year** with a manifest: request parameters, the ERA5
grid point and its elevation, the licence, and `complete`. ERA5 is published with a delay
of about five days, so the current year is marked incomplete and re-downloaded on the
next run; finished years come from the cache. Changing a park's coordinates triggers a
re-download for that park only (section 4.2 used exactly that).

`build_generation` concatenates the years, converts the timestamps, **runs the sun check
for the solar site and stops the build if it fails**, runs the site model and writes
`weather_<park>.parquet` and `generation_<park>.parquet`.

### 3.4 `weather/pv.py`, `weather/wind.py`, `weather/yields.py`

Each model is one function from a weather frame to an MW series, with all parameters
from the configuration (`tilt_deg`, `dc_ac_ratio`, `turbine_type`, `hub_height_m`,
`losses_pct`, ...). The wind power curve comes from windpowerlib's turbine library,
which ships with the package (no download in CI). `yields.py` turns hourly MW into annual
energy per **complete** local year and computes P50/P90.

### 3.5 Tests: what each one protects

| Test file | Protects against |
|---|---|
| `test_open_meteo.py` (7) | wrong units; radiation not shifted (caught by two tests, one on real data); gaps; wrong request parameters |
| `test_weather_models.py` (9) | sun output at night; exceeding the inverter limit; wrong shear maths; power curve beyond cut-out; no temperature loss |
| `test_yields.py` (2) | partial years counted as weather years; wrong P90 formulas |
| `test_weather_pipeline.py` (4) | re-downloading cached years; never refreshing the current year; a shifted dataset slipping through |
| `test_generation_analysis.py` (3) | plain instead of weighted capture price; UTC months; trend per year instead of per decade |
| `test_step04_report.py` (2), `test_cli.py` (+1) | the report and `ppa-lab weather` end to end, including too-short ranges |

The key tests were checked by planting the bug they protect against and watching them fail.

---

## 4. Four real findings

### 4.1 The weather data is labelled at the end of the hour

- **Symptom:** none yet. This was found *before* it could cause one, by reading the
  source's documentation and then testing the claim with data.
- **Evidence:** compare hourly irradiance with the clear-sky sun computed for different
  times. A full year (2025) of converted data:

  | Sun position taken at | Correlation with irradiance |
  |---|---|
  | 30 min before the row label | 0.872 |
  | **30 min after (mid-interval)** | **0.919** |
  | 90 min after | 0.890 |

- **Why it matters:** without the shift, every solar MWh sits one hour late. Solar
  output would meet the evening price ramp instead of the midday dip, and the capture
  price would come out too high, exactly the error that costs money in a PPA.
- **Guard rails:** a unit test on a real two-day ERA5 sample, and a check inside every
  build that stops `ppa-lab weather` if the data ever arrives shifted
  (`test_build_generation_refuses_weather_with_shifted_timestamps`).

### 4.2 The wind model was 19.5% above the published yield

- **Symptom:** with the textbook 12% losses the Everswinkel model gave **76.5 GWh** a year
  (2,684 full-load hours) against the about 64 GWh Encavis publishes: +19.5%. The solar
  model with 10% losses gave 124.3 GWh against about 121 GWh (+2.7%).
- **Investigation, in the order a yield analyst would go:**

  | Check | Borrentin (solar) | Everswinkel (wind) |
  |---|---|---|
  | ERA5 grid point | 53.75 N, 13.00 E, 39 m: land, 7 km away | 52.00 N, 7.75 E, 70 m: land, 10 km away |
  | Machine data | layout not published (tilt, DC/AC assumed) | no N149/N163 curve in the library: E-126 EP4 stand-in, similar specific power |
  | Height | – | hub not published (164 m assumed); ERA5 gives 100 m, the rest is extrapolated with the measured shear |
  | Site practice | – | sound-reduced night operation and bat curtailment are common in NRW, and no model of the weather sees them |

- **Fix:** keep the weather and the hourly shape from ERA5, take the level from the
  operator: losses 12.4% for solar and 26.4% for wind, so that each P50 matches its
  published yield (model P50 −0.0% and −0.1%).
- **Lesson:** a pricing desk combines a **yield assessment** (the level, from the operator
  or a consultant) with **reanalysis** (variability and hourly shape). A model 20% off
  before calibration is normal for a single wind park with unknown machines and
  operating rules; a model you cannot tie to any published number is the one to distrust.
  And look at the grid point you got: a cell average, its elevation, land or sea.

### 4.3 The solar site earns a bit more than the national fleet

| Capture rate | 2023 | 2024 | 2025 |
|---|---|---|---|
| Borrentin (model) | 0.799 | 0.601 | 0.542 |
| National solar | 0.759 | 0.592 | 0.516 |

Two candidate reasons, both plausible: (1) **one site is not the fleet**: the hourly
correlation is 0.92, and when the north-east is sunny while the south, where most German
solar is, is not, prices are higher; (2) **inverter clipping** removes energy exactly in the sunniest, cheapest
hours. Separating them is a play idea in the notebook (change `dc_ac_ratio`). For pricing
it means: the national capture rate is a good first guess, but a site's own profile can
be worth a few EUR/MWh.

### 4.4 Small ones

- **Rate limits:** a whole year of hourly data counts as many API calls. With 4 s between
  requests the two sites' 1995-2026 records (64 site-years) download in a few minutes.
- **A test that tested formatting:** the first report test looked for `"| 2025 |"` in a
  Markdown table, which depends on column padding. It now checks that both years appear in
  the right section: test behaviour, not layout.
- **Constant series:** the synthetic national wind in the tests is constant, so its
  correlation is undefined; the function now returns NaN quietly instead of a warning.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # the offline tests (290 in v1.11)
make weather               # first run about 5 minutes (downloads), then seconds
open reports/step04_generation.md
make notebook              # Step 4 section: 4.1 to 4.6, then your solutions
```

In the notebook, run 4.2 (the timestamp evidence yourself) and play with 4.3 (any week at
both sites) and 4.6 (site vs national).

---

## 6. Results: what the data says

### 6.1 Volumes

| | Borrentin solar (114 MWp) | Everswinkel wind (28.5 MW) |
|---|---|---|
| ERA5 grid point | 53.75 N, 13.00 E, 39 m | 52.00 N, 7.75 E, 70 m |
| P50 | 120.9 GWh = **1,061 kWh/kWp** | 64.0 GWh = **2,245 full-load hours** |
| Published expectation | about 121 GWh | about 64 GWh |
| Variability (CoV) | 4.6% | 7.2% |
| P90 one year | 113.4 GWh (−5.9%) | 58.1 GWh (−9.2%) |
| P90 ten years | 118.3 GWh (−1.9%) | 62.1 GWh (−2.9%) |
| Worst / best year | 1998 −8.9% / 2018 +10.2% | 2010 −13.5% / 1998 +13.6% |
| Trend | +2.1% per decade | −1.7% per decade |

![Annual energy per weather year](../../reports/figures/step04_annual_yield.png)

![Monthly shares, site vs national](../../reports/figures/step04_monthly_shares.png)

### 6.2 Five stories

1. **One year in ten is 6-9% short.** The one-year P90 is 5.9% below the mean for
   Borrentin and 9.2% for Everswinkel. For a 10-year average it is only 1.9% and 2.9%: the
   reason long contracts can carry volume risk.
2. **Solar is getting sunnier, this wind site calmer.** Borrentin +2.1% per decade over
   1995-2025 matches the European "brightening" (cleaner air since the 1980s and 1990s);
   Everswinkel −1.7% per decade. A P50 from the full 31-year mean may misstate today's
   yields either way. Which period defines "standard weather" is a real decision, not a
   detail.
3. **The extremes are −9 to +10% for solar and ±14% for wind.** Encavis reports that annual
   wind yields can deviate by up to ±25%: real parks add outages, curtailment and shorter
   periods to the weather signal, which our potential-output model does not include. Treat
   our P90 as a weather-only floor.
4. **Wind is a winter product, solar a summer one.** In 2021-2025 Everswinkel delivered
   12.1% of its year in January and 5.0% in August; Borrentin 14.0% in May and in June and
   1.7% in December. The two parks together are smoother than either alone (exercise 3
   shows what that is worth).
5. **One site is not the fleet, and wind is more local.** Hourly correlation with the
   national fleet is 0.91-0.93 for Borrentin and 0.86-0.88 for Everswinkel. Wind is the
   riskier volume on every count here: year to year (7.2% against 4.6%), locally, and in
   the modelling choices (power curve, hub height, losses).

### 6.3 What this means for pricing

- The **fair price** uses expected (P50) volumes; the **risk premium** and debt sizing use
  the spread (P90). Both now come from the site, not the country.
- Step 6 will pair these 31 weather years with simulated prices. Because windy and sunny
  hours are cheap hours, the volume and the price of each hour must stay together.

---

## 7. Exercises

**Warm-up (in `exercises/step04_generation.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **Specific yield and full-load hours** for both parks in 2024.
2. **P50 and P90** by hand from the 31 weather years.
3. **A solar + wind portfolio:** the capture rate of both parks sold together.
4. **Written:** one-year vs ten-year P90, and what makes the ten-year figure optimistic.

**Core**

5. **Clipping (test first).** Write a test that a DC/AC ratio of 1.0 produces more energy
   than 1.4 at the same DC capacity, then measure the energy and capture-rate difference
   for 2025. Does clipping explain the solar site's higher capture rate (section 4.3)?
6. **Hub height.** Re-run the wind model with 144 m and 184 m hubs for 2024 (Everswinkel
   is modelled at 164 m). How much energy
   does each 20 m add, and why does the answer depend on the shear?
7. **Monthly P90.** Compute P90 for each calendar month of the solar park. Why do the twelve
   monthly P90s not add up to the annual P90?

**Stretch**

8. **Air density.** Add `surface_pressure` to the weather request and use windpowerlib's
   density correction. How large is the effect in winter vs summer?
9. **P99** with the normal approximation and empirically. Which do you trust with 31 years?

<details>
<summary>Hints and solution sketches</summary>

1. `generation["mw"].tz_convert(TZ).loc["2024"].sum() / capacity`: about 1,058 kWh/kWp for
   Borrentin and 2,267 hours for Everswinkel in 2024.
2. `annual.median()` and `annual.mean() - 1.2816 * annual.std(ddof=1)`.
3. Add the two `mw` Series, align with prices on common hours, then capture / mean price.
4. Averages of independent years have a standard deviation σ/√n. Lenders of a 10-year
   loan look at the 10-year number but add margins because years are not independent
   (trends, persistent regimes) and because σ itself is estimated from only 31 years.
5. Call `solar_power_mw` twice with different `dc_ac_ratio`; compare sums and capture
   rates with Step 2's formula.
6. Higher hubs gain more where shear is strong (night, stable air).
7. Monthly deviations partly cancel within a year; adding monthly P90s adds twelve
   "bad months" that rarely happen together.
8. `ModelChain(..., density_model="barometric")` needs pressure and temperature at hub height.
9. `mean - 2.326 * std` vs the 1st percentile of 31 values (which is just the worst year).

</details>

---

## 8. Self-check quiz

1. What is a reanalysis, and why use it instead of on-site measurements for long-term yields?
2. What are GHI, DNI and DHI?
3. Why is the sun position computed at mid-interval?
4. What did Open-Meteo's time label mean for radiation, and how did we check our conversion?
5. What is the DC/AC ratio, and what is clipping?
6. Why is the mean wind speed not enough to compute energy?
7. How is wind speed extrapolated from 100 m to hub height here?
8. Define P50, one-year P90 and ten-year P90. Why is the ten-year P90 closer to the mean?
9. Why are the models' losses 12.4% (solar) and 26.4% (wind) instead of the textbook 10-12%?
10. How do you check a model when no official figure exists?

<details>
<summary>Answers</summary>

1. A weather model run over past decades that assimilates all observations, giving a
   consistent, gap-free hourly record everywhere; sites rarely have decades of measurements.
2. Global horizontal (everything on a flat surface), direct normal (the sun's beam on a
   surface facing it), diffuse horizontal (scattered sky light).
3. An hourly mean describes the whole hour; the sun at its middle represents it best.
4. Mean of the preceding hour (labelled at the end). After shifting, irradiance must match
   the clear-sky sun best at +30 minutes; a test and a build check enforce it.
5. Panel (DC) capacity divided by inverter (AC) capacity; above the inverter limit output
   is cut off, which loses some energy in the sunniest hours.
6. Power rises roughly with the cube of speed and is capped and cut out by the power
   curve, so the distribution of speeds matters, not just its mean.
7. Power law with the shear exponent measured each hour from the 10 m and 100 m speeds:
   v_hub = v100 · (h/100)^alpha, alpha clipped to [0, 0.6].
8. Median year; mean − 1.2816σ; mean − 1.2816σ/√10. Averaging ten independent years
   shrinks the standard deviation by √10.
9. They are calibrated so that each P50 matches the yield Encavis publishes (121 and 64
   GWh): with textbook losses the models gave +2.7% and +19.5%. For wind the gap covers what
   the model cannot see: sound-reduced nights and bat curtailment, the stand-in power curve,
   the extrapolation from 100 m to 164 m. The level comes from the operator, the variability
   and hourly shape from ERA5.
10. Tie the level to whatever is published (here the expected annual yield), then check
    benchmarks, hourly correlation and seasonal shape against the national fleet, the
    capture rate at real prices, and physical checks such as timestamps against the sun.

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* to price a PPA and size its debt, a bank needs the park's own P50 and P90,
> not a national profile. *Task:* model hourly output of two Encavis parks, the Borrentin
> solar park (114 MWp) and the Everswinkel wind park (28.5 MW), over many weather years.
> *Action:* I pulled 31 years of ERA5 reanalysis for each site, converted its end-of-hour
> radiation labels and verified them against the sun's position, modelled the parks with
> pvlib and windpowerlib, calibrated their losses to the published yields and checked them
> against the national fleet. *Result:* P50 120.9 GWh (1,061 kWh/kWp) and 64.0 GWh (2,245
> full-load hours), one-year P90s 5.9% and 9.2% below the mean, and two traps caught on the
> way: shifted timestamps, and a raw wind model 19.5% above the published yield.

**Likely questions and strong answers:**

- *"How do you use weather data in risk?"* Long-term reanalysis (ERA5) at the site, a
  physical model to power, annual energies per weather year for P50/P90, and the same
  weather years paired with prices for joint risk, because volume and price are correlated.
- *"Your model and the real park disagree. What do you check first?"* Timestamps and time
  zones, the grid point and its surroundings, the power curve and hub height, losses and
  curtailment, then the long-term period used.
- *"What drives the difference between one-year and ten-year P90?"* Averaging: σ/√n under
  independence. In practice lenders add margins for trends, persistence and estimation
  error.
- *"Is wind or solar riskier on volume?"* Wind, here on every count: year to year (7.2%
  against 4.6%), more local (hourly correlation with the fleet 0.87 against 0.92) and more
  sensitive to modelling choices such as the power curve, hub height and site losses.

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| ERA5 via Open-Meteo | ERA5, MERRA-2 and commercial reanalyses; on-site met masts and lidar |
| pvlib / windpowerlib models | Energy yield assessments by consultants; SCADA data of operating parks |
| P50/P90 over 31 weather years | Budget (P50), debt sizing (P90/P99), "standard weather" over 30 years |
| Sun check on timestamps | Data-quality rules on SCADA and meter data |
| Losses calibrated to the published yield | Yield assessment for the level, reanalysis for variability and shape; site exposure checks |
| Site vs national capture rate | Asset-level capture-rate monitoring and PPA settlement checks |

Encavis reports that annual wind yields can deviate strongly from the mean and uses
long-term data, external yield reports and sensitivity analyses: today's work is the
small, transparent version of that toolbox.

---

## 11. Your to-dos for Step 4

- [ ] Read sections 1 and 4; redo the shear calculation in 1.4 for v10 = 5, v100 = 7.5 m/s
      and Everswinkel's 164 m hub (you should get about 8.18 m/s).
- [ ] Run section 5; in the notebook, reproduce the timestamp table of section 4.1 (cell 4.2).
- [ ] Exercises 1-4 in `exercises/step04_generation.py`; check them in "My solutions: Step 4".
- [ ] **Commit Step 4** (commands below).
- [ ] **German vocabulary of this step:** die Globalstrahlung, die Direktstrahlung, die
      Diffusstrahlung, die Modultemperatur, der Wechselrichter, die Nabenhöhe, die
      Leistungskennlinie, die Volllaststunden, der spezifische Ertrag, das Windjahr,
      der Nachlaufverlust (wake loss), die Verfügbarkeit, die Reanalyse.
- [ ] Stand-up update: *"Yesterday: site models for Borrentin and Everswinkel from 31 years
      of ERA5, calibrated to their published yields; P50 120.9 and 64.0 GWh, P90 one year
      −5.9% and −9.2%.
      Today: stochastic price model (PPA-5). Blockers: none."*

Commit (check `git status` first: no `.env`, no ` M .env.example`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status --short
git add src tests exercises config reports docs notebooks METHODOLOGY.md README.md CHANGELOG.md Makefile pyproject.toml
git status --short
git commit -m "feat(weather): ERA5 site models for solar and wind, P50/P90 volumes (PPA-4)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Reanalysis | Weather model run over the past, assimilating observations (ERA5) |
| GHI / DNI / DHI | Global horizontal / direct normal / diffuse horizontal irradiance |
| POA irradiance | Irradiance on the plane of the tilted panels |
| DC/AC ratio, clipping | Panel vs inverter capacity; output cut at the inverter limit |
| Specific yield | Annual energy per kWp of panels (kWh/kWp) |
| Wind shear, alpha | Increase of wind speed with height; power-law exponent |
| Power curve | Turbine output as a function of hub-height wind speed |
| Full-load hours | Annual energy divided by capacity |
| Wake loss | Energy lost because turbines shadow each other |
| P50 / P90 | Energy exceeded in 50% / 90% of years |
| Weather year | One historical year of weather run through the park model |
| Grid point / cell | Location and area a reanalysis value represents |

## 13. Sources

- Hersbach, H. et al. (2020): The ERA5 global reanalysis. *Quarterly Journal of the Royal
  Meteorological Society* 146, 1999-2049.
- Open-Meteo Historical Weather API documentation (variables, units, time conventions).
- pvlib python documentation; Hay, J. and Davies, J. (1980), transposition model; Faiman, D.
  (2008), *Progress in Photovoltaics* 16(4), module temperature model; Dobos, A. (2014),
  PVWatts Version 5 Manual, NREL/TP-6A20-62641.
- windpowerlib documentation (oemof project) and its turbine library (power curves).
- Encavis preparation guide: weather and volume risk, "standard weather" over 30 years,
  interview question "How do you use weather data in risk?".
