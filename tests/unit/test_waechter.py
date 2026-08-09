"""Der Totmannschalter (waechter.py) — geprueft ohne Netz.

Die Kernaussage, die hier festgehalten wird: Der Waechter schlaegt GENAU
DANN an, wenn die Stille nicht mehr normal erklaerbar ist — und jede Form
von "kann das Alter nicht bestimmen" zaehlt als Alarm, nie als "wird
schon passen". Und: solange alles laeuft, schweigt er (kein Herzschlag).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest
import yaml

from momentum.waechter import SCHWELLE_TAGE, befund, main

Date = _dt.date

# Ein Montag -- der Wochentag, an dem der Waechter planmaessig laeuft.
MONTAG = Date(2026, 8, 10)
assert MONTAG.weekday() == 0


def status_datei(tmp_path: Path, lauf_datum: str) -> Path:
    pfad = tmp_path / "status.json"
    pfad.write_text(json.dumps({"lauf_datum": lauf_datum}), encoding="utf-8")
    return pfad


# ------------------------------------------------------------ Die Schwelle


def test_das_wochenende_ist_keine_stille():
    """Freitags-Lauf, Montags-Pruefung: drei Tage, kein Alarm."""
    freitag = MONTAG - _dt.timedelta(days=3)
    alter, grund = befund_mit(freitag.isoformat())
    assert (alter, grund) == (3, None)


def test_ein_bereits_gemeldeter_einzelfehlschlag_ist_keine_stille():
    """Donnerstag-Stand am Montag (Freitag war rot und hat sich selbst
    gemeldet): vier Tage, kein Alarm — sonst wuerde jeder Einzelfehlschlag
    doppelt gemeldet."""
    donnerstag = MONTAG - _dt.timedelta(days=4)
    alter, grund = befund_mit(donnerstag.isoformat())
    assert (alter, grund) == (4, None)


def test_ab_fuenf_tagen_ist_es_alarm():
    mittwoch = MONTAG - _dt.timedelta(days=5)
    alter, grund = befund_mit(mittwoch.isoformat())
    assert alter == 5
    assert grund is not None and "vor 5 Kalendertagen" in grund


def test_eine_woche_stille_ist_sicher_alarm():
    alter, grund = befund_mit((MONTAG - _dt.timedelta(days=7)).isoformat())
    assert alter == 7 and grund is not None


def befund_mit(lauf_datum: str, tmp_path=None):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = status_datei(Path(tmp), lauf_datum)
        return befund(pfad, MONTAG)


# --------------------------------------- Unlesbar ist Alarm, nicht Achselzucken


def test_fehlende_datei_ist_alarm(tmp_path):
    alter, grund = befund(tmp_path / "gibt-es-nicht.json", MONTAG)
    assert alter is None
    assert grund is not None and "existiert nicht" in grund


def test_kaputtes_json_ist_alarm(tmp_path):
    pfad = tmp_path / "status.json"
    pfad.write_text("{halb geschrie", encoding="utf-8")
    alter, grund = befund(pfad, MONTAG)
    assert alter is None and grund is not None


def test_fehlendes_oder_unsinniges_lauf_datum_ist_alarm(tmp_path):
    for inhalt in ({}, {"lauf_datum": "gestern"}, {"lauf_datum": None}):
        pfad = tmp_path / "status.json"
        pfad.write_text(json.dumps(inhalt), encoding="utf-8")
        alter, grund = befund(pfad, MONTAG)
        assert alter is None and grund is not None, inhalt


# ------------------------------------------------- main: Push und Exit-Code


def test_im_normalfall_kein_push_und_exit_null(tmp_path):
    """KEIN Herzschlag: solange alles laeuft, geht nichts raus."""
    pfad = status_datei(tmp_path, (MONTAG - _dt.timedelta(days=3)).isoformat())
    gerufen = []
    code = main(
        ["--heute", MONTAG.isoformat(), "--status", str(pfad)],
        melder=lambda grund: gerufen.append(grund) or True,
    )
    assert code == 0
    assert gerufen == [], "der Waechter hat ohne Grund gefunkt"


def test_im_alarmfall_genau_ein_push_und_exit_eins(tmp_path):
    pfad = status_datei(tmp_path, (MONTAG - _dt.timedelta(days=9)).isoformat())
    gerufen = []
    code = main(
        ["--heute", MONTAG.isoformat(), "--status", str(pfad)],
        melder=lambda grund: gerufen.append(grund) or True,
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "vor 9 Kalendertagen" in gerufen[0]


def test_auch_ein_gescheiterter_push_laesst_den_lauf_rot_enden(tmp_path):
    """Der rote Waechter-Lauf ist das zweite, vom ntfy-Weg unabhaengige
    Signal — er darf nicht davon abhaengen, ob der Push durchging."""
    pfad = status_datei(tmp_path, (MONTAG - _dt.timedelta(days=9)).isoformat())
    code = main(
        ["--heute", MONTAG.isoformat(), "--status", str(pfad)],
        melder=lambda grund: False,
    )
    assert code == 1


def test_der_alarm_geht_durch_denselben_push_wie_alles_andere():
    """Kein Sonderweg: push_lauf_ueberfaellig ruft notify.push -- dieselbe
    Thema-Pruefung, dieselbe Fehlerbehandlung wie jeder echte Push."""
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    assert "def push_lauf_ueberfaellig" in quelltext
    # Grober, aber ehrlicher Nachweis: die Funktion delegiert an push(...)
    # und baut keinen eigenen urllib-Aufruf.
    koerper = quelltext.split("def push_lauf_ueberfaellig")[1].split("\ndef ")[0]
    assert "return push(" in koerper
    assert "urllib" not in koerper
    assert notify.push_lauf_ueberfaellig  # importierbar


# ------------------------------------------------------------ Der Workflow


def test_der_waechter_workflow_ist_ein_eigener_und_kann_nicht_schreiben():
    daten = yaml.safe_load(
        Path(".github/workflows/waechter.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read"}
    # Woechentlich UND von Hand ausloesbar.
    zeitplaene = daten[True]["schedule"] if True in daten else daten["on"]["schedule"]
    assert len(zeitplaene) == 1
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "workflow_dispatch" in ausloeser
    # Der Alarm braucht das Secret -- ohne kaeme nur der rote Lauf.
    text = Path(".github/workflows/waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text
    # Und der Lauf selbst darf den Waechter nicht enthalten: ein Schritt im
    # Lauf kann das Ausbleiben des Laufs nicht bemerken.
    assert "waechter" not in Path(".github/workflows/lauf.yml").read_text(encoding="utf-8")


def test_die_schwelle_passt_zur_herleitung():
    """Wochenende = 3, plus ein bereits gemeldeter Einzel-Fehlschlag = 4.
    Wer die Schwelle aendert, muss die Herleitung im Docstring mitaendern —
    dieser Test zwingt zumindest dazu, hier vorbeizukommen."""
    assert SCHWELLE_TAGE == 4
