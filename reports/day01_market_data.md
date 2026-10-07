# Day 1 report: German day-ahead market data

Generated 2026-10-07 12:43 UTC by `ppa-lab report`.
Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE). Bidding zone DE-LU,
delivery days 2023-01-01 to 2026-09-30 (local time, Europe/Berlin).

## 1. Data quality

**23 pass, 1 warn, 0 fail.**
Full details: [data_quality.md](data_quality.md).

## 2. Reconciliation with published figures

| metric             |   year |   ours |   published |   difference |   tolerance | status           |
|:-------------------|-------:|-------:|------------:|-------------:|------------:|:-----------------|
| mean_price_eur_mwh |   2025 |  89.32 |       89.32 |            0 |         0.5 | within tolerance |
| negative_hours     |   2025 | 576    |      575    |            1 |         5   | within tolerance |
| negative_hours     |   2024 | 457    |      459    |           -2 |         5   | within tolerance |
| negative_hours     |   2023 | 301    |      301    |            0 |         5   | within tolerance |

Sources: 2025 mean_price_eur_mwh: netztransparenz.de annual spot market value 2025 = 8.932 ct/kWh (DGS evaluation, Jan 2026); 2025 negative_hours: DGS evaluation of 2025 market values: 575 h with negative prices (pv magazine reports 573 h); 2024 negative_hours: DGS evaluation: 459 h in 2024 (other sources report 457 h); 2023 negative_hours: DGS evaluation: 301 h in 2023.

## 3. Annual statistics

|   Year | First day   | Last day   |   Mean price (EUR/MWh) |     Min |    Max |   Negative hours |   Hours with any negative interval |   Negative time (h) |   Longest negative streak (h) |
|-------:|:------------|:-----------|-----------------------:|--------:|-------:|-----------------:|-----------------------------------:|--------------------:|------------------------------:|
|   2023 | 2023-01-01  | 2023-12-31 |                  95.18 | -500.00 | 524.27 |              301 |                                301 |              301.00 |                            36 |
|   2024 | 2024-01-01  | 2024-12-31 |                  78.51 | -135.45 | 936.28 |              457 |                                457 |              457.00 |                            18 |
|   2025 | 2025-01-01  | 2025-12-31 |                  89.32 | -250.32 | 583.40 |              576 |                                588 |              574.75 |                            20 |
|   2026 | 2026-01-01  | 2026-09-30 |                 107.72 | -499.99 | 747.10 |              471 |                                558 |              463.25 |                            18 |

## 4. Charts

![Monthly price](figures/day01_monthly_price.png)

![Negative hours](figures/day01_negative_hours.png)

![Resolution switch](figures/day01_resolution_switch.png)

![Hourly profile](figures/day01_hourly_profile.png)
