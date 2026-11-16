# Requirements Traceability Matrix

Which requirement is verified by which test. Companion to
[CONFIGURATION_MANAGEMENT.md](CONFIGURATION_MANAGEMENT.md) §5 (configuration
verification and audit).

Requirements are the acceptance criteria in [docs/BACKLOG.md](docs/BACKLOG.md),
one block per ticket. Tests are the 310 collected tests, defined by 300 test
functions across 43 modules under `tests/` (some are parametrised). Every test
reference below was checked against the repository when this matrix was written;
none is a placeholder.

## How to read it

| Code | Meaning |
|---|---|
| **A** | Automated. A named test fails if the requirement stops holding. |
| **P** | Partly automated. The computed part is tested; an accompanying document (learning page, methodology section, notebook) is verified by review. |
| **R** | Review only. A documentation or presentation deliverable with no automated check. |
| **E** | External fact. Depends on a published source outside the repository and cannot be verified by test. |

## Summary

| | Count |
|---|---|
| Requirement rows | **88** |
| — stated acceptance criteria in `docs/BACKLOG.md` | 81 |
| — reconstructed (ticket has no stated AC: PPA-1, PPA-1b, PPA-6c) | 3 |
| — cross-cutting (owned by no single ticket) | 4 |
| Verified by at least one automated test (**A** + **P**) | **80 (91%)** |
| Review only (**R**) | 7 (8%) |
| External fact (**E**) | 1 (1%) |
| Distinct test functions cited | **265 of 300 (88%)** |
| Test references, all resolving | 284 |
| Test files with no cited test | **0** |

---

## 1. Forward traceability: requirement → test

### PPA-1 — Market-data foundation (Step 1)

> No acceptance criteria are stated for this ticket; the row below is
> reconstructed from the code and tests. See §3.1.

| # | Requirement | V | Verified by |
|---|---|---|---|
| 1.1 | API clients, raw cache, data-quality checks, reconciliation | A | `test_energy_charts.py::test_client_retries_transient_errors`, `::test_client_honours_retry_after_on_rate_limit`; `test_entsoe.py::test_client_returns_only_the_sdac_sequence_by_default`, `::test_token_never_leaks_through_errors_or_repr`; `test_store.py::test_roundtrip_and_manifest`, `::test_raw_files_are_not_overwritten_by_accident`; `test_pipeline.py::test_fetch_downloads_once_then_uses_cache`, `::test_build_processed_creates_native_and_hourly_views`; `test_quality.py::test_real_prices_pass_all_checks`; `test_reconcile.py::test_reconcile_flags_differences_beyond_tolerance`; `test_timeutils.py::test_plain_python_datetime_gets_dst_wrong`; `test_report.py::test_step01_report_end_to_end` |

### PPA-2 — Capture prices and capture rates (Step 2)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 2.1 | `capture_price` volume-weighted, with the three stated invariants | A | `test_capture.py::test_capture_price_is_volume_weighted`, `::test_flat_profile_has_capture_rate_one`, `::test_generation_only_in_negative_hours_gives_negative_capture_price`, `::test_capture_rate_divides_by_the_time_weighted_base_price` |
| 2.2 | Monthly and annual capture prices and rates by technology | A | `test_capture.py::test_capture_table_groups_by_local_month_not_utc_month`, `::test_capture_table_on_a_synthetic_day`; `test_step02_report.py::test_complete_months_drops_partial_first_and_last_month` |
| 2.3 | Reconcile 2025 solar capture price with the official Jahresmarktwert | A | `test_capture.py::test_reconciliation_metrics_are_in_published_units`, `::test_load_market_values_reads_the_reference_file`, `::test_compare_monthly_reports_the_difference_in_ct_kwh`; `test_reconcile.py::test_difference_with_a_documented_cause_is_marked_explained` |
| 2.4 | Chart: capture rate by month and technology | A | `test_step02_report.py::test_gap_and_cannibalisation_charts_render_for_several_months`, `::test_monthly_comparison_text_summarises_each_series` |
| 2.5 | Learning-track page `step02_capture_prices.md` | R | — |

