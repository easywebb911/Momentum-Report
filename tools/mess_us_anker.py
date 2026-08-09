"""WEGWERF-MESSUNG: Welchen Tag bewertet ein S&P-500-UCITS-Fonds?

Nach zwei bis drei Mess-Tagen wieder loeschen (zusammen mit
.github/workflows/mess_us_anker.yml).

DIE FRAGE, und warum sie gemessen und nicht angenommen wird
Die Wegwerf-Probe vom 09.08.2026 hat gezeigt: zwei europaeische
S&P-500-ETFs von iShares liefern ueber den deutschen Endpunkt eine
Bestandsliste im vertrauten Format, mit Kurs-Spalte in USD. Damit waere
eine zweite, von Yahoo unabhaengige Kursquelle fuer den US-Markt
erreichbar (Stufe 2b).

Bevor daraus ein Gatter wird, das einen Monats-Stichtag verweigern kann,
muessen ZWEI Groessen bekannt sein, und beide sind heute unbekannt:

  ANKER  -- Welchen Handelstag bewertet der Fonds eigentlich? Der
            Bestands-Stichtag im Vorspann ist das Datum der Datei, nicht
            zwingend das Datum der Kurse. Ein UCITS-Fonds mit
            europaeischem Bewertungszeitpunkt kann US-Aktien zum Schluss
            DESSELBEN Tages bewerten -- oder zum Schluss des Tages
            DAVOR, weil die US-Boerse zum Bewertungszeitpunkt noch gar
            nicht geschlossen hatte. Ein Gatter auf dem falschen Anker
            misst eine Tagesrendite und meldet einen Bruch, wo keiner ist.

  TOLERANZ -- Wie weit liegen zwei richtige Quellen normalerweise
            auseinander? Die 1,0 % des DE-Gatters sind gesetzt, nicht
            gemessen. Fuer die US-Seite soll die Schwelle aus der
            beobachteten Streuung folgen.

Diese Messung liefert beide Zahlen. Sie vergleicht dieselbe Titelmenge
gegen ZWEI Anker-Tage; welcher Anker der richtige ist, zeigt sich daran,
welcher die dramatisch kleinere Streuung ergibt. Das ist Kalibrierung
eines Messinstruments und kein Strategie-Tuning: kein Score, kein Rang
und keine Kursreihe des Werkzeugs werden dabei beruehrt -- diese Datei
schreibt nichts und wird von nichts gelesen.

WARUM MEHRERE TAGE: Ein einzelner Tag kann durch einen Feiertag, eine
Indexumstellung oder einen ruhigen Markt taeuschen. Erst zwei bis drei
Werktage zeigen, ob der Anker STABIL derselbe ist.

ROT ODER GRUEN: Der Lauf endet ROT, sobald eine Quelle nicht liefert --
eine Messung ohne Daten ist keine Messung, und ein gruener Lauf ohne
Zahlen waere die schlechteste aller Ausgaben. Liefern beide Quellen,
endet er gruen; das Ergebnis steht ausschliesslich im Protokoll.
"""

from __future__ import annotations

import datetime as _dt
import math
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from momentum.config import MARKETS_BY_KEY  # noqa: E402
from momentum.data import download_prices  # noqa: E402
from momentum.ishares import (  # noqa: E402
    Befund,
    QuelleUnbrauchbar,
    lade,
    parse_ishares_holdings,
)

Date = _dt.date

# Die beiden Kandidaten, verifiziert am 09.08.2026 auf dem Runner: beide
# liefern ueber den DEUTSCHEN Endpunkt-Typ (1478358465952.ajax) eine echte
# CSV mit 504 Aktien-Zeilen, Kurs-Spalte und deutscher Zahlenschreibweise.
_DOWNLOAD = (
    "https://www.ishares.com/de/privatanleger/de/produkte/{produkt}/{schnipsel}/"
    "1478358465952.ajax?fileType=csv&fileName={datei}&dataType=fund"
)

