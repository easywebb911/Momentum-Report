"""Die Push-Schleifen der Workflows — als Verhalten geprueft, nicht behauptet.

Workflow-YAML laesst sich nicht als Ganzes testen. Das entscheidende Stueck
aber schon: die Fallunterscheidung, ob ein fehlgeschlagener Push einen
zweiten Versuch verdient. Sie wird hier aus der Datei geholt und mit echten
git-Fehlermeldungen gegen bash laufen gelassen.

Hintergrund: Der Universum-Lauf vom 02.08.2026 hat einen Regelverstoss
(GH013) fuenfmal mit Backoff wiederholt. Eine Schutzregel lehnt aber IMMER
ab -- das Warten war verlorene Zeit, und die fuenf identischen Fehlerbloecke
haben im Protokoll den eigentlichen Befund nach oben aus dem Blick geschoben.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = {
    "lauf": Path(".github/workflows/lauf.yml"),
    "universum": Path(".github/workflows/universum.yml"),
}

# Echte Ausgaben, so wie git sie liefert.
ABLEHNUNG_SCHUTZREGEL = """\
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
remote: - Required status check "tests" is expected.
 ! [remote rejected] HEAD -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/easywebb911/Momentum-Report'"""

ABLEHNUNG_GESCHUETZTER_ZWEIG = """\
remote: error: GH006: Protected branch update failed for refs/heads/main.
 ! [remote rejected] HEAD -> main (protected branch hook declined)"""

ECHTER_KONFLIKT = """\
 ! [rejected]        HEAD -> main (non-fast-forward)
error: failed to push some refs to 'https://github.com/easywebb911/Momentum-Report'
hint: Updates were rejected because the tip of your current branch is behind"""

NETZFEHLER = """\
fatal: unable to access 'https://github.com/...': Could not resolve host: github.com"""


def _push_schritt(name: str) -> str:
    """Das Skript des Schrittes holen, der zurueckschreibt."""
    daten = yaml.safe_load(WORKFLOWS[name].read_text(encoding="utf-8"))
    for job in daten["jobs"].values():
        for schritt in job["steps"]:
            if "run" in schritt and "git push origin" in schritt["run"]:
                return schritt["run"]
    raise AssertionError(f"{name}: kein Schritt mit git push gefunden")


def _case_muster(skript: str) -> str:
    """Die Musterzeile der Fallunterscheidung aus dem Skript schneiden."""
    treffer = re.search(r"^\s*(\*GH013\*\|[^)]*)\)", skript, re.MULTILINE)
    assert treffer, "Fallunterscheidung fuer Schutzregeln nicht gefunden"
    return treffer.group(1)