### PPA-3 — PPA structures and pricing maths (Step 3)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 3.1 | Cash flows per interval for every structure | A | `test_contracts.py::test_merchant_sells_everything_at_spot`, `::test_pay_as_produced_pays_the_strike_for_every_mwh`, `::test_negative_price_clause_removes_payment_in_negative_intervals`, `::test_floor_cap_and_collar_on_the_running_example`, `::test_collar_with_floor_equal_to_cap_is_a_cfd`, `::test_collar_rejects_a_floor_above_the_cap` |
| 3.2 | Fair prices as ratios of expectations, with discounting | A | `test_contracts.py::test_fair_price_is_a_ratio_of_expectations_not_an_average_of_ratios`, `::test_discounting_weights_later_cash_flows_less`, `::test_discount_factors_compound_annually_from_the_valuation_date`, `::test_fair_baseload_price_is_the_time_weighted_base_price` |
| 3.3 | **Invariant tests** — floor never lowers value; CfD removes price risk; baseload = merchant + swap; break-even strike = capture price | A | `test_contracts.py::test_floor_never_lowers_value`, `::test_cfd_removes_price_risk_whatever_the_prices`, `::test_baseload_is_merchant_plus_a_baseload_swap`, `::test_fair_pay_as_produced_price_is_the_capture_price`, `::test_at_the_fair_price_every_structure_earns_the_merchant_revenue_in_total` |
| 3.4 | `METHODOLOGY.md` v0 | R | — |
| 3.5 | Back-test 2024-2025 with prior-year strikes, plan and surprise | A | `test_backtest.py::test_strikes_are_fixed_at_the_previous_years_outcome`, `::test_backtest_cash_flows_per_structure`, `::test_plan_is_each_structure_applied_to_the_previous_year_at_the_same_strikes`, `::test_summarise_reports_revenue_surprise_and_worst_month`; `test_step03_report.py::test_step03_report_end_to_end` |
| 3.6 | Learning page, notebook section, exercises | R | — |

AC 3.3 is the cleanest traceability in the project: the backlog names four
invariants and four tests carry those names.

### PPA-4 — Weather to power (Step 4)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 4.1 | ERA5 weather for two sites, cached with provenance | A | `test_open_meteo.py::test_client_requests_era5_in_utc_and_metres_per_second`, `::test_parse_keeps_the_api_labels_and_renames_columns`; `test_weather_pipeline.py::test_fetch_caches_one_file_per_site_and_year`, `::test_the_current_year_is_refetched_until_it_is_complete` |
| 4.2 | Timestamp convention verified against the sun's position | A | `test_open_meteo.py::test_converted_radiation_matches_the_sun_at_mid_interval`, `::test_to_interval_beginning_moves_radiation_back_one_hour_and_averages_instants`; `test_weather_pipeline.py::test_build_generation_refuses_weather_with_shifted_timestamps`; `test_quality.py::test_time_zone_bug_is_caught_by_night_solar_check` |
| 4.3 | pvlib solar park and windpowerlib wind park from configuration | A | `test_weather_models.py::test_solar_is_zero_at_night_and_never_above_the_inverter_limit`, `::test_solar_produces_most_of_its_ac_capacity_on_a_sunny_june_noon`, `::test_solar_scales_with_capacity`, `::test_hotter_modules_produce_less`, `::test_wind_power_follows_the_power_curve_with_losses`, `::test_hub_height_speed_extrapolates_with_the_power_law`, `::test_shear_is_clipped_to_a_physical_range` |
| 4.4 | Annual energy per weather year, P50/P90, trend | A | `test_yields.py::test_annual_energy_sums_each_complete_local_year`, `::test_p_values_from_three_weather_years`; `test_generation_analysis.py::test_yield_trend_per_decade` |
| 4.5 | Checks against national generation | A | `test_generation_analysis.py::test_site_vs_national_compares_correlation_and_capture`, `::test_monthly_shares_sum_to_one_and_follow_the_profile` |
| 4.6 | Report, learning page, notebook, exercises | P | `test_step04_report.py::test_step04_report_end_to_end`, `::test_step04_report_copes_without_complete_weather_years` |

