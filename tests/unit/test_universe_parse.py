"""Universums-Quellen — mit eingespielten Beispieldateien, OHNE Netz.

Zwei Quellen, zwei Testblöcke:
  * USA: Wikipedia-Listenartikel (HTML-Tabelle)
  * DE:  taegliche Bestandslisten der iShares-Index-ETFs (CSV)

Die CSV-Beispiele bilden genau die Faelle ab, an denen so ein Parser
scheitert: deutsche und englische Fassung, Vorspann-Zeilen, Bargeld- und
Derivate-Zeilen, fehlender Ticker mit ISIN-Reserve, falscher Fonds hinter
der URL, veralteter Bestand, fehlender Stichtag, HTML statt CSV.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import build_universe as bu  # noqa: E402

Date = _dt.date
HEUTE = Date(2026, 8, 3)  # Montag

# --------------------------------------------------------------------------
# USA: Wikipedia
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


def test_sp500_parse_trifft_die_richtige_tabelle_und_uebersetzt_klassenticker():
    befund = bu.parse_us(SP500_HTML)
    ticker = [k.ticker for k in befund.kandidaten]
    assert ticker == ["AAPL", "BRK-B", "BF-B", "MSFT"]
    assert "XYZ" not in ticker, "die kleine Nebentabelle darf nicht gewinnen"
    assert befund.kandidaten[1].name == "Berkshire Hathaway"


def test_sp500_ohne_symbolspalte_bricht_laut_ab():
    with pytest.raises(bu.QuelleUnbrauchbar, match="NICHTS geschrieben"):
        bu.parse_us(SP500_OHNE_SYMBOL_HTML)


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
    assert bu.xetra_zu_yahoo("VOW") == "VOW.DE"
    assert bu.xetra_zu_yahoo("VOW3") == "VOW3.DE"


# --------------------------------------------------------------------------
# DE: iShares-Bestandslisten
# --------------------------------------------------------------------------

# Deutsche Fassung: Semikolon, Dezimal-Komma, Vorspann, Bargeld-Zeile.
DAX_CSV_DE = """\
"iShares Core DAX UCITS ETF (DE)";;;;;;;
"Fondsbestände Stand";"31.Jul.2026";;;;;;
"Basiswährung";"EUR";;;;;;
;;;;;;;
"Emittententicker";"Name";"Sektor";"Anlageklasse";"Marktwert";"Gewichtung (%)";"ISIN";"Börse"
"SAP";"SAP SE";"Informationstechnologie";"Aktien";"1.234.567,89";"10,52";"DE0007164600";"Xetra"
"AIXA";"AIXTRON SE";"Informationstechnologie";"Aktien";"123.456,78";"1,05";"DE000A0WMPJ6";"Xetra"
"VOW3";"VOLKSWAGEN AG VZ";"Zyklische Konsumgüter";"Aktien";"234.567,89";"2,01";"DE0007664039";"Xetra"
"1COV";"COVESTRO AG";"Grundstoffe";"Aktien";"45.678,90";"0,39";"DE0006062144";"Xetra"
"—";"EUR CASH";"Bargeld";"Bargeld und/oder Derivate";"1.000,00";"0,01";"-";"-"
"—";"DAX INDEX FUTURE SEP 26";"Derivate";"Futures";"5.000,00";"0,04";"-";"EUREX"
"""

# Englische Fassung: Komma, Dezimalpunkt, andere Spaltennamen.
MDAX_CSV_EN = """\
iShares MDAX UCITS ETF (DE)
Fund Holdings as of,"Jul 31, 2026"
Inception Date,"Feb 12, 2001"