def _greift(muster: str, ausgabe: str) -> bool:
    """Die Fallunterscheidung im echten bash auswerten."""
    skript = f'''
case "$AUSGABE" in
  {muster}) echo SOFORT ;;
  *) echo WEITER ;;
esac
'''
    ergebnis = subprocess.run(
        ["bash", "-c", skript],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "AUSGABE": ausgabe},
    )
    return ergebnis.stdout.strip() == "SOFORT"


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS))
@pytest.mark.parametrize(
    "beschreibung,ausgabe,sofort_abbrechen",
    [
        ("Schutzregel GH013", ABLEHNUNG_SCHUTZREGEL, True),
        ("geschuetzter Zweig GH006", ABLEHNUNG_GESCHUETZTER_ZWEIG, True),
        ("echter Konflikt", ECHTER_KONFLIKT, False),
        ("Netzfehler", NETZFEHLER, False),
    ],
)
def test_nur_aussichtslose_faelle_brechen_sofort_ab(
    workflow, beschreibung, ausgabe, sofort_abbrechen
):
    """Regelverstoss -> sofort raus. Konflikt und Netzfehler -> wiederholen."""
    muster = _case_muster(_push_schritt(workflow))
    assert _greift(muster, ausgabe) is sofort_abbrechen, beschreibung


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS))
def test_vor_jedem_versuch_wird_ein_haengender_rebase_abgeraeumt(workflow):
    """Anforderung aus dem Auftrag: rebase --abort vor jedem Wiederholversuch."""
    skript = _push_schritt(workflow)
    rumpf = skript.split("for ", 1)[1].split("\n")[1:]
    wirksam = [
        z.strip() for z in rumpf if z.strip() and not z.strip().startswith("#")
    ]
    assert wirksam, "Schleifenrumpf ist leer"
    assert "git rebase --abort" in wirksam[0], (
        f"erste Anweisung der Schleife ist {wirksam[0]!r}, "
        f"erwartet wurde das Aufraeumen eines haengenden Rebase"
    )
    # ... und zwar leise: die Meldung "no rebase in progress" ist der
    # Normalfall und hat im Protokoll nichts verloren.
    for zeile in skript.splitlines():
        if "git rebase --abort" in zeile:
            assert ">/dev/null 2>&1" in zeile, f"laute rebase-Zeile: {zeile.strip()}"


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS))
def test_geschrieben_wird_nur_auf_main(workflow):
    daten = yaml.safe_load(WORKFLOWS[workflow].read_text(encoding="utf-8"))
    for job in daten["jobs"].values():
        for schritt in job["steps"]:
            if "run" in schritt and "git push origin" in schritt["run"]:
                assert "github.ref_name == 'main'" in str(schritt.get("if", "")), (
                    f"{workflow}: der Schreib-Schritt ist nicht auf main begrenzt"
                )


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS))
def test_die_meldung_nennt_den_weg_zur_abhilfe(workflow):
    """Eine Fehlermeldung ohne Handlungsanweisung ist nur halb so viel wert."""
    skript = _push_schritt(workflow)
    assert "Bypass list" in skript
    assert "Schutzregel" in skript
    assert "Kein Wiederholen" in skript or "Wiederholen aendert daran nichts" in skript


def test_der_taegliche_lauf_wuergt_sich_nicht_selbst_ab():
    """concurrency wie beauftragt: nicht parallel, aber auch nicht abbrechen."""
    daten = yaml.safe_load(WORKFLOWS["lauf"].read_text(encoding="utf-8"))
    assert daten["concurrency"]["group"] == "daily-momentum"
    assert daten["concurrency"]["cancel-in-progress"] is False


def test_checkout_folgt_dem_zweignamen_nicht_dem_eingefrorenen_sha():
    for name, pfad in WORKFLOWS.items():
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        for job in daten["jobs"].values():
            for schritt in job["steps"]:
                if str(schritt.get("uses", "")).startswith("actions/checkout"):
                    assert schritt["with"]["ref"] == "${{ github.ref_name }}", name


# --------------------------------------------------------------------------
# VERDRAHTUNGSPROBE — das Eingabefeld am Workflow
# --------------------------------------------------------------------------


def _lauf_yaml() -> dict:
    return yaml.safe_load(WORKFLOWS["lauf"].read_text(encoding="utf-8"))


def test_der_lauf_hat_ein_feld_fuer_die_verdrahtungsprobe():
    daten = _lauf_yaml()
    # PyYAML liest das YAML-Schluesselwort "on" als True.
    ausloeser = daten.get("on", daten.get(True))
    felder = ausloeser["workflow_dispatch"]["inputs"]
    assert "testpush" in felder, "das Eingabefeld fehlt"
    probe = felder["testpush"]
    assert probe["type"] == "boolean"
    assert probe["default"] is False, "die Probe ist standardmaessig AUS"
    assert probe["required"] is False


def test_der_schalter_erreicht_das_programm():
    """Ohne diese Verdrahtung waere das Feld ein Knopf ohne Draht."""
    daten = _lauf_yaml()
    analyse = [
        schritt
        for job in daten["jobs"].values()
        for schritt in job["steps"]
        if schritt.get("id") == "analyse"
    ]
    assert len(analyse) == 1
    skript = analyse[0]["run"]
    assert "inputs.testpush" in skript
    assert "--testpush" in skript
    # Der normale Lauf bleibt unangetastet: die Probe kommt ZUSAETZLICH.
    assert "python -m momentum.run" in skript
    assert "--no-push" in skript
