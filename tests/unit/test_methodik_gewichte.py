"""GEWICHTE JE MARKT AUF METHODIK-SEITE UND KARTE (PR #84, PR 2 von 3).

Die Rechnung (Fahrplan, PR #83) bleibt unberuehrt; hier geht es nur um die
Anzeige:
  * Die Methodik-Seite nennt BEIDE US-Regeln mit Monatsangabe und beide
    Maerkte getrennt -- erzeugt aus config.Market.gewichts_fahrplan, nicht
    aus WEIGHT_*. Sie haengt nur am Fahrplan, nie an Datum oder Uhr.
  * Die Karte liest die Gewichte aus ranking["methode"]: bei 52W-Gewicht 0
    erscheint "nur Info, zaehlt nicht im Score", bei 0.5/0.5 nicht -- und
    fehlt das Feld, ebenfalls nicht (fail-soft).
"""

from __future__ import annotations

import copy
import datetime as _dt
import re
from dataclasses import replace

import pytest

import momentum.render as render
from momentum.config import FAHRPLAN_BEGINN, MARKETS, MARKETS_BY_KEY, GewichtsEintrag
from momentum.render import (
    MarketView,
    gewichte_je_markt_text,
    render_index,
    render_methodik,
)
from momentum.sources import SOURCES, WEIGHTING_SOURCES
from tests.unit.test_render import _ranking

Date = _dt.date
HINWEIS = "nur Info, zählt nicht im Score"


def _text(html: str) -> str:
    """Sichtbarer Text ohne Tags, Leerraum zusammengefasst."""
    ohne_tags = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", ohne_tags.replace(" ", " "))


# --------------------------------------------------------- Methodik-Seite


def test_methodik_nennt_beide_us_regeln_mit_monat_und_beide_maerkte_getrennt():
    text = _text(render_methodik())
    assert "USA: bis Ranking Oktober 2026 50/50, ab Ranking November 2026 100/0" in text
    assert "Deutschland: 50/50" in text
    # Formeln je Markt und Zeitraum
    assert (
        "USA bis Ranking Oktober 2026: Score = 50 × Perzentil(12-1-Momentum) "
        "+ 50 × Perzentil(52-Wochen-Hoch-Nähe)" in text
    )
    assert "USA ab Ranking November 2026: Score = 100 × Perzentil(12-1-Momentum)" in text
    assert (
        "Deutschland: Score = 50 × Perzentil(12-1-Momentum) "
        "+ 50 × Perzentil(52-Wochen-Hoch-Nähe)" in text
    )


def test_zutat_52w_sagt_fuer_usa_klar_dass_sie_nicht_mehr_zaehlt():
    text = _text(render_methodik())
    assert (
        "USA: bis Ranking Oktober 2026 50 %, zählt ab Ranking November 2026 "
        "nicht mehr im Score, wird nur noch angezeigt" in text
    )
    assert "USA: bis Ranking Oktober 2026 50 %, ab Ranking November 2026 100 %" in text


def test_falsch_gewordene_aussagen_sind_weg():
    html = render_methodik()
    assert "Beide Zutaten zählen gleich viel" not in html
    assert "sogar die Nähe zum 52-Wochen-Hoch die stärkere" not in html
    assert "Gleichgewichtung die ehrliche Wahl" not in html
    # Gewichte stehen nicht mehr als feste Zahl im Kartentitel
    assert "(Gewicht 50 %)" not in html


def test_begruendung_usa_und_deutschland_steht_da_ehrlich_formuliert():
    text = _text(render_methodik())
    # USA: tragende Quelle mit beiden Zahlen, IMC mit Gegenzahl
    assert "0,13 % pro Monat" in text and "t-Wert von 0,38" in text
    assert "1,16 % pro Monat" in text and "3,99" in text
    assert "IR von 0,24 gegen 0,20" in text
    assert "0,07 gegen 0,11" in text
    assert "IR = Mehrertrag je Einheit Abweichungsrisiko" in text
    assert "nicht begutachtet" in text
    # Deutschland: ehrlich, nicht "belegt richtig"
    assert "weil nichts Besseres belegt ist" in text
    assert "nicht weil 50/50 als richtig belegt wäre" in text
    assert "nur im SDAX, nicht in DAX und MDAX" in text
    # Zwischenwerte bewusst verworfen
    assert "Zwischenwerte wie 60/40 sind bewusst verworfen" in text
    assert "Parametersuche" in text


@pytest.mark.parametrize("key", WEIGHTING_SOURCES)
def test_jede_gewichtungs_quelle_steht_mit_kennzeichnung_auf_der_seite(key):
    html = render_methodik()
    q = SOURCES[key]
    assert render.e(q.authors) in html
    assert render.e(q.journal) in html
    assert str(q.year) in html


def test_nicht_begutachtete_quellen_sind_im_journal_feld_gekennzeichnet():
    assert "nicht begutachtet" in SOURCES["weights_barroso_wang"].journal
    assert "Arbeitspapier" in SOURCES["weights_barroso_wang"].journal
    assert "nicht begutachtet" in SOURCES["weights_imc"].journal
    assert "Eigeninteresse" in SOURCES["weights_imc"].journal
    assert "Review of Financial Studies 33(5)" in SOURCES["weights_hxz"].journal


