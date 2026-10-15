# Indicative price for a 10-year solar PPA (Lusatia, 50 MWp)

<p class="meta">Memo · 15 Oct 2026 · ppa-lab 1.2.0 · illustrative analysis
from public data, not an offer · details: reports/step07_ppa_pricing.md</p>

**Bottom line.** For a 10-year pay-as-produced PPA (2027-2036) the negotiation range is
**45.2 to 56.1 EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR 1.67 m to 0.41 m per year (**−75%**) for about
**9.4 EUR/MWh** (EUR 0.52 m per year) against selling at spot.

## The price, layer by layer (EUR/MWh)

| Layer | Solar park | Wind park |
|---|---|---|
| Forward 2027 (average of the scenarios) | 141.0 | 141.0 |
| Shape: output falls in cheap hours | −54.1 | −10.2 |
| **= Fair price 2027** | **86.9** | **130.7** |
| Later years: forward curve falls, capture-rate trend; degradation | −30.8 | −41.2 |
| **= Fair price, 10 years** | **56.1** | **89.5** |
| Buyer's risk premium after a baseload hedge | −8.4 | −4.7 |
| Balancing and route to market (assumed) | −1.5 | −2.0 |
| Credit and liquidity (assumed) | −1.0 | −1.0 |
| **= Indicative price, 10 years** | **45.2** | **81.8** |

## What we keep and what we give away

- **Volume** stays with us: P50 55.1 GWh a year, one year in ten below
  51.5 GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium and the credit cost (balancing is paid either way).

## What would change the price

- Older days represent 2027 (whole 2024-2026 window instead of the last 12 months): **+6.0 EUR/MWh**
- Capture-rate trend ±1 pp per year: **±3.5 EUR/MWh**
- Forward curve ±10%: **±5.6 EUR/MWh**
- The capture rate stays as at the recent price level (104 EUR/MWh) instead of rising with the forward: **−7.2 EUR/MWh**

For comparison, the risk premium and the costs together take
10.9 EUR/MWh off the fair price.

## Recommendations

1. Quote within the range above; do not go below 45.2 EUR/MWh.
2. Keep a negative-price clause out, or price it separately: 10% of the solar output
   falls in hours with negative prices and would be unpaid.
3. Agree the cannibalisation view with Risk before signing, and for any unsold volume sell about 83% of the average output as Cal base futures: it cuts the merchant cash flow at risk by 76% (solar park).

## Method and limits

496 joint scenarios for 2027: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from 2025-10-01). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
the forward curve and a flat capture rate, discounted at 6%. Forward:
EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. Limits: the forwards are published quotes from secondary sources, not EEX files, the costs are illustrative, the parks produce their
potential output (no curtailment), and the shape comes from one market regime
(2024-2026). The Cal-27 forward moved between 104 and 140 EUR/MWh since 2026-07-31 (published quotes): refresh the offer with the forward curve on the day of signing.
