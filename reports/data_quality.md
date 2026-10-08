# Data-quality report

Generated 2026-10-08 09:59 UTC by `ppa-lab check`. Result: **23 pass, 1 warn, 0 fail**.

| Dataset | Check | Status | Detail |
|---|---|---|---|
| prices | not empty | PASS | 59,135 rows |
| prices | index is UTC | PASS | tz=UTC |
| prices | no duplicate timestamps | PASS | 0 duplicates |
| prices | sorted in time | PASS | monotonic increasing |
| prices | no missing prices | PASS | 0 NaN values |
| prices | within SDAC clearing-price limits | PASS | 0 values outside limits; observed min -500.00, max 936.28 EUR/MWh |
| prices | intervals at the price floor | WARN | 1 intervals at the harmonised minimum (real events, but worth a look) |
| prices | complete delivery days (DST-aware) | PASS | 1369/1369 days complete |
| prices | covers configured range | PASS | 2023-01-01 to 2026-09-30 |
| prices | resolution regimes | PASS | 60 min 2023-01-01 to 2025-09-30; 15 min 2025-10-01 to 2026-09-30 |
| power | not empty | PASS | 131,420 rows |
| power | index is UTC | PASS | tz=UTC |
| power | no duplicate timestamps | PASS | 0 duplicates |
| power | sorted in time | PASS | monotonic increasing |
| power | required columns present | PASS | solar_mw, wind_onshore_mw, wind_offshore_mw, load_mw |
| power | solar_mw completeness | PASS | 0.000% missing |
| power | wind_onshore_mw completeness | PASS | 0.000% missing |
| power | wind_offshore_mw completeness | PASS | 0.000% missing |
| power | load_mw completeness | PASS | 0.000% missing |
| power | solar is non-negative | PASS | min 0.0 MW |
| power | no solar at night (00-03 local) | PASS | mean night-time solar 0.0 MW |
| power | complete delivery days (DST-aware) | PASS | 1369/1369 days complete |
| power | covers configured range | PASS | 2023-01-01 to 2026-09-30 |
| power | resolution regimes | PASS | 15 min 2023-01-01 to 2026-09-30 |
