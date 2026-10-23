# Indicative price for a 10-year solar PPA (Borrentin, 114 MWp)

<p class="meta">Memo · 23 Oct 2026 · ppa-lab 1.13.0 · illustrative, from
public data: not an offer, no view on actual contracts · details: Step 7 report</p>

**Bottom line.** For a 10-year pay-as-produced PPA (2027-2036) the negotiation range is
**21.4 to 35.1 EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR 3.02 m to 0.70 m per year (**−77%**) for about
**14.6 EUR/MWh** (EUR 1.77 m per year) against selling at spot.

## The price, layer by layer (EUR/MWh)

| Layer | Solar park | Wind park |
|---|---|---|
| Forward 2027 (average of the scenarios) | 141.1 | 141.1 |
| Shape: output falls in cheap hours | −63.5 | −11.1 |
| **= Fair price 2027** | **77.5** | **129.9** |
| Later years: lower forwards and capture rates; degradation | −42.4 | −43.3 |
| **= Fair price, 10 years** | **35.1** | **86.6** |
| Buyer's risk premium after a baseload hedge | −10.5 | −5.5 |
| Balancing and route to market (assumed) | −2.2 | −1.6 |
| Credit and liquidity (assumed) | −1.0 | −1.0 |
| **= Indicative price, 10 years** | **21.4** | **78.6** |

## What we keep and what we give away

- **Volume** stays with us: P50 120.9 GWh a year, one year in ten below
  113.4 GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium, the credit cost and the 3.1 EUR/MWh that stopping at negative prices saves (balancing is paid either way).

## What would change the price

- Build-out scenarios for solar and storage after 2027: **−3.4 / +8.7**; ±1 pp a year of trend on top: **±3.5** EUR/MWh
- Forward curve −10% / +10%: **−5.6 / +5.5 EUR/MWh**
- Capture rate as far off as the model was out of sample in earlier years (+0.03, Step 6): **−2.1 EUR/MWh**

For comparison, the risk premium and the costs together take
13.7 EUR/MWh off the fair price.

## Recommendations

1. Quote within the range above; do not go below 21.4 EUR/MWh.
2. Offer a negative-price clause as the alternative: we stop producing at negative prices (18% of the solar output in 2027, more later) and are paid 39.3 EUR/MWh per delivered MWh: 27.3 per MWh of output against 21.4 without the clause, at a higher cash flow at risk (EUR 1.29 m instead of 0.70 m).
3. Agree the cannibalisation view with Risk before signing, and for any unsold volume sell about 87% of the average output as Cal base futures: it cuts the merchant cash flow at risk by 72% (solar park).

## Method and limits

496 joint scenarios for 2027: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from 2025-10-01). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
the forward curve, capture rates moving with the price level as in the model (and 2023-2026 history), solar's with the build-out, discounted at 6%. Forward:
EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. Limits: the forwards are published quotes from secondary sources, not EEX files, the costs are illustrative, grid curtailment is not
modelled, and the shape comes from one market regime
(2024-2026). The Cal-27 forward moved between 104 and 140 EUR/MWh since 2026-07-31 (published quotes): refresh the offer with the forward curve on the day of signing.