Ticker,Name,Sector,Asset Class,Market Value,Weight (%),ISIN,Exchange
AT1,AROUNDTOWN SA,Real Estate,Equity,"1,234,567.89",2.10,LU1673108939,Xetra
FPE3,FUCHS SE PREF,Materials,Equity,"234,567.89",1.02,DE000A3E5D64,Xetra
RHM,RHEINMETALL AG,Industrials,Equity,"456,789.01",3.44,DE0007030009,Xetra
-,EUR CASH,Cash,Cash and/or Derivatives,"2,000.00",0.02,-,-
"""

# TecDAX: teilt sich Mitglieder mit DAX (SAP, AIXA) -> Doppelmitglieder.
TECDAX_CSV_DE = """\
"iShares TecDAX UCITS ETF (DE)";;;;;;;
"Fondsbestände Stand";"31.Jul.2026";;;;;;
;;;;;;;
"Emittententicker";"Name";"Sektor";"Anlageklasse";"Marktwert";"Gewichtung (%)";"ISIN";"Börse"
"SAP";"SAP SE";"Informationstechnologie";"Aktien";"1.000.000,00";"9,80";"DE0007164600";"Xetra"
"AIXA";"AIXTRON SE";"Informationstechnologie";"Aktien";"100.000,00";"0,98";"DE000A0WMPJ6";"Xetra"
"NA9";"NAGARRO SE";"Informationstechnologie";"Aktien";"50.000,00";"0,49";"DE000A3H2200";"Xetra"
"""

# Aktien-Zeile ohne Ticker, aber mit ISIN -> die Reserve muss greifen.
DAX_CSV_OHNE_TICKER = """\
"iShares Core DAX UCITS ETF (DE)";;;;;;;
"Fondsbestände Stand";"31.Jul.2026";;;;;;
;;;;;;;
"Emittententicker";"Name";"Sektor";"Anlageklasse";"Marktwert";"Gewichtung (%)";"ISIN";"Börse"
"SAP";"SAP SE";"Informationstechnologie";"Aktien";"1.000,00";"9,80";"DE0007164600";"Xetra"
"-";"SIEMENS AG";"Industrie";"Aktien";"2.000,00";"8,10";"DE0007236101";"Xetra"
"""

HTML_STATT_CSV = """<!DOCTYPE html>
<html><head><title>iShares</title></head><body><p>Cookie-Hinweis</p></body></html>
"""


def _de_lade(inhalt, index="DAX", heute=HEUTE, **kw):
    return bu.parse_ishares_holdings(inhalt, index, heute=heute, **kw)


# ------------------------------------------------------- Grundfunktion


def test_deutsche_fassung_wird_gelesen():
    befund = _de_lade(DAX_CSV_DE)
    assert [k.ticker for k in befund.kandidaten] == [
        "SAP.DE",
        "AIXA.DE",
        "VOW3.DE",
        "1COV.DE",
    ]
    assert befund.fonds_name == "iShares Core DAX UCITS ETF (DE)"
    assert befund.bestand_stand == Date(2026, 7, 31)
    assert all(k.herkunft == "DAX" for k in befund.kandidaten)
    assert befund.ungeloest == []


def test_englische_fassung_wird_gelesen():
    befund = _de_lade(MDAX_CSV_EN, index="MDAX")
    assert [k.ticker for k in befund.kandidaten] == ["AT1.DE", "FPE3.DE", "RHM.DE"]
    assert befund.fonds_name == "iShares MDAX UCITS ETF (DE)"
    assert befund.bestand_stand == Date(2026, 7, 31)


def test_bargeld_und_derivate_fliegen_raus():
    """Nur Anlageklasse Aktie zaehlt — Cash, Futures, Geldmarkt nicht."""
    befund = _de_lade(DAX_CSV_DE)
    namen = [k.name for k in befund.kandidaten]
    assert "EUR CASH" not in namen
    assert not any("FUTURE" in n for n in namen)
    assert befund.nicht_aktien == 2

    englisch = _de_lade(MDAX_CSV_EN, index="MDAX")
    assert "EUR CASH" not in [k.name for k in englisch.kandidaten]
    assert englisch.nicht_aktien == 1


def test_vorspann_wird_uebersprungen_und_ausgewertet():
    befund = _de_lade(DAX_CSV_DE)
    # Die Vorspann-Zeilen duerfen nicht als Titel im Universum landen
    assert not any("Fondsbestände" in k.name for k in befund.kandidaten)
    assert not any("Basiswährung" in k.name for k in befund.kandidaten)
    # ... ihre Angaben aber sehr wohl ausgewertet werden
    assert befund.fonds_name.startswith("iShares")
    assert befund.bestand_stand is not None


def test_fehlender_ticker_greift_auf_die_isin_reserve_zurueck():
    befund = _de_lade(
        DAX_CSV_OHNE_TICKER, isin_resolver={"DE0007236101": "SIE.DE"}.get
    )
    assert [k.ticker for k in befund.kandidaten] == ["SAP.DE", "SIE.DE"]
    assert befund.kandidaten[1].ueber_reserve is True
    # JEDE Reserve-Aufloesung wird namentlich protokolliert
    assert len(befund.ueber_reserve) == 1
    eintrag = befund.ueber_reserve[0]
    assert "SIEMENS AG" in eintrag and "DE0007236101" in eintrag and "SIE.DE" in eintrag


def test_isin_reserve_ohne_treffer_laesst_den_titel_ungeloest():
    befund = _de_lade(DAX_CSV_OHNE_TICKER, isin_resolver=lambda isin: None)
    assert [k.ticker for k in befund.kandidaten] == ["SAP.DE"]
    assert len(befund.ungeloest) == 1
    assert "SIEMENS AG" in befund.ungeloest[0]


def test_ohne_reserve_bleibt_der_titel_ungeloest():
    befund = _de_lade(DAX_CSV_OHNE_TICKER, isin_resolver=None)
    assert [k.ticker for k in befund.kandidaten] == ["SAP.DE"]
    assert len(befund.ungeloest) == 1


# ------------------------------------------------------- Fondsname-Gatter


def test_falscher_fonds_hinter_der_url_bricht_ab():
    """Die MDAX-Datei unter der DAX-URL: muss auffallen, nicht durchrutschen."""
    with pytest.raises(bu.QuelleUnbrauchbar, match="gehoert zum MDAX"):
        _de_lade(MDAX_CSV_EN, index="DAX")


def test_tecdax_datei_unter_der_dax_url_bricht_ab():
    with pytest.raises(bu.QuelleUnbrauchbar, match="gehoert zum TecDAX"):
        _de_lade(TECDAX_CSV_DE, index="DAX")


def test_dax_datei_unter_der_mdax_url_bricht_ab():
    with pytest.raises(bu.QuelleUnbrauchbar, match="gehoert zum DAX"):
        _de_lade(DAX_CSV_DE, index="MDAX")


@pytest.mark.parametrize(
    "name,erwartet",
    [
        ("iShares Core DAX UCITS ETF (DE)", "DAX"),
        ("iShares MDAX UCITS ETF (DE)", "MDAX"),
        ("iShares TecDAX UCITS ETF (DE)", "TecDAX"),
        ("iShares TECDAX UCITS ETF", "TecDAX"),
        ("iShares STOXX Europe 600", None),
    ],
)
def test_index_erkennung_achtet_auf_wortgrenzen(name, erwartet):
    """MDAX enthaelt DAX als Zeichenfolge — das darf nicht verwechselt werden."""
    assert bu._index_im_namen(name) == erwartet


def test_ohne_erkennbaren_index_im_fondsnamen_bricht_es_ab():
    ohne = DAX_CSV_DE.replace("iShares Core DAX UCITS ETF (DE)", "iShares Irgendwas ETF")
    with pytest.raises(bu.QuelleUnbrauchbar, match="kein Index"):
        _de_lade(ohne)


# ------------------------------------------------------ Veraltungs-Gatter


def test_veralteter_bestand_bricht_ab():
    """DAS Gatter gegen den Wikipedia-Fehler: alte Liste faellt jetzt auf."""
    alt = DAX_CSV_DE.replace("31.Jul.2026", "01.Jun.2026")
    with pytest.raises(bu.QuelleUnbrauchbar, match="Handelstage alt"):
        _de_lade(alt)


def test_frischer_bestand_kommt_durch():
    frisch = DAX_CSV_DE.replace("31.Jul.2026", "31.Jul.2026")
    assert _de_lade(frisch, heute=Date(2026, 8, 3)).bestand_stand == Date(2026, 7, 31)


def test_genau_an_der_grenze():
    """10 Handelstage sind erlaubt, 11 nicht."""
    stand = Date(2026, 7, 20)   # Montag
    assert bu.handelstage_zwischen(stand, Date(2026, 8, 3)) == 10
    bu.pruefe_aktualitaet(stand, Date(2026, 8, 3), "Test")
    with pytest.raises(bu.QuelleUnbrauchbar, match="Handelstage alt"):
        bu.pruefe_aktualitaet(stand, Date(2026, 8, 4), "Test")


def test_fehlender_stichtag_bricht_ab():
    """Ohne Stichtag laesst sich Veraltung nicht ausschliessen — also Abbruch."""
    ohne = DAX_CSV_DE.replace('"Fondsbestände Stand";"31.Jul.2026";;;;;;\n', "")
    with pytest.raises(bu.QuelleUnbrauchbar, match="kein lesbarer Bestands-Stichtag"):
        _de_lade(ohne)


@pytest.mark.parametrize(
    "text,erwartet",
    [
        ("Fondsbestände Stand;31.Jul.2026", Date(2026, 7, 31)),
        ('Fund Holdings as of,"Jul 31, 2026"', Date(2026, 7, 31)),
        ("Stand: 31.07.2026", Date(2026, 7, 31)),
        ("as of 2026-07-31", Date(2026, 7, 31)),
        ("Stand: 1. Dezember 2026", Date(2026, 12, 1)),
        ("Basiswährung;EUR", None),
    ],
)
def test_datumsformate(text, erwartet):
    assert bu._datum_aus_text(text) == erwartet


def test_wochenenden_zaehlen_nicht_als_handelstage():
    # Freitag -> Montag ist EIN Handelstag, nicht drei Kalendertage
    assert bu.handelstage_zwischen(Date(2026, 7, 31), Date(2026, 8, 3)) == 1
    assert bu.handelstage_zwischen(Date(2026, 8, 3), Date(2026, 8, 3)) == 0


# --------------------------------------------------- Format-Aenderungen


def test_html_statt_csv_bricht_laut_ab():
    """Cookie-Seite oder Fehlerseite statt Datei: muss knallen."""
    with pytest.raises(bu.QuelleUnbrauchbar, match="keine Kopfzeile"):
        _de_lade(HTML_STATT_CSV)


def test_umbenannte_spalten_brechen_ab():
    """Benennt BlackRock die Spalten um, faellt das sofort auf."""
    umbenannt = DAX_CSV_DE.replace('"Emittententicker";"Name"', '"Kuerzel";"Titel"')
    with pytest.raises(bu.QuelleUnbrauchbar, match="keine Kopfzeile"):
        _de_lade(umbenannt)


def test_leere_bestandsliste_bricht_ab():
    leer = "\n".join(DAX_CSV_DE.splitlines()[:5]) + "\n"
    with pytest.raises(bu.QuelleUnbrauchbar, match="kein einziger Aktien-Eintrag"):
        _de_lade(leer)


# ---------------------------------------------------------------- HDAX


def _hdax():
    return bu.vereinige(
        [
            _de_lade(DAX_CSV_DE),
            _de_lade(MDAX_CSV_EN, index="MDAX"),
            _de_lade(TECDAX_CSV_DE, index="TecDAX"),
        ]
    )


def test_doppelmitglieder_erscheinen_genau_einmal():
    hdax = _hdax()
    ticker = [k.ticker for k in hdax.kandidaten]
    # 4 (DAX) + 3 (MDAX) + 3 (TecDAX) = 10 Eintraege, davon 2 doppelt -> 8
    assert len(ticker) == 8
    assert len(set(ticker)) == len(ticker), "kein Ticker darf doppelt auftauchen"
    assert ticker.count("SAP.DE") == 1
    assert ticker.count("AIXA.DE") == 1


def test_doppelmitglied_behaelt_beide_herkuenfte():
    nach_ticker = {k.ticker: k for k in _hdax().kandidaten}
    assert nach_ticker["SAP.DE"].herkunft == "DAX, TecDAX"
    assert nach_ticker["AIXA.DE"].herkunft == "DAX, TecDAX"
    assert nach_ticker["VOW3.DE"].herkunft == "DAX"
    assert nach_ticker["AT1.DE"].herkunft == "MDAX"
    assert nach_ticker["NA9.DE"].herkunft == "TecDAX"


def test_vereinigung_ist_nach_ticker_sortiert():
    ticker = [k.ticker for k in _hdax().kandidaten]
    assert ticker == sorted(ticker)


def test_aeltester_stichtag_zaehlt_fuer_das_gesamtuniversum():
    """Das Universum ist nur so frisch wie seine schwaechste Zutat."""
    aelter = DAX_CSV_DE.replace("31.Jul.2026", "29.Jul.2026")
    hdax = bu.vereinige(
        [
            _de_lade(aelter),
            _de_lade(MDAX_CSV_EN, index="MDAX"),
            _de_lade(TECDAX_CSV_DE, index="TecDAX"),
        ]
    )
    assert hdax.bestand_stand == Date(2026, 7, 29)


# --------------------------------------------------- Determinismus / Form


def _kandidaten():
    return [
        bu.Kandidat("SAP.DE", "SAP SE", "DAX, TecDAX"),
        bu.Kandidat("AIXA.DE", "AIXTRON SE", "DAX, TecDAX"),
        bu.Kandidat("1COV.DE", "COVESTRO AG", "DAX"),
    ]


def test_gleicher_input_gleiche_datei_unabhaengig_von_der_reihenfolge():
    a = bu.rendere_universum("HDAX", "Quelle", "2026-08-03", "lauf-1", _kandidaten())
    b = bu.rendere_universum(
        "HDAX", "Quelle", "2026-08-03", "lauf-1", list(reversed(_kandidaten()))
    )
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_gleiche_csv_inhalte_ergeben_identische_universums_dateien():
    """Zweimal dieselben Bestandslisten -> Zeichen fuer Zeichen dieselbe Datei."""
    erste = bu.rendere_universum(
        "HDAX", "Quelle", "2026-08-03", "lauf-1", _hdax().kandidaten
    )
    zweite = bu.rendere_universum(
        "HDAX", "Quelle", "2026-08-03", "lauf-1", _hdax().kandidaten
    )
    assert erste == zweite
    assert erste.splitlines()[9:] == [
        "1COV.DE\tCOVESTRO AG",
        "AIXA.DE\tAIXTRON SE",
        "AT1.DE\tAROUNDTOWN SA",
        "FPE3.DE\tFUCHS SE PREF",
        "NA9.DE\tNAGARRO SE",
        "RHM.DE\tRHEINMETALL AG",
        "SAP.DE\tSAP SE",
        "VOW3.DE\tVOLKSWAGEN AG VZ",
    ]


def test_datei_traegt_den_geprueften_status():
    text = bu.rendere_universum("HDAX", "Quelle", "2026-08-03", "lauf-1", _kandidaten())
    assert "# STATUS: VERIFIED" in text
    assert "# Herkunft: Quelle" in text
    assert "# Stand: 2026-08-03" in text


def test_erzeugte_datei_wird_vom_werkzeug_akzeptiert(tmp_path):
    """Gegenprobe: was der Bootstrap schreibt, muss der Lauf lesen koennen."""
    from momentum.universe import load_universe

    pfad = tmp_path / "u.txt"
    pfad.write_text(
        bu.rendere_universum("HDAX", "Quelle", "2026-08-03", "lauf-1", _kandidaten()),
        encoding="utf-8",
    )
    universum = load_universe(pfad)
    assert universum.status == "VERIFIED"
    assert universum.tickers == ("1COV.DE", "AIXA.DE", "SAP.DE")
    assert universum.name_of("AIXA.DE") == "AIXTRON SE"


# ------------------------------------------------------------ Konstanten


def test_plausibilitaets_schranken_stehen_wie_beauftragt():
    assert bu.ERWARTET["us"] == (495, 510)
    assert bu.ERWARTET["de"] == (95, 125)


def test_die_drei_bestandsquellen_sind_vollstaendig_beschrieben():
    assert [q.index_name for q in bu.ISHARES_DE] == ["DAX", "MDAX", "TecDAX"]
    assert [q.xetra for q in bu.ISHARES_DE] == ["EXS1", "EXS3", "EXS2"]
    for quelle in bu.ISHARES_DE:
        assert quelle.url.startswith("https://www.ishares.com/")
        assert "fileType=csv" in quelle.url
        assert quelle.env_override.startswith("MOMENTUM_URL_")


def test_nur_die_tecdax_isin_gilt_als_belegt():
    """Ehrlichkeit im Code: was Recherche ist, steht als Recherche drin."""
    belegt = {q.index_name: q.isin_belegt for q in bu.ISHARES_DE}
    assert belegt == {"DAX": False, "MDAX": False, "TecDAX": True}
    tecdax = next(q for q in bu.ISHARES_DE if q.index_name == "TecDAX")
    assert tecdax.isin == "DE0005933972"


def test_url_kann_ohne_code_aenderung_ersetzt_werden(monkeypatch):
    quelle = bu.ISHARES_DE[0]
    assert bu.quellen_url(quelle) == quelle.url
    monkeypatch.setenv(quelle.env_override, "https://example.invalid/holdings.csv")
    assert bu.quellen_url(quelle) == "https://example.invalid/holdings.csv"


def test_max_alter_ist_eine_benannte_konstante():
    assert bu.MAX_ALTER_HANDELSTAGE == 10
