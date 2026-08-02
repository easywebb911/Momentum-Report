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
HANDRECHNUNG PLATZZIFFERN  (1 = bester, gleiche Ordnung wie die Perzentile)

  12-1:   EEE 1. | AAA 2. | DDD 3. | BBB 4. | CCC 5.
  52W:    DDD 1. | BBB 2. | AAA 3. | EEE 4. | CCC 5.

--------------------------------------------------------------------------
HANDRECHNUNG ENDSCORE  = 50 x Perzentil(12-1) + 50 x Perzentil(52W)

  AAA = 50 x 0,75 + 50 x 0,50 = 37,5 + 25,0 = 62,5
  BBB = 50 x 0,25 + 50 x 0,75 = 12,5 + 37,5 = 50,0
  CCC = 50 x 0,00 + 50 x 0,00 =  0,0 +  0,0 =  0,0
  DDD = 50 x 0,50 + 50 x 1,00 = 25,0 + 50,0 = 75,0
  EEE = 50 x 1,00 + 50 x 0,25 = 50,0 + 12,5 = 62,5

RANGFOLGE (Score absteigend): DDD 75,0 | AAA 62,5 | EEE 62,5 | BBB 50,0 | CCC 0,0

AAA und EEE liegen EXAKT gleichauf -- und das ist kein Zufall des
Beispiels, sondern die Eigenschaft der Gleichgewichtung: AAA steht (2., 3.),
EEE steht (1., 4.), die Summe der Perzentile ist beide Male 1,25. Wer vorn
steht, entscheidet dann allein das Alphabet: AAA vor EEE.

Unter den frueheren 70/30 waeren die beiden weit auseinandergelegen
(AAA 67,5 gegen EEE 77,5). Der Gleichstand ist also ein echter Nachweis,
dass hier 50/50 gerechnet wird -- und nicht bloss irgendetwas.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from momentum.config import WEIGHT_HIGH_52W, WEIGHT_MOMENTUM_12_1
from momentum.scoring import (
    InsufficientHistory,
    combined_score,
    high_52w_ratio,
    momentum_12_1,
    ordinal_ranks,
    percentile_ranks,
)
from tests.conftest import ASOF, sample_series

SOLL_MOMENTUM = {"AAA": 0.50, "BBB": 0.20, "CCC": -0.10, "DDD": 0.20, "EEE": 0.60}
SOLL_HIGH_52W = {"AAA": 0.80, "BBB": 1.00, "CCC": 0.50, "DDD": 1.00, "EEE": 0.75}
SOLL_PCT_MOM = {"CCC": 0.00, "BBB": 0.25, "DDD": 0.50, "AAA": 0.75, "EEE": 1.00}
SOLL_PCT_HIGH = {"CCC": 0.00, "EEE": 0.25, "AAA": 0.50, "BBB": 0.75, "DDD": 1.00}
SOLL_RANG_MOM = {"EEE": 1, "AAA": 2, "DDD": 3, "BBB": 4, "CCC": 5}
SOLL_RANG_HIGH = {"DDD": 1, "BBB": 2, "AAA": 3, "EEE": 4, "CCC": 5}
SOLL_SCORE = {"AAA": 62.5, "BBB": 50.0, "CCC": 0.0, "DDD": 75.0, "EEE": 62.5}
SOLL_RANGFOLGE = ["DDD", "AAA", "EEE", "BBB", "CCC"]


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


# ------------------------------------------------------- Gleichgewichtung


def test_die_gewichte_sind_gleich_und_summieren_auf_eins():
    """50/50 -- Konvention der Komposit-Literatur, kein belegtes Optimum."""
    assert WEIGHT_MOMENTUM_12_1 == 0.50
    assert WEIGHT_HIGH_52W == 0.50
    assert WEIGHT_MOMENTUM_12_1 + WEIGHT_HIGH_52W == 1.0


def test_50_50_rechnet_wirklich_50_50():
    """Spiegelbildliche Teil-Raenge muessen punktgleich landen.

    Bei fuenf Titeln: Platz 1 -> Perzentil 1,00 | Platz 3 -> 0,50.
    Ein Titel auf (1., 3.) und einer auf (3., 1.) haben denselben Score --
    das gilt GENAU DANN, wenn beide Zutaten gleich wiegen. Der Gegencheck
    mit 70/30 zeigt, dass der Test wirklich die Gewichtung misst.
    """
    eins_drei = combined_score(1.00, 0.50)
    drei_eins = combined_score(0.50, 1.00)
    assert eins_drei == pytest.approx(drei_eins, abs=1e-12)
    assert eins_drei == pytest.approx(75.0, abs=1e-12)

    # Gegenprobe: unter 70/30 waeren es 85 gegen 65 -- weit auseinander.
    assert 100 * (0.70 * 1.00 + 0.30 * 0.50) != pytest.approx(
        100 * (0.70 * 0.50 + 0.30 * 1.00)
    )


def test_bei_punktgleichheit_entscheidet_das_alphabet():
    """Der Gleichstands-Bruch gilt unveraendert auch fuer 50/50-Gleichstand."""
    serien = sample_series()
    pct_mom = percentile_ranks({t: momentum_12_1(p, ASOF) for t, p in serien.items()})
    pct_high = percentile_ranks({t: high_52w_ratio(p, ASOF) for t, p in serien.items()})
    scores = {t: combined_score(pct_mom[t], pct_high[t]) for t in serien}

    # AAA steht (2., 3.), EEE steht (1., 4.) -- exakt gleicher Score.
    assert scores["AAA"] == pytest.approx(scores["EEE"], abs=1e-12)
    rangfolge = sorted(scores, key=lambda t: (-scores[t], t))
    assert rangfolge.index("AAA") < rangfolge.index("EEE"), "AAA < EEE im Alphabet"


@pytest.mark.parametrize(
    "werte,soll",
    [
        (SOLL_MOMENTUM, SOLL_RANG_MOM),
        (SOLL_HIGH_52W, SOLL_RANG_HIGH),
    ],
)
def test_platzziffern_treffen_die_handrechnung(werte, soll):
    assert ordinal_ranks(werte) == soll


def test_platzziffer_und_perzentil_laufen_nie_auseinander():
    """Platz 1 muss immer Perzentil 1,0 sein -- sonst luegt die Anzeige."""
    werte = {t: momentum_12_1(p, ASOF) for t, p in sample_series().items()}
    plaetze = ordinal_ranks(werte)
    perzentile = percentile_ranks(werte)
    n = len(werte)
    for ticker in werte:
        # Platz p (1..n) entspricht Perzentil (n - p) / (n - 1).
        assert perzentile[ticker] == pytest.approx(
            (n - plaetze[ticker]) / (n - 1), abs=1e-12
        ), ticker
    bester = min(plaetze, key=plaetze.get)
    assert plaetze[bester] == 1 and perzentile[bester] == pytest.approx(1.0)


def test_platzziffern_randfaelle():
    assert ordinal_ranks({}) == {}
    assert ordinal_ranks({"X": 1.23}) == {"X": 1}
    # Gleichstand: alphabetisch gebrochen, der spaetere Ticker ist "besser"
    assert ordinal_ranks({"B": 1.0, "A": 1.0, "C": 1.0}) == {"C": 1, "B": 2, "A": 3}


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
