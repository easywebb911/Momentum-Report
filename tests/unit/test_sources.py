"""QUELLEN-VOLLSTAENDIGKEIT: 1:1-Abgleich Code <-> Methodik-Seite.

Jede Score-Komponente traegt ihre Quelle im Code; die Methodik-Seite listet
exakt dieselben. Weil die Seite aus sources.SOURCES erzeugt wird, ist das
strukturell — hier wird es zusaetzlich nachgewiesen, inklusive
Grep-Nachweis im Quelltext der Rechenfunktionen.
"""

from __future__ import annotations

import html as _html
from pathlib import Path

import pytest

from momentum.config import WEIGHT_HIGH_52W, WEIGHT_MOMENTUM_12_1
from momentum.render import HONESTY, render_methodik
from momentum.sources import SCORE_COMPONENT_SOURCES, SOURCES

SCORING_QUELLTEXT = Path("src/momentum/scoring.py").read_text(encoding="utf-8")
METHODIK = render_methodik()


def test_jede_gewichtete_komponente_hat_belege():
    assert WEIGHT_MOMENTUM_12_1 > 0 and WEIGHT_HIGH_52W > 0
    assert set(SCORE_COMPONENT_SOURCES) == {"momentum_12_1", "high_52w"}
    for komponente, keys in SCORE_COMPONENT_SOURCES.items():
        assert keys, f"{komponente} ohne Quelle"
        for key in keys:
            assert key in SOURCES, f"{komponente}: unbekannter Quellenschluessel {key}"


@pytest.mark.parametrize("key", sorted({k for ks in SCORE_COMPONENT_SOURCES.values() for k in ks}))
def test_grep_nachweis_quelle_steht_im_rechencode(key):
    """Der Beleg muss im Quelltext der Rechenfunktionen stehen, nicht nur im Dict."""
    assert key in SCORING_QUELLTEXT, f"Beleg {key} fehlt als Kommentar in scoring.py"


@pytest.mark.parametrize("key", sorted(SOURCES))
def test_jede_quelle_erscheint_auf_der_methodik_seite(key):
    quelle = SOURCES[key]
    # die Seite ist HTML — "&" steht dort als "&amp;"
    assert _html.escape(quelle.authors) in METHODIK, f"{key}: Autoren fehlen"
    assert str(quelle.year) in METHODIK, f"{key}: Jahr fehlt"
    assert _html.escape(quelle.journal) in METHODIK, f"{key}: Journal fehlt"


def test_methodik_seite_nennt_keine_unbekannte_quelle():
    """Gegenrichtung: keine Autorennennung auf der Seite ohne Eintrag im Code."""
    bekannt = {q.authors for q in SOURCES.values()}
    # Autorennamen, die auf der Seite auftauchen duerften
    for name in ("Jegadeesh", "George", "Hwang", "Rouwenhorst", "Moskowitz", "Asness", "Chui", "Fama"):
        if name in METHODIK:
            assert any(name in autoren for autoren in bekannt), name


def test_alle_vier_ehrlichkeits_anzeigen_haengen_an_einer_quelle():
    assert len(HONESTY) == 4
    for key, _titel, _text, _link in HONESTY:
        assert key in SOURCES, f"Ehrlichkeits-Anzeige ohne Beleg: {key}"


def test_ehrlichkeits_anzeigen_treffen_die_beauftragten_aussagen():
    keys = [key for key, *_ in HONESTY]
    assert keys == ["portfolio_statistic", "momentum_crash", "decay", "long_only"]
    texte = " ".join(f"{t} {x}" for _k, t, x, _l in HONESTY)
    assert "keine Einzelaktien-Prognose" in texte.lower() or "Keine Einzelaktien-Prognose" in texte
    assert "0,3 %" in texte
    assert "MINUS" in texte
    # der Crash-Hinweis verlinkt die Trend-Ampel-Erklaerung
    assert any(link and "trend-ampel" in link for _k, _t, _x, link in HONESTY)


def test_methodik_erklaert_warum_ostasien_fehlt():
    for begriff in ("Japan", "Taiwan", "Südkorea"):
        assert begriff in METHODIK, begriff


def test_methodik_nennt_was_bewusst_nicht_getan_wird():
    for begriff in ("Backtest", "Trefferquote", "Kursziele"):
        assert begriff in METHODIK, begriff


def test_methodik_datei_in_docs_ist_aktuell():
    """docs/methodik.html muss der erzeugten Fassung entsprechen."""
    datei = Path("docs/methodik.html")
    assert datei.exists(), "docs/methodik.html fehlt — 'python -m momentum.build_pages' laufen lassen"
    assert datei.read_text(encoding="utf-8") == METHODIK, (
        "docs/methodik.html ist veraltet — neu erzeugen und mit committen"
    )
