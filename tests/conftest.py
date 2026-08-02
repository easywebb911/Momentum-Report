"""Gemeinsame Testbausteine.

Alle Standardtests laufen OHNE Netz: die Kursquelle wird durch einen
injizierten `downloader` ersetzt, der genau die Datenform liefert, die
yfinance liefert (MultiIndex-Spalten je Ticker).
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd
import pytest

Date = _dt.date


# --------------------------------------------------------------------------
# Das KUNST-BEISPIEL: 5 Ticker, 13 Monatskurse.
# Alle Sollwerte in tests/unit/test_scoring_values.py sind von Hand
# hergeleitet und stehen dort im Klartext.
# --------------------------------------------------------------------------

MONTH_ENDS = [
    Date(2025, 7, 31),
    Date(2025, 8, 31),
    Date(2025, 9, 30),
    Date(2025, 10, 31),
    Date(2025, 11, 30),
    Date(2025, 12, 31),
    Date(2026, 1, 31),
    Date(2026, 2, 28),
    Date(2026, 3, 31),
    Date(2026, 4, 30),
    Date(2026, 5, 31),
    Date(2026, 6, 30),
    Date(2026, 7, 31),
]

ASOF = Date(2026, 7, 31)

_RAW = {
    #        2025-07  08      09      10      11      12    2026-01  02      03      04      05      06      07
    "AAA": [100.00, 110.00, 120.00, 130.00, 150.00, 200.00, 180.00, 170.00, 165.00, 155.00, 152.00, 150.00, 160.00],
    "BBB": [100.00, 101.00, 102.00, 104.00, 106.00, 108.00, 110.00, 112.00, 114.00, 116.00, 118.00, 120.00, 125.00],
    "CCC": [100.00, 150.00, 180.00, 160.00, 140.00, 130.00, 120.00, 110.00, 105.00, 100.00,  95.00,  90.00,  90.00],
    "DDD": [200.00, 205.00, 210.00, 215.00, 220.00, 225.00, 228.00, 230.00, 232.00, 235.00, 238.00, 240.00, 250.00],
    "EEE": [ 50.00,  55.00,  60.00,  65.00,  70.00,  80.00,  90.00,  95.00, 100.00,  92.00,  85.00,  80.00,  75.00],
}

# Marktindex fuer die Trend-Ampel: steigt durchgehend -> keine Warnlage.
_INDEX = [4000.0 + 20.0 * i for i in range(13)]


def sample_series() -> dict[str, dict[Date, float]]:
    return {
        ticker: {day: value for day, value in zip(MONTH_ENDS, values)}
        for ticker, values in _RAW.items()
    }


def index_series(values: list[float] | None = None) -> dict[Date, float]:
    return dict(zip(MONTH_ENDS, values if values is not None else _INDEX))


@pytest.fixture
def prices() -> dict[str, dict[Date, float]]:
    return sample_series()


# --------------------------------------------------------------------------
# Ersatz fuer yfinance
# --------------------------------------------------------------------------


def make_downloader(
    series_map: dict[str, dict[Date, float]],
    *,
    volume: float = 10_000_000.0,
    raw_close: dict[str, dict[Date, float]] | None = None,
    volumes: dict[str, float] | None = None,
):
    """Baut einen `downloader`, der yfinance-formige DataFrames liefert.

    `raw_close` erlaubt es, den unbereinigten Kurs bewusst vom bereinigten
    abweichen zu lassen (Split-/Dividenden-Nachweis).
    """

    def downloader(batch, start, end):
        frames: dict[str, pd.DataFrame] = {}
        for ticker in batch:
            series = series_map.get(ticker)
            if not series:
                continue
            days = sorted(d for d in series if start <= d <= end)
            if not days:
                continue
            raw = (raw_close or {}).get(ticker, {})
            vol = (volumes or {}).get(ticker, volume)
            frames[ticker] = pd.DataFrame(
                {
                    "Close": [raw.get(d, series[d]) for d in days],
                    "Adj Close": [series[d] for d in days],
                    "Volume": [vol] * len(days),
                },
                index=pd.DatetimeIndex([pd.Timestamp(d) for d in days]),
            )
        if not frames:
            return pd.DataFrame()
        if len(batch) == 1 and batch[0] in frames:
            return frames[batch[0]]
        return pd.concat(frames, axis=1)

    return downloader


def write_universe(
    path, tickers, *, label="Testuniversum", origin="Kunst-Beispiel", status="VERIFIED"
):
    lines = [
        f"# Universum: {label}",
        f"# Herkunft: {origin}",
        "# Stand: 2026-07-31",
        f"# STATUS: {status}",
    ]
    lines += [f"{t}\tFirma {t}" for t in tickers]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