### PPA-5 — Stochastic price model (Step 5)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 5.1 | Local calendar with the nine nationwide holidays | A | `test_price_calendar.py::test_easter_sunday_known_years`, `::test_nationwide_holidays_2025`, `::test_calendar_features_use_local_time` |
| 5.2 | Model in arcsinh space, saved as `price_model.json` | A | `test_price_model.py::test_arcsinh_transform_round_trip_and_negative_prices`, `::test_model_round_trips_through_json`, `::test_the_trend_and_the_pool_days_survive_json`, `::test_each_simulated_day_reuses_one_whole_historical_day` |
| 5.3 | Parameter recovery on synthetic prices with known parameters | A | `test_price_model.py::test_fit_ar1_recovers_a_known_coefficient`, `::test_fit_recovers_the_daily_shape`, `::test_fit_recovers_the_daily_mean_reversion`, `::test_half_life_from_the_ar1_coefficient`, `::test_fit_ar1_ignores_pairs_across_gaps` |
| 5.4 | Level calibrated to a forward price; level volatility | A | `test_price_model.py::test_level_is_calibrated_to_a_target_average_price`, `::test_level_volatility_spreads_the_annual_averages`, `::test_simulation_is_reproducible_and_has_one_row_per_path` |
| 5.5 | Validation against history: distribution, negative hours, autocorrelation | A | `test_price_model.py::test_price_statistics_by_hand`, `::test_autocorrelation_of_an_ar1_is_phi_to_the_lag`, `::test_in_sample_seasonal_mean_uses_the_fitted_monthly_levels`, `::test_daily_factor_has_the_stationary_variance`, `::test_simulation_starts_in_the_stationary_state` |
| 5.6 | Report, learning page, notebook, exercises | P | `test_step05_report.py::test_step05_report_end_to_end` |

### PPA-6 — Joint weather and price scenarios (Step 6)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 6.1 | Daily weather features; day × hour matrices; calendar mapping | A | `test_scenarios_weather.py::test_daily_features_are_capacity_factors_and_mean_temperature_per_local_day`, `::test_daily_features_use_local_days_across_daylight_saving`, `::test_day_hour_matrix_handles_23_and_25_hour_days`, `::test_weather_days_keep_the_calendar_date_and_map_29_february`, `::test_monthly_climatology_averages_only_the_chosen_years` |
| 6.2 | Weather-price link with parameter recovery on synthetic data | A | `test_scenarios_link.py::test_link_recovers_the_wind_response`, `::test_link_keeps_the_memory_that_weather_does_not_explain`, `::test_analog_days_are_the_nearest_within_the_seasonal_window`, `::test_windy_weather_lowers_prices_in_a_future_year`, `::test_sunny_days_get_deeper_middays`, `::test_a_constant_feature_does_not_break_the_analog_search` |
| 6.3 | 31 weather years × 16 price paths, one level for all | A | `test_scenarios_generator.py::test_every_weather_year_gets_the_same_number_of_price_paths`, `::test_volumes_are_the_weather_year_placed_on_the_delivery_calendar`, `::test_delivery_hours_cover_the_local_year`; `test_scenarios_link.py::test_linked_level_is_calibrated_to_the_forward_and_reproducible` |
| 6.4 | Checks: correlation as in history, capture rates in range, MC standard error | A | `test_scenarios_generator.py::test_the_weather_link_lowers_what_solar_and_wind_earn`, `::test_the_average_price_over_all_scenarios_is_the_forward`, `::test_scenario_table_and_fair_price_by_hand` |
| 6.5 | Report, per-scenario results for Step 7, learning page, notebook, exercises | P | `test_step06_report.py::test_step06_report_end_to_end`, `::test_step06_report_explains_missing_weather` |

### PPA-7 — Pricing and risk (Step 7)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 7.1 | All structures on the joint scenarios: fair price, expected and P5 revenue, CFaR95 | A | `test_risk.py::test_premium_and_cfar_by_hand`, `::test_structures_move_risk_from_the_producer` |
| 7.2 | Buyer's premium after a baseload hedge, split into profile and volume | A | `test_risk.py::test_profile_and_volume_parts_of_the_premium`, `::test_the_buyer_breaks_even_at_the_fair_price`, `::test_a_baseload_hedge_removes_the_level_risk_of_flat_volumes` |
| 7.3 | Price stack from the forward to an indicative price | A | `test_dashboard.py::test_the_stack_adds_up_and_shows_the_trend`, `::test_default_assumptions_reproduce_the_step07_answer` |
| 7.4 | Ten-year price with discounting, degradation and sensitivities | A | `test_risk.py::test_the_tenor_follows_the_delivered_volume`, `::test_tenor_price_with_flat_assumptions_is_the_one_year_price`, `::test_tenor_price_follows_drift_degradation_and_discounting`, `::test_tenor_price_can_follow_a_forward_curve`, `::test_tenor_price_holds_the_last_quoted_year_flat`; `test_dashboard.py::test_sensitivities_move_one_assumption_at_a_time` |
| 7.5 | Analog-pool decision in configuration; results in `ppa_pricing.json` | A | `test_config.py::test_ppa_pricing_settings_match_the_scenarios`; `test_scenarios_link.py::test_the_analog_pool_can_be_restricted_to_recent_days`, `::test_in_sample_effects_use_anomalies_within_the_month` |
| 7.6 | Report, learning page, notebook, exercises | P | `test_step07_report.py::test_step07_report_end_to_end`, `::test_step07_report_explains_missing_weather` |

