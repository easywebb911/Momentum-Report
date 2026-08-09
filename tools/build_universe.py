"""Universums-Listen aus dokumentierter Quelle erzeugen — bewusst manuell.

Laeuft NUR ueber den Workflow "Universum aktualisieren" (workflow_dispatch),
nie automatisch. Das Universum darf sich nicht unbemerkt unter einem
laufenden Ranking wegdrehen.

QUELLEN
  USA:  Wikipedia (englisch) "List of S&P 500 companies", Spalte "Symbol".
        Der Artikel wird laufend gepflegt und war im ersten Lauf brauchbar.

  DE:   die TAEGLICHEN Bestandslisten (Holdings-CSV) von drei physisch
        replizierenden iShares-Index-ETFs. Physisch replizierend heisst:
        der Fonds haelt die Aktien wirklich, sein Bestand ist praktisch der
        Index. Damit wird das Universum aus einer Quelle gespeist, die sich
        jeden Handelstag aktualisiert.

        WARUM NICHT MEHR WIKIPEDIA: Die englischen Artikel zu den deutschen
        Indizes sind veraltet (TecDAX zuletzt eine blosse Namensliste ohne
        Symbolspalte, Stand Februar 2024; MDAX-Tabelle Stand 2023). Eine
        FEHLENDE Neuaufnahme faellt bei keiner Kurspruefung auf -- der
        Ticker, den es nicht gibt, kann nicht durchfallen. Genau dagegen
        hilft das Veraltungs-Gatter weiter unten.

ANNAHME ZUM ".DE"-SUFFIX (ausdruecklich benannt, nicht stillschweigend):
Yahoo-Ticker = Xetra-Symbol + ".DE". Vorzugsaktien brauchen KEINE
Sonderbehandlung, weil das Xetra-Symbol die Gattung bereits traegt --
VOW3 (Volkswagen Vz.), HEN3 (Henkel Vz.), SRT3 (Sartorius Vz.), FPE3
(Fuchs Vz.) werden zu VOW3.DE usw. und treffen damit genau die
Vorzugsgattung. Symbole mit fuehrender Ziffer (1COV) sind zugelassen.
Titel ohne Xetra-Notierung oder mit abweichendem Yahoo-Symbol fallen in
der Kurspruefung heraus und werden dort NAMENTLICH genannt.

SICHERUNGEN, in dieser Reihenfolge:
  1. Bestands-Stichtag aus dem Vorspann lesen; aelter als 10 Handelstage
     -> Abbruch (VERALTUNGS-GATTER)
  2. nur Zeilen der Anlageklasse Aktie; Cash, Futures, Geldmarkt fliegen raus
  3. Anzahl der Aktien-Zeilen gegen den erwarteten Bereich des Index pruefen
     -- eine vertauschte URL faellt damit auf, statt still ein falsches
     Universum zu erzeugen (ANZAHL-GATTER, siehe ANZAHL_ERWARTET)
  4. Ticker-Spalte lesen; fehlt der Ticker, ISIN-Reserve ueber die
     Yahoo-Suche -- jede solche Aufloesung wird namentlich protokolliert
  5. Vereinigung der drei Listen, Doppelmitglieder genau einmal
  6. JEDER Ticker wird gegen echte Kursdaten geprueft; Aussortierte werden
     namentlich genannt
  7. Plausibilitaets-Schranke: Anzahl ausserhalb des Bereichs -> nichts
     schreiben
  8. Erst dann die Datei -- mit "# STATUS: VERIFIED". Diese Zeile ist der
     einzige Weg, wie ein Universum rechenbar wird (default-deny in
     momentum/universe.py).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import io
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent / 'src'))
from momentum.meta import dump_meta  # noqa: E402

USER_AGENT = (
    "Momentum-Report/0.1 (+https://github.com/easywebb911/Momentum-Report) "
    "python-urllib"
)

QUELLE_US = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# --------------------------------------------------------------------------
# DIE DREI iSHARES-BESTANDSLISTEN — die einzige Stelle mit URLs.
#
# SO FINDET MAN DIE URL WIEDER (falls eine hier nicht mehr zieht):
#   1. ishares.com aufrufen, Land Deutschland / Privatanleger
#   2. den Fonds ueber seine Xetra-Kennung suchen (EXS1 / EXS3 / EXS2)
#   3. auf der Produktseite ganz nach unten zum Abschnitt "Positionen"
#      bzw. "Holdings"; dort steht der Link "Positionen und Analysen
#      herunterladen" / "Detailed Holdings and Analytics" -> CSV
#   4. diesen Link kopieren und hier eintragen ODER dem Workflow
#      "Universum aktualisieren" als Eingabefeld mitgeben (url_dax,
#      url_mdax, url_tecdax) -- dann ist keine Code-Aenderung noetig
#
# STAND DER PRUEFUNG (02.08.2026): Die drei PRODUKT-IDs unten sind extern
# verifiziert -- die Dateien wurden abgerufen und ausgezaehlt: 251464 = DAX
# (40 Aktien-Zeilen), 251845 = MDAX (50), 251975 = TecDAX (30), alle mit
# Bestands-Stichtag 31. Juli 2026. Der Egress-Proxy dieser Sitzung blockt
# ishares.com, hier konnte also nichts nachgeprueft werden.
#
# NICHT einzeln verifiziert ist der sprechende Namensteil im Pfad
# ({schnipsel}); er dient der Lesbarkeit, geschluesselt wird ueber die
# Produkt-ID. Zieht eine URL trotzdem nicht, bricht der Lauf LAUT ab und
# nennt die Anleitung oben; der Ersatz-Link laesst sich dem Workflow als
# Eingabefeld mitgeben, ohne den Code zu aendern.
#
# Ebenfalls unverifiziert bleibt die Zuordnung Xetra-Kennung -> Fonds fuer
# EXS1 und EXS3 (aus Recherche). Belegt ist nur EXS2 = iShares TecDAX,
# ISIN DE0005933972. Gegen eine vertauschte URL schuetzt deshalb das
# ANZAHL-GATTER: die drei Indizes haben verschieden viele Mitglieder, und
# die erlaubten Bereiche ueberlappen nicht.
# --------------------------------------------------------------------------

_ISHARES_DOWNLOAD = (
    "https://www.ishares.com/de/privatanleger/de/produkte/{produkt}/{schnipsel}/"
    "1478358465952.ajax?fileType=csv&fileName={datei}&dataType=fund"
)


@dataclass(frozen=True)
class Bestandsquelle:
    index_name: str        # erwarteter Index -- Schluessel fuer ANZAHL_ERWARTET
    xetra: str             # Xetra-Kennung des ETF
    isin: str | None       # ISIN des ETF, soweit belegt
    isin_belegt: bool      # False = aus Recherche, nicht bestaetigt
    url: str
    env_override: str      # Umgebungsvariable, die die URL ersetzen darf


ISHARES_DE: tuple[Bestandsquelle, ...] = (
    Bestandsquelle(
        index_name="DAX",
        xetra="EXS1",
        isin="DE0005933931",
        isin_belegt=False,
        url=_ISHARES_DOWNLOAD.format(
            produkt="251464", schnipsel="ishares-dax-ucits-etf-de-fund", datei="EXS1_holdings"
        ),
        env_override="MOMENTUM_URL_DAX",
    ),
    Bestandsquelle(
        index_name="MDAX",
        xetra="EXS3",
        isin="DE0005933923",
        isin_belegt=False,
        url=_ISHARES_DOWNLOAD.format(
            produkt="251845", schnipsel="ishares-mdax-ucits-etf-de-fund", datei="EXS3_holdings"
        ),
        env_override="MOMENTUM_URL_MDAX",
    ),
    Bestandsquelle(
        index_name="TecDAX",
        xetra="EXS2",
        isin="DE0005933972",   # belegt
        isin_belegt=True,
        url=_ISHARES_DOWNLOAD.format(
            produkt="251975", schnipsel="ishares-tecdax-ucits-etf-de-fund", datei="EXS2_holdings"
        ),
        env_override="MOMENTUM_URL_TECDAX",
    ),
)

# Plausibilitaets-Schranken. Ausserhalb: Abbruch statt Halbergebnis.
#
# DE: HDAX = DAX (40) + MDAX (50) + TecDAX (30) = 120 Eintraege VOR Abzug der
# Doppelmitglieder. TecDAX-Werte sind seit 2018 zugleich in DAX oder MDAX,
# und wie gross diese Ueberschneidung ausfaellt, aendert sich mit JEDER
# Index-Ueberpruefung der Deutschen Boerse. Die Vereinigungsmenge ist damit
# keine feste Zahl, sondern schwankt -- deshalb der Boden bei 95: eine
# Schranke, die bei jeder zweiten Umstellung anschlaegt, schuetzt nicht,
# sie blockiert nur.
ERWARTET = {"us": (495, 510), "de": (95, 125)}

# ANZAHL-GATTER: So viele Aktien-Zeilen muss die Bestandsliste EINES Index
# fuehren. Das ist der Ersatz fuer die frueher geprueften Fondsnamen -- die
# echten deutschen iShares-Dateien fuehren gar keinen Fondsnamen, ihr
# Vorspann besteht aus einer einzigen Zeile mit dem Stichtag.
#
# Der Schutz bleibt derselbe: Die drei Bereiche UEBERLAPPEN NICHT. Zeigt die
# DAX-URL versehentlich auf die MDAX-Datei, kommen 50 Zeilen an, wo 38–42
# erwartet werden -- Abbruch, statt still ein falsches Universum zu bauen.
#
# Warum ein Bereich und keine feste Zahl: zwischen zwei Index-Ueberpruefungen
# der Deutschen Boerse kann ein Wert ausscheiden, bevor der Nachruecker im
# Fondsbestand ankommt, und ein physisch replizierender ETF haelt am
# Umstellungstag kurzzeitig beide. +/- 2 faengt das ab, ohne die Trennung
# zwischen den Indizes aufzuweichen (kleinster Abstand: 42 zu 48).
#
# Sollwerte extern verifiziert am 02.08.2026 an den echten Dateien.
ANZAHL_ERWARTET: dict[str, tuple[int, int]] = {
    "DAX": (38, 42),
    "MDAX": (48, 52),
    "TecDAX": (28, 32),
}

# VERALTUNGS-GATTER: So alt darf der Bestands-Stichtag hoechstens sein.
# Ein physisch replizierender ETF veroeffentlicht arbeitstaeglich; ist die
# Datei aelter, stimmt etwas nicht -- entweder liefert die Quelle einen
# Zwischenspeicher-Stand oder der Abruf trifft die falsche Datei. In beiden
# Faellen ist die Liste als Index-Abbild wertlos.
MAX_ALTER_HANDELSTAGE = 10

# Spaltennamen, unter denen die Quellen ihre Felder fuehren.
SYMBOL_SPALTEN = ("symbol", "ticker", "ticker symbol", "emittententicker", "issuer ticker")
NAME_SPALTEN = ("security", "company", "name", "company name", "bezeichnung")
# Branche. Beide Quellen fuehren sie ohnehin mit -- sie wird nur
# mitgeschrieben, nicht zusaetzlich beschafft.
SEKTOR_SPALTEN = ("sektor", "sector", "gics sector", "gics sektor", "branche")
ISIN_SPALTEN = ("isin",)
ANLAGEKLASSE_SPALTEN = ("asset class", "anlageklasse")

# Nur diese Anlageklassen sind Aktien. Alles andere (Bargeld, Derivate,
# Geldmarkt, Futures) gehoert nicht ins Universum.
AKTIEN_KLASSEN = {"equity", "equities", "aktien", "aktie", "stock", "stocks"}

# Xetra-Kuerzel: 2-6 Zeichen, Ziffern erlaubt (1COV), auch fuehrend.
XETRA_MUSTER = re.compile(r"^[A-Z0-9]{2,6}$")
ISIN_MUSTER = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
PRAEFIX_MUSTER = re.compile(r"^(ETR|XETR|XETRA|FWB|FRA|DE)[:\s]+")

YAHOO_SUCHE = "https://query2.finance.yahoo.com/v1/finance/search?q={}&quotesCount=8"

MONATE = {
    **{m: i for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )},
    **{m: i for i, m in enumerate(
        ["jan", "feb", "mär", "apr", "mai", "jun", "jul", "aug", "sep", "okt", "nov", "dez"], 1
    )},
    "mrz": 3, "maerz": 3, "marz": 3, "okt": 10, "dez": 12,
}


class QuelleUnbrauchbar(Exception):
    """Die Quelle taugt nicht -- lauter Abbruch fuer DIESEN Markt.

    Bewusst eine Ausnahme und kein SystemExit: ein unbrauchbarer Markt darf
    den anderen nicht mitreissen. Genau das ist im ersten Lauf passiert --
    der TecDAX-Artikel riss das bereits fertige US-Universum mit ins Aus,
    weil der Prozess sofort endete und der Commit-Schritt uebersprungen wurde.
    """


@dataclass
class Kandidat:
    ticker: str
    name: str
    herkunft: str = ""
    ueber_reserve: bool = False
    # Rein beschreibend, geht in keine Rechnung ein (siehe momentum/meta.py).
    sektor: str = ""


@dataclass
class Befund:
    """Was ein Parse-Durchgang ergeben hat -- inklusive aller Randfaelle."""

    kandidaten: list[Kandidat] = field(default_factory=list)
    ueber_reserve: list[str] = field(default_factory=list)
    ungeloest: list[str] = field(default_factory=list)
    bestand_stand: _dt.date | None = None
    # Zeilen der Anlageklasse Aktie -- die Groesse, gegen die das
    # ANZAHL-GATTER prueft. Bewusst NICHT len(kandidaten): eine Zeile ohne
    # aufloesbaren Ticker ist trotzdem ein Index-Mitglied, und ob die Datei
    # zum erwarteten Index gehoert, ist eine andere Frage als die, ob jeder
    # Titel einen Kurs hat. Letzteres klaert die Kurspruefung.
    aktien_zeilen: int = 0
    nicht_aktien: int = 0


# --------------------------------------------------------------------------
# Reine Funktionen: nehmen Dateiinhalt entgegen, kein Netz. So sind sie testbar.
# --------------------------------------------------------------------------


def tabellen(html: str):
    """Alle HTML-Tabellen einer Seite -- oder ein sprechender Abbruch.

    `flavor="lxml"` ist bewusst festgelegt und nicht dem Zufall ueberlassen:
    ohne Angabe probiert pandas der Reihe nach mehrere Parser durch und
    meldet, wenn KEINER greift, die fehlende OPTIONALE Bibliothek des
    letzten Versuchs ("Import html5lib failed"). Diese Meldung schickt
    jeden, der sie liest, in die falsche Richtung -- nach einem fehlenden
    Paket zu suchen, wo in Wahrheit die Fremdseite keine Tabelle mehr
    enthaelt. lxml steht fest in requirements.txt; damit ist die Festlegung
    nur das Aussprechen dessen, was ohnehin gilt, und der Fehlerfall meldet
    endlich die Wahrheit.
    """
    import pandas as pd

    return pd.read_html(io.StringIO(html), flavor="lxml")


def _spalte(frame, kandidaten: tuple[str, ...]):
    """Erste passende Spalte finden; Vergleich klein geschrieben und getrimmt."""
    for gesucht in kandidaten:
        for spalte in frame.columns:
            if str(spalte).strip().lower() == gesucht:
                return spalte
    return None


def _text(zeile, spalte) -> str:
    if spalte is None:
        return ""
    wert = str(zeile[spalte]).strip()
    return "" if wert.lower() in ("nan", "none", "") else wert


def xetra_zu_yahoo(symbol: str) -> str | None:
    """Xetra-Kuerzel in einen Yahoo-Ticker uebersetzen. None, wenn unbrauchbar."""
    roh = PRAEFIX_MUSTER.sub("", symbol.strip().upper())
    roh = roh.replace(" ", "")
    if not XETRA_MUSTER.match(roh):
        return None
    return f"{roh}.DE"


def parse_us(html: str) -> Befund:
    """S&P-500-Mitglieder aus dem englischen Listenartikel.

    Yahoo schreibt Klassen-Ticker mit Bindestrich statt Punkt:
    BRK.B -> BRK-B, BF.B -> BF-B.
    """
    bester: Befund | None = None
    try:
        gefundene = tabellen(html)
    except QuelleUnbrauchbar:
        raise
    except Exception as exc:  # noqa: BLE001 - siehe Begruendung
        # Uebersetzen statt durchreichen. Eine nackte Bibliotheks-Ausnahme
        # aus dem HTML-Parser wuerde an der Markt-Isolierung im Lauf und am
        # Vertragstest vorbeirauschen: beide erkennen QuelleUnbrauchbar,
        # nicht "irgendeinen Fehler aus pandas". Der US-Markt wuerde damit
        # nicht sauber ausfallen, sondern den ganzen Vorgang mitreissen.
        raise QuelleUnbrauchbar(
            f"Quelle US: die Seite liess sich nicht als Tabelle lesen "
            f"({type(exc).__name__}: {exc}). Enthaelt der Artikel ueberhaupt "
            f"noch eine Tabelle? Es wurde NICHTS geschrieben."
        ) from exc
    for frame in gefundene:
        symbol_spalte = _spalte(frame, SYMBOL_SPALTEN)
        name_spalte = _spalte(frame, NAME_SPALTEN)
        sektor_spalte = _spalte(frame, SEKTOR_SPALTEN)
        if symbol_spalte is None or name_spalte is None:
            continue
        lauf = Befund()
        for _, zeile in frame.iterrows():
            symbol = _text(zeile, symbol_spalte)
            name = _text(zeile, name_spalte)
            sektor = _text(zeile, sektor_spalte)
            if not symbol:
                if name:
                    lauf.ungeloest.append(f"S&P 500: {name} (kein Symbol)")
                continue
            lauf.kandidaten.append(
                Kandidat(symbol.replace(".", "-"), name or symbol, "S&P 500", sektor=sektor)
            )
        # Die groesste passende Tabelle gewinnt -- Artikel enthalten daneben
        # kleinere Tabellen (Zu- und Abgaenge), die zufaellig dieselben
        # Spaltennamen tragen koennen.
        if bester is None or len(lauf.kandidaten) > len(bester.kandidaten):
            bester = lauf
    if bester is not None:
        return bester
    raise QuelleUnbrauchbar(
        "Quelle US: keine Mitgliedertabelle mit Symbol- und Namensspalte gefunden. "
        "Vermutlich hat sich der Aufbau des Wikipedia-Artikels geaendert -- "
        "es wurde NICHTS geschrieben."
    )


# ------------------------------------------------- iShares-Bestandslisten


def _trenner(zeile: str) -> str:
    """Semikolon (deutsche Fassung) oder Komma (englische) erkennen."""
    return ";" if zeile.count(";") > zeile.count(",") else ","


def _kopfzeile_finden(zeilen: list[str]) -> tuple[int, str, list[str]]:
    """Erste Zeile finden, die wie eine Spaltenueberschrift aussieht.

    iShares stellt der Tabelle Vorspann-Zeilen voran -- in den echten
    deutschen Dateien genau eine mit dem Stichtag, in anderen Fassungen
    mehrere. Die Kopfzeile erkennt man daran, dass sie eine Namensspalte
    UND eine Ticker- oder ISIN-Spalte fuehrt; wie viele Zeilen davor
    stehen, spielt dadurch keine Rolle.
    """
    for i, zeile in enumerate(zeilen):
        if not zeile.strip():
            continue
        trenner = _trenner(zeile)
        felder = [f.strip().strip('"').lower() for f in next(csv.reader([zeile], delimiter=trenner))]
        hat_name = any(f in NAME_SPALTEN for f in felder)
        hat_kennung = any(f in SYMBOL_SPALTEN or f in ISIN_SPALTEN for f in felder)
        if hat_name and hat_kennung:
            return i, trenner, felder
    raise QuelleUnbrauchbar(
        "Bestandsliste: keine Kopfzeile mit Namens- und Ticker-/ISIN-Spalte gefunden. "
        "Entweder hat die Datei ein anderes Format bekommen oder der Abruf hat "
        "etwas anderes als die Bestandsliste geliefert (z. B. eine HTML-Seite). "
        "Es wurde NICHTS geschrieben."
    )


def _datum_aus_text(text: str) -> _dt.date | None:
    """Datum aus einer Vorspann-Zeile lesen; deutsche und englische Schreibung."""
    aufbereitet = text.lstrip("﻿").strip().strip('"')
    treffer = re.search(r"(\d{4})-(\d{2})-(\d{2})", aufbereitet)
    if treffer:
        return _dt.date(int(treffer[1]), int(treffer[2]), int(treffer[3]))
    # 31.Jul.2026 / 31-Jul-2026 / 31. Juli 2026 / 31.Juli2026
    #
    # Der Trenner VOR dem Jahr ist ausdruecklich freigestellt: die echten
    # deutschen iShares-Dateien schreiben "31.Juli2026", ganz ohne. Genau
    # daran ist der Lauf vom 02.08.2026 gescheitert. Der ausgeschriebene
    # Monatsname wird ueber seine ersten drei Zeichen aufgeloest, damit
    # alle zwoelf deutschen Namen ohne eigene Liste greifen.
    treffer = re.search(r"(\d{1,2})[.\-/ ]\s*([A-Za-zÄÖÜäöüß]{3,9})\.?[.\-/ ]?\s*(\d{4})", aufbereitet)
    if treffer:
        monat = MONATE.get(treffer[2][:3].lower())
        if monat:
            return _dt.date(int(treffer[3]), monat, int(treffer[1]))
    # Jul 31, 2026
    treffer = re.search(r"([A-Za-zÄÖÜäöüß]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", aufbereitet)
    if treffer:
        monat = MONATE.get(treffer[1][:3].lower())
        if monat:
            return _dt.date(int(treffer[3]), monat, int(treffer[2]))
    # 31.07.2026 / 31/07/2026
    treffer = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", aufbereitet)
    if treffer:
        return _dt.date(int(treffer[3]), int(treffer[2]), int(treffer[1]))
    return None


def _anderer_index_mit_dieser_anzahl(anzahl: int, ausser: str) -> str | None:
    """Passt die Anzahl zu einem ANDEREN Index? Dann ist die URL vertauscht."""
    for name, (unten, oben) in ANZAHL_ERWARTET.items():
        if name != ausser and unten <= anzahl <= oben:
            return name
    return None


def pruefe_anzahl(
    anzahl: int, erwarteter_index: str, bereich: tuple[int, int] | None = None
) -> None:
    """ANZAHL-GATTER: Abbruch, wenn die Datei nicht zu diesem Index passen kann.

    Ersetzt die frueher geprueften Fondsnamen -- die echten deutschen
    iShares-Bestandslisten fuehren keinen. Weil die erlaubten Bereiche der
    drei Indizes nicht ueberlappen, faellt eine vertauschte URL genauso auf
    wie vorher, nur gegen das tatsaechliche Dateiformat.
    """
    unten, oben = bereich if bereich is not None else ANZAHL_ERWARTET[erwarteter_index]
    if unten <= anzahl <= oben:
        return
    verwechselt = _anderer_index_mit_dieser_anzahl(anzahl, erwarteter_index)
    hinweis = (
        f" Diese Anzahl passt zum {verwechselt} -- vermutlich zeigt die "
        f"{erwarteter_index}-URL auf die {verwechselt}-Bestandsliste."
        if verwechselt
        else ""
    )
    raise QuelleUnbrauchbar(
        f"{erwarteter_index}-Bestandsliste: {anzahl} Aktien-Zeilen, erwartet "
        f"waren {unten}–{oben}.{hinweis} Es wurde NICHTS geschrieben."
    )


def handelstage_zwischen(frueher: _dt.date, spaeter: _dt.date) -> int:
    """Werktage von `frueher` bis `spaeter`.

    Feiertage werden NICHT abgezogen. Dadurch zaehlt die Funktion eher zu
    viele Handelstage als zu wenige -- das Veraltungs-Gatter schlaegt also
    im Zweifel frueher an. Die strenge Richtung ist hier die richtige.
    """
    if spaeter <= frueher:
        return 0
    tage = 0
    lauf = frueher
    while lauf < spaeter:
        lauf += _dt.timedelta(days=1)
        if lauf.weekday() < 5:
            tage += 1
    return tage


def pruefe_aktualitaet(
    stand: _dt.date | None, heute: _dt.date, quelle: str, max_tage: int = MAX_ALTER_HANDELSTAGE
) -> None:
    """VERALTUNGS-GATTER. Ohne lesbaren Stichtag ebenfalls Abbruch.

    Das ist die Luecke, an der die alte Wikipedia-Quelle gescheitert ist:
    eine veraltete Liste sieht fehlerfrei aus, weil FEHLENDE Neuaufnahmen
    von keiner Pruefung entdeckt werden koennen. Nur ein Stichtag deckt das auf.
    """
    if stand is None:
        raise QuelleUnbrauchbar(
            f"{quelle}: im Vorspann steht kein lesbarer Bestands-Stichtag. Ohne "
            f"Stichtag laesst sich nicht feststellen, ob die Liste aktuell ist "
            f"-- und eine veraltete Liste faellt sonst nirgends auf. "
            f"Es wurde NICHTS geschrieben."
        )
    alter = handelstage_zwischen(stand, heute)
    if alter > max_tage:
        raise QuelleUnbrauchbar(
            f"{quelle}: Bestands-Stichtag {stand.isoformat()} ist {alter} "
            f"Handelstage alt (erlaubt: {max_tage}). Ein physisch "
            f"replizierender ETF veroeffentlicht arbeitstaeglich -- diese Datei "
            f"bildet den Index nicht mehr ab. Es wurde NICHTS geschrieben."
        )


def parse_ishares_holdings(
    inhalt: str,
    erwarteter_index: str,
    *,
    heute: _dt.date,
    isin_resolver=None,
    max_alter: int = MAX_ALTER_HANDELSTAGE,
    erwartete_anzahl: tuple[int, int] | None = None,
) -> Befund:
    """Eine iShares-Bestandsliste auswerten.

    Nimmt den Dateiinhalt entgegen, nicht eine URL -- deshalb ohne Netz
    testbar. `isin_resolver` ist die Reserve fuer Zeilen ohne Ticker.
    `erwartete_anzahl` uebersteuert das ANZAHL-GATTER; ohne Angabe gilt der
    Bereich aus ANZAHL_ERWARTET.

    Ein FONDSNAME wird nirgends erwartet: die echten deutschen Dateien
    fuehren keinen. Ihr gesamter Vorspann ist eine Zeile mit dem Stichtag.
    """
    # Byte-Order-Mark am Dateianfang: die echten Dateien tragen eine. Hier
    # abgeraeumt und nicht erst beim Abruf, damit die Funktion fuer sich
    # allein richtig ist -- egal, wer ihr den Inhalt reicht.
    zeilen = inhalt.lstrip("﻿").splitlines()
    kopf_index, trenner, spalten = _kopfzeile_finden(zeilen)

    befund = Befund()
    for zeile in zeilen[:kopf_index]:
        gefunden = _datum_aus_text(zeile)
        if gefunden is not None:
            befund.bestand_stand = gefunden
            break

    quelle = f"{erwarteter_index}-Bestandsliste"
    pruefe_aktualitaet(befund.bestand_stand, heute, quelle, max_alter)

    def feld(zeile: list[str], namen: tuple[str, ...]) -> str:
        for name in namen:
            if name in spalten:
                stelle = spalten.index(name)
                if stelle < len(zeile):
                    return zeile[stelle].strip().strip('"')
        return ""

    # Erster Durchgang: nur aussortieren und zaehlen. Das ANZAHL-GATTER
    # greift damit VOR jeder ISIN-Reserve -- eine vertauschte Datei loest
    # keinen einzigen Netzabruf mehr aus.
    aktien: list[list[str]] = []
    for roh in csv.reader(zeilen[kopf_index + 1 :], delimiter=trenner):
        if not roh or not any(f.strip() for f in roh):
            continue
        if not feld(roh, NAME_SPALTEN):
            continue
        klasse = feld(roh, ANLAGEKLASSE_SPALTEN).lower()
        if klasse and klasse not in AKTIEN_KLASSEN:
            befund.nicht_aktien += 1
            continue
        aktien.append(roh)

    befund.aktien_zeilen = len(aktien)
    pruefe_anzahl(befund.aktien_zeilen, erwarteter_index, erwartete_anzahl)

    for roh in aktien:
        name = feld(roh, NAME_SPALTEN)
        sektor = feld(roh, SEKTOR_SPALTEN)
        ticker = xetra_zu_yahoo(feld(roh, SYMBOL_SPALTEN))
        if ticker is None:
            isin = feld(roh, ISIN_SPALTEN).upper()
            if isin_resolver is not None and ISIN_MUSTER.match(isin):
                ticker = isin_resolver(isin)
                if ticker:
                    befund.ueber_reserve.append(
                        f"{erwarteter_index}: {name} — kein Ticker in der Bestandsliste, "
                        f"ueber ISIN {isin} aufgeloest zu {ticker}"
                    )
                    befund.kandidaten.append(
                        Kandidat(ticker, name, erwarteter_index, ueber_reserve=True,
                                 sektor=sektor)
                    )
                    continue
            befund.ungeloest.append(
                f"{erwarteter_index}: {name} (kein Ticker ermittelbar)"
            )
            continue
        befund.kandidaten.append(
            Kandidat(ticker, name, erwarteter_index, sektor=sektor)
        )

    if not befund.kandidaten:
        raise QuelleUnbrauchbar(
            f"{quelle}: {befund.aktien_zeilen} Aktien-Zeilen gelesen, aber aus "
            f"keiner einzigen liess sich ein Ticker gewinnen. "
            f"Es wurde NICHTS geschrieben."
        )
    return befund


def vereinige(befunde: list[Befund]) -> Befund:
    """HDAX bilden: Doppelmitglieder genau einmal, Herkunft zusammenfassen."""
    zusammen = Befund()
    nach_ticker: dict[str, Kandidat] = {}
    staende = []
    for befund in befunde:
        zusammen.ueber_reserve.extend(befund.ueber_reserve)
        zusammen.ungeloest.extend(befund.ungeloest)
        zusammen.aktien_zeilen += befund.aktien_zeilen
        zusammen.nicht_aktien += befund.nicht_aktien
        if befund.bestand_stand:
            staende.append(befund.bestand_stand)
        for kandidat in befund.kandidaten:
            vorhanden = nach_ticker.get(kandidat.ticker)
            if vorhanden is None:
                nach_ticker[kandidat.ticker] = Kandidat(
                    kandidat.ticker,
                    kandidat.name,
                    kandidat.herkunft,
                    kandidat.ueber_reserve,
                    kandidat.sektor,
                )
                continue
            # Doppelmitglied: nur die Herkunft ergaenzen, kein zweiter Eintrag.
            teile = vorhanden.herkunft.split(", ") if vorhanden.herkunft else []
            if kandidat.herkunft and kandidat.herkunft not in teile:
                teile.append(kandidat.herkunft)
                vorhanden.herkunft = ", ".join(teile)
    # Der aelteste Stichtag zaehlt: das Universum ist nur so frisch wie seine
    # schwaechste Zutat.
    zusammen.bestand_stand = min(staende) if staende else None
    zusammen.kandidaten = sorted(nach_ticker.values(), key=lambda k: k.ticker)
    return zusammen


def meta_aus_kandidaten(kandidaten: list[Kandidat]) -> dict[str, dict[str, str]]:
    """Ticker -> {name, sektor}. Leere Angaben bleiben leer, nie geraten."""
    return {
        k.ticker: {"name": k.name or "", "sektor": k.sektor or ""}
        for k in sorted(kandidaten, key=lambda k: k.ticker)
    }


def rendere_universum(
    bezeichnung: str, herkunft: str, stand: str, lauf: str, kandidaten: list[Kandidat]
) -> str:
    """Dateiinhalt erzeugen -- bei gleichen Eingaben Zeichen fuer Zeichen gleich.

    Die Zeile "# STATUS: VERIFIED" steht hier und NUR hier: sie ist die
    Zusage, dass jeder Ticker gegen echte Kursdaten geprueft wurde.
    """
    zeilen = [
        f"# Universum: {bezeichnung}",
        f"# Herkunft: {herkunft}",
        f"# Stand: {stand}",
        "# STATUS: VERIFIED",
        f"# Erzeugt von: .github/workflows/universum.yml (Lauf {lauf})",
        "# Jeder Ticker wurde beim Erzeugen gegen echte Kursdaten geprueft.",
        "# Aktualisierung ist ein bewusster manueller Vorgang.",
        "#",
        "# Format: TICKER<TAB>Firmenname",
    ]
    zeilen += [
        f"{k.ticker}\t{k.name}" for k in sorted(kandidaten, key=lambda k: k.ticker)
    ]
    return "\n".join(zeilen) + "\n"


# --------------------------------------------------------------------------
# Netz: Abruf, ISIN-Reserve, Kurspruefung
# --------------------------------------------------------------------------


def quellen_url(quelle: Bestandsquelle) -> str:
    """URL der Bestandsliste -- Umgebungsvariable schlaegt die Konstante."""
    return os.environ.get(quelle.env_override, "").strip() or quelle.url


def lade(url: str) -> str:  # pragma: no cover - echter Netzpfad
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as antwort:
        rohdaten = antwort.read()
    for kodierung in ("utf-8-sig", "cp1252"):
        try:
            return rohdaten.decode(kodierung)
        except UnicodeDecodeError:
            continue
    return rohdaten.decode("utf-8", "replace")


def lade_bestandsliste(quelle: Bestandsquelle) -> str:  # pragma: no cover - Netzpfad
    url = quellen_url(quelle)
    try:
        inhalt = lade(url)
    except Exception as exc:  # noqa: BLE001
        raise QuelleUnbrauchbar(
            f"{quelle.index_name}: Bestandsliste nicht abrufbar ({exc}).\n"
            f"URL: {url}\n"
            f"So kommt man an die richtige: ishares.com -> Deutschland/"
            f"Privatanleger -> Fonds {quelle.xetra} suchen -> Abschnitt "
            f"'Positionen' -> Link 'Positionen und Analysen herunterladen' "
            f"(CSV). Diesen Link dem Workflow als Eingabefeld mitgeben "
            f"(url_dax / url_mdax / url_tecdax) oder in tools/build_universe.py "
            f"eintragen. Es wurde NICHTS geschrieben."
        ) from exc
    if "<html" in inhalt[:2000].lower():
        raise QuelleUnbrauchbar(
            f"{quelle.index_name}: der Abruf lieferte eine HTML-Seite statt einer "
            f"CSV-Bestandsliste. Die URL zeigt nicht auf den Download.\n"
            f"URL: {url}\nEs wurde NICHTS geschrieben."
        )
    return inhalt


def yahoo_ticker_aus_isin(isin: str) -> str | None:  # pragma: no cover - Netzpfad
    """Reserve-Aufloesung ueber die Yahoo-Suche; nur deutsche Notierungen."""
    request = urllib.request.Request(
        YAHOO_SUCHE.format(isin), headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as antwort:
            daten = json.loads(antwort.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001
        return None
    for treffer in daten.get("quotes", []):
        symbol = str(treffer.get("symbol", ""))
        if symbol.endswith(".DE"):
            return symbol
    return None


def pruefe(kandidaten: list[Kandidat], markt: str) -> tuple[list[Kandidat], list[str]]:
    """Jeden Ticker gegen echte Kursdaten pruefen. Ohne Kurse -> raus, namentlich."""
    import yfinance as yf

    heute = _dt.date.today()
    start = (heute - _dt.timedelta(days=40)).isoformat()
    ok: list[Kandidat] = []
    raus: list[str] = []
    block = 40
    for i in range(0, len(kandidaten), block):
        teil = kandidaten[i : i + block]
        symbole = [k.ticker for k in teil]
        try:
            frame = yf.download(
                tickers=symbole,
                start=start,
                auto_adjust=False,
                actions=False,
                progress=False,
                group_by="ticker",
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001
            raus.extend(f"{k.ticker} ({k.name}): Abruf fehlgeschlagen {exc}" for k in teil)
            continue
        for kandidat in teil:
            if markt == "de" and not kandidat.ticker.endswith(".DE"):
                raus.append(f"{kandidat.ticker} ({kandidat.name}): keine deutsche Notierung")
                continue
            try:
                sub = frame if len(teil) == 1 else frame[kandidat.ticker]
                spalte = sub["Adj Close"].dropna()
            except Exception:  # noqa: BLE001
                spalte = None
            if spalte is None or spalte.empty:
                raus.append(f"{kandidat.ticker} ({kandidat.name}): keine Kurse")
                continue
            ok.append(kandidat)
    return ok, raus


# --------------------------------------------------------------------------
# Ablauf
# --------------------------------------------------------------------------


def zusammenfassung(text: str) -> None:
    print(text)
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if pfad:
        with open(pfad, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def sammle(markt: str, heute: _dt.date) -> tuple[Befund, str, str, str]:  # pragma: no cover
    if markt == "us":
        return (
            parse_us(lade(QUELLE_US)),
            "S&P 500",
            f"Wikipedia (englisch) „List of S&P 500 companies“ ({QUELLE_US})",
            "universe/universe_us.txt",
        )
    befunde = []
    for quelle in ISHARES_DE:
        befund = parse_ishares_holdings(
            lade_bestandsliste(quelle),
            quelle.index_name,
            heute=heute,
            isin_resolver=yahoo_ticker_aus_isin,
        )
        unten, oben = ANZAHL_ERWARTET[quelle.index_name]
        zusammenfassung(
            f"- {quelle.index_name} ({quelle.xetra}): "
            f"**{befund.aktien_zeilen}** Aktien-Zeilen (erwartet {unten}–{oben}), "
            f"davon {len(befund.kandidaten)} mit Ticker, "
            f"Bestands-Stichtag **{befund.bestand_stand}**"
        )
        befunde.append(befund)
    return (
        vereinige(befunde),
        "HDAX (DAX + MDAX + TecDAX)",
        "Taegliche Bestandslisten der iShares-ETFs EXS1 (DAX), EXS3 (MDAX) "
        "und EXS2 (TecDAX), physisch replizierend",
        "universe/universe_de.txt",
    )


def verarbeite(markt: str, heute: _dt.date, lauf: str, stand: str) -> bool:  # pragma: no cover
    """Einen Markt vollstaendig verarbeiten. True = geschrieben."""
    unten, oben = ERWARTET[markt]
    zusammenfassung(f"\n## Universum {markt.upper()}\n")

    befund, bezeichnung, herkunft, pfad = sammle(markt, heute)
    zusammenfassung(f"\n- aus der Quelle gelesen: **{len(befund.kandidaten)}** (nach Dedup)")
    if befund.bestand_stand:
        zusammenfassung(f"- aeltester Bestands-Stichtag: **{befund.bestand_stand}**")
    if befund.nicht_aktien:
        zusammenfassung(
            f"- {befund.nicht_aktien} Zeilen ohne Anlageklasse Aktie uebersprungen "
            f"(Bargeld, Derivate, Geldmarkt)"
        )
    if befund.ueber_reserve:
        zusammenfassung(f"\n**Ueber die ISIN-Reserve aufgeloest ({len(befund.ueber_reserve)}):**\n")
        for eintrag in sorted(befund.ueber_reserve):
            zusammenfassung(f"  - {eintrag}")
    if befund.ungeloest:
        zusammenfassung(f"\n**Gar nicht aufgeloest ({len(befund.ungeloest)}):**\n")
        for eintrag in sorted(set(befund.ungeloest)):
            zusammenfassung(f"  - {eintrag}")

    geprueft, raus = pruefe(befund.kandidaten, markt)
    zusammenfassung(f"\n- nach Kurspruefung uebrig: **{len(geprueft)}**")
    zusammenfassung(f"- erwarteter Bereich: {unten}–{oben}")
    if raus:
        zusammenfassung(f"\n**In der Kurspruefung aussortiert ({len(raus)}):**\n")
        for eintrag in sorted(raus):
            zusammenfassung(f"  - {eintrag}")

    if not (unten <= len(geprueft) <= oben):
        raise QuelleUnbrauchbar(
            f"{len(geprueft)} Titel liegen ausserhalb von {unten}–{oben}. "
            f"Es wurde NICHTS geschrieben — lieber kein Universum als ein halbes. "
            f"Ist die Zahl plausibel und nur die Schranke zu eng, ist sie in "
            f"tools/build_universe.py in der Zeile `ERWARTET` zu weiten."
        )

    with open(pfad, "w", encoding="utf-8") as handle:
        handle.write(rendere_universum(bezeichnung, herkunft, stand, lauf, geprueft))
    zusammenfassung(f"\n`{pfad}` geschrieben, Status VERIFIED.")

    # Beschreibende Angaben im GLEICHEN Vorgang und zum gleichen Zeitpunkt.
    # Sie frieren damit zusammen mit dem Universum ein und koennen gar nicht
    # auseinanderlaufen. Reine Anzeige -- kein Score, kein Ranking.
    meta_pfad = f"universe/ticker_meta_{markt}.json"
    with open(meta_pfad, "w", encoding="utf-8") as handle:
        handle.write(dump_meta(meta_aus_kandidaten(geprueft)))
    mit_sektor = sum(1 for k in geprueft if k.sektor)
    zusammenfassung(
        f"`{meta_pfad}` geschrieben: {len(geprueft)} Eintraege, "
        f"davon {mit_sektor} mit Sektor."
    )
    return True


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - Netzpfad
    parser = argparse.ArgumentParser(description="Universums-Listen erzeugen")
    parser.add_argument("markt", choices=["us", "de", "beide"])
    parser.add_argument("--heute", help="Laufdatum JJJJ-MM-TT (nur fuer Tests)")
    args = parser.parse_args(argv)
    maerkte = ["us", "de"] if args.markt == "beide" else [args.markt]
    heute = _dt.date.fromisoformat(args.heute) if args.heute else _dt.date.today()
    lauf = os.environ.get("GITHUB_RUN_URL", "manuell")
    stand = heute.isoformat()

    fehler: list[str] = []
    for markt in maerkte:
        # Jeder Markt fuer sich: ein unbrauchbarer Markt darf den anderen
        # NICHT mitreissen. Genau das ist im ersten Lauf passiert.
        try:
            verarbeite(markt, heute, lauf, stand)
        except QuelleUnbrauchbar as exc:
            zusammenfassung(f"\n**ABBRUCH {markt.upper()}:** {exc}")
            fehler.append(markt)
        except Exception as exc:  # noqa: BLE001
            zusammenfassung(f"\n**ABBRUCH {markt.upper()}:** unerwartet: {exc}")
            fehler.append(markt)

    if fehler:
        zusammenfassung(
            f"\nFehlgeschlagen: {', '.join(m.upper() for m in fehler)}. "
            f"Erfolgreiche Maerkte wurden trotzdem geschrieben und werden "
            f"vom Workflow committet."
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
