"""Die iShares-Bestandslisten: abrufen, lesen, an den Gattern pruefen.

WARUM DIESE DATEI EXISTIERT (und der Code nicht mehr in tools/ liegt):
Seit dem DE-Kursvergleich braucht nicht nur das Universums-Werkzeug diese
Dateien, sondern auch der Lauf selbst -- er stellt am Stichtag die
Kurs-Spalte der Bestandslisten gegen die Kursquelle. Beide muessen
zwingend DENSELBEN Parser benutzen. Ein zweiter, "kleiner" Leser fuer den
Lauf waere die schlimmste Sorte Fehler: er wuerde einen anderen Vertrag
pruefen als den, an dem das Universum haengt, und dabei aussehen wie
Sicherheit. (Derselbe Grundsatz traegt schon den Vertragstest, siehe
tools/vertragstest.py.)

Der Umzug hierher ist ein reiner Umzug: `tools/build_universe.py`
reicht jeden Namen unveraendert weiter, und keine einzige Testzeile
musste angefasst werden.

WAS HIER GEPRUEFT WIRD, in dieser Reihenfolge:
  1. Bestands-Stichtag aus dem Vorspann; aelter als 10 Handelstage
     -> Abbruch (VERALTUNGS-GATTER)
  2. nur Zeilen der Anlageklasse Aktie; Cash, Futures, Geldmarkt raus
  3. Anzahl der Aktien-Zeilen gegen den erwarteten Bereich des Index
     (ANZAHL-GATTER) -- faengt eine vertauschte URL ab
  4. Ticker-Spalte lesen; fehlt der Ticker, ISIN-Reserve

Jeder Abbruch ist ein `QuelleUnbrauchbar` und damit fuer den Lauf, das
Universums-Werkzeug und den Vertragstest gleichermassen erkennbar.
"""

from __future__ import annotations

import csv
import datetime as _dt
import os
import re
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = (
    "Momentum-Report/0.1 (+https://github.com/easywebb911/Momentum-Report) "
    "python-urllib"
)

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
# Bestands-Stichtag 31. Juli 2026. Am 09.08.2026 hat der Vertragstest auf
# dem Runner alle drei erneut gelesen (Stichtag 06.08.2026, 40/50/30
# Aktien-Zeilen). Der Egress-Proxy der Bau-Sitzung blockt ishares.com,
# hier konnte also nie etwas nachgeprueft werden.
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

# Der BlackRock-Bewertungskurs je Titel. "Kurs" steht woertlich in der
# extern verifizierten Kopfzeile der echten deutschen Dateien (02.08.2026);
# "price" ist der englische Zwilling derselben Dateifamilie und steht hier
# aus demselben Grund wie "security" neben "name" -- nicht weil er belegt
# waere, sondern damit die englische Fassung nicht an einem Wort scheitert.
KURS_SPALTEN = ("kurs", "price", "preis")
# Ebenfalls woertlich aus der verifizierten Kopfzeile: "Marktwährung".
WAEHRUNG_SPALTEN = ("marktwährung", "marktwaehrung", "market currency", "währung",
                    "waehrung", "currency")

# Nur diese Anlageklassen sind Aktien. Alles andere (Bargeld, Derivate,
# Geldmarkt, Futures) gehoert nicht ins Universum.
AKTIEN_KLASSEN = {"equity", "equities", "aktien", "aktie", "stock", "stocks"}

# Xetra-Kuerzel: 2-6 Zeichen, Ziffern erlaubt (1COV), auch fuehrend.
XETRA_MUSTER = re.compile(r"^[A-Z0-9]{2,6}$")
ISIN_MUSTER = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
PRAEFIX_MUSTER = re.compile(r"^(ETR|XETR|XETRA|FWB|FRA|DE)[:\s]+")

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
    # Der Bewertungskurs aus der Bestandsliste. Er geht AUSDRUECKLICH in
    # keinen Score und in keine Kursreihe ein -- er dient allein dem
    # Vergleich gegen die Kursquelle (siehe momentum/kursvergleich.py).
    kurs: float | None = None
    waehrung: str = ""


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
    # Wie die Kurs-Spalte ihre Zahlen schreibt: "komma" (1.234,56),
    # "punkt" (1,234.56) oder None = nicht entscheidbar. Bei None bleibt
    # jeder `Kandidat.kurs` leer -- lieber kein Vergleich als ein Vergleich
    # gegen eine falsch gelesene Zahl.
    kurs_konvention: str | None = None


# --------------------------------------------------------------------------
# Reine Funktionen: nehmen Dateiinhalt entgegen, kein Netz. So sind sie testbar.
# --------------------------------------------------------------------------


