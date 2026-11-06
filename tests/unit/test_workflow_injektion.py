"""INJEKTIONS-SCHUTZ der Workflows (SESSION_HANDOVER.md §4 Punkt 14c).

Ein Wert, den jemand beim Start eines Workflows eintippt (workflow_dispatch-
Eingabe) oder der aus dem Ereignis stammt (github.event.*), darf NIE per
${{ }} im Shell-Text eines run:-Blocks stehen. GitHub setzt ${{ }} VOR dem
Start der Shell als Text ein -- ein Wert wie "2026-11-03; echo PWNED" wuerde
so zu einem zweiten Befehl. Richtig ist: Wert ueber env: uebergeben, im
Skript als Variable lesen (und wo noetig pruefen).

Bewiesen wird zweierlei:
  1. statisch, ueber ALLE Workflow-Dateien: kein ${{ inputs.* }},
     ${{ github.event.* }} oder ${{ github.head_ref }} in einem run:-Block;
  2. echt ausgefuehrt: das Analyse-Skript aus lauf.yml laeuft in bash mit
     boesartigen Eingaben -- nichts davon wird ausgefuehrt, ein ungueltiges
     Datum bricht ab, gueltige Eingaben kommen unveraendert beim Programm an.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW_DIR = Path(".github/workflows")
VERBOTEN = re.compile(r"\$\{\{[^}]*\b(inputs\.|github\.event\.|github\.head_ref)")


def _workflows() -> list[Path]:
    dateien = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    assert dateien, "keine Workflow-Dateien gefunden -- Test greift ins Leere"
    return dateien


def _run_bloecke(pfad: Path) -> list[tuple[str, str]]:
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    out = []
    for job_name, job in (daten.get("jobs") or {}).items():
        for i, schritt in enumerate(job.get("steps") or []):
            if "run" in schritt:
                out.append((f"{pfad.name}:{job_name}:{schritt.get('name', i)}", schritt["run"]))
    return out


@pytest.mark.parametrize("pfad", _workflows(), ids=lambda p: p.name)
def test_kein_ereignis_oder_eingabewert_im_shell_text(pfad):
    for wo, skript in _run_bloecke(pfad):
        treffer = VERBOTEN.findall(skript)
        assert not treffer, f"{wo}: ${{{{ ... }}}} mit {treffer} im run:-Block"


def test_das_muster_erkennt_die_alte_form_wirklich():
    """Gegenprobe: die frueher in lauf.yml stehende Zeile wird erkannt."""
    alt = "${{ inputs.datum && format('--today {0}', inputs.datum) || '' }}"
    assert VERBOTEN.search(alt)
    assert VERBOTEN.search("${{ github.event.pull_request.title }}")
    assert VERBOTEN.search("${{ github.head_ref }}")
    assert not VERBOTEN.search("${{ github.run_number }}")
    assert not VERBOTEN.search('"${EINGABE_DATUM}"')


# ---------------------------------------------------------------- echt


def _analyse_schritt() -> dict:
    daten = yaml.safe_load((WORKFLOW_DIR / "lauf.yml").read_text(encoding="utf-8"))
    treffer = [
        s for job in daten["jobs"].values() for s in job["steps"] if s.get("id") == "analyse"
    ]
    assert len(treffer) == 1
    return treffer[0]


def test_eingaben_kommen_ueber_env():
    schritt = _analyse_schritt()
    assert schritt["env"] == {
        "EINGABE_DATUM": "${{ inputs.datum }}",
        "EINGABE_OHNE_PUSH": "${{ inputs.ohne_push }}",
        "EINGABE_TESTPUSH": "${{ inputs.testpush }}",
        "EINGABE_OHNE_KURSVERGLEICH": "${{ inputs.ohne_kursvergleich }}",
    }


def _fuehre_aus(tmp_path: Path, **eingaben: str) -> tuple[int, list[str], str]:
    """Das echte run:-Skript in bash, mit einem Ersatz-`python`, der nur
    seine Argumente aufschreibt. bash -e wie bei GitHub Actions."""
    bash = shutil.which("bash")
    assert bash, "bash fehlt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argfile = tmp_path / "args.txt"
    fake = bin_dir / "python"
    fake.write_text(f'#!{bash}\nprintf "%s\\n" "$@" > "{argfile}"\n', encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    umgebung = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
        "EINGABE_DATUM": "",
        "EINGABE_OHNE_PUSH": "",
        "EINGABE_TESTPUSH": "",
        "EINGABE_OHNE_KURSVERGLEICH": "",
    }
    umgebung.update(eingaben)
    ergebnis = subprocess.run(
        [bash, "-e", "-c", _analyse_schritt()["run"]],
        env=umgebung,
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    args = argfile.read_text(encoding="utf-8").splitlines() if argfile.exists() else []
    return ergebnis.returncode, args, ergebnis.stdout + ergebnis.stderr


@pytest.mark.parametrize(
    "boese",
    [
        "2026-11-03; touch PWNED",
        "2026-11-03 && touch PWNED",
        "$(touch PWNED)",
        "`touch PWNED`",
        "2026-11-03\ntouch PWNED",
        "2026-11-03 --no-push",
        "--today 2026-11-03",
        "03.11.2026",
        "2026-1-3",
    ],
)
def test_boesartiges_datum_wird_nicht_ausgefuehrt_und_bricht_ab(tmp_path, boese):
    code, args, ausgabe = _fuehre_aus(tmp_path, EINGABE_DATUM=boese)
    assert code == 1, ausgabe
    assert not (tmp_path / "PWNED").exists(), "Eingabe wurde als Befehl ausgefuehrt"
    assert args == [], "das Programm darf gar nicht erst starten"
    assert "Ungueltiges Datum" in ausgabe
    # Der boese Wert wird nicht ins Protokoll gespiegelt (keine ::-Befehle).
    assert "PWNED" not in ausgabe


def test_planmaessiger_lauf_ohne_eingaben_ruft_wie_bisher_ohne_zusaetze(tmp_path):
    code, args, ausgabe = _fuehre_aus(tmp_path)
    assert code == 0, ausgabe
    assert args == ["-m", "momentum.run"]


def test_gueltige_eingaben_kommen_unveraendert_an(tmp_path):
    code, args, ausgabe = _fuehre_aus(
        tmp_path,
        EINGABE_DATUM="2026-11-03",
        EINGABE_OHNE_PUSH="true",
        EINGABE_TESTPUSH="true",
        EINGABE_OHNE_KURSVERGLEICH="true",
    )
    assert code == 0, ausgabe
    assert args == [
        "-m", "momentum.run", "--today", "2026-11-03",
        "--no-push", "--testpush", "--ohne-kursvergleich",
    ]


@pytest.mark.parametrize("wert", ["false", "", "TRUE", "1", "true; touch PWNED"])
def test_schalter_nur_bei_exakt_true(tmp_path, wert):
    code, args, ausgabe = _fuehre_aus(tmp_path, EINGABE_OHNE_PUSH=wert, EINGABE_TESTPUSH=wert)
    assert code == 0, ausgabe
    assert args == ["-m", "momentum.run"]
    assert not (tmp_path / "PWNED").exists()


def test_programm_fehler_wird_weitergereicht(tmp_path):
    """Bricht momentum.run ab, muss der Schritt rot werden (die Folge-
    schritte in lauf.yml haengen an success()/failure())."""
    bash = shutil.which("bash")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "python"
    fake.write_text(f"#!{bash}\nexit 2\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    ergebnis = subprocess.run(
        [bash, "-e", "-c", _analyse_schritt()["run"]],
        env={"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
             "EINGABE_DATUM": "", "EINGABE_OHNE_PUSH": "", "EINGABE_TESTPUSH": "",
             "EINGABE_OHNE_KURSVERGLEICH": ""},
        capture_output=True, text=True,
    )
    assert ergebnis.returncode == 2
