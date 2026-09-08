"""Die duenne Orchestrierungs-Huelle (tools/agent_datumsformat_oeffnen.py)
-- OHNE echtes Git, OHNE echtes `gh`, OHNE Netz. Jeder Aufruf wird nur
AUFGEZEICHNET, nie ausgefuehrt (siehe `_aufzeichner` unten).

Geprueft wird: die Bremse (ein offener PR je Quelle, kein zweiter), die
Reihenfolge der Git-/gh-Schritte bei einem tatsaechlichen Oeffnen, UND die
harte Grenze selbst -- dass `gh pr merge` an KEINER Stelle im Quelltext
dieses Werkzeugs vorkommt.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import agent_datumsformat_oeffnen as oeffnen  # noqa: E402


def _aufzeichner(*, offene_pr_zaehler: dict[str, int] | None = None):
    """Ersetzt subprocess.run: zeichnet jeden Aufruf auf, statt ihn
    auszufuehren. `offene_pr_zaehler` steuert, was `gh pr list` je Titel
    "findet" -- ohne echtes GitHub."""
    offene_pr_zaehler = offene_pr_zaehler or {}
    aufrufe: list[list[str]] = []

    def laeufer(cmd, **kwargs):
        aufrufe.append(cmd)
        if cmd[:3] == ["gh", "pr", "list"]:
            titel_suche = cmd[cmd.index("--search") + 1]
            treffer = 0
            for titel, anzahl in offene_pr_zaehler.items():
                if f'"{titel}"' == titel_suche.split("in:title ", 1)[1]:
                    treffer = anzahl
            return SimpleNamespace(stdout=json.dumps([{}] * treffer), returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    return laeufer, aufrufe


VORSCHLAG = {
    "quelle": "iShares EXS1 (DAX)",
    "rohzeile": "2026/Aug/06",
    "datum": "2026-08-06",
    "titel": "Agent: iShares-Datumsformat iShares EXS1 (DAX)",
    "pr_text": "## Was\n...",
    "neuer_quelltext": "# neuer Inhalt von ishares.py\n",
}


def test_bereits_offener_pr_erkennt_einen_vorhandenen():
    laeufer, _ = _aufzeichner(offene_pr_zaehler={VORSCHLAG["titel"]: 1})
    assert oeffnen.bereits_offener_pr(VORSCHLAG["titel"], laeufer=laeufer) is True


def test_bereits_offener_pr_erkennt_wenn_keiner_da_ist():
    laeufer, _ = _aufzeichner()
    assert oeffnen.bereits_offener_pr(VORSCHLAG["titel"], laeufer=laeufer) is False


def test_ein_bestehender_pr_verhindert_das_erneute_oeffnen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    laeufer, aufrufe = _aufzeichner(offene_pr_zaehler={VORSCHLAG["titel"]: 1})
    pfad = tmp_path / "vorschlaege.json"
    pfad.write_text(json.dumps({"vorschlaege": [VORSCHLAG]}), encoding="utf-8")

    code = oeffnen.main([str(pfad)], laeufer=laeufer)

    assert code == 0
    # NUR `gh pr list` wurde aufgerufen -- kein `git checkout -b`, kein
    # `gh pr create`. Die Bremse hat gegriffen.
    befehle = [a[0] for a in aufrufe]
    assert befehle == ["gh"]
    assert not any(a[:2] == ["git", "checkout"] and "-b" in a for a in aufrufe)
    assert not any(a[:3] == ["gh", "pr", "create"] for a in aufrufe)


def test_ohne_bestehenden_pr_wird_ordentlich_geoeffnet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "momentum").mkdir(parents=True)
    laeufer, aufrufe = _aufzeichner()
    pfad = tmp_path / "vorschlaege.json"
    pfad.write_text(json.dumps({"vorschlaege": [VORSCHLAG]}), encoding="utf-8")

    code = oeffnen.main([str(pfad)], laeufer=laeufer)

    assert code == 0
    befehle = [a[0:2] for a in aufrufe]
    assert ["gh", "pr"] in befehle  # der list-Aufruf
    assert ["git", "checkout"] in befehle
    assert ["git", "add"] in befehle
    assert ["git", "commit"] in befehle
    assert ["git", "push"] in befehle
    # Reihenfolge: erst pruefen, dann Branch, dann committen, dann pushen,
    # dann der PR -- niemals ein `gh pr create` vor dem Push.
    namen = [" ".join(a[:3]) for a in aufrufe]
    assert namen.index("git push -u") < namen.index("gh pr create")
    assert namen.index("git checkout -b") < namen.index("git commit -m")

    # Der neue Quelltext wurde tatsaechlich geschrieben.
    assert (tmp_path / "src/momentum/ishares.py").read_text(
        encoding="utf-8"
    ) == VORSCHLAG["neuer_quelltext"]


def test_gh_pr_create_ist_immer_ein_entwurf(tmp_path, monkeypatch):
    # `oeffne_pr` schreibt src/momentum/ishares.py relativ zum Arbeits-
    # verzeichnis -- OHNE Isolierung liefe das gegen den echten Quellbaum.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "momentum").mkdir(parents=True)
    laeufer, aufrufe = _aufzeichner()
    oeffnen.oeffne_pr(VORSCHLAG, 0, laeufer=laeufer)
    erstellt = next(a for a in aufrufe if a[:3] == ["gh", "pr", "create"])
    assert "--draft" in erstellt


def test_mehrere_vorschlaege_ergeben_mehrere_zweige(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src" / "momentum").mkdir(parents=True)
    laeufer, aufrufe = _aufzeichner()
    zweiter = {**VORSCHLAG, "quelle": "iShares EXS3 (MDAX)",
               "titel": "Agent: iShares-Datumsformat iShares EXS3 (MDAX)"}
    pfad = tmp_path / "vorschlaege.json"
    pfad.write_text(
        json.dumps({"vorschlaege": [VORSCHLAG, zweiter]}), encoding="utf-8"
    )
    code = oeffnen.main([str(pfad)], laeufer=laeufer)
    assert code == 0
    zweige = {a[3] for a in aufrufe if a[:3] == ["git", "checkout", "-b"]}
    assert len(zweige) == 2, "zwei Vorschlaege muessen zwei verschiedene Zweige ergeben"


# ------------------------------------------------- Die harte Grenze selbst


def test_kein_merge_aufruf_existiert_im_quelltext():
    """Nicht nur behauptet: nachgemessen, AM CODE, nicht an der Prosa (die
    Doku darf "gh pr merge" natuerlich ERWAEHNEN, um die Grenze zu
    erklaeren -- verboten ist nur, dass der String je als tatsaechliches
    Kommandozeilen-Argument auftaucht)."""
    baum = ast.parse(Path("tools/agent_datumsformat_oeffnen.py").read_text(encoding="utf-8"))
    verbotene_worte = {"merge", "--auto", "--squash", "--merge"}
    treffer = [
        knoten.value
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Constant) and knoten.value in verbotene_worte
    ]
    assert treffer == [], f"verbotenes Argument als Code-Konstante gefunden: {treffer}"
