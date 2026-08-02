"""ADJUSTIERUNGS-BEWEIS (ohne Netz).

Gezeigt wird an einem Titel mit bekanntem Split UND bekannter Dividende,
dass die 12-1-Rendite dieses Werkzeugs die GESAMTRENDITE ist:

  * Split 4:1 zum 15.01.2026 — der unbereinigte Kurs faellt von 400 auf 100,
    ohne dass ein Anleger etwas verloren haette.
  * Dividende von insgesamt 8,00 je (nachsplit-)Aktie im Messfenster.

Erwartung:
  * Die Pipeline rechnet mit der bereinigten Reihe ('Adj Close') und kommt
    auf die Gesamtrendite.
  * Wuerde sie mit dem unbereinigten Kurs rechnen, kaeme ein katastrophal
    falscher Wert von rund -75 % heraus.
  * Der unbereinigte Kurs wird ausschliesslich fuer den Umsatz des
    Handelbarkeits-Filters verwendet.

Die Gegenprobe an echten Kursen steht in tests/network/test_adjustment_live.py.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from momentum.data import download_prices
from momentum.ranking import median_turnover
from momentum.scoring import momentum_12_1
from tests.conftest import make_downloader

Date = _dt.date
ASOF = Date(2026, 7, 31)
SPLIT_TAG = Date(2026, 1, 15)

# --------------------------------------------------------------------------
# Konstruktion (alles von Hand gerechnet)
#
# Ein Anleger haelt 1 Aktie ab 31.07.2025 zu 300,00.
# Bis 30.06.2026 steigt der Wert der Position auf 400,00 (nach Split
# 4 Aktien zu je 100,00), plus 8,00 je Aktie x 4 = 32,00 Dividende ... in
# der bereinigten Reihe ist das eingerechnet.
#
# Bereinigte Reihe ('Adj Close'), Gesamtrendite-Sicht:
#   31.07.2025: 75,00       (= 300,00 vorsplit / 4)
#   30.06.2026: 97,50
#   -> 12-1 = 97,50 / 75,00 - 1 = +0,30  (= +30 %)
#
# Unbereinigte Reihe ('Close'), wie an der Boerse gehandelt:
#   31.07.2025: 300,00      (vor dem Split)
#   30.06.2026: 100,00      (nach dem Split)
#   -> naiv gerechnet: 100 / 300 - 1 = -0,6667  (voellig falsch)
# --------------------------------------------------------------------------

BEREINIGT = {
    Date(2025, 7, 31): 75.00,
    Date(2025, 8, 31): 78.00,
    Date(2025, 9, 30): 80.00,
    Date(2025, 10, 31): 82.00,
    Date(2025, 11, 30): 85.00,
    Date(2025, 12, 31): 88.00,
    SPLIT_TAG: 90.00,
    Date(2026, 1, 31): 91.00,
    Date(2026, 2, 28): 92.00,
    Date(2026, 3, 31): 94.00,
    Date(2026, 4, 30): 95.00,
    Date(2026, 5, 31): 96.00,
    Date(2026, 6, 30): 97.50,
    Date(2026, 7, 31): 99.00,
}

# Unbereinigt: vor dem Split das Vierfache plus noch nicht abgegangene
# Dividende; danach die tatsaechlich gehandelten Kurse.
UNBEREINIGT = {
    Date(2025, 7, 31): 300.00,
    Date(2025, 8, 31): 312.00,
    Date(2025, 9, 30): 320.00,
    Date(2025, 10, 31): 328.00,
    Date(2025, 11, 30): 340.00,
    Date(2025, 12, 31): 352.00,
    SPLIT_TAG: 92.00,
    Date(2026, 1, 31): 93.00,
    Date(2026, 2, 28): 94.00,
    Date(2026, 3, 31): 96.00,
    Date(2026, 4, 30): 97.00,
    Date(2026, 5, 31): 98.00,
    Date(2026, 6, 30): 100.00,
    Date(2026, 7, 31): 101.50,
}

SOLL_GESAMTRENDITE = 97.50 / 75.00 - 1  # = +0,30


@pytest.fixture
def bundle():
    return download_prices(
        ["SPLITCO"],
        Date(2025, 1, 1),
        ASOF,
        downloader=make_downloader(
            {"SPLITCO": BEREINIGT},
            raw_close={"SPLITCO": UNBEREINIGT},
            volume=2_000_000.0,
        ),
    )


def test_pipeline_liefert_die_bereinigte_reihe(bundle):
    reihe = bundle.adjusted["SPLITCO"]
    assert reihe[Date(2025, 7, 31)] == pytest.approx(75.00)
    assert reihe[Date(2026, 6, 30)] == pytest.approx(97.50)
    # kein Split-Bruch: der Sprung 352 -> 92 aus der unbereinigten Reihe
    # taucht in der bereinigten nirgends auf
    tage = sorted(reihe)
    groesster_tagesabfall = min(
        reihe[b] / reihe[a] - 1 for a, b in zip(tage, tage[1:])
    )
    assert groesster_tagesabfall > -0.10


def test_12_1_ist_die_gesamtrendite(bundle):
    ist = momentum_12_1(bundle.adjusted["SPLITCO"], ASOF)
    assert ist == pytest.approx(SOLL_GESAMTRENDITE, abs=1e-12)
    assert ist == pytest.approx(0.30, abs=1e-12)


def test_ohne_bereinigung_waere_das_ergebnis_katastrophal_falsch():
    """Gegenprobe: dieselbe Formel auf der unbereinigten Reihe."""
    falsch = momentum_12_1(UNBEREINIGT, ASOF)
    assert falsch == pytest.approx(100.00 / 300.00 - 1, abs=1e-12)
    assert falsch < -0.6
    assert falsch != pytest.approx(SOLL_GESAMTRENDITE)


def test_umsatz_nutzt_den_kurs_wie_gehandelt(bundle):
    """Der Handelbarkeits-Filter rechnet mit dem unbereinigten Kurs.

    Sonst waere der Umsatz vergangener Tage nach Dividende oder Split
    systematisch zu klein und der Filter wuerde zu viel aussortieren.
    """
    umsatz = bundle.turnover["SPLITCO"]
    assert umsatz[Date(2025, 7, 31)] == pytest.approx(300.00 * 2_000_000.0)
    assert umsatz[Date(2026, 6, 30)] == pytest.approx(100.00 * 2_000_000.0)
    # Fenster ab 01.04.2026, also 30.04. / 31.05. / 30.06. / 31.07.:
    #   97,00 | 98,00 | 100,00 | 101,50  ->  Median (98,00 + 100,00) / 2 = 99,00
    assert median_turnover(umsatz, ASOF) == pytest.approx(99.00 * 2_000_000.0)


def test_nicht_endliche_zeilen_werden_verworfen_und_gezaehlt():
    reihe = dict(BEREINIGT)
    reihe[Date(2026, 7, 15)] = float("nan")
    reihe[Date(2026, 7, 16)] = float("inf")
    bundle = download_prices(
        ["SPLITCO"], Date(2025, 1, 1), ASOF, downloader=make_downloader({"SPLITCO": reihe})
    )
    assert bundle.stats.rows_dropped_nonfinite == 2
    assert Date(2026, 7, 15) not in bundle.adjusted["SPLITCO"]
    assert bundle.stats.as_dict()["zeilen_verworfen_nicht_endlich"] == 2


def test_monatsraender_werden_korrekt_getroffen(bundle):
    """Der Split-Tag mitten im Januar darf den Monatsschluss nicht verdraengen."""
    from momentum.scoring import month_end_close

    assert month_end_close(bundle.adjusted["SPLITCO"], 2026, 1, ASOF) == pytest.approx(91.00)
