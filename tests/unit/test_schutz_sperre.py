"""Die Schutz-Sperre (schutz_sperre.py) — geprueft ohne echtes `gh`/Netz
(die Test-Naht `laeufer` ersetzt jeden `gh api`/`git`-Aufruf) und ohne
echte Umgebungsvariablen (`umgebung` ersetzt `os.environ` bei
`lies_ereignis`).

Kernaussagen: ein ungeschuetzter Diff ist gruen; eine geschuetzte Datei
oder eine geaenderte geschuetzte Konstante/Funktion ist rot; eine
gueltige Freigabe (Label "freigabe-easy" von easywebb911, NACH dem
letzten Push) macht ihn gruen; ein "[Wächter]"-PR-Titel bleibt trotz
Freigabe rot, sobald eine geschuetzte Zone beruehrt ist; jeder
Lesefehler (Diff, Events) macht ihn rot, nie gruen (fail-closed). Und:
MELDEN, NIE HANDELN -- dieses Modul schreibt nirgends.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from momentum.schutz_sperre import (
    FREIGABE_AKTEUR,
    FREIGABE_LABEL,
    GESCHUETZTE_SYMBOLE,
    WAECHTER_TITEL_PRAEFIX,
    ermittle_geaenderte_dateien,
    ermittle_label_ereignisse,
    gueltige_freigabe,
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


def _laeufer(*, dateien=None, ereignisse=None, inhalte=None, zeitpunkte=None, fehler=None):
    """Baut einen `laeufer`, der `gh api .../files`, `gh api .../events`,
    `git show <sha>:<pfad>` und `git show -s --format=%cI <sha>`
    bedient. `inhalte`: {(sha, pfad): text}. `zeitpunkte`: {sha: iso}.
    `fehler`: Menge der Befehlstypen ("dateien"/"ereignisse"/"show"/
    "zeitpunkt"), die stattdessen rc=1 liefern."""
    fehler = fehler or set()
    dateien = dateien if dateien is not None else []
    ereignisse = ereignisse if ereignisse is not None else []
    inhalte = inhalte or {}
    zeitpunkte = zeitpunkte or {}

    def laeufer(cmd, **kw):
        if cmd[:2] == ["gh", "api"]:
            ziel = cmd[2]
            if "/files" in ziel:
                if "dateien" in fehler:
                    return _ErgebnisAttrapp(1, stderr="HTTP 500")
                return _ErgebnisAttrapp(0, stdout=json.dumps([{"filename": d} for d in dateien]))
            if "/events" in ziel:
                if "ereignisse" in fehler:
                    return _ErgebnisAttrapp(1, stderr="HTTP 500")
                return _ErgebnisAttrapp(0, stdout=json.dumps(ereignisse))
            raise AssertionError(f"unerwarteter gh-api-Aufruf: {ziel}")
        if cmd[:2] == ["git", "show"] and len(cmd) == 3:
            if "zeigt" in fehler:
                pass
            sha, _, pfad = cmd[2].partition(":")
            if "show" in fehler:
                return _ErgebnisAttrapp(1, stderr="fatal: path does not exist")
            text = inhalte.get((sha, pfad), "")
            return _ErgebnisAttrapp(0, stdout=text)
        if cmd[:3] == ["git", "show", "-s"]:
            sha = cmd[-1]
            if "zeitpunkt" in fehler:
                return _ErgebnisAttrapp(1, stderr="fatal: bad object")
            return _ErgebnisAttrapp(0, stdout=zeitpunkte.get(sha, "2026-10-01T00:00:00+00:00") + "\n")
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


def _label_ereignis(*, akteur="easywebb911", zeit="2026-10-25T12:00:00Z", name=FREIGABE_LABEL):
    return {"event": "labeled", "label": {"name": name}, "actor": {"login": akteur}, "created_at": zeit}


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


def test_symbol_verletzungen_neu_angelegte_datei_zaehlt_als_verletzung():
    betroffen = symbol_verletzungen("x.py", "", "WEIGHT_MOMENTUM_12_1 = 0.5\n", frozenset({"WEIGHT_MOMENTUM_12_1"}))
    assert betroffen == ["WEIGHT_MOMENTUM_12_1"]


def test_symbol_verletzungen_kaputter_quelltext_ist_none():
    betroffen = symbol_verletzungen("x.py", "def f(:\n", "def f():\n    pass\n", frozenset({"f"}))
    assert betroffen is None


# --------------------------------------------------------------- gueltige_freigabe


def test_gueltige_freigabe_von_mir_nach_dem_push():
    ereignisse = [_label_ereignis(akteur="easywebb911", zeit="2026-10-25T12:00:00Z")]
    assert gueltige_freigabe(ereignisse, letzter_push_iso="2026-10-25T10:00:00+00:00") is True


def test_label_von_anderem_akteur_ist_ungueltig():
    ereignisse = [_label_ereignis(akteur="irgendjemand-sonst", zeit="2026-10-25T12:00:00Z")]
    assert gueltige_freigabe(ereignisse, letzter_push_iso="2026-10-25T10:00:00+00:00") is False


def test_label_vor_dem_letzten_push_ist_ungueltig():
    ereignisse = [_label_ereignis(akteur="easywebb911", zeit="2026-10-25T09:00:00Z")]
    assert gueltige_freigabe(ereignisse, letzter_push_iso="2026-10-25T10:00:00+00:00") is False


def test_anderer_labelname_zaehlt_nicht():
    ereignisse = [_label_ereignis(name="irgendein-anderes-label")]
    assert gueltige_freigabe(ereignisse, letzter_push_iso="2026-10-25T10:00:00+00:00") is False


def test_keine_label_ereignisse_ist_ungueltig():
    assert gueltige_freigabe([], letzter_push_iso="2026-10-25T10:00:00+00:00") is False


def test_juengstes_label_ereignis_entscheidet():
    """Ein frueheres (ungueltiges) Ereignis darf ein spaeteres gueltiges
    nicht verdecken -- und umgekehrt."""
    ereignisse = [
        _label_ereignis(akteur="jemand-anders", zeit="2026-10-25T08:00:00Z"),
        _label_ereignis(akteur="easywebb911", zeit="2026-10-25T12:00:00Z"),
    ]
    assert gueltige_freigabe(ereignisse, letzter_push_iso="2026-10-25T10:00:00+00:00") is True


# --------------------------------------------------- ermittle_geaenderte_dateien/ereignisse


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


def test_ermittle_label_ereignisse_fehlschlag_wird_gemeldet():
    laeufer = _laeufer(fehler={"ereignisse"})
    ereignisse, grund = ermittle_label_ereignisse("easywebb911/Momentum-Report", 1, laeufer=laeufer)
    assert ereignisse is None
    assert grund is not None


# --------------------------------------------------------------------- main()


def test_main_ungeschuetzter_diff_ist_gruen(tmp_path):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(dateien=["src/momentum/render.py"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 0


def test_main_geschuetzte_datei_ist_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path)
    laeufer = _laeufer(dateien=[".github/workflows/irgendwas.yml"])
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


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


def test_main_label_von_mir_macht_gruen(tmp_path):
    umgebung = _ereignis_datei(tmp_path, kopf="kopfsha")
    laeufer = _laeufer(
        dateien=[".github/workflows/irgendwas.yml"],
        ereignisse=[_label_ereignis(akteur="easywebb911", zeit="2026-10-25T12:00:00Z")],
        zeitpunkte={"kopfsha": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 0


def test_main_label_von_anderem_akteur_bleibt_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path, kopf="kopfsha")
    laeufer = _laeufer(
        dateien=[".github/workflows/irgendwas.yml"],
        ereignisse=[_label_ereignis(akteur="jemand-anders", zeit="2026-10-25T12:00:00Z")],
        zeitpunkte={"kopfsha": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_label_vor_dem_letzten_push_bleibt_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path, kopf="kopfsha")
    laeufer = _laeufer(
        dateien=[".github/workflows/irgendwas.yml"],
        ereignisse=[_label_ereignis(akteur="easywebb911", zeit="2026-10-25T08:00:00Z")],
        zeitpunkte={"kopfsha": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_waechter_titel_bleibt_rot_trotz_gueltigem_label(tmp_path):
    umgebung = _ereignis_datei(tmp_path, titel=f"{WAECHTER_TITEL_PRAEFIX} Automatischer Fix", kopf="kopfsha")
    laeufer = _laeufer(
        dateien=[".github/workflows/irgendwas.yml"],
        ereignisse=[_label_ereignis(akteur="easywebb911", zeit="2026-10-25T12:00:00Z")],
        zeitpunkte={"kopfsha": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


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


def test_main_event_abruf_scheitert_ist_rot(tmp_path):
    umgebung = _ereignis_datei(tmp_path, kopf="kopfsha")
    laeufer = _laeufer(
        dateien=[".github/workflows/irgendwas.yml"],
        fehler={"ereignisse"},
        zeitpunkte={"kopfsha": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        code = main(laeufer=laeufer)
    assert code == 1


def test_main_ereignis_datei_fehlt_ist_rot():
    """Bewusst explizit auf eine LEERE Umgebung umgeschaltet, statt sich
    darauf zu verlassen, dass GITHUB_EVENT_PATH ambient nicht gesetzt
    ist -- in einem echten GitHub-Actions-Lauf (auch in DIESER Suite,
    wenn sie als `pull_request`-Check laeuft) ist diese Variable IMMER
    gesetzt, lokal dagegen meist nicht. Ohne diese Umschaltung haengt
    das Ergebnis vom Ausfuehrungsort ab -- genau das soll dieser Test
    nicht tun."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", {})
        code = main(laeufer=_laeufer())
    assert code == 1


