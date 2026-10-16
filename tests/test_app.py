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
    at.sidebar.slider[0].set_value(-20).run()          # forward 20% lower
    assert not at.exception
    assert at.metric[0].value != base                  # the indicative price moved
    lower = at.metric[0].value
    at.sidebar.selectbox[0].set_value("storage_boom").run()   # solar build-out (v1.11)
    assert not at.exception and float(at.metric[0].value) > float(lower)
    at.sidebar.radio[0].set_value("Wind park · Everswinkel · 28.5 MW").run()
    assert not at.exception and "EUR/MWh" in at.metric[0].label
    assert float(at.metric[0].value) > 0


def test_a_redeploy_does_not_run_against_an_old_ppa_lab_in_memory(monkeypatch):
    """Streamlit keeps imported modules between reruns; on Cloud the v1.11 script met the v1.10
    dashboard module and failed with a TypeError. The app must import ppa_lab afresh."""
    import types

    stale = types.ModuleType("ppa_lab.dashboard")     # an old module without what the app needs
    monkeypatch.setitem(sys.modules, "ppa_lab.dashboard", stale)
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
