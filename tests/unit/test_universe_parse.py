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


def test_seite_ohne_tabelle_ist_ein_sauberer_quellen_abbruch():
    """Gefunden beim Bau des Vertragstests (#24): ohne Tabelle kam aus
    pandas eine nackte ImportError-Meldung ueber eine fehlende OPTIONALE
    Bibliothek -- eine Spur, die in die voellig falsche Richtung fuehrt.
    Schlimmer noch: weder die Markt-Isolierung im Lauf noch der
    Vertragstest erkennen so etwas als Quellen-Bruch, weil beide auf
    QuelleUnbrauchbar hoeren.
    """
    for html in (
        "<html><body><p>Nur Text, keine Tabelle</p></body></html>",
        "",
        "\x00 kein HTML",
    ):
        with pytest.raises(bu.QuelleUnbrauchbar, match="Quelle US"):
            bu.parse_us(html)


def test_die_meldung_zeigt_auf_die_seite_und_nicht_auf_ein_paket():
    """Der Sinn der Uebersetzung: Wer sie liest, sucht an der richtigen
    Stelle."""
    with pytest.raises(bu.QuelleUnbrauchbar) as fehler:
        bu.parse_us("<html><body>ohne Tabelle</body></html>")
    text = str(fehler.value)
    assert "Enthaelt der Artikel ueberhaupt noch eine Tabelle?" in text
    assert "NICHTS geschrieben" in text
    assert "html5lib" not in text, "die irrefuehrende Paket-Spur ist zurueck"


# --------------------------------------------------------------------------
# DE: iShares-Bestandslisten
# --------------------------------------------------------------------------

# ==========================================================================
# DAS ECHTE FORMAT. Vorspann und Kopfzeile stehen hier WOERTLICH so, wie
# iShares die Datei ausliefert — extern verifiziert am 02.08.2026 an allen
# drei Dateien (EXS1 / EXS3 / EXS2, Bestands-Stichtag 31. Juli 2026).
#
# Drei Eigenheiten, an denen der Lauf vom 02.08.2026 gescheitert ist:
#   * KEIN Fondsname — der ganze Vorspann ist eine einzige Zeile.
#   * Stichtag als "31.Juli2026": deutscher Monatsname, ohne Leerzeichen.
#   * UTF-8-BOM am Dateianfang.
# Dazu: Komma als Trenner und KEINE ISIN-Spalte.
#
# Nicht verifiziert sind die Datenzeilen selbst — geliefert wurden nur
# Vorspann, Kopfzeile und die Zeilenzahl je Index. Die Werte unten sind
# deshalb nachgebildet; wortwoertlich ist alles ueber der ersten Datenzeile.
# ==========================================================================

BOM = "﻿"

# Zweite Zeile: eine Zeile mit genau EINEM Leerzeichen, kein Leerstring.
VORSPANN_ECHT = 'Fondsposition per,"31.Juli2026"\n \n'

KOPFZEILE_ECHT = (
    "Emittententicker,Name,Sektor,Anlageklasse,Marktwert,Gewichtung (%),"
    "Nominalwert,Nominale,Kurs,Standort,Börse,Marktwährung"
)


def echte_datei(titel, *, vorspann=VORSPANN_ECHT, bom=True, zusatz=()):
    """Eine Bestandsliste im echten Format bauen. `titel`: (Ticker, Name)."""
    zeilen = [KOPFZEILE_ECHT]
    zeilen += [
        f"{ticker},{name},Informationstechnologie,Aktien,"
        f"1234567.89,1.23,10000,10000,123.45,Deutschland,Xetra,EUR"
        for ticker, name in titel
    ]
    zeilen += list(zusatz)
    return (BOM if bom else "") + vorspann + "\n".join(zeilen) + "\n"


def platzhalter(anzahl):
    """`anzahl` verschiedene Aktien-Zeilen — fuer die Tests am Anzahl-Gatter."""
    return [(f"T{i:02d}", f"BEISPIEL {i:02d} AG") for i in range(anzahl)]


# Echte Groessen der drei Indizes, ausgezaehlt an den echten Dateien.
ECHTE_ANZAHL = {"DAX": 40, "MDAX": 50, "TecDAX": 30}

