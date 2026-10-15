"""The forward's description names its source and the curve, or says it is an assumption."""

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
