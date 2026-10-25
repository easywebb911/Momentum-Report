"""Agenten-Kontrolle: prueft, ob sich der geplante Waechter-Agent (Auftrag
5 der Automatisierung vom 24.10.2026) in den letzten FENSTER_STUNDEN noch
gemeldet hat.

AUSGANGSLAGE: seit 25.10.2026 laeuft taeglich ~11:31 UTC ein geplanter
Claude-Agent ("Waechter"), der sich IMMER meldet -- gesund per lautlosem
Status-Push (Titel "Momentum-Waechter OK TT.MM.", Prioritaet min, dieselbe
Ausnahme vom Herzschlag-Bann wie push_waechter_ok, siehe SESSION_HANDOVER.md
Entscheid 25.10.2026) oder im Fehlerfall mit einem Befund ("Momentum-
Waechter TT.MM."). Beide gehen ueber `ntfy_relay.yml` (workflow_dispatch,
siehe ntfy_relay.py) -- bleibt der Agent aus, bleibt bisher auch JEDER
Alarm aus: kein Lauf selbst kann das eigene Ausbleiben melden, derselbe
Grundgedanke wie beim Totmannschalter (waechter.py) fuer lauf.yml, nur
diesmal fuer den Agenten statt fuer den Lauf.

DIE DATENQUELLE: `gh api repos/{REPO_SLUG}/actions/workflows/
{WORKFLOW_NTFY_RELAY}/runs` -- derselbe rohe REST-Endpunkt wie in
lauf_zeitversatz_waechter.py, aus demselben Grund (kein Zugriff auf eine
echte `gh`-CLI zum Gegenpruefen von `--json`-Feldnamen in dieser Sitzung).

DAS FELD, EMPIRISCH BELEGT (nicht nur angenommen, Kriterium 4): `gh api
.../runs` liefert pro Lauf ein Feld `display_title` -- das ist entweder
der ueber `run-name:` ausgewertete Anzeigetext (sobald dieser PR gemerged
ist) oder, FUER JEDEN LAUF VON DAVOR, ein Rueckfall auf den schlichten
Workflow-`name:` ("ntfy-Relay"). Live gegen dieses Repository abgefragt
(25.10.2026): genau EIN bisheriger Lauf, Lauf-ID 40191482916,
`display_title: "ntfy-Relay"`, `head_sha: e99c1b717b...` == der Merge-
Commit von PR #75 -- ein echtes, konkretes Beispiel fuer genau den Fall,
den der Anlaufschutz unten abfangen muss: ein Lauf OHNE das neue
`run-name:`, der nie unter dem neuen Titel ("ntfy: Momentum-Waechter...")
auftauchen kann und deshalb nicht gegen das Lebenszeichen zaehlen darf.

RUN-NAME IST KEINE INJEKTIONS-FLAeCHE (belegt, Kriterium 2): `run-name:`
ist ein Top-Level-Schluessel (Geschwister von `name:`), seine `${{ }}`-
Auswertung hat NUR Zugriff auf die Kontexte `github`/`inputs`/`vars` (laut
GitHub-eigener Kontext-Tabelle KEIN `secrets`-Zugriff) und ihr Ergebnis
landet AUSSCHLIESSLICH als Anzeigetext in der Actions-Lauf-Liste -- nie in
einer Shell, anders als eine `${{ }}`-Interpolation in einer `run:`-Zeile
(die eigentliche Injektionsmechanik, siehe CVE-2023-49291 und GitHubs
eigene "script injections"-Doku: dort wird der Ausdruck VOR dem
Shell-Parsing textuell eingesetzt). Das einzige verbleibende Risiko ist
rein kosmetisch: ein praeparierter `inputs.title` koennte einen
irrefuehrenden Text in der Actions-Oberflaeche erzeugen ("Display-
Spoofing") -- keine Befehlsausfuehrung. Siehe
tests/unit/test_agenten_kontrolle.py::test_run_name_ist_keine_shell_interpolation
fuer den statischen Beleg gegen die tatsaechliche Workflow-Datei.

ANLAUFSCHUTZ, GENAU: Laeufe von VOR diesem PR (ohne `run-name:`) duerfen
nicht als "kein Lebenszeichen" gewertet werden, sonst waere die allererste
Pruefung nach dem Merge ein Fehlalarm. Statt eines geschaetzten/
hartcodierten Merge-Zeitpunkts (der beim Schreiben dieses Moduls noch
nicht bekannt ist -- Easy merged von Hand, zu einem unbekannten Zeitpunkt
NACH dem Oeffnen des PRs) wird der tatsaechliche Einfuehrungs-Zeitpunkt
EMPIRISCH aus der Git-Historie von ntfy_relay.yml ermittelt: der aelteste
Commit, der die Zeile "run-name:" in dieser Datei einfuehrt (`git log -S`,
absteigend sortiert, letzte Zeile der Ausgabe = der aelteste Treffer).
Das ist der tatsaechliche Merge-Commit dieses PRs (jeder Merge auf `main`
ist selbst ein Commit) -- exakt, nicht geschaetzt. Gibt es NOCH KEINEN
Lauf mit dem neuen Titel UND liegt dieser Einfuehrungs-Zeitpunkt weniger
als FENSTER_STUNDEN zurueck: kein Alarm, nur eine Log-Zeile.

FAIL-SOFT, AUSDRUECKLICH ANDERS ALS BEI DEN ANDEREN WAeCHTERN DIESES
PROJEKTS: scheitert EINE der beiden Ermittlungen (Lauf-Historie ODER
Einfuehrungs-Zeitpunkt), wird dieser Lauf ROT (Exit 1, sichtbar fuer
push_zustellung_waechter.py) -- aber es wird KEIN Push verschickt. Begruendung
(Bau-Punkt 5 des Auftrags): dieses Modul ist ein ALARM, kein Herzschlag --
ein Fehlalarm bei technischer Unsicherheit waere genau die Sorte Rauschen,
die den Alarmkanal abstumpft (derselbe Massstab wie beim Herzschlag-Bann,
SESSION_HANDOVER.md 10.08.2026). Ein technischer Fehlschlag macht sich
stattdessen durch den roten CI-Lauf selbst bemerkbar.

JETZT IST EIN PARAMETER (Kriterium 7): `datetime.now(UTC)` steht einzig
in main() (als Default fuer `--jetzt`), niemals in der Entscheidungslogik
selbst -- dieselbe Form wie bei datenabdeckung_waechter.py/
wiedervorlagen_waechter.py. Dieselbe Lauf-Historie UND derselbe
Einfuehrungs-Zeitpunkt muessen bei gleichem `jetzt` immer dieselbe
Entscheidung ergeben.

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich (`gh api .../runs`, `git
log`) und schreibt NIRGENDS -- keinen Workflow erneut ausloesen, keinen
`gh pr merge`. Serverseitig erzwungen durch die Rechte des zugehoerigen
Workflows (nur `contents: read`, `actions: read`) UND durch einen
statischen Test (tests/unit/test_agenten_kontrolle.py), der den Quelltext
auf jeden schreibenden Aufruf UND auf jede `gh pr merge`-Konstante
durchsucht.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path

from .config import REPO_SLUG, WORKFLOW_NTFY_RELAY
from .notify import push_waechter_agent_stumm

DateTime = _dt.datetime
UTC = _dt.timezone.utc

# Der Waechter-Agent meldet sich taeglich (~11:31 UTC). 48 Std. ist das
# DOPPELTE dieser taeglichen Kadenz -- ein einzelner ausgebliebener/
# verspaeteter Tag loest noch keinen Alarm aus (derselbe Sicherheitsabstand-
# Gedanke wie bei ERINNERUNG_TAGE/SCHWELLE_STUNDEN in den anderen
# Waechtern), aber zwei ausgebliebene Tage in Folge sind kein Zufall mehr.
FENSTER_STUNDEN = 48.0

# Das Lebenszeichen des Waechter-Agenten -- siehe Modul-Docstring.
TITEL_PRAEFIX = "ntfy: Momentum-Waechter"

# Wie viele der juengsten Laeufe von ntfy_relay.yml betrachtet werden.
# Grosszuegig: ntfy_relay.yml wird auch von Lit-Check/Monatsrundgang
# ausgeloest, 30 Laeufe deckt mehrere Wochen ab, selbst wenn dazwischen
# viele andere Titel liegen.
ANZAHL_LETZTE_LAEUFE = 30

# Die Zeile, nach der in der Git-Historie von ntfy_relay.yml gesucht wird,
# um den tatsaechlichen Einfuehrungs-Zeitpunkt des Anlaufschutzes zu
# finden (siehe Modul-Docstring, ANLAUFSCHUTZ).
RUN_NAME_SUCHMUSTER = "run-name:"

NTFY_RELAY_PFAD = ".github/workflows/ntfy_relay.yml"


def log(text: str) -> None:
    print(text, flush=True)


def _laeufe_ntfy_relay(
    *, laeufer=subprocess.run, anzahl: int = ANZAHL_LETZTE_LAEUFE, repo: str = REPO_SLUG,
    workflow: str = WORKFLOW_NTFY_RELAY,
) -> tuple[list[dict] | None, str | None]:
    """(rohe Lauf-Datensaetze, Fehlergrund). Genau einer der beiden ist
    None. Dasselbe Fehlerbehandlungs-Muster wie in
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