DAX_ECHT = echte_datei(
    [
        ("SAP", "SAP SE"),
        ("AIXA", "AIXTRON SE"),
        ("VOW3", "VOLKSWAGEN AG VZ"),
        ("1COV", "COVESTRO AG"),
    ],
    zusatz=[
        "-,EUR CASH,Bargeld,Bargeld und/oder Derivate,"
        "1000.00,0.01,1000,1000,1.00,-,-,EUR",
        "-,DAX INDEX FUTURE SEP 26,Derivate,Futures,"
        "5000.00,0.04,5,5,1000.00,-,EUREX,EUR",
    ],
)


# ==========================================================================
# FORMVARIANTEN — ausdruecklich NICHT das verifizierte Format.
#
# Semikolon statt Komma, ISIN-Spalte, mehrere Vorspann-Zeilen samt
# Fondsnamen. Sie bleiben im Bestand, weil sie beweisen, dass der Parser
# nicht auf genau eine Schreibweise festgenagelt ist: eine ueberzaehlige
# Vorspann-Zeile darf ihn ebenso wenig aus dem Tritt bringen wie der
# Wechsel des Trenners. Der frueher hier gepruefte Fondsname wird nirgends
# mehr gelesen — er steht nur noch als harmlose Vorspann-Zeile drin.
# ==========================================================================

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


# Das ANZAHL-GATTER ausgesetzt: die Beispieldateien oben sind bewusst
# klein, ein DAX mit 40 Zeilen waere in jedem Test unlesbar. Das Gatter
# selbst hat weiter unten eigene Tests — mit echten Groessen.
OHNE_ANZAHL_GATTER = (0, 1000)


def _de_lade(inhalt, index="DAX", heute=HEUTE, anzahl=OHNE_ANZAHL_GATTER, **kw):
    return bu.parse_ishares_holdings(
        inhalt, index, heute=heute, erwartete_anzahl=anzahl, **kw
    )


# ------------------------------------------------------- Grundfunktion


def test_das_echte_format_wird_gelesen():
    """Der Fall, an dem der Lauf vom 02.08.2026 gescheitert ist.

    BOM, einzeiliger Vorspann ohne Fondsnamen, Stichtag "31.Juli2026",
    Komma-Trenner, keine ISIN-Spalte — alles in einer Datei.
    """
    befund = _de_lade(DAX_ECHT)
    assert [k.ticker for k in befund.kandidaten] == [
        "SAP.DE",
        "AIXA.DE",
        "VOW3.DE",
        "1COV.DE",
    ]
    assert befund.bestand_stand == Date(2026, 7, 31)
    assert befund.aktien_zeilen == 4
    assert befund.nicht_aktien == 2, "Bargeld- und Futures-Zeile gehoeren nicht dazu"
    assert befund.ungeloest == []
    assert all(k.herkunft == "DAX" for k in befund.kandidaten)


def test_das_byte_order_mark_stoert_nicht():
    """Mit und ohne BOM muss dasselbe herauskommen."""
    mit = _de_lade(DAX_ECHT)
    ohne = _de_lade(echte_datei([("SAP", "SAP SE")], bom=False))
    assert DAX_ECHT.startswith(BOM), "die Beispieldatei traegt gar keine BOM"
    assert mit.kandidaten[0].ticker == ohne.kandidaten[0].ticker == "SAP.DE"
    assert mit.bestand_stand == ohne.bestand_stand == Date(2026, 7, 31)


def test_ohne_fondsnamen_laeuft_es_trotzdem():
    """Die echten Dateien fuehren keinen — kein Codepfad darf einen erwarten."""
    assert "iShares" not in DAX_ECHT
    assert not hasattr(bu, "pruefe_fondsname")
    assert not hasattr(bu, "_index_im_namen")
    assert "fonds_name" not in bu.Befund().__dict__
    assert _de_lade(DAX_ECHT).kandidaten, "Datei ohne Fondsnamen muss durchgehen"


def test_deutsche_fassung_wird_gelesen():
    befund = _de_lade(DAX_CSV_DE)
    assert [k.ticker for k in befund.kandidaten] == [
        "SAP.DE",
        "AIXA.DE",
        "VOW3.DE",
        "1COV.DE",
    ]
    assert befund.bestand_stand == Date(2026, 7, 31)
    assert all(k.herkunft == "DAX" for k in befund.kandidaten)
    assert befund.ungeloest == []