def test_methodik_haengt_nur_am_fahrplan_nicht_an_datum_oder_uhr(monkeypatch):
    vorher = render_methodik()

    class KaputteUhr(_dt.date):
        @classmethod
        def today(cls):
            raise AssertionError("render_methodik darf das Datum nicht lesen")

    class KaputteZeit(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("render_methodik darf die Uhr nicht lesen")

        @classmethod
        def utcnow(cls):
            raise AssertionError("render_methodik darf die Uhr nicht lesen")

    monkeypatch.setattr(render._dt, "date", KaputteUhr)
    monkeypatch.setattr(render._dt, "datetime", KaputteZeit)
    assert render_methodik() == vorher


def test_methodik_folgt_dem_fahrplan(monkeypatch):
    """Aendert sich der Fahrplan, aendert sich der Text -- er ist erzeugt,
    nicht abgeschrieben."""
    us = MARKETS_BY_KEY["us"]
    anders = replace(
        us,
        gewichts_fahrplan=(
            GewichtsEintrag(FAHRPLAN_BEGINN, 0.5, 0.5),
            GewichtsEintrag((2027, 3), 1.0, 0.0),
        ),
    )
    assert gewichte_je_markt_text(anders) == (
        "USA: bis Ranking Februar 2027 50/50, ab Ranking März 2027 100/0"
    )
    assert gewichte_je_markt_text(MARKETS_BY_KEY["de"]) == "Deutschland: 50/50"
    neue_maerkte = tuple(anders if m.key == "us" else m for m in MARKETS)
    monkeypatch.setattr(render, "MARKETS", neue_maerkte)
    monkeypatch.setattr(render, "MARKETS_BY_KEY", {m.key: m for m in neue_maerkte})
    text = _text(render_methodik())
    assert "USA: bis Ranking Februar 2027 50/50, ab Ranking März 2027 100/0" in text
    assert "November 2026" not in text


def test_methodik_bezieht_keine_weight_konstanten_mehr():
    quelltext = render.__file__
    with open(quelltext, encoding="utf-8") as f:
        code = f.read()
    assert "WEIGHT_MOMENTUM_12_1" not in code
    assert "WEIGHT_HIGH_52W" not in code


# ------------------------------------------------------------------ Karte


def _view(methode: dict | None) -> MarketView:
    ranking = _ranking(warnung=False)
    if methode is None:
        ranking.pop("methode", None)
    else:
        ranking["methode"] = copy.deepcopy(methode)
    return MarketView(
        market=MARKETS_BY_KEY["us"],
        ranking=ranking,
        price_asof=Date(2026, 12, 1),
        prices={"AAA": 130.5, "BBB": 48.25},
        next_ranking_date=Date(2026, 12, 31),
    )


def test_karte_bei_100_0_zeigt_hinweis_und_behaelt_52w_wert_und_rang():
    html = render_index(
        [_view({"gewicht_momentum_12_1": 1.0, "gewicht_high_52w": 0.0})],
        Date(2026, 12, 1),
    )
    # ein Hinweis je Karte (zwei Titel im Test-Ranking)
    assert html.count(HINWEIS) == 2
    assert 'class="card-ft card-ft--nur-info"' in html
    assert "52W-Hoch-Nähe" in html
    assert "Rang 52W-Hoch-Nähe" in html
    assert "98,1" in html  # 52W-Wert von AAA bleibt sichtbar


def test_karte_bei_50_50_ohne_hinweis_und_exakt_wie_ohne_feld():
    mit = render_index(
        [_view({"gewicht_momentum_12_1": 0.5, "gewicht_high_52w": 0.5})],
        Date(2026, 12, 1),
    )
    ohne_feld = render_index([_view(None)], Date(2026, 12, 1))
    leer = render_index([_view({})], Date(2026, 12, 1))
    assert HINWEIS not in mit
    assert HINWEIS not in ohne_feld
    assert HINWEIS not in leer
    # 0.5/0.5 sieht exakt aus wie heute (= ohne Gewichtsangabe)
    assert mit == ohne_feld == leer


def test_karte_liest_die_gewichte_aus_der_ranking_datei_nicht_aus_config():
    """Ein Oktober-Ranking (0.5/0.5) bleibt hinweisfrei, auch wenn der
    Fahrplan fuer spaetere Monate 100/0 sagt -- und ein 100/0-Ranking zeigt
    den Hinweis unabhaengig vom Monat."""
    okt = _view({"gewicht_momentum_12_1": 0.5, "gewicht_high_52w": 0.5})
    okt.ranking["ranking_monat"] = "2026-10"
    assert HINWEIS not in render_index([okt], Date(2026, 11, 16))
    jul_100 = _view({"gewicht_momentum_12_1": 1.0, "gewicht_high_52w": 0.0})
    assert HINWEIS in render_index([jul_100], Date(2026, 8, 3))