FONDS: tuple[tuple[str, str], ...] = (
    (
        "SXR8 (iShares Core S&P 500 UCITS, Acc)",
        _DOWNLOAD.format(
            produkt="253743",
            schnipsel="ishares-sp-500-b-ucits-etf-acc-fund",
            datei="SXR8_holdings",
        ),
    ),
    (
        "IUSA (iShares S&P 500 UCITS, Inc)",
        _DOWNLOAD.format(
            produkt="251900",
            schnipsel="ishares-sp-500-ucits-etf-inc-fund",
            datei="IUSA_holdings",
        ),
    ),
)

# Das ANZAHL-GATTER des Parsers, auf einen S&P 500 gestellt. Dieselbe
# Schranke, die das US-Universum ohnehin kennt (build_universe.ERWARTET).
ANZAHL_SP500 = (495, 510)

# Erwartete Marktwaehrung der Kurs-Spalte. Beobachtet: USD, Boerse NASDAQ
# bzw. NYSE. Ein Titel in einer anderen Waehrung wird NICHT verglichen --
# ein Waehrungsunterschied waere eine riesige Schein-Abweichung.
ERWARTETE_WAEHRUNG = "USD"

# Die drei Kandidaten-Toleranzen, gegen die gezaehlt wird. Sie sind hier
# ausdruecklich KEINE Schwellen, sondern Messpunkte: die Verteilung soll
# zeigen, welche davon die echte Streuung abdeckt.
KANDIDATEN_TOLERANZEN = (0.005, 0.010, 0.020)

# So viele Kalendertage werden Kurse geholt. Grosszuegig, damit auch ueber
# ein langes Feiertagswochenende zwei Handelstage im Fenster liegen.
FENSTER_TAGE = 21

# Unterhalb dieses Anteils gelieferter Kursreihen ist die Messung kein
# Befund mehr, sondern ein Zufallsbild -- dann ROT statt gruen.
MIN_LIEFERQUOTE = 0.80

# So viele Titel werden je Fall namentlich genannt. Genug, um ein Muster zu
# erkennen; wenig genug, dass das Protokoll lesbar bleibt.
NAMENTLICH = 10
NAMENTLICH_FEHLEND = 40


def log(text: str = "") -> None:
    print(text, flush=True)


# --------------------------------------------------------------------------
# Kleine Statistik. Bewusst ohne Fremdbibliothek: was hier gerechnet wird,
# soll man beim Lesen nachvollziehen koennen.
# --------------------------------------------------------------------------


def perzentil(werte: list[float], anteil: float) -> float:
    """Naechster-Rang-Perzentil: der kleinste Wert, unter dem mindestens
    `anteil` der Beobachtungen liegen.

    Bewusst diese Definition und keine Interpolation: hier werden keine
    Zwischenwerte geschaetzt, sondern echte Beobachtungen benannt. p99 von
    100 Werten ist der 99. -- ein Wert, den es wirklich gibt.
    """
    if not werte:
        return float("nan")
    sortiert = sorted(werte)
    stelle = max(0, min(len(sortiert) - 1, math.ceil(anteil * len(sortiert)) - 1))
    return sortiert[stelle]


@dataclass(frozen=True)
class Paar:
    """Ein Titel mit beiden Kursen an einem Anker-Tag."""

    ticker: str
    name: str
    ishares: float
    yahoo: float

    @property
    def abweichung(self) -> float:
        return (self.yahoo - self.ishares) / self.ishares

    def zeile(self, links: str = "iShares", rechts: str = "Yahoo") -> str:
        """Die Namen der beiden Seiten sind einstellbar, weil dieselbe
        Darstellung zweimal gebraucht wird: einmal Fonds gegen Kursquelle,
        einmal Fonds gegen Fonds. Ein festverdrahtetes "Yahoo" waere im
        zweiten Fall schlicht gelogen."""
        return (
            f"{self.ticker:<8} {links} {self.ishares:>10.4f}  "
            f"{rechts} {self.yahoo:>10.4f}  {self.abweichung * 100:+7.2f} %   {self.name}"
        )


# --------------------------------------------------------------------------
# Handelskalender und Anker
# --------------------------------------------------------------------------


