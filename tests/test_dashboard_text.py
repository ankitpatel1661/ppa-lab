"""The dashboard's texts: every label the app translates has a German version with the same
placeholders, the explanations exist in both languages, numbers are written the German way."""

import ast
import re
from pathlib import Path

from ppa_lab.dashboard_text import (
    COLUMN_HELP,
    DE,
    GLOSSARY,
    HEDGING_EXPLAINED,
    HELP,
    METHOD,
    STRUCTURES_EXPLAINED,
    number,
    percent,
    translator,
)

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{(\w*)\}", text))


def _strings(node: ast.AST) -> list[str]:
    """The texts an argument of _() can be: a literal, or either side of `a if c else b`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _strings(node.body) + _strings(node.orelse)
    return []


def app_texts() -> set[str]:
    """Every literal the app passes to _(), and the options of its radio buttons."""
    tree = ast.parse(APP.read_text())
    texts = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "_" and node.args):
            texts |= set(_strings(node.args[0]))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
                and node.targets[0].id in ("PARKS", "POOLS", "CLAUSE")):
            texts |= {v.value for v in node.value.values}
    return texts


def test_every_label_of_the_app_has_a_german_version():
    texts = app_texts()
    assert len(texts) > 100
    assert sorted(t for t in texts if t not in DE) == []


def test_german_templates_keep_the_placeholders():
    assert [k for k, v in DE.items() if _placeholders(k) != _placeholders(v)] == []
    for en, de in ((HELP["en"], HELP["de"]), (COLUMN_HELP["en"], COLUMN_HELP["de"])):
        assert en.keys() == de.keys()
        assert [k for k in en if _placeholders(en[k]) != _placeholders(de[k])] == []
    for texts in (STRUCTURES_EXPLAINED, HEDGING_EXPLAINED, METHOD):
        assert texts.keys() == {"en", "de"}
        assert _placeholders(texts["en"]) == _placeholders(texts["de"])


def test_explanations_fill_in():
    for lang in ("en", "de"):
        for text in HELP[lang].values():
            text.format(start=2027, n=1000, forward_text="EEX Cal-27")
        METHOD[lang].format(n=1000, forward_text="EEX Cal-27", repo="https://example.org")
        assert len(GLOSSARY[lang]) == len(GLOSSARY["en"])
    assert [t for t, _ in GLOSSARY["de"]] != [t for t, _ in GLOSSARY["en"]]


def test_german_numbers():
    assert number(12345.678, 1, "en") == "12,345.7"
    assert number(12345.678, 1, "de") == "12.345,7"
    assert number(-3.5, 2, "de") == "−3,50"
    assert number(2.5, 1, "de", sign=True) == "+2,5"
    assert percent(0.774, 0, "de") == "77\u202f%"       # narrow no-break space
    assert percent(-0.31, 0, "en", sign=True) == "−31%"


def test_translator_falls_back_to_english_and_records_the_gap():
    from ppa_lab import dashboard_text

    missing = dashboard_text.MISSING
    missing.clear()
    assert translator("en")("Park") == "Park"
    assert translator("de")("Your assumptions") == "Ihre Annahmen"
    assert translator("de")("no such label") == "no such label"
    assert missing == {"no such label"}
    missing.clear()
