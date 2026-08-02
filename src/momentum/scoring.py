"""Die Rechenkerne. Reine Funktionen, keine Netzwerk- oder Dateizugriffe.

Jede Funktion nennt im Docstring ihren Primaerbeleg (Schluessel aus
sources.py). Die Tests in tests/unit pruefen NICHT, ob die Zahlen "gut"
sind -- sie pruefen, ob exakt die dokumentierte Formel gerechnet wird.
"""

from __future__ import annotations

import datetime as _dt
import math
from collections.abc import Mapping, Sequence

from .config import (
    HIGH_52W_WINDOW_DAYS,
    MOMENTUM_LOOKBACK_MONTHS,
    MOMENTUM_SKIP_MONTHS,
    SCORE_SCALE,
    WEIGHT_HIGH_52W,
    WEIGHT_MOMENTUM_12_1,
)

Date = _dt.date
# Kursreihe: Datum -> bereinigter Schlusskurs. Bewusst ein einfaches Mapping
# statt pandas, damit die Tests die Eingabe von Hand hinschreiben koennen.
Series = Mapping[Date, float]


class InsufficientHistory(Exception):
    """Zu wenig Historie fuer die dokumentierte Formel -- Titel faellt raus.

    Bewusst eine Ausnahme statt eines Ersatzwerts: ein fehlender Stuetzpunkt
    darf niemals still zu einer 0 werden.
    """


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """Monatsarithmetik ohne Fremdbibliothek. delta darf negativ sein."""
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def month_end_close(prices: Series, year: int, month: int, asof: Date) -> float:
    """Schlusskurs des letzten Handelstags in (year, month), hoechstens asof.

    "Letzter Handelstag" heisst hier: der spaeteste Tag dieses Monats, fuer
    den die Datenquelle ueberhaupt einen Kurs geliefert hat. Feiertage und
    Handelsruhe brauchen deshalb keinen eigenen Kalender.
    """
    candidates = [d for d in prices if d.year == year and d.month == month and d <= asof]
    if not candidates:
        raise InsufficientHistory(f"kein Kurs in {year}-{month:02d} bis {asof}")
    return float(prices[max(candidates)])


def momentum_12_1(prices: Series, asof: Date) -> float:
    """12-1-Momentum am Stichtag asof.

    Beleg: momentum_12_1 (Jegadeesh & Titman 1993, The Journal of Finance),
    skip_month (Jegadeesh 1990), total_return (bereinigte Kurse).

    Formel, exakt wie dokumentiert -- M ist der Monat des Stichtags:

        AdjClose(letzter Handelstag Monat M-1)
        --------------------------------------  -  1
        AdjClose(letzter Handelstag Monat M-12)

    Der juengste Monat M wird UEBERSPRUNGEN. Das ist Teil der belegten
    Rezeptur (kurzfristige Umkehr, Beleg skip_month) und keine Option:
    wer stattdessen Monat M in den Zaehler nimmt, rechnet eine andere
    Kennzahl. tests/unit/test_skip_month_mutation.py haelt genau das fest.
    """
    num_year, num_month = shift_month(asof.year, asof.month, -MOMENTUM_SKIP_MONTHS)
    den_year, den_month = shift_month(asof.year, asof.month, -MOMENTUM_LOOKBACK_MONTHS)
    numerator = month_end_close(prices, num_year, num_month, asof)
    denominator = month_end_close(prices, den_year, den_month, asof)
    if denominator <= 0:
        raise InsufficientHistory("Nennerkurs <= 0")
    return numerator / denominator - 1.0


def high_52w_ratio(prices: Series, asof: Date) -> float:
    """Naehe zum 52-Wochen-Hoch, 0..1.

    Beleg: high_52w (George & Hwang 2004, The Journal of Finance),
    total_return (bereinigte Kurse).

        AdjClose(asof) / max(AdjClose der letzten 52 Wochen)

    Fenster: 364 Kalendertage vor dem Stichtag, Stichtag eingeschlossen.
    Das Maximum wird ueber TAGES-SCHLUSSKURSE gebildet, nicht ueber
    Intraday-Hochs -- die uebliche Replikations-Konvention. So steht es auch
    auf der Methodik-Seite; ein Intraday-Hoch ergaebe systematisch kleinere
    Werte und waere eine andere Kennzahl.
    """
    if asof not in prices:
        raise InsufficientHistory(f"kein Kurs am Stichtag {asof}")
    window_start = asof - _dt.timedelta(days=HIGH_52W_WINDOW_DAYS)
    window = [float(v) for d, v in prices.items() if window_start <= d <= asof]
    if not window:
        raise InsufficientHistory("52-Wochen-Fenster leer")
    highest = max(window)
    if highest <= 0:
        raise InsufficientHistory("52-Wochen-Hoch <= 0")
    return float(prices[asof]) / highest


