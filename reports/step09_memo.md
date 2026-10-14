# Indicative price for a 10-year solar PPA (Lusatia, 50 MWp)

<p class="meta">Memo · 14 Oct 2026 · ppa-lab 0.9.0 · illustrative analysis
from public data, not an offer · details: reports/step07_ppa_pricing.md</p>

**Bottom line.** For a 10-year pay-as-produced PPA (2027-2036) the negotiation range is
**33.3 to 41.1 EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR 1.44 m to 0.20 m per year (**−86%**) for about
**6.3 EUR/MWh** (EUR 0.35 m per year) against selling at spot.

## The price, layer by layer (EUR/MWh, 2027)

| Layer | Solar park | Wind park |
|---|---|---|
| Forward (assumed 85; average of the scenarios) | 85.4 | 85.4 |
| Shape: output falls in cheap hours | −44.3 | −10.6 |
| **= Fair price** | **41.1** | **74.8** |
| Buyer's risk premium after a baseload hedge | −5.3 | −3.4 |
| Balancing and route to market (assumed) | −1.5 | −2.0 |
| Credit and liquidity (assumed) | −1.0 | −1.0 |
| **= Indicative price** | **33.3** | **68.4** |

## What we keep and what we give away

- **Volume** stays with us: P50 55.1 GWh a year, one year in ten below
  51.5 GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium and the credit cost (balancing is paid either way).

## What would change the price

- Older days represent 2027 (whole 2024-2026 window instead of the last 12 months): **+7.6 EUR/MWh**
- Capture-rate trend ±1 pp per year: **±3.4 EUR/MWh**
- Forward ±10%: **±4.1 EUR/MWh**

The view on solar cannibalisation (which past represents 2027, and the trend) matters
more than the risk premium and the costs together.

## Recommendations

1. Quote within the range above; do not go below 33.3 EUR/MWh.
2. Keep a negative-price clause out, or price it separately: 25% of the solar output
   falls in hours with negative prices and would be unpaid.
3. Agree the cannibalisation view with Risk before signing, and hedge the level of any unsold
   volume with baseload forwards (next step of the project: market forwards and hedge ratio).

## Method and limits

496 joint scenarios for 2027: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from 2025-10-01). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
a flat forward and capture rate, discounted at 6%. Limits: the
forward is an assumption, the costs are illustrative, the parks produce their potential output
(no curtailment), and one market regime is in the data. Wind park for comparison: fair
74.8, indicative 68.4 EUR/MWh.