def _run_name_eingefuehrt_am(
    *, laeufer=subprocess.run, pfad: str = NTFY_RELAY_PFAD,
) -> tuple[DateTime | None, str | None]:
    """(Zeitpunkt der Einfuehrung von `run-name:` in ntfy_relay.yml,
    Fehlergrund) -- siehe Modul-Docstring, ANLAUFSCHUTZ. `git log -S`
    listet neueste Treffer zuerst; die LETZTE Zeile der Ausgabe ist damit
    der AELTESTE Commit, der das Suchmuster einfuehrt."""
    try:
        ergebnis = laeufer(
            [
                "git", "log", f"-S{RUN_NAME_SUCHMUSTER}",
                "--format=%aI", "--", pfad,
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, f"git log endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
    zeilen = [z for z in ergebnis.stdout.splitlines() if z.strip()]
    if not zeilen:
        return None, f"kein Commit fuehrt {RUN_NAME_SUCHMUSTER!r} in {pfad} ein."
    try:
        return _dt.datetime.fromisoformat(zeilen[-1].strip()), None
    except ValueError as exc:
        return None, f"git log lieferte kein gueltiges ISO-8601-Datum ({exc})."


def _lauf_zeit(lauf: dict) -> DateTime | None:
    roh = lauf.get("run_started_at") or lauf.get("created_at")
    if not roh:
        return None
    try:
        return _dt.datetime.fromisoformat(str(roh).replace("Z", "+00:00"))
    except ValueError:
        return None


def juengstes_lebenszeichen(laeufe: list[dict]) -> DateTime | None:
    """Der juengste Zeitpunkt unter den ERFOLGREICHEN Laeufen, deren Titel
    mit TITEL_PRAEFIX beginnt -- None, wenn keiner passt (weder
    fehlgeschlagene Laeufe noch andersartige Titel wie ein Lit-Check-Lauf
    zaehlen)."""
    treffer: list[DateTime] = []
    for lauf in laeufe:
        if not isinstance(lauf, dict):
            continue
        if lauf.get("conclusion") != "success":
            continue
        titel = lauf.get("display_title") or ""
        if not str(titel).startswith(TITEL_PRAEFIX):
            continue
        zeit = _lauf_zeit(lauf)
        if zeit is not None:
            treffer.append(zeit)
    return max(treffer) if treffer else None


def alarm_faellig(
    laeufe: list[dict], *, jetzt: DateTime, eingefuehrt_am: DateTime,
) -> tuple[bool, str]:
    """(Alarm faellig?, Log-Zeile). Reine Entscheidungslogik -- `jetzt`
    und `eingefuehrt_am` kommen IMMER von aussen (Kriterium 7)."""
    letztes = juengstes_lebenszeichen(laeufe)
    if letztes is not None:
        alter = (jetzt - letztes).total_seconds() / 3600
        if alter <= FENSTER_STUNDEN:
            return False, f"Letztes Lebenszeichen vor {alter:.1f} Std. — im Rahmen."
        return True, (
            f"Letztes Lebenszeichen vor {alter:.1f} Std. > "
            f"Schwelle {FENSTER_STUNDEN} Std."
        )

    seit_einfuehrung = (jetzt - eingefuehrt_am).total_seconds() / 3600
    if seit_einfuehrung < FENSTER_STUNDEN:
        return False, (
            f"Anlaufschutz aktiv: run-name erst seit {seit_einfuehrung:.1f} Std. "
            f"eingefuehrt (< {FENSTER_STUNDEN} Std.) — noch kein Lebenszeichen "
            "unter dem neuen Titel erwartet."
        )
    return True, (
        f"Kein Lebenszeichen mit Titel {TITEL_PRAEFIX!r} gefunden, und "
        f"run-name bereits seit {seit_einfuehrung:.1f} Std. eingefuehrt "
        f"(Anlaufschutz abgelaufen)."
    )


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie in den anderen Waechtern."""
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
    melder=push_waechter_agent_stumm,
    ermittle_laeufe=_laeufe_ntfy_relay,
    ermittle_eingefuehrt_am=_run_name_eingefuehrt_am,
) -> int:
    """`melder`/`ermittle_laeufe`/`ermittle_eingefuehrt_am` sind die
    Test-Naehte, wie bei jedem anderen Waechter dieses Projekts."""
    parser = argparse.ArgumentParser(description="Agenten-Kontrolle")
    parser.add_argument(
        "--jetzt", help="Bezugszeitpunkt UTC, ISO-8601 (nur fuer Tests)"
    )
    args = parser.parse_args(argv)
    if args.jetzt:
        jetzt = _dt.datetime.fromisoformat(args.jetzt)
        if jetzt.tzinfo is None:
            jetzt = jetzt.replace(tzinfo=UTC)
    else:
        jetzt = _dt.datetime.now(UTC)  # einzige Stelle, nie in der Entscheidungslogik

    laeufe, grund = ermittle_laeufe()
    if grund is not None:
        # FAIL-SOFT (siehe Modul-Docstring): rot, aber KEIN Push --
        # anders als bei den anderen Waechtern dieses Projekts, bewusst,
        # weil dieses Modul selbst ein Alarm ist, kein Herzschlag.
        log(f"Waechter: Lauf-Historie nicht ermittelbar — {grund}")
        return 1

    eingefuehrt_am, grund = ermittle_eingefuehrt_am()
    if grund is not None:
        log(f"Waechter: Einfuehrungs-Zeitpunkt von run-name nicht ermittelbar — {grund}")
        return 1

    alarm, text = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=eingefuehrt_am)
    log(f"Waechter: {text}")
    if not alarm:
        return 0

    _melden(
        melder,
        "Der Wächter-Agent hat sich seit über 48 Std. nicht gemeldet. "
        "Bitte Claude fragen, wie die geplanten Aufgaben gelaufen sind.\n\n"
        f"{text}",
    )
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring der
    # anderen Waechter fuer dieselbe Begruendung).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
