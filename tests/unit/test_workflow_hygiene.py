"""Hygiene der vier Workflow-Dateien -- gemessen, nicht behauptet.

Drei Eigenschaften, die beim Bauen leicht verrutschen und die niemandem
auffallen, solange alles gutgeht:

  1. Jeder Job hat einen Zeit-Deckel. Ohne ihn laeuft ein haengender Abruf
     bis zum GitHub-Standard von sechs Stunden weiter.
  2. Die Test-Werkzeuge sind festgenagelt -- aus demselben Grund wie die
     Datenbibliotheken. Ein unbemerkter playwright-Sprung wuerde still
     aendern, was "passt auf 390 px" ueberhaupt misst.
  3. Die Frischepruefung deckt ALLE Seiten ab, die `build_pages` erzeugt.
     Als die Konfluenz-Seite dazukam (#14), tat sie das nicht -- eine
     Aenderung an `render_konfluenz()` mit veralteter Seite waere
     durchgerutscht.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW_ORDNER = Path(".github/workflows")
ALLE = sorted(WORKFLOW_ORDNER.glob("*.yml"))
TESTS_YML = WORKFLOW_ORDNER / "tests.yml"
DEV_ANFORDERUNGEN = Path("requirements-dev.txt")


def test_es_gibt_die_erwarteten_workflows():
    assert {p.name for p in ALLE} == {
        "lauf.yml", "universum.yml", "tests.yml", "datenquelle.yml",
        # Der Totmannschalter (siehe waechter.py) -- er meldet das
        # Ausbleiben des Laufs, das kein Lauf selbst melden kann.
        "waechter.yml",
        # Der Vertragstest (siehe tools/vertragstest.py) -- er fragt im
        # Fenster vor dem Stichtag, ob die Fremdquellen noch ihre Form
        # halten.
        "vertrag.yml",
    }


@pytest.mark.parametrize("pfad", ALLE, ids=lambda p: p.name)
def test_jeder_job_hat_einen_zeitdeckel(pfad):
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    for name, job in daten["jobs"].items():
        deckel = job.get("timeout-minutes")
        assert deckel is not None, f"{pfad.name}/{name} ohne timeout-minutes"
        # Ein Deckel, der groesser ist als der GitHub-Standard, waere keiner.
        assert 1 <= deckel <= 60, f"{pfad.name}/{name}: {deckel} min ist kein Deckel"


def test_die_test_werkzeuge_sind_festgenagelt():
    zeilen = [
        z.strip()
        for z in DEV_ANFORDERUNGEN.read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.strip().startswith("#")
    ]
    assert zeilen, "requirements-dev.txt ist leer"
    for zeile in zeilen:
        assert "==" in zeile, f"nicht festgenagelt: {zeile}"
    namen = {re.split(r"[=<>!\[]", z, 1)[0].lower() for z in zeilen}
    # Genau die drei, die die Tests brauchen -- pytest, das YAML-Lesen der
    # Workflow-Tests und der Browser der 390-px-Messung.
    assert namen == {"pytest", "pyyaml", "playwright"}


def test_die_ci_installiert_nichts_ungepinntes():
    text = TESTS_YML.read_text(encoding="utf-8")
    assert "-r requirements-dev.txt" in text
    # Jede pip-install-Zeile muss aus einer Anforderungsdatei speisen; ein
    # nackter Paketname waere wieder eine unversionierte Quelle.
    for zeile in text.splitlines():
        blank = zeile.strip()
        if blank.startswith("pip install") and "--upgrade pip" not in blank:
            assert "-r " in blank, f"ungepinnte Installation: {blank}"


def test_die_frischepruefung_deckt_alle_erzeugten_seiten_ab():
    """Was `build_pages` schreibt, muss die CI auch pruefen."""
    quelle = Path("src/momentum/build_pages.py").read_text(encoding="utf-8")
    erzeugt = set(re.findall(r'DOCS_DIR / "([\w.-]+\.html)"', quelle))
    assert erzeugt, "keine erzeugten Seiten gefunden -- Muster passt nicht mehr"

    text = TESTS_YML.read_text(encoding="utf-8")
    for seite in erzeugt:
        if seite in ("index.html", "evaluation.html"):
            # Beide tragen echte Lauf-Daten (Ranking bzw. Monats-
            # Rueckblicke) und werden von build_pages nur angelegt, wenn es
            # sie noch nicht gibt. Sie duerfen und koennen hier nicht auf
            # Frische geprueft werden.
            continue
        assert f"docs/{seite}" in text, f"docs/{seite} fehlt in der Frischepruefung"
