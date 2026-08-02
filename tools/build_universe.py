"""Universums-Listen aus dokumentierter Quelle erzeugen — bewusst manuell.

Laeuft NUR ueber den Workflow "Universum aktualisieren" (workflow_dispatch),
nie automatisch. Das Universum darf sich nicht unbemerkt unter einem
laufenden Ranking wegdrehen.

QUELLEN (alle englischsprachige Wikipedia — dort fuehren die Tabellen eine
Symbol-Spalte mit Xetra-Kuerzeln, die deutschsprachigen tun das nicht):
  USA:          "List of S&P 500 companies", Spalte "Symbol"
  Deutschland:  "DAX", "MDAX", "TecDAX", jeweils die Komponenten-Tabelle;
                HDAX = Vereinigung der drei, Doppelmitglieder genau einmal

ANNAHME ZUM ".DE"-SUFFIX (ausdruecklich benannt, nicht stillschweigend):
Yahoo-Ticker = Xetra-Symbol + ".DE". Vorzugsaktien brauchen KEINE
Sonderbehandlung, weil das Xetra-Symbol die Gattung bereits traegt --
VOW3 (Volkswagen Vz.), HEN3 (Henkel Vz.), SRT3 (Sartorius Vz.), FPE3
(Fuchs Vz.) werden zu VOW3.DE, HEN3.DE, SRT3.DE, FPE3.DE und treffen
damit genau die Vorzugsgattung. Symbole mit fuehrender Ziffer (1COV) sind
zugelassen. Titel ohne Xetra-Notierung oder mit abweichendem Yahoo-Symbol
fallen in der Kurspruefung heraus und werden dort NAMENTLICH genannt --
sie verschwinden nie stillschweigend.

SICHERUNGEN, in dieser Reihenfolge:
  1. Symbol-Spalte lesen; fehlt sie fuer einen Titel, greift ersatzweise
     die ISIN-Aufloesung ueber die Yahoo-Suche -- jede solche Aufloesung
     wird namentlich ins Lauf-Log geschrieben
  2. Vereinigung der drei deutschen Listen, Doppelmitglieder genau einmal
  3. JEDER Ticker wird gegen echte Kursdaten geprueft; Aussortierte werden
     namentlich genannt
  4. Plausibilitaets-Schranke: liegt die Anzahl ausserhalb des erwarteten
     Bereichs, wird NICHTS geschrieben und der Lauf faellt durch
  5. Erst dann wird die Datei geschrieben -- mit "# STATUS: VERIFIED".
     Diese Zeile ist der einzige Weg, wie ein Universum ueberhaupt
     rechenbar wird (momentum/universe.py arbeitet default-deny).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = (
    "Momentum-Report/0.1 (+https://github.com/easywebb911/Momentum-Report) "
    "python-urllib"
)

QUELLE_US = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
QUELLEN_DE = {
    "DAX": "https://en.wikipedia.org/wiki/DAX",
    "MDAX": "https://en.wikipedia.org/wiki/MDAX",
    "TecDAX": "https://en.wikipedia.org/wiki/TecDAX",
}

# Plausibilitaets-Schranken. Ausserhalb: Abbruch statt Halbergebnis.
#
# DE: HDAX = DAX (40) + MDAX (50) + TecDAX (30) = 120 Eintraege vor Abzug
# der Doppelmitglieder; TecDAX-Werte sind seit 2018 zugleich in DAX oder
# MDAX. Der Auftrag setzt 110-125 nach Dedup. ACHTUNG: faellt die echte
# Vereinigungsmenge knapp darunter, schreibt der Lauf bewusst nichts --
# dann ist HIER die eine Zeile zu weiten, nirgends sonst.
ERWARTET = {"us": (495, 510), "de": (110, 125)}

# Spaltennamen, unter denen die Quellen das Boersenkuerzel fuehren.
SYMBOL_SPALTEN = ("symbol", "ticker", "ticker symbol", "code", "trading symbol")
NAME_SPALTEN = ("security", "company", "name", "company name")
ISIN_SPALTEN = ("isin",)

# Xetra-Kuerzel: 2-6 Zeichen, Ziffern erlaubt (1COV), auch fuehrend.
XETRA_MUSTER = re.compile(r"^[A-Z0-9]{2,6}$")
ISIN_MUSTER = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
PRAEFIX_MUSTER = re.compile(r"^(ETR|XETR|XETRA|FWB|FRA|DE)[:\s]+")

YAHOO_SUCHE = "https://query2.finance.yahoo.com/v1/finance/search?q={}&quotesCount=8"


@dataclass
class Kandidat:
    ticker: str
    name: str
    herkunft: str = ""
    ueber_reserve: bool = False


@dataclass
class Befund:
    """Was ein Parse-Durchgang ergeben hat -- inklusive aller Randfaelle."""

    kandidaten: list[Kandidat] = field(default_factory=list)
    ueber_reserve: list[str] = field(default_factory=list)
    ungeloest: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Reine Funktionen: nehmen HTML entgegen, kein Netz. So sind sie testbar.
# --------------------------------------------------------------------------


def tabellen(html: str):
    import pandas as pd

    return pd.read_html(io.StringIO(html))


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
    for frame in tabellen(html):
        symbol_spalte = _spalte(frame, SYMBOL_SPALTEN)
        name_spalte = _spalte(frame, NAME_SPALTEN)
        if symbol_spalte is None or name_spalte is None:
            continue
        lauf = Befund()
        for _, zeile in frame.iterrows():
            symbol = _text(zeile, symbol_spalte)
            name = _text(zeile, name_spalte)
            if not symbol:
                if name:
                    lauf.ungeloest.append(f"S&P 500: {name} (kein Symbol)")
                continue
            lauf.kandidaten.append(
                Kandidat(symbol.replace(".", "-"), name or symbol, "S&P 500")
            )
        # Die groesste passende Tabelle gewinnt -- Artikel enthalten daneben
        # kleinere Tabellen (Zu- und Abgaenge), die zufaellig dieselben
        # Spaltennamen tragen koennen.
        if bester is None or len(lauf.kandidaten) > len(bester.kandidaten):
            bester = lauf
    if bester is not None:
        return bester
    raise SystemExit(
        "Quelle US: keine Mitgliedertabelle mit Symbol- und Namensspalte gefunden. "
        "Vermutlich hat sich der Aufbau des Wikipedia-Artikels geaendert -- "
        "es wurde NICHTS geschrieben."
    )


def parse_de_index(html: str, index_name: str, isin_resolver=None) -> Befund:
    """Komponenten eines deutschen Index aus dem englischen Artikel.

    `isin_resolver` ist die Reserve fuer Titel ohne Symbol-Spalte und wird
    injiziert -- damit laufen die Tests ohne Netz.

    Zwei verschiedene Fehlerbilder, bewusst getrennt:
      * gar keine passende Tabelle -> SystemExit (der Artikelaufbau hat sich
        geaendert; darauf darf nichts aufgebaut werden)
      * Tabelle da, aber kein Titel aufloesbar -> normaler Befund mit
        gefuellter Liste `ungeloest`; die Namen gehoeren ins Protokoll,
        und die Plausibilitaets-Schranke bricht danach ohnehin ab
    """
    bester: Befund | None = None
    for frame in tabellen(html):
        symbol_spalte = _spalte(frame, SYMBOL_SPALTEN)
        name_spalte = _spalte(frame, NAME_SPALTEN)
        isin_spalte = _spalte(frame, ISIN_SPALTEN)
        if name_spalte is None or (symbol_spalte is None and isin_spalte is None):
            continue
        lauf = Befund()
        for _, zeile in frame.iterrows():
            name = _text(zeile, name_spalte)
            if not name:
                continue
            ticker = None
            if symbol_spalte is not None:
                ticker = xetra_zu_yahoo(_text(zeile, symbol_spalte))
            if ticker is None and isin_spalte is not None and isin_resolver is not None:
                isin = _text(zeile, isin_spalte).upper()
                if ISIN_MUSTER.match(isin):
                    ticker = isin_resolver(isin)
                    if ticker:
                        lauf.ueber_reserve.append(
                            f"{index_name}: {name} — kein Symbol in der Tabelle, "
                            f"ueber ISIN {isin} aufgeloest zu {ticker}"
                        )
                        lauf.kandidaten.append(
                            Kandidat(ticker, name, index_name, ueber_reserve=True)
                        )
                        continue
            if ticker is None:
                lauf.ungeloest.append(f"{index_name}: {name} (kein Ticker ermittelbar)")
                continue
            lauf.kandidaten.append(Kandidat(ticker, name, index_name))
        if bester is None or len(lauf.kandidaten) > len(bester.kandidaten):
            bester = lauf
    if bester is None:
        raise SystemExit(
            f"Quelle {index_name}: keine brauchbare Komponenten-Tabelle gefunden. "
            f"Vermutlich hat sich der Aufbau des Wikipedia-Artikels geaendert -- "
            f"es wurde NICHTS geschrieben."
        )
    return bester


def vereinige(befunde: list[Befund]) -> Befund:
    """HDAX bilden: Doppelmitglieder genau einmal, Herkunft zusammenfassen."""
    zusammen = Befund()
    nach_ticker: dict[str, Kandidat] = {}
    for befund in befunde:
        zusammen.ueber_reserve.extend(befund.ueber_reserve)
        zusammen.ungeloest.extend(befund.ungeloest)
        for kandidat in befund.kandidaten:
            vorhanden = nach_ticker.get(kandidat.ticker)
            if vorhanden is None:
                nach_ticker[kandidat.ticker] = Kandidat(
                    kandidat.ticker,
                    kandidat.name,
                    kandidat.herkunft,
                    kandidat.ueber_reserve,
                )
                continue
            # Doppelmitglied: nur die Herkunft ergaenzen, kein zweiter Eintrag.
            teile = vorhanden.herkunft.split(", ") if vorhanden.herkunft else []
            if kandidat.herkunft and kandidat.herkunft not in teile:
                teile.append(kandidat.herkunft)
                vorhanden.herkunft = ", ".join(teile)
    zusammen.kandidaten = sorted(nach_ticker.values(), key=lambda k: k.ticker)
    return zusammen


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


def lade(url: str) -> str:  # pragma: no cover - echter Netzpfad
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as antwort:
        return antwort.read().decode("utf-8", "replace")


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


def sammle(markt: str) -> tuple[Befund, str, str, str]:  # pragma: no cover - Netzpfad
    if markt == "us":
        return (
            parse_us(lade(QUELLE_US)),
            "S&P 500",
            f"Wikipedia (englisch) „List of S&P 500 companies“ ({QUELLE_US})",
            "universe/universe_us.txt",
        )
    befunde = [
        parse_de_index(lade(url), name, isin_resolver=yahoo_ticker_aus_isin)
        for name, url in QUELLEN_DE.items()
    ]
    return (
        vereinige(befunde),
        "HDAX (DAX + MDAX + TecDAX)",
        "Wikipedia (englisch), Komponenten-Tabellen der Artikel DAX, MDAX, TecDAX",
        "universe/universe_de.txt",
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - Netzpfad
    parser = argparse.ArgumentParser(description="Universums-Listen erzeugen")
    parser.add_argument("markt", choices=["us", "de", "beide"])
    args = parser.parse_args(argv)
    maerkte = ["us", "de"] if args.markt == "beide" else [args.markt]
    lauf = os.environ.get("GITHUB_RUN_URL", "manuell")
    stand = _dt.date.today().isoformat()

    fehler = False
    for markt in maerkte:
        befund, bezeichnung, herkunft, pfad = sammle(markt)
        unten, oben = ERWARTET[markt]

        zusammenfassung(f"\n## Universum {markt.upper()} — {bezeichnung}\n")
        zusammenfassung(f"- aus der Quelle gelesen: **{len(befund.kandidaten)}** (nach Dedup)")

        if befund.ueber_reserve:
            zusammenfassung(
                f"\n**Ueber die ISIN-Reserve aufgeloest ({len(befund.ueber_reserve)}):**\n"
            )
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
            zusammenfassung(
                f"\n**ABBRUCH:** {len(geprueft)} Titel liegen ausserhalb von "
                f"{unten}–{oben}. Es wurde NICHTS geschrieben — lieber kein "
                f"Universum als ein halbes. Ist die Zahl plausibel und nur die "
                f"Schranke zu eng, ist sie in tools/build_universe.py in der "
                f"Zeile `ERWARTET` zu weiten (eine Zeile, sonst nichts)."
            )
            fehler = True
            continue

        with open(pfad, "w", encoding="utf-8") as handle:
            handle.write(rendere_universum(bezeichnung, herkunft, stand, lauf, geprueft))
        zusammenfassung(f"\n`{pfad}` geschrieben, Status VERIFIED.")

    return 1 if fehler else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
