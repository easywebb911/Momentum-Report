"""Die Schutz-Sperre (schutz_sperre.py) — jetzt eine reine AMPEL, keine
Sperre (siehe Modul-Docstring): geprueft ohne echtes `gh`/Netz (die
Test-Naht `laeufer` ersetzt jeden `gh api`/`git`-Aufruf) und ohne echte
Umgebungsvariablen (`umgebung` ersetzt `os.environ` bei
`lies_ereignis`).

Kernaussagen: ein ungeschuetzter Diff ist gruen; eine geschuetzte Datei
oder eine geaenderte geschuetzte Konstante/Funktion ist rot, MIT einer
klaren Liste der beruehrten Zonen -- ohne jede Freigabe-Moeglichkeit.
Ein "[Wächter]"-PR-Titel mit beruehrter Zone bekommt zusaetzlich einen
eigenen Hinweis. Jeder Lesefehler (Diff) macht ihn rot, nie gruen
(fail-closed). Und: MELDEN, NIE HANDELN, UND KEINE LABEL-/AKTEUR-LOGIK
MEHR -- ein statischer Test belegt beides.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from momentum.schutz_sperre import (
    GESCHUETZTE_SYMBOLE,
    WAECHTER_TITEL_PRAEFIX,
    ermittle_geaenderte_dateien,
    ist_voll_geschuetzter_pfad,
    lies_ereignis,
    main,
    symbol_verletzungen,
)

CONFIG_NAMEN = GESCHUETZTE_SYMBOLE["src/momentum/config.py"]


class _ErgebnisAttrapp:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _laeufer(*, dateien=None, inhalte=None, fehler=None):
    """Baut einen `laeufer`, der `gh api .../files` und
    `git show <sha>:<pfad>` bedient. `inhalte`: {(sha, pfad): text}.
    `fehler`: Menge der Befehlstypen ("dateien"/"show"), die
    stattdessen rc=1 liefern."""
    fehler = fehler or set()
    dateien = dateien if dateien is not None else []
    inhalte = inhalte or {}

    def laeufer(cmd, **kw):
        if cmd[:2] == ["gh", "api"]:
            ziel = cmd[2]
            if "/files" in ziel:
                if "dateien" in fehler:
                    return _ErgebnisAttrapp(1, stderr="HTTP 500")
                return _ErgebnisAttrapp(0, stdout=json.dumps([{"filename": d} for d in dateien]))
            raise AssertionError(f"unerwarteter gh-api-Aufruf: {ziel}")
        if cmd[:2] == ["git", "show"] and len(cmd) == 3:
            if "show" in fehler:
                return _ErgebnisAttrapp(1, stderr="fatal: path does not exist")
            sha, _, pfad = cmd[2].partition(":")
            text = inhalte.get((sha, pfad), "")
            return _ErgebnisAttrapp(0, stdout=text)
        raise AssertionError(f"unerwarteter Aufruf: {cmd}")

    return laeufer


def _ereignis_datei(tmp_path, *, nummer=1, titel="Mein PR", basis="base123", kopf="head456"):
    pfad = tmp_path / "event.json"
    pfad.write_text(
        json.dumps(
            {
                "pull_request": {
                    "number": nummer,
                    "title": titel,
                    "base": {"sha": basis},
                    "head": {"sha": kopf},
                }
            }
        ),
        encoding="utf-8",
    )
    return {"GITHUB_EVENT_PATH": str(pfad), "GITHUB_REPOSITORY": "easywebb911/Momentum-Report"}


# --------------------------------------------------------------- lies_ereignis


def test_lies_ereignis_liest_pull_request_feld(tmp_path):
    umgebung = _ereignis_datei(tmp_path, nummer=42, titel="Titel")
    pr, grund = lies_ereignis(umgebung=umgebung)
    assert grund is None
    assert pr["number"] == 42
    assert pr["title"] == "Titel"


def test_lies_ereignis_fehlender_pfad_ist_fail_closed():
    pr, grund = lies_ereignis(umgebung={})
    assert pr is None
    assert grund is not None


def test_lies_ereignis_kaputtes_json_ist_fail_closed(tmp_path):
    pfad = tmp_path / "event.json"
    pfad.write_text("{halb", encoding="utf-8")
    pr, grund = lies_ereignis(umgebung={"GITHUB_EVENT_PATH": str(pfad)})
    assert pr is None
    assert grund is not None


def test_lies_ereignis_ohne_pull_request_feld_ist_fail_closed(tmp_path):
    pfad = tmp_path / "event.json"
    pfad.write_text(json.dumps({"irgendwas": 1}), encoding="utf-8")
    pr, grund = lies_ereignis(umgebung={"GITHUB_EVENT_PATH": str(pfad)})
    assert pr is None
    assert grund is not None


# --------------------------------------------------------- ist_voll_geschuetzter_pfad


def test_workflow_datei_ist_voll_geschuetzt():
    assert ist_voll_geschuetzter_pfad(".github/workflows/irgendwas.yml") is True


def test_ranking_datendatei_ist_voll_geschuetzt():
    assert ist_voll_geschuetzter_pfad("data/rankings/us_2026-10.json") is True


def test_render_py_ist_nicht_geschuetzt():
    assert ist_voll_geschuetzter_pfad("src/momentum/render.py") is False


# --------------------------------------------------------- symbol_verletzungen


def test_symbol_verletzungen_erkennt_geaenderte_konstante():
    basis = "WEIGHT_MOMENTUM_12_1 = 0.50\nWEIGHT_HIGH_52W = 0.50\n"
    kopf = "WEIGHT_MOMENTUM_12_1 = 0.70\nWEIGHT_HIGH_52W = 0.50\n"
    betroffen = symbol_verletzungen("x.py", basis, kopf, frozenset({"WEIGHT_MOMENTUM_12_1", "WEIGHT_HIGH_52W"}))
    assert betroffen == ["WEIGHT_MOMENTUM_12_1"]


def test_symbol_verletzungen_ungeaenderte_konstante_ist_leer():
    basis = "TOP_N = 5\nWEIGHT_MOMENTUM_12_1 = 0.50\n"
    kopf = "TOP_N = 10\nWEIGHT_MOMENTUM_12_1 = 0.50\n"
    betroffen = symbol_verletzungen("x.py", basis, kopf, frozenset({"WEIGHT_MOMENTUM_12_1"}))
    assert betroffen == []


def test_symbol_verletzungen_erkennt_geaenderte_funktion():
    basis = "def build_ranking():\n    return 1\n"
    kopf = "def build_ranking():\n    return 2\n"
    betroffen = symbol_verletzungen("x.py", basis, kopf, frozenset({"build_ranking"}))
    assert betroffen == ["build_ranking"]


def test_symbol_verletzungen_neu_angelegte_datei_zaehlt_als_beruehrung():
    betroffen = symbol_verletzungen("x.py", "", "WEIGHT_MOMENTUM_12_1 = 0.5\n", frozenset({"WEIGHT_MOMENTUM_12_1"}))
    assert betroffen == ["WEIGHT_MOMENTUM_12_1"]


def test_symbol_verletzungen_kaputter_quelltext_ist_none():
    betroffen = symbol_verletzungen("x.py", "def f(:\n", "def f():\n    pass\n", frozenset({"f"}))
    assert betroffen is None


# --------------------------------------------------- ermittle_geaenderte_dateien


def test_ermittle_geaenderte_dateien():
    laeufer = _laeufer(dateien=["a.py", "b.py"])
    dateien, grund = ermittle_geaenderte_dateien("easywebb911/Momentum-Report", 1, laeufer=laeufer)
    assert grund is None
    assert dateien == ["a.py", "b.py"]


def test_ermittle_geaenderte_dateien_fehlschlag_wird_gemeldet():
    laeufer = _laeufer(fehler={"dateien"})
    dateien, grund = ermittle_geaenderte_dateien("easywebb911/Momentum-Report", 1, laeufer=laeufer)
    assert dateien is None
    assert grund is not None


# --------------------------------------------------------------------- main()


def test_main_ungeschuetzter_diff_ist_gruen(tmp_path):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(dateien=["src/momentum/render.py"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 0


def test_main_geschuetzte_datei_ist_rot_mit_zonen_liste(tmp_path, capsys):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(dateien=[".github/workflows/irgendwas.yml"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1
    ausgabe = capsys.readouterr().out
    assert ".github/workflows/irgendwas.yml" in ausgabe
    assert "Entscheidung noetig" in ausgabe


def test_main_geschuetzte_konstante_in_config_ist_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path, basis="basis", kopf="kopf")
    inhalte = {
        ("basis", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.50\n",
        ("kopf", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.70\n",
    }
    laeufer = _laeufer(dateien=["src/momentum/config.py"], inhalte=inhalte)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_ungeschuetzte_konstante_in_config_ist_gruen(tmp_path):
    assert "SCHEMA_VERSION" not in CONFIG_NAMEN, "Testannahme ungueltig -- bitte andere Konstante waehlen"
    umgebung = _ereignis_datei(tmp_path, basis="basis", kopf="kopf")
    inhalte = {
        ("basis", "src/momentum/config.py"): "SCHEMA_VERSION = 2\n",
        ("kopf", "src/momentum/config.py"): "SCHEMA_VERSION = 3\n",
    }
    laeufer = _laeufer(dateien=["src/momentum/config.py"], inhalte=inhalte)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 0


def test_main_waechter_titel_mit_geschuetzter_zone_ist_rot_mit_eigenem_hinweis(tmp_path, capsys):
    umgebung = _ereignis_datei(tmp_path, titel=f"{WAECHTER_TITEL_PRAEFIX} Automatischer Fix")
    laeufer = _laeufer(dateien=[".github/workflows/irgendwas.yml"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1
    ausgabe = capsys.readouterr().out
    assert WAECHTER_TITEL_PRAEFIX in ausgabe
    assert "Agenten mergen nie" in ausgabe


def test_main_waechter_titel_ohne_geschuetzte_zone_bleibt_gruen(tmp_path):
    umgebung = _ereignis_datei(tmp_path, titel=f"{WAECHTER_TITEL_PRAEFIX} Automatischer Fix")
    laeufer = _laeufer(dateien=["src/momentum/render.py"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 0


def test_main_aenderung_am_check_selbst_ist_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(dateien=["src/momentum/schutz_sperre.py"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_dateiliste_nicht_lesbar_ist_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(fehler={"dateien"})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_ereignis_datei_fehlt_ist_rot():
    """Bewusst explizit auf eine LEERE Umgebung umgeschaltet, statt sich
    darauf zu verlassen, dass GITHUB_EVENT_PATH ambient nicht gesetzt
    ist -- in einem echten GitHub-Actions-Lauf (auch in DIESER Suite,
    wenn sie als `pull_request`-Check laeuft) ist diese Variable IMMER
    gesetzt, lokal dagegen meist nicht."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", {})
        code = main(laeufer=_laeufer())
    assert code == 1


