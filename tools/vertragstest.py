"""VERTRAGSTEST: Halten die vier Fremdquellen noch die Form, von der der
Lauf lebt? Gefragt wird TAGE VOR dem Monats-Stichtag, nicht an ihm.

WARUM ES DAS GIBT
Der Momentum-Lauf braucht vier fremde Quellen, und drei davon sind
Dateien fremder Anbieter ohne Zusage an uns. Bricht eine ihre Form, faellt
das bisher genau dann auf, wenn es am teuersten ist: am Stichtag, an dem
das Monats-Ranking entsteht. Dieser Test fragt stattdessen im Zeitfenster
davor -- ein roter Lauf am 27. ist ein ruhiger Abend, ein roter Lauf am
31. ist ein verlorener Monat.

DER TRAGENDE ENTWURFSGRUNDSATZ: KEINE ZWEIT-IMPLEMENTIERUNG.
Geprueft wird ausschliesslich mit den ECHTEN Parsern und Gattern, von
denen der Lauf lebt -- `parse_us`, `parse_ishares_holdings` samt
ANZAHL- und VERALTUNGS-Gatter, `download_prices`, `parse_ezb_csv`. Ein
nachgebauter Pruefer wuerde einen anderen Vertrag testen als den, der
zaehlt, und waere damit schlimmer als kein Test: er gaebe Sicherheit,
ohne sie zu decken.

WAS ER NICHT TUT
Er schreibt nichts. Kein `data/`, kein `docs/`, kein Commit -- der
Workflow hat `contents: read`. Er rechnet auch kein Ranking: er stellt
nur fest, ob die Zutaten noch die zugesagte Form haben.

STILL IM NORMALFALL (Waechter-Philosophie, siehe waechter.py): Halten
alle Vertraege, endet der Lauf gruen und es geht NICHTS raus. Bricht
mindestens einer: ein roter Lauf UND genau EIN Push mit allen Bruechen
als Liste -- kein Push-Gewitter, wenn ein Anbieter mehrere Dateien
gleichzeitig verhagelt.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_universe import (  # noqa: E402
    ANZAHL_ERWARTET,
    ERWARTET,
    ISHARES_DE,
    MAX_ALTER_HANDELSTAGE,
    QUELLE_US,
    Bestandsquelle,
    QuelleUnbrauchbar,
    handelstage_zwischen,
    lade,
    lade_bestandsliste,
    parse_ishares_holdings,
    parse_us,
    quellen_url,
)
from momentum.config import MARKETS_BY_KEY  # noqa: E402
from momentum.data import download_prices  # noqa: E402
from momentum.notify import push_vertrag_gebrochen  # noqa: E402
from momentum.riskfree import EZB_URL, IRX_TICKER, parse_ezb_csv  # noqa: E402

Date = _dt.date

# --------------------------------------------------------------------------
# Stichproben und Schwellen -- jede mit Begruendung, keine geraten.
# --------------------------------------------------------------------------

# Kleine, feste Stichprobe je Markt. Sie prueft NICHT einzelne Firmen,
# sondern ob die Kursquelle ueberhaupt noch bereinigte Schlusskurse
# liefert. Deshalb genuegt die MEHRHEIT: ein einzelner Titel kann
# umbenannt oder ausgesetzt sein, ohne dass der Vertrag der Quelle bricht.
# Bricht dagegen das Format, liefert keiner mehr etwas.
STICHPROBE = {
    "us": ("AAPL", "MSFT", "JNJ"),
    "de": ("SAP.DE", "SIE.DE", "ALV.DE"),
}
STICHPROBE_MINDESTENS = 2

# Die Index- und Zinsreihen dagegen sind EINZELN tragend: ohne ^GDAXI gibt
# es fuer Deutschland gar keinen Handelskalender und damit keinen Stichtag.
# Hier zaehlt jede einzelne.
TRAGENDE_REIHEN = (
    MARKETS_BY_KEY["us"].index_ticker,
    MARKETS_BY_KEY["de"].index_ticker,
    IRX_TICKER,
)

# €STR erscheint an jedem TARGET2-Geschaeftstag. Fuenf Handelstage lassen
# Feiertagsketten (Ostern, Jahreswechsel) zu, ohne eine echte Stille zu
# verschlucken.
ESTR_MAX_HANDELSTAGE = 5

# Wie weit zurueck die Kursstichprobe geholt wird. Kurz genug, um schnell
# zu sein; lang genug, dass Feiertage kein leeres Fenster ergeben.
KURS_FENSTER_TAGE = 14


@dataclass(frozen=True)
class Verdikt:
    """Ein geprueftes Versprechen einer Quelle."""

    quelle: str      # wer verspricht
    vertrag: str     # was versprochen ist
    ok: bool
    befund: str      # erwartet vs. vorgefunden -- immer, auch bei ok

    def zeile(self) -> str:
        return f"[{'ok ' if self.ok else 'ROT'}] {self.quelle} — {self.vertrag}: {self.befund}"


def log(text: str = "") -> None:
    print(text, flush=True)


# --------------------------------------------------------------------------
# Die vier Vertraege. Reine Funktionen: Inhalt rein, Verdikt raus -- damit
# ohne Netz mit Fixtures pruefbar (tests/unit/test_vertragstest.py).
# --------------------------------------------------------------------------


def pruefe_us_tabelle(html: str) -> Verdikt:
    """Vertrag: Der Artikel traegt eine Mitgliedertabelle mit Symbol-Spalte,
    und ihre Zeilenzahl passt zu einem S&P 500."""
    unten, oben = ERWARTET["us"]
    try:
        befund = parse_us(html)
    except Exception as exc:  # noqa: BLE001 - siehe Begruendung
        # Bewusst JEDE Ausnahme, nicht nur QuelleUnbrauchbar: ein Parser,
        # der auf einer Fremdseite anders als geplant abbricht, hat den
        # Vertrag genauso gebrochen wie einer, der sauber ablehnt.
        # Konkret beobachtet: enthaelt die Seite ueberhaupt keine Tabelle,
        # kommt aus pandas ein ImportError (html5lib-Rueckfall) statt
        # QuelleUnbrauchbar. Der Vertragstest darf daran nicht selbst
        # zerschellen -- die Ursache gehoert in einen eigenen PR am
        # Universums-Parser, nicht hierher.
        return Verdikt(
            "Wikipedia S&P 500", "Mitgliedertabelle mit Symbol-Spalte", False,
            f"erwartet: parsebare Tabelle — vorgefunden: {type(exc).__name__}: {exc}",
        )
    anzahl = len(befund.kandidaten)
    if not unten <= anzahl <= oben:
        return Verdikt(
            "Wikipedia S&P 500", f"Anzahl im Bereich {unten}–{oben}", False,
            f"erwartet: {unten}–{oben} Titel — vorgefunden: {anzahl}",
        )
    return Verdikt(
        "Wikipedia S&P 500", f"Tabelle parsebar, Anzahl {unten}–{oben}", True,
        f"{anzahl} Titel mit Symbol",
    )


def pruefe_ishares(inhalt: str, quelle: Bestandsquelle, heute: Date) -> Verdikt:
    """Vertrag: Die Bestandsliste laedt, traegt einen jungen Stichtag und
    die zum Index passende Zahl von Aktien-Zeilen.

    Alle drei Bedingungen prueft `parse_ishares_holdings` selbst -- genau
    dieselben Gatter, die den Universums-Lauf abbrechen lassen. Der
    ISIN-Rueckfall bleibt hier bewusst AUS: er wuerde je Zeile eine
    Yahoo-Suche ausloesen und den Vertragstest zu einem Lasttest machen.
    Fuer die Frage "haelt die Datei ihre Form" ist er ohne Belang.
    """
    unten, oben = ANZAHL_ERWARTET[quelle.index_name]
    vertrag = (
        f"Stichtag ≤ {MAX_ALTER_HANDELSTAGE} Handelstage alt, "
        f"{unten}–{oben} Aktien-Zeilen, Ticker-Spalte traegt"
    )
    try:
        befund = parse_ishares_holdings(inhalt, quelle.index_name, heute=heute)
    except QuelleUnbrauchbar as exc:
        return Verdikt(f"iShares {quelle.xetra} ({quelle.index_name})", vertrag, False,
                       f"erwartet: {vertrag} — vorgefunden: {exc}")
    if not befund.kandidaten:
        return Verdikt(
            f"iShares {quelle.xetra} ({quelle.index_name})", vertrag, False,
            f"erwartet: aufloesbare Ticker — vorgefunden: {befund.aktien_zeilen} "
            f"Aktien-Zeilen, aber kein einziger Ticker lesbar",
        )
    stand = befund.bestand_stand.isoformat() if befund.bestand_stand else "—"
    return Verdikt(
        f"iShares {quelle.xetra} ({quelle.index_name})", vertrag, True,
        f"Stichtag {stand}, {befund.aktien_zeilen} Aktien-Zeilen, "
        f"{len(befund.kandidaten)} Ticker",
    )


def pruefe_kurse(geliefert: set[str]) -> list[Verdikt]:
    """Vertrag: Die Kursquelle liefert bereinigte Schlusskurse.

    Zwei Verdikte, weil zwei verschiedene Versprechen dahinterstehen: die
    tragenden Reihen einzeln (ohne sie gibt es keinen Stichtag), die
    Aktien-Stichprobe als Mehrheit (sie prueft das Format, nicht die Firma).
    """
    raus: list[Verdikt] = []

    fehlend = [t for t in TRAGENDE_REIHEN if t not in geliefert]
    raus.append(Verdikt(
        "Kursquelle (yfinance)", "Index- und Zinsreihen liefern Adj Close",
        not fehlend,
        f"alle {len(TRAGENDE_REIHEN)} Reihen geliefert: {', '.join(TRAGENDE_REIHEN)}"
        if not fehlend else
        f"erwartet: {', '.join(TRAGENDE_REIHEN)} — vorgefunden: ohne Daten: "
        f"{', '.join(fehlend)}",
    ))

    for markt, titel in STICHPROBE.items():
        da = [t for t in titel if t in geliefert]
        ok = len(da) >= STICHPROBE_MINDESTENS
        raus.append(Verdikt(
            f"Kursquelle (yfinance), Markt {markt.upper()}",
            f"mindestens {STICHPROBE_MINDESTENS} von {len(titel)} der Stichprobe",
            ok,
            f"{len(da)} von {len(titel)} geliefert ({', '.join(da) or 'keiner'})"
            if ok else
            f"erwartet: ≥ {STICHPROBE_MINDESTENS} von {len(titel)} — vorgefunden: "
            f"{len(da)} ({', '.join(da) or 'keiner'}); ohne Daten: "
            f"{', '.join(t for t in titel if t not in geliefert)}",
        ))
    return raus


def pruefe_estr(text: str, heute: Date) -> Verdikt:
    """Vertrag: Die CSV ist ueber ihre Kopfzeile lesbar und die juengste
    Beobachtung ist nicht aelter als wenige Handelstage."""
    vertrag = f"CSV parsebar, juengster Satz ≤ {ESTR_MAX_HANDELSTAGE} Handelstage alt"
    werte = parse_ezb_csv(text)
    if not werte:
        return Verdikt(
            "EZB €STR", vertrag, False,
            "erwartet: Kopfzeile mit TIME_PERIOD und OBS_VALUE plus Datenzeilen "
            "— vorgefunden: keine einzige lesbare Beobachtung",
        )
    juengste = max(werte)
    alter = handelstage_zwischen(juengste, heute)
    if alter > ESTR_MAX_HANDELSTAGE:
        return Verdikt(
            "EZB €STR", vertrag, False,
            f"erwartet: ≤ {ESTR_MAX_HANDELSTAGE} Handelstage — vorgefunden: "
            f"juengste Beobachtung {juengste.isoformat()}, {alter} Handelstage alt",
        )
    return Verdikt("EZB €STR", vertrag, True,
                   f"{len(werte)} Beobachtung(en), juengste {juengste.isoformat()} "
                   f"({alter} Handelstage alt)")


# --------------------------------------------------------------------------
# Der Push-Text. Ein Push, alle Brueche, jeder mit Quelle und Handreichung.
# --------------------------------------------------------------------------

WAS_TUN = {
    "Wikipedia": "Artikelaufbau geaendert? tools/build_universe.py parse_us pruefen.",
    "iShares": "CSV-Link umgezogen? Ersatz-URL dem Workflow 'Universum "
               "aktualisieren' als Eingabefeld mitgeben (url_dax/url_mdax/url_tecdax).",
    "Kursquelle": "yfinance-Fassung oder Yahoo-Format geaendert? "
                  "requirements.txt und momentum/data.py pruefen.",
    "EZB": "Reihe oder Spaltennamen geaendert? momentum/riskfree.py pruefen.",
}


def handreichung(quelle: str) -> str:
    for schluessel, rat in WAS_TUN.items():
        if quelle.startswith(schluessel):
            return rat
    return ""


def bericht(verdikte: list[Verdikt], heute: Date) -> str:
    """Der Push-Text bei mindestens einem Bruch. Deterministisch: gleiche
    Verdikte, gleicher Text -- keine Uhrzeit, keine Zufallsreihenfolge."""
    kaputt = [v for v in verdikte if not v.ok]
    zeilen = [
        f"Stand {heute.isoformat()}: {len(kaputt)} von {len(verdikte)} "
        f"Vertraegen gebrochen.",
        "",
    ]
    for v in kaputt:
        zeilen.append(f"* {v.quelle}")
        zeilen.append(f"  Vertrag: {v.vertrag}")
        zeilen.append(f"  {v.befund}")
        rat = handreichung(v.quelle)
        if rat:
            zeilen.append(f"  Was tun: {rat}")
        zeilen.append("")
    zeilen.append(
        "Der Monats-Stichtag steht bevor. Bis dahin repariert, laeuft er "
        "normal; sonst bricht er laut ab und es entsteht kein Ranking."
    )
    return "\n".join(zeilen)


# --------------------------------------------------------------------------
# Der Lauf: holen, pruefen, berichten. Alles Aeussere ist injizierbar.
# --------------------------------------------------------------------------


def sammle_verdikte(
    heute: Date,
    *,
    hole_us=None,
    hole_ishares=None,
    hole_estr=None,
    downloader=None,
) -> list[Verdikt]:
    """Alle vier Vertraege pruefen. Ein Abruf-Fehler ist selbst ein Bruch --
    eine Quelle, die nicht antwortet, haelt ihren Vertrag nicht."""
    hole_us = hole_us or (lambda: lade(QUELLE_US))
    hole_ishares = hole_ishares or lade_bestandsliste
    hole_estr = hole_estr or (
        lambda: lade(EZB_URL.format(start=(heute - _dt.timedelta(days=30)).isoformat()))
    )

    verdikte: list[Verdikt] = []

    try:
        verdikte.append(pruefe_us_tabelle(hole_us()))
    except Exception as exc:  # noqa: BLE001 - nicht abrufbar ist ein Bruch
        verdikte.append(Verdikt("Wikipedia S&P 500", "Artikel abrufbar", False,
                                f"erwartet: HTTP-Antwort — vorgefunden: "
                                f"{type(exc).__name__}: {exc}"))

    for quelle in ISHARES_DE:
        try:
            verdikte.append(pruefe_ishares(hole_ishares(quelle), quelle, heute))
        except Exception as exc:  # noqa: BLE001
            verdikte.append(Verdikt(
                f"iShares {quelle.xetra} ({quelle.index_name})", "Datei abrufbar", False,
                f"erwartet: CSV-Download — vorgefunden: {type(exc).__name__}: {exc}",
            ))

    alle_ticker = list(TRAGENDE_REIHEN) + [t for ts in STICHPROBE.values() for t in ts]
    try:
        buendel = download_prices(
            alle_ticker, heute - _dt.timedelta(days=KURS_FENSTER_TAGE), heute,
            downloader=downloader,
        )
        verdikte.extend(pruefe_kurse(set(buendel.adjusted)))
    except Exception as exc:  # noqa: BLE001
        verdikte.append(Verdikt("Kursquelle (yfinance)", "Abruf moeglich", False,
                                f"erwartet: Kursdaten — vorgefunden: "
                                f"{type(exc).__name__}: {exc}"))

    try:
        verdikte.append(pruefe_estr(hole_estr(), heute))
    except Exception as exc:  # noqa: BLE001
        verdikte.append(Verdikt("EZB €STR", "Schnittstelle abrufbar", False,
                                f"erwartet: CSV-Antwort — vorgefunden: "
                                f"{type(exc).__name__}: {exc}"))

    return verdikte


def main(argv: list[str] | None = None, *, melder=push_vertrag_gebrochen, **naehte) -> int:
    parser = argparse.ArgumentParser(description="Vertragstest der Fremdquellen")
    parser.add_argument("--heute", help="Pruefdatum JJJJ-MM-TT (nur fuer Tests)")
    args = parser.parse_args(argv)
    heute = Date.fromisoformat(args.heute) if args.heute else Date.today()

    log(f"Vertragstest, Stand {heute.isoformat()}")
    for q in ISHARES_DE:
        url = quellen_url(q)
        woher = "Ersatz-URL aus der Umgebung" if url != q.url else "eingebaute URL"
        log(f"  {q.index_name} ({q.xetra}): {woher}")
    log()

    verdikte = sammle_verdikte(heute, **naehte)
    for v in verdikte:
        log(v.zeile())

    kaputt = [v for v in verdikte if not v.ok]
    log()
    if not kaputt:
        log(f"Alle {len(verdikte)} Vertraege halten. Kein Push.")
        return 0

    text = bericht(verdikte, heute)
    log(text)
    verschickt = melder(text)
    log("Push verschickt." if verschickt else "Push NICHT verschickt (siehe oben).")
    # Rot enden unabhaengig davon, ob der Push durchging: der rote Lauf in
    # der Actions-Liste ist das zweite, vom ntfy-Weg unabhaengige Signal.
    return 1


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
