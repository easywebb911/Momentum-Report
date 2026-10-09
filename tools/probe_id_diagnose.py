"""WEGWERF-DIAGNOSE: Information Discreteness (ID, Da/Gurun/Warachka 2014).

Beantwortet NUR eine Frage, einmalig: wuerde ID an den drei bisherigen
Monats-Stichtagen (und am aktuellen Stand) die Top-5 veraendert haben,
wenn man die Top-15 des Scores nach ID statt nach Score sortiert? Das
Ergebnis steht AUSSCHLIESSLICH im Job-Log dieses Laufs -- keine Datei
wird geschrieben, kein Commit, kein Push, kein ntfy, keine Aenderung an
Score/Ranking/bestehendem Code. Nach Auswertung wird diese Datei (und
der zugehoerige Workflow) in einem eigenen Rueckbau-PR wieder entfernt
(zweiter Schritt, siehe PR-Text).

DEFINITION, woertlich aus dem Auftrag, nicht selbst hergeleitet:
    ID = Vorzeichen(12-1-Rendite) x (Anteil negativer Tage - Anteil
         positiver Tage), ueber EXAKT dasselbe 12-1-Fenster wie
         momentum_12_1 in scoring.py.
Niedriger (negativer) Wert = stetiger Anstieg (viele kleine Auf-Tage),
hoeherer Wert = sprunghaft (wenige grosse Spruenge, sonst eher flach/
negativ) -- Da/Gurun/Warachka selbst nennen das "frog in the pan".

FENSTERLOGIK -- UEBERNOMMEN, NICHT NEU ERFUNDEN:
`shift_month`/`month_end_close` kommen unveraendert aus
`src/momentum/scoring.py`. Das 12-1-Fenster fuer momentum_12_1 ist durch
ZWEI MONATS-END-SCHLUSSKURSE definiert (Monat M-1 im Zaehler, Monat
M-12 im Nenner, M = Monat des Stichtags), nicht durch ein Tagesfenster.
Fuer ID werden aber TAGES-Vorzeichen gebraucht. Diese Datei uebernimmt
dafuer exakt dieselbe Kandidaten-Auswahl wie `month_end_close()`
(gleicher Filter: `d.year==year and d.month==month and d<=asof`, dann
`max(...)`), fragt aber nach dem DATUM statt dem Kurs -- keine eigene
Fensterdefinition, nur eine zweite Ablesung derselben Auswahl.

WIDERSPRUCH GEMELDET, NICHT STILL ENTSCHIEDEN (Auftrag Kriterium 2/6):
Die beiden so gefundenen Monats-End-Tage (Nenner-Tag `start`, Zaehler-
Tag `ende`) legen ein TAGES-Intervall [start, ende] fest. Taeglich
RENDITEN gibt es aber nur fuer aufeinanderfolgende Handelstage INNERHALB
dieses Intervalls -- der allererste Tag (`start`) selbst hat keinen
Vortageskurs mehr im Fenster. Diese Datei zaehlt deshalb die Renditen
fuer alle Handelstage NACH `start` bis `ende` (halboffenes Intervall
`(start, ende]`), nicht `[start, ende]`. Das ist eine bewusste, aber
NICHT mit Easy abgestimmte Wahl -- der Auftrag selbst war hier nicht
eindeutig (das Papier definiert ID ueber taegliche Renditen eines reinen
Kalenderfensters, nicht ueber zwei Monats-End-Ankerkurse). Wer sie anders
will: `id_fenster()` liefert `(start, ende)`, der Zuschnitt passiert in
`berechne_id()`, eine Zeile.

WEITERE, SELBST GESETZTE SCHWELLEN (Annahmen, Auftrag Kriterium 4 -- klar
benannt, nicht aus Literatur oder Tests abgeleitet):
  * MIN_RENDITETAGE_FUER_ID = 150: das volle Fenster hat ueblicherweise
    rund 230 Handelstage (~11 Monate). Darunter gilt ein Titel als
    "zu kurz" und wird NICHT gerechnet (Auftrag: "nicht berechnen"),
    um keine ID aus einem Loch in der Kurshistorie zu erfinden.
  * Kontrollrechnung momentum_12_1 (neu) gegen momentum_12_1 (gespeichert):
    Abweichung <= 1e-6 gilt als reine Rundung, 1e-6..1e-3 als "kleine,
    vermutlich nachtraegliche yfinance-Kursanpassung" (Dividende/Split
    nachgebucht, kein Fensterfehler), > 1e-3 als Warnung ganz oben im
    Log ("Fenster passt nicht").
  * "Umsortierung nach ID" sortiert AUFSTEIGEND (niedrigster/stetigster
    Wert zuerst) -- abgeleitet aus der Richtung der Kennzahl, nicht
    ausdruecklich von Easy festgelegt. Wer die Richtung umdrehen will:
    eine Zeile in `top15_neu_sortiert()`.

ANNAHMEN, GEKLAERT (Auftrag Kriterium 4):
  * Tickerlisten je Stichtag: GENAU die Ticker aus der jeweiligen
    `data/rankings/{markt}_*.json` (`rangliste[].ticker`) -- nicht aus
    den (ggf. inzwischen veraenderten) Universums-Dateien. Nur fuer den
    AKTUELLEN Stand (noch kein eingefrorenes Ranking) gilt das volle,
    aktuell VERIFIED-e Universum aus `universe/universe_{markt}.txt`.
  * Mindest-Handelstage: siehe oben, 150.
  * Zeitzonen: `download_prices()` (unveraendert aus `data.py`)
    liefert je Handelstag bereits ein reines Kalenderdatum
    (`stamp.date()`), keine Uhrzeit/Zeitzone -- fuer US wie DE identisch
    behandelt, kein eigener Zeitzonen-Code noetig oder vorhanden.

RATE-LIMIT (Auftrag: "kein Retry-Sturm, hoechstens ein einziger
Wiederholungsversuch pro Batch"): diese Datei fuegt KEINE eigene
Wiederholung hinzu -- sie ruft `download_prices()` unveraendert auf, das
bereits intern bis zu `DOWNLOAD_RETRIES` (= 3, `config.py`, bestehender,
bereits geprueften Code) mit Backoff versucht und jeden endgueltig
gescheiterten Block in `stats.failed_chunks` vermerkt, ohne den Lauf
abzubrechen. Das ist EIN Widerspruch zum woertlichen "hoechstens ein
einziger Versuch" (hier sind es bis zu drei) -- bewusst in Kauf
genommen, um `data.py` nicht zu aendern/zweit-zu-implementieren
("Fensterlogik ... NICHT neu erfinden" gilt sinngemaess auch fuer den
Download selbst). Fehlende Bloecke/Ticker werden im Log klar benannt,
der Lauf endet dabei trotzdem gruen (fail-soft, kein Abbruch ohne
Ausgabe).

SCHREIBT NIRGENDS: kein `open(..., "w")`, kein `git`, kein `push`, kein
ntfy-Import. Workflow-Token nur `contents: read`.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from momentum.config import MARKETS_BY_KEY  # noqa: E402
from momentum.data import download_prices  # noqa: E402
from momentum.scoring import (  # noqa: E402
    InsufficientHistory,
    MOMENTUM_LOOKBACK_MONTHS,
    MOMENTUM_SKIP_MONTHS,
    momentum_12_1,
    percentile_ranks,
    shift_month,
)
from momentum.universe import UniverseNotReady, load_universe  # noqa: E402

Date = _dt.date
Series = dict[Date, float]

RANKINGS_DIR = Path("data/rankings")

MIN_RENDITETAGE_FUER_ID = 150
KONTROLLE_RUNDUNG = 1e-6
KONTROLLE_KLEIN = 1e-3
TOP_N_TABELLE = 15
TOP_N_SCORE = 5


# --------------------------------------------------------------------------
# Fensterlogik: uebernommen aus scoring.py (siehe Modul-Docstring)
# --------------------------------------------------------------------------


def _letzter_handelstag_in_monat(prices: Series, year: int, month: int, asof: Date) -> Date:
    """Dieselbe Kandidaten-Auswahl wie `scoring.month_end_close()`, hier das
    DATUM statt den Kurs -- keine eigene Fensterdefinition."""
    kandidaten = [d for d in prices if d.year == year and d.month == month and d <= asof]
    if not kandidaten:
        raise InsufficientHistory(f"kein Handelstag in {year}-{month:02d} bis {asof}")
    return max(kandidaten)


def id_fenster(prices: Series, asof: Date) -> tuple[Date, Date]:
    """(Nenner-Tag, Zaehler-Tag) -- exakt die Monate, die momentum_12_1 fuer
    denselben `asof` verwendet (M-12 bzw. M-1)."""
    zaehler_jahr, zaehler_monat = shift_month(asof.year, asof.month, -MOMENTUM_SKIP_MONTHS)
    nenner_jahr, nenner_monat = shift_month(asof.year, asof.month, -MOMENTUM_LOOKBACK_MONTHS)
    start = _letzter_handelstag_in_monat(prices, nenner_jahr, nenner_monat, asof)
    ende = _letzter_handelstag_in_monat(prices, zaehler_jahr, zaehler_monat, asof)
    return start, ende


def _vorzeichen(wert: float) -> int:
    if wert > 0:
        return 1
    if wert < 0:
        return -1
    return 0


@dataclass
class IdBefund:
    id_wert: float | None
    grund: str | None  # None, wenn id_wert gesetzt ist
    renditetage: int
    anteil_pos: float | None
    anteil_neg: float | None


def berechne_id(prices: Series, asof: Date) -> IdBefund:
    """ID fuer EINEN Titel. `grund` gesetzt und `id_wert is None`, wenn das
    Fenster fehlt oder zu kurz ist -- "zu kurz" wird ausgewiesen, nicht
    geraten (Auftrag: "nicht berechnen")."""
    try:
        start, ende = id_fenster(prices, asof)
        momentum = momentum_12_1(prices, asof)
    except InsufficientHistory as exc:
        return IdBefund(None, f"Fenster fehlt: {exc}", 0, None, None)

    tage = sorted(d for d in prices if start < d <= ende)
    if len(tage) < MIN_RENDITETAGE_FUER_ID:
        return IdBefund(
            None,
            f"zu kurz ({len(tage)} von mind. {MIN_RENDITETAGE_FUER_ID} Renditetagen)",
            len(tage),
            None,
            None,
        )

    vortag = start
    pos = neg = 0
    for tag in tage:
        ret = prices[tag] / prices[vortag] - 1.0
        if ret > 0:
            pos += 1
        elif ret < 0:
            neg += 1
        vortag = tag

    n = len(tage)
    anteil_pos = pos / n
    anteil_neg = neg / n
    id_wert = _vorzeichen(momentum) * (anteil_neg - anteil_pos)
    return IdBefund(id_wert, None, n, anteil_pos, anteil_neg)


# --------------------------------------------------------------------------
# Eingaben: gespeicherte Ranglisten + aktueller Stand
# --------------------------------------------------------------------------


@dataclass
class StichtagEingabe:
    markt: str
    label: str  # z. B. "2026-07" oder "aktuell"
    asof: Date
    tickers: list[str]
    rang_von_ticker: dict[str, int]
    gespeichertes_momentum: dict[str, float] | None  # None == "aktuell", kein Soll-Wert


def lies_rangliste(pfad: Path) -> StichtagEingabe:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    markt = daten["markt"]
    stichtag = Date.fromisoformat(daten["stichtag"])
    rang_von_ticker: dict[str, int] = {}
    gespeichert: dict[str, float] = {}
    tickers: list[str] = []
    for eintrag in daten["rangliste"]:
        ticker = eintrag["ticker"]
        tickers.append(ticker)
        rang_von_ticker[ticker] = eintrag["rang"]
        gespeichert[ticker] = eintrag["momentum_12_1"]
    label = f"{stichtag.year}-{stichtag.month:02d}"
    return StichtagEingabe(markt, label, stichtag, tickers, rang_von_ticker, gespeichert)


def historische_eingaben(markt: str) -> list[StichtagEingabe]:
    pfade = sorted(RANKINGS_DIR.glob(f"{markt}_*.json"))
    return [lies_rangliste(p) for p in pfade]


def aktuelle_eingabe(markt: str, heute: Date, log) -> StichtagEingabe | None:
    """Voller, aktuell VERIFIED-er Universums-Stand -- kein eingefrorenes
    Ranking existiert dafuer noch, deshalb kein Soll-Wert fuer die
    Kontrollrechnung (gespeichertes_momentum bleibt None)."""
    try:
        universum = load_universe(MARKETS_BY_KEY[markt].universe_file)
    except UniverseNotReady as exc:
        log(f"[{markt}] aktueller Stand nicht ermittelbar: {exc}")
        return None
    return StichtagEingabe(markt, "aktuell", heute, list(universum.tickers), {}, None)


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------


def top15_neu_sortiert(top15: list[tuple[str, float | None]]) -> list[str]:
    """Top-15-Ticker (Score-Reihenfolge) nach ID AUFSTEIGEND umsortiert.
    "Zu kurz"/fehlende ID-Titel bleiben an ihrer bisherigen Stelle ganz
    hinten -- sie koennen nicht vorgezogen werden, ohne eine ID zu
    erfinden."""
    mit_id = [(t, i) for t, i in top15 if i is not None]
    ohne_id = [t for t, i in top15 if i is None]
    mit_id.sort(key=lambda ti: (ti[1], ti[0]))
    return [t for t, _ in mit_id] + ohne_id


def verarbeite(
    markt: str, eingabe: StichtagEingabe, bundle_adjusted: dict[str, Series],
    warnungen: list[str], log,
) -> None:
    befunde: dict[str, IdBefund] = {}
    fehlende_ticker: list[str] = []
    for ticker in eingabe.tickers:
        prices = bundle_adjusted.get(ticker)
        if not prices:
            fehlende_ticker.append(ticker)
            continue
        befunde[ticker] = berechne_id(prices, eingabe.asof)

    id_werte = {t: b.id_wert for t, b in befunde.items() if b.id_wert is not None}
    perzentile = percentile_ranks(id_werte)

    log(f"--- {markt.upper()} {eingabe.label} (Stichtag {eingabe.asof.isoformat()}) ---")
    log(
        f"Universum: {len(eingabe.tickers)} Ticker, davon {len(fehlende_ticker)} ohne "
        f"Kursdaten im Download-Fenster, {len(id_werte)} mit berechneter ID, "
        f"{len(befunde) - len(id_werte)} 'zu kurz'."
    )
    if fehlende_ticker:
        log(f"  ohne Kursdaten: {', '.join(sorted(fehlende_ticker)[:20])}" + (" ..." if len(fehlende_ticker) > 20 else ""))

    # Kontrollrechnung -- nur dort, wo ein gespeicherter Wert existiert.
    if eingabe.gespeichertes_momentum is not None:
        abweichungen_gross = 0
        abweichungen_klein = 0
        for ticker, prices in bundle_adjusted.items():
            if ticker not in eingabe.gespeichertes_momentum:
                continue
            try:
                neu = momentum_12_1(prices, eingabe.asof)
            except InsufficientHistory:
                continue
            soll = eingabe.gespeichertes_momentum[ticker]
            diff = abs(neu - soll)
            if diff > KONTROLLE_KLEIN:
                abweichungen_gross += 1
                warnungen.append(
                    f"{markt.upper()} {eingabe.label} {ticker}: momentum_12_1 neu={neu:.6f} "
                    f"vs. gespeichert={soll:.6f} (Differenz {diff:.6f} > {KONTROLLE_KLEIN}) "
                    f"-- Fenster passt moeglicherweise nicht."
                )
            elif diff > KONTROLLE_RUNDUNG:
                abweichungen_klein += 1
        log(
            f"Kontrollrechnung momentum_12_1: {abweichungen_gross} Abweichung(en) > "
            f"{KONTROLLE_KLEIN} (siehe Warnungen), {abweichungen_klein} kleine "
            f"Abweichung(en) ({KONTROLLE_RUNDUNG}..{KONTROLLE_KLEIN}, vermutlich "
            f"nachtraegliche Kursanpassung)."
        )
    else:
        log("Kontrollrechnung momentum_12_1: entfaellt (kein eingefrorenes Ranking fuer 'aktuell').")

    # Top-15 nach Score -- nur fuer Stichtage mit gespeichertem Rang sinnvoll.
    if not eingabe.rang_von_ticker:
        log("(kein Score-Rang verfuegbar -- Top-15/Top-5-Vergleich entfaellt fuer 'aktuell')")
        log()
        return

    rang_sortiert = sorted(eingabe.rang_von_ticker.items(), key=lambda kv: kv[1])
    top15 = [(t, r) for t, r in rang_sortiert if r <= TOP_N_TABELLE]

    log(f"{'Rang':>4} {'Ticker':<10} {'ID':>10} {'ID-Perz.':>9}")
    top15_mit_id: list[tuple[str, float | None]] = []
    for ticker, rang in top15:
        befund = befunde.get(ticker)
        if befund is None:
            log(f"{rang:>4} {ticker:<10} {'(fehlt)':>10} {'':>9}")
            top15_mit_id.append((ticker, None))
            continue
        if befund.id_wert is None:
            log(f"{rang:>4} {ticker:<10} {'zu kurz':>10} {'':>9}")
            top15_mit_id.append((ticker, None))
            continue
        perz = perzentile.get(ticker)
        log(f"{rang:>4} {ticker:<10} {befund.id_wert:>10.4f} {perz:>9.3f}")
        top15_mit_id.append((ticker, befund.id_wert))

    top5_perzentile = [perzentile[t] for t, r in top15 if r <= TOP_N_SCORE and t in perzentile]
    top15_perzentile = [perzentile[t] for t, r in top15 if t in perzentile]
    if top5_perzentile:
        log(
            f"ID-Perzentil Top-5 (Score): min={min(top5_perzentile):.3f} "
            f"max={max(top5_perzentile):.3f} -- sprunghaftes Drittel = Perzentil > 0.667."
        )
        sprunghaft = [p for p in top5_perzentile if p > 2 / 3]
        if sprunghaft:
            log(f"  {len(sprunghaft)} von 5 Top-5-Titeln liegen im sprunghaften Drittel.")
    if top15_perzentile:
        log(
            f"ID-Perzentil Top-15 (Score): min={min(top15_perzentile):.3f} "
            f"max={max(top15_perzentile):.3f}"
        )

    alte_top5 = {t for t, r in top15 if r <= TOP_N_SCORE}
    neu_sortiert = top15_neu_sortiert(top15_mit_id)
    neue_top5 = set(neu_sortiert[:TOP_N_SCORE])
    weg = sorted(alte_top5 - neue_top5)
    neu = sorted(neue_top5 - alte_top5)
    log(
        f"Umsortierung Top-15 nach ID (aufsteigend) -> Top-5 aendert sich um "
        f"{len(weg)} von 5 Titeln."
    )
    if weg:
        log(f"  faellt raus: {', '.join(weg)}")
    if neu:
        log(f"  kommt neu rein: {', '.join(neu)}")
    log()


def download_fenster(eingaben: list[StichtagEingabe]) -> tuple[Date, Date]:
    """Ein gemeinsames Download-Fenster je Markt -- deckt Nenner-Monat
    (M-12) der FRUEHESTEN und Stichtag der SPAETESTEN Eingabe ab, mit
    zehn Tagen Vorlauf gegen Monatsende/Wochenende an der Fenstergrenze."""
    fruehester_nenner = min(
        Date(*shift_month(e.asof.year, e.asof.month, -MOMENTUM_LOOKBACK_MONTHS), 1)
        for e in eingaben
    )
    spaetester_asof = max(e.asof for e in eingaben)
    return fruehester_nenner - _dt.timedelta(days=10), spaetester_asof


def main() -> int:
    heute = _dt.datetime.now(_dt.timezone.utc).date()
    warnungen: list[str] = []
    ausgabe_puffer: list[str] = []

    def log(text: str = "") -> None:
        """Puffert, statt sofort zu drucken -- Warnungen sollen ganz oben
        im Job-Log stehen (Auftrag), stehen aber erst nach der Berechnung
        fest. Der tatsaechliche Druck passiert ganz am Ende von main()."""
        ausgabe_puffer.append(text)

    for markt in sorted(MARKETS_BY_KEY):
        eingaben = historische_eingaben(markt)
        aktuell = aktuelle_eingabe(markt, heute, log)
        if aktuell is not None:
            eingaben.append(aktuell)
        if not eingaben:
            log(f"[{markt}] keine Rankings-Dateien gefunden -- nichts zu tun.")
            continue

        start, ende = download_fenster(eingaben)
        alle_ticker = sorted({t for e in eingaben for t in e.tickers})
        log(f"[{markt}] lade {len(alle_ticker)} Ticker, Fenster {start}..{ende}")
        bundle = download_prices(alle_ticker, start, ende)
        if bundle.stats.failed_chunks:
            warnungen.append(
                f"{markt.upper()}: {len(bundle.stats.failed_chunks)} Download-Block(e) "
                f"endgueltig fehlgeschlagen: {bundle.stats.failed_chunks}"
            )
        if bundle.stats.empty_tickers:
            log(
                f"[{markt}] ohne Kursdaten geliefert: "
                f"{len(bundle.stats.empty_tickers)} Ticker "
                f"({', '.join(sorted(bundle.stats.empty_tickers)[:20])}"
                + (" ...)" if len(bundle.stats.empty_tickers) > 20 else ")")
            )
        log()

        for eingabe in eingaben:
            verarbeite(markt, eingabe, bundle.adjusted, warnungen, log)

    print("=" * 78, flush=True)
    if warnungen:
        print(f"WARNUNGEN ({len(warnungen)}) -- zuerst, siehe Auftrag Kriterium 3/6:", flush=True)
        for w in warnungen:
            print(f"  !! {w}", flush=True)
    else:
        print("Keine Warnungen -- Kontrollrechnung ohne Abweichung > Rundung.", flush=True)
    print("=" * 78, flush=True)
    print(flush=True)
    for zeile in ausgabe_puffer:
        print(zeile, flush=True)

    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
