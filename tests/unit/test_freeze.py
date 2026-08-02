"""MONATS-EINFRIERUNG: ein Lauf mitten im Monat darf das Ranking nicht anfassen.

Bewiesen wird beides:
  * die Ranking-Datei bleibt BYTE-IDENTISCH
  * die Anzeige-Kurse aendern sich sehr wohl
und zusaetzlich der technische Riegel: an einem gewoehnlichen Tag werden
die Daten, aus denen ein Ranking entstehen koennte, gar nicht erst geladen.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import replace

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.ranking import RankingNotPossible, write_ranking
from momentum.run import process_market
from tests.conftest import index_series, make_downloader, sample_series, write_universe

Date = _dt.date
STICHTAG = Date(2026, 7, 31)
MITTE_AUGUST = Date(2026, 8, 5)


def _markt(tmp_path):
    uni = write_universe(tmp_path / "universe_us.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    return replace(MARKETS_BY_KEY["us"], universe_file=str(uni))


def _daten(spaetere_kurse: dict[str, float] | None = None):
    serien = sample_series()
    if spaetere_kurse:
        for ticker, kurs in spaetere_kurse.items():
            for tag in (Date(2026, 8, 3), Date(2026, 8, 4), Date(2026, 8, 5)):
                serien[ticker][tag] = kurs
    serien["^GSPC"] = index_series()
    return serien


def test_lauf_mitten_im_monat_laesst_das_ranking_byte_identisch(tmp_path):
    markt = _markt(tmp_path)
    wurzel = tmp_path / "rankings"
    daten = tmp_path / "data"

    # --- Stichtags-Lauf 31.07.2026 -------------------------------------
    view1, neu1, _ = process_market(
        markt,
        STICHTAG,
        downloader=make_downloader(_daten()),
        ranking_root=wurzel,
        data_root=daten,
    )
    assert neu1 is not None, "am Stichtag muss ein Ranking entstehen"
    datei = wurzel / "us_2026-07.json"
    vorher = datei.read_bytes()
    kurse_vorher = dict(view1.prices)

    # --- Lauf mitten im Monat, mit DEUTLICH anderen Kursen -------------
    view2, neu2, _ = process_market(
        markt,
        MITTE_AUGUST,
        downloader=make_downloader(
            _daten({"AAA": 999.0, "BBB": 1.0, "CCC": 500.0, "DDD": 2.0, "EEE": 300.0})
        ),
        ranking_root=wurzel,
        data_root=daten,
    )

    assert neu2 is None, "mitten im Monat darf kein neues Ranking entstehen"
    assert datei.read_bytes() == vorher, "Ranking-Datei wurde veraendert"
    assert view2.ranking["rangliste"] == view1.ranking["rangliste"]
    assert view2.ranking["top"] == view1.ranking["top"]
    assert view2.ranking["stichtag"] == "2026-07-31"

    # ... aber die Anzeige-Kurse sind neu und ehrlich datiert
    assert view2.price_asof == MITTE_AUGUST
    assert view2.prices != kurse_vorher
    assert view2.prices["AAA"] == pytest.approx(999.0)


def test_anzeige_lauf_laedt_nur_die_top5_nicht_das_universum(tmp_path):
    """Technischer Riegel: die Daten fuer ein neues Ranking werden gar nicht geholt."""
    markt = _markt(tmp_path)
    wurzel = tmp_path / "rankings"
    daten = tmp_path / "data"
    process_market(
        markt,
        STICHTAG,
        downloader=make_downloader(_daten()),
        ranking_root=wurzel,
        data_root=daten,
    )

    angefragt: list[list[str]] = []
    basis = make_downloader(_daten({"AAA": 111.0, "BBB": 111.0, "CCC": 111.0, "DDD": 111.0, "EEE": 111.0}))

    def mitschnitt(batch, start, end):
        angefragt.append(list(batch))
        return basis(batch, start, end)

    process_market(
        markt, MITTE_AUGUST, downloader=mitschnitt, ranking_root=wurzel, data_root=daten
    )

    assert len(angefragt) == 1, "Anzeige-Lauf darf genau einen Abruf machen"
    assert sorted(angefragt[0]) == ["AAA", "BBB", "CCC", "DDD", "EEE"]
    assert "^GSPC" not in angefragt[0], "kein Indexabruf noetig, es wird nicht gerankt"


def test_naechster_stichtag_bildet_ein_neues_ranking(tmp_path):
    """31.08.2026 ist ein Montag und der letzte Werktag — dann wird neu gerankt."""
    markt = _markt(tmp_path)
    wurzel = tmp_path / "rankings"
    daten = tmp_path / "data"
    process_market(
        markt, STICHTAG, downloader=make_downloader(_daten()), ranking_root=wurzel, data_root=daten
    )

    serien = _daten()
    for ticker in ("AAA", "BBB", "CCC", "DDD", "EEE"):
        serien[ticker][Date(2026, 8, 31)] = serien[ticker][Date(2026, 7, 31)] * 1.1
    serien["^GSPC"][Date(2026, 8, 31)] = 4300.0

    view, neu, _ = process_market(
        markt,
        Date(2026, 8, 31),
        downloader=make_downloader(serien),
        ranking_root=wurzel,
        data_root=daten,
    )
    assert neu is not None
    assert neu["ranking_monat"] == "2026-08"
    assert neu["stichtag"] == "2026-08-31"
    assert (wurzel / "us_2026-07.json").exists(), "das alte Ranking bleibt erhalten"


def test_bestehendes_ranking_wird_nie_ueberschrieben(tmp_path):
    ranking = {"markt": "us", "ranking_monat": "2026-07", "rangliste": []}
    write_ranking(ranking, tmp_path)
    with pytest.raises(RankingNotPossible, match="eingefroren"):
        write_ranking(ranking, tmp_path)
