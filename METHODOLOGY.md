# Methodology

How `ppa-lab` values renewable power purchase agreements (PPAs): the definitions,
formulas and conventions behind the code, and their limitations.

**Version 1.5** (ticket PPA-8d): cash flows and fair prices of the standard structures,
applied to history (PPA-3), site volumes from weather with P50/P90 (PPA-4, section 7), a
stochastic hourly price model calibrated to a forward price (PPA-5, section 8), joint
weather and price scenarios (PPA-6, section 9), prices, risk premia and cash flow at risk
on those scenarios (PPA-7, section 10), and hedging with power futures with a market check of
the forward (PPA-8, section 11). Since version 1.1 the price level is the market's: the Cal-27
base quote for the delivery year and the published Cal-28 and Cal-29 quotes for later years.
Since version 1.2 each quarter of the delivery year follows the market's seasonal shape
(section 9), and the solar park's capture rate falls 1 percentage point a year (section 10).
Since version 1.3 the parks are two Encavis parks modelled from public data: Borrentin solar
(114 MWp) and Everswinkel wind (28.5 MW), with losses calibrated to their published yields
(section 7). Since version 1.4 the market history starts in 2021. Since version 1.5 each later
year's capture rate moves with that year's forward along the price model's own response to the
price level, which 2023-2026 history confirms for solar (section 10).

---

## 1. Scope and conventions

- **Perspective:** the producer (an IPP such as Encavis). Positive cash flows are money
  to the producer. The buyer's view is the mirror image.
- **Time:** intervals $t$ of length $\Delta t$ (15 minutes; hourly prices before
  1 Oct 2025 apply to all four quarter-hours of their hour). Periods (months, years)
  are local (`Europe/Berlin`).
- **Market:** German-Luxembourg day-ahead auction (SDAC), one bidding zone, so no
  basis between the plant's location and the settlement price.
- **Code:** `src/ppa_lab/pricing/contracts.py` (cash flows, fair prices),
  `src/ppa_lab/pricing/backtest.py` (historical back-test),
  `src/ppa_lab/analysis/capture.py` (capture prices), `src/ppa_lab/weather/` (volumes),
  `src/ppa_lab/prices/` (price model).

### Notation

| Symbol | Meaning | Unit |
|---|---|---|
| $P_t$ | Day-ahead price in interval $t$ | EUR/MWh |
| $q_t$ | Energy produced in interval $t$ | MWh |
| $D_t$ | Discount factor to the valuation date | – |
| $K$ | Fixed (strike) price of a pay-as-produced PPA or CfD | EUR/MWh |
| $K_B$, $B$ | Baseload PPA price and band (energy per interval) | EUR/MWh, MWh |
| $F$, $C$ | Floor and cap prices | EUR/MWh |
| $\bar P$ | Time-weighted (baseload) average price of a period | EUR/MWh |

---

## 2. Capture price and capture rate

The energy-weighted price a profile earns, and its ratio to the baseload price:

$$
\bar P^{cap} = \frac{\sum_t q_t P_t}{\sum_t q_t}, \qquad
c = \frac{\bar P^{cap}}{\bar P}, \qquad
\bar P = \frac{\sum_t \Delta t\, P_t}{\sum_t \Delta t}.
$$

This is the formula of the official German market values (EEG 2023, Anlage 1,
Nr. 3.3 and 4.3, per quarter-hour), which the project reconciles against (Step 2).
The **profile cost** of a period is $(\bar P - \bar P^{cap}) \sum_t q_t$.

Why solar earns less than baseload, in one line: over a period of $n$ intervals,

$$
\sum_t q_t P_t = n\,\bar q\,\bar P + \sum_t (q_t - \bar q)(P_t - \bar P),
$$

so $\bar P^{cap} = \bar P + \text{Cov}(q, P)/\bar q$. Solar output and prices move in
opposite directions (cannibalisation), the covariance is negative and $c < 1$. The same
identity inside each hour explains why hourly data overstates solar capture prices
since 15-minute prices started.

---

## 3. Cash flows of each structure (producer view)

The producer sells its physical output on the spot market unless the contract says
otherwise. Each structure is then "spot revenue + financial settlement".