def handelstage(index_reihe: dict[Date, float]) -> list[Date]:
    """Die US-Handelstage laut Indexreihe -- derselbe Kalender, den auch
    `resolve_asof` benutzt. So braucht diese Messung keine Feiertagsliste."""
    return sorted(index_reihe)


def anker(tage: list[Date], stand: Date) -> tuple[Date | None, Date | None, str]:
    """(Anker A, Anker B, Hinweis).

    ANNAHME, ausdruecklich benannt: Anker A ist der Bestands-Stichtag der
    Datei selbst, falls die US-Boerse an diesem Tag gehandelt hat. War der
    Tag ein US-Feiertag (die deutsche und die amerikanische Boerse haben
    verschiedene), gilt der letzte US-Handelstag DAVOR als A -- und der
    Hinweis sagt es. Anker B ist immer der US-Handelstag vor A.
    """
    vorher = [t for t in tage if t <= stand]
    if not vorher:
        return None, None, "kein US-Handelstag am oder vor dem Bestands-Stichtag"
    a = vorher[-1]
    hinweis = "" if a == stand else (
        f"Bestands-Stichtag {stand} war kein US-Handelstag — "
        f"Anker A auf den letzten davor gesetzt ({a})"
    )
    b = vorher[-2] if len(vorher) >= 2 else None
    return a, b, hinweis


# --------------------------------------------------------------------------
# Die Messung
# --------------------------------------------------------------------------


def us_ticker(yahoo_de: str) -> str:
    """"NVDA.DE" -> "NVDA".

    Der gemeinsame Parser uebersetzt jedes Symbol in die deutsche
    Schreibweise, weil er fuer die deutschen Bestandslisten gebaut ist.
    Fuer eine US-Liste ist das Suffix schlicht abzuziehen.

    ANNAHME: Die Titel, die den Parser passiert haben, tragen ein reines
    A-Z0-9-Symbol -- fuer sie ist die Rueckuebersetzung eindeutig. Genau
    daran scheitern die KLASSEN-TITEL (BRK.B, BF.B): ihr Symbol enthaelt
    einen Punkt oder Schraegstrich und faellt schon im Parser heraus. Sie
    werden hier deshalb nicht falsch uebersetzt, sondern weiter unten
    NAMENTLICH als "ohne Ticker" gemeldet.
    """
    return yahoo_de[:-3] if yahoo_de.endswith(".DE") else yahoo_de


def verteilung(paare: list[Paar], titel: str) -> None:
    """Die Zahlen, um die es geht -- fuer einen Fonds an einem Anker-Tag."""
    if not paare:
        log(f"  {titel}: kein einziger vergleichbarer Titel.")
        return
    betraege = [abs(p.abweichung) for p in paare]
    log(f"  {titel}: {len(paare)} Titel")
    log(
        f"    Median {perzentil(betraege, 0.50) * 100:6.3f} %   "
        f"p90 {perzentil(betraege, 0.90) * 100:6.3f} %   "
        f"p99 {perzentil(betraege, 0.99) * 100:6.3f} %   "
        f"Max {max(betraege) * 100:6.3f} %"
    )
    zaehler = "   ".join(
        f"> {t * 100:.1f} %: {sum(1 for b in betraege if b > t):>3}"
        for t in KANDIDATEN_TOLERANZEN
    )
    log(f"    jenseits der Kandidaten-Toleranzen:   {zaehler}")
    schlimmste = sorted(paare, key=lambda p: -abs(p.abweichung))[:NAMENTLICH]
    log(f"    die {len(schlimmste)} schlechtesten:")
    for p in schlimmste:
        log(f"      {p.zeile()}")


def sammle_paare(
    kandidaten: list, kurse: dict[str, dict[Date, float]], tag: Date
) -> tuple[list[Paar], list[str]]:
    """Alle Titel mit beiden Kursen an EINEM Anker-Tag."""
    paare: list[Paar] = []
    fehlend: list[str] = []
    for k in kandidaten:
        symbol = us_ticker(k.ticker)
        reihe = kurse.get(symbol)
        wert = reihe.get(tag) if reihe else None
        if wert is None:
            fehlend.append(symbol)
            continue
        paare.append(Paar(symbol, k.name, k.kurs, wert))
    return paare, fehlend


