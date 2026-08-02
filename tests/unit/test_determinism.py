"""DETERMINISMUS: zwei Laeufe auf denselben Daten -> identisches Ranking.

Einschliesslich der Gleichstands-Faelle: BBB und DDD haben im Kunst-Beispiel
exakt dasselbe 12-1-Momentum (+0,20) und exakt dieselbe 52-Wochen-Naehe
(1,00). Genau dort entscheidet der alphabetische Gleichstandsbruch.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import replace

from momentum.config import MARKETS_BY_KEY
from momentum.data import download_prices
from momentum.ranking import build_ranking, dump_ranking
from momentum.universe import load_universe
from tests.conftest import ASOF, index_series, make_downloader, sample_series, write_universe

Date = _dt.date


def _aufbau(tmp_path, reihenfolge):
    tmp_path.mkdir(parents=True, exist_ok=True)
    uni = write_universe(tmp_path / "u.txt", reihenfolge)
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(uni))
    universum = load_universe(uni)
    serien = sample_series()
    bundle = download_prices(
        list(universum.tickers),
        Date(2025, 1, 1),
        ASOF,
        downloader=make_downloader(serien),
    )
    return build_ranking(markt, universum, bundle, index_series(), ASOF)


def test_zwei_laeufe_liefern_byte_identische_rankings(tmp_path):
    a = _aufbau(tmp_path / "a", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    b = _aufbau(tmp_path / "b", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    assert dump_ranking(a) == dump_ranking(b)


def test_reihenfolge_im_universum_aendert_nichts(tmp_path):
    """Auch bei umgedrehter Eingabereihenfolge kommt dasselbe Ranking heraus."""
    a = _aufbau(tmp_path / "a", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    b = _aufbau(tmp_path / "b", ["EEE", "DDD", "CCC", "BBB", "AAA"])
    assert dump_ranking(a) == dump_ranking(b)


def test_gleichstand_wird_in_beiden_kennzahlen_deterministisch_gebrochen(tmp_path):
    """BBB und DDD sind in 12-1 UND in der 52W-Naehe gleichauf."""
    ranking = _aufbau(tmp_path, ["AAA", "BBB", "CCC", "DDD", "EEE"])
    nach_ticker = {r["ticker"]: r for r in ranking["rangliste"]}

    assert nach_ticker["BBB"]["momentum_12_1"] == nach_ticker["DDD"]["momentum_12_1"]
    assert nach_ticker["BBB"]["high_52w"] == nach_ticker["DDD"]["high_52w"]
    # alphabetisch frueher -> kleineres Perzentil -> kleinerer Score
    assert nach_ticker["BBB"]["score"] < nach_ticker["DDD"]["score"]
    assert nach_ticker["BBB"]["rang"] > nach_ticker["DDD"]["rang"]


def test_top5_entspricht_der_handrechnung(tmp_path):
    ranking = _aufbau(tmp_path, ["AAA", "BBB", "CCC", "DDD", "EEE"])
    assert ranking["top"] == ["EEE", "AAA", "DDD", "BBB", "CCC"]
    assert [r["rang"] for r in ranking["rangliste"]] == [1, 2, 3, 4, 5]


def test_ranking_datei_enthaelt_keinen_zeitstempel(tmp_path):
    """Ohne Erzeugungs-Zeitstempel ist Byte-Identitaet ueberhaupt erst moeglich."""
    text = dump_ranking(_aufbau(tmp_path, ["AAA", "BBB", "CCC", "DDD", "EEE"]))
    for verboten in ("erzeugt", "timestamp", "generated_at", "lauf_zeit"):
        assert verboten not in text.lower()
