"""Einstiegspunkt des werktaeglichen Laufs.

Ablauf je Markt:
  1. Universum laden (Platzhalter -> lauter Abbruch, nie stiller Rueckfall)
  2. Pruefen, ob fuer einen Monat noch ein Ranking fehlt
  3. NUR falls ja: volles Universum laden und das Monats-Ranking bilden;
     danach ist es eingefroren und wird nie wieder ueberschrieben
  4. Sonst: ausschliesslich Anzeige-Kurse der bestehenden Top-5 nachladen
  5. Seiten neu erzeugen

Punkt 3/4 ist die technische Durchsetzung der Monats-Einfrierung: an einem
gewoehnlichen Tag werden die Daten, die ein Ranking veraendern koennten,
gar nicht erst beschafft.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import traceback
from pathlib import Path

from .config import HISTORY_DAYS, MARKETS, TOP_N, Market
from .data import PriceBundle, download_prices
from .evaluation import (
    EVAL_DIR,
    all_evaluations,
    build_evaluation,
    evaluation_path,
    write_evaluation,
)
from .ishares import (
    ISHARES_DE,
    ISHARES_US,
    ANZAHL_ERWARTET_US,
    QuelleUnbrauchbar,
    lade_bestandsliste,
    parse_ishares_holdings,
    us_symbol_zu_yahoo,
)
from .kursvergleich import (
    ABGESCHALTET,
    NICHT_VORGESEHEN,
    Vergleich,
    abbruchtext,
    kurzfassung_aus_report,
    vergleiche,
)
from . import kursvergleich_us
from .notify import push_new_ranking, push_run_failed, push_test
from .ranking import (
    RANKING_DIR,
    RankingNotPossible,
    build_ranking,
    due_months,
    existing_months,
    latest_ranking,
    ranking_path,
    read_ranking,
    resolve_asof,
    write_ranking,
)
from .meta import load_meta
from .riskfree import IRX_TICKER, QUELLE_FEHLT, riskfree_12m
from .render import (
    MarketView,
    last_weekday_of_month,
    render_evaluation,
    render_index,
    render_konfluenz,
    render_methodik,
)
from .scoring import shift_month
from .universe import UniverseNotReady, load_universe

Date = _dt.date

DOCS_DIR = Path("docs")
DATA_DIR = Path("data")


def log(message: str) -> None:
    print(message, flush=True)


def _prices_path(market_key: str, root: Path = DATA_DIR) -> Path:
    return Path(root) / f"kurse_{market_key}.json"


def _download_window(needed: list[tuple[int, int]], today: Date) -> tuple[Date, Date]:
    """Zeitfenster fuer den Download."""
    earliest = today
    for year, month in needed:
        earliest = min(earliest, Date(year, month, 1))
    return earliest - _dt.timedelta(days=HISTORY_DAYS), today


def _latest_common_date(bundle: PriceBundle, tickers: list[str]) -> Date | None:
    """Juengstes Datum, an dem ALLE gefragten Titel einen Kurs haben."""
    sets = [set(bundle.adjusted.get(t, {})) for t in tickers]
    if not sets or any(not s for s in sets):
        return None
    common = set.intersection(*sets)
    return max(common) if common else None


def _zins_reihe(start: Date, end: Date, *, downloader=None) -> dict[Date, float]:
    """Die ^IRX-Reihe holen — fail-soft, ohne den Lauf zu gefaehrden.

    Der Abruf laeuft bewusst als EIGENER Aufruf, nicht zusammen mit dem
    Index: der Einzelabruf ist die Form, die data._extract sicher zuordnen
    kann. Faellt er aus, gibt es hier ein leeres Dict und die Ampel rechnet
    sichtbar ohne Zins-Abzug.
    """
    try:
        buendel = download_prices([IRX_TICKER], start, end, downloader=downloader)
    except Exception as exc:  # noqa: BLE001 - die Ampel ist Anzeige, kein Gatter
        log(f"[zins] {IRX_TICKER} nicht abrufbar ({type(exc).__name__}) — {QUELLE_FEHLT}")
        return {}
    return buendel.adjusted.get(IRX_TICKER) or {}


def _bestandslisten(heute: Date, *, oeffner=None) -> list:
    """Die drei iShares-Bestandslisten holen und mit dem ECHTEN Parser lesen.

    Derselbe Parser samt Gattern, aus dem auch das Universum entsteht
    (momentum/ishares.py) -- ein zweiter Leser wuerde einen anderen
    Vertrag pruefen als den, der zaehlt.

    Die ISIN-Reserve bleibt bewusst AUS: sie loeste je Zeile eine
    Yahoo-Suche aus, und fuer den Kursvergleich ist ein Titel ohne Ticker
    ohnehin nicht vergleichbar.
    """
    oeffner = oeffner or lade_bestandsliste
    return [
        parse_ishares_holdings(oeffner(quelle), quelle.index_name, heute=heute)
        for quelle in ISHARES_DE
    ]


def _bestandsliste_us(heute: Date, *, oeffner=None) -> tuple:
    """SXR8 primaer, IUSA als dokumentierter Ausweich (Easys Entscheid vom
    14.08.2026 zu Stufe 2b). Scheitert SXR8 aus IRGENDEINEM Grund -- auch
    unerwartet, nicht nur QuelleUnbrauchbar --, wird IUSA versucht, bevor
    der Vergleich als Ganzes entfaellt. Gibt (Befund, Fondsname) zurueck.
    """
    oeffner = oeffner or lade_bestandsliste
    gruende: list[str] = []
    for quelle in ISHARES_US:
        try:
            inhalt = oeffner(quelle)
            befund = parse_ishares_holdings(
                inhalt, quelle.index_name, heute=heute,
                ticker_uebersetzer=us_symbol_zu_yahoo,
                erwartete_anzahl=ANZAHL_ERWARTET_US,
            )
            return befund, quelle.xetra
        except QuelleUnbrauchbar as exc:
            gruende.append(f"{quelle.xetra}: {exc}")
        except Exception as exc:  # noqa: BLE001 - Ausweich statt Abbruch
            gruende.append(f"{quelle.xetra}: {type(exc).__name__}: {exc}")
    raise QuelleUnbrauchbar("SXR8 UND IUSA unbrauchbar — " + " | ".join(gruende))


def _kursvergleich(
    market: Market,
    bundle: PriceBundle,
    universum: tuple[str, ...],
    heute: Date,
    *,
    oeffner=None,
    splits_oeffner=None,
    aktiv: bool = True,
):
    """Das Verdikt der zweiten Kursquelle -- fail-soft, aber nie still.

    Jeder Fehlschlag auf dem Weg (Datei nicht abrufbar, Format geaendert,
    Gatter gerissen) wird zu "entfallen" MIT Grund, nicht zu einem stillen
    Durchwinken und nicht zu einem Abbruch: dass die zweite Quelle heute
    nicht antwortet, sagt nichts ueber die Richtigkeit der ersten.
    Verweigert wird nur, wenn beide Quellen antworten und sich
    widersprechen.
    """
    if market.key == "de":
        if not aktiv:
            return Vergleich.entfaellt(ABGESCHALTET)
        try:
            befunde = _bestandslisten(heute, oeffner=oeffner)
        except QuelleUnbrauchbar as exc:
            return Vergleich.entfaellt(f"Bestandsliste unbrauchbar — {exc}")
        except Exception as exc:  # noqa: BLE001 - die Zweitquelle darf nie der Grund sein
            return Vergleich.entfaellt(
                f"Bestandslisten nicht lesbar ({type(exc).__name__}: {exc})"
            )
        return vergleiche(befunde, bundle.close, universum=set(universum))
    if market.key == "us":
        if not aktiv:
            return kursvergleich_us.Vergleich.entfaellt(ABGESCHALTET)
        try:
            befund, fonds = _bestandsliste_us(heute, oeffner=oeffner)
        except QuelleUnbrauchbar as exc:
            return kursvergleich_us.Vergleich.entfaellt(f"Bestandsliste unbrauchbar — {exc}")
        except Exception as exc:  # noqa: BLE001 - die Zweitquelle darf nie der Grund sein
            return kursvergleich_us.Vergleich.entfaellt(
                f"Bestandsliste nicht lesbar ({type(exc).__name__}: {exc})"
            )
        return kursvergleich_us.vergleiche(
            befund, fonds, bundle.close, universum=set(universum),
            splits_oeffner=splits_oeffner,
        )
    return Vergleich.entfaellt(NICHT_VORGESEHEN)


def process_market(
    market: Market,
    today: Date,
    *,
    downloader=None,
    ranking_root: Path = RANKING_DIR,
    data_root: Path = DATA_DIR,
    evaluation_root: Path = EVAL_DIR,
    zins_oeffner=None,
    bestand_oeffner=None,
    splits_oeffner=None,
    kursvergleich_aktiv: bool = True,
) -> tuple[MarketView, dict | None, dict]:
    """Einen Markt verarbeiten. Gibt (Ansicht, neues Ranking oder None, Status)."""
    universe = load_universe(market.universe_file)
    log(
        f"[{market.key}] Universum '{universe.label}', Stand {universe.as_of}, "
        f"{len(universe.entries)} Titel"
    )

    have = existing_months(market.key, ranking_root)
    needed = [m for m in due_months(today) if m not in have]
    status: dict = {
        "markt": market.key,
        "faellige_monate_offen": [f"{y:04d}-{m:02d}" for y, m in needed],
    }

    new_ranking: dict | None = None

    if needed:
        # --- Stichtags-Lauf: volles Universum ---------------------------
        start, end = _download_window(needed, today)
        log(f"[{market.key}] Stichtags-Lauf: lade {len(universe.entries)} Titel {start}..{end}")
        index_bundle = download_prices([market.index_ticker], start, end, downloader=downloader)
        index_series = index_bundle.adjusted.get(market.index_ticker)
        if not index_series:
            raise RankingNotPossible(
                f"[{market.key}] Keine Indexdaten fuer {market.index_ticker} — "
                f"ohne Handelskalender kein Stichtag."
            )
        bundle = download_prices(list(universe.tickers), start, end, downloader=downloader)
        status["daten"] = bundle.stats.as_dict()

        # --- Das Vergleichsgatter, VOR jeder Ranking-Bildung --------------
        # Die Reihenfolge ist nicht Geschmack: verweigert der Vergleich,
        # darf kein Ranking entstanden und erst recht keins geschrieben
        # worden sein.
        vergleich = _kursvergleich(
            market, bundle, universe.tickers, today,
            oeffner=bestand_oeffner, splits_oeffner=splits_oeffner,
            aktiv=kursvergleich_aktiv,
        )
        for zeile in vergleich.protokoll():
            log(f"[{market.key}] {zeile}")
        status["kursvergleich"] = vergleich.als_status()
        if vergleich.verweigert:
            # Welcher Abbruchtext stimmt, haengt am Markt: die beiden
            # Gatter haben verschiedene Schwellen und verschiedene Texte
            # ueber sich selbst (siehe kursvergleich_us.py).
            text_erzeuger = abbruchtext if market.key == "de" else kursvergleich_us.abbruchtext
            raise RankingNotPossible(text_erzeuger(vergleich, market.key))

        # Der Geldmarktsatz gehoert zur Waehrung; fuer USD kommt er aus
        # derselben Kursquelle, fuer EUR aus der EZB (siehe riskfree.py).
        irx = _zins_reihe(start, end, downloader=downloader) if market.currency == "USD" else {}

        for year, month in needed:
            asof = resolve_asof(index_series, year, month, today)
            log(f"[{market.key}] Ranking {year:04d}-{month:02d}, Stichtag {asof}")
            zins = riskfree_12m(
                market.currency, index_series, asof,
                irx_series=irx, oeffner=zins_oeffner,
            )
            if zins[0] is None:
                # Niemals still: der Ausfall steht im Log UND im Report.
                log(
                    f"[{market.key}] Zinsquelle {QUELLE_FEHLT} — Trend-Kriterium "
                    f"rechnet ohne Zins-Abzug (Rendite gegen null)."
                )
            else:
                log(f"[{market.key}] Geldmarkt 12M {zins[0] * 100:.2f} % ({zins[1]})")
            ranking = build_ranking(
                market, universe, bundle, index_series, asof,
                riskfree=zins, kursvergleich=vergleich,
            )
            write_ranking(ranking, ranking_root)
            new_ranking = ranking

            # Monats-Rueckblick fuer den VORANGEGANGENEN Monat: reines
            # Nebenprodukt, kein zusaetzlicher Kursabruf -- der Kurs der
            # damaligen Top-5 steht bereits in `bundle` (siehe
            # evaluation.py). Nur wenn es ein Vorgaenger-Ranking gibt UND
            # dessen Rueckblick noch nicht existiert -- beides normal beim
            # allerersten Monat bzw. bei einem bereits erfassten Rueckblick.
            prev_year, prev_month = shift_month(year, month, -1)
            prev_ranking_datei = ranking_path(market.key, prev_year, prev_month, ranking_root)
            eval_datei = evaluation_path(market.key, prev_year, prev_month, evaluation_root)
            if prev_ranking_datei.exists() and not eval_datei.exists():
                prev_ranking = read_ranking(prev_ranking_datei)
                evaluation = build_evaluation(prev_ranking, market, bundle, asof)
                write_evaluation(evaluation, evaluation_root)
                log(
                    f"[{market.key}] Monats-Rueckblick {prev_year:04d}-{prev_month:02d} "
                    f"geschrieben (Endkurs vom {asof})."
                )
        current = new_ranking
        top = current["top"]
        price_bundle = bundle
    else:
        # --- Anzeige-Lauf: NUR die Kurse der eingefrorenen Top-5 --------
        current = latest_ranking(market.key, ranking_root)
        if current is None:
            log(f"[{market.key}] Noch kein Ranking vorhanden.")
            return (
                MarketView(market, {}, None, {}, last_weekday_of_month(today.year, today.month)),
                None,
                status,
            )
        top = current["top"][:TOP_N]
        log(f"[{market.key}] Anzeige-Lauf: nur Kurse fuer {', '.join(top)}")
        price_bundle = download_prices(
            top, today - _dt.timedelta(days=14), today, downloader=downloader
        )
        status["daten"] = price_bundle.stats.as_dict()

    price_asof = _latest_common_date(price_bundle, list(top))
    prices = (
        {t: price_bundle.adjusted[t][price_asof] for t in top if t in price_bundle.adjusted}
        if price_asof
        else {}
    )
    if price_asof:
        _prices_path(market.key, data_root).parent.mkdir(parents=True, exist_ok=True)
        _prices_path(market.key, data_root).write_text(
            json.dumps(
                {"stichtag_kurse": price_asof.isoformat(), "kurse": prices},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    status["kurse_vom"] = price_asof.isoformat() if price_asof else None

    ranking_month = tuple(int(x) for x in current["ranking_monat"].split("-"))
    nxt_year, nxt_month = shift_month(ranking_month[0], ranking_month[1], +1)
    view = MarketView(
        market=market,
        ranking=current,
        price_asof=price_asof,
        prices=prices,
        next_ranking_date=last_weekday_of_month(nxt_year, nxt_month),
        # Beschreibende Angaben zur Anzeige. Fehlt die Datei, bleibt das
        # Dict leer und die Karten zeigen "—" -- der Lauf laeuft weiter.
        meta=load_meta(market.key),
    )
    return view, new_ranking, status


def _schreibe_top5(views: list[MarketView], docs_root: Path) -> None:
    """Die eingefrorenen Top-5 als eigene, kleine Datei — rein additiv.

    Sie aendert nichts an bestehenden Dateien und wird von nichts in diesem
    Werkzeug gelesen. Sie existiert, damit die Konfluenz-Seite (und
    grundsaetzlich jeder andere Leser) an die Top-5 kommt, ohne das
    vollstaendige Ranking oder die HTML-Seite auseinandernehmen zu muessen.

    Ohne Zeitstempel und mit sortierten Schluesseln: die Datei aendert sich
    nur, wenn sich ihr Inhalt aendert.
    """
    maerkte: dict[str, dict] = {}
    for view in views:
        if not view.ranking:
            continue
        stichtag = view.ranking["stichtag"]
        maerkte[view.market.key] = {
            "name": view.market.name,
            "stichtag": stichtag,
            "top5": [
                {
                    "ticker": row["ticker"],
                    "rang": row["rang"],
                    "score": row["score"],
                    "stichtag": stichtag,
                }
                for row in view.ranking["rangliste"][:TOP_N]
            ],
        }
    if not maerkte:
        return
    ziel = docs_root / "data" / "top5.json"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(
        json.dumps({"schema": 1, "maerkte": maerkte}, ensure_ascii=False,
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    log(f"Top-5-Export geschrieben: {ziel}")


def _github_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def main(
    argv: list[str] | None = None,
    *,
    downloader=None,
    zins_oeffner=None,
    bestand_oeffner=None,
    splits_oeffner=None,
) -> int:
    """`downloader`, `zins_oeffner`, `bestand_oeffner` und `splits_oeffner`
    sind die Test-Naehte: ohne sie laufen der echte Kursabruf, der echte
    EZB-Abruf, der echte Abruf der iShares-Bestandslisten und der echte
    Abruf des Yahoo-Split-Kalenders (nur US, siehe kursvergleich_us.py)."""
    parser = argparse.ArgumentParser(description="Momentum-Report Lauf")
    parser.add_argument("--today", help="Laufdatum JJJJ-MM-TT (nur fuer Tests)")
    parser.add_argument(
        "--no-push", action="store_true", help="Keinen ntfy-Push verschicken"
    )
    parser.add_argument(
        "--testpush",
        action="store_true",
        help="Zusaetzlich EINEN leisen Probe-Push verschicken (Verdrahtung pruefen)",
    )
    parser.add_argument(
        "--ohne-kursvergleich",
        action="store_true",
        help=(
            "Das DE- UND das US-Vergleichsgatter aussetzen. NOTAUS von "
            "Hand: falls ein Gatter am Stichtag faelschlich verweigert, "
            "kommt der Monat so trotzdem zustande. Der Verzicht steht "
            "sichtbar im Report und im Push — still ausgesetzt wird nie."
        ),
    )
    args = parser.parse_args(argv)
    today = Date.fromisoformat(args.today) if args.today else Date.today()
    log(f"Momentum-Report Lauf, Datum {today}")

    views: list[MarketView] = []
    new_rankings: list[dict] = []
    statuses: list[dict] = []

    for market in MARKETS:
        view, new_ranking, status = process_market(
            market, today,
            downloader=downloader,
            zins_oeffner=zins_oeffner,
            bestand_oeffner=bestand_oeffner,
            splits_oeffner=splits_oeffner,
            kursvergleich_aktiv=not args.ohne_kursvergleich,
        )
        views.append(view)
        statuses.append(status)
        if new_ranking:
            new_rankings.append(new_ranking)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(render_index(views, today), encoding="utf-8")
    (DOCS_DIR / "methodik.html").write_text(render_methodik(), encoding="utf-8")
    (DOCS_DIR / "konfluenz.html").write_text(render_konfluenz(), encoding="utf-8")
    evaluations = {m.key: all_evaluations(m.key) for m in MARKETS}
    (DOCS_DIR / "evaluation.html").write_text(
        render_evaluation(evaluations), encoding="utf-8"
    )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "status.json").write_text(
        json.dumps(
            {"lauf_datum": today.isoformat(), "maerkte": statuses},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    _schreibe_top5(views, DOCS_DIR)

    _github_output("ranking_created", "true" if new_rankings else "false")

    if new_rankings and not args.no_push:
        entries = []
        hinweise = []
        for ranking in new_rankings:
            top_row = ranking["rangliste"][0]
            entries.append(
                {
                    "markt": ranking["markt_name"],
                    "stichtag": ranking["stichtag"],
                    "top": top_row["ticker"],
                    "top_name": top_row["name"],
                    "score": top_row["score"],
                }
            )
            # Ein entfallener oder nur knapp bestandener Kursvergleich
            # gehoert in dieselbe Nachricht, nicht in eine zweite: sonst
            # steht die gute Nachricht ohne ihre Einschraenkung da.
            # "entfallen, weil fuer diesen Markt nicht vorgesehen" waere
            # dagegen bei jedem Push dieselbe Zeile -- also weglassen.
            block = ranking.get("kursvergleich") or {}
            if block.get("grund") == NICHT_VORGESEHEN:
                continue
            satz = kurzfassung_aus_report(block) if block else None
            if satz:
                hinweise.append(f"{ranking['markt_name']}: {satz}")
        push_new_ranking(entries, hinweise=hinweise)

    # Verdrahtungsprobe. Sie kommt NUR auf ausdrueckliche Anforderung, laeuft
    # zusaetzlich zum normalen Lauf und ruehrt keine Daten an. --no-push hat
    # Vorrang: wer ausdruecklich keine Pushes will, bekommt auch keine Probe.
    if args.testpush and not args.no_push:
        if push_test():
            log("Testpush: verschickt.")
        else:
            log("Testpush: NICHT verschickt — der Grund steht in den Zeilen darueber.")
    elif args.testpush:
        log("Testpush: uebersprungen, weil --no-push gesetzt ist.")

    log("Lauf beendet.")
    return 0


def cli() -> int:
    """Einstieg fuer die Kommandozeile.

    Ein Abbruch ist hier IMMER laut: deutliche Zeile im Lauf-Log UND
    Fehlschlag-Push mit dem exakten Grund. Der Push wird bewusst hier
    verschickt und nicht erst vom Workflow -- so steht der wirkliche Grund
    drin ("Universum ist Platzhalter") statt eines allgemeinen "Job rot".
    Der Workflow deckt nur noch die Faelle ab, in denen dieses Programm gar
    nicht erst startet (siehe .github/workflows/lauf.yml).
    """
    try:
        return main()
    except (UniverseNotReady, RankingNotPossible) as exc:
        log("")
        log("=" * 72)
        log(f"LAUF ABGEBROCHEN: {exc}")
        log("Es wurde bewusst nichts veroeffentlicht und nichts eingefroren.")
        log("=" * 72)
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error title=Lauf abgebrochen::{exc}", flush=True)
        push_run_failed(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        push_run_failed(f"Unerwarteter Fehler: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(cli())
