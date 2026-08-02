"""ADJUSTIERUNGS-BEWEIS an echten Kursen (braucht Netz).

Laeuft NICHT im Standardlauf (Marker "network"), sondern im Workflow
"Datenquelle pruefen". Zweck: die Annahmen ueber die Kursquelle sichtbar
halten, statt sie zu glauben.

Geprueft wird an einem Titel mit hoher Dividende (Exxon Mobil), dass die
bereinigte Reihe tatsaechlich die GESAMTRENDITE traegt: ueber ein volles
Jahr muss die bereinigte Rendite spuerbar ueber der reinen Kursrendite
liegen — und zwar ungefaehr um die Dividendenrendite.
"""

from __future__ import annotations

import datetime as _dt

import pytest

pytestmark = pytest.mark.network

TICKER = "XOM"  # zahlt seit Jahrzehnten Quartalsdividende
VON = _dt.date(2024, 1, 1)
BIS = _dt.date(2024, 12, 31)


@pytest.fixture(scope="module")
def frame():
    yf = pytest.importorskip("yfinance")
    daten = yf.download(
        tickers=[TICKER],
        start=VON.isoformat(),
        end=BIS.isoformat(),
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="ticker",
        threads=False,
    )
    if daten is None or daten.empty:
        pytest.skip("Kursquelle lieferte keine Daten")
    return daten if TICKER not in daten.columns.get_level_values(0) else daten[TICKER]


def test_quelle_liefert_die_bereinigte_spalte(frame):
    """Faellt 'Adj Close' weg, ist die Datenbasis eine andere — das MUSS knallen."""
    assert "Adj Close" in frame.columns, (
        "Die Kursquelle liefert kein 'Adj Close' mehr. Bis das geklaert ist, "
        "darf kein Ranking gebildet werden."
    )
    assert "Close" in frame.columns
    assert "Volume" in frame.columns


def test_bereinigte_rendite_ist_groesser_als_die_reine_kursrendite(frame):
    bereinigt = frame["Adj Close"].dropna()
    roh = frame["Close"].dropna()
    gesamt = float(bereinigt.iloc[-1]) / float(bereinigt.iloc[0]) - 1
    nur_kurs = float(roh.iloc[-1]) / float(roh.iloc[0]) - 1
    differenz = gesamt - nur_kurs
    # Dividendenrendite von XOM lag zuletzt bei rund 3 % pro Jahr.
    assert differenz > 0.015, (
        f"Gesamtrendite {gesamt:.4f} vs. Kursrendite {nur_kurs:.4f} — "
        f"die bereinigte Reihe traegt offenbar keine Dividenden mehr."
    )
    assert differenz < 0.10, "unplausibel grosse Differenz — Quelle pruefen"


def test_index_ticker_liefern_daten():
    """Die Trend-Ampel haengt an genau diesen beiden Symbolen."""
    yf = pytest.importorskip("yfinance")
    from momentum.config import MARKETS

    for markt in MARKETS:
        daten = yf.download(
            tickers=[markt.index_ticker],
            period="1mo",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        assert daten is not None and not daten.empty, (
            f"{markt.index_ticker} liefert keine Daten — ohne Handelskalender "
            f"kann fuer {markt.key} kein Stichtag bestimmt werden."
        )
