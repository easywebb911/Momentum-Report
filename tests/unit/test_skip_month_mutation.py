"""MUTATIONSPROBE: der uebersprungene Monat.

DIE Verwechslungs-Falle der 12-1-Formel ist, den juengsten Monat
versehentlich MITzurechnen. Dieser Test baut genau diesen Fehler
kuenstlich ein und haelt fest, dass die Wert-Tests dann rot werden.

Faellt dieser Test aus, ist die Absicherung gegen den Fehler weg.
"""

from __future__ import annotations

import pytest

from momentum import scoring
from momentum.scoring import combined_score, high_52w_ratio, momentum_12_1, percentile_ranks
from tests.conftest import ASOF, sample_series
from tests.unit.test_scoring_values import SOLL_MOMENTUM, SOLL_RANGFOLGE, SOLL_SCORE


@pytest.fixture
def ohne_skip(monkeypatch):
    """Mutation: der juengste Monat wird MITgerechnet (Zaehler = Monat M)."""
    monkeypatch.setattr(scoring, "MOMENTUM_SKIP_MONTHS", 0)
    return None


def test_mutation_veraendert_die_werte(ohne_skip):
    """Ohne Ueberspringen kommen andere 12-1-Werte heraus."""
    serien = sample_series()
    # Handrechnung der MUTIERTEN Variante (Zaehler 31.07.2026):
    #   AAA 160/100-1 = +0,60 (statt +0,50)
    #   BBB 125/100-1 = +0,25 (statt +0,20)
    #   DDD 250/200-1 = +0,25 (statt +0,20)
    #   EEE  75/ 50-1 = +0,50 (statt +0,60)
    assert momentum_12_1(serien["AAA"], ASOF) == pytest.approx(0.60)
    assert momentum_12_1(serien["EEE"], ASOF) == pytest.approx(0.50)

    abweichungen = [
        t
        for t, soll in SOLL_MOMENTUM.items()
        if momentum_12_1(serien[t], ASOF) != pytest.approx(soll, abs=1e-12)
    ]
    assert abweichungen, "Mutation blieb folgenlos — der Skip-Monat waere ungeprueft"
    assert set(abweichungen) == {"AAA", "BBB", "DDD", "EEE"}


def test_mutation_kippt_die_rangfolge(ohne_skip):
    """Und sie aendert das Ergebnis, auf das es ankommt: die Reihenfolge."""
    serien = sample_series()
    pct_mom = percentile_ranks({t: momentum_12_1(p, ASOF) for t, p in serien.items()})
    pct_high = percentile_ranks({t: high_52w_ratio(p, ASOF) for t, p in serien.items()})
    scores = {t: combined_score(pct_mom[t], pct_high[t]) for t in serien}
    rangfolge = sorted(scores, key=lambda t: (-scores[t], t))

    # Mutierte Perzentile 12-1 (aufsteigend, Gleichstand BBB vor DDD):
    #   CCC 0,00 | BBB 0,25 | DDD 0,50 | EEE 0,75 | AAA 1,00
    # 52W-Perzentile bleiben unveraendert. Endscore bei 50/50:
    #   AAA 75,0 | DDD 75,0 | BBB 50,0 | EEE 50,0 | CCC 0,0
    # Zwei Gleichstaende, beide alphabetisch gebrochen (AAA vor DDD,
    # BBB vor EEE).
    assert rangfolge == ["AAA", "DDD", "BBB", "EEE", "CCC"]
    assert rangfolge != SOLL_RANGFOLGE
    assert scores["AAA"] == pytest.approx(75.0)
    assert scores["AAA"] != pytest.approx(SOLL_SCORE["AAA"])


def test_ohne_mutation_stimmt_wieder_alles():
    """Gegenprobe: ohne die Mutation gilt die Handrechnung unveraendert."""
    serien = sample_series()
    for ticker, soll in SOLL_MOMENTUM.items():
        assert momentum_12_1(serien[ticker], ASOF) == pytest.approx(soll, abs=1e-12)


def test_skip_konstante_ist_eins():
    """Die dokumentierte Rezeptur ueberspringt genau einen Monat."""
    from momentum.config import MOMENTUM_LOOKBACK_MONTHS, MOMENTUM_SKIP_MONTHS

    assert MOMENTUM_SKIP_MONTHS == 1
    assert MOMENTUM_LOOKBACK_MONTHS == 12
