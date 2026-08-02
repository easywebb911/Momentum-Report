"""WERT-Tests: von Hand nachgerechnetes Soll, keine reinen Aufruf-Tests.

Die Herleitung steht vollstaendig im Klartext, damit sie jemand mit Papier
nachvollziehen kann. Kunst-Beispiel: 5 Ticker, 13 Monatskurse (siehe
tests/conftest.py), Stichtag 31.07.2026.

--------------------------------------------------------------------------
HANDRECHNUNG 12-1-MOMENTUM
Stichtag-Monat M = 2026-07.
Zaehler  = letzter Handelstag M-1  = 30.06.2026
Nenner   = letzter Handelstag M-12 = 31.07.2025
Der Juli 2026 (Monat M) faellt heraus -- uebersprungener Monat.

  AAA  150,00 / 100,00 - 1 = +0,50
  BBB  120,00 / 100,00 - 1 = +0,20
  CCC   90,00 / 100,00 - 1 = -0,10
  DDD  240,00 / 200,00 - 1 = +0,20     <- Gleichstand mit BBB
  EEE   80,00 /  50,00 - 1 = +0,60

--------------------------------------------------------------------------
HANDRECHNUNG 52-WOCHEN-HOCH-NAEHE
Fenster = 364 Tage vor dem 31.07.2026, Stichtag eingeschlossen
        = 01.08.2025 bis 31.07.2026.
Der Punkt vom 31.07.2025 liegt bewusst AUSSERHALB (365 Tage zurueck).
Hoechster Tages-Schlusskurs im Fenster je Titel:

  AAA  Hoch 200,00 (31.12.2025), Kurs 160,00 -> 160/200 = 0,80
  BBB  Hoch 125,00 (31.07.2026, = Stichtag), Kurs 125,00 -> 1,00
  CCC  Hoch 180,00 (30.09.2025), Kurs  90,00 ->  90/180 = 0,50
  DDD  Hoch 250,00 (31.07.2026, = Stichtag), Kurs 250,00 -> 1,00
  EEE  Hoch 100,00 (31.03.2026), Kurs  75,00 ->  75/100 = 0,75

--------------------------------------------------------------------------
HANDRECHNUNG PERZENTILE  (aufsteigend, i / (n-1), n = 5 -> Schritte 0,25;
Gleichstand alphabetisch nach Ticker gebrochen)

  12-1:   CCC -0,10 -> 0,00 | BBB +0,20 -> 0,25 | DDD +0,20 -> 0,50
          AAA +0,50 -> 0,75 | EEE +0,60 -> 1,00
          (BBB vor DDD, weil "BBB" < "DDD")

  52W:    CCC 0,50 -> 0,00 | EEE 0,75 -> 0,25 | AAA 0,80 -> 0,50
          BBB 1,00 -> 0,75 | DDD 1,00 -> 1,00
          (BBB vor DDD, weil "BBB" < "DDD")

--------------------------------------------------------------------------
HANDRECHNUNG ENDSCORE  = 70 x Perzentil(12-1) + 30 x Perzentil(52W)

  AAA = 70 x 0,75 + 30 x 0,50 = 52,5 + 15,0 = 67,5
  BBB = 70 x 0,25 + 30 x 0,75 = 17,5 + 22,5 = 40,0
  CCC = 70 x 0,00 + 30 x 0,00 =  0,0 +  0,0 =  0,0
  DDD = 70 x 0,50 + 30 x 1,00 = 35,0 + 30,0 = 65,0
  EEE = 70 x 1,00 + 30 x 0,25 = 70,0 +  7,5 = 77,5

RANGFOLGE (Score absteigend): EEE 77,5 | AAA 67,5 | DDD 65,0 | BBB 40,0 | CCC 0,0
--------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from momentum.scoring import (
    InsufficientHistory,
    combined_score,
    high_52w_ratio,
    momentum_12_1,
    percentile_ranks,
)
from tests.conftest import ASOF, sample_series

SOLL_MOMENTUM = {"AAA": 0.50, "BBB": 0.20, "CCC": -0.10, "DDD": 0.20, "EEE": 0.60}
SOLL_HIGH_52W = {"AAA": 0.80, "BBB": 1.00, "CCC": 0.50, "DDD": 1.00, "EEE": 0.75}
SOLL_PCT_MOM = {"CCC": 0.00, "BBB": 0.25, "DDD": 0.50, "AAA": 0.75, "EEE": 1.00}
SOLL_PCT_HIGH = {"CCC": 0.00, "EEE": 0.25, "AAA": 0.50, "BBB": 0.75, "DDD": 1.00}
SOLL_SCORE = {"AAA": 67.5, "BBB": 40.0, "CCC": 0.0, "DDD": 65.0, "EEE": 77.5}
SOLL_RANGFOLGE = ["EEE", "AAA", "DDD", "BBB", "CCC"]


@pytest.mark.parametrize("ticker,soll", sorted(SOLL_MOMENTUM.items()))
def test_momentum_12_1_trifft_handrechnung(ticker, soll):
    prices = sample_series()[ticker]
    assert momentum_12_1(prices, ASOF) == pytest.approx(soll, abs=1e-12)


@pytest.mark.parametrize("ticker,soll", sorted(SOLL_HIGH_52W.items()))
def test_high_52w_trifft_handrechnung(ticker, soll):
    prices = sample_series()[ticker]
    assert high_52w_ratio(prices, ASOF) == pytest.approx(soll, abs=1e-12)


def test_der_juengste_monat_liegt_ausserhalb_des_zaehlers():
    """Zaehler ist der 30.06., NICHT der 31.07. — das ist der Kern der Formel."""
    aaa = sample_series()["AAA"]
    # 150,00 / 100,00 - 1 = 0,50  (mit Juli waeren es 160/100 - 1 = 0,60)
    assert momentum_12_1(aaa, ASOF) == pytest.approx(0.50)
    assert momentum_12_1(aaa, ASOF) != pytest.approx(0.60)


def test_52w_fenster_schliesst_den_punkt_vor_365_tagen_aus():
    """CCC steht am 31.07.2025 bei 100 — das darf das Hoch nicht beeinflussen."""
    ccc = sample_series()["CCC"]
    # Hoch im Fenster ist 180 (30.09.2025), nicht etwa 100 vom 31.07.2025.
    assert high_52w_ratio(ccc, ASOF) == pytest.approx(90.0 / 180.0)


def test_perzentile_momentum_treffen_handrechnung():
    werte = {t: momentum_12_1(p, ASOF) for t, p in sample_series().items()}
    ist = percentile_ranks(werte)
    for ticker, soll in SOLL_PCT_MOM.items():
        assert ist[ticker] == pytest.approx(soll, abs=1e-12), ticker


def test_perzentile_52w_treffen_handrechnung():
    werte = {t: high_52w_ratio(p, ASOF) for t, p in sample_series().items()}
    ist = percentile_ranks(werte)
    for ticker, soll in SOLL_PCT_HIGH.items():
        assert ist[ticker] == pytest.approx(soll, abs=1e-12), ticker


def test_gleichstand_wird_alphabetisch_gebrochen():
    """BBB und DDD haben identisches 12-1 (+0,20). BBB bekommt das kleinere Perzentil."""
    werte = {t: momentum_12_1(p, ASOF) for t, p in sample_series().items()}
    assert werte["BBB"] == pytest.approx(werte["DDD"])
    ist = percentile_ranks(werte)
    assert ist["BBB"] < ist["DDD"]
    assert (ist["BBB"], ist["DDD"]) == pytest.approx((0.25, 0.50))


def test_endscore_trifft_handrechnung():
    serien = sample_series()
    pct_mom = percentile_ranks({t: momentum_12_1(p, ASOF) for t, p in serien.items()})
    pct_high = percentile_ranks({t: high_52w_ratio(p, ASOF) for t, p in serien.items()})
    for ticker, soll in SOLL_SCORE.items():
        ist = combined_score(pct_mom[ticker], pct_high[ticker])
        assert ist == pytest.approx(soll, abs=1e-10), ticker


def test_rangfolge_trifft_handrechnung():
    serien = sample_series()
    pct_mom = percentile_ranks({t: momentum_12_1(p, ASOF) for t, p in serien.items()})
    pct_high = percentile_ranks({t: high_52w_ratio(p, ASOF) for t, p in serien.items()})
    scores = {t: combined_score(pct_mom[t], pct_high[t]) for t in serien}
    rangfolge = sorted(scores, key=lambda t: (-scores[t], t))
    assert rangfolge == SOLL_RANGFOLGE


def test_perzentil_randfaelle():
    assert percentile_ranks({}) == {}
    assert percentile_ranks({"X": 1.23}) == {"X": 1.0}
    # exakt gleiche Werte: trotzdem gleichmaessig verteilt, alphabetisch
    assert percentile_ranks({"B": 1.0, "A": 1.0, "C": 1.0}) == {
        "A": 0.0,
        "B": 0.5,
        "C": 1.0,
    }


def test_fehlende_historie_wird_zur_ausnahme_nicht_zur_null():
    """Ein fehlender Stuetzpunkt darf NIE still zu einer 0 werden."""
    kurz = {d: v for d, v in sample_series()["AAA"].items() if d.year == 2026}
    with pytest.raises(InsufficientHistory):
        momentum_12_1(kurz, ASOF)
