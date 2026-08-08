"""Die Sicherheitsannahme, auf der die Wegwerf-Probe steht.

Die Probe (tools/probelauf.py, siehe .github/workflows/probelauf.yml) hat
KEIN Sonderflag im Produktivcode -- sie ruft `process_market` mit
umgelenkten Wurzeln auf. Das ist der bessere Weg: kein Schalter, den ein
echter Lauf versehentlich setzen koennte, weil es keinen gibt.

Damit haengt aber alles an einer Eigenschaft: `process_market` darf
ausschliesslich unterhalb der uebergebenen Wurzeln schreiben. Waere das
nicht so, wuerde die Probe genau die Dateien anfassen, die sie beweisen
soll. Genau das steht hier -- ohne Netz, mit eingespeisten Kursen.

Diese Datei geht mit dem Rueckbau-PR wieder raus, gemeinsam mit der Probe.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from dataclasses import replace
from pathlib import Path

from momentum.config import MARKETS_BY_KEY
from momentum.run import process_market
from tests.conftest import MONTH_ENDS, index_series, make_downloader, sample_series, write_universe

Date = _dt.date
TICKER = ["AAA", "BBB", "CCC", "DDD", "EEE"]


def abdruck(wurzel: Path) -> dict[str, str]:
    """Pfad -> Pruefsumme fuer alles unterhalb von `wurzel`."""
    return {
        str(p.relative_to(wurzel)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(wurzel.rglob("*"))
        if p.is_file()
    }


def test_process_market_schreibt_nur_in_die_uebergebenen_wurzeln(tmp_path):
    """Der Probe-Lauf darf `data/` und `docs/` des Repos nicht beruehren."""
    datei = write_universe(tmp_path / "u.txt", TICKER, label="Probe")
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))

    serien = sample_series()
    serien[markt.index_ticker] = index_series()
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}

    echt_data, echt_docs = Path("data"), Path("docs")
    vorher_data, vorher_docs = abdruck(echt_data), abdruck(echt_docs)

    ziel = tmp_path / "wegwerf"
    _view, neu, _status = process_market(
        markt,
        Date(2026, 8, 2),
        downloader=make_downloader(serien),
        ranking_root=ziel / "rankings",
        data_root=ziel / "data",
    )

    # Der Lauf hat wirklich gerechnet -- sonst waere der Test wertlos.
    assert neu is not None, "kein Stichtags-Lauf: die Probe wuerde nichts beweisen"
    assert (ziel / "rankings" / "us_2026-07.json").exists()
    assert (ziel / "data" / "kurse_us.json").exists()

    # ... und das echte Repo ist Byte fuer Byte unveraendert geblieben.
    assert abdruck(echt_data) == vorher_data, "process_market hat data/ angefasst"
    assert abdruck(echt_docs) == vorher_docs, "process_market hat docs/ angefasst"


def test_der_zins_pfad_wird_im_stichtags_lauf_wirklich_betreten(tmp_path):
    """Sonst waere PROBE A gruen, ohne je einen Zins geholt zu haben."""
    datei = write_universe(tmp_path / "u.txt", TICKER, label="Probe")
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))

    serien = sample_series()
    serien[markt.index_ticker] = index_series()
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}

    _view, neu, _status = process_market(
        markt,
        Date(2026, 8, 2),
        downloader=make_downloader(serien),
        ranking_root=tmp_path / "r",
        data_root=tmp_path / "d",
    )
    ampel = neu["trend_ampel"]
    assert ampel["riskfree_12m"] is not None
    assert ampel["riskfree_quelle"] != "nicht erreichbar"
    # Und die Probe erkennt den Fail-soft-Fall: ohne ^IRX bleibt das Feld None.
    ohne = process_market(
        markt,
        Date(2026, 8, 2),
        downloader=make_downloader({k: v for k, v in serien.items() if k != "^IRX"}),
        ranking_root=tmp_path / "r2",
        data_root=tmp_path / "d2",
    )[1]
    assert ohne["trend_ampel"]["riskfree_12m"] is None


def test_die_probe_haengt_an_keinem_produktivpfad():
    """Einbahnstrasse: die Probe kennt das Werkzeug, nie umgekehrt."""
    for pfad in sorted(Path("src").rglob("*.py")):
        text = pfad.read_text(encoding="utf-8")
        assert "probelauf" not in text, f"{pfad} verweist auf die Wegwerf-Probe"
    # Und es gibt keinen Probe-Schalter, den ein echter Lauf setzen koennte.
    lauf = Path(".github/workflows/lauf.yml").read_text(encoding="utf-8")
    assert "probelauf" not in lauf, "der echte Lauf darf die Probe nicht kennen"
    # `run.py` spricht von der ntfy-Verdrahtungsprobe (#13) -- das ist etwas
    # anderes. Gemeint ist hier: kein Schalter fuer DIESE Wegwerf-Probe.
    assert "probelauf" not in Path("src/momentum/run.py").read_text(encoding="utf-8")


def test_der_probe_workflow_kann_nicht_schreiben():
    """contents: read ist die eigentliche Sicherung -- nicht die Absicht."""
    text = Path(".github/workflows/probelauf.yml").read_text(encoding="utf-8")
    assert "permissions:\n  contents: read" in text
    assert "timeout-minutes: 20" in text
    assert "schedule:" not in text, "die Probe darf nie von selbst kommen"
    # Nicht das Wort, sondern die Verdrahtung: ohne das Secret im env kann
    # der Probe-Lauf gar nichts verschicken.
    assert "secrets.NTFY_TOPIC" not in text, "aus der Probe geht kein Push raus"
