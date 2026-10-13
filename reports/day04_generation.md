# Day 4 report: weather to power

Generated 2026-10-13 09:07 UTC by `ppa-lab weather`.
Weather: CC BY 4.0 - Open-Meteo.com; contains modified Copernicus Climate Change Service information (ERA5). Hourly ERA5 reanalysis per site; radiation converted from
end-of-hour to interval-beginning labels (checked against the sun's position).

## 1. The parks

| Park       | Site                             | Requested        | ERA5 grid point        | Capacity    | Model                                                        |
|:-----------|:---------------------------------|:-----------------|:-----------------------|:------------|:-------------------------------------------------------------|
| Solar Park | Lusatia, Brandenburg             | 51.75 N, 14.25 E | 51.75 N, 14.25 E, 68 m | 50 MWp (DC) | tilt_deg=25, azimuth_deg=180, dc_ac_ratio=1.2, losses_pct=10 |
| Wind Park  | North Frisia, Schleswig-Holstein | 54.50 N, 9.25 E  | 54.50 N, 9.25 E, 30 m  | 30 MW       | turbine_type=V126/3450, hub_height_m=137, losses_pct=12      |

## 2. Annual energy over the weather years (volume risk)

P50 = median weather year. P90 = energy exceeded in 90% of years (normal approximation,
mean − 1.2816 σ); for a 10-year average σ shrinks by √10.

|                                     | Solar Park                                       |
|:------------------------------------|:-------------------------------------------------|
| Weather years                       | 1995-2025 (31)                                   |
| P50 (median year)                   | 55.1 GWh = 1,102 kWh/kWp                         |
| Mean                                | 55.0 GWh                                         |
| Year-to-year variability (std, CoV) | 2.7 GWh (5.0%)                                   |
| P90, one year                       | 51.5 GWh (-6.4% vs mean)                         |
| P90, 10-year average                | 53.9 GWh (-2.0%)                                 |
| Worst / best year                   | 2001: 49.2 GWh (-10.7%) / 2018: 59.9 GWh (+8.9%) |
| Linear trend                        | +2.5% per decade                                 |

|                                     | Wind Park                                        |
|:------------------------------------|:-------------------------------------------------|
| Weather years                       | 1995-2025 (31)                                   |
| P50 (median year)                   | 110.0 GWh = 3,668 full-load hours                |
| Mean                                | 109.9 GWh                                        |
| Year-to-year variability (std, CoV) | 6.0 GWh (5.5%)                                   |
| P90, one year                       | 102.2 GWh (-7.0% vs mean)                        |
| P90, 10-year average                | 107.4 GWh (-2.2%)                                |
| Worst / best year                   | 2003: 99.1 GWh (-9.8%) / 1998: 120.8 GWh (+9.9%) |
| Linear trend                        | +0.1% per decade                                 |

## 3. Checks against national data

The site models are compared with national generation of the same technology (Day 1)
and priced with the same hourly day-ahead prices (capture rate as on Day 2).

| Park       |   Year |   Hourly correlation with national |   Capture rate, site |   Capture rate, national |   Site capture price (EUR/MWh) |
|:-----------|-------:|-----------------------------------:|---------------------:|-------------------------:|-------------------------------:|
| Solar Park |   2023 |                               0.92 |                0.781 |                    0.759 |                          74.31 |
| Solar Park |   2024 |                               0.92 |                0.622 |                    0.592 |                          48.85 |
| Solar Park |   2025 |                               0.92 |                0.555 |                    0.516 |                          49.58 |
| Wind Park  |   2023 |                               0.75 |                0.849 |                    0.824 |                          80.79 |
| Wind Park  |   2024 |                               0.72 |                0.827 |                    0.822 |                          64.9  |
| Wind Park  |   2025 |                               0.74 |                0.881 |                    0.865 |                          78.67 |

## 4. What the numbers say

- **Solar Park:** P50 1,102 kWh/kWp; one year in ten falls below -6.4% of the mean, the worst year (2001) was -10.7%; trend +2.5% per decade. Hourly correlation with the national fleet 0.92-0.92; capture rate site 0.653 vs national 0.622 (average of the check years).
- **Wind Park:** P50 3,668 full-load hours; one year in ten falls below -7.0% of the mean, the worst year (2003) was -9.8%; trend +0.1% per decade. Hourly correlation with the national fleet 0.72-0.75; capture rate site 0.852 vs national 0.837 (average of the check years).

## 5. Charts

![annual](figures/day04_annual_yield.png)

![monthly](figures/day04_monthly_shares.png)
