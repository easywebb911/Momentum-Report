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
        hilft das Veraltungs-Gatter in momentum/ishares.py.

ANNAHME ZUM ".DE"-SUFFIX (ausdruecklich benannt, nicht stillschweigend):
Yahoo-Ticker = Xetra-Symbol + ".DE". Vorzugsaktien brauchen KEINE
Sonderbehandlung, weil das Xetra-Symbol die Gattung bereits traegt --
VOW3 (Volkswagen Vz.), HEN3 (Henkel Vz.), SRT3 (Sartorius Vz.), FPE3
(Fuchs Vz.) werden zu VOW3.DE usw. und treffen damit genau die
Vorzugsgattung. Symbole mit fuehrender Ziffer (1COV) sind zugelassen.
Titel ohne Xetra-Notierung oder mit abweichendem Yahoo-Symbol fallen in
der Kurspruefung heraus und werden dort NAMENTLICH genannt.

SICHERUNGEN, in dieser Reihenfolge:
  1.-4. stecken im gemeinsamen Parser (momentum/ishares.py): Stichtag,
     Anlageklasse, ANZAHL-GATTER, Ticker samt ISIN-Reserve
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
import datetime as _dt
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent / 'src'))
from momentum.meta import dump_meta  # noqa: E402

# --------------------------------------------------------------------------
# DIE DE-QUELLE LIEGT NICHT MEHR HIER, sondern in src/momentum/ishares.py.
#
# Grund: seit dem DE-Kursvergleich liest auch der LAUF die Bestandslisten --
# er stellt am Stichtag ihre Kurs-Spalte gegen die Kursquelle. Lauf,
# Universums-Werkzeug und Vertragstest muessen dabei zwingend denselben
# Parser benutzen; ein zweiter Leser wuerde einen anderen Vertrag pruefen
# als den, an dem das Universum haengt, und dabei aussehen wie Sicherheit.
#
# Die Namen werden hier unveraendert weitergereicht: jeder bestehende
# Aufruf `build_universe.X` funktioniert genau wie vorher. Genau das ist
# der Beleg, dass der Umzug ein reiner Umzug war -- keine Testzeile und
# kein Aufrufer musste angefasst werden.
# --------------------------------------------------------------------------
from momentum.ishares import (  # noqa: E402,F401
    AKTIEN_KLASSEN,
    ANLAGEKLASSE_SPALTEN,
    ANZAHL_ERWARTET,
    ANZAHL_ERWARTET_US,
    ISHARES_DE,
    ISHARES_US,
    ISIN_MUSTER,
    ISIN_SPALTEN,
    KURS_SPALTEN,
    MAX_ALTER_HANDELSTAGE,
    MONATE,
    NAME_SPALTEN,
    PRAEFIX_MUSTER,
    SEKTOR_SPALTEN,
    SYMBOL_SPALTEN,
    USER_AGENT,
    WAEHRUNG_SPALTEN,
    XETRA_MUSTER,
    Befund,
    Bestandsquelle,
    Kandidat,
    QuelleUnbrauchbar,
    _datum_aus_text,
    _kopfzeile_finden,
    _trenner,
    _zahl,
    handelstage_zwischen,
    kurs_konvention,
    lade,
    lade_bestandsliste,
    parse_ishares_holdings,
    pruefe_aktualitaet,
    pruefe_anzahl,
    quellen_url,
    us_symbol_zu_yahoo,
    xetra_zu_yahoo,
)

QUELLE_US = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Plausibilitaets-Schranken fuer das FERTIGE Universum eines Marktes.
# Ausserhalb: Abbruch statt Halbergebnis.
#
# DE: HDAX = DAX (40) + MDAX (50) + TecDAX (30) = 120 Eintraege VOR Abzug der
# Doppelmitglieder. TecDAX-Werte sind seit 2018 zugleich in DAX oder MDAX,
# und wie gross diese Ueberschneidung ausfaellt, aendert sich mit JEDER
# Index-Ueberpruefung der Deutschen Boerse. Die Vereinigungsmenge ist damit
# keine feste Zahl, sondern schwankt -- deshalb der Boden bei 95: eine
# Schranke, die bei jeder zweiten Umstellung anschlaegt, schuetzt nicht,
# sie blockiert nur.
ERWARTET = {"us": (495, 510), "de": (95, 125)}

YAHOO_SUCHE = "https://query2.finance.yahoo.com/v1/finance/search?q={}&quotesCount=8"


# --------------------------------------------------------------------------
# USA: der Wikipedia-Listenartikel. Reine Funktionen, kein Netz.
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


# --------------------------------------------------------------------------
# Zusammenbau
# --------------------------------------------------------------------------


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
                    kandidat.kurs,
                    kandidat.waehrung,
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
# Netz: ISIN-Reserve, Kurspruefung
# --------------------------------------------------------------------------


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
