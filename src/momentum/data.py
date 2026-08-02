"""Datenbeschaffung ueber yfinance -- die einzige Stelle mit Netzzugriff.

Grundsatz: bereinigte Kurse (Dividenden UND Splits) fuer alles, was
gerechnet wird -- die Studien messen Gesamtrenditen (Beleg total_return).

Warum der Download mit auto_adjust=False laeuft, obwohl bereinigt gerechnet
wird: mit diesem Schalter liefert Yahoo zusaetzlich zur bereinigten Reihe
('Adj Close') auch den Schlusskurs wie gehandelt ('Close'). Gerechnet wird
ausschliesslich mit 'Adj Close' -- inhaltlich identisch zu auto_adjust=True.
Der unbereinigte 'Close' wird NUR fuer den Handelbarkeits-Filter gebraucht
(Umsatz = Kurs wie gehandelt x Stueck); mit bereinigten Kursen waere der
Umsatz vergangener Tage nach einer Dividende systematisch zu klein.
tests/network/test_adjustment_live.py haelt fest, dass 'Adj Close' hier
tatsaechlich die Gesamtrendite traegt.

Nicht-endliche Zeilen (NaN, inf) werden an der Quelle verworfen und
gezaehlt; die Zahl steht im Lauf-Status und auf der Seite.
"""

from __future__ import annotations

import datetime as _dt
import time
from dataclasses import dataclass, field

from .config import (
    DOWNLOAD_BACKOFF_SECONDS,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_RETRIES,
)
from .scoring import is_finite

Date = _dt.date


@dataclass
class FetchStats:
    """Zaehler fuer den Lauf-Status -- alles, was verworfen wurde, wird sichtbar."""

    requested: int = 0
    delivered: int = 0
    rows_total: int = 0
    rows_dropped_nonfinite: int = 0
    empty_tickers: list[str] = field(default_factory=list)
    failed_chunks: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "angefragt": self.requested,
            "geliefert": self.delivered,
            "zeilen_gesamt": self.rows_total,
            "zeilen_verworfen_nicht_endlich": self.rows_dropped_nonfinite,
            "ticker_ohne_daten": sorted(self.empty_tickers),
            "fehlgeschlagene_bloecke": self.failed_chunks,
        }


@dataclass
class PriceBundle:
    """Alles, was der Rest des Programms an Kursen braucht."""

    # Ticker -> {Datum: bereinigter Schlusskurs}
    adjusted: dict[str, dict[Date, float]]
    # Ticker -> {Datum: Umsatz in Heimatwaehrung (Kurs wie gehandelt x Stueck)}
    turnover: dict[str, dict[Date, float]]
    stats: FetchStats

    def tickers(self) -> list[str]:
        return sorted(self.adjusted)


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _extract(frame, ticker: str, single: bool):
    """Spalten eines Tickers aus dem yfinance-Ergebnis holen.

    yfinance liefert je nach Version und Anzahl der Ticker mal flache, mal
    zweistufige Spalten -- besonders beim EINZELNEN Ticker (die Indizes der
    Trend-Ampel!) ist das nicht verlaesslich. Deshalb wird hier die Form
    geprueft und nicht angenommen.
    """
    spalten = getattr(frame, "columns", None)
    if spalten is None:
        return None
    if getattr(spalten, "nlevels", 1) > 1:
        if ticker in spalten.get_level_values(0):
            return frame[ticker]
        # Manche Fassungen drehen die Ebenen (Feld, Ticker).
        if ticker in spalten.get_level_values(-1):
            return frame.xs(ticker, axis=1, level=-1)
        return None
    # Flache Spalten: nur beim Einzelabruf eindeutig diesem Ticker zuzuordnen.
    return frame if single else None


def download_prices(
    tickers: list[str],
    start: Date,
    end: Date,
    *,
    downloader=None,
    sleep=time.sleep,
) -> PriceBundle:
    """Kurse laden. `downloader` ist injizierbar, damit Tests ohne Netz laufen.

    end ist EINSCHLIESSLICH; yfinance bekommt intern den Folgetag.
    """
    if downloader is None:  # pragma: no cover - echter Netzpfad
        import yfinance as yf

        def downloader(batch, start_, end_):
            return yf.download(
                tickers=batch,
                start=start_.isoformat(),
                end=(end_ + _dt.timedelta(days=1)).isoformat(),
                auto_adjust=False,
                actions=False,
                progress=False,
                group_by="ticker",
                threads=False,
            )

    stats = FetchStats(requested=len(tickers))
    adjusted: dict[str, dict[Date, float]] = {}
    turnover: dict[str, dict[Date, float]] = {}

    for batch in _chunks(sorted(set(tickers)), DOWNLOAD_CHUNK_SIZE):
        frame = None
        last_error: Exception | None = None
        for attempt in range(DOWNLOAD_RETRIES):
            try:
                frame = downloader(batch, start, end)
                break
            except Exception as exc:  # noqa: BLE001 - jede Quelle darf zicken
                last_error = exc
                if attempt < DOWNLOAD_RETRIES - 1:
                    sleep(DOWNLOAD_BACKOFF_SECONDS * (attempt + 1))
        if frame is None or getattr(frame, "empty", True):
            stats.failed_chunks.append(
                f"{batch[0]}..{batch[-1]}: {type(last_error).__name__ if last_error else 'leer'}"
            )
            continue

        single = len(batch) == 1
        for ticker in batch:
            sub = _extract(frame, ticker, single)
            if sub is None or getattr(sub, "empty", True):
                stats.empty_tickers.append(ticker)
                continue
            series_adj: dict[Date, float] = {}
            series_turnover: dict[Date, float] = {}
            for stamp, row in sub.iterrows():
                stats.rows_total += 1
                day = stamp.date() if hasattr(stamp, "date") else stamp
                adj = row.get("Adj Close")
                close = row.get("Close")
                volume = row.get("Volume")
                if not is_finite(adj) or float(adj) <= 0:
                    stats.rows_dropped_nonfinite += 1
                    continue
                series_adj[day] = float(adj)
                if is_finite(close) and is_finite(volume) and close > 0 and volume >= 0:
                    series_turnover[day] = float(close) * float(volume)
            if not series_adj:
                stats.empty_tickers.append(ticker)
                continue
            adjusted[ticker] = series_adj
            turnover[ticker] = series_turnover

    stats.delivered = len(adjusted)
    return PriceBundle(adjusted=adjusted, turnover=turnover, stats=stats)
