# Indicative price for a 10-year solar PPA (Borrentin, 114 MWp)

<p class="meta">Memo · 15 Oct 2026 · ppa-lab 1.6.0 · illustrative, from
public data: not an offer, no view on actual contracts · details: Step 7 report</p>

**Bottom line.** For a 10-year pay-as-produced PPA (2027-2036) the negotiation range is
**36.8 to 48.6 EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR 3.37 m to 0.78 m per year (**−77%**) for about
**10.3 EUR/MWh** (EUR 1.25 m per year) against selling at spot.

## The price, layer by layer (EUR/MWh)

| Layer | Solar park | Wind park |
|---|---|---|
| Forward 2027 (average of the scenarios) | 141.1 | 141.1 |
| Shape: output falls in cheap hours | −54.7 | −11.9 |
| **= Fair price 2027** | **86.4** | **129.2** |
| Later years: lower forwards and capture rates; degradation | −37.8 | −43.2 |
| **= Fair price, 10 years** | **48.6** | **86.0** |
| Buyer's risk premium after a baseload hedge | −9.3 | −5.5 |
| Balancing and route to market (assumed) | −1.5 | −2.0 |
| Credit and liquidity (assumed) | −1.0 | −1.0 |
| **= Indicative price, 10 years** | **36.8** | **77.5** |

## What we keep and what we give away

- **Volume** stays with us: P50 120.9 GWh a year, one year in ten below
  113.4 GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium and the credit cost (balancing is paid either way).

## What would change the price

- Older days represent 2027 (whole 2024-2026 window instead of the last 12 months): **+5.0 EUR/MWh**
- Capture-rate trend ±1 pp per year: **±3.5 EUR/MWh**
- Forward curve −10% / +10%: **−7.1 / +7.1 EUR/MWh**
- Capture rate as far off as the model was out of sample in earlier years (+0.12, Step 6): **−11.9 EUR/MWh**

For comparison, the risk premium and the costs together take
11.8 EUR/MWh off the fair price.

## Recommendations

1. Quote within the range above; do not go below 36.8 EUR/MWh.
2. Keep a negative-price clause out, or price it separately: 14% of the solar output
   falls in hours with negative prices and would be unpaid.
3. Agree the cannibalisation view with Risk before signing, and for any unsold volume sell about 79% of the average output as Cal base futures: it cuts the merchant cash flow at risk by 73% (solar park).

## Method and limits

496 joint scenarios for 2027: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from 2025-10-01). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
the forward curve, capture rates moving with the price level as in the model (and 2023-2026 history), discounted at 6%. Forward:
EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. Limits: the forwards are published quotes from secondary sources, not EEX files, the costs are illustrative, the parks produce their
potential output (no curtailment), and the shape comes from one market regime
(2024-2026). The Cal-27 forward moved between 104 and 140 EUR/MWh since 2026-07-31 (published quotes): refresh the offer with the forward curve on the day of signing.
