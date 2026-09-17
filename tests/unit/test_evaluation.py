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
    _top5_veraenderung,
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


# --------------------------------------------------------------------------
# Index-Vergleich (schema 2) -- reine Zusatz-Einordnung, siehe Modul-
# Docstring. Externer Qualitaets-Check: "Top-5 +8 %" ist ohne
# Vergleichsmassstab bedeutungslos.
# --------------------------------------------------------------------------


def test_top5_veraenderung_ist_das_gleichgewichtete_mittel():
    titel = [{"veraenderung": 0.10}, {"veraenderung": 0.06}, {"veraenderung": -0.04}]
    assert _top5_veraenderung(titel) == pytest.approx(0.04)


def test_top5_veraenderung_ignoriert_unbekannte_titel_statt_null_zu_setzen():
    """Ein delisteter Titel (veraenderung None) darf den Durchschnitt nicht
    kuenstlich nach unten ziehen -- er faellt aus dem Mittel heraus, wie
    klassifiziere() es fuer die Einzelklassifikation schon haelt."""
    titel = [{"veraenderung": 0.10}, {"veraenderung": None}]
    assert _top5_veraenderung(titel) == pytest.approx(0.10)


def test_top5_veraenderung_ist_none_wenn_alle_titel_unbekannt_sind():
    titel = [{"veraenderung": None}, {"veraenderung": None}]
    assert _top5_veraenderung(titel) is None


def test_index_vergleich_kriterium_3_beispiel_monat():
    """Nachweis-Testfall (Kriterium 3): ein nachvollziehbares Beispiel, bei
    dem Top-5 UND Index von Hand nachgerechnet werden koennen.

    Zwei Top-5-Titel: AAA +10 %, BBB +6 % -> Mittel +8 %.
    Index: 4000 -> 4200 -> +5 %.
    Differenz: +8 % - +5 % = +3 Punkte -- die Auswahl lag hier VOR dem
    Index, das Vorzeichen ist rein rechnerisch, keine Wertung im Code.
    """
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0), ("BBB", "Firma BBB", 100.0)])
    bundle = _bundle(
        {"AAA": {Date(2026, 8, 31): 110.0}, "BBB": {Date(2026, 8, 31): 106.0}}
    )
    index_series = {Date(2026, 7, 31): 4000.0, Date(2026, 8, 31): 4200.0}
    ev = build_evaluation(
        prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31), index_series=index_series
    )

    iv = ev["index_vergleich"]
    assert iv["index_ticker"] == "^SP500TR"
    assert iv["start"] == 4000.0
    assert iv["end"] == 4200.0
    assert iv["veraenderung"] == pytest.approx(0.05)
    assert iv["top5_veraenderung"] == pytest.approx(0.08)
    assert iv["differenz"] == pytest.approx(0.03)
    assert ev["schema"] == 2


def test_index_vergleich_faellt_soft_aus_wenn_keine_indexreihe_uebergeben_wird():
    """Vorgabewert None -- kein Absturz, sichtbar leer statt geraten. Ticker
    und Name des Index bleiben trotzdem bekannt (aus `market`), nur die
    Werte fehlen."""
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0)])
    bundle = _bundle({"AAA": {Date(2026, 8, 31): 110.0}})
    ev = build_evaluation(prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31))

    iv = ev["index_vergleich"]
    assert iv["index_ticker"] == "^SP500TR"
    assert iv["start"] is None
    assert iv["end"] is None
    assert iv["veraenderung"] is None
    assert iv["differenz"] is None
    # Die Top-5-eigene Zahl bleibt bekannt -- sie haengt nicht am Index.
    assert iv["top5_veraenderung"] == pytest.approx(0.10)


def test_index_vergleich_faellt_soft_aus_bei_luecke_im_start_oder_endtag():
    """Die Indexreihe existiert, deckt aber genau den benoetigten Tag
    nicht ab (z. B. ein echter Datenausfall) -- auch dann keine Erfindung."""
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0)])
    bundle = _bundle({"AAA": {Date(2026, 8, 31): 110.0}})
    index_series = {Date(2026, 8, 31): 4200.0}  # 31.07. fehlt
    ev = build_evaluation(
        prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31), index_series=index_series
    )
    assert ev["index_vergleich"]["veraenderung"] is None


def test_index_vergleich_ist_deterministisch():
    """Kriterium 7: gleiche Eingaben -> immer dieselben gerundeten Werte,
    kein Rundungs-Zufall zwischen zwei Aufrufen."""
    prev = _prev_ranking([("AAA", "Firma AAA", 100.0), ("BBB", "Firma BBB", 100.0)])
    bundle = _bundle(
        {"AAA": {Date(2026, 8, 31): 103.0}, "BBB": {Date(2026, 8, 31): 97.0}}
    )
    index_series = {Date(2026, 7, 31): 4000.0, Date(2026, 8, 31): 4030.0}
    ev1 = build_evaluation(
        prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31), index_series=index_series
    )
    ev2 = build_evaluation(
        prev, MARKETS_BY_KEY["us"], bundle, Date(2026, 8, 31), index_series=index_series
    )
    assert ev1["index_vergleich"] == ev2["index_vergleich"]
