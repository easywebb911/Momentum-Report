"""Die drei Karten-Ergaenzungen: Chart-Verweis, Beschreibung, Live-Anker.

Alles ADDITIV. Ohne Meta-Datei und ohne erreichbaren Kurs-Dienst sieht die
Karte aus wie vorher — das ist hier die tragende Aussage, nicht ein
Nebeneffekt.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.meta import dump_meta, load_meta, meta_pfad
from momentum.render import MarketView, chart_url, render_index

sys.path.insert(0, str(Path("tools").resolve()))

Date = _dt.date


def _ranking(ticker: str = "AAA", markt: str = "us") -> dict:
    return {
        "schema": 1,
        "markt": markt,
        "markt_name": "USA",
        "waehrung": "USD",
        "ranking_monat": "2026-07",
        "stichtag": "2026-07-31",
        "universum": {"bezeichnung": "S&P 500", "herkunft": "T", "stand": "2026-07-31",
                      "titel_gesamt": 500},
        "methode": {},
        "trend_ampel": {"index_ticker": "^SP500TR", "index_name": "S&P 500",
                        "rendite_12m": 0.152, "warnung": False},
        "abdeckung": {"universum": 500, "mit_kursen": 498, "nach_handelbarkeit": 470,
                      "ohne_handelbarkeit": 28, "ohne_ausreichende_historie": [],
                      "bewertet": 469},
        "rangliste": [{
            "ticker": ticker, "name": "Aus dem Ranking AG", "score": 97.5,
            "momentum_12_1": 0.42, "high_52w": 0.98, "kurs_stichtag": 123.45,
            "rank_12_1": 3, "rank_52w": 12, "rang": 1,
        }],
        "top": [ticker],
    }


def _view(ticker="AAA", markt="us", meta=None) -> MarketView:
    return MarketView(
        market=MARKETS_BY_KEY[markt],
        ranking=_ranking(ticker, markt),
        price_asof=Date(2026, 8, 3),
        prices={ticker: 130.5},
        next_ranking_date=Date(2026, 8, 31),
        meta=meta or {},
    )


# ------------------------------------------------------- 1. Chart-Verweis


@pytest.mark.parametrize(
    "ticker,soll",
    [
        ("AAPL", "https://stockanalysis.com/stocks/AAPL/"),
        ("BRK-B", "https://stockanalysis.com/stocks/BRK-B/"),
        ("SAP.DE", "https://stockanalysis.com/quote/etr/SAP"),
        ("VOW3.DE", "https://stockanalysis.com/quote/etr/VOW3"),
        ("1COV.DE", "https://stockanalysis.com/quote/etr/1COV"),
    ],
)
def test_chart_adresse_folgt_dem_muster(ticker, soll):
    assert chart_url(ticker) == soll


def test_nur_die_de_endung_wird_abgeschnitten():
    """.DE ist die einzige Endung im Universum — nichts anderes wird gekuerzt."""
    assert chart_url("DELL") == "https://stockanalysis.com/stocks/DELL/"
    assert chart_url("DE") == "https://stockanalysis.com/stocks/DE/"


def test_der_chart_badge_oeffnet_sicher_in_neuem_tab():
    html = render_index([_view()], Date(2026, 8, 3))
    assert 'class="chart-badge"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html, "ohne noopener kein neuer Tab"
    assert "stockanalysis.com/stocks/AAA/" in html
    assert 'aria-label="Chart für AAA' in html


# ------------------------------------------------ 2. Beschreibung (Meta)


def test_beschreibung_kommt_aus_der_meta_datei():
    html = render_index(
        [_view(meta={"AAA": {"name": "Arthur J. Gallagher & Co.", "sektor": "Financials"}})],
        Date(2026, 8, 3),
    )
    assert "Arthur J. Gallagher &amp; Co." in html
    assert '<span class="csektor">Financials</span>' in html
    assert "Aus dem Ranking AG" not in html, "die Meta-Angabe hat Vorrang"


def test_fehlender_meta_eintrag_zeigt_einen_gedankenstrich():
    """NIE ein Fehler — eine fehlende Branche haelt kein Ranking auf."""
    html = render_index([_view(meta={})], Date(2026, 8, 3))
    assert '<span class="csektor">—</span>' in html
    # Der Name faellt auf den aus dem Ranking zurueck, statt zu verschwinden.
    assert "Aus dem Ranking AG" in html


def test_halber_meta_eintrag_faellt_feldweise_zurueck():
    html = render_index(
        [_view(meta={"AAA": {"name": "", "sektor": "Health Care"}})], Date(2026, 8, 3)
    )
    assert "Aus dem Ranking AG" in html
    assert "Health Care" in html


def test_meta_datei_wird_fail_soft_gelesen(tmp_path):
    assert load_meta("us", tmp_path) == {}, "fehlende Datei -> leer, keine Ausnahme"

    pfad = meta_pfad("us", tmp_path)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    for muell in ("", "kein json", "[]", '"text"', "null", '{"AAA": 5}'):
        pfad.write_text(muell, encoding="utf-8")
        assert load_meta("us", tmp_path) == {} or "AAA" not in load_meta("us", tmp_path), muell

    pfad.write_text(
        json.dumps({"AAA": {"name": "A AG", "sektor": "IT"}, "BBB": {"name": "B AG"}}),
        encoding="utf-8",
    )
    gelesen = load_meta("us", tmp_path)
    assert gelesen["AAA"] == {"name": "A AG", "sektor": "IT"}
    assert gelesen["BBB"] == {"name": "B AG", "sektor": ""}


def test_die_meta_datei_ist_deterministisch():
    eintraege = {"BBB": {"name": "B", "sektor": "Y"}, "AAA": {"name": "A", "sektor": "X"}}
    a = dump_meta(eintraege)
    b = dump_meta(dict(reversed(list(eintraege.items()))))
    assert a == b, "Reihenfolge darf die Datei nicht veraendern"
    assert a.index('"AAA"') < a.index('"BBB"'), "sortiert"
    assert "2026" not in a, "kein Zeitstempel in der Datei"


# ---------------------------------------------- Meta aus beiden Quellen


ISHARES_CSV = (
    "﻿" + 'Fondsposition per,"31.Juli2026"\n \n'
    "Emittententicker,Name,Sektor,Anlageklasse,Marktwert,Gewichtung (%),"
    "Nominalwert,Nominale,Kurs,Standort,Börse,Marktwährung\n"
    "SAP,SAP SE,Informationstechnologie,Aktien,1.0,1.0,1,1,1.0,Deutschland,Xetra,EUR\n"
    "RHM,RHEINMETALL AG,Industrie,Aktien,1.0,1.0,1,1,1.0,Deutschland,Xetra,EUR\n"
)

WIKIPEDIA_HTML = """
<table class="wikitable">
  <tr><th>Symbol</th><th>Security</th><th>GICS Sector</th></tr>
  <tr><td>AJG</td><td>Arthur J. Gallagher &amp; Co.</td><td>Financials</td></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td><td>Information Technology</td></tr>
