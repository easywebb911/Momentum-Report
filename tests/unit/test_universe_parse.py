"""Wikipedia-Parse — mit eingespielten Beispiel-Tabellen, OHNE Netz.

Alle Tabellen hier sind von Hand geschrieben und bilden genau die Faelle ab,
an denen so ein Parser scheitert:
  * Klassen-Ticker (BRK.B -> BRK-B)
  * Xetra-Kuerzel mit fuehrender Ziffer (1COV) und Vorzugsgattung (VOW3)
  * Symbol-Spalte fehlt komplett -> ISIN-Reserve, namentlich protokolliert
  * ISIN-Reserve findet nichts -> Titel bleibt ungeloest, wird genannt
  * Doppelmitglied in zwei Indizes -> genau EIN Eintrag
  * Nebentabelle mit gleichen Spaltennamen -> die groessere gewinnt
  * Spalten fehlen ganz -> lauter Abbruch, es wird nichts geschrieben
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import build_universe as bu  # noqa: E402

# --------------------------------------------------------------------------
# Beispiel-Tabellen
# --------------------------------------------------------------------------

SP500_HTML = """
<h2>Selected changes</h2>
<table class="wikitable">
  <tr><th>Symbol</th><th>Security</th><th>Date</th></tr>
  <tr><td>XYZ</td><td>Ehemalige AG</td><td>2026-01-02</td></tr>
</table>
<h2>Components</h2>
<table class="wikitable" id="constituents">
  <tr><th>Symbol</th><th>Security</th><th>GICS Sector</th></tr>
  <tr><td>AAPL</td><td>Apple Inc.</td><td>Information Technology</td></tr>
  <tr><td>BRK.B</td><td>Berkshire Hathaway</td><td>Financials</td></tr>
  <tr><td>BF.B</td><td>Brown-Forman</td><td>Consumer Staples</td></tr>
  <tr><td>MSFT</td><td>Microsoft</td><td>Information Technology</td></tr>
</table>
"""

SP500_OHNE_SYMBOL_HTML = """
<table class="wikitable">
  <tr><th>Security</th><th>GICS Sector</th></tr>
  <tr><td>Apple Inc.</td><td>Information Technology</td></tr>
</table>
"""

DAX_HTML = """
<h2>Components</h2>
<table class="wikitable">
  <tr><th>Company</th><th>Prime Standard Sector</th><th>Ticker symbol</th></tr>
  <tr><td>Aixtron</td><td>Technology</td><td>AIXA</td></tr>
  <tr><td>Volkswagen Group</td><td>Automotive</td><td>VOW3</td></tr>
  <tr><td>Covestro</td><td>Chemicals</td><td>1COV</td></tr>
  <tr><td>SAP</td><td>Software</td><td>SAP</td></tr>
  <tr><td>Henkel</td><td>Consumer</td><td>HEN3</td></tr>
</table>
"""

MDAX_HTML = """
<table class="wikitable">
  <tr><th>Company</th><th>Sector</th><th>Ticker</th></tr>
  <tr><td>Aroundtown</td><td>Real Estate</td><td>AT1</td></tr>
  <tr><td>Fuchs</td><td>Chemicals</td><td>FPE3</td></tr>
</table>
"""

# TecDAX teilt sich Mitglieder mit DAX (Aixtron, SAP) -- Doppelmitglieder.
TECDAX_HTML = """
<table class="wikitable">
  <tr><th>Company</th><th>Sector</th><th>Ticker symbol</th></tr>
  <tr><td>Aixtron</td><td>Technology</td><td>AIXA</td></tr>
  <tr><td>SAP</td><td>Software</td><td>SAP</td></tr>
  <tr><td>Nagarro</td><td>IT Services</td><td>NA9</td></tr>
</table>
"""

# Aufbau ohne Symbol-Spalte: nur Name und ISIN -> die Reserve muss greifen.
DAX_OHNE_SYMBOL_HTML = """
<table class="wikitable">
  <tr><th>Company</th><th>Sector</th><th>ISIN</th></tr>
  <tr><td>Siemens</td><td>Industrial</td><td>DE0007236101</td></tr>
  <tr><td>Allianz</td><td>Insurance</td><td>DE0008404005</td></tr>
</table>
"""

DAX_UNBRAUCHBAR_HTML = """
<table class="wikitable">
  <tr><th>Sector</th><th>Weighting</th></tr>
  <tr><td>Technology</td><td>12,3 %</td></tr>