| Structure | Cash flow in interval $t$ | Risk left with the producer |
|---|---|---|
| Merchant | $q_t P_t$ | price level, shape, volume |
| Pay-as-produced (PaP) PPA | $K q_t$ | volume |
| PaP PPA, no payment at negative prices | $K q_t \mathbb 1[P_t \ge 0]$ | volume, frequency of negative prices |
| Virtual PPA (two-sided CfD on produced volume) | $q_t P_t + (K - P_t) q_t = K q_t$ | volume (and basis, where it exists) |
| Floor (bought put strip) | $q_t \max(P_t, F)$ | upside price, shape, volume; downside capped at $F$ |
| Cap (sold call strip) | $q_t \min(P_t, C)$ | downside price; upside given away above $C$ |
| Collar | $q_t\, \text{clip}(P_t, F, C)$ | price inside $[F, C]$ |
| Baseload PPA | $K_B B + (q_t - B) P_t$ | **shape** and volume |

Notes:

- The **negative-price clause** assumes the producer curtails when $P_t < 0$; a price of
  exactly zero is still paid (EEG §51 refers to prices below zero).
- **Floor at 0 EUR/MWh = curtailment.** A plant that can switch off when the price is
  negative owns a free put struck at 0: $q_t \max(P_t, 0)$.
- A collar with $F = C = K$ is a CfD at $K$.
- **A baseload PPA is merchant revenue plus a baseload swap:**
  $K_B B + (q_t - B) P_t = q_t P_t + B (K_B - P_t)$. It fixes the price *level* of the
  band, but the residual $q_t - B$ is settled at spot: shortfalls are bought exactly
  when prices are high (winter evenings for solar). That residual is the shape risk.
- Option premiums are not in these cash flows. They are the fair value of the floor or
  cap (section 4) and are paid separately or built into the strike.

---

## 4. Fair (break-even) prices

The fair price makes the contract worth the same as selling at spot, in expectation
over price and volume scenarios $\omega$ (one scenario = history in the back-test):

$$
K^\star = \frac{E\left[\sum_t D_t q_t P_t\right]}{E\left[\sum_t D_t q_t\right]}, \qquad
K_B^\star = \frac{E\left[\sum_t D_t P_t\right]}{\sum_t D_t}.
$$

- $K^\star$ is a **ratio of expectations**, not the average of each scenario's capture
  price: high-volume scenarios weigh more (`test_fair_price_is_a_ratio_of_expectations...`).
- With one history and $D_t = 1$, $K^\star$ is the capture price and $K_B^\star$ the
  base price: at those strikes every structure earns the merchant revenue in total.
- Fair option values per MWh of expected production:
  floor $= E[\sum_t D_t q_t (F - P_t)^+]/E[\sum_t D_t q_t]$,
  cap $= E[\sum_t D_t q_t (P_t - C)^+]/E[\sum_t D_t q_t]$. A zero-cost collar chooses
  $F$ and $C$ so that the two are equal.
- Discounting: $D_t = (1 + r)^{-\tau_t}$, $\tau_t$ in years of 365.25 days from the
  valuation date, annual compounding.

### From the baseload forward to a pay-as-produced price

In practice the buyer's reference is the baseload forward price $F^{base}$. Then

$$
K^{PaP} \approx F^{base} \cdot E[c] \;-\; \text{risk premia} \;-\; \text{costs},
$$

with the risk premium for profile and volume uncertainty, the expected cost of negative
prices and curtailment, balancing and route-to-market costs, and credit and liquidity.
Version 0 quantified only the first term on history; PPA-7 computes all of them on the
joint scenarios (section 10).

---

## 5. Risk measures (used from PPA-7)

For simulated contract cash flows $\Pi$ (per scenario):

$$
\text{premium} = \frac{E[\Pi] - q_{5\%}(\Pi)}{E\left[\sum_t q_t\right]}, \qquad
\text{CFaR}_{95} = E[CF] - q_{5\%}(CF).
$$

How they are applied to the scenarios (whose value $\Pi$, whose cash flow $CF$, which hedge)
is section 10.

---

## 6. Historical back-test (version 0)

Implemented in `pricing/backtest.py`; report `reports/step03_ppa_structures.md`.

- **Parks:** since v1.3 Borrentin solar (114 MWp, 1,061 full-load hours) and Everswinkel
  wind (28.5 MW, 2,246 h), from their published yields (v1.0: 50 MW / 1,000 h and 30 MW /
  2,000 h), using the national profile of their technology, scaled per year to capacity ×
  full-load hours. Since v1.3 the back-test is repeated with each park's own Step 4 profile
  (hourly site output spread evenly over the quarter-hours, `site_energy`).
