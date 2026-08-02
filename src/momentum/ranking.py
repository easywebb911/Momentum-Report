"""Monats-Ranking bilden und einfrieren.

ZENTRALE MECHANIK (Literaturtreue): Ein Ranking entsteht EINMAL pro Monat,
zum letzten Handelstag. Danach ist es eingefroren -- werktaegliche Laeufe
aktualisieren nur noch Anzeige-Kurse. Ein Lauf mitten im Monat darf Score,
Rang und Top-5 NICHT veraendern, weil die Evidenz monatlich ist.

Technisch durchgesetzt: eine einmal geschriebene Ranking-Datei wird nie
wieder ueberschrieben (write_ranking weigert sich). Die Dateien enthalten
bewusst KEINEN Erzeugungs-Zeitstempel, damit "zweimal derselbe Stichtag auf
denselben Daten" byte-identische Dateien ergibt.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .config import (
    LIQUIDITY_MIN_MEDIAN_TURNOVER,
    LIQUIDITY_WINDOW_MONTHS,
    MIN_UNIVERSE_COVERAGE,
    SCHEMA_VERSION,
    TOP_N,
    WEIGHT_HIGH_52W,
    WEIGHT_MOMENTUM_12_1,
    Market,
)
from .data import PriceBundle
from .scoring import (
    InsufficientHistory,
    combined_score,
    high_52w_ratio,
    index_12m_return,
    median,
    momentum_12_1,
    ordinal_ranks,
    percentile_ranks,
    shift_month,
)
from .universe import Universe

Date = _dt.date

# Erster Stichtag ueberhaupt: rueckwirkend der letzte Handelstag Juli 2026.
START_RANKING_MONTH = (2026, 7)

RANKING_DIR = Path("data/rankings")


class RankingNotPossible(Exception):
    """Ranking kann nicht literaturtreu gebildet werden -- lauter Abbruch."""


# --------------------------------------------------------------------------
# Stichtags-Mechanik
# --------------------------------------------------------------------------


def is_last_weekday_of_month(day: Date) -> bool:
    """True, wenn nach `day` kein Werktag mehr in diesem Monat folgt."""
    probe = day + _dt.timedelta(days=1)
    while probe.month == day.month:
        if probe.weekday() < 5:
            return False
        probe += _dt.timedelta(days=1)
    return True


def due_months(today: Date, start: tuple[int, int] = START_RANKING_MONTH) -> list[tuple[int, int]]:
    """Monate, fuer die bis heute ein Ranking vorliegen muss.

    Regel, bewusst feiertagsfest formuliert:
      (a) Jeder ABGESCHLOSSENE Monat ist faellig -- dadurch holt der erste
          Lauf eines Monats ein wegen Feiertag oder Stoerung ausgefallenes
          Ranking rueckwirkend und mit korrektem Stichtag nach.
      (b) Der laufende Monat ist zusaetzlich faellig, sobald der Lauf am
          letzten WERKTAG des Monats stattfindet -- so kommt das Ranking im
          Normalfall noch am Stichtag selbst.
    Der Stichtag ist in beiden Faellen der letzte Handelstag des Monats,
    wie ihn die Indexreihe ausweist (siehe resolve_asof).
    """
    last = (today.year, today.month)
    if not is_last_weekday_of_month(today):
        last = shift_month(today.year, today.month, -1)
    out: list[tuple[int, int]] = []
    cursor = start
    guard = 0
    while cursor <= last and guard < 600:
        out.append(cursor)
        cursor = shift_month(cursor[0], cursor[1], +1)
        guard += 1
    return out


def resolve_asof(index_series: dict[Date, float], year: int, month: int, today: Date) -> Date:
    """Letzter Handelstag des Monats laut Indexreihe, hoechstens heute.

    Der Marktindex dient als Handelskalender: er hat genau an Handelstagen
    einen Kurs. Damit braucht das Tool keine gepflegte Feiertagsliste.
    """
    days = [d for d in index_series if d.year == year and d.month == month and d <= today]
    if not days:
        raise RankingNotPossible(
            f"Kein Indexkurs im Monat {year}-{month:02d} -- Stichtag nicht bestimmbar."
        )
    return max(days)


# --------------------------------------------------------------------------
# Handelbarkeits-Filter (KEIN Signal)
# --------------------------------------------------------------------------


def median_turnover(series: dict[Date, float], asof: Date) -> float | None:
    """Median-Tagesumsatz der letzten 3 Monate vor dem Stichtag."""
    start_year, start_month = shift_month(asof.year, asof.month, -LIQUIDITY_WINDOW_MONTHS)
    window_start = _dt.date(start_year, start_month, 1)
    values = [v for d, v in series.items() if window_start <= d <= asof and v > 0]
    if not values:
        return None
    return median(values)


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------


def build_ranking(
    market: Market,
    universe: Universe,
    bundle: PriceBundle,
    index_series: dict[Date, float],
    asof: Date,
) -> dict:
    """Das vollstaendige, eingefrorene Monats-Ranking eines Marktes.

    Reihenfolge der Schritte ist inhaltlich bedeutsam:
      1. Handelbarkeits-Filter (Liquiditaet) -- reduziert nur die Auswahl
      2. Kennzahlen je Titel (12-1, 52W-Naehe)
      3. Perzentil-Raenge NUR innerhalb dieses Marktes (Beleg within_market)
      4. Score = gleichgewichtetes Mittel beider Perzentile (50/50),
         Sortierung mit deterministischem Gleichstandsbruch
    """
    universe_tickers = list(universe.tickers)
    delivered = [t for t in universe_tickers if t in bundle.adjusted]
    coverage = len(delivered) / len(universe_tickers)
    if coverage < MIN_UNIVERSE_COVERAGE:
        raise RankingNotPossible(
            f"{market.key}: nur {coverage:.1%} des Universums mit Kursen "
            f"({len(delivered)}/{len(universe_tickers)}), Mindestabdeckung "
            f"{MIN_UNIVERSE_COVERAGE:.0%}. Lieber kein Stichtag als ein "
            f"Stichtag auf Luecken."
        )

    liquid: list[str] = []
    illiquid = 0
    for ticker in delivered:
        turnover = median_turnover(bundle.turnover.get(ticker, {}), asof)
        if turnover is None or turnover < LIQUIDITY_MIN_MEDIAN_TURNOVER:
            illiquid += 1
            continue
        liquid.append(ticker)

    momentum: dict[str, float] = {}
    high52: dict[str, float] = {}
    closes: dict[str, float] = {}
    skipped_history: list[str] = []
    for ticker in liquid:
        prices = bundle.adjusted[ticker]
        try:
            momentum[ticker] = momentum_12_1(prices, asof)
            high52[ticker] = high_52w_ratio(prices, asof)
            closes[ticker] = float(prices[asof])
        except (InsufficientHistory, KeyError):
            momentum.pop(ticker, None)
            high52.pop(ticker, None)
            skipped_history.append(ticker)

    if not momentum:
        raise RankingNotPossible(f"{market.key}: kein Titel mit vollstaendiger Historie")

    pct_mom = percentile_ranks(momentum)
    pct_high = percentile_ranks(high52)
    # Zusaetzlich die Platzziffern je Zutat. Sie gehen NICHT in die Rechnung
    # ein -- sie machen sichtbar, woher der Endscore kommt. Bei 50/50 ist
    # genau das die interessante Information: ein Titel kann vorn stehen,
    # weil er in einer Zutat sehr stark und in der anderen mittelmaessig
    # ist. Das soll man sehen, statt es glauben zu muessen.
    rang_mom = ordinal_ranks(momentum)
    rang_high = ordinal_ranks(high52)

    rows = []
    for ticker in momentum:
        score = combined_score(pct_mom[ticker], pct_high[ticker])
        rows.append(
            {
                "ticker": ticker,
                "name": universe.name_of(ticker),
                "score": round(score, 6),
                "momentum_12_1": round(momentum[ticker], 8),
                "high_52w": round(high52[ticker], 8),
                "perzentil_momentum": round(pct_mom[ticker], 8),
                "perzentil_high_52w": round(pct_high[ticker], 8),
                "rank_12_1": rang_mom[ticker],
                "rank_52w": rang_high[ticker],
                "kurs_stichtag": round(closes[ticker], 4),
            }
        )
    # Gleichstand deterministisch: hoeherer Score zuerst, dann Ticker A->Z.
    rows.sort(key=lambda r: (-r["score"], r["ticker"]))
    for position, row in enumerate(rows, start=1):
        row["rang"] = position

    index_return = index_12m_return(index_series, asof)

    return {
        "schema": SCHEMA_VERSION,
        "markt": market.key,
        "markt_name": market.name,
        "waehrung": market.currency,
        "ranking_monat": f"{asof.year:04d}-{asof.month:02d}",
        "stichtag": asof.isoformat(),
        "universum": {
            "bezeichnung": universe.label,
            "herkunft": universe.origin,
            "stand": universe.as_of,
            "titel_gesamt": len(universe_tickers),
        },
        "methode": {
            "gewicht_momentum_12_1": WEIGHT_MOMENTUM_12_1,
            "gewicht_high_52w": WEIGHT_HIGH_52W,
            "liquiditaets_schwelle": LIQUIDITY_MIN_MEDIAN_TURNOVER,
            "liquiditaets_fenster_monate": LIQUIDITY_WINDOW_MONTHS,
        },
        "trend_ampel": {
            "index_ticker": market.index_ticker,
            "index_name": market.index_name,
            "rendite_12m": round(index_return, 8),
            "warnung": index_return <= 0,
        },
        "abdeckung": {
            "universum": len(universe_tickers),
            "mit_kursen": len(delivered),
            "nach_handelbarkeit": len(liquid),
            "ohne_handelbarkeit": illiquid,
            "ohne_ausreichende_historie": sorted(skipped_history),
            "bewertet": len(rows),
        },
        "rangliste": rows,
        "top": [r["ticker"] for r in rows[:TOP_N]],
    }


# --------------------------------------------------------------------------
# Einfrieren / Persistenz
# --------------------------------------------------------------------------


def ranking_path(market_key: str, year: int, month: int, root: Path = RANKING_DIR) -> Path:
    return Path(root) / f"{market_key}_{year:04d}-{month:02d}.json"


def dump_ranking(ranking: dict) -> str:
    """Kanonische, stabile JSON-Form -- Grundlage der Byte-Identitaet."""
    return json.dumps(ranking, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_ranking(ranking: dict, root: Path = RANKING_DIR) -> Path:
    """Ranking schreiben -- und ein bestehendes NIE ueberschreiben."""
    year, month = (int(x) for x in ranking["ranking_monat"].split("-"))
    path = ranking_path(ranking["markt"], year, month, root)
    if path.exists():
        raise RankingNotPossible(
            f"{path} existiert bereits. Ein gebildetes Monats-Ranking ist "
            f"eingefroren und wird nicht neu geschrieben."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_ranking(ranking), encoding="utf-8")
    return path


def read_ranking(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_ranking(market_key: str, root: Path = RANKING_DIR) -> dict | None:
    """Juengstes vorhandenes Ranking eines Marktes (oder None)."""
    root = Path(root)
    if not root.exists():
        return None
    files = sorted(root.glob(f"{market_key}_*.json"))
    if not files:
        return None
    return read_ranking(files[-1])


def existing_months(market_key: str, root: Path = RANKING_DIR) -> set[tuple[int, int]]:
    root = Path(root)
    if not root.exists():
        return set()
    months = set()
    for path in root.glob(f"{market_key}_*.json"):
        stem = path.stem.split("_", 1)[1]
        year, month = stem.split("-")
        months.add((int(year), int(month)))
    return months