### PPA-8 — Hedging with futures (Step 8)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8.1 | German futures products on the delivery calendar | A | `test_hedging.py::test_products_cover_the_delivery_hours`, `::test_model_forwards_are_average_prices_over_product_hours` |
| 8.2 | Hedge payoffs and minimum-variance hedges | A | `test_hedging.py::test_min_variance_hedge_recovers_a_known_exposure` |
| 8.3 | Strategies for both parks' merchant output with CFaR and variance removed | A | `test_hedging.py::test_strategies_rank_the_hedges` |
| 8.4 | The PPA buyer's minimum-variance band | A | `test_hedging.py::test_the_buyer_needs_less_than_a_full_band_when_output_is_peaky` |
| 8.5 | Back-test on 2024-2025 and a market check against published quotes | A | `test_hedging.py::test_backtest_sells_at_the_previous_years_average`; `test_config.py::test_hedging_backtest_needs_the_previous_year_and_quotes_name_known_products` |
| 8.6 | Report, `hedging.json`, learning page, notebook, exercises | P | `test_step08_report.py::test_step08_report_end_to_end`, `::test_step08_report_explains_missing_weather` |

### PPA-9 — Memo, dashboard, public MVP (Step 9)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 9.1 | One-page memo generated from Step 7 results (Markdown and PDF) | A | `test_step09_memo.py::test_memo_states_the_answer_and_publishes_the_results`, `::test_memo_without_pricing_results_says_what_to_run`, `::test_memo_uses_the_hedging_results_when_present` |
| 9.2 | Dashboard logic tested without Streamlit; app smoke test | A | `test_dashboard.py::test_structures_table_is_in_eur_millions`, `::test_hedging_table_when_step8_results_are_published`; `test_app.py::test_dashboard_runs_and_reacts_to_assumptions`, `::test_each_park_starts_from_its_own_base_case` |
| 9.3 | Runs from committed results only | A | `test_dashboard.py::test_missing_results_say_how_to_make_them`; `test_app.py::test_a_redeploy_does_not_run_against_an_old_ppa_lab_in_memory` |
| 9.4 | README as a front page with the answer and a CI badge | R | — |
| 9.5 | Learning page, notebook section, exercises | R | — |
| 9.6 | v1.12/v1.13: headline fair price, an explanation behind every number, German version | A | `test_dashboard_text.py::test_every_language_is_offered_and_translated`, `::test_every_label_of_the_app_is_translated`, `::test_translations_keep_the_placeholders`, `::test_explanations_fill_in`, `::test_local_numbers`, `::test_forward_described_in_german_italian_and_spanish`, `::test_translator_falls_back_to_english_and_records_the_gap`; `test_app.py::test_translated_dashboard_has_no_english_left`, `::test_switching_the_language_keeps_the_assumptions` |

### PPA-8b — Anchor the price level to the market forward (v1.1, re-anchored v1.16)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8b.1 | Decide the level: the market curve (decision of 15 Oct 2026) | R | — (decision recorded in `docs/BACKLOG.md` and `CHANGELOG.md`) |
| 8b.2 | Config keys `forward_eur_mwh`, `forward_date`, `forward_source`, `[ppa.forward_curve]` | A | `test_forwards.py::test_a_market_forward_names_its_date_source_and_curve`, `::test_an_assumed_forward_says_so`; `test_config.py::test_the_forward_names_its_source_and_the_curve_covers_later_years` |
| 8b.3 | The capture rate's dependence on the level; sensitivity added | A | `test_risk.py::test_tenor_price_moves_the_capture_rate_with_the_forward_curve`, `::test_level_shift_interpolates_in_log_level_and_is_flat_beyond_the_ends`; `test_dashboard.py::test_the_capture_rate_moves_with_the_level_when_the_response_is_published` |
| 8b.4 | v1.16: re-anchored to the quotes of 23 Oct 2026 | A | `test_step09_memo.py::test_memo_anchored_to_the_market_says_how_far_the_forward_moved` |