def quervergleich(links, rechts, name_links: str, name_rechts: str) -> None:
    """Stuetzen sich BlackRocks eigene Zahlen gegenseitig?

    Zwei Fonds desselben Hauses auf denselben Index: ihre Bewertungskurse
    muessten praktisch identisch sein. Weichen sie voneinander ab, liegt
    das Problem NICHT bei Yahoo -- dann ist schon die Zweitquelle in sich
    uneinig, und als Schiedsrichter taugt sie nicht.
    """
    log(f"\n  Quervergleich {name_links} gegen {name_rechts} (beide iShares):")
    a = {us_ticker(k.ticker): k for k in links.kandidaten if k.kurs is not None}
    b = {us_ticker(k.ticker): k for k in rechts.kandidaten if k.kurs is not None}
    gemeinsam = sorted(set(a) & set(b))
    if not gemeinsam:
        log("    keine gemeinsamen Titel — nicht vergleichbar.")
        return
    if links.bestand_stand != rechts.bestand_stand:
        log(
            f"    ACHTUNG: verschiedene Bestands-Stichtage "
            f"({links.bestand_stand} vs. {rechts.bestand_stand}). Die Zahlen "
            f"unten enthalten damit eine Tagesbewegung und sagen NICHTS "
            f"ueber die Einigkeit der Quelle."
        )
    paare = [
        Paar(t, a[t].name, a[t].kurs, b[t].kurs) for t in gemeinsam
    ]
    betraege = [abs(p.abweichung) for p in paare]
    log(f"    {len(paare)} gemeinsame Titel")
    log(
        f"    Median {perzentil(betraege, 0.50) * 100:6.3f} %   "
        f"p90 {perzentil(betraege, 0.90) * 100:6.3f} %   "
        f"p99 {perzentil(betraege, 0.99) * 100:6.3f} %   "
        f"Max {max(betraege) * 100:6.3f} %"
    )
    if max(betraege) == 0:
        log("    kein einziger Titel weicht ab — die Quelle ist mit sich einig.")
        return
    for p in sorted(paare, key=lambda p: -abs(p.abweichung))[:NAMENTLICH]:
        log(f"      {p.zeile(name_links, name_rechts)}")


def nenne(titel: str, eintraege: list[str], grenze: int = NAMENTLICH_FEHLEND) -> None:
    if not eintraege:
        log(f"  {titel}: keine.")
        return
    log(f"  {titel}: {len(eintraege)}")
    for eintrag in sorted(eintraege)[:grenze]:
        log(f"    - {eintrag}")
    if len(eintraege) > grenze:
        log(f"    … und {len(eintraege) - grenze} weitere")


