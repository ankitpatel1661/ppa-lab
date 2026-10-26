"""Smoke test of the Streamlit dashboard, headless. Skipped where Streamlit is not installed
(CI installs only the dev extra); the logic itself is tested in test_dashboard.py."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
RESULTS = APP.parents[1] / "reports" / "results.json"
pytestmark = pytest.mark.skipif(not RESULTS.exists(), reason="reports/results.json missing")


def _ppa_lab_modules() -> dict:
    return {k: v for k, v in sys.modules.items() if k == "ppa_lab" or k.startswith("ppa_lab.")}


@pytest.fixture(autouse=True)
def restore_ppa_lab_modules():
    """The app imports ppa_lab afresh, in this process: give later tests the module objects
    their imports point to, or monkeypatching a module would miss the functions they use."""
    saved = _ppa_lab_modules()
    yield
    for name in _ppa_lab_modules():
        del sys.modules[name]
    sys.modules.update(saved)


def test_dashboard_runs_and_reacts_to_assumptions():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    base = at.metric[0].value
    at.slider(key="forward_shift").set_value(-20).run()     # forward 20% lower
    assert not at.exception
    assert at.metric[0].value != base                  # the indicative price moved
    lower = at.metric[0].value
    at.selectbox(key="buildout").set_value("storage_boom").run()   # solar build-out (v1.11)
    assert not at.exception and float(at.metric[0].value) > float(lower)
    at.radio(key="park").set_value("wind_park").run()
    assert not at.exception and at.metric[0].label == "Indicative price"
    assert any("EUR/MWh over" in c.value for c in at.caption)      # the unit, under the number
    assert float(at.metric[0].value) > 0
    assert any(m.label == "Weather" for m in at.metric)   # why the capture rate is what it is


def _gaps() -> set:
    return sys.modules["ppa_lab.dashboard_text"].MISSING     # the app's fresh import, this run


def _english_in_tables(at: AppTest, lang: str) -> list:
    """Table labels still in English although a translation exists."""
    table = sys.modules["ppa_lab.dashboard_text"].TRANSLATIONS[lang]
    labels = [x for df in at.dataframe for x in [*df.value.columns, *df.value.index]]
    return [x for x in labels if isinstance(x, str) and table.get(x, x) != x]


@pytest.mark.parametrize(("lang", "indicative", "central"), [
    ("de", "Indikativer Preis", "Zentral (Basisfall)"),
    ("it", "Prezzo indicativo", "Centrale (caso base)"),
    ("es", "Precio indicativo", "Central (caso base)"),
])
def test_translated_dashboard_has_no_english_left(lang, indicative, central):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.query_params["lang"] = lang
    at.run()
    assert not at.exception and _gaps() == set() and _english_in_tables(at, lang) == []
    assert at.metric[0].label == indicative
    assert "," in at.metric[0].value                    # decimal comma
    assert central in at.dataframe[2].value.index       # composed labels too
    for key, value in (("clause", True), ("pool", "whole"), ("park", "wind_park")):
        at.radio(key=key).set_value(value).run()
        assert not at.exception and _gaps() == set(), key
        assert _english_in_tables(at, lang) == [], key


def test_switching_the_language_keeps_the_assumptions():
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.slider(key="forward_shift").set_value(-20).run()
    english = float(at.metric[0].value)
    for lang in ("de", "it", "es"):
        at.selectbox(key="lang").set_value(lang).run()
        assert not at.exception and at.slider(key="forward_shift").value == -20
        assert float(at.metric[0].value.replace(".", "").replace(",", ".")) == english


def test_a_redeploy_does_not_run_against_an_old_ppa_lab_in_memory(monkeypatch):
    """Streamlit keeps imported modules between reruns; on Cloud the v1.11 script met the v1.10
    dashboard module and failed with a TypeError. The app must import ppa_lab afresh."""
    import types

    stale = types.ModuleType("ppa_lab.dashboard")     # an old module without what the app needs
    monkeypatch.setitem(sys.modules, "ppa_lab.dashboard", stale)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception


def test_each_park_starts_from_its_own_base_case():
    """The cost sliders belong to the park: the wind park opens with its own balancing cost,
    not the solar park's (widget keys keep values across reruns, so they carry the park)."""
    import json

    wind = json.loads(RESULTS.read_text())["parks"]["wind_park"]["assumptions"]
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.radio(key="park").set_value("wind_park").run()
    assert at.select_slider(key="balancing_wind_park").value == wind["balancing_eur_mwh"]
    assert any("+0.0 vs the base case" in c.value for c in at.caption)