def test_englische_fassung_wird_gelesen():
    befund = _de_lade(MDAX_CSV_EN, index="MDAX")
    assert [k.ticker for k in befund.kandidaten] == ["AT1.DE", "FPE3.DE", "RHM.DE"]
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
    assert befund.bestand_stand is not None
    # Auch beim echten, einzeiligen Vorspann
    echt = _de_lade(DAX_ECHT)
    assert not any("Fondsposition" in k.name for k in echt.kandidaten)
    assert echt.bestand_stand is not None


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


# ---------------------------------------------------------- Anzahl-Gatter
#
# Der Ersatz fuer das frueher gepruefte Fondsnamen-Gatter. Weil die echten
# Dateien keinen Fondsnamen fuehren, wird die Vertauschung jetzt an der
# Zeilenzahl erkannt — die drei erlaubten Bereiche ueberlappen nicht.


@pytest.mark.parametrize("index,anzahl", sorted(ECHTE_ANZAHL.items()))
def test_die_echte_groesse_kommt_durch(index, anzahl):
    befund = bu.parse_ishares_holdings(
        echte_datei(platzhalter(anzahl)), index, heute=HEUTE
    )
    assert befund.aktien_zeilen == anzahl
    assert len(befund.kandidaten) == anzahl


@pytest.mark.parametrize(
    "echter_index,unter_url_von",
    [
        ("DAX", "MDAX"),
        ("MDAX", "DAX"),
        ("DAX", "TecDAX"),
        ("TecDAX", "DAX"),
        ("MDAX", "TecDAX"),
        ("TecDAX", "MDAX"),
    ],
)
def test_jede_vertauschung_faellt_auf(echter_index, unter_url_von):
    """Jede der drei Paarungen, in beide Richtungen — einzeln bewiesen.

    Die Datei des einen Index landet unter der URL des anderen. Genau der
    Fall, den frueher der Fondsname abgefangen hat.
    """
    datei = echte_datei(platzhalter(ECHTE_ANZAHL[echter_index]))
    with pytest.raises(bu.QuelleUnbrauchbar) as fehler:
        bu.parse_ishares_holdings(datei, unter_url_von, heute=HEUTE)

    text = str(fehler.value)
    unten, oben = bu.ANZAHL_ERWARTET[unter_url_von]
    assert f"{ECHTE_ANZAHL[echter_index]} Aktien-Zeilen" in text, "Ist-Zahl fehlt"
    assert f"{unten}–{oben}" in text, "erwarteter Bereich fehlt"
    # "passt zum DAX" darf nicht versehentlich in "passt zum MDAX" treffen —
    # der Praefix bis einschliesslich "zum " macht die Pruefung eindeutig.
    assert f"passt zum {echter_index}" in text, "der Verursacher wird nicht genannt"
    assert "NICHTS geschrieben" in text


def test_die_drei_bereiche_ueberlappen_nicht():
    """Darauf ruht die Vertauschungs-Erkennung — also festgenagelt."""
    assert bu.ANZAHL_ERWARTET == {
        "DAX": (38, 42),
        "MDAX": (48, 52),
        "TecDAX": (28, 32),
    }
    bereiche = sorted(bu.ANZAHL_ERWARTET.values())
    for (_, oben), (unten, _) in zip(bereiche, bereiche[1:]):
        assert oben < unten, f"Bereiche ueberlappen: {oben} >= {unten}"


def test_eine_zahl_ausserhalb_aller_bereiche_bricht_ohne_verdacht_ab():
    """Kein Verwechslungs-Hinweis, wo es nichts zu verwechseln gibt."""
    with pytest.raises(bu.QuelleUnbrauchbar) as fehler:
        bu.parse_ishares_holdings(echte_datei(platzhalter(7)), "DAX", heute=HEUTE)
    text = str(fehler.value)
    assert "7 Aktien-Zeilen" in text and "38–42" in text
    assert "vermutlich zeigt" not in text.lower()


