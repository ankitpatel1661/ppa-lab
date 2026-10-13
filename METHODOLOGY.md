# Methodology

How `ppa-lab` values renewable power purchase agreements (PPAs): the definitions,
formulas and conventions behind the code, and their limitations.

**Version 0.1** (ticket PPA-4): cash flows and fair prices of the standard structures,
applied to history (PPA-3), and site volumes from weather with P50/P90 (PPA-4, section 7).
Later versions add simulated prices and joint scenarios (PPA-5, PPA-6), risk premia
(PPA-7) and hedging (PPA-8).

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
  `src/ppa_lab/analysis/capture.py` (capture prices).

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
Nr. 3.3 and 4.3, per quarter-hour), which the project reconciles against (Day 2).
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
Version 0 quantifies only the first term on history; the others follow in PPA-7.

---

## 5. Risk measures (used from PPA-7)

For simulated contract cash flows $\Pi$ (per scenario):

$$
\text{premium} = \frac{E[\Pi] - q_{5\%}(\Pi)}{E\left[\sum_t q_t\right]}, \qquad
\text{CFaR}_{95} = E[CF] - q_{5\%}(CF).
$$

---

## 6. Historical back-test (version 0)

Implemented in `pricing/backtest.py`; report `reports/day03_ppa_structures.md`.

- **Parks:** 50 MW solar (1,000 full-load hours) and 30 MW onshore wind (2,000 h), using
  the national profile of their technology, scaled per year to capacity × full-load hours.
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
G_t = G^{API}_{t+1h}, \qquad x_t = 	frac12\,(x^{API}_t + x^{API}_{t+1h}).
$$

Every build checks that irradiance then matches the clear-sky sun at mid-interval ($t$ + 30 min).

**Solar (pvlib).** Sun position at mid-interval; plane-of-array irradiance (Hay-Davies);
cell temperature (Faiman); PVWatts DC with $\gamma = -0.35\%/K$; system losses
$(1 - L)$; PVWatts inverter (96%) clipped at the AC capacity $P_{DC}/r$ (DC/AC ratio $r$).

**Wind (windpowerlib).** Hourly shear exponent from the two heights, clipped to $[0, 0.6]$,
and the power law to hub height $h$:

$$
lpha_t = rac{\ln(v_{100,t}/v_{10,t})}{\ln 10}, \qquad
v_{hub,t} = v_{100,t}\left(rac{h}{100}ight)^{lpha_t},
$$

then the turbine power curve (no air-density correction) scaled to the park capacity, times
$(1 - L)$ for wake, availability and electrical losses.

**Volume statistics.** For annual energies $E_y$ over $N$ weather years (mean $\mu$, sample
standard deviation $\sigma$):

$$
P50 = \operatorname{median}(E_y), \qquad
P90_{1y} = \mu - 1.2816\,\sigma, \qquad
P90_{10y} = \mu - 1.2816\,rac{\sigma}{\sqrt{10}},
$$

the last assuming independent years. Site models are checked against national generation of
the same technology (hourly correlation, monthly shares, capture rate), because no official
figure exists for an illustrative park.

## 8. Assumptions and limitations

| Assumption | Effect | Addressed in |
|---|---|---|
| National profile instead of a site profile (Day 3 back-test) | Smoother output, no site-specific volume risk | PPA-4 site models; back-test re-run later |
| Hourly ERA5 at a ~0.25° grid point | Smooths gusts and local terrain; coastal cells mix land and sea | site chosen on land; v2: downscaling or measured data |
| Site models give potential output | No grid curtailment (heavy in Schleswig-Holstein), outages or degradation | v2 |
| Years assumed independent for P90 (10 years) | Too optimistic if weather has trends or persistence | PPA-6 (resampling) |
| Prior-year prices instead of forward prices | Strikes are naive, not market quotes | PPA-5/PPA-8 (price model, futures) |
| One history, no scenarios | No distribution, no risk premium | PPA-6/PPA-7 (Monte Carlo) |
| Measured generation is after curtailment | Slightly higher capture prices than official market values (Day 2) | Backlog PPA-2b |
| No balancing, imbalance, route-to-market or credit costs | Fair prices are upper bounds | PPA-7 |
| Negative-price clause assumes curtailment | No cost of producing at negative prices | – |
| Option premiums not included in cash flows | Floors and caps shown as payoffs only | PPA-7 |
| No taxes, grid fees, guarantees of origin | Not part of the energy price | – |

---

## Changelog of this note

- **v0, PPA-3:** structures, fair prices, discounting, back-test design.
- **v0.1, PPA-4:** volume section (weather conversion, solar and wind models, P50/P90).