### PPA-8c — Quarterly forward curve and the capture rate vs the level (v1.2)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8c.1 | Calibrate quarterly levels to market quarter forwards | A | `test_forwards.py::test_quarter_forwards_keep_the_market_shape_and_the_annual_forward`, `::test_the_description_names_the_quarterly_shape`; `test_config.py::test_quarter_quotes_are_complete_and_average_to_their_cal`; `test_scenarios_generator.py::test_quarterly_forwards_set_each_quarter_and_keep_the_annual_average` |
| 8c.2 | Solar capture-rate trend in the base case | A | `test_price_model.py::test_the_intraday_trend_comes_from_years_not_from_the_season`, `::test_one_year_has_no_trend` |
| 8c.3 | Capture rate vs level on more history; decide between the two views (closed in PPA-8d) | A | `test_level_effect.py::test_the_regression_recovers_a_known_level_effect_and_build_out` |

### PPA-8d — Does the capture rate rise with the price level? (v1.5)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8d.1 | Monthly regression on 2021-2026 history, month effects, share of load, HC1 errors | A | `test_level_effect.py::test_monthly_panel_measures_capture_rate_and_share`, `::test_the_regression_recovers_a_known_level_effect_and_build_out`, `::test_no_level_effect_is_not_mistaken_for_one`, `::test_no_answer_when_the_data_cannot_separate_the_effects`, `::test_the_sample_can_start_later`, `::test_the_log_form_recovers_a_proportional_share_effect` |
| 8d.2 | The model's own slope measured at twelve forwards with the same draws | A | `test_risk.py::test_tenor_price_moves_the_capture_rate_with_the_forward_curve` |
| 8d.3 | Fix: each later year's capture rate moves with its forward | A | `test_risk.py::test_tenor_price_can_follow_a_forward_curve`; `test_step07_report.py::test_tenor_rows_follow_the_curve_and_move_the_capture_rate_with_the_level` |
| 8d.4 | History's 95% range as a Step 7 sensitivity; report, memo lever, METHODOLOGY §10 | P | `test_dashboard.py::test_sensitivities_move_one_assumption_at_a_time` |

### PPA-6b — Years the model never saw, and the negative tail (v1.6)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 6b.1 | Walk-forward test for 2024, 2025 and 2026 | A | `test_step06_report.py::test_step06_report_tests_a_year_the_model_never_saw`, `::test_pool_start_options_cover_window_latest_year_and_last_twelve_months` |
| 6b.2 | Statistics, capture rates and negative-price shares; `out_of_sample.json` | A | `test_step06_report.py::test_step06_report_end_to_end` |
| 6b.3 | Negative prices with their own scale *b*, chosen by a stated rule | A | `test_price_model.py::test_negative_prices_can_have_their_own_scale`, `::test_arcsinh_transform_round_trip_and_negative_prices` |
| 6b.4 | The out-of-sample error priced in Step 7 and shown in the memo | P | `test_step07_report.py::test_step07_report_end_to_end`; `test_step09_memo.py::test_memo_states_the_answer_and_publishes_the_results` |

### PPA-8e — Capture rates that follow the build-out (v1.7)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8e.1 | Use the out-of-sample test as the yardstick | A | `test_step06_report.py::test_step06_report_tests_a_year_the_model_never_saw` |
| 8e.2 | Delivery year: historical days moved by the measured trend | A | `test_price_model.py::test_a_pattern_moves_by_the_trend_times_the_years_between_the_days`, `::test_the_intraday_trend_comes_from_years_not_from_the_season`, `::test_each_simulated_day_reuses_one_whole_historical_day` |
| 8e.3 | Justify −1 pp a year after the delivery year against history's pace | A | `test_level_effect.py::test_share_pace_uses_complete_years` |