def test_das_gatter_greift_vor_der_isin_reserve():
    """Eine vertauschte Datei darf keinen einzigen Netzabruf ausloesen."""
    gerufen = []

    def resolver(isin):
        gerufen.append(isin)
        return "SIE.DE"

    # Eigene Datei: sie braucht eine ISIN-Spalte, damit die Reserve ueberhaupt
    # greifen KOENNTE. Das echte Format fuehrt keine — hier ginge der Test
    # sonst folgenlos durch und wuerde nichts beweisen.
    zeilen = ['Fondsbestände Stand;"31.Juli2026"', "Emittententicker;Name;Anlageklasse;ISIN"]
    zeilen += [f"-;BEISPIEL {i} AG;Aktien;DE00000{i:05d}" for i in range(50)]
    datei = "\n".join(zeilen) + "\n"

    with pytest.raises(bu.QuelleUnbrauchbar, match="Aktien-Zeilen"):
        bu.parse_ishares_holdings(datei, "DAX", heute=HEUTE, isin_resolver=resolver)
    assert gerufen == [], "die ISIN-Reserve wurde trotz falscher Datei befragt"

    # Gegenprobe: bei passender Anzahl wird sie sehr wohl befragt.
    passend = "\n".join(zeilen[:2] + zeilen[2:42]) + "\n"
    bu.parse_ishares_holdings(passend, "DAX", heute=HEUTE, isin_resolver=resolver)
    assert len(gerufen) == 40


def test_die_grenzen_des_bereichs_sind_eingeschlossen():
    for index, (unten, oben) in bu.ANZAHL_ERWARTET.items():
        bu.pruefe_anzahl(unten, index)
        bu.pruefe_anzahl(oben, index)
        with pytest.raises(bu.QuelleUnbrauchbar):
            bu.pruefe_anzahl(unten - 1, index)
        with pytest.raises(bu.QuelleUnbrauchbar):
            bu.pruefe_anzahl(oben + 1, index)


def test_anzahl_gatter_und_gesamtschranke_vertragen_sich():
    """Die Frage, die man sich bei zwei Schranken stellen muss.

    Heute sind 18 TecDAX-Werte zugleich im DAX oder MDAX (40 + 50 + 30 =
    120 Zeilen, nach Dedup 102 Titel — extern ausgezaehlt am 02.08.2026).
    Bei dieser Ueberschneidung liegt JEDE Kombination der drei Bereiche
    innerhalb der Gesamtschranke 95–125: keine Datei kann alle drei
    Anzahl-Gatter bestehen und dann an der Gesamtschranke scheitern.

    Die Ueberschneidung aendert sich mit jeder Index-Ueberpruefung der
    Deutschen Boerse — deshalb bleibt die Gesamtschranke der Auffangriegel
    und wird hier nicht wegoptimiert.
    """
    ueberschneidung = 18
    unten_ges, oben_ges = bu.ERWARTET["de"]
    kleinste = sum(u for u, _ in bu.ANZAHL_ERWARTET.values()) - ueberschneidung
    groesste = sum(o for _, o in bu.ANZAHL_ERWARTET.values()) - ueberschneidung
    assert (kleinste, groesste) == (96, 108)
    assert unten_ges <= kleinste and groesste <= oben_ges


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
        # DAS echte Format: deutscher Monatsname, KEIN Leerzeichen davor.
        ('Fondsposition per,"31.Juli2026"', Date(2026, 7, 31)),
        # ... auch mit BOM davor, also als allererste Zeile der Datei.
        ('﻿Fondsposition per,"31.Juli2026"', Date(2026, 7, 31)),
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


@pytest.mark.parametrize(
    "monat,nummer",
    list(
        zip(
            [
                "Januar", "Februar", "März", "April", "Mai", "Juni",
                "Juli", "August", "September", "Oktober", "November", "Dezember",
            ],
            range(1, 13),
        )
    ),
)
def test_alle_zwoelf_deutschen_monatsnamen_ohne_leerzeichen(monat, nummer):
    """Im August faellt nur der Juli auf — geprueft wird trotzdem das Jahr."""
    assert bu._datum_aus_text(f'"15.{monat}2026"') == Date(2026, nummer, 15)