- **Strike rule:** a contract for delivery year $Y$ is signed at the end of $Y-1$ at
  $Y-1$'s fair prices ($K$ = capture price, $K_B$ = base price, $B$ = expected energy
  delivered flat). Without forward data this is a naive forward proxy.
- **Plan and surprise:** the plan is each structure applied, with the same terms, to
  year $Y-1$'s prices and profile: what the producer expected at signing. Surprise =
  realised − plan per MWh is the risk each structure left with the producer.
- **Not a risk measure:** the spread of monthly revenue within a year. It is mostly
  seasonality, which is known in advance. (A pay-as-produced PPA has *more* monthly
  spread than merchant revenue, because the high summer volume is no longer offset by
  low summer prices, yet it removes all price risk.)

---

## 7. Volume: from weather to energy (PPA-4)

**Weather.** ERA5 reanalysis (ECMWF / Copernicus) through the Open-Meteo archive API: hourly
global, direct and diffuse irradiance, 2 m temperature and wind at 10 m and 100 m at the
nearest ~0.25° grid point, 1995 onwards. Open-Meteo labels radiation at the end of its hour
(mean of the preceding hour) and gives the other variables as instants. Converted to the
project's interval-beginning convention:

$$
G_t = G^{API}_{t+1h}, \qquad x_t = \tfrac12\,(x^{API}_t + x^{API}_{t+1h}).
$$

Every build checks that irradiance then matches the clear-sky sun at mid-interval ($t$ + 30 min).

**Solar (pvlib).** Sun position at mid-interval; plane-of-array irradiance (Hay-Davies);
cell temperature (Faiman); PVWatts DC with $\gamma = -0.35\%/K$; system losses
$(1 - L)$; PVWatts inverter (96%) clipped at the AC capacity $P_{DC}/r$ (DC/AC ratio $r$).

**Wind (windpowerlib).** Hourly shear exponent from the two heights, clipped to $[0, 0.6]$,
and the power law to hub height $h$:

$$
\alpha_t = \frac{\ln(v_{100,t}/v_{10,t})}{\ln 10}, \qquad
v_{hub,t} = v_{100,t}\left(\frac{h}{100}\right)^{\alpha_t},
$$

then the turbine power curve (no air-density correction) scaled to the park capacity, times
$(1 - L)$ for wake, availability and electrical losses.

**Volume statistics.** For annual energies $E_y$ over $N$ weather years (mean $\mu$, sample
standard deviation $\sigma$):

$$
P50 = \operatorname{median}(E_y), \qquad
P90_{1y} = \mu - 1.2816\,\sigma, \qquad
P90_{10y} = \mu - 1.2816\,\frac{\sigma}{\sqrt{10}},
$$

the last assuming independent years. Site models are checked against national generation of
the same technology (hourly correlation, monthly shares, capture rate). **Calibration to the
published yield (v1.3):** where the operator publishes an expected annual yield $E^{pub}$, the
loss factor is set so that the P50 matches it, $1 - L = (1 - L_0)\,E^{pub}/P50_0$, with $L_0$
the technical losses and $P50_0$ the uncalibrated model's P50. The level then comes from the
operator's yield assessment (measured wind, exact turbines, curtailment plans) and the
variability and hourly shape from ERA5, as a pricing desk would combine them. A uniform factor
leaves capture rates and relative P90s unchanged; curtailment that hits specific hours (noise
at night, bats on summer evenings) is not modelled.

---

## 8. Prices: the stochastic model (PPA-5)

Code: `src/ppa_lab/prices/` (`calendar.py`, `model.py`, `validation.py`); report
`reports/step05_price_model.md`; parameters `data/processed/price_model.json`.

**Transform.** Hourly day-ahead prices (quarter-hours averaged) in arcsinh space,

$$
y_t = \operatorname{arcsinh}(P_t / s), \qquad P_t = s \sinh(y_t),
$$

with scale $s$ = 120 EUR/MWh, chosen by the validation below over $s$ = 30 to 300.

**Decomposition.** On the calibration window (2024-01-01 to 2026-09-30, local days):

$$
y_t = L_{m(t)} + S_{c(t),k(t),h(t)} + D_{d(t)} + u_t,
$$

with $m$ the calendar month, $c$ the season, $k$ the day type (working day, Saturday, Sunday
or one of the nine nationwide holidays), $h$ the local hour and $d$ the local day. $L$ and $S$
are group means, estimated by back-fitting (three passes).

**Daily factor.** $D_d$ is the daily mean of $y - L - S$ and follows an AR(1) across days:

$$
D_d = \phi\, D_{d-1} + \sigma_{c(d)}\, z_d, \qquad t_{1/2} = \frac{\ln 2}{-\ln \phi},
$$

$\phi$ by least squares on pairs of consecutive days only, $\sigma_c$ by season from the
residuals, $z_d = \varepsilon_d / \sigma_{c(d)}$ the standardised shocks. Monthly demeaning
biases $\hat\phi$ down by about $(1 + 3\phi)/30$ (Kendall); the estimate is used uncorrected
because the correction did not improve validation.

**Intraday patterns.** $u_t = y_t - L - S - D_{d(t)}$ for every complete 24-hour day, stored
with the day's season and $z_d$ (the resampling pool).

**Simulation.** Per path and simulated day $d$, draw a pool day $j$ of the same season, then

$$
D_d = \phi\, D_{d-1} + \sigma_{c(d)}\, z_j, \qquad D_0 = \frac{\sigma_{c(0)}\, z_{j_0}}{\sqrt{1 - \phi^2}},
\qquad y_t = \mu_t + D_{d(t)} + u_{j, h(t)},
$$

so each day keeps the 24-hour pattern of one real day together with its shock, and the path
starts in the stationary state. For a future year $\mu_t = \lambda + \bar L_{m(t)} + S_t$,
with $\bar L_m$ the average monthly shape and $\lambda$ the annual level. Level uncertainty:
$\lambda \to \lambda + \sigma_\lambda \eta_n$ with one $\eta_n \sim N(0, 1)$ per path
($\sigma_\lambda$ = 0.12).

**Calibration to a forward.** $\lambda$ solves, by bisection,

$$
\frac{1}{N T} \sum_{n=1}^{N} \sum_{t=1}^{T} s \sinh\!\left(\lambda + \bar L_{m(t)} + S_t + x_{n,t}\right) = F,
$$

with the same residual draws $x_{n,t}$ as the simulation (common random numbers), so the
simulated average equals the forward $F$ exactly before level uncertainty. Because $\sinh$
is convex, setting the level from $\operatorname{arcsinh}(F/s)$ would overshoot $F$ (Jensen).

**Validation.** In-sample, 200 paths over the calibration window with the fitted monthly
levels. For each statistic (mean, standard deviation, 1/5/50/95/99% quantiles, share of
negative hours, autocorrelation at 1, 24 and 168 hours) history should lie inside the 5-95%
range across paths. Version 2 meets 7 of 11; the misses (1% quantile, negative share,
autocorrelation at 1 and 24 hours) are explained in the report and in learning track Step 5,
section 4.4. Version 1, a single hourly AR(1), failed on day-to-day memory and was replaced.

---

## 9. Joint weather and price scenarios (PPA-6)

Code: `src/ppa_lab/scenarios/` (`weather.py`, `link.py`, `generator.py`); report
`reports/step06_joint_scenarios.md`; per-scenario results `data/processed/scenarios_<year>.parquet`.

**Why.** A park's revenue is $\sum_t q_t P_t$ and $E[qP] = E[q]\,E[P] + \operatorname{Cov}(q, P)$.
For renewables the covariance is negative; prices simulated independently of the weather set it
to zero and overstate the capture price.

**Weather features.** Per local day $d$: $w_d = (\text{CF}^{solar}_d, \text{CF}^{wind}_d, T_d)$,
the capacity factors of the two parks (mean MW / capacity, Step 4 site models) and the mean 2 m
temperature at the solar site. Climatology $\bar w_m$: the mean per calendar month over the
weather years (1995-2025).

**Link.** On the Step 5 calibration window, with $D_d$ the daily mean of $y - L - S$:

$$
D_d = c_{s(d)} + \beta_{s(d)}^\top a_d + r_d, \qquad
r_d = \phi_r\, r_{d-1} + \sigma_{r, s(d)}\, \xi_d,
$$