def percentile_ranks(values: Mapping[str, float]) -> dict[str, float]:
    """Perzentil-Raenge 0..1 innerhalb EINES Marktes.

    Beleg: within_market (Rouwenhorst 1998) -- Raenge werden nie ueber
    Maerkte hinweg gemischt; diese Funktion sieht immer nur die Titel eines
    Marktes, weil ranking.py sie je Markt getrennt aufruft.

    Konvention, bewusst simpel und exakt nachrechenbar:
      * aufsteigend sortieren nach (Wert, Ticker)
      * Rang i (0-basiert) -> Perzentil i / (n - 1)
      * schlechtester Titel 0.0, bester 1.0
      * Gleichstaende werden NICHT gemittelt, sondern deterministisch
        alphabetisch nach Ticker gebrochen; der alphabetisch fruehere Ticker
        erhaelt das kleinere Perzentil. Damit ist die Rangfolge bei jedem
        Lauf byte-identisch reproduzierbar.
      * n == 1 -> 1.0 (einziger Titel ist zugleich bester)
    """
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda kv: (kv[1], kv[0]))
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 1.0}
    return {ticker: i / (n - 1) for i, (ticker, _) in enumerate(ordered)}


def ordinal_ranks(values: Mapping[str, float]) -> dict[str, int]:
    """Platzziffern 1..n innerhalb EINES Marktes -- 1 ist der beste Titel.

    Bewusst aus DERSELBEN Sortierung wie percentile_ranks abgeleitet: beide
    ordnen nach (Wert, Ticker) aufsteigend. Damit koennen die angezeigte
    Platzziffer und das gerechnete Perzentil nicht auseinanderlaufen -- der
    beste Titel hat immer zugleich Perzentil 1.0 und Platz 1.

    Gleichstaende werden wie dort alphabetisch gebrochen, nicht gemittelt.
    """
    ordered = sorted(values.items(), key=lambda kv: (kv[1], kv[0]))
    n = len(ordered)
    return {ticker: n - i for i, (ticker, _) in enumerate(ordered)}


def combined_score(pct_momentum: float, pct_high_52w: float) -> float:
    """Endscore 0..100 = 50 x Perzentil(12-1) + 50 x Perzentil(52W-Naehe).

    GLEICHGEWICHTET, und das ist eine Aussage: Die Literatur liefert KEIN
    Mischverhaeltnis fuer diese beiden Zutaten -- sie vergleicht sie als
    getrennte Strategien. Gleichgewichtung ist die Konvention der
    Komposit-Arbeiten und zugleich die einzige Wahl, die nichts behauptet,
    was nicht belegt ist. Die Gewichte stehen als benannte Konstanten an
    genau einer Stelle (config.WEIGHT_*), samt Begruendung.

    Belege: momentum_12_1, high_52w, within_market.
    """
    return SCORE_SCALE * (
        WEIGHT_MOMENTUM_12_1 * pct_momentum + WEIGHT_HIGH_52W * pct_high_52w
    )


def index_12m_return(prices: Series, asof: Date) -> float:
    """12-Monats-Rendite des Marktindex fuer die Trend-Ampel.

    Beleg: trend_filter (Moskowitz/Ooi/Pedersen 2012), Warnlage-Formulierung
    momentum_crash (Daniel & Moskowitz 2016).

        AdjClose(asof) / AdjClose(letzter Handelstag Monat M-12)  -  1

    Hier wird KEIN Monat uebersprungen: die Zeitreihen-Momentum-Arbeit misst
    die vollen zwoelf Monate bis zum Stichtag. Reine Anzeige, greift nie ins
    Ranking ein.
    """
    if asof not in prices:
        raise InsufficientHistory(f"kein Indexkurs am Stichtag {asof}")
    base_year, base_month = shift_month(asof.year, asof.month, -MOMENTUM_LOOKBACK_MONTHS)
    base = month_end_close(prices, base_year, base_month, asof)
    if base <= 0:
        raise InsufficientHistory("Index-Basiskurs <= 0")
    return float(prices[asof]) / base - 1.0


def median(values: Sequence[float]) -> float:
    """Median ohne numpy -- damit die Handelbarkeits-Pruefung testbar bleibt."""
    if not values:
        raise ValueError("Median einer leeren Reihe")
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return (float(ordered[mid - 1]) + float(ordered[mid])) / 2.0


def is_finite(value: object) -> bool:
    """True nur fuer echte, endliche Zahlen (NaN/inf/None fallen raus)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))
