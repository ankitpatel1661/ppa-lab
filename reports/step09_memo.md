# Indicative price for a 10-year solar PPA (Borrentin, 114 MWp)

<p class="meta">Memo · 03 Nov 2026 · ppa-lab 1.16.0 · illustrative, from
public data: not an offer, no view on actual contracts · details: Step 7 report</p>

**Bottom line.** For a 10-year pay-as-produced PPA (2027-2036) the negotiation range is
**22.6 to 37.2 EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR 3.24 m to 0.79 m per year (**−76%**) for about
**15.0 EUR/MWh** (EUR 1.81 m per year) against selling at spot.

## The price, layer by layer (EUR/MWh)

| Layer | Solar park | Wind park |
|---|---|---|
| Forward 2027 (average of the scenarios) | 155.3 | 155.3 |
| Shape: output falls in cheap hours | −67.5 | −11.7 |
| **= Fair price 2027** | **87.8** | **143.7** |
| Later years: lower forwards and capture rates; degradation | −50.6 | −54.0 |
| **= Fair price, 10 years** | **37.2** | **89.7** |
| Buyer's risk premium after a baseload hedge | −11.4 | −5.6 |
| Balancing and route to market (assumed) | −2.2 | −1.6 |
| Credit and liquidity (assumed) | −1.0 | −1.0 |
| **= Indicative price, 10 years** | **22.6** | **81.5** |

## What we keep and what we give away

- **Volume** stays with us: P50 120.9 GWh a year, one year in ten below
  113.4 GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium, the credit cost and the 2.6 EUR/MWh that stopping at negative prices saves (balancing is paid either way).

## What would change the price

- Build-out scenarios for solar and storage after 2027: **−3.5 / +8.8**; ±1 pp a year of trend on top: **±3.5** EUR/MWh
- Forward curve −10% / +10%: **−5.8 / +5.7 EUR/MWh**
- Capture rate as far off as the model was out of sample in earlier years (+0.03, Step 6): **−2.2 EUR/MWh**

For comparison, the risk premium and the costs together take
14.6 EUR/MWh off the fair price.

## Recommendations

1. Quote within the range above; do not go below 22.6 EUR/MWh.
2. Offer a negative-price clause as the alternative: we stop producing at negative prices (15% of the solar output in 2027, more later) and are paid 41.0 EUR/MWh per delivered MWh: 28.8 per MWh of output against 22.6 without the clause, at a higher cash flow at risk (EUR 1.35 m instead of 0.79 m).
3. Agree the cannibalisation view with Risk before signing, and for any unsold volume sell about 84% of the average output as Cal base futures: it cuts the merchant cash flow at risk by 72% (solar park).

## Method and limits

496 joint scenarios for 2027: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from 2025-10-01). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
the forward curve, capture rates moving with the price level as in the model (and 2023-2026 history), solar's with the build-out, discounted at 6%. Forward:
EEX German Power Cal-27 base 154.42 EUR/MWh (quote of 2026-10-23, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 198.4 / 128.8 / 137.9 / 153.2, quotes of 2026-10-04); later years follow the forward curve (2028: 113.94, 2029: 87.93), held flat after 2029. Limits: the forwards are published quotes from secondary sources, not EEX files, the costs are illustrative, grid curtailment is not
modelled, and the shape comes from one market regime
(2024-2026). The Cal-27 forward moved between 104 and 154 EUR/MWh since 2026-07-31 (published quotes): refresh the offer with the forward curve on the day of signing.
