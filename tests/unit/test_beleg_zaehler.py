"""BELEG-ZAEHLER in data.download_prices (reine Beobachtung).

Zweck: belegen, ob Yahoo bei der naechtlichen Verzoegerung die Tageszeile
MIT gueltigem Rohkurs (Close) liefert und nur Adj Close fehlt -- die
ungepruefte Annahme hinter Variante V3 der Stichtags-Pruefung
(SESSION_HANDOVER.md §4 Punkt 16).

Bewiesen wird:
  * Close ok / Adj NaN  -> "mit Rohkurs" +1
  * Close NaN / Adj NaN -> "ohne Rohkurs" +1
  * mit + ohne == zeilen_verworfen_nicht_endlich (nie ein Widerspruch)
  * Datums-Zaehlung je Tag stimmt, nach aussen auf die juengsten 3 Tage
    begrenzt, aufsteigend sortiert
  * WELCHE Zeilen verworfen werden, aendert sich nicht (adjusted/close/
    turnover gleich wie ohne Zaehler)
"""

from __future__ import annotations

import datetime as _dt
import json

import pytest

from momentum.data import VERWORFEN_TAGE_MAX, FetchStats, download_prices
from tests.conftest import make_downloader

Date = _dt.date
NAN = float("nan")
TAGE = [Date(2026, 10, d) for d in (26, 27, 28, 29, 30)]


def _abruf(serien, roh, *, tickers=None):
    tickers = tickers or sorted(serien)
    return download_prices(
        tickers, TAGE[0], TAGE[-1], downloader=make_downloader(serien, raw_close=roh)
    )


def test_close_ok_adj_nan_zaehlt_mit_rohkurs():
    serien = {"AAA": {t: 100.0 for t in TAGE}}
    serien["AAA"][TAGE[-1]] = NAN
    roh = {"AAA": {TAGE[-1]: 101.0}}
    stats = _abruf(serien, roh).stats.as_dict()
    assert stats["zeilen_verworfen_nicht_endlich"] == 1
    assert stats["zeilen_verworfen_mit_rohkurs"] == 1
    assert stats["zeilen_verworfen_ohne_rohkurs"] == 0
    assert stats["verworfen_je_tag_juengste"] == {"2026-10-30": 1}


def test_close_nan_adj_nan_zaehlt_ohne_rohkurs():
    serien = {"AAA": {t: 100.0 for t in TAGE}}
    serien["AAA"][TAGE[-1]] = NAN
    roh = {"AAA": {TAGE[-1]: NAN}}
    stats = _abruf(serien, roh).stats.as_dict()
    assert stats["zeilen_verworfen_nicht_endlich"] == 1
    assert stats["zeilen_verworfen_mit_rohkurs"] == 0
    assert stats["zeilen_verworfen_ohne_rohkurs"] == 1


def test_nicht_positiver_rohkurs_zaehlt_ohne_rohkurs():
    """"Mit Rohkurs" heisst: derselbe gueltige Close wie im Vergleichspfad
    (endlich UND > 0, siehe close_valid in data.py)."""
    serien = {"AAA": {t: 100.0 for t in TAGE}}
    serien["AAA"][TAGE[-1]] = NAN
    roh = {"AAA": {TAGE[-1]: 0.0}}
    stats = _abruf(serien, roh).stats.as_dict()
    assert stats["zeilen_verworfen_ohne_rohkurs"] == 1