### PPA-7b — Curtailment at negative prices (v1.8)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 7b.1 | Merchant and spot-settled structures curtail below a configured price; the plain PPA does not | A | `test_risk.py::test_curtailing_keeps_the_value_a_plain_ppa_destroys`; `test_contracts.py::test_negative_price_clause_removes_payment_in_negative_intervals`, `::test_a_price_of_exactly_zero_is_not_negative` |
| 7b.2 | The clause at E[Σq°P]/E[Σq°] with its own premium, stack and tenor price | A | `test_risk.py::test_curtailment_value_per_mwh_of_potential_output`; `test_dashboard.py::test_the_negative_price_clause_is_priced_per_delivered_mwh` |
| 7b.3 | The value of curtailing in 2027 and in 2021-2026 history; Step 7 §5 | P | `test_step07_report.py::test_step07_report_end_to_end` |
| 7b.4 | Step 8 hedges the curtailing merchant; the memo prices the clause; the dashboard can switch | A | `test_hedging.py::test_strategies_rank_the_hedges`; `test_step09_memo.py::test_memo_uses_the_hedging_results_when_present`; `test_dashboard.py::test_the_negative_price_clause_is_priced_per_delivered_mwh` |

### PPA-7c — The EEG premium against a PPA (v1.9)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 7c.1 | The market premium as a strip of monthly puts, tested by hand | A | `test_eeg.py::test_the_premium_is_a_put_on_each_months_market_value`, `::test_one_annual_put_is_worth_less_than_twelve_monthly_ones`, `::test_no_premium_and_no_output_at_negative_prices`, `::test_reference_must_be_month_or_year` |
| 7c.2 | Market value proxied from the park's capture price; basis measured on history | A | `test_eeg.py::test_basis_ratio_compares_the_official_value_with_the_parks_capture_price` |
| 7c.3 | Per year and over the tenor against the PPA; risk at two price levels | P | `test_step07_report.py::test_step07_report_end_to_end` |

### PPA-8f — Build-out and storage after the delivery year (v1.11)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 8f.1 | Solar and storage build-out scenarios for 2028-2036 in `[buildout]` | A | `test_buildout.py::test_buildout_paths_calibrate_on_the_processed_data`, `::test_kappa_and_lambda_from_history_and_assumptions`; `test_config.py::test_build_out_scenarios_are_complete_and_named` |
| 8f.2 | Capture rates per contract year from the share effect, amplified by seasonality | A | `test_buildout.py::test_seasonal_solar_amplifies_the_share_effect`, `::test_storage_beyond_historys_pace_slows_the_share_and_the_capture_rate_falls`; `test_risk.py::test_build_out_factors_scale_each_years_capture_rate`; `test_step07_report.py::test_tenor_rows_scale_the_capture_rate_by_the_build_out_factors`; `test_dashboard.py::test_a_build_out_scenario_scales_later_capture_rates_for_any_tenor`, `::test_buildout_table_prices_every_scenario_with_the_other_assumptions` |
| 8f.3 | Step 7 §8, memo lever, METHODOLOGY §10, limitations | P | `test_step09_memo.py::test_memo_gives_the_build_out_range_with_the_trend_on_top` |

### PPA-4b — Two Encavis parks instead of illustrative ones (v1.3)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 4b.1 | Ownership confirmed from Encavis press releases | **E** | — external published source; see §3.3 |
| 4b.2 | Sites, capacities and published yields in the configuration | A | `test_config.py::test_backtest_parks_are_configured`, `::test_every_park_has_a_site_and_a_model`; `test_app.py::test_each_park_starts_from_its_own_base_case` |
| 4b.3 | ERA5 for both sites, Steps 3-9 re-run, site models checked against published yields | A | `test_weather_pipeline.py::test_build_generation_writes_hourly_output_per_park`; `test_generation_analysis.py::test_site_vs_national_compares_correlation_and_capture` |
| 4b.4 | Framing: public data only; results are illustrative | R | — |

### PPA-2b — Wind capture prices vs official market values (v1.10)

