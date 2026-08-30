"""Monats-Rueckblick: Klassifikation und Persistenz.

Deckt die drei Punkte ab, die Easy vor dem Bau festgelegt hat:
  * Schwelle +/- 2 %, Randwert zaehlt zu "neutral" (keine Grauzone)
  * fehlender Endkurs -> "unbekannt", NIE als 0 % oder stillschweigend weg
  * ein einmal geschriebener Rueckblick wird nie neu geschrieben
"""

from __future__ import annotations

import datetime as _dt

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.data import FetchStats, PriceBundle
from momentum.evaluation import (
    EvaluationBereitsVorhanden,
    build_evaluation,
    dump_evaluation,
    klassifiziere,
    write_evaluation,
)

Date = _dt.date


def _bundle(prices: dict[str, dict[Date, float]]) -> PriceBundle:
    return PriceBundle(adjusted=prices, turnover={}, stats=FetchStats())


def _prev_ranking(top5: list[tuple[str, str, float]]) -> dict:
    return {
        "markt": "us",
        "ranking_monat": "2026-07",
        "stichtag": "2026-07-31",
        "rangliste": [
            {"ticker": t, "name": n, "kurs_stichtag": k} for t, n, k in top5
        ],
    }


@pytest.mark.parametrize(
    "veraenderung, erwartet",
    [
        (0.021, "positiv"),
        (0.02, "neutral"),
        (0.0, "neutral"),
        (-0.02, "neutral"),
        (-0.021, "negativ"),
        (None, "unbekannt"),
    ],
)
def test_klassifiziere_deterministisch(veraenderung, erwartet):
    assert klassifiziere(veraenderung) == erwartet
    # Zweiter Aufruf mit denselben Eingaben -> dasselbe Ergebnis.
    assert klassifiziere(veraenderung) == erwartet


def test_build_evaluation_rechnet_veraenderung_und_klassifiziert():
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0), ("BBB", "Firma BBB", 100.0)])
    bundle = _bundle({"AAA": {Date(2026, 8, 31): 103.0}, "BBB": {Date(2026, 8, 31): 97.0}})
    ev = build_evaluation(prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31))

    assert ev["ausgewerteter_monat"] == "2026-07"
    assert ev["start_stichtag"] == "2026-07-31"
    assert ev["end_stichtag"] == "2026-08-31"
    aaa, bbb = ev["titel"]
    assert aaa["kurs_end"] == 103.0
    assert aaa["veraenderung"] == pytest.approx(0.03)
    assert aaa["klasse"] == "positiv"
    assert bbb["veraenderung"] == pytest.approx(-0.03)
    assert bbb["klasse"] == "negativ"


def test_randwert_bleibt_neutral_trotz_gleitkomma_rauschen():
    """51 / 50 - 1 ist in Gleitkomma 0.020000000000000018, nicht exakt 0.02
    -- ohne Rundung VOR der Klassifikation wuerde ein exakt +2,0 %
    angezeigter Titel unsichtbar als "positiv" gezaehlt (siehe
    build_evaluation: erst runden, dann klassifizieren)."""
    prev = _prev_ranking([("ABC", "Firma ABC", 50.0)])
    bundle = _bundle({"ABC": {Date(2026, 8, 31): 51.0}})
    ev = build_evaluation(prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31))

    assert ev["titel"][0]["veraenderung"] == 0.02
    assert ev["titel"][0]["klasse"] == "neutral"


def test_fehlender_endkurs_wird_unbekannt_nicht_null():
    """Titel aus dem Universum gefallen: kein Kurs im Bundle des Folgemonats."""
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0), ("ZZZ", "Firma ZZZ", 50.0)])
    bundle = _bundle({"AAA": {Date(2026, 8, 31): 110.0}})  # ZZZ fehlt komplett
    ev = build_evaluation(prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31))

    zzz = next(t for t in ev["titel"] if t["ticker"] == "ZZZ")
    assert zzz["kurs_end"] is None
    assert zzz["veraenderung"] is None
    assert zzz["klasse"] == "unbekannt"


def test_rueckblick_wird_nie_ueberschrieben(tmp_path):
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0)])
    bundle = _bundle({"AAA": {Date(2026, 8, 31): 110.0}})
    ev = build_evaluation(prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31))
    write_evaluation(ev, tmp_path)
    with pytest.raises(EvaluationBereitsVorhanden, match="eingefroren"):
        write_evaluation(ev, tmp_path)


def test_dump_ist_stabil_und_sortiert():
    ev1 = {"markt": "us", "ausgewerteter_monat": "2026-07", "b": 1, "a": 2}
    assert dump_evaluation(ev1) == dump_evaluation(dict(reversed(list(ev1.items()))))
