"""The forward's description names its source and the curve, or says it is an assumption."""

import pytest

from ppa_lab.pricing.forwards import describe_forward


def test_a_market_forward_names_its_date_source_and_curve():
    text = describe_forward({"price_eur_mwh": 140.21, "date": "2026-10-09",
                             "source": "https://www.tacto.ai/en/energy/electricity-price"},
                            {"2029": 87.58, "2028": 104.75}, 2027)
    assert text == ("EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via "
                    "tacto.ai); later years follow the forward curve (2028: 104.75, 2029: 87.58), "
                    "held flat after 2029")


def test_an_assumed_forward_says_so():
    text = describe_forward({"price_eur_mwh": 85.0}, {}, 2027)
    assert text == "85.00 EUR/MWh (an assumption, not a market quote); flat over the tenor"


def test_quarter_forwards_keep_the_market_shape_and_the_annual_forward():
    from types import SimpleNamespace

    import pandas as pd

    from ppa_lab.pricing.forwards import quarter_forwards
    quotes = SimpleNamespace(quarters={1: 179.47, 2: 114.04, 3: 120.35, 4: 130.09})
    f = quarter_forwards(140.21, quotes, 2027, "Europe/Berlin")
    assert f[1] / f[2] == pytest.approx(179.47 / 114.04)                 # shape kept
    local = pd.date_range("2027-01-01", "2028-01-01", freq="h", tz="Europe/Berlin",
                          inclusive="left")
    hours = pd.Series(local.quarter).value_counts()
    assert sum(hours[q] * f[q] for q in f) / hours.sum() == pytest.approx(140.21)
    assert quarter_forwards(140.21, None, 2027, "Europe/Berlin") is None


def test_the_description_names_the_quarterly_shape():
    text = describe_forward({"price_eur_mwh": 140.21, "date": "2026-10-09", "source": None,
                             "quarters": {"1": 185.29, "2": 117.74, "3": 124.26, "4": 134.31},
                             "quarters_date": "2026-09-14"}, {}, 2027)
    assert "quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, " \
           "quotes of 2026-09-14)" in text