| # | Requirement | V | Verified by |
|---|---|---|---|
| 2b.1 | Download the TSOs' online extrapolation from netztransparenz.de | A | `test_netztransparenz.py::test_client_uses_client_credentials_and_bearer_tokens`, `::test_client_renews_an_expired_token_and_backs_off_on_rate_limits`, `::test_parse_csv_reads_german_numbers_and_time_zones`, `::test_parse_csv_refuses_unknown_layouts`, `::test_fetch_tso_stores_months_and_skips_cached_ones` |
| 2b.2 | Recompute monthly capture prices and compare with the official values | A | `test_balancing.py::test_capture_prices_and_energy_at_any_resolution`, `::test_bias_is_removed_month_by_month`, `::test_hourly_prices_hold_for_their_quarter_hours`; `test_capture.py::test_compare_monthly_skips_months_without_an_official_value` |
| 2b.3 | Add a `note` to the wind references | A | `test_reconcile.py::test_a_note_does_not_hide_a_difference_within_tolerance`; `test_config.py::test_every_reference_metric_is_computed_by_the_pipeline` |

### PPA-6c — Balancing costs from forecast errors and reBAP (v1.10)

> No acceptance criteria are stated for this ticket; reconstructed. See §3.1.

| # | Requirement | V | Verified by |
|---|---|---|---|
| 6c.1 | Balancing costs from forecast errors and reBAP | A | `test_balancing.py::test_imbalance_cost_by_hand`; `test_netztransparenz.py::test_parse_csv_reads_the_rebap_layout`; `test_step02b_report.py::test_step02b_report_end_to_end`, `::test_step02b_report_explains_missing_data` |

### PPA-1b — History from 2021, the 2022 gas crisis (v1.4)

> No acceptance criteria are stated for this ticket; reconstructed. See §3.1.

| # | Requirement | V | Verified by |
|---|---|---|---|
| 1b.1 | History from 2021 covering the 2022 gas crisis | A | `test_config.py::test_price_model_window_must_lie_inside_the_market_data`, `::test_a_delivery_year_needs_the_previous_year_in_the_data_range`, `::test_scenarios_use_complete_weather_years_and_need_the_price_model`, `::test_price_limits_change_on_29_may_2026`; `test_quality.py::test_price_floor_moved_to_minus_600_on_29_may_2026` |

---

## 2. Cross-cutting requirements

These are relied on by every step and owned by no single ticket. They were added
after the reverse-traceability check in §3.2 found their tests cited by no
requirement.

### CC-1 — Command-line interface and pipeline orchestration

| # | Requirement | V | Verified by |
|---|---|---|---|
| CC-1.1 | Every step command writes its report; `all` runs the whole pipeline; `check` exits non-zero on bad data | A | `test_cli.py::test_parser_defaults`, `::test_all_runs_the_whole_pipeline`, `::test_prices_command_writes_the_step05_report`, `::test_scenarios_command_writes_the_step06_report`, `::test_pricing_command_writes_the_step07_report`, `::test_memo_command_writes_the_memo_and_the_results_file`, `::test_hedging_command_writes_the_step08_report`, `::test_weather_command_builds_generation_and_the_step04_report`, `::test_ppa_command_writes_the_step03_report`, `::test_capture_command_writes_the_step02_report`, `::test_check_fails_with_exit_code_1_on_bad_data` |

### CC-2 — Time zone, daylight saving and resolution handling

| # | Requirement | V | Verified by |
|---|---|---|---|
| CC-2.1 | Local days, DST transitions and the 15-minute resolution switch handled across every dataset | A | `test_timeutils.py::test_hours_in_local_day`, `::test_expected_intervals`, `::test_from_unix_seconds_is_utc`, `::test_interval_minutes_handles_resolution_switch`, `::test_interval_minutes_is_robust_to_gaps`, `::test_to_hourly_averages_quarter_hours_and_keeps_hourly_values`, `::test_to_hourly_rejects_naive_index`, `::test_local_dates_follow_berlin_midnight`; `test_energy_charts.py::test_price_payload_on_dst_days`, `::test_price_payload_with_resolution_switch`; `test_entsoe.py::test_request_uses_utc_period_for_a_local_delivery_day` |

### CC-3 — Configuration integrity

| # | Requirement | V | Verified by |
|---|---|---|---|
| CC-3.1 | Loaded settings are internally consistent and every reference metric is produced | A | `test_config.py::test_project_config_loads`, `::test_inverted_date_range_is_rejected`, `::test_reference_dir_holds_the_official_market_values` |

### CC-4 — Input validation and error handling on every external source

