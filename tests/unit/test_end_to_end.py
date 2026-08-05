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
from tests.conftest import (
    MONTH_ENDS,
    index_series,
    make_downloader,
    sample_series,
    write_universe,
)

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
    serien["^SP500TR"] = index_series()
    # Der Dollar-Geldmarktsatz kommt aus derselben Kursquelle. Fuer den
    # Euro wird bewusst KEINE Quelle eingespielt: der DE-Markt laeuft damit
    # durch den Fail-soft-Pfad, und beide Wege sind in einem Lauf geprueft.
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}
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
    assert us["top"] == ["DDD", "AAA", "EEE", "BBB", "CCC"]
    assert us["trend_ampel"]["warnung"] is False
    # US: Zins gezogen (3 % im Mittel), Ueberschuss = Rendite minus Zins.
    assert us["trend_ampel"]["riskfree_12m"] == pytest.approx(0.03)
    assert us["trend_ampel"]["ueberschuss_12m"] == pytest.approx(
        us["trend_ampel"]["rendite_12m"] - 0.03
    )

    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    # Perzentile werden je Markt getrennt gebildet — gleiche Kurse, gleiche Reihenfolge
    assert de["top"] == us["top"]
    assert de["trend_ampel"]["warnung"] is True, "DAX faellt in dieser Welt"
    # DE: ohne erreichbare Zinsquelle wird NICHTS geschaetzt -- kein Abzug,
    # und der Ausfall steht als Herkunft im Report.
    assert de["trend_ampel"]["riskfree_12m"] is None
    assert de["trend_ampel"]["riskfree_quelle"] == "nicht erreichbar"
    assert de["trend_ampel"]["ueberschuss_12m"] == de["trend_ampel"]["rendite_12m"]

    # Seiten erzeugt
    index = (tmp_path / "docs/index.html").read_text(encoding="utf-8")
    assert "Momentum-Report" in index
    assert "Ranking vom 31.07." in index
    assert "Momentum-Gefahrenlage:" in index, "die DE-Warnlage muss sichtbar sein"
    # Der fehlende Euro-Zins steht sichtbar auf der Seite, nicht nur im Log.
    assert "ohne Zins-Abzug — Zinsquelle nicht erreichbar" in index
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
    assert all(e["top"] == "DDD" for e in eintraege)


def test_der_euro_zins_erreicht_das_ranking(welt, monkeypatch):
    """Die zweite Zinsquelle, durch den ganzen Lauf gereicht.

    Eingespielt wird die EZB-Antwort im echten CSV-Format; ohne die
    Einspielung greift der Fail-soft-Pfad (siehe Test oben). Damit sind
    beide Wege der EUR-Seite belegt.
    """
    tmp_path, downloader = welt
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    kopf = "KEY,FREQ,REF_AREA,PROVIDER_FM_ID,TIME_PERIOD,OBS_VALUE,OBS_STATUS"
    zeilen = [
        f"EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,{tag.isoformat()},2.0,A"
        for tag in MONTH_ENDS
    ]
    antwort = "\n".join([kopf, *zeilen]) + "\n"

    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        zins_oeffner=lambda _url: antwort,
    )
    assert code == 0

    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    ampel = de["trend_ampel"]
    assert ampel["riskfree_12m"] == pytest.approx(0.02)
    assert "EZB" in ampel["riskfree_quelle"]
    assert ampel["ueberschuss_12m"] == pytest.approx(ampel["rendite_12m"] - 0.02)
    # Der Hinweis auf den Ausfall darf jetzt NICHT mehr dastehen.
    index = (tmp_path / "docs/index.html").read_text(encoding="utf-8")
    assert "ohne Zins-Abzug" not in index


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


# --------------------------------------------------------------------------
# VERDRAHTUNGSPROBE im Lauf
# --------------------------------------------------------------------------


def test_ohne_den_schalter_geht_keine_probe_raus(welt, monkeypatch):
    """Der Standardfall: kein Testpush, egal was sonst passiert."""
    tmp_path, downloader = welt
    proben = []
    monkeypatch.setattr(run_modul, "push_test", lambda **kw: proben.append(kw) or True)
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    assert run_modul.main(["--today", "2026-07-31"], downloader=downloader) == 0
    assert proben == [], "es ging ein Testpush raus, ohne dass er angefordert wurde"


def test_mit_dem_schalter_geht_genau_eine_probe_raus(welt, monkeypatch, capsys):
    tmp_path, downloader = welt
    proben = []
    monkeypatch.setattr(run_modul, "push_test", lambda **kw: proben.append(kw) or True)
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    assert run_modul.main(
        ["--today", "2026-07-31", "--testpush"], downloader=downloader
    ) == 0
    assert len(proben) == 1, "genau eine Probe, nicht mehr und nicht weniger"
    assert "Testpush: verschickt." in capsys.readouterr().out


def test_die_probe_aendert_nichts_an_den_daten(welt, monkeypatch):
    """Sie laeuft zusaetzlich — der Lauf selbst bleibt Zeichen fuer Zeichen gleich."""
    tmp_path, downloader = welt
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)
    monkeypatch.setattr(run_modul, "push_test", lambda **kw: True)

    run_modul.main(["--today", "2026-07-31"], downloader=downloader)
    ohne = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in sorted(tmp_path.rglob("*"))
        if p.is_file()
    }

    run_modul.main(["--today", "2026-07-31", "--testpush"], downloader=downloader)
    mit = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in sorted(tmp_path.rglob("*"))
        if p.is_file()
    }
    assert set(mit) == set(ohne), "die Probe hat Dateien angelegt oder entfernt"
    for name in ohne:
        if name.parts[:2] == ("data", "rankings"):
            assert mit[name] == ohne[name], f"{name} wurde veraendert"


def test_ein_fehlschlag_der_probe_steht_im_protokoll(welt, monkeypatch, capsys):
    """Erfolg UND Fehler bekommen eine eigene, klare Zeile."""
    tmp_path, downloader = welt
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)
    monkeypatch.setattr(run_modul, "push_test", lambda **kw: False)

    assert run_modul.main(
        ["--today", "2026-07-31", "--testpush"], downloader=downloader
    ) == 0, "eine misslungene Probe darf den Lauf nicht rot machen"
    ausgabe = capsys.readouterr().out
    assert "Testpush: NICHT verschickt" in ausgabe


def test_ohne_push_schlaegt_die_probe_nicht_durch(welt, monkeypatch, capsys):
    """Wer ausdruecklich keine Pushes will, bekommt auch keine Probe."""
    tmp_path, downloader = welt
    proben = []
    monkeypatch.setattr(run_modul, "push_test", lambda **kw: proben.append(kw) or True)

    run_modul.main(
        ["--today", "2026-07-31", "--testpush", "--no-push"], downloader=downloader
    )
    assert proben == []
    assert "uebersprungen, weil --no-push" in capsys.readouterr().out