with one least-squares regression per season $s$. The anomaly $a_d$ is $w_d$ minus the mean of
its calendar month in the calibration window (the fitted monthly levels already contain each
month's weather); for a future year it is $w_d - \bar w_{m(d)}$, so that an unusually windy month
lowers prices. $\phi_r$ uses consecutive days only.

**Analog days.** For a simulated day with weather $w$, candidates are the complete historical
days $j$ within $\pm 30$ days of the same date (any year of the window), at distance
$\sum_f \left((w_f - w_{j,f}) / \text{sd}_f\right)^2$ with $\text{sd}_f$ over the pool. Each path
draws one of the $k = 10$ nearest and takes its 24-hour pattern $u_j$ and its shock $\xi_j$:

$$
y_t = \mu_t + E_d + r_d + u_{j, h(t)}, \qquad E_d = c_{s(d)} + \beta_{s(d)}^\top a_d,
$$

with $r$ started in its stationary state. In-sample validation excludes analogs within 7 days of
the simulated day.

**Scenarios.** Scenario $(Y, n)$: the parks' output in weather year $Y$ placed date by date and
local hour by local hour on the delivery calendar (29 February → 28 February), and price path $n$
simulated for that weather. All scenarios have equal weight; one level $\lambda_k$ per local
quarter $k$ makes the average price over all scenarios and the quarter's hours equal the quarter
forward $F_k = F \cdot Q_k / \bar Q$ (section 8's bisection, per quarter), where $Q_k$ are
published quarter quotes of one trading day (`[price_model.quarter_quotes]`), $\bar Q$ their
hour-weighted mean and $F$ the Cal forward: the market's seasonal shape at today's level, and
the year still averages $F$. Without quarter quotes one annual level is used. Within a quarter
the monthly and hourly shape comes from history. Then the level uncertainty adds one shift per
scenario. Fair pay-as-produced price over $S$ scenarios:

$$
K^\star = \frac{\sum_s \sum_t q_{s,t} P_{s,t}}{\sum_s \sum_t q_{s,t}}, \qquad
\text{SE}(K^\star) \approx \frac{\operatorname{sd}_s\!\left(R_s - K^\star Q_s\right)}{\sqrt{S}\;\bar Q},
$$

with $R_s$ and $Q_s$ the revenue and energy of scenario $s$.

**Checks.** In-sample with the real weather: the validation statistics of section 8, capture
rates per historical year inside the simulated range, the within-month correlation between
wind and the daily price (history −0.58, Step 6 −0.60, Step 5 0.00). Sensitivity: the period of
the analog pool (solar fair price 48.7 / 44.9 / 41.1 EUR/MWh for pools from 2024, 2025 and the
last 12 months).

---

## 10. Pricing and risk on the scenarios (PPA-7)

Code: `src/ppa_lab/pricing/risk.py`; report `reports/step07_ppa_pricing.md`; results
`data/processed/ppa_pricing.json`. Arrays $P_{s,t}$ and $q_{s,t}$ over $S$ equally likely
scenarios (section 9, with analog days from `[ppa] analog_pool_start`) and the $T$ hours of the
first delivery year.

**Structures (producer view).** The contract functions of section 3, unchanged, on every
scenario; annual revenue $R_s$ per structure, each struck at its fair price (section 4):
merchant; pay-as-produced at $K^\star$; pay-as-produced with the negative-price clause at the
same $K^\star$ (the clause costs the producer its output at $P < 0$); merchant plus a floor $F$
net of its fair premium $E[\sum_t q_t (F - P_t)^+]$; baseload at $K_B^\star = \bar P$ with band
$B = E[\sum_t q_t]/T$. Risk: $\text{CFaR}_{95} = E[R] - q_{5\%}(R)$.

**Buyer's premium.** The buyer of a pay-as-produced PPA at strike $K$ is worth, per scenario,

$$
V_s = \sum_t q_{s,t}\,(P_{s,t} - K) \;+\; B \sum_t (\bar P - P_{s,t}),
$$

the second term being a baseload band $B$ sold at the scenarios' average price $\bar P$ (the
model's forward), which removes the price level. At $K = K^\star$, $E[V] = 0$ and

$$
\pi_{joint} = \frac{E[V] - q_{5\%}(V)}{E\left[\sum_t q_t\right]}, \qquad
\pi_{profile} = \pi_{joint}\big|_{q_{s,t} \to \bar q_t}, \qquad
\pi_{volume} = \pi_{joint} - \pi_{profile},
$$

with $\bar q_t$ the expected hourly volume (so $\pi_{profile}$ only sees the price shape) and
$\pi_{volume}$ what varying volumes and their link to prices add. The premium without the hedge
is reported for comparison.

**Price stack.** $K^{PaP} = \bar P \cdot c - \pi_{joint} - \text{balancing} - \text{credit}$, with
$c = K^\star/\bar P$ the expected capture rate and the costs from `[ppa.parks.*]` (stated
assumptions).

**Tenor.** For years $i = 0, \dots, N-1$: $F_0$ the first year's forward, $F_i$ from
`[ppa.forward_curve]` where it gives the year, and a year after the last quoted one keeps that
quote (long-dated years trade too little for a quote);
$c_i = c + \delta\, i + \gamma(F_i) - \gamma(F_0)$ with the capture-rate trend $\delta$ from
`[ppa.parks.*]` (base case: solar $-1$ percentage point a year, wind 0; history fell faster,
but storage and curtailment at negative prices slow it) and $\gamma(F)$ the capture rate at
price level $F$ (below), $K_i = F_i c_i$, $E_i = E[\sum_t q_t]\,(1 - g)^i$,
$D_i = (1 + r)^{-(i + 1/2)}$, and

$$
K_N = \frac{\sum_i D_i E_i K_i}{\sum_i D_i E_i},
$$

with capture-rate drift $\delta$, degradation $g$ and discount rate $r$. The first year's premium
and costs per MWh are applied to every year. The forward sensitivities ($\pm 10\%$) shift the
whole curve, and the capture rate with it: $c \to c + \gamma(0.9 F_0) - \gamma(F_0)$.

**The capture rate and the price level (PPA-8d).** The price model shifts all hours together
in arcsinh units (section 8), so a higher level lifts the hours near zero and solar's capture
rate rises with it; the usual shape-factor view scales all hours and keeps $c$ fixed. The
model's response $\gamma(F)$ is measured, not assumed: the first year's scenarios are rebuilt
at twelve forwards (the tenor's quotes, the analog pool's average and eight levels from 60% of
the lowest to 140% of the highest quote) with the same random draws, and $\gamma$ is linear in
$\ln F$ between them and flat beyond. History tests it on monthly data,

$$
c_m = a_{month(m)} + b \ln \bar P_m + \beta\, \text{share}_m + \varepsilon_m,
$$

with month effects $a$, the technology's share of load (its build-out) and HC1 standard errors
(`src/ppa_lab/analysis/level_effect.py`; sample from `[ppa] level_effect_start_year`).

| Slope $b$ (change of capture rate per unit of $\ln$ price) | Solar | Wind onshore |
|---|---|---|
| History 2023-2026, 45 months (95% interval) | 0.27 (0.10 to 0.45), t = 3.1 | 0.02 (−0.09 to 0.14) |
| History 2021-2026, 69 months | 0.10 (0.06 to 0.13) | −0.00 (−0.04 to 0.04) |
| Model, recent level (105) to Cal-27 (141) | 0.25 | 0.07 |
| Model, over the tenor's forwards (88 to 141) | 0.28 | 0.08 |

The model lies inside history's 95% interval for both technologies, and history rejects the
shape-factor view for solar. The 2021-2026 slope is smaller, which fits the mechanism: the
lift acts on hours near zero, and at a 9-11% solar share of load in 2021-2022 those were rare
whatever the level. The two history sensitivities of Step 7 replace $\gamma$ with
$c_{ref} + b \ln(F / F_{ref})$ from the analog pool's level $F_{ref}$, at both ends of the
interval, for the first year too.

## 11. Hedging with futures (PPA-8)

Code: `src/ppa_lab/hedging/` (`products.py`, `hedge.py`); report `reports/step08_hedging.md`;
results `data/processed/hedging.json`. Same scenarios as section 10.

**Products.** EEX German power futures as masks $M_k$ over the delivery hours, in local time:
Cal base (all hours), Cal peak (Monday to Friday 08:00-20:00, public holidays included, as on
EEX), quarters Q1-Q4 and months M01-M12 (base). The model forward of product $k$ is the
scenarios' mean price over its hours, $F_k = \frac{1}{S\,|M_k|}\sum_s \sum_{t \in M_k} P_{s,t}$,
so every hedge is fair in expectation and changes only the spread.

**Payoff.** Selling $h_k$ MW of product $k$ pays, per scenario,

$$
H_s = \sum_k h_k X_{s,k}, \qquad X_{s,k} = \sum_{t \in M_k} (F_k - P_{s,t}).
$$

**Minimum-variance hedge.** For a revenue $C_s$ (merchant: $\sum_t q_{s,t} P_{s,t}$),

$$
h^\star = \arg\min_h \operatorname{Var}(C + X h)
= -\left(\tilde X^\top \tilde X\right)^{-1} \tilde X^\top \tilde C,
$$

a least-squares fit on the centred $\tilde X$, $\tilde C$ (Ederington, 1979); for one product,
$h^\star = -\operatorname{Cov}(C, X)/\operatorname{Var}(X)$. No sign or position limits. Hedge
ratio $= \sum_k h_k |M_k| / \sum_t \bar q_t$ (MW sold as a year average, over the average output in MW);
hedge effectiveness $= 1 - \operatorname{Var}(C + H)/\operatorname{Var}(C)$; CFaR as in section 5.
Strategies compared: none, Cal base at 50% and 100% of the average output, and minimum-variance
with Cal base, quarters and months.

**Buyer's hedge.** The PPA buyer of section 10 sells a band $B$; Step 7 used
$B = E[\sum_t q_t]/T$. Step 8 also reports $B^\star$, the minimum-variance band for the buyer's
position $\sum_t q_{s,t}(P_{s,t} - K^\star)$, and the premium $\pi_{joint}$ with $B^\star$.

**Back-test.** For year $Y$, sell $h$ MW of Cal base at $F_Y = \bar P_{Y-1}$, the previous
local calendar year's average day-ahead price (a naive proxy, no futures history in the
project); hedge P&L $= h \sum_{t \in Y} (F_Y - P_t)$ next to the merchant revenue of the measured
historical output. $h$ = minimum-variance ratio $\times$ P50 average output.

**Market check.** Published Cal base (and peak) quotes (`[hedging.market_quotes]`: product,
delivery year, price, date, source URL) against $F_k$; the indicative price at the latest Cal
base quote is the section 10 stack with the whole forward curve and the fair price scaled by
$F^{mkt}/\bar P$ (capture rate, premium and costs unchanged; the dashboard's forward knob).
If the model's forward is within 5% of the latest quote (anchored, since version 1.1), the
report shows instead how far the quotes moved over time. The quotes are from secondary web
sources and stand in for EEX settlement prices.

## 12. Assumptions and limitations

| Assumption | Effect | Addressed in |
|---|---|---|
| National profile instead of a site profile (Step 3 back-test) | Smoother output, no site-specific volume risk | PPA-4 site models; back-test re-run later |
| Hourly ERA5 at a ~0.25° grid point | Smooths gusts and local terrain; coastal cells mix land and sea | site chosen on land; v2: downscaling or measured data |
| Site models include losses and availability (v1.3: calibrated to the published yields, solar 12.4%, wind 26.4% incl. curtailment the model cannot see) and degradation in later years, but no explicit grid curtailment; unpublished layout details (tilt, DC/AC, hub height, Nordex curve) are assumptions | Redispatch is heavy in northern Germany but compensated (§13a EnWG), so roughly revenue-neutral for the producer; a PPA must say who bears the undelivered volume | Contract clause; v2: curtailment data |
| Years assumed independent for P90 (10 years) | Too optimistic if weather has trends or persistence | PPA-6 (resampling) |
| Prior-year prices instead of forward prices | Strikes are naive, not market quotes | PPA-5 (price model); PPA-8 compares with market quotes |
| One history, no scenarios | No distribution, no risk premium | PPA-5 (price paths); PPA-6/PPA-7 (joint Monte Carlo, premia) |
| Price model: symmetric transform, no soft floor at zero | Too few hours just below 0 EUR/MWh, too many deep negative hours | v2 of the price model |
| Price paths independent of weather (PPA-5) | Capture rates overstated (wind 1.02 vs 0.88, solar 0.62 vs 0.555 in 2025) | Done in PPA-6 (section 9) |
| Two sites stand in for national weather | National solar and wind, and weather abroad, are only proxied; weather explains about half of daily price moves | v2: national and neighbour weather |
| Analog pool from one window (2024-2026) | Solar dips deepen year by year: 2024 too low in-sample; 2027 dips may be deeper than the pool's | Sensitivity reported; PPA-7 chooses the pool |
| Linear daily response per season | No saturation (e.g. once prices hit zero, more wind changes little) | Analog patterns carry part of it; v2 |
| Parks produce at negative prices unless the contract has the clause | Merchant revenue includes negative-price hours (solar: 9% of output at 2027 prices); a rational merchant would curtail | The clause structure (sections 3, 10); v2: curtailment in the merchant case |
| One delivery year of scenarios; later years by the forward curve, the level response, drift and degradation | Later years' capture rates come from the first year's scenarios rebuilt at each year's forward (first year's calendar, quarter shape and analog days) | v1.5 (PPA-8d); v2: scenarios per contract year |
| Premium from a one-year 5% quantile, applied to every year | Ignores averaging over ten weather years and the growing level uncertainty | v2: multi-year scenarios |
| Buyer hedges with one baseload band at the model's average price | No transaction costs, no basis to the real forward | PPA-8: minimum-variance band (solar premium 5.4 instead of 8.4 EUR/MWh in v1.2); transaction costs v2 |
| One calibration window (2024-2026), in-sample validation only | Regime changes and out-of-sample errors not tested | v2: rolling, out-of-sample validation |
| Cal base forwards from published quotes (Cal-27 140.21, Cal-28 104.75, Cal-29 87.58), held flat after 2029; quarter shape from Q1-Q4/27 quotes of 14 Sep 2026; months and hours from history | Quotes are a month older than the Cal level and come from secondary sources; later years keep the first year's seasonal shape; 2030-2036 rest on the Cal-29 quote | v1.1-1.2 (PPA-8b, 8c); v2: monthly curve (HPFC) from EEX settlements |
| Capture rate rises with the price level (arcsinh: hours near zero are lifted) | Solar capture rate 0.48 at 88 EUR/MWh, 0.61 at 141. History 2023-2026 confirms it for solar (slope 0.27, 95% 0.10 to 0.45; model 0.25); for wind history cannot tell it from zero (model 0.07 inside). Holding the first year's capture rate instead overstated the solar ten-year price by 9.8 EUR/MWh | v1.5 (PPA-8d): tested on monthly history; history's 95% range as a Step 7 sensitivity (solar −0.1 to +2.0 EUR/MWh) |
| Solar capture-rate trend −1 pp a year at a fixed level | History's build-out coefficient (−2.9 per unit of solar's share of load) at the 2022-2025 pace (+1.3 pp of load a year) means about −3.7 pp a year; the trend assumes storage, flexible demand and curtailment slow it | −2 pp sensitivity in PPA-7; backlog PPA-8e |
| The forward moves fast | Cal-27 base moved between 104 and 140 EUR/MWh from July to October 2026 | Refresh the quotes on the pricing day; forward ±10% sensitivity |
| Hedges at the model forward, no limits, no costs | Real hedges trade at market prices with bid-ask spreads, margining and position limits; unconstrained monthly hedges can be negative | v2: constraints (no negative sales), costs |
| Hedge back-test with last year's average as forward | Not a market price; two years only, so it illustrates, not measures | v2: EEX settlement history |
| Market quotes from secondary web sources | Not official EEX settlements; dates differ | Replace with EEX data |
| Measured generation is after curtailment | Slightly higher capture prices than official market values (Step 2) | Backlog PPA-2b |
| Balancing, route-to-market and credit costs as fixed EUR/MWh | Not modelled from imbalance prices or counterparty data | Stated assumptions in PPA-7; models in v2 |
| Negative-price clause assumes curtailment | No cost of producing at negative prices | – |
| Option premiums not included in cash flows (history) | Floors and caps shown as payoffs only in the back-test | PPA-7 prices the floor on scenarios |
| No taxes, grid fees, guarantees of origin | Not part of the energy price | – |