</table>
"""


# --------------------------------------------------------------------------
# Xetra-Kuerzel -> Yahoo-Ticker
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "eingabe,erwartet",
    [
        ("AIXA", "AIXA.DE"),
        ("AT1", "AT1.DE"),
        ("VOW3", "VOW3.DE"),      # Vorzugsaktie: Gattung steckt im Kuerzel
        ("HEN3", "HEN3.DE"),      # Henkel Vz.
        ("SRT3", "SRT3.DE"),      # Sartorius Vz.
        ("1COV", "1COV.DE"),      # fuehrende Ziffer
        ("ETR: AIXA", "AIXA.DE"), # Praefix der Quelle
        ("XETRA SAP", "SAP.DE"),
        ("sap", "SAP.DE"),
        ("—", None),
        ("", None),
        ("n/a", None),
        ("VIELZULANGESKUERZEL", None),
    ],
)
def test_xetra_kuerzel_werden_zu_yahoo_tickern(eingabe, erwartet):
    assert bu.xetra_zu_yahoo(eingabe) == erwartet


def test_vorzugsaktien_brauchen_keine_sonderbehandlung():
    """Die Annahme ausdruecklich festgehalten: das Kuerzel traegt die Gattung."""
    stamm = bu.xetra_zu_yahoo("VOW")
    vorzug = bu.xetra_zu_yahoo("VOW3")
    assert stamm == "VOW.DE" and vorzug == "VOW3.DE"
    assert stamm != vorzug


# --------------------------------------------------------------------------
# USA
# --------------------------------------------------------------------------


def test_sp500_parse_trifft_die_richtige_tabelle_und_uebersetzt_klassenticker():
    befund = bu.parse_us(SP500_HTML)
    ticker = [k.ticker for k in befund.kandidaten]
    assert ticker == ["AAPL", "BRK-B", "BF-B", "MSFT"]
    assert "XYZ" not in ticker, "die kleine Nebentabelle darf nicht gewinnen"
    assert befund.kandidaten[1].name == "Berkshire Hathaway"


def test_sp500_ohne_symbolspalte_bricht_laut_ab():
    with pytest.raises(SystemExit, match="NICHTS geschrieben"):
        bu.parse_us(SP500_OHNE_SYMBOL_HTML)


# --------------------------------------------------------------------------
# Deutschland
# --------------------------------------------------------------------------


def test_dax_parse_liest_die_symbolspalte():
    befund = bu.parse_de_index(DAX_HTML, "DAX")
    assert [k.ticker for k in befund.kandidaten] == [
        "AIXA.DE",
        "VOW3.DE",
        "1COV.DE",
        "SAP.DE",
        "HEN3.DE",
    ]
    assert befund.ungeloest == []
    assert befund.ueber_reserve == []
    assert all(k.herkunft == "DAX" for k in befund.kandidaten)


def test_fehlende_symbolspalte_greift_auf_die_isin_reserve_zurueck():
    aufgeloest = {"DE0007236101": "SIE.DE", "DE0008404005": "ALV.DE"}
    befund = bu.parse_de_index(
        DAX_OHNE_SYMBOL_HTML, "DAX", isin_resolver=aufgeloest.get
    )
    assert [k.ticker for k in befund.kandidaten] == ["SIE.DE", "ALV.DE"]
    assert all(k.ueber_reserve for k in befund.kandidaten)
    # JEDE Reserve-Aufloesung wird namentlich protokolliert
    assert len(befund.ueber_reserve) == 2
    assert any("Siemens" in z and "DE0007236101" in z and "SIE.DE" in z for z in befund.ueber_reserve)


def test_isin_reserve_ohne_treffer_laesst_den_titel_ungeloest():
    befund = bu.parse_de_index(
        DAX_OHNE_SYMBOL_HTML, "DAX", isin_resolver=lambda isin: None
    )
    assert befund.kandidaten == []
    assert len(befund.ungeloest) == 2
    assert any("Siemens" in z for z in befund.ungeloest)


def test_ohne_reserve_bleibt_ein_titel_ohne_symbol_ungeloest():
    befund = bu.parse_de_index(DAX_OHNE_SYMBOL_HTML, "DAX", isin_resolver=None)
    assert befund.kandidaten == []
    assert len(befund.ungeloest) == 2


def test_unbrauchbare_tabelle_bricht_laut_ab():
    with pytest.raises(SystemExit, match="NICHTS geschrieben"):
        bu.parse_de_index(DAX_UNBRAUCHBAR_HTML, "DAX")


# --------------------------------------------------------------------------
# HDAX: Vereinigung mit Doppelmitgliedern
# --------------------------------------------------------------------------


def test_doppelmitglieder_erscheinen_genau_einmal():
    hdax = bu.vereinige(
        [
            bu.parse_de_index(DAX_HTML, "DAX"),
            bu.parse_de_index(MDAX_HTML, "MDAX"),
            bu.parse_de_index(TECDAX_HTML, "TecDAX"),
        ]
    )
    ticker = [k.ticker for k in hdax.kandidaten]
    # 5 (DAX) + 2 (MDAX) + 3 (TecDAX) = 10 Eintraege, davon 2 doppelt -> 8
    assert len(ticker) == 8
    assert len(set(ticker)) == len(ticker), "kein Ticker darf doppelt auftauchen"
    assert ticker.count("AIXA.DE") == 1
    assert ticker.count("SAP.DE") == 1


def test_doppelmitglied_behaelt_beide_herkuenfte():
    hdax = bu.vereinige(
        [
            bu.parse_de_index(DAX_HTML, "DAX"),
            bu.parse_de_index(TECDAX_HTML, "TecDAX"),
        ]
    )
    nach_ticker = {k.ticker: k for k in hdax.kandidaten}
    assert nach_ticker["AIXA.DE"].herkunft == "DAX, TecDAX"
    assert nach_ticker["HEN3.DE"].herkunft == "DAX"
    assert nach_ticker["NA9.DE"].herkunft == "TecDAX"


def test_vereinigung_ist_nach_ticker_sortiert():
    hdax = bu.vereinige([bu.parse_de_index(DAX_HTML, "DAX")])
    ticker = [k.ticker for k in hdax.kandidaten]
    assert ticker == sorted(ticker)


# --------------------------------------------------------------------------
# Determinismus und Dateiform
# --------------------------------------------------------------------------


def _kandidaten():
    return [
        bu.Kandidat("SAP.DE", "SAP", "DAX"),
        bu.Kandidat("AIXA.DE", "Aixtron", "DAX, TecDAX"),
        bu.Kandidat("1COV.DE", "Covestro", "DAX"),
    ]


def test_gleicher_input_gleiche_datei_unabhaengig_von_der_reihenfolge():
    a = bu.rendere_universum("HDAX", "Quelle", "2026-08-02", "lauf-1", _kandidaten())
    b = bu.rendere_universum(
        "HDAX", "Quelle", "2026-08-02", "lauf-1", list(reversed(_kandidaten()))
    )
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_datei_traegt_den_geprueften_status():
    text = bu.rendere_universum("HDAX", "Quelle", "2026-08-02", "lauf-1", _kandidaten())
    assert "# STATUS: VERIFIED" in text
    assert "# Herkunft: Quelle" in text
    assert "# Stand: 2026-08-02" in text


def test_erzeugte_datei_wird_vom_werkzeug_akzeptiert(tmp_path):
    """Gegenprobe: was der Bootstrap schreibt, muss der Lauf lesen koennen."""
    from momentum.universe import load_universe

    pfad = tmp_path / "u.txt"
    pfad.write_text(
        bu.rendere_universum("HDAX", "Quelle", "2026-08-02", "lauf-1", _kandidaten()),
        encoding="utf-8",
    )
    universum = load_universe(pfad)
    assert universum.status == "VERIFIED"
    assert universum.tickers == ("1COV.DE", "AIXA.DE", "SAP.DE")
    assert universum.name_of("AIXA.DE") == "Aixtron"


# --------------------------------------------------------------------------
# Plausibilitaets-Schranken
# --------------------------------------------------------------------------


def test_plausibilitaets_schranken_stehen_wie_beauftragt():
    assert bu.ERWARTET["us"] == (495, 510)
    assert bu.ERWARTET["de"] == (110, 125)


def test_quellen_sind_die_englische_wikipedia():
    assert "en.wikipedia.org" in bu.QUELLE_US
    assert set(bu.QUELLEN_DE) == {"DAX", "MDAX", "TecDAX"}
    for url in bu.QUELLEN_DE.values():
        assert "en.wikipedia.org" in url, url
