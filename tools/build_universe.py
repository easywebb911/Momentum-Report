"""Universums-Listen aus dokumentierter Quelle erzeugen — bewusst manuell.

Laeuft NUR in GitHub Actions ueber den Workflow "Universum aktualisieren"
(workflow_dispatch), nie automatisch. Grund: das Universum darf sich nicht
unbemerkt unter einem laufenden Ranking wegdrehen.

Vorgehen und Sicherungen:
  1. Mitgliederliste aus der Quelle holen (Wikipedia-Listenartikel)
  2. auf Yahoo-Ticker abbilden
  3. JEDEN Ticker gegen die Kursquelle pruefen — was keine Kurse liefert,
     fliegt raus und wird namentlich im Lauf-Protokoll genannt
  4. Plausibilitaets-Schranke: liegt die Anzahl ausserhalb des erwarteten
     Bereichs, wird NICHTS geschrieben und der Lauf faellt durch
  5. Datei mit Herkunft, Stand-Datum und Lauf-URL im Kopf schreiben

Nichts davon faellt still zurueck. Im Zweifel lieber kein Universum als
ein halbes.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import os
import re
import sys
import urllib.request
from dataclasses import dataclass

USER_AGENT = (
    "Momentum-Report/0.1 (+https://github.com/easywebb911/Momentum-Report) "
    "python-urllib"
)

QUELLE_US = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
QUELLEN_DE = {
    "DAX": "https://de.wikipedia.org/wiki/DAX",
    "MDAX": "https://de.wikipedia.org/wiki/MDAX",
    "TecDAX": "https://de.wikipedia.org/wiki/TecDAX",
}

# Plausibilitaets-Schranken. Ausserhalb: Abbruch statt Halbergebnis.
ERWARTET = {"us": (470, 520), "de": (80, 115)}

YAHOO_SUCHE = "https://query2.finance.yahoo.com/v1/finance/search?q={}&quotesCount=8"


@dataclass
class Kandidat:
    ticker: str
    name: str
    herkunft: str = ""


def _lade(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as antwort:
        return antwort.read().decode("utf-8", "replace")


def _tabellen(html: str):
    import pandas as pd

    return pd.read_html(io.StringIO(html))


def _spalte(frame, *namen):
    for name in namen:
        for spalte in frame.columns:
            if str(spalte).strip().lower() == name.lower():
                return spalte
    return None


# --------------------------------------------------------------------------
# USA
# --------------------------------------------------------------------------


def kandidaten_us() -> list[Kandidat]:
    html = _lade(QUELLE_US)
    for frame in _tabellen(html):
        symbol = _spalte(frame, "Symbol")
        name = _spalte(frame, "Security", "Company")
        if symbol is None or name is None:
            continue
        out = []
        for _, zeile in frame.iterrows():
            roh = str(zeile[symbol]).strip()
            if not roh or roh.lower() == "nan":
                continue
            # Yahoo schreibt Klassen-Ticker mit Bindestrich: BRK.B -> BRK-B
            out.append(Kandidat(roh.replace(".", "-"), str(zeile[name]).strip()))
        if len(out) > 400:
            return out
    raise SystemExit("Quelle US: keine brauchbare Mitgliedertabelle gefunden.")


# --------------------------------------------------------------------------
# Deutschland (HDAX = DAX + MDAX + TecDAX, Vereinigungsmenge)
# --------------------------------------------------------------------------


def _yahoo_ticker_aus_isin(isin: str) -> str | None:
    """Yahoo-Ticker ueber die ISIN aufloesen; nur deutsche Notierungen."""
    import json

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


def kandidaten_de() -> list[Kandidat]:
    gefunden: dict[str, Kandidat] = {}
    ungeloest: list[str] = []
    for index_name, url in QUELLEN_DE.items():
        html = _lade(url)
        for frame in _tabellen(html):
            name_spalte = _spalte(frame, "Name", "Unternehmen")
            isin_spalte = _spalte(frame, "ISIN")
            symbol_spalte = _spalte(frame, "Symbol", "Ticker", "Kürzel", "Kuerzel")
            if name_spalte is None or (isin_spalte is None and symbol_spalte is None):
                continue
            if len(frame) < 20:
                continue
            for _, zeile in frame.iterrows():
                name = str(zeile[name_spalte]).strip()
                if not name or name.lower() == "nan":
                    continue
                ticker = None
                if symbol_spalte is not None:
                    roh = str(zeile[symbol_spalte]).strip().upper()
                    roh = re.sub(r"^(ETR|XETRA|FWB)[:\s]+", "", roh)
                    if re.fullmatch(r"[A-Z0-9]{2,6}", roh):
                        ticker = f"{roh}.DE"
                if ticker is None and isin_spalte is not None:
                    isin = str(zeile[isin_spalte]).strip().upper()
                    if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", isin):
                        ticker = _yahoo_ticker_aus_isin(isin)
                if ticker is None:
                    ungeloest.append(f"{index_name}: {name}")
                    continue
                gefunden.setdefault(ticker, Kandidat(ticker, name, index_name))
            break
    if ungeloest:
        print("\nNICHT AUFGELOEST (kein Yahoo-Ticker ermittelbar):")
        for eintrag in sorted(set(ungeloest)):
            print(f"  - {eintrag}")
    if not gefunden:
        raise SystemExit("Quelle DE: keine brauchbare Mitgliedertabelle gefunden.")
    return sorted(gefunden.values(), key=lambda k: k.ticker)


# --------------------------------------------------------------------------
# Pruefung gegen die Kursquelle
# --------------------------------------------------------------------------


def pruefe(kandidaten: list[Kandidat], markt: str) -> tuple[list[Kandidat], list[str]]:
    """Jeden Ticker gegen Yahoo pruefen. Ohne Kurse -> raus, aber namentlich."""
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
            try:
                sub = frame if len(teil) == 1 else frame[kandidat.ticker]
                spalte = sub["Adj Close"].dropna()
            except Exception:  # noqa: BLE001
                spalte = None
            if spalte is None or spalte.empty:
                raus.append(f"{kandidat.ticker} ({kandidat.name}): keine Kurse")
                continue
            if markt == "de" and not kandidat.ticker.endswith(".DE"):
                raus.append(f"{kandidat.ticker} ({kandidat.name}): keine deutsche Notierung")
                continue
            ok.append(kandidat)
    return ok, raus


# --------------------------------------------------------------------------
# Schreiben
# --------------------------------------------------------------------------


def schreibe(pfad: str, bezeichnung: str, herkunft: str, kandidaten: list[Kandidat]) -> None:
    lauf = os.environ.get("GITHUB_RUN_URL", "manuell")
    zeilen = [
        f"# Universum: {bezeichnung}",
        f"# Herkunft: {herkunft}",
        f"# Stand: {_dt.date.today().isoformat()}",
        f"# Erzeugt von: .github/workflows/universum.yml (Lauf {lauf})",
        "# Jeder Ticker wurde beim Erzeugen gegen die Kursquelle geprueft.",
        "# Aktualisierung ist ein bewusster manueller Vorgang.",
        "#",
        "# Format: TICKER<TAB>Firmenname",
    ]
    zeilen += [f"{k.ticker}\t{k.name}" for k in sorted(kandidaten, key=lambda k: k.ticker)]
    with open(pfad, "w", encoding="utf-8") as handle:
        handle.write("\n".join(zeilen) + "\n")


def zusammenfassung(text: str) -> None:
    print(text)
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if pfad:
        with open(pfad, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Universums-Listen erzeugen")
    parser.add_argument("markt", choices=["us", "de", "beide"])
    args = parser.parse_args(argv)
    maerkte = ["us", "de"] if args.markt == "beide" else [args.markt]

    fehler = False
    for markt in maerkte:
        if markt == "us":
            kandidaten = kandidaten_us()
            bezeichnung = "S&P 500"
            herkunft = f"Wikipedia „List of S&P 500 companies“ ({QUELLE_US})"
            pfad = "universe/universe_us.txt"
        else:
            kandidaten = kandidaten_de()
            bezeichnung = "HDAX (DAX + MDAX + TecDAX)"
            herkunft = "Wikipedia-Listenartikel DAX, MDAX, TecDAX (de.wikipedia.org)"
            pfad = "universe/universe_de.txt"

        geprueft, raus = pruefe(kandidaten, markt)
        unten, oben = ERWARTET[markt]

        zusammenfassung(f"\n## Universum {markt.upper()}\n")
        zusammenfassung(f"- aus der Quelle gelesen: **{len(kandidaten)}**")
        zusammenfassung(f"- nach Kurspruefung uebrig: **{len(geprueft)}**")
        zusammenfassung(f"- erwarteter Bereich: {unten}–{oben}")
        if raus:
            zusammenfassung(f"\n**Aussortiert ({len(raus)}):**\n")
            for eintrag in sorted(raus):
                zusammenfassung(f"  - {eintrag}")

        if not (unten <= len(geprueft) <= oben):
            zusammenfassung(
                f"\n**ABBRUCH:** {len(geprueft)} Titel liegen ausserhalb von "
                f"{unten}–{oben}. Es wurde NICHTS geschrieben — lieber kein "
                f"Universum als ein halbes."
            )
            fehler = True
            continue

        schreibe(pfad, bezeichnung, herkunft, geprueft)
        zusammenfassung(f"\n`{pfad}` geschrieben.")

    return 1 if fehler else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
