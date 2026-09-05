"""ENDE-ZU-ENDE: der Konfluenz-Push innerhalb eines echten Laufs.

Bewiesen wird, was der Auftrag verlangt:
  * ein NEUER Konfluenz-Treffer loest genau EINEN Push aus,
  * derselbe Treffer beim naechsten Lauf loest KEINEN erneuten Push aus,
  * ein voellig unveraenderter Lauf (kein Treffer je Markt) loest ebenfalls
    keinen Push aus,
  * ein nicht erreichbarer Elliott-Bericht loescht nicht den bisherigen
    Stand (sonst saehe der naechste erfolgreiche Lauf alles als "neu").
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import replace

import pytest

from momentum import run as run_modul
from momentum.config import MARKETS_BY_KEY
from tests.conftest import MONTH_ENDS, index_series, make_downloader, sample_series, write_universe

Date = _dt.date
STICHTAG = Date(2026, 7, 31)
TICKER = ["AAA", "BBB", "CCC", "DDD", "EEE"]


@pytest.fixture
def welt(tmp_path, monkeypatch):
    (tmp_path / "universe").mkdir()
    (tmp_path / "docs").mkdir()
    for datei in ("style.css", "app.js"):
        (tmp_path / "docs" / datei).write_text("/* Platzhalter */", encoding="utf-8")

    maerkte = []
    for key in ("us", "de"):
        pfad = write_universe(
            tmp_path / "universe" / f"universe_{key}.txt", TICKER, label=f"Test {key.upper()}"
        )
        maerkte.append(replace(MARKETS_BY_KEY[key], universe_file=str(pfad)))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_modul, "MARKETS", tuple(maerkte))
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    serien = sample_series()
    serien["^SP500TR"] = index_series()
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}
    serien["^GDAXI"] = index_series([5000.0 + 30.0 * i for i in range(13)])
    return tmp_path, make_downloader(serien)


def _elliott_opener(bericht: dict):
    """Baut einen `opener` mit derselben Form wie urllib.request.urlopen,
    der IMMER `bericht` als JSON zurueckgibt -- kein Netz."""

    class _Antwort:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps(bericht).encode("utf-8")

    def opener(*_args, **_kwargs):
        return _Antwort()

    return opener


def _kaputter_opener():
    def opener(*_args, **_kwargs):
        raise OSError("Elliott-Report gerade nicht erreichbar")

    return opener


def _push_aufzeichnen(monkeypatch):
    verschickt = []
    monkeypatch.setattr(
        run_modul, "push_konfluenz_treffer", lambda treffer, **kw: verschickt.append(treffer) or True
    )
    return verschickt


# US-Top-5 in dieser Welt ist immer ["DDD", "AAA", "EEE", "BBB", "CCC"]
# (siehe test_end_to_end.py::test_kompletter_lauf_erzeugt_alles) -- DDD
# steht an Rang 1.
ELLIOTT_MIT_TREFFER_AUF_DDD = {
    "markets": {
        "US": {"candidates": [
            {"ticker": "DDD", "direction": "long", "company_name": "Firma DDD",
             "score_heuristic": 55.5},
        ]},
        "DE": {"candidates": []},
    }
}

ELLIOTT_OHNE_TREFFER = {
    "markets": {
        "US": {"candidates": [
            {"ticker": "ZZZ", "direction": "long", "company_name": "Ausserhalb",
             "score_heuristic": 10.0},
        ]},
        "DE": {"candidates": []},
    }
}


def test_neuer_treffer_loest_genau_einen_push_aus(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = _push_aufzeichnen(monkeypatch)

    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_MIT_TREFFER_AUF_DDD),
    )
    assert code == 0
    assert len(verschickt) == 1, "genau ein Push fuer den neuen Treffer erwartet"
    treffer = verschickt[0]
    assert [t["ticker"] for t in treffer] == ["DDD"]
    assert treffer[0]["markt"] == "us"
    assert treffer[0]["momentum_rang"] == 1
    assert treffer[0]["elliott_score"] == 55.5

    stand = json.loads(
        (tmp_path / "data/konfluenz_stand.json").read_text(encoding="utf-8")
    )
    assert stand["treffer"] == ["us:DDD"]


def test_derselbe_treffer_am_naechsten_tag_loest_nichts_erneut_aus(welt, monkeypatch):
    """DER Kernfall des Auftrags: kein Ermuedungs-Alarm bei unveraendertem
    Treffer."""
    tmp_path, downloader = welt
    verschickt = _push_aufzeichnen(monkeypatch)

    # Tag 1: der Treffer entsteht.
    run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_MIT_TREFFER_AUF_DDD),
    )
    assert len(verschickt) == 1

    # Tag 2 (Anzeige-Lauf, kein neues Ranking faellig): derselbe Elliott-
    # Bericht, derselbe Treffer -- er ist bereits bekannt.
    code = run_modul.main(
        ["--today", (STICHTAG + _dt.timedelta(days=1)).isoformat()],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_MIT_TREFFER_AUF_DDD),
    )
    assert code == 0
    assert len(verschickt) == 1, "ein bereits bekannter Treffer hat erneut ausgeloest"


def test_lauf_ohne_ueberschneidung_loest_keinen_push_aus(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = _push_aufzeichnen(monkeypatch)

    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_OHNE_TREFFER),
    )
    assert code == 0
    assert verschickt == []
    stand = json.loads(
        (tmp_path / "data/konfluenz_stand.json").read_text(encoding="utf-8")
    )
    assert stand["treffer"] == []


def test_nicht_erreichbarer_bericht_loescht_den_stand_nicht(welt, monkeypatch):
    """Fail-soft: ein Netzausfall darf den bisherigen Stand nicht auf leer
    zuruecksetzen -- sonst saehe der naechste erfolgreiche Lauf jeden
    bisherigen Treffer faelschlich als neu an."""
    tmp_path, downloader = welt
    verschickt = _push_aufzeichnen(monkeypatch)

    run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_MIT_TREFFER_AUF_DDD),
    )
    assert len(verschickt) == 1
    stand_vorher = (tmp_path / "data/konfluenz_stand.json").read_text(encoding="utf-8")

    code = run_modul.main(
        ["--today", (STICHTAG + _dt.timedelta(days=1)).isoformat()],
        downloader=downloader,
        elliott_oeffner=_kaputter_opener(),
    )
    assert code == 0, "ein nicht erreichbarer Elliott-Bericht darf den Lauf nicht rot machen"
    assert len(verschickt) == 1, "kein weiterer Push bei nicht erreichbarem Bericht"
    stand_nachher = (tmp_path / "data/konfluenz_stand.json").read_text(encoding="utf-8")
    assert stand_nachher == stand_vorher, "der Stand wurde trotz Netzausfall angefasst"


def test_no_push_schalter_unterdrueckt_auch_den_konfluenz_push(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = _push_aufzeichnen(monkeypatch)

    code = run_modul.main(
        ["--today", STICHTAG.isoformat(), "--no-push"],
        downloader=downloader,
        elliott_oeffner=_elliott_opener(ELLIOTT_MIT_TREFFER_AUF_DDD),
    )
    assert code == 0
    assert verschickt == []
    assert not (tmp_path / "data/konfluenz_stand.json").exists(), (
        "--no-push darf auch nicht heimlich den Stand fortschreiben"
    )
