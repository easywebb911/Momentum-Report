"""Doku-Waechter: erkennt, wenn SESSION_HANDOVER.md gegenueber dem
tatsaechlichen PR-Stand zu weit zurueckliegt.

Dasselbe Grundmuster wie der Totmannschalter (waechter.py), auf ein
anderes Symptom angewandt: SESSION_HANDOVER.md meldet sein eigenes
Zurueckliegen nie selbst -- niemand stoesst die Pflege automatisch an,
sie braucht immer einen bewusst gewaehlten Anlass. Genau das ist diese
Woche real passiert: sieben gemergte PRs (#51-#57) lang blieb das
Dokument unveraendert, bis es zufaellig aufgefallen ist (siehe
SESSION_HANDOVER.md, Lesson 11 und ihre Wiederholung in der Kopf-Notiz).

DIE ZAEHLWEISE, exakt: der juengste main-Commit, der SESSION_HANDOVER.md
veraendert hat, markiert "hier war das Dokument zuletzt auf dem
laufenden". Jeder auf `main` gemergte PR mit `mergedAt` NACH diesem
Zeitpunkt (streng >, nicht >=) zaehlt als seither ungepflegt. Der
PR, der den Handover-Commit selbst enthielt, faellt dadurch automatisch
heraus -- sein `mergedAt` liegt nie NACH dem eigenen Commit.

Committer-Datum (`git log --format=%cI`), nicht Autoren-Datum: bei einem
Squash- oder Fast-Forward-Merge (das uebliche Muster in diesem Repo, vgl.
SESSION_HANDOVER.md §2) setzt GitHub das Committer-Datum auf den
tatsaechlichen Landungszeitpunkt auf `main`; das Autoren-Datum kann vom
urspruenglichen, oft frueheren Branch-Commit stammen. Vergleichbar mit
`mergedAt` (ebenfalls ein Landungszeitpunkt) ist nur das Committer-Datum.

DIE SCHWELLE: 4 ungepflegte PRs, unveraendert aus dem Auftrag uebernommen
(nicht selbst hergeleitet) -- der reale Fall dieser Woche waere damit
schon bei #54 (dem vierten ungepflegten PR nach #51/#52/#53) erkannt
worden, nicht erst bei #57.

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich (`git log`, `gh pr list`) und
schreibt NIRGENDS in SESSION_HANDOVER.md, committet nichts, oeffnet
keinen PR. Abgesichert auf zwei unabhaengigen Ebenen: das Token des
Workflows selbst traegt nur `contents: read` und `pull-requests: read`
(ein `gh pr create` wuerde damit serverseitig mit 403 abgelehnt, nicht
nur durch Programmierdisziplin vermieden) UND ein statischer Test
(tests/unit/test_handover_waechter.py) durchsucht diese Datei nach jedem
Schreib- oder PR-Erzeugungs-Aufruf und schlaegt fehl, wenn einer
auftaucht.

DIE PUSH-MECHANIK: EIN lautloser Push (Prioritaet "min", wie der
bestehende Erfolgspuls des Lauf-Waechters -- push_waechter_ok), NIE eine
Sirene. Das ist eine Erinnerung an eine noch zu erledigende, bewusst
geprueft anzustossende Pflege, kein "etwas ist kaputt" -- die eigentliche
Pflege bleibt ein eigener PR wie bisher. Entsprechend bleibt der
Waechter-Lauf auch beim Ueberschreiten der Schwelle GRUEN (Exit 0): der
Push selbst ist das Signal, kein roter Lauf noetig. Nur wenn sich der
Zustand technisch gar nicht ermitteln laesst (git log liefert nichts,
`gh pr list` schlaegt fehl oder liefert unlesbare Daten), endet der Lauf
ROT (Exit 1) -- dasselbe Prinzip wie beim Lauf-Waechter: "kann den
Zustand nicht bestimmen" ist selbst ein Befund, nie ein Achselzucken,
und verdient das zweite, vom Push unabhaengige Signal.

GRENZE, ehrlich benannt: gezaehlt werden PRs, die `gh pr list` als auf
`main` gemergt kennt. Ein Push direkt auf `main` ohne PR wuerde nicht
erfasst -- in diesem Repo policy-widrig und praktisch nicht vorgesehen,
aber technisch nicht ausgeschlossen. Ebenso bleibt, wie beim Lauf-
Waechter, EINE Stufe Rekursion offen: faellt GitHub Actions als Ganzes
aus, schweigt auch dieser Waechter.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path

from .notify import push_handover_pflege_faellig

HANDOVER_PFAD = Path("SESSION_HANDOVER.md")

# Ab wie vielen seit dem letzten Handover-Commit gemergten PRs die Pflege
# faellig ist. Unveraendert aus dem Auftrag uebernommen, nicht selbst
# hergeleitet (siehe Modul-Docstring).
SCHWELLE_PRS = 4

# Grosszuegig ueber der bisherigen Gesamtzahl aller PRs dieses Repos --
# ein zu knappes Limit koennte aeltere PRs verschlucken, aber (weil
# `gh pr list` neuere PRs zuerst liefert) nie zu einer FALSCH ZU NIEDRIGEN
# Zaehlung fuehren, hoechstens zu einem laut gemeldeten technischen
# Fehlschlag weiter unten in der Kette.
PR_LISTEN_LIMIT = 500


def log(text: str) -> None:
    print(text, flush=True)


def letzter_handover_commit(
    pfad: Path = HANDOVER_PFAD, *, laeufer=subprocess.run
) -> tuple[_dt.datetime | None, str | None]:
    """(Committer-Datum des juengsten main-Commits auf `pfad`, Fehlergrund).

    Genau einer der beiden ist immer None. Jede Form von "laesst sich
    nicht ermitteln" -- kein Commit, git nicht aufrufbar, unlesbares
    Datum -- liefert einen Grund, nie ein stillschweigendes "wird schon
    passen" (dasselbe Prinzip wie waechter.befund()).
    """
    try:
        ergebnis = laeufer(
            ["git", "log", "-1", "--format=%cI", "--", str(pfad)],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"git log auf {pfad} endete mit rc={ergebnis.returncode}: "
            f"{ergebnis.stderr.strip()}"
        )
    zeile = ergebnis.stdout.strip()
    if not zeile:
        return None, (
            f"git log fand keinen Commit, der {pfad} veraendert hat -- "
            f"Datei fehlt oder Historie ist unvollstaendig (shallow clone?)."
        )
    try:
        return _dt.datetime.fromisoformat(zeile), None
    except ValueError as exc:
        return None, f"Unlesbares Commit-Datum {zeile!r} ({exc})."


def gemergte_prs_seit(
    seit: _dt.datetime, *, laeufer=subprocess.run, limit: int = PR_LISTEN_LIMIT
) -> tuple[list[tuple[int, str]] | None, str | None]:
    """(sortierte Liste (Nummer, Titel) aller auf `main` gemergten PRs mit
    `mergedAt` > `seit`, Fehlergrund). Genau einer der beiden ist None.

    `gh pr list` filtert nicht serverseitig nach `mergedAt` -- deshalb
    wird hier Client-seitig verglichen (siehe PR_LISTEN_LIMIT oben zur
    Begruendung des grossen Limits).
    """
    try:
        ergebnis = laeufer(
            [
                "gh", "pr", "list",
                "--state", "merged",
                "--base", "main",
                "--limit", str(limit),
                "--json", "number,title,mergedAt",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"gh pr list endete mit rc={ergebnis.returncode}: "
            f"{ergebnis.stderr.strip()}"
        )
    try:
        prs = json.loads(ergebnis.stdout)
    except json.JSONDecodeError as exc:
        return None, f"gh pr list lieferte kein gueltiges JSON ({exc})."

    ungepflegt: list[tuple[int, str]] = []
    for pr in prs:
        roh = pr.get("mergedAt")
        if not roh:
            return None, f"PR #{pr.get('number', '?')} traegt kein mergedAt."
        try:
            gemergt = _dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
        except ValueError as exc:
            return None, f"PR #{pr.get('number', '?')}: unlesbares mergedAt {roh!r} ({exc})."
        if gemergt > seit:
            ungepflegt.append((pr["number"], pr.get("title", "")))

    ungepflegt.sort(key=lambda eintrag: eintrag[0])
    return ungepflegt, None


def stand_text(ungepflegt: list[tuple[int, str]]) -> str:
    """Die Nutzlast des Push -- Anzahl UND Nummern, damit der naechste
    Handover-Nachzug direkt weiss, was fehlt, ohne selbst erst zu zaehlen."""
    nummern = ", ".join(f"#{nummer}" for nummer, _ in ungepflegt)
    return (
        f"SESSION_HANDOVER.md liegt {len(ungepflegt)} gemergte PR(s) "
        f"zurueck (Schwelle {SCHWELLE_PRS}): {nummern}."
    )


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst (dasselbe Prinzip
    wie in waechter.main()): ein fehlschlagender ODER werfender Melder
    darf diesen Waechter nie zum Absturz bringen, nur zu einer Log-Zeile."""
    try:
        verschickt = melder(text)
    except Exception as exc:  # noqa: BLE001 - der Push ist Beiwerk
        log(f"Waechter: Push fehlgeschlagen ({type(exc).__name__}: {exc}).")
        return
    log(
        "Waechter: Push (lautlos) verschickt."
        if verschickt
        else "Waechter: Push NICHT verschickt (siehe Meldung oben)."
    )