---

## Changelog of this note

- **v0, PPA-3:** structures, fair prices, discounting, back-test design.
- **v0.1, PPA-4:** volume section (weather conversion, solar and wind models, P50/P90).
- **v0.2, PPA-5:** stochastic price model (section 8); four LaTeX commands in section 7 that
  had been saved as control characters (`\t`, `\a`, `\f`, `\r`) restored.
- **v0.3, PPA-6:** joint weather and price scenarios (section 9); limitations updated.
- **v0.4, PPA-7:** pricing and risk on the scenarios (section 10); limitations updated.
- **v1.0, PPA-8:** hedging with futures and the market check (section 11); assumptions
  renumbered to section 12; limitations updated.
- **v1.1, PPA-8b:** the price level anchored to the market (Cal-27 base quote of 9 Oct 2026,
  forward curve for later years held flat after the last quote); section 10 tenor and section
  11 market check updated; limitations updated.
- **v1.2, PPA-8c:** quarterly levels at the market's seasonal shape (section 9); a solar
  capture-rate trend of −1 pp a year in the base case (section 10); availability and
  curtailment stated correctly in the limitations.
- **v1.3, PPA-4b:** two Encavis parks (Borrentin solar, Everswinkel wind) from public data;
  losses calibrated to the published yields (section 7).
- **v1.4, PPA-1b:** market history from 2021 (no change to the method).
- **v1.5, PPA-8d:** each later year's capture rate moves with its forward along the model's
  level response, tested on 2021-2026 history (section 10); limitations updated.