def test_summe_passt_immer_zu_verworfen_und_tage_auf_drei_begrenzt():
    # 4 Titel, verworfene Tage gemischt: alle 5 Tage kommen vor, nach aussen
    # nur die juengsten 3.
    serien = {t: {d: 50.0 for d in TAGE} for t in ("AAA", "BBB", "CCC", "DDD")}
    roh: dict = {t: {} for t in serien}
    # 30.10.: alle vier ohne Adj, drei mit Rohkurs, einer ohne
    for t in serien:
        serien[t][TAGE[4]] = NAN
        roh[t][TAGE[4]] = 51.0
    roh["DDD"][TAGE[4]] = NAN
    # 29.10.: zwei; 28.10.: einer; 27.10. und 26.10.: je einer (fallen raus)
    for t in ("AAA", "BBB"):
        serien[t][TAGE[3]] = NAN
    serien["CCC"][TAGE[2]] = float("inf")
    serien["AAA"][TAGE[1]] = -1.0
    serien["BBB"][TAGE[0]] = NAN
    stats = _abruf(serien, roh).stats
    d = stats.as_dict()
    assert d["zeilen_verworfen_nicht_endlich"] == 4 + 2 + 1 + 1 + 1
    assert (
        d["zeilen_verworfen_mit_rohkurs"] + d["zeilen_verworfen_ohne_rohkurs"]
        == d["zeilen_verworfen_nicht_endlich"]
    )
    # vollstaendig im Speicher ...
    assert stats.dropped_by_day == {
        TAGE[0]: 1, TAGE[1]: 1, TAGE[2]: 1, TAGE[3]: 2, TAGE[4]: 4,
    }
    # ... nach aussen nur die juengsten drei, aufsteigend
    assert VERWORFEN_TAGE_MAX == 3
    assert list(d["verworfen_je_tag_juengste"].items()) == [
        ("2026-10-28", 1), ("2026-10-29", 2), ("2026-10-30", 4),
    ]
    # bleibt JSON-tauglich und deterministisch
    assert json.dumps(d, sort_keys=True) == json.dumps(stats.as_dict(), sort_keys=True)


def test_ohne_verworfene_zeilen_sind_die_zaehler_null_und_leer():
    serien = {"AAA": {t: 100.0 for t in TAGE}}
    d = _abruf(serien, None).stats.as_dict()
    assert d["zeilen_verworfen_nicht_endlich"] == 0
    assert d["zeilen_verworfen_mit_rohkurs"] == 0
    assert d["zeilen_verworfen_ohne_rohkurs"] == 0
    assert d["verworfen_je_tag_juengste"] == {}


def test_bestehende_felder_unveraendert_und_nur_ergaenzt():
    alt = {
        "angefragt", "geliefert", "zeilen_gesamt", "zeilen_verworfen_nicht_endlich",
        "ticker_ohne_daten", "fehlgeschlagene_bloecke",
    }
    neu = {"zeilen_verworfen_mit_rohkurs", "zeilen_verworfen_ohne_rohkurs",
           "verworfen_je_tag_juengste"}
    assert set(FetchStats().as_dict()) == alt | neu


def test_welche_zeilen_verworfen_werden_aendert_sich_nicht():
    """Gleiche Eingabe -> gleiche Reihen wie die bisherige Regel: Score-Pfad
    ohne den Tag, Vergleichspfad mit dem gueltigen Rohkurs."""
    serien = {"AAA": {t: 100.0 + i for i, t in enumerate(TAGE)}}
    serien["AAA"][TAGE[-1]] = NAN
    roh = {"AAA": {TAGE[-1]: 105.0}}
    b = _abruf(serien, roh)
    assert TAGE[-1] not in b.adjusted["AAA"]
    assert TAGE[-1] not in b.turnover["AAA"]
    assert b.close["AAA"][TAGE[-1]] == pytest.approx(105.0)
    assert sorted(b.adjusted["AAA"]) == TAGE[:-1]


def test_log_zeile_nur_bei_verworfenen_zeilen(capsys):
    serien = {"AAA": {t: 100.0 for t in TAGE}}
    _abruf(serien, None)
    assert "[daten]" not in capsys.readouterr().out
    serien["AAA"][TAGE[-1]] = NAN
    _abruf(serien, {"AAA": {TAGE[-1]: 101.0}})
    zeile = capsys.readouterr().out
    assert "[daten] 1 Titel (ab AAA): 1 Zeilen ohne gueltiges Adj Close verworfen" in zeile
    assert "davon mit Rohkurs 1, ohne Rohkurs 0" in zeile
    assert "'2026-10-30': 1" in zeile