def main(
    argv: list[str] | None = None,
    *,
    melder=push_handover_pflege_faellig,
    ermittle_commit=letzter_handover_commit,
    ermittle_prs=gemergte_prs_seit,
) -> int:
    """`melder`, `ermittle_commit`, `ermittle_prs` sind die Test-Naehte --
    Tests ersetzen sie durch Doubles, genau wie `melder`/`status_melder`
    bei waechter.main(). `ermittle_commit`/`ermittle_prs` sind zusaetzlich
    noetig, weil hier (anders als beim Lauf-Waechter) zwei externe
    Prozesse (`git`, `gh`) befragt werden, nicht nur eine lokale Datei."""
    parser = argparse.ArgumentParser(description="Doku-Waechter fuer SESSION_HANDOVER.md")
    parser.add_argument("--handover", default=str(HANDOVER_PFAD), help="Pfad zur Handover-Datei")
    args = parser.parse_args(argv)

    seit, grund = ermittle_commit(Path(args.handover))
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte den Handover-Rueckstand nicht ermitteln: {grund}")
        return 1

    ungepflegt, grund = ermittle_prs(seit)
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte den Handover-Rueckstand nicht ermitteln: {grund}")
        return 1

    anzahl = len(ungepflegt)
    if anzahl < SCHWELLE_PRS:
        log(
            f"Waechter: {anzahl} PR(s) seit dem letzten Handover-Commit "
            f"({seit.isoformat()}) — unter der Schwelle ({SCHWELLE_PRS}), still."
        )
        return 0

    text = stand_text(ungepflegt)
    log(f"Waechter: Meldung faellig — {text}")
    _melden(melder, text)
    # Bewusst gruen: der Push IST das Signal, kein zusaetzlicher roter
    # Lauf noetig (anders als beim Lauf-Waechter -- siehe Modul-Docstring).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