</table>
"""


def test_sektor_kommt_aus_der_ishares_bestandsliste():
    import build_universe as bu

    befund = bu.parse_ishares_holdings(
        ISHARES_CSV, "DAX", heute=Date(2026, 8, 3), erwartete_anzahl=(1, 10)
    )
    nach_ticker = {k.ticker: k for k in befund.kandidaten}
    assert nach_ticker["SAP.DE"].sektor == "Informationstechnologie"
    assert nach_ticker["RHM.DE"].sektor == "Industrie"


def test_sektor_kommt_aus_der_wikipedia_tabelle():
    import build_universe as bu

    befund = bu.parse_us(WIKIPEDIA_HTML)
    nach_ticker = {k.ticker: k for k in befund.kandidaten}
    assert nach_ticker["AJG"].sektor == "Financials"
    assert nach_ticker["AJG"].name == "Arthur J. Gallagher & Co."
    assert nach_ticker["AAPL"].sektor == "Information Technology"


def test_quelle_ohne_sektorspalte_laesst_das_feld_leer():
    """Keine Spalte -> leeres Feld -> auf der Karte ein Gedankenstrich."""
    import build_universe as bu

    ohne = """<table><tr><th>Symbol</th><th>Security</th></tr>
    <tr><td>AAPL</td><td>Apple Inc.</td></tr></table>"""
    befund = bu.parse_us(ohne)
    assert befund.kandidaten[0].sektor == ""
    assert bu.meta_aus_kandidaten(befund.kandidaten)["AAPL"]["sektor"] == ""


def test_die_vereinigung_traegt_den_sektor_weiter():
    import build_universe as bu

    a = bu.Befund(kandidaten=[bu.Kandidat("SAP.DE", "SAP SE", "DAX", sektor="IT")])
    b = bu.Befund(kandidaten=[bu.Kandidat("SAP.DE", "SAP SE", "TecDAX", sektor="IT")])
    zusammen = bu.vereinige([a, b])
    assert len(zusammen.kandidaten) == 1
    assert zusammen.kandidaten[0].sektor == "IT"
    assert zusammen.kandidaten[0].herkunft == "DAX, TecDAX"


# ---------------------------------------------------- 3. Live-Kurs-Anker


def test_die_karte_traegt_die_anker_fuer_den_live_kurs():
    html = render_index([_view()], Date(2026, 8, 3))
    assert 'data-quote="AAA"' in html
    assert 'data-quote-change="AAA"' in html
    assert 'data-live="us"' in html
    assert 'class="live" data-live="us" hidden' in html, "ohne JS bleibt sie unsichtbar"


def test_live_beruehrt_score_und_rang_nicht():
    """Klare Trennung: Live ersetzt nur die Tages-Kurszeile.

    Score, Momentum, 52W-Naehe und die Teil-Raenge tragen KEINEN
    data-quote-Anker — die Browser-Schicht kann sie gar nicht anfassen.
    """
    import re

    html = render_index([_view()], Date(2026, 8, 3))
    for block in re.findall(r"<span[^>]*data-quote=[^>]*>.*?</span>", html, flags=re.S):
        # Der einzige beschriftete Anker ist die Kurs-Kachel.
        assert "Score" not in block and "Momentum" not in block

    # Gegenprobe: die Score-Anzeige liegt ausserhalb jedes Ankers.
    score = re.search(r'<span class="score-val">([^<]+)</span>', html)
    assert score, "Score-Anzeige fehlt"
    assert "data-quote" not in html[max(0, score.start() - 200):score.start()]


def test_der_kurs_der_kachel_ist_der_lauf_kurs():
    """Ohne JS zeigt die Kachel weiter den Kurs aus dem Lauf."""
    from momentum.render import NBSP

    html = render_index([_view()], Date(2026, 8, 3))
    assert f'data-quote="AAA">${NBSP}130,50<' in html