| # | Requirement | V | Verified by |
|---|---|---|---|
| CC-4.1 | Malformed, incomplete or unauthorised responses are rejected with a clear error rather than silently accepted | A | `test_energy_charts.py::test_price_payload_rejects_unknown_unit`, `::test_price_payload_rejects_length_mismatch`, `::test_price_payload_rejects_missing_keys`, `::test_client_does_not_retry_client_errors`, `::test_client_gives_up_after_max_retries`; `test_entsoe.py::test_invalid_xml_is_rejected`, `::test_acknowledgement_document_becomes_a_clear_error`, `::test_unauthorized_token_gives_actionable_message`; `test_open_meteo.py::test_parse_rejects_unexpected_units`, `::test_to_interval_beginning_refuses_gaps`, `::test_client_raises_its_own_error_on_bad_requests`; `test_netztransparenz.py::test_client_gives_up_on_other_errors`; `test_scenarios_link.py::test_missing_weather_days_are_refused`; `test_capture.py::test_capture_price_requires_the_same_time_grid`, `::test_capture_price_without_generation_is_undefined`; `test_contracts.py::test_contracts_refuse_series_on_different_time_grids`; `test_pipeline.py::test_month_chunks_reject_inverted_range`; `test_quality.py::test_duplicate_timestamp_fails`, `::test_missing_quarter_hour_fails_completeness`, `::test_impossible_price_fails` |

---

## 3. Gaps and limitations

### 3.1 Three tickets have no stated acceptance criteria

`PPA-1`, `PPA-1b` and `PPA-6c` appear only as rows in the summary table of
`docs/BACKLOG.md`; they have no `## PPA-n:` block with acceptance criteria. Their
rows in this matrix were **reconstructed from the code and tests**, which is
traceability in the wrong direction: it records what was built, not what was
asked for. A requirement written after the fact cannot fail.

This affects the foundation ticket (`PPA-1`), which is the one carrying the API
clients, the cache and the data-quality gate. Writing acceptance criteria for
those three retrospectively would not fix the ordering problem, but it would at
least make the intent explicit.

### 3.2 Reverse traceability: 265 of 300 tests are cited

35 test functions are not cited against any requirement. They are not untested
behaviour — they are additional cases inside files that are cited (edge cases,
error paths, helper-level assertions). Examples: 5 of 9 in `test_backtest.py`,
4 of 13 in `test_energy_charts.py`, 3 of 15 in `test_capture.py`.

Every test *file* is now cited by at least one requirement. Before the
cross-cutting section was added, `test_cli.py` was cited by none — 11 tests
covering the whole command surface traced to no requirement at all. That is
exactly the kind of gap a reverse check exists to find, and it was found here
rather than assumed absent.

### 3.3 One requirement cannot be verified by test

`PPA-4b.1` — park ownership, capacity and grid connection taken from Encavis
press releases. This is an external published fact. The configuration records
the values and `test_config.py` checks they are present and internally
consistent, but no test can confirm they match the press releases. If the
published figures were misread, every downstream number inherits the error.

### 3.4 Seven requirements are documentation deliverables

The `R` rows are learning-track pages, notebook sections, exercises, the README
front page and `METHODOLOGY.md` version bumps. They are verified by review only.
`make docs` renders them and `make notebook-run` executes every notebook cell
and fails on any error, so the notebooks at least cannot be silently broken —
but nothing checks that a learning page is *correct* or that the methodology
text matches the code it describes.

### 3.5 "End-to-end" report tests check production, not every number

The `*_report_end_to_end` tests assert that a step's report and figures are
produced and are internally coherent. They do not re-derive every number in the
report. The numbers themselves are covered by the unit tests in §1 and by the
29 reconciliation entries described in `CONFIGURATION_MANAGEMENT.md` §5.3. A
report could therefore be produced successfully while containing a number that
no test and no reconciliation entry constrains.

### 3.6 This matrix is maintained by hand

Nothing enforces that it stays current. A new ticket, or a renamed test, will not
break the build. Every test reference here resolved when the matrix was written;
re-checking them is a manual step. Keeping it honest means updating it in the
same change that adds a requirement or renames a test — the discipline, not the
tooling, is the control.

---

## 4. Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-16 | First issue. 88 requirement rows, 284 validated test references, 265 of 300 test functions cited. |