def xetra_zu_yahoo(symbol: str) -> str | None:
    """Xetra-Kuerzel in einen Yahoo-Ticker uebersetzen. None, wenn unbrauchbar."""
    roh = PRAEFIX_MUSTER.sub("", symbol.strip().upper())
    roh = roh.replace(" ", "")
    if not XETRA_MUSTER.match(roh):
        return None
    return f"{roh}.DE"


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
    # 31.Jul.2026 / 06.Aug.2026 / 31-Jul-2026 / 31. Juli 2026 / 31.Juli2026
    #
    # Der Trenner VOR dem Jahr ist ausdruecklich freigestellt: die echten
    # deutschen iShares-Dateien schreiben mal "31.Juli2026" (ganz ohne),
    # mal "06.Aug.2026" (abgekuerzt, mit Punkt). Genau an der ersten Form
    # ist der Lauf vom 02.08.2026 gescheitert. Der Monatsname wird ueber
    # seine ersten drei Zeichen aufgeloest, damit alle zwoelf Namen in
    # ausgeschriebener UND abgekuerzter Form ohne eigene Liste greifen.
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


# ------------------------------------------------------- Die Kurs-Spalte
#
# Zahlen aus einer Fremddatei zu lesen ist genau dann gefaehrlich, wenn man
# raet. "1,234" ist im deutschen Format 1,234 und im englischen 1234 --
# derselbe Text, ein Faktor 1000 Unterschied. Weil an diesen Zahlen ein
# Gatter haengt, das einen Monats-Stichtag verweigern kann, wird hier
# NICHT geraten: was nicht eindeutig ist, bleibt leer.
#
# Die Eindeutigkeit wird fuer die GANZE Datei einmal entschieden. Jede
# Zelle, die beide Trenner traegt ("1.234,56") oder deren einziger Trenner
# nicht genau drei Ziffern hinter sich hat ("123,45"), ist fuer sich
# eindeutig und gibt eine Stimme ab. Widersprechen sich die Stimmen, gilt
# die Datei als nicht lesbar.


def _stimme(roh: str) -> str | None:
    """Welches Zeichen ist in DIESER Zelle nachweislich das Dezimaltrennzeichen?"""
    hat_komma, hat_punkt = "," in roh, "." in roh
    if hat_komma and hat_punkt:
        return "komma" if roh.rfind(",") > roh.rfind(".") else "punkt"
    for zeichen, name in ((",", "komma"), (".", "punkt")):
        if roh.count(zeichen) == 1 and len(roh.split(zeichen)[1]) != 3:
            return name
    return None


def kurs_konvention(rohwerte: list[str]) -> str | None:
    """Wie schreibt diese Datei ihre Kurse? "komma", "punkt" oder None."""
    stimmen = {_stimme(w) for w in rohwerte if w}
    stimmen.discard(None)
    return stimmen.pop() if len(stimmen) == 1 else None


def _zahl(roh: str, konvention: str | None) -> float | None:
    """Eine Kurs-Zelle in eine Zahl -- oder None, wenn irgendetwas unklar ist."""
    if konvention is None:
        return None
    # \u00a0 = geschuetztes Leerzeichen; iShares setzt es als Tausender-
    # trennung ein, und es ist im Editor von einem normalen nicht zu
    # unterscheiden.
    roh = roh.strip().strip('"').replace("\u00a0", "").replace(" ", "")
    if not roh or not re.fullmatch(r"[-+]?[\d.,]+", roh):
        return None
    if konvention == "komma":
        roh = roh.replace(".", "").replace(",", ".")
    else:
        roh = roh.replace(",", "")
    try:
        wert = float(roh)
    except ValueError:
        return None
    # Ein Kurs von null oder darunter ist kein Kurs, sondern eine Luecke.
    return wert if wert > 0 else None


# ------------------------------------------------------------- Die Gatter


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


# --------------------------------------------------------------- Der Parser


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

    # Die Zahlenschreibweise EINMAL fuer die ganze Datei entscheiden.
    befund.kurs_konvention = kurs_konvention(
        [feld(roh, KURS_SPALTEN) for roh in aktien]
    )

    for roh in aktien:
        name = feld(roh, NAME_SPALTEN)
        sektor = feld(roh, SEKTOR_SPALTEN)
        kurs = _zahl(feld(roh, KURS_SPALTEN), befund.kurs_konvention)
        waehrung = feld(roh, WAEHRUNG_SPALTEN).upper()
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
                                 sektor=sektor, kurs=kurs, waehrung=waehrung)
                    )
                    continue
            befund.ungeloest.append(
                f"{erwarteter_index}: {name} (kein Ticker ermittelbar)"
            )
            continue
        befund.kandidaten.append(
            Kandidat(ticker, name, erwarteter_index, sektor=sektor,
                     kurs=kurs, waehrung=waehrung)
        )

    if not befund.kandidaten:
        raise QuelleUnbrauchbar(
            f"{quelle}: {befund.aktien_zeilen} Aktien-Zeilen gelesen, aber aus "
            f"keiner einzigen liess sich ein Ticker gewinnen. "
            f"Es wurde NICHTS geschrieben."
        )
    return befund


# --------------------------------------------------------------------------
# Netz
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
