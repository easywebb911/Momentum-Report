"""Sektor-Haeufungs-Hinweis: reine Render-Zeit-Berechnung aus Top-5 +
Meta-Daten, kein neues Schema, keine Persistenz (siehe render.py,
_sektor_konzentration/_sektor_hinweis).

Nachweise wie gefordert: 5/5- und 3/5-Fund, 2/5-Nicht-Fund, fehlender
Sektor, weniger als TOP_N Titel, Determinismus -- UND die Ziel-Mechanik
an den ECHTEN Rankings (US 2026-09 muss den Hinweis zeigen, DE 2026-09
nicht), nicht nur an synthetischen Faellen.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from momentum.config import MARKETS_BY_KEY, TOP_N
from momentum.render import (
    SEKTOR_KONZENTRATION_SCHWELLE,
    MarketView,
    _sektor_hinweis,
    _sektor_konzentration,
    render_index,
)

Date = _dt.date


def _reihe(ticker: str, rang: int) -> dict:
    return {
        "ticker": ticker,
        "name": f"{ticker} AG",
        "score": 100.0 - rang,
        "momentum_12_1": 0.1,
        "high_52w": 0.9,
        "kurs_stichtag": 10.0,
        "rank_12_1": rang,
        "rank_52w": rang,
        "rang": rang,
    }


def _ranking(tickers: list[str]) -> dict:
    return {
        "schema": 1,
        "markt": "us",
        "markt_name": "USA",
        "waehrung": "USD",
        "ranking_monat": "2026-07",
        "stichtag": "2026-07-31",
        "universum": {"bezeichnung": "S&P 500", "herkunft": "T", "stand": "2026-07-31",
                      "titel_gesamt": 500},
        "methode": {},
        "trend_ampel": {"index_ticker": "^SP500TR", "index_name": "S&P 500",
                        "rendite_12m": 0.1, "warnung": False},
        "abdeckung": {"universum": 500, "mit_kursen": 498, "nach_handelbarkeit": 470,
                      "ohne_handelbarkeit": 28, "ohne_ausreichende_historie": [],
                      "bewertet": 469},
        "rangliste": [_reihe(t, i + 1) for i, t in enumerate(tickers)],
        "top": tickers,
    }


def _meta(sektoren: dict[str, str]) -> dict:
    return {t: {"name": f"{t} AG", "sektor": s} for t, s in sektoren.items()}


def _view(tickers: list[str], sektoren: dict[str, str]) -> MarketView:
    return MarketView(
        market=MARKETS_BY_KEY["us"],
        ranking=_ranking(tickers),
        price_asof=Date(2026, 8, 3),
        prices={},
        next_ranking_date=Date(2026, 8, 31),
        meta=_meta(sektoren),
    )


FUENF = ["A", "B", "C", "D", "E"]


# --------------------------------------------------- _sektor_konzentration


def test_fuenf_von_fuenf_wird_erkannt():
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({t: "Information Technology" for t in FUENF})
    fund = _sektor_konzentration(rows, meta)
    assert fund == (5, "Information Technology")


def test_drei_von_fuenf_wird_erkannt():
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({
        "A": "Health Care", "B": "Health Care", "C": "Health Care",
        "D": "Energy", "E": "Consumer Discretionary",
    })
    assert _sektor_konzentration(rows, meta) == (3, "Health Care")


def test_zwei_von_fuenf_kein_fund():
    """DE lag in allen drei bisherigen Monaten bei hoechstens 2/5 -- das ist
    laut Schwelle ausdruecklich KEIN Fund."""
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({
        "A": "Finanzwesen", "B": "Finanzwesen", "C": "Materialien",
        "D": "Industrie", "E": "Versorger",
    })
    assert SEKTOR_KONZENTRATION_SCHWELLE == 3  # Pruefung setzt genau das voraus
    assert _sektor_konzentration(rows, meta) is None


def test_fehlender_sektor_eines_titels_unterdrueckt_den_hinweis():
    """Fehlt der Sektor (oder der Meta-Eintrag ueberhaupt) fuer EINEN
    Top-5-Titel, gilt die Menge als nicht vollstaendig beurteilbar -- auch
    wenn die vier bekannten Sektoren uebereinstimmen."""
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({
        "A": "Information Technology", "B": "Information Technology",
        "C": "Information Technology", "D": "Information Technology",
    })  # "E" fehlt komplett
    assert _sektor_konzentration(rows, meta) is None


def test_leerer_sektor_string_zaehlt_als_fehlend():
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({t: "Information Technology" for t in FUENF})
    meta["E"]["sektor"] = ""
    assert _sektor_konzentration(rows, meta) is None


def test_weniger_als_top_n_titel_kein_hinweis():
    vier = FUENF[:4]
    rows = [_reihe(t, i + 1) for i, t in enumerate(vier)]
    meta = _meta({t: "Information Technology" for t in vier})
    assert len(rows) < TOP_N
    assert _sektor_konzentration(rows, meta) is None


def test_fehlende_meta_datei_insgesamt_kein_absturz():
    """Fail-soft wie meta.py: eine komplett leere Meta-Zuordnung (Datei
    fehlt/unlesbar) darf nie eine Ausnahme werfen, nur keinen Fund liefern."""
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    assert _sektor_konzentration(rows, {}) is None


def test_determinismus_wiederholter_aufruf_liefert_identisches_ergebnis():
    rows = [_reihe(t, i + 1) for i, t in enumerate(FUENF)]
    meta = _meta({t: "Information Technology" for t in FUENF})
    assert _sektor_konzentration(rows, meta) == _sektor_konzentration(rows, meta)


# ------------------------------------------------------------ _sektor_hinweis


def test_text_wortlaut_und_platzhalter():
    view = _view(FUENF, {t: "Information Technology" for t in FUENF})
    html = _sektor_hinweis(view)
    assert '<p class="sektor-hinweis">' in html
    assert (
        "Sektor-Häufung: 5 von 5 Top-5-Werten liegen im Sektor "
        "Information Technology." in html
    )
    assert "Titel im selben Sektor können sich ähnlich bewegen." in html
    assert (
        "Das ist eine Beobachtung über das Ranking, kein Risikomaß und "
        "keine Handlungsempfehlung." in html
    )


def test_kein_fund_liefert_leeren_string():
    view = _view(FUENF, {
        "A": "Finanzwesen", "B": "Finanzwesen", "C": "Materialien",
        "D": "Industrie", "E": "Versorger",
    })
    assert _sektor_hinweis(view) == ""


# --------------------------------------------------------------- render_index


def test_render_index_zeigt_hinweis_bei_konzentration():
    view = _view(FUENF, {t: "Information Technology" for t in FUENF})
    html = render_index([view], Date(2026, 8, 3))
    assert "sektor-hinweis" in html
    assert "Sektor-Häufung" in html


def test_render_index_zeigt_keinen_hinweis_ohne_konzentration():
    view = _view(FUENF, {
        "A": "Finanzwesen", "B": "Finanzwesen", "C": "Materialien",
        "D": "Industrie", "E": "Versorger",
    })
    html = render_index([view], Date(2026, 8, 3))
    assert "sektor-hinweis" not in html
    assert "Sektor-Häufung" not in html


# ------------------------------------------------ Ziel-Mechanik an echten Daten


def _echte_view(markt_key: str, monat: str) -> MarketView:
    ranking = json.loads(
        Path(f"data/rankings/{markt_key}_{monat}.json").read_text(encoding="utf-8")
    )
    meta = json.loads(
        Path(f"universe/ticker_meta_{markt_key}.json").read_text(encoding="utf-8")
    )
    return MarketView(
        market=MARKETS_BY_KEY[markt_key],
        ranking=ranking,
        price_asof=Date.fromisoformat(ranking["stichtag"]),
        prices={},
        next_ranking_date=Date(2026, 10, 30),
        meta=meta,
    )


def test_echtes_us_september_ranking_zeigt_den_hinweis():
    """Ziel-Mechanik, nicht nur 'nichts kaputt': die echte US-September-
    Rangliste (5 von 5 Information Technology laut Diagnose) muss den
    Hinweis tatsaechlich zeigen."""
    view = _echte_view("us", "2026-09")
    fund = _sektor_konzentration(view.ranking["rangliste"][:TOP_N], view.meta)
    assert fund == (5, "Information Technology")
    assert "sektor-hinweis" in render_index([view], Date(2026, 10, 1))


def test_echtes_de_september_ranking_zeigt_keinen_hinweis():
    """Gegenprobe: dieselbe echte Datenlage fuer DE (hoechstens 2 von 5 im
    selben Sektor laut Diagnose) darf KEINEN Hinweis zeigen."""
    view = _echte_view("de", "2026-09")
    fund = _sektor_konzentration(view.ranking["rangliste"][:TOP_N], view.meta)
    assert fund is None
    assert "sektor-hinweis" not in render_index([view], Date(2026, 10, 1))


# --------------------------------------------------- Byte-Identitaet (Beleg)


def test_hinweis_beruehrt_kein_anderes_feld_der_karten():
    """Das Marktabschnitt-Markup darf sich ausser dem neuen Hinweis-Element
    nicht aendern -- Stichprobe auf bekannte, unveraenderte Bestandteile."""
    view = _view(FUENF, {t: "Information Technology" for t in FUENF})
    html = render_index([view], Date(2026, 8, 3))
    for ticker in FUENF:
        assert f'<span class="ticker">{ticker}</span>' in html
    assert html.count('<article class="card card--us">') == TOP_N