# ----------------------------------------------- Ziel-Mechanik (Exzellenz 1)


def test_weight_aenderung_ohne_label_ist_rot_mit_meinem_frischen_label_gruen(tmp_path):
    inhalte = {
        ("basis", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.50\n",
        ("kopf", "src/momentum/config.py"): "WEIGHT_MOMENTUM_12_1 = 0.70\n",
    }
    umgebung = _ereignis_datei(tmp_path, basis="basis", kopf="kopf")

    ohne_label = _laeufer(dateien=["src/momentum/config.py"], inhalte=inhalte, zeitpunkte={"kopf": "2026-10-25T10:00:00+00:00"})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        assert main(laeufer=ohne_label) == 1

    mit_meinem_label = _laeufer(
        dateien=["src/momentum/config.py"],
        inhalte=inhalte,
        ereignisse=[_label_ereignis(akteur=FREIGABE_AKTEUR, zeit="2026-10-25T12:00:00Z")],
        zeitpunkte={"kopf": "2026-10-25T10:00:00+00:00"},
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("os.environ", umgebung)
        assert main(laeufer=mit_meinem_label) == 0


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


def test_der_workflow_kann_nur_lesen():
    daten = yaml.safe_load(Path(".github/workflows/schutz_sperre.yml").read_text(encoding="utf-8"))
    assert daten["permissions"] == {"contents": "read", "pull-requests": "read", "issues": "read"}
    assert "write" not in yaml.dump(daten["permissions"])
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "pull_request" in ausloeser
    assert ausloeser["pull_request"]["branches"] == ["main"]
    for schritt in daten["jobs"]["pruefen"]["steps"]:
        assert "${{ inputs." not in schritt.get("run", "")
    text = Path(".github/workflows/schutz_sperre.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in text
