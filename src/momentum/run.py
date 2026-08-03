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
from .notify import push_new_ranking, push_run_failed, push_test
from .ranking import (
    RANKING_DIR,
    RankingNotPossible,
    build_ranking,
    due_months,
    existing_months,
    latest_ranking,
    resolve_asof,
    write_ranking,
)
from .meta import load_meta
from .render import MarketView, last_weekday_of_month, render_index, render_methodik
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


def process_market(
    market: Market,
    today: Date,
    *,
    downloader=None,
    ranking_root: Path = RANKING_DIR,
    data_root: Path = DATA_DIR,
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

        for year, month in needed:
            asof = resolve_asof(index_series, year, month, today)
            log(f"[{market.key}] Ranking {year:04d}-{month:02d}, Stichtag {asof}")
            ranking = build_ranking(market, universe, bundle, index_series, asof)
            write_ranking(ranking, ranking_root)
            new_ranking = ranking
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


def _github_output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None, *, downloader=None) -> int:
    """`downloader` ist die Test-Naht: ohne ihn laeuft der echte Abruf."""
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
    args = parser.parse_args(argv)
    today = Date.fromisoformat(args.today) if args.today else Date.today()
    log(f"Momentum-Report Lauf, Datum {today}")

    views: list[MarketView] = []
    new_rankings: list[dict] = []
    statuses: list[dict] = []

    for market in MARKETS:
        view, new_ranking, status = process_market(market, today, downloader=downloader)
        views.append(view)
        statuses.append(status)
        if new_ranking:
            new_rankings.append(new_ranking)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(render_index(views, today), encoding="utf-8")
    (DOCS_DIR / "methodik.html").write_text(render_methodik(), encoding="utf-8")

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

    _github_output("ranking_created", "true" if new_rankings else "false")

    if new_rankings and not args.no_push:
        entries = []
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
        push_new_ranking(entries)

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