def main() -> int:
    heute = _dt.date.today()
    log(f"Mess-Probe US-Anker, Laufdatum {heute.isoformat()}")
    log("Sie misst und entscheidet nichts. Sie schreibt nichts.")
    log("")

    # --- 1. Die beiden Bestandslisten, mit dem ECHTEN Parser -------------
    befunde: dict[str, Befund] = {}
    for name, url in FONDS:
        log(f"### {name}")
        try:
            inhalt = lade(url)
        except Exception as exc:  # noqa: BLE001 - eine Messung ohne Daten ist keine
            log(f"  ABBRUCH: Bestandsliste nicht abrufbar ({type(exc).__name__}: {exc})")
            return 1
        try:
            befund = parse_ishares_holdings(
                inhalt, name, heute=heute, erwartete_anzahl=ANZAHL_SP500
            )
        except QuelleUnbrauchbar as exc:
            log(f"  ABBRUCH: {exc}")
            return 1
        mit_kurs = [k for k in befund.kandidaten if k.kurs is not None]
        fremde = [k for k in mit_kurs if k.waehrung and k.waehrung != ERWARTETE_WAEHRUNG]
        log(
            f"  Bestands-Stichtag {befund.bestand_stand}, "
            f"{befund.aktien_zeilen} Aktien-Zeilen, {len(befund.kandidaten)} Ticker, "
            f"{len(mit_kurs)} Kurse, Zahlenschreibweise {befund.kurs_konvention}"
        )
        nenne("ohne Ticker (Klassen-Titel?)", befund.ungeloest)
        if fremde:
            nenne(
                f"Marktwaehrung nicht {ERWARTETE_WAEHRUNG} — nicht verglichen",
                [f"{k.ticker} ({k.waehrung})" for k in fremde],
            )
        # Ab hier traegt der Befund nur noch, was ueberhaupt vergleichbar
        # ist: Kurs vorhanden und in der erwarteten Waehrung.
        befund.kandidaten = [
            k for k in mit_kurs
            if not (k.waehrung and k.waehrung != ERWARTETE_WAEHRUNG)
        ]
        befunde[name] = befund
        log("")

    # --- 2. Handelskalender und Anker ------------------------------------
    index_ticker = MARKETS_BY_KEY["us"].index_ticker
    frueheste = min(b.bestand_stand for b in befunde.values())
    von, bis = frueheste - _dt.timedelta(days=FENSTER_TAGE), heute
    log(f"### Handelskalender ({index_ticker}), Fenster {von} .. {bis}")
    kalender = download_prices([index_ticker], von, bis)
    tage = handelstage(kalender.adjusted.get(index_ticker) or {})
    if len(tage) < 2:
        log(f"  ABBRUCH: {index_ticker} lieferte {len(tage)} Handelstage — ohne "
            f"Kalender ist kein Anker bestimmbar.")
        return 1
    log(f"  {len(tage)} US-Handelstage, zuletzt {tage[-1]}")
    log("")

    # --- 3. Die Kurse, EIN Abruf fuer beide Fonds -------------------------
    alle = sorted({us_ticker(k.ticker) for b in befunde.values() for k in b.kandidaten})
    log(f"### Kursquelle: {len(alle)} Titel, {von} .. {bis}")
    buendel = download_prices(alle, von, bis)
    quote = len(buendel.close) / len(alle) if alle else 0.0
    log(f"  {len(buendel.close)} von {len(alle)} Reihen geliefert ({quote:.1%})")
    if quote < MIN_LIEFERQUOTE:
        log(f"  ABBRUCH: unter {MIN_LIEFERQUOTE:.0%} — eine Messung auf so vielen "
            f"Luecken ist kein Befund, sondern ein Zufallsbild.")
        return 1
    log("")

    # --- 4. Die Verteilung je Fonds und Anker ----------------------------
    for name, befund in befunde.items():
        log(f"### {name} — Bestands-Stichtag {befund.bestand_stand}")
        a, b, hinweis = anker(tage, befund.bestand_stand)
        if hinweis:
            log(f"  Hinweis: {hinweis}")
        if a is None:
            log("  ABBRUCH: kein Anker bestimmbar.")
            return 1
        for marke, tag in (("Anker A (Stichtag selbst)", a), ("Anker B (Tag davor)", b)):
            if tag is None:
                log(f"  {marke}: nicht bestimmbar (Fenster zu kurz).")
                continue
            paare, fehlend = sammle_paare(befund.kandidaten, buendel.close, tag)
            verteilung(paare, f"{marke} = {tag}")
            nenne("    ohne Yahoo-Kurs an diesem Tag", fehlend)
        log("")

    # --- 5. Quervergleich der beiden Fonds --------------------------------
    log("### Stuetzen sich die beiden iShares-Dateien gegenseitig?")
    (name_a, befund_a), (name_b, befund_b) = list(befunde.items())
    quervergleich(befund_a, befund_b, name_a.split()[0], name_b.split()[0])
    log("")

    log("Ende der Messung. Kein Ergebnis dieser Messung wirkt auf einen Lauf.")
    log("Der Anker ist der Tag mit der DEUTLICH kleineren Streuung; die "
        "Toleranz folgt aus p99 und Maximum ueber alle Mess-Tage.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
