"""Schutz-Sperre: ein PR-Check (`on: pull_request`), der rot wird, wenn
ein PR eine geschuetzte Zone (Score/Ranking/Stichtag/Konfluenz-
Entscheidung/geschuetzte Daten/Golden-Tests/Selbstschutz) beruehrt --
Auftrag 3 der Automatisierung vom 24.10.2026, in dieser Fassung
umgestellt auf eine reine AMPEL (siehe "WARUM KEINE FREIGABE MEHR"
unten).

NAME BEWUSST UNVERAENDERT GELASSEN (Kriterium 6, Auftrag: "bei Zweifel
Namen lassen und melden"): das Modul heisst weiterhin `schutz_sperre.py`
und der Workflow weiterhin "Schutz-Sperre", obwohl es inzwischen keine
Sperre mehr im wörtlichen Sinn ist (siehe unten) -- eine Umbenennung
haette Tests, Doku-Verweise (SESSION_HANDOVER.md §7.8) und den
Closed-Set-Eintrag in `test_workflow_hygiene.py` mitgezogen, ohne dass
der Auftrag das verlangt hat. Im PR-Text ausdruecklich benannt statt
stillschweigend entschieden.

WARUM EIN CHECK, KEIN RULESET: das Ruleset "Main-Schutz" bleibt
ausdruecklich `enforcement: disabled` (siehe SESSION_HANDOVER.md §4
Punkt 14). Ein roter Check blockiert OHNE Ruleset keinen manuellen
Merge -- und WIRD es nach dieser Fassung auch nie, siehe unten.

WARUM KEINE FREIGABE MEHR, NUR NOCH EINE AMPEL: die vorherige Fassung
liess eine geschuetzte Zone per Label `freigabe-easy` (Akteur
`easywebb911`, nach dem letzten Push) wieder gruen werden. Schritt 0
einer eigenen Diagnose-Sitzung ergab: der Code dieses Repos -- und
jeder kuenftige automatisiert arbeitende Agent (Auftrag 5) -- handelt
in der GitHub-API SELBST als `easywebb911` (`gh api user`/`get_me()`
lieferten `login: "easywebb911"`; PR #77 trug `user.login` UND
`merged_by` jeweils `"easywebb911"`, obwohl ein Agent es geoeffnet
bzw. kommentiert haette). Eine Freigabe "von easywebb911" ist unter
dieser Identitaet fuer denselben Agenten, der sie prueft, trivial
faelschbar -- ein Label oder ein `/freigabe`-Kommentar waere vom
Agenten selbst setzbar, ohne dass sich das von Easys echter Entscheidung
unterscheiden liesse. ENTSCHEID (festgehalten in SESSION_HANDOVER.md):
Agenten MERGEN NIE. Sie oeffnen PRs und melden per ntfy; Easy entscheidet
und merged selbst -- wie seit PR #49 fuer den Reparatur-Agenten Stufe 3.
Eine echte technische Freigabe-Grenze braeuchte eine vom Agenten
UNTERSCHEIDBARE Identitaet (eigene GitHub-App oder ein zweites Konto) --
bewusst nicht gebaut, siehe PR-Text. Diese Sperre ist deshalb keine
Sperre mehr: sie zeigt nur noch GRUEN ("keine geschuetzte Zone beruehrt")
oder ROT ("geschuetzte Zone beruehrt, Easys Entscheidung noetig") --
rot heisst NICHT "verboten", sondern "hier bewusst hinschauen".

GESCHUETZTE ZONEN -- unveraendert gegenueber PR #77 (siehe dort fuer
Begruendung und die vier Ergaenzungen ueber die urspruengliche Vorgabe
hinaus: `universe.py`, `kursvergleich.py`/`kursvergleich_us.py`,
`ishares.py::MAX_ALTER_HANDELSTAGE`, `run.py::process_market`/
`_kursvergleich`/`_download_window`/`main`). Die vollstaendige Liste
(Pfad- und Symbol-Ebene) steht als Code unten (`GESCHUETZTE_DATEIEN`,
`GESCHUETZTE_ORDNER`, `GESCHUETZTE_SYMBOLE`) -- das ist die einzige
Quelle, nicht eine zweite, womoeglich abweichende Aufzaehlung in Prosa.

GRANULARITAET: ganze Dateien, wo eine Datei fast vollstaendig aus
geschuetzter Logik besteht (z. B. `scoring.py`) ODER wo ein AST-
Vergleich nicht sauber moeglich war; Funktions-/Konstanten-Ebene
(`GESCHUETZTE_SYMBOLE`) fuer Dateien, in denen Geschuetztes und
Ungeschuetztes gemischt vorkommt (`config.py`, `ranking.py`,
`konfluenz.py`, `ishares.py`, `run.py`).

DER AST-VERGLEICH, GENAU: fuer eine Datei in `GESCHUETZTE_SYMBOLE` wird
ihr Inhalt bei `base.sha` UND bei `head.sha` geparst (`ast.parse`); fuer
jeden geschuetzten Namen wird der Quelltext-Ausschnitt des passenden
Top-Level-Knotens (Funktion, Klasse, oder Zuweisung mit diesem Namen als
Ziel) per `ast.get_source_segment()` verglichen. Unterschiedlicher Text
(geaendert, entfernt, oder bei einer Datei, die es im PR neu gibt,
hinzugefuegt) gilt als Beruehrung. FRAGIL (Kriterium 6, hier benannt):
`ast.get_source_segment()` liefert den Quelltext INKLUSIVE Kommentaren
ueber dem Knoten, die als Teil des vorausgehenden Tokens erfasst werden
-- eine reine Kommentaraenderung ueber einer geschuetzten Konstante
wuerde deshalb faelschlich als Beruehrung gelten. Das ist eine BEWUSST
KONSERVATIVE Abweichung (ein Fehlalarm ist hier das sicherere Verhalten
als eine uebersehene Aenderung), kein Mini-Stopp-Anlass.

KANN EINE DATEI IN `GESCHUETZTE_SYMBOLE` BEI EINER SEITE NICHT GEPARST
WERDEN (Syntaxfehler, z. B. ein fehlschlagender Merge-Konflikt-Marker):
FAIL-CLOSED -- die ganze Datei gilt fuer diesen Lauf als beruehrt, nicht
als "nicht pruefbar, also gruen".

[WAECHTER]-PRS: ein PR-Titel, der mit "[Wächter]" beginnt, UND eine
geschuetzte Zone beruehrt, bleibt immer rot -- UND die Check-Ausgabe
weist zusaetzlich ausdruecklich darauf hin (eigene Log-Zeile), damit
genau dieser Fall (ein automatisiert arbeitender Agent ruehrt eine
geschuetzte Zone an) im Lauf-Protokoll nicht einfach als "eine von
vielen roten Zeilen" untergeht.

FORKS: dieses Repository ist ein privates Solo-Repository ohne externe
Mitwirkende -- ein `pull_request`-Lauf von einem Fork ist praktisch
ausgeschlossen (Kriterium 4, hier geklaert statt stillschweigend
vorausgesetzt). Deshalb genuegt der normale `pull_request`-Trigger mit
`GITHUB_TOKEN`; ein `pull_request_target`-Umweg ist hier nicht
einschlaegig, weil dieser Check keine Secrets braucht und nichts
ausfuehrt, was aus dem PR-Branch selbst stammt.

HARTE GRENZE: dieser Check MELDET nur per Exit-Code -- er schreibt
NIRGENDS (kein Label, kein Kommentar, kein Merge, keine Datei). Er
liest nicht einmal mehr Issue-/Label-Ereignisse (das war die einzige
Stelle, die je einen `issues: read`-Zugriff brauchte -- entfallen mit
der Freigabe, siehe `.github/workflows/schutz_sperre.yml`).
Abgesichert auf zwei Ebenen: das Workflow-Token traegt nur
`contents: read`, `pull-requests: read` UND ein statischer Test
(tests/unit/test_schutz_sperre.py) durchsucht diese Datei nach jedem
schreibenden Aufruf UND bestaetigt, dass keine Label-/Akteur-Logik mehr
existiert.

DETERMINISMUS (Kriterium 7): `main()` braucht ÜBERHAUPT KEINEN
Zeitbezug mehr (die vorherige Fassung brauchte den Commit-Zeitpunkt des
Kopf-SHA fuer die Freigabe-Pruefung -- das entfaellt vollstaendig).
Das Ergebnis ist eine reine Funktion von PR-Titel und Diff (Basis-/
Kopf-SHA): derselbe Diff ergibt immer dasselbe Ergebnis.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path

WAECHTER_TITEL_PRAEFIX = "[Wächter]"

# Grosszuegige Obergrenze je API-Abruf -- eine einzelne Seite reicht
# fuer jeden realistischen PR dieses Solo-Repositories bei weitem.
# FRAGIL, hier benannt: ein PR mit mehr als so vielen geaenderten
# Dateien wuerde Treffer jenseits der Grenze nicht mehr sehen.
DATEI_LISTEN_LIMIT = 300

# --------------------------------------------------- Geschuetzte Zonen

# Ganze Datei geschuetzt -- jede Aenderung an diesem Pfad ist eine
# Beruehrung. Begruendung je Eintrag: siehe Modul-Docstring und PR #77.
GESCHUETZTE_DATEIEN: frozenset[str] = frozenset(
    {
        "src/momentum/scoring.py",
        "src/momentum/evaluation.py",
        "src/momentum/universe.py",
        "src/momentum/kursvergleich.py",
        "src/momentum/kursvergleich_us.py",
        "data/konfluenz_historie.json",
        "tests/unit/test_freeze.py",
        "tests/unit/test_scoring_values.py",
        "tests/unit/test_konfluenz_python.py",
        "src/momentum/schutz_sperre.py",
        "tests/unit/test_schutz_sperre.py",
    }
)

# Ganze Ordner geschuetzt -- jeder Pfad, der mit einem dieser Praefixe
# beginnt, ist eine Beruehrung (Daten-Verzeichnisse mit wachsendem
# Inhalt, plus jede einzelne Workflow-Datei als Selbstschutz).
GESCHUETZTE_ORDNER: tuple[str, ...] = (
    "data/rankings/",
    "data/evaluation/",
    ".github/workflows/",
)

# Nur diese Top-Level-Namen sind in der jeweiligen Datei geschuetzt --
# der Rest der Datei darf sich frei aendern.
GESCHUETZTE_SYMBOLE: dict[str, frozenset[str]] = {
    "src/momentum/config.py": frozenset(
        {
            "WEIGHT_MOMENTUM_12_1",
            "WEIGHT_HIGH_52W",
            "SCORE_SCALE",
            "MOMENTUM_LOOKBACK_MONTHS",
            "MOMENTUM_SKIP_MONTHS",
            "HIGH_52W_WINDOW_DAYS",
            "LIQUIDITY_MIN_MEDIAN_TURNOVER",
            "LIQUIDITY_WINDOW_MONTHS",
            "MIN_UNIVERSE_COVERAGE",
            "TOP_N",
            "HISTORY_DAYS",
            "Market",
            "MARKETS",
            "_check_weights_are_backed",
        }
    ),
    "src/momentum/ranking.py": frozenset(
        {
            "is_last_weekday_of_month",
            "due_months",
            "resolve_asof",
            "_juengster_werktag",
            "zu_frueh_fuer_stichtag",
            "median_turnover",
            "build_ranking",
        }
    ),
    "src/momentum/konfluenz.py": frozenset(
        {"elliott_long", "konfluenz", "neue_konfluenz_treffer"}
    ),
    "src/momentum/ishares.py": frozenset({"MAX_ALTER_HANDELSTAGE"}),
    "src/momentum/run.py": frozenset(
        {"process_market", "_kursvergleich", "_download_window", "main"}
    ),
}


def log(text: str) -> None:
    print(text, flush=True)


def ist_voll_geschuetzter_pfad(pfad: str) -> bool:
    if pfad in GESCHUETZTE_DATEIEN:
        return True
    return any(pfad.startswith(ordner) for ordner in GESCHUETZTE_ORDNER)


# --------------------------------------------------------- Ereignis/Diff lesen


def lies_ereignis(*, umgebung: dict | None = None) -> tuple[dict | None, str | None]:
    """Das `pull_request`-Webhook-Ereignis aus `GITHUB_EVENT_PATH`.
    Genau einer der beiden Rueckgabewerte ist None."""
    umgebung = umgebung if umgebung is not None else os.environ
    pfad = umgebung.get("GITHUB_EVENT_PATH")
    if not pfad:
        return None, "GITHUB_EVENT_PATH ist nicht gesetzt."
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"{pfad} nicht lesbar ({type(exc).__name__}: {exc})."
    except json.JSONDecodeError as exc:
        return None, f"{pfad} enthaelt kein gueltiges JSON ({exc})."
    pr = daten.get("pull_request")
    if not isinstance(pr, dict):
        return None, "Ereignis enthaelt kein 'pull_request'-Feld."
    for feld in ("number", "title", "base", "head"):
        if feld not in pr:
            return None, f"pull_request-Feld {feld!r} fehlt im Ereignis."
    return pr, None


def _gh_api(pfad: str, *, laeufer=subprocess.run) -> tuple[object | None, str | None]:
    try:
        ergebnis = laeufer(["gh", "api", pfad], capture_output=True, text=True)
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, f"gh api {pfad} endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
    try:
        return json.loads(ergebnis.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh api {pfad} lieferte kein gueltiges JSON ({exc})."


def ermittle_geaenderte_dateien(
    repo: str, nummer: int, *, laeufer=subprocess.run, limit: int = DATEI_LISTEN_LIMIT
) -> tuple[list[str] | None, str | None]:
    daten, grund = _gh_api(
        f"repos/{repo}/pulls/{nummer}/files?per_page={limit}", laeufer=laeufer
    )
    if grund is not None:
        return None, grund
    if not isinstance(daten, list):
        return None, "Antwort auf .../files war keine Liste."
    try:
        return [eintrag["filename"] for eintrag in daten], None
    except (KeyError, TypeError) as exc:
        return None, f"ein Eintrag der Datei-Liste hat kein 'filename'-Feld ({exc})."


def _git_show(commit: str, pfad: str, *, laeufer=subprocess.run) -> tuple[str | None, str | None]:
    try:
        ergebnis = laeufer(["git", "show", f"{commit}:{pfad}"], capture_output=True, text=True)
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        # Existiert die Datei bei diesem Commit nicht (neu angelegt bzw.
        # geloescht), ist das KEIN technischer Fehlschlag -- leerer Text.
        return "", None
    return ergebnis.stdout, None


# ------------------------------------------------------------- AST-Vergleich


def _top_level_quelltexte(quelltext: str) -> dict[str, str]:
    """Name -> Quelltext-Ausschnitt je Top-Level-Funktion/Klasse/
    Zuweisung. Wirft SyntaxError bei kaputtem Quelltext -- vom Aufrufer
    fail-closed behandelt, nie stillschweigend uebergangen."""
    baum = ast.parse(quelltext)
    ergebnis: dict[str, str] = {}
    for knoten in baum.body:
        quelle = ast.get_source_segment(quelltext, knoten) or ""
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ergebnis[knoten.name] = quelle
        elif isinstance(knoten, ast.Assign):
            for ziel in knoten.targets:
                if isinstance(ziel, ast.Name):
                    ergebnis[ziel.id] = quelle
        elif isinstance(knoten, ast.AnnAssign) and isinstance(knoten.target, ast.Name):
            ergebnis[knoten.target.id] = quelle
    return ergebnis


def symbol_verletzungen(
    pfad: str, basis_text: str, kopf_text: str, namen: frozenset[str]
) -> list[str] | None:
    """Liste geaenderter geschuetzter Namen, oder None bei einem
    Parse-Fehler (vom Aufrufer als fail-closed zu behandeln)."""
    try:
        basis_map = _top_level_quelltexte(basis_text) if basis_text else {}
        kopf_map = _top_level_quelltexte(kopf_text) if kopf_text else {}
    except SyntaxError:
        return None
    verletzt = []
    for name in sorted(namen):
        if basis_map.get(name) != kopf_map.get(name):
            verletzt.append(name)
    return verletzt


# -------------------------------------------------------------------- main()


def main(argv: list[str] | None = None, *, laeufer=subprocess.run) -> int:
    pr, grund = lies_ereignis()
    if grund is not None:
        log(f"Schutz-Sperre: ROT (fail-closed) — Ereignis nicht lesbar: {grund}")
        return 1

    nummer = pr["number"]
    titel = pr.get("title") or ""
    basis_sha = pr["base"]["sha"]
    kopf_sha = pr["head"]["sha"]
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        log("Schutz-Sperre: ROT (fail-closed) — GITHUB_REPOSITORY ist nicht gesetzt.")
        return 1

    dateien, grund = ermittle_geaenderte_dateien(repo, nummer, laeufer=laeufer)
    if grund is not None:
        log(f"Schutz-Sperre: ROT (fail-closed) — Diff nicht lesbar: {grund}")
        return 1

    beruehrungen: list[str] = []
    for pfad in dateien:
        if ist_voll_geschuetzter_pfad(pfad):
            beruehrungen.append(f"{pfad} (ganze Datei geschuetzt)")
            continue
        namen = GESCHUETZTE_SYMBOLE.get(pfad)
        if namen is None:
            continue
        basis_text, grund = _git_show(basis_sha, pfad, laeufer=laeufer)
        if grund is not None:
            log(f"Schutz-Sperre: ROT (fail-closed) — {pfad} bei {basis_sha[:8]}: {grund}")
            return 1
        kopf_text, grund = _git_show(kopf_sha, pfad, laeufer=laeufer)
        if grund is not None:
            log(f"Schutz-Sperre: ROT (fail-closed) — {pfad} bei {kopf_sha[:8]}: {grund}")
            return 1
        betroffene = symbol_verletzungen(pfad, basis_text, kopf_text, namen)
        if betroffene is None:
            log(f"Schutz-Sperre: ROT (fail-closed) — {pfad} liess sich nicht parsen.")
            return 1
        if betroffene:
            beruehrungen.append(f"{pfad}: {', '.join(betroffene)}")

    if not beruehrungen:
        log("Schutz-Sperre: keine geschuetzte Zone beruehrt — gruen.")
        return 0

    log("Schutz-Sperre: geschuetzte Zone(n) beruehrt — Easys Entscheidung noetig:")
    for zeile in beruehrungen:
        log(f"  - {zeile}")

    if titel.strip().startswith(WAECHTER_TITEL_PRAEFIX):
        log(
            f"Schutz-Sperre: Hinweis — PR-Titel beginnt mit {WAECHTER_TITEL_PRAEFIX!r} "
            "UND beruehrt eine geschuetzte Zone. Agenten mergen nie; dieser PR "
            "braucht wie jeder andere Easys bewusste Entscheidung."
        )

    log("Schutz-Sperre: ROT — nicht verboten, nur eine Entscheidung wert.")
    return 1


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
