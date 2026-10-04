"""Push-Zustellungs-Wächter: fehlgeschlagene ntfy-Versandversuche, die
sich sonst nie von selbst zeigen.

NEU AUFGESETZT (Option 2 nach einem Mini-Stopp, siehe PR-Beschreibung):
die zuvor gebaute Variante protokollierte jeden Versandversuch in
data/push_health.json (geschrieben von notify.push()). Vor dem Versand
wurde entdeckt, dass diese Datei fuer VIER der fuenf Quellen (vertrag.yml,
waechter.yml, handover_waechter.yml, pr_verwaisung_waechter.yml) NIE
persistiert haette: alle vier tragen `permissions: contents: read` ohne
Commit-Schritt, nur lauf.yml schreibt data/ zurueck ins Repository. Genau
die vier waeren betroffen gewesen, nicht lauf.yml -- der reale Vorfall
(25.-30.09.2026, viermal in vertrag.yml) waere also NICHT erkannt worden.
Diese Variante wurde komplett verworfen, nicht nur angepasst: notify.push()
schreibt wieder NICHTS, es gibt keine Protokoll-Datei mehr.

DIE NEUE DATENQUELLE: die Actions-JOB-LOGS der letzten
ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW Laeufe JEDES der folgenden Workflows:

    lauf.yml, vertrag.yml, waechter.yml, handover_waechter.yml,
    pr_verwaisung_waechter.yml

durchsucht nach notify.FEHLSCHLAG_ANKERTEXT ("ntfy hat den Push
abgelehnt:") -- wortgleich importiert, nicht neu formuliert, damit Text
hier und Text dort nie auseinanderlaufen koennen (siehe notify.py).

"agent_datumsformat" ist KEIN eigener Workflow und steht deshalb NICHT in
der Liste oben: es ist der zweite JOB innerhalb von vertrag.yml (siehe
dort). `gh run view --log` liefert je Lauf-ID das Log ALLER Jobs dieses
Laufs in einem Aufruf -- ein Treffer in diesem zweiten Job wird also schon
mit erfasst, sobald vertrag.yml gescannt wird.

ZWEI `gh`-Aufrufe je Workflow-Lauf:
  1. `gh api repos/{REPO_SLUG}/actions/workflows/{workflow}/runs?per_page=N`
     -- dieselbe, in dieser Sitzung bereits gegen das echte Repository
     verifizierte Form wie in lauf_zeitversatz_waechter.py (liefert u. a.
     `id`, `run_started_at`).
  2. `gh run view {run_id} --repo {REPO_SLUG} --log` -- bewusst DIESER Weg,
     nicht der rohe REST-Endpunkt `.../actions/jobs/{job_id}/logs`: Letzterer
     leitet auf Blob-Storage um, und das in dieser Sitzung verfuegbare
     `gh api` verweigert diese Weiterleitung ausdruecklich (ausserhalb von
     api.github.com). `gh run view --log` ist der dokumentierte,
     CLI-eigene Weg, der diese Weiterleitung selbst handhabt -- NICHT
     direkt in dieser Sitzung nachstellbar (derselbe sandbox-bedingte
     Vorbehalt wie beim `gh api`-vs-`gh run list`-Entscheid in
     lauf_zeitversatz_waechter.py), aber der Weg, den die echte
     `gh`-Installation auf dem Actions-Runner dafuer dokumentiert vorsieht.

SCOPE-PRUEFUNG (Kriterium 2 des Auftrags, hier ausdruecklich beantwortet):
Ob DIESER Workflow (push_zustellung_waechter.yml) die Laeufe/Logs eines
ANDEREN Workflows lesen darf, haengt NICHT von dessen eigenem
`permissions:`-Block ab, sondern ausschliesslich vom Token-Scope DIESES
lesenden Workflows. Dass vertrag.yml/waechter.yml/handover_waechter.yml/
pr_verwaisung_waechter.yml selbst nur `contents: read` deklarieren,
beschraenkt nur, was IHR EIGENER GITHUB_TOKEN waehrend IHRER EIGENEN
Ausfuehrung darf -- nicht, was ein FREMDER Workflow ueber die Actions-API
ueber sie lesen darf. Entscheidend ist allein, dass
push_zustellung_waechter.yml selbst `actions: read` eintraegt (siehe dort).
Keine der vier Grenzen wird dafuer angefasst -- "harte Grenze
unangetastet" bleibt gewahrt.

MELDUNG JE WORKFLOW, NICHT JE PUSH-TYP: der Ankertext selbst nennt den
Push-TITEL nicht (er steht nur im print()-Aufruf von notify.push(), nicht
im Fehlertext), und mehrere Workflows (lauf.yml, vertrag.yml) rufen
mehrere verschiedene push_*-Funktionen auf -- eine zuverlaessige
Typ-Zuordnung allein aus dem Log waere Raten, kein Befund. Die Zaehlung
gruppiert deshalb bewusst nach WORKFLOW-DATEI, nicht nach Push-Typ.

FENSTER: nur Laeufe der letzten FENSTER_TAGE_PRUEFUNG (7) Tage gehen in
die Log-Pruefung ein -- aeltere Laeufe wuerden nur unnoetig viele
Log-Abrufe kosten, ohne das Ergebnis ("Fehlschlag in der letzten Woche?")
zu aendern.

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich (`gh api`, `gh run view
--log`) und schreibt NIRGENDS -- keinen Push wiederholen, keine Datei
aendern. Abgesichert durch die Rechte unten (`contents: read`,
`actions: read`) UND durch einen statischen Test
(tests/unit/test_push_zustellung_waechter.py), der diese Datei nach jedem
schreibenden Aufruf durchsucht.

RATE-LIMIT-REGEL: kein `gh`-Aufruf wird bei einem Fehlschlag (auch nicht
bei einer Ratenbegrenzung) wiederholt -- ein Fehlschlag wird sofort als
solcher gemeldet (siehe `fehler`-Liste in `fehlschlaege_je_workflow`),
nie stillschweigend erneut versucht.

DIE PUSH-MECHANIK: EIN Push bei mindestens einem Fund im Fenster
(Prioritaet "default", wie push_vertrag_gebrochen -- ein tatsaechlicher
Fehlschlag ist mehr als eine blosse Beobachtung). Der Lauf bleibt GRUEN
(Exit 0), solange sich der Zustand fuer MINDESTENS EINEN der ueberwachten
Workflows ermitteln liess -- ROT (Exit 1) nur, wenn sich ALLE Workflows
nicht pruefen liessen (vollstaendiges technisches Unvermoegen, dasselbe
Prinzip wie bei den anderen vier Waechtern).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess

from .config import REPO_SLUG, WORKFLOW_LAUF
from .notify import FEHLSCHLAG_ANKERTEXT, push_ntfy_fehlschlaege_woche

DateTime = _dt.datetime

# Die ueberwachten Workflow-Dateien. "agent_datumsformat" ist kein
# eigener Eintrag -- siehe Modul-Docstring (zweiter Job von vertrag.yml).
UEBERWACHTE_WORKFLOWS = (
    WORKFLOW_LAUF,
    "vertrag.yml",
    "waechter.yml",
    "handover_waechter.yml",
    "pr_verwaisung_waechter.yml",
)

# Je Workflow hoechstens so viele juengste Laeufe abfragen, bevor nach
# FENSTER_TAGE_PRUEFUNG gefiltert wird.
ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW = 20

# Nur Laeufe der letzten so vielen Tage gehen in die Log-Pruefung ein.
FENSTER_TAGE_PRUEFUNG = 7


def log(text: str) -> None:
    print(text, flush=True)


def _laeufe_eines_workflows(
    workflow: str,
    *,
    laeufer=subprocess.run,
    anzahl: int = ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW,
    repo: str = REPO_SLUG,
) -> tuple[list[dict] | None, str | None]:
    """(rohe Lauf-Datensaetze, Fehlergrund) fuer EINEN Workflow. Genau
    einer der beiden ist None. Dieselbe Form wie
    lauf_zeitversatz_waechter._letzte_laeufe()."""
    try:
        ergebnis = laeufer(
            [
                "gh", "api",
                f"repos/{repo}/actions/workflows/{workflow}/runs?per_page={anzahl}",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"gh api endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
        )
    try:
        daten = json.loads(ergebnis.stdout)
    except json.JSONDecodeError as exc:
        return None, f"gh api lieferte kein gueltiges JSON ({exc})."
    laeufe = daten.get("workflow_runs") if isinstance(daten, dict) else None
    if laeufe is None:
        return None, "Antwort enthielt kein 'workflow_runs'-Feld."
    return laeufe, None


def _log_eines_laufs(
    run_id: int, *, laeufer=subprocess.run, repo: str = REPO_SLUG,
) -> tuple[str | None, str | None]:
    """(Text-Log aller Jobs dieses Laufs, Fehlergrund). Genau einer der
    beiden ist None. Siehe Modul-Docstring fuer die Wahl von
    `gh run view --log` statt des rohen REST-Endpunkts."""
    try:
        ergebnis = laeufer(
            ["gh", "run", "view", str(run_id), "--repo", repo, "--log"],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"gh run view endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
        )
    return ergebnis.stdout, None


def _laeufe_im_fenster(
    laeufe: list[dict], *, jetzt: DateTime, fenster_tage: int = FENSTER_TAGE_PRUEFUNG,
) -> list[dict]:
    """Nur Laeufe, deren `run_started_at` (oder ersatzweise `created_at`)
    innerhalb der letzten `fenster_tage` Tage liegt."""
    grenze = jetzt - _dt.timedelta(days=fenster_tage)
    ausgewaehlt = []
    for lauf in laeufe:
        if not isinstance(lauf, dict):
            continue
        roh = lauf.get("run_started_at") or lauf.get("created_at")
        if not roh:
            continue
        try:
            start = _dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError:
            continue
        if start >= grenze:
            ausgewaehlt.append(lauf)
    return ausgewaehlt


def fehlschlaege_je_workflow(
    *,
    jetzt: DateTime | None = None,
    laeufer=subprocess.run,
    workflows: tuple[str, ...] = UEBERWACHTE_WORKFLOWS,
    anzahl: int = ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW,
    fenster_tage: int = FENSTER_TAGE_PRUEFUNG,
    repo: str = REPO_SLUG,
) -> tuple[dict[str, int], list[str], list[str], list[str]]:
    """(Zaehlung je Workflow, Liste aller Einzelprobleme, Liste komplett
    nicht pruefbarer Workflows, Liste erfolgreich geprueften Workflows).

    Die vierte Rueckgabe (`geprueft`) ist der Grund, warum `main()` NIE
    eine feste Workflow-Anzahl gegen `nicht_pruefbar` vergleichen muss --
    sie zaehlt genau die Workflows, fuer die eine Lauf-Liste tatsaechlich
    ankam (unabhaengig davon, ob darin Treffer steckten). Ist sie leer,
    liess sich ueberhaupt kein Workflow pruefen.

    `laeufer` ist die Test-Naht fuer BEIDE `gh`-Aufrufarten (Lauf-Liste
    UND Einzel-Log) -- derselbe Parametername wie in
    lauf_zeitversatz_waechter.py, hier aber zweifach genutzt.
    """
    jetzt = jetzt or _dt.datetime.now(_dt.timezone.utc)
    zaehlung: dict[str, int] = {}
    fehler: list[str] = []
    nicht_pruefbar: list[str] = []
    geprueft: list[str] = []
    for workflow in workflows:
        laeufe, grund = _laeufe_eines_workflows(
            workflow, laeufer=laeufer, anzahl=anzahl, repo=repo,
        )
        if grund is not None:
            fehler.append(f"{workflow}: Lauf-Liste nicht ermittelbar ({grund})")
            nicht_pruefbar.append(workflow)
            continue
        geprueft.append(workflow)
        for lauf in _laeufe_im_fenster(laeufe, jetzt=jetzt, fenster_tage=fenster_tage):
            run_id = lauf.get("id")
            if run_id is None:
                continue
            log_text, grund = _log_eines_laufs(run_id, laeufer=laeufer, repo=repo)
            if grund is not None:
                fehler.append(f"{workflow}#{run_id}: Log nicht ermittelbar ({grund})")
                continue
            treffer = log_text.count(FEHLSCHLAG_ANKERTEXT)
            if treffer:
                zaehlung[workflow] = zaehlung.get(workflow, 0) + treffer
    return zaehlung, fehler, nicht_pruefbar, geprueft


def stand_text(zaehlung: dict[str, int]) -> str:
    gesamt = sum(zaehlung.values())
    zeilen = [f"{workflow} (×{anzahl})" for workflow, anzahl in sorted(zaehlung.items())]
    return (
        f"{gesamt} fehlgeschlagene(r) ntfy-Versandversuch(e) in den "
        f"letzten {FENSTER_TAGE_PRUEFUNG} Tagen, gefunden in den "
        f"Actions-Logs:\n\n"
        + "\n".join(zeilen)
        + "\n\nZaehlung je betroffenem Workflow, nicht je Push-Typ -- der "
        "Ankertext selbst nennt den Push-Typ nicht."
    )


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie in den anderen vier Waechtern."""
    try:
        verschickt = melder(text)
    except Exception as exc:  # noqa: BLE001 - der Push ist Beiwerk
        log(f"Waechter: Push fehlgeschlagen ({type(exc).__name__}: {exc}).")
        return
    log(
        "Waechter: Push verschickt."
        if verschickt
        else "Waechter: Push NICHT verschickt (siehe Meldung oben)."
    )


def main(
    argv: list[str] | None = None,
    *,
    melder=push_ntfy_fehlschlaege_woche,
    ermittle=fehlschlaege_je_workflow,
) -> int:
    """`melder`/`ermittle` sind die Test-Naehte, wie bei den anderen vier
    Waechtern."""
    parser = argparse.ArgumentParser(description="Push-Zustellungs-Wächter")
    parser.parse_args(argv)

    zaehlung, fehler, nicht_pruefbar, geprueft = ermittle()
    for zeile in fehler:
        log(f"Waechter: {zeile}")

    if not geprueft:
        log("Waechter: Zustand nicht ermittelbar — kein Workflow liess sich pruefen.")
        _melden(melder, "Konnte keinen der ueberwachten Workflows pruefen (siehe Actions-Log).")
        return 1

    if not zaehlung:
        log("Waechter: keine Fehlschlaege in den Actions-Logs gefunden — still.")
        return 0

    log(f"Waechter: {sum(zaehlung.values())} Fehlschlaege gefunden.")
    _melden(melder, stand_text(zaehlung))
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring der
    # anderen Waechter fuer dieselbe Begruendung).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
