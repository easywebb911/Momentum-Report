"""Schutz-Sperre: ein PR-Check (`on: pull_request`), der rot wird, wenn
ein PR eine geschuetzte Zone (Score/Ranking/Stichtag/Konfluenz-
Entscheidung/Geschuetzte Daten/Golden-Tests/Selbstschutz) beruehrt --
Auftrag 3 der Automatisierung vom 24.10.2026.

WARUM EIN CHECK, KEIN RULESET: das Ruleset "Main-Schutz" bleibt
ausdruecklich `enforcement: disabled` (blockierte Bot-Direktpushes,
Bypass "GitHub Actions" am iPhone nicht einrichtbar -- siehe
SESSION_HANDOVER.md §4 Punkt 14). Dieser Check ersetzt das NICHT -- ein
roter Check blockiert OHNE Ruleset keinen manuellen Merge. Er wird erst
zur harten Grenze, wenn ein kuenftiger Merge-Workflow (Auftrag 5) ihn vor
dem Mergen abfragt. Dieser Auftrag baut NUR den Check.

DIESER AUFTRAG BAUT NUR DEN CHECK, KEINEN MERGE-WORKFLOW -- bewusst so
im Auftrag festgehalten, hier wiederholt, damit niemand aus der
Existenz dieses Moduls faelschlich auf eine bereits wirksame Sperre
schliesst.

GESCHUETZTE ZONEN -- per grep bestaetigt UND ueber die urspruengliche
Vorgabe hinaus VERVOLLSTAENDIGT (Auftrag: "vollstaendig machen"; Kriterium
2, Widerspruch gemeldet statt still uebergangen). Die vollstaendige
Liste mit Begruendung steht im PR-Text; hier nur die VIER Ergaenzungen,
die ueber die woertliche Vorgabe hinausgehen:

  1. `universe.py` (GANZE DATEI) -- `load_universe()` ist das DEFAULT-
     DENY-Gatter ("# STATUS: VERIFIED"), in SESSION_HANDOVER.md §8
     wiederholt als "Kronjuwel" bezeichnet. Von der urspruenglichen Zonen-
     Liste nicht genannt, aber ersichtlich derselben Kategorie wie die
     dort genannte Stichtag-Logik: OHNE dieses Gatter wird ueberhaupt
     erst gerechnet.
  2. `kursvergleich.py`/`kursvergleich_us.py` (JE GANZE DATEI) -- deren
     `vergleiche()`/`Vergleich.verweigert` kann `run.py` per
     `RankingNotPossible` zum Abbruch VOR dem Schreiben eines Rankings
     zwingen (siehe `run.py::_kursvergleich`) -- dieselbe Kategorie wie
     die explizit genannte Konfluenz-Entscheidung, nur folgenreicher
     (Konfluenz aendert nichts am Ranking selbst, dieses Gatter kann es
     verhindern).
  3. `ishares.py::MAX_ALTER_HANDELSTAGE` (EINE Konstante, nicht die
     ganze Datei -- der Rest von `ishares.py` ist HTTP-Abruf/Parsing,
     keine Entscheidungslogik) -- die Veraltungs-Schwelle, die
     `kursvergleich.py`/`kursvergleich_us.py` beim Pruefen der iShares-
     Bestandsliste verwenden.
  4. `run.py::process_market`/`_kursvergleich`/`_download_window`/`main`
     -- NICHT die ganze Datei (grosse Teile sind Push-Verdrahtung/CLI,
     keine Entscheidungslogik), aber GENAU diese vier: `process_market`
     ist die Funktion, die `build_ranking`, das Vergleichsgatter und das
     Schreiben der Ranking-Datei je Markt ueberhaupt erst zusammenruft
     -- real belegt durch PR #70 (Split-Waechter-Einhaengung): eine
     scheinbar harmlose, tatsaechlich schon gemergte zwei-Zeilen-
     Ergaenzung MITTEN in `process_market` waere ohne diese Ergaenzung
     an diesem Check spurlos vorbeigelaufen (siehe Rueckblick-Tabelle im
     PR-Text, #70). `_download_window` bestimmt den Kurs-Abrufzeitraum
     (dieselbe Kategorie wie `HISTORY_DAYS`), `main` ist die
     Orchestrierung, die alle Schritte in der richtigen Reihenfolge
     aufruft.

DIE VOLLSTAENDIGE LISTE (Pfad- und Symbol-Ebene) steht als Code unten
(`GESCHUETZTE_DATEIEN`, `GESCHUETZTE_ORDNER`, `GESCHUETZTE_SYMBOLE`) --
das ist die einzige Quelle, nicht eine zweite, womoeglich abweichende
Aufzaehlung irgendwo in Prosa.

GRANULARITAET: ganze Dateien, wo eine Datei fast vollstaendig aus
geschuetzter Logik besteht (z. B. `scoring.py`) ODER wo ein AST-
Vergleich nicht sauber moeglich war; Funktions-/Konstanten-Ebene
(`GESCHUETZTE_SYMBOLE`) fuer Dateien, in denen Geschuetztes und
Ungeschuetztes gemischt vorkommt (`config.py`, `ranking.py`,
`konfluenz.py`, `ishares.py`).

DER AST-VERGLEICH, GENAU: fuer eine Datei in `GESCHUETZTE_SYMBOLE` wird
ihr Inhalt bei `base.sha` UND bei `head.sha` geparst (`ast.parse`); fuer
jeden geschuetzten Namen wird der Quelltext-Ausschnitt des passenden
Top-Level-Knotens (Funktion, Klasse, oder Zuweisung mit diesem Namen als
Ziel) per `ast.get_source_segment()` verglichen. Unterschiedlicher Text
(geaendert, entfernt, oder bei einer Datei, die es im PR neu gibt,
hinzugefuegt) gilt als Verletzung. FRAGIL (Kriterium 6, hier benannt):
`ast.get_source_segment()` liefert den Quelltext INKLUSIVE Kommentaren
ueber dem Knoten, die als Teil des vorausgehenden Tokens erfasst werden
-- eine reine Kommentaraenderung ueber einer geschuetzten Konstante
wuerde deshalb faelschlich als Verletzung gelten. Das ist eine BEWUSST
KONSERVATIVE Abweichung (ein Fehlalarm ist hier das sicherere Verhalten
als eine uebersehene Aenderung), kein Mini-Stopp-Anlass.

KANN EINE DATEI IN `GESCHUETZTE_SYMBOLE` BEI EINER SEITE NICHT GEPARST
WERDEN (Syntaxfehler, z. B. ein fehlschlagender Merge-Konflikt-Marker):
FAIL-CLOSED -- die ganze Datei gilt fuer diesen Lauf als verletzt, nicht
als "nicht pruefbar, also gruen".

DIE FREIGABE, GENAU (Regel 3): `gh api repos/{repo}/issues/{nummer}/
events` liefert je Ereignis u. a. `{"event": "labeled", "label":
{"name": ...}, "actor": {"login": ...}, "created_at": "..."}` (von
dieser Sitzung GEGENGEPRUEFT, nicht nur angenommen -- siehe PR-Text).
Gueltig ist eine Freigabe nur, wenn das JUENGSTE solche Ereignis mit
`label.name == "freigabe-easy"` einen Akteur `login == "easywebb911"`
traegt UND sein `created_at` NACH dem Commit-Zeitpunkt (`%cI`) von
`head.sha` liegt (siehe `main()`). FRAGIL (Kriterium 6): der Commit-
Zeitpunkt des Head-SHA dient hier als Stellvertreter fuer "letzter
Push" -- bei einem Force-Push auf einen AELTEREN Commit waere das kein
verlaessliches Signal mehr; in diesem Solo-Repository ohne Force-Push-
Gewohnheit (siehe SESSION_HANDOVER.md) eine vertretbare Annahme, hier
ausdruecklich benannt statt stillschweigend vorausgesetzt.

[WAECHTER]-PRS (Regel 4): ein PR-Titel, der mit "[Wächter]" beginnt,
wird bei Beruehrung einer geschuetzten Zone IMMER rot -- auch mit
gueltiger Freigabe. Das deckt den Fall ab, dass ein kuenftiger,
automatisiert arbeitender Agent (Auftrag 5) selbst einen solchen Titel
traegt und NIE durch eine geschuetzte Zone soll, unabhaengig davon, ob
irgendwo ein Label sitzt.

FORKS: dieses Repository ist ein privates Solo-Repository ohne externe
Mitwirkende -- ein `pull_request`-Lauf von einem Fork ist praktisch
ausgeschlossen (Kriterium 4, hier geklaert statt stillschweigend
vorausgesetzt). Deshalb genuegt der normale `pull_request`-Trigger mit
`GITHUB_TOKEN`; ein `pull_request_target`-Umweg (fuer Secrets gegenueber
nicht vertrauenswuerdigem Fork-Code) ist hier nicht einschlaegig, weil
dieser Check keine Secrets braucht und nichts ausfuehrt, was aus dem
PR-Branch selbst stammt (nur lesen, nie `checkout` des Fork-Codes
AUSFUEHREN).

HARTE GRENZE: dieser Check MELDET nur per Exit-Code -- er schreibt
NIRGENDS (kein Label, kein Kommentar, kein Merge, keine Datei).
Abgesichert auf zwei Ebenen: das Workflow-Token traegt nur
`contents: read`, `pull-requests: read`, `issues: read` UND ein
statischer Test (tests/unit/test_schutz_sperre.py) durchsucht diese
Datei nach jedem schreibenden Aufruf.

DETERMINISMUS (Kriterium 7): `main()` nimmt KEINE eigene Uhrzeit --
`jetzt_iso` kommt ausschliesslich aus dem Commit-Zeitpunkt von
`head.sha` (siehe oben), kein `datetime.now()` irgendwo in der
Entscheidungslogik. Derselbe Diff und dieselben Ereignisse ergeben
immer dasselbe Ergebnis.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path

WAECHTER_TITEL_PRAEFIX = "[Wächter]"
FREIGABE_LABEL = "freigabe-easy"
FREIGABE_AKTEUR = "easywebb911"

# Grosszuegige Obergrenzen je API-Abruf -- eine einzelne Seite reicht
# fuer jeden realistischen PR dieses Solo-Repositories bei weitem.
# FRAGIL, hier benannt: ein PR mit mehr als so vielen geaenderten
# Dateien bzw. Label-Ereignissen wuerde Treffer jenseits der Grenze
# nicht mehr sehen.
DATEI_LISTEN_LIMIT = 300
EREIGNIS_LISTEN_LIMIT = 100

# --------------------------------------------------- Geschuetzte Zonen

# Ganze Datei geschuetzt -- jede Aenderung an diesem Pfad ist eine
# Verletzung. Begruendung je Eintrag: siehe Modul-Docstring und PR-Text.
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
# beginnt, ist eine Verletzung (Daten-Verzeichnisse mit wachsendem
# Inhalt, plus jede einzelne Workflow-Datei als Selbstschutz).
GESCHUETZTE_ORDNER: tuple[str, ...] = (
    "data/rankings/",
    "data/evaluation/",
    ".github/workflows/",
)

# Nur diese Top-Level-Namen sind in der jeweiligen Datei geschuetzt --
# der Rest der Datei darf sich frei aendern. Siehe Modul-Docstring fuer
# die drei Ergaenzungen ueber die urspruengliche Vorgabe hinaus.
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


def ermittle_label_ereignisse(
    repo: str, nummer: int, *, laeufer=subprocess.run, limit: int = EREIGNIS_LISTEN_LIMIT
) -> tuple[list[dict] | None, str | None]:
    daten, grund = _gh_api(
        f"repos/{repo}/issues/{nummer}/events?per_page={limit}", laeufer=laeufer
    )
    if grund is not None:
        return None, grund
    if not isinstance(daten, list):
        return None, "Antwort auf .../events war keine Liste."
    return daten, None


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


def _commit_zeitpunkt(commit: str, *, laeufer=subprocess.run) -> tuple[str | None, str | None]:
    try:
        ergebnis = laeufer(
            ["git", "show", "-s", "--format=%cI", commit], capture_output=True, text=True
        )
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, f"git show -s {commit} endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
    zeile = ergebnis.stdout.strip()
    if not zeile:
        return None, f"git show -s {commit} lieferte keinen Zeitstempel."
    return zeile, None


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


# --------------------------------------------------------------- Freigabe


def gueltige_freigabe(
    ereignisse: list[dict], *, letzter_push_iso: str
) -> bool:
    """True, wenn das JUENGSTE 'labeled'-Ereignis fuer FREIGABE_LABEL
    von FREIGABE_AKTEUR stammt UND NACH `letzter_push_iso` liegt."""
    treffer = [
        e
        for e in ereignisse
        if e.get("event") == "labeled"
        and isinstance(e.get("label"), dict)
        and e["label"].get("name") == FREIGABE_LABEL
    ]
    if not treffer:
        return False
    juengstes = max(treffer, key=lambda e: e.get("created_at") or "")
    akteur = (juengstes.get("actor") or {}).get("login")
    if akteur != FREIGABE_AKTEUR:
        return False
    zeitpunkt = juengstes.get("created_at")
    if not zeitpunkt:
        return False
    return zeitpunkt > letzter_push_iso


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

    verletzungen: list[str] = []
    for pfad in dateien:
        if ist_voll_geschuetzter_pfad(pfad):
            verletzungen.append(f"{pfad} (ganze Datei geschuetzt)")
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
            verletzungen.append(f"{pfad}: {', '.join(betroffene)}")

    if not verletzungen:
        log("Schutz-Sperre: keine geschuetzte Zone beruehrt — gruen.")
        return 0

    log("Schutz-Sperre: geschuetzte Zone(n) beruehrt:")
    for zeile in verletzungen:
        log(f"  - {zeile}")

    if titel.strip().startswith(WAECHTER_TITEL_PRAEFIX):
        log(
            f"Schutz-Sperre: ROT — PR-Titel beginnt mit {WAECHTER_TITEL_PRAEFIX!r}, "
            "das gilt IMMER, auch mit Label (Regel 4)."
        )
        return 1

    letzter_push_iso, grund = _commit_zeitpunkt(kopf_sha, laeufer=laeufer)
    if grund is not None:
        log(f"Schutz-Sperre: ROT (fail-closed) — Push-Zeitpunkt nicht ermittelbar: {grund}")
        return 1

    ereignisse, grund = ermittle_label_ereignisse(repo, nummer, laeufer=laeufer)
    if grund is not None:
        log(f"Schutz-Sperre: ROT (fail-closed) — Label-Ereignisse nicht lesbar: {grund}")
        return 1

    if gueltige_freigabe(ereignisse, letzter_push_iso=letzter_push_iso):
        log(
            f"Schutz-Sperre: GRUEN — gueltige Freigabe ({FREIGABE_LABEL!r} von "
            f"{FREIGABE_AKTEUR!r}, nach dem letzten Push {letzter_push_iso})."
        )
        return 0

    log(
        f"Schutz-Sperre: ROT — keine gueltige Freigabe (Label {FREIGABE_LABEL!r} von "
        f"{FREIGABE_AKTEUR!r}, NACH dem letzten Push {letzter_push_iso})."
    )
    return 1


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