# ------------------------------------------- Die ABGEKUERZTE Schreibweise
#
# Am 08.08.2026 extern verifiziert: die EXS1-Datei trug an diesem Tag den
# Vorspann `Fondsposition per,"06.Aug.2026"` — abgekuerzter deutscher
# Monatsname MIT Punkten. Beim Bau des Parsers gab es nur die
# ausgeschriebene Form ("31.Juli2026").
#
# BEFUND ZUR EINORDNUNG: Der Parser liest diese Form BEREITS richtig, und
# das ist nicht Theorie — der Vertragstest hat am 09.08.2026 auf dem
# Runner alle drei echten Dateien gelesen und fuer jede "Stichtag
# 2026-08-06" gemeldet. Der Grund ist die Aufloesung ueber die ersten drei
# Zeichen des Monatsnamens: sie trifft die abgekuerzte Form genauso wie
# die ausgeschriebene.
#
# Die Tests unten aendern daran also nichts — sie nageln es fest. Genau
# das ist ihr Wert: die Zeile darunter im Parser ist eine, die man beim
# naechsten Umbau fuer eine Vereinfachung halten koennte.

VORSPANN_ABGEKUERZT = 'Fondsposition per,"06.Aug.2026"'

DEUTSCHE_KUERZEL = [
    "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def test_die_echte_zeile_vom_08_08_2026_wird_gelesen():
    """Woertlich so, wie iShares sie an diesem Tag ausgeliefert hat."""
    assert bu._datum_aus_text(VORSPANN_ABGEKUERZT) == Date(2026, 8, 6)


def test_die_echte_zeile_traegt_auch_eine_ganze_datei():
    """Nicht nur die Zeile — die vollstaendige Datei mit diesem Vorspann."""
    datei = echte_datei(
        [("SAP", "SAP SE")], vorspann=f'{VORSPANN_ABGEKUERZT}\n \n'
    )
    befund = _de_lade(datei, heute=Date(2026, 8, 10))
    assert befund.bestand_stand == Date(2026, 8, 6)
    assert [k.ticker for k in befund.kandidaten] == ["SAP.DE"]


@pytest.mark.parametrize("nummer,kuerzel", list(enumerate(DEUTSCHE_KUERZEL, 1)))
@pytest.mark.parametrize("punkt", ["", "."], ids=["ohne-Punkt", "mit-Punkt"])
def test_alle_zwoelf_monate_abgekuerzt_mit_und_ohne_punkt(nummer, kuerzel, punkt):
    assert bu._datum_aus_text(f'"06.{kuerzel}{punkt}2026"') == Date(2026, nummer, 6)


@pytest.mark.parametrize("schreibweise,nummer", [("Mär", 3), ("März", 3), ("Sept", 9)])
def test_die_umlaut_und_vier_zeichen_kuerzel_greifen_auch(schreibweise, nummer):
    """März wird mal "Mrz", mal "Mär" abgekuerzt; September mal "Sept"."""
    assert bu._datum_aus_text(f'"06.{schreibweise}.2026"') == Date(2026, nummer, 6)


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
    """Ohne ausgesetztes Gatter faengt schon die Anzahl den leeren Fall ab."""
    leer = "\n".join(DAX_CSV_DE.splitlines()[:5]) + "\n"
    with pytest.raises(bu.QuelleUnbrauchbar, match="0 Aktien-Zeilen"):
        bu.parse_ishares_holdings(leer, "DAX", heute=HEUTE)


def test_aktien_ohne_aufloesbaren_ticker_brechen_ab():
    """Zeilen da, Ticker keiner: eigener Befund, eigene Meldung."""
    ohne_ticker = echte_datei([("-", f"OHNE TICKER {i} AG") for i in range(4)])
    with pytest.raises(bu.QuelleUnbrauchbar, match="keiner einzigen"):
        _de_lade(ohne_ticker)


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


def test_die_extern_verifizierten_produkt_ids_stehen_drin():
    """Am 02.08.2026 abgerufen und ausgezaehlt — nicht wieder verlieren."""
    ids = {q.index_name: q.url for q in bu.ISHARES_DE}
    assert "/produkte/251464/" in ids["DAX"]
    assert "/produkte/251845/" in ids["MDAX"]
    assert "/produkte/251975/" in ids["TecDAX"]


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
