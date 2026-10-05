"""Lauf-Zeitversatz-Wächter: wie weit die juengsten Momentum-Laeufe
tatsaechlich vom nominellen Cron-Zeitpunkt abwichen.

Fuenftes Modul nach demselben Grundmuster wie die anderen vier Waechter
dieses Projekts, auf ein fuenftes Symptom angewandt -- diesmal nicht
binaer (lief/lief nicht), sondern eine WACHSENDE GROESSE, die noch
nicht kritisch ist, es aber werden kann: GitHub Actions garantiert
NIE einen exakten Cron-Zeitpunkt, nur einen fruehesten (siehe
https://docs.github.com/actions -- geplante Workflows koennen sich bei
hoher Last verzoegern). Bisher unkritisch, weil die Zeitfenster-Logik
des Laufs selbst grosszuegig ist (siehe config.Market.
stichtag_lauf_nicht_vor_utc und den realen Vorfall, Lauf 48, 31.08.2026,
in SESSION_HANDOVER.md). Eine langsam WACHSENDE Verzoegerung koennte das
irgendwann aendern (siehe PR #53) -- und eine Drift, die sich ueber
Wochen aufbaut, faellt niemandem auf, der nicht gezielt misst.

DIE DATENQUELLE: `gh api repos/{REPO_SLUG}/actions/workflows/
{WORKFLOW_LAUF}/runs` -- bewusst `gh api` (roher REST-Endpunkt) statt
`gh run list` (das CLI-eigene `--json`-Feldschema). Grund, hier belegt
statt angenommen: dieses Projekt hat keinen Zugriff auf eine echte
`gh`-CLI-Installation zum Gegenpruefen der genauen `--json`-Feldnamen,
waehrend der rohe REST-Endpunkt bereits in dieser Sitzung direkt
abgefragt wurde und zuverlaessig ein Feld `run_started_at`
(ISO-8601, UTC, Sekundengenau) liefert -- z. B. fuer Lauf-ID 36798080643
("2026-10-01T00:49:22Z"). `gh api` ist Teil JEDER `gh`-Installation
(auch der echten auf dem Actions-Runner), der rohe REST-Pfad ist damit
die zuverlaessigere Annahme, nicht die CLI-eigene Feld-Umbenennung.

DIE NOMINELLE ZEIT bleibt FEST bei 21:45 UTC (== lauf.yml, `cron: "45 21
* * 1-5"`) -- unabhaengig von Zeitzone oder Sommer-/Winterzeit auf
irgendeiner Seite, weil cron-Zeitplaene von GitHub Actions selbst IMMER
in UTC ausgewertet werden (dokumentiert) und `run_started_at` ebenfalls
in UTC steht. Keine lokale Zeitumrechnung noetig oder gewollt.

NUR `event == "schedule"`-Laeufe gehen in die Auswertung ein -- ein
WIDERSPRUCH, hier gemeldet statt stillschweigend uebergangen (Kriterium
2): ein `workflow_dispatch`-Lauf (z. B. Lauf 72, 01.10.2026 21:13 UTC,
Easys manueller Nachlauf nach dem iShares-Fehlschlag) hat KEINEN
nominellen Cron-Zeitpunkt, gegen den sich eine "Verspaetung" ueberhaupt
sinnvoll bestimmen liesse -- er haette in dieser Auswertung als
nahezu-puenktlicher ODER als wild verspaeteter Lauf erscheinen koennen,
rein zufaellig je nachdem, wann Easy ihn ausgeloest hat. Das waere eine
Verzerrung der Beobachtung gewesen, kein Befund.

DAS NOMINELLE-ZEITPUNKT-PROBLEM UEBER MITTERNACHT: ein Lauf, der um
21:45 UTC ausgeloest, aber erst kurz nach Mitternacht tatsaechlich
gestartet wird (der REALE, haeufige Fall -- siehe nominal_vor()-
Docstring fuer die drei beobachteten Beispiele), liegt kalendarisch
einen Tag NACH seinem eigenen nominellen Zeitpunkt. `nominal_vor()`
sucht deshalb rueckwaerts den naechstgelegenen Werktag-21:45-Zeitpunkt
VOR dem tatsaechlichen Start -- niemals vorwaerts, weil ein Cron-Trigger
sich nur verspaeten, nie vorauseilen kann.

DIE SCHWELLE: mehr als 4 Stunden Verzoegerung bei MINDESTENS EINEM der
letzten ANZAHL_LETZTE_LAEUFE (10) Laeufe loest die Meldung aus -- beides
aus dem Auftrag uebernommen, nicht selbst hergeleitet.

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich (`gh api .../runs`) und
schreibt NIRGENDS -- keinen Workflow erneut ausloesen, keinen Zeitplan
aendern. Abgesichert wie bei pr_verwaisung_waechter.py: das Workflow-
Token traegt nur `contents: read` und `actions: read`, UND ein
statischer Test durchsucht diese Datei nach jedem schreibenden Aufruf.

DIE PUSH-MECHANIK: EIN lautloser Push (Prioritaet "min", wie
push_waechter_ok), NIE eine Sirene -- reine Beobachtung ohne
Handlungsaufforderung, ausdruecklich aus dem Auftrag. Der Lauf bleibt
GRUEN (Exit 0), solange sich der Zustand ermitteln liess -- unabhaengig
davon, ob eine Verzoegerung gefunden wurde. ROT (Exit 1) nur bei
technischem Unvermoegen, den Zustand ueberhaupt zu ermitteln (dasselbe
Prinzip wie bei den anderen vier Waechtern).

GRENZE, ehrlich benannt: `nominal_vor()` sucht hoechstens
RUECKBLICK_TAGE_NOMINAL (3) Kalendertage zurueck nach einem gueltigen
Werktag. Faellt ein Lauf aus diesem Rahmen (z. B. ein extrem verspaeteter
Lauf, der ueber ein ganzes Wochenende hinweg erst Montagnacht
nachgeholt wuerde), liefert `nominal_vor()` None und dieser EINE Lauf
wird aus der Verzoegerungs-Auswertung ausgeschlossen (nicht als Fehler
behandelt) -- ein derart extremer Fall waere ohnehin laengst vom
Totmannschalter (waechter.py) erkannt worden, das ist nicht die Aufgabe
dieses Moduls.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path

from .config import REPO_SLUG, WORKFLOW_LAUF
from .notify import push_zeitversatz_beobachtet

DateTime = _dt.datetime

# Die letzten so vielen Laeufe werden betrachtet. Unveraendert aus dem
# Auftrag uebernommen.
ANZAHL_LETZTE_LAEUFE = 10

# Mehr als so viele Stunden Verzoegerung bei MINDESTENS EINEM der
# betrachteten Laeufe loest die Meldung aus. Unveraendert aus dem
# Auftrag uebernommen.
SCHWELLE_STUNDEN = 4.0

# lauf.yml: `cron: "45 21 * * 1-5"` -- IMMER UTC (GitHub wertet
# Workflow-Zeitplaene ausschliesslich in UTC aus), hier deshalb bewusst
# keine Zeitzonen-Bibliothek und kein DST-Umrechnen.
NOMINELLE_UHRZEIT_UTC = _dt.time(21, 45)

# Wie weit nominal_vor() hoechstens rueckwaerts nach einem gueltigen
# Werktag sucht, bevor sie aufgibt (siehe Modul-Docstring, GRENZE).
RUECKBLICK_TAGE_NOMINAL = 3


def log(text: str) -> None:
    print(text, flush=True)


def nominal_vor(start: DateTime, *, rueckblick_tage: int = RUECKBLICK_TAGE_NOMINAL) -> DateTime | None:
    """Den naechstgelegenen Werktag-21:45-UTC-Zeitpunkt VOR (oder genau
    auf) `start` finden -- niemals danach, ein Cron-Trigger kann sich nur
    verspaeten, nie vorauseilen.

    Reale Beispiele aus dieser Sitzung (02.10.2026, `gh api`-Abfrage
    gegen das echte Repository): drei aufeinanderfolgende `schedule`-
    Laeufe mit `run_started_at` 2026-09-30T00:45:02Z, 2026-10-01T00:49:22Z
    und 2026-10-02T01:04:16Z -- jeder davon kalendarisch am TAG NACH
    seinem eigenen nominellen 21:45-UTC-Zeitpunkt, mit Verzoegerungen von
    rund 2h58m bis 3h19m. `nominal_vor()` liefert fuer alle drei den
    korrekten Vortag (29./30.09./01.10., je 21:45 UTC) -- keiner davon
    haette die SCHWELLE_STUNDEN gerissen, aber alle drei liegen bereits
    in derselben Groessenordnung, die diese Beobachtung einfangen soll.
    """
    kandidat = start.replace(
        hour=NOMINELLE_UHRZEIT_UTC.hour, minute=NOMINELLE_UHRZEIT_UTC.minute,
        second=0, microsecond=0,
    )
    if kandidat > start:
        kandidat -= _dt.timedelta(days=1)
    for _ in range(rueckblick_tage):
        if kandidat.weekday() < 5:  # Montag=0 ... Freitag=4
            return kandidat
        kandidat -= _dt.timedelta(days=1)
    return None


def _letzte_laeufe(
    *, laeufer=subprocess.run, anzahl: int = ANZAHL_LETZTE_LAEUFE, repo: str = REPO_SLUG,
    workflow: str = WORKFLOW_LAUF,
) -> tuple[list[dict] | None, str | None]:
    """(rohe Lauf-Datensaetze, Fehlergrund). Genau einer der beiden ist
    None. Dieselbe Fehlerbehandlung wie bei den `gh`-Aufrufen in
    pr_verwaisung_waechter.py/handover_waechter.py."""
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


def verzoegerungen_stunden(laeufe: list[dict]) -> list[tuple[int, float]]:
    """(Lauf-ID, Verzoegerung in Stunden) je AUSWERTBAREM Lauf -- nur
    `event == "schedule"` (siehe Modul-Docstring) und nur, wenn
    `nominal_vor()` einen gueltigen Bezugspunkt findet."""
    ergebnisse: list[tuple[int, float]] = []
    for lauf in laeufe:
        if not isinstance(lauf, dict) or lauf.get("event") != "schedule":
            continue
        roh_start = lauf.get("run_started_at")
        if not roh_start:
            continue
        try:
            start = _dt.datetime.fromisoformat(str(roh_start).replace("Z", "+00:00"))
        except ValueError:
            continue
        nominal = nominal_vor(start)
        if nominal is None:
            continue
        delta_stunden = (start - nominal).total_seconds() / 3600
        ergebnisse.append((lauf.get("id"), delta_stunden))
    return ergebnisse


def stand_text(groesste: float) -> str:
    return (
        f"Groesste beobachtete Verspaetung gegenueber dem nominellen "
        f"Cron-Zeitpunkt (21:45 UTC) unter den juengsten "
        f"{ANZAHL_LETZTE_LAEUFE} Laeufen: {groesste:.1f} Std.\n\n"
        f"Reine Beobachtung, keine Handlungsaufforderung."
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
    melder=push_zeitversatz_beobachtet,
    ermittle_laeufe=_letzte_laeufe,
) -> int:
    """`melder`/`ermittle_laeufe` sind die Test-Naehte, wie bei den
    anderen vier Waechtern."""
    parser = argparse.ArgumentParser(description="Lauf-Zeitversatz-Wächter")
    parser.parse_args(argv)

    laeufe, grund = ermittle_laeufe()
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte Lauf-Historie nicht ermitteln: {grund}")
        return 1

    verzoegerungen = verzoegerungen_stunden(laeufe)
    if not verzoegerungen:
        log("Waechter: keine auswertbaren (schedule-ausgeloesten) Laeufe gefunden — still.")
        return 0

    groesste = max(stunden for _, stunden in verzoegerungen)
    if groesste <= SCHWELLE_STUNDEN:
        log(f"Waechter: groesste Verzoegerung {groesste:.1f} Std. — im Rahmen.")
        return 0

    log(f"Waechter: Verzoegerung {groesste:.1f} Std. > Schwelle {SCHWELLE_STUNDEN} Std.")
    _melden(melder, stand_text(groesste))
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring der
    # anderen Waechter fuer dieselbe Begruendung).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
