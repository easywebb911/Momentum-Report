"""ENDE-ZU-ENDE: der komplette Lauf, in einem Wegwerf-Verzeichnis.

Geprueft wird, dass ein echter Lauf
  * beide Maerkte verarbeitet,
  * die Ranking-Dateien schreibt,
  * die Seiten erzeugt,
  * genau einen Push mit BEIDEN Top-Titeln verschickt,
und dass ein zweiter Lauf am selben Tag nichts am Ranking aendert.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import replace

import pytest

from momentum import run as run_modul
from momentum.config import MARKETS_BY_KEY
from tests.conftest import index_series, make_downloader, sample_series, write_universe

Date = _dt.date
STICHTAG = Date(2026, 7, 31)
TICKER = ["AAA", "BBB", "CCC", "DDD", "EEE"]


@pytest.fixture
def welt(tmp_path, monkeypatch):
    """Ein vollstaendiges Miniatur-Projekt in einem Wegwerf-Verzeichnis."""
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

    serien = sample_series()
    serien["^GSPC"] = index_series()
    serien["^GDAXI"] = index_series([5000.0 - 30.0 * i for i in range(13)])  # Warnlage
    return tmp_path, make_downloader(serien)


def test_kompletter_lauf_erzeugt_alles(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = []
    monkeypatch.setattr(
        run_modul, "push_new_ranking", lambda entries, **kw: verschickt.append(entries) or True
    )

    code = run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader)
    assert code == 0

    # Rankings geschrieben, je Markt eines
    assert (tmp_path / "data/rankings/us_2026-07.json").exists()
    assert (tmp_path / "data/rankings/de_2026-07.json").exists()

    us = json.loads((tmp_path / "data/rankings/us_2026-07.json").read_text(encoding="utf-8"))
    assert us["stichtag"] == "2026-07-31"
    assert us["top"] == ["EEE", "AAA", "DDD", "BBB", "CCC"]
    assert us["trend_ampel"]["warnung"] is False

    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    # Perzentile werden je Markt getrennt gebildet — gleiche Kurse, gleiche Reihenfolge
    assert de["top"] == us["top"]
    assert de["trend_ampel"]["warnung"] is True, "DAX faellt in dieser Welt"

    # Seiten erzeugt
    index = (tmp_path / "docs/index.html").read_text(encoding="utf-8")
    assert "Momentum-Report" in index
    assert "Ranking vom 31.07." in index
    assert "Momentum-Gefahrenlage:" in index, "die DE-Warnlage muss sichtbar sein"
    assert (tmp_path / "docs/methodik.html").exists()

    # Kurs- und Statusdateien
    kurse = json.loads((tmp_path / "data/kurse_us.json").read_text(encoding="utf-8"))
    assert kurse["stichtag_kurse"] == "2026-07-31"
    status = json.loads((tmp_path / "data/status.json").read_text(encoding="utf-8"))
    assert status["lauf_datum"] == "2026-07-31"
    assert {m["markt"] for m in status["maerkte"]} == {"us", "de"}

    # GENAU EIN Push, mit beiden Maerkten
    assert len(verschickt) == 1
    eintraege = verschickt[0]
    assert {e["markt"] for e in eintraege} == {"USA", "Deutschland"}
    assert all(e["top"] == "EEE" for e in eintraege)


def test_zweiter_lauf_am_selben_tag_aendert_nichts(welt, monkeypatch):
    tmp_path, downloader = welt
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    assert run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader) == 0
    vorher = {
        p.name: p.read_bytes() for p in (tmp_path / "data/rankings").glob("*.json")
    }
    assert run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader) == 0
    nachher = {
        p.name: p.read_bytes() for p in (tmp_path / "data/rankings").glob("*.json")
    }
    assert vorher == nachher


def test_kein_push_mit_no_push(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = []
    monkeypatch.setattr(
        run_modul, "push_new_ranking", lambda entries, **kw: verschickt.append(entries) or True
    )
    run_modul.main(["--today", STICHTAG.isoformat(), "--no-push"], downloader=downloader)
    assert verschickt == []


def test_github_ausgabe_meldet_neues_ranking(welt, monkeypatch, tmp_path_factory):
    tmp_path, downloader = welt
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)
    ausgabe = tmp_path_factory.mktemp("gh") / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(ausgabe))

    run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader)
    assert "ranking_created=true" in ausgabe.read_text(encoding="utf-8")

    run_modul.main(["--today", "2026-08-05"], downloader=downloader)
    assert "ranking_created=false" in ausgabe.read_text(encoding="utf-8")


def test_platzhalter_universum_bricht_den_ganzen_lauf_ab(tmp_path, monkeypatch):
    """Das ausgelieferte Repo darf ohne befuelltes Universum NICHTS erzeugen."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    for key in ("us", "de"):
        (tmp_path / "universe" / f"universe_{key}.txt").write_text(
            "# Universum: X\n# Herkunft: y\n# Stand: 2026-07-31\n# STATUS: PLACEHOLDER\n",
            encoding="utf-8",
        )
    maerkte = tuple(
        replace(MARKETS_BY_KEY[k], universe_file=f"universe/universe_{k}.txt")
        for k in ("us", "de")
    )
    monkeypatch.setattr(run_modul, "MARKETS", maerkte)

    # cli() faengt den Abbruch ab und meldet ihn mit Code 2 — laut, aber
    # ohne Absturz-Rueckverfolgung.
    monkeypatch.setattr("sys.argv", ["momentum.run"])
    assert run_modul.cli() == 2
    assert not (tmp_path / "docs").exists(), "es darf keine Seite entstehen"
    assert not (tmp_path / "data").exists(), "es darf keine Datei entstehen"