def test_main_kaputter_quelltext_bei_geschuetzter_datei_ist_rot(tmp_path):
    """AST-Parse-Fehlschlag (z. B. ein nicht aufgeloester Merge-
    Konflikt-Marker) gilt fail-closed als VOLLE Beruehrung, nicht als
    'nicht pruefbar, also gruen'."""
    umgebung = _ereignis_datei(tmp_path, basis="basis", kopf="kopf")
    inhalte = {
        ("basis", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.5\n",
        ("kopf", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.5\n<<<<<<< HEAD\n",
    }
    laeufer = _laeufer(dateien=["src/momentum/config.py"], inhalte=inhalte)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


# ----------------------------------------------- Ziel-Mechanik (Exzellenz 1)


def test_weight_aenderung_ist_immer_rot_keine_freigabe_macht_es_gruen(tmp_path):
    """Nichts -- kein Label, kein Kommentar -- kann eine beruehrte
    geschuetzte Zone mehr gruen machen."""
    inhalte = {
        ("basis", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.50\n",
        ("kopf", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.70\n",
    }
    umgebung = _ereignis_datei(tmp_path, basis="basis", kopf="kopf")
    laeufer = _laeufer(dateien=["src/momentum/config.py"], inhalte=inhalte)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        assert main(laeufer=laeufer) == 1


# --------------------------------------------- Rueckblick unveraendert (Kriterium 3)


def test_zonen_definitionen_unveraendert_gegenueber_pr_77():
    """Belegt, dass dieser PR die geschuetzten Zonen selbst nicht
    veraendert hat -- nur die Freigabe-Pruefung wurde entfernt."""
    from momentum.schutz_sperre import GESCHUETZTE_DATEIEN, GESCHUETZTE_ORDNER

    assert "src/momentum/scoring.py" in GESCHUETZTE_DATEIEN
    assert "src/momentum/universe.py" in GESCHUETZTE_DATEIEN
    assert "src/momentum/kursvergleich.py" in GESCHUETZTE_DATEIEN
    assert ".github/workflows/" in GESCHUETZTE_ORDNER
    assert GESCHUETZTE_SYMBOLE["src/momentum/run.py"] == frozenset(
        {"process_market", "_kursvergleich", "_download_window", "main"}
    )


# -------------------------------------------------------- Melden, nie Handeln


def test_der_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu jedem anderen Waechter/
    Check dieses Projekts."""
    quelltext = Path("src/momentum/schutz_sperre.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "git commit", "git push", "git add", "gh pr", "gh issue",
        "--label", "unlabel",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"


def test_keine_label_oder_akteur_logik_mehr_vorhanden():
    """Statischer Beleg (Auftrag: 'statischer Test'), dass die Freigabe
    per Label/Akteur vollstaendig entfernt wurde, nicht nur ungenutzt
    danebenliegt. Geprueft wird der CODE, nicht der Modul-Docstring --
    der erklaert absichtlich, WAS entfernt wurde und WARUM, und darf
    deshalb die frueheren Namen in Prosa nennen (dasselbe Muster wie
    test_der_code_kann_nirgends_schreiben())."""
    quelltext = Path("src/momentum/schutz_sperre.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "FREIGABE_LABEL", "FREIGABE_AKTEUR", "freigabe-easy", "easywebb911",
        "gueltige_freigabe", "ermittle_label_ereignisse", "labeled",
        "issues/", "issues:",
    ]
    for muster in verboten:
        assert muster not in code, f"Reste der Freigabe-Logik gefunden: {muster!r}"

    import momentum.schutz_sperre as modul

    for name in ("gueltige_freigabe", "ermittle_label_ereignisse", "FREIGABE_LABEL", "FREIGABE_AKTEUR"):
        assert not hasattr(modul, name), f"{name} existiert noch im Modul"


def test_der_workflow_kann_nur_lesen_und_kennt_kein_issues_recht():
    daten = yaml.safe_load(Path(".github/workflows/schutz_sperre.yml").read_text(encoding="utf-8"))
    assert daten["permissions"] == {"contents": "read", "pull-requests": "read"}
    assert "issues" not in daten["permissions"]
    assert "write" not in yaml.dump(daten["permissions"])
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "pull_request" in ausloeser
    assert ausloeser["pull_request"]["branches"] == ["main"]
    assert "issue_comment" not in ausloeser
    for schritt in daten["jobs"]["pruefen"]["steps"]:
        assert "${{ inputs." not in schritt.get("run", "")
    text = Path(".github/workflows/schutz_sperre.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in text
    assert "freigabe-easy" not in text
