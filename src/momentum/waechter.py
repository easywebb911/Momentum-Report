"""Totmannschalter: schlaegt an, wenn der Momentum-Lauf NICHT stattfindet.

Der Lauf meldet seine Fehlschlaege selbst (push_run_failed). Was er
prinzipbedingt nie melden kann: dass er gar nicht mehr aufgerufen wird --
abgeschalteter Workflow, kaputte YAML, ein von GitHub stillgelegter
Zeitplan. Dann friert die Seite kommentarlos auf dem letzten guten Stand
ein, und der einzige Hinweis waere das Staleness-Banner, das nur sieht,
wer ohnehin hinschaut.

Dieses Modul prueft deshalb aus einem EIGENEN, unabhaengigen Workflow
heraus das Alter von data/status.json -- die Datei schreibt jeder
erfolgreiche Lauf neu. Ist der letzte Lauf aelter als jede normale
Luecke, geht ein Push mit Sirene raus und der Waechter-Lauf endet rot.

DIE SCHWELLE, hergeleitet statt geraten: Der Lauf ist werktaeglich
(21:45 UTC). Die laengste normale Luecke ist das Wochenende -- Freitag-
Lauf bis Montag-Morgen sind drei Kalendertage. Schlaegt zusaetzlich ein
einzelner Freitags-Lauf fehl (das meldet er selbst), steht der letzte
Stand vom Donnerstag: vier Tage. Ab MEHR als vier Kalendertagen ist die
Stille durch nichts Normales mehr erklaerbar.

KEIN HERZSCHLAG: Der Waechter schweigt, solange alles laeuft. Ein
woechentlicher "alles ok"-Push wuerde nur abstumpfen -- und ein
ausbleibender "alles ok"-Push faellt genauso wenig auf wie ein
ausbleibender Lauf.

GRENZE, ehrlich benannt: Der Waechter ist selbst ein geplanter Workflow.
Faellt GitHub Actions als Ganzes aus oder deaktiviert GitHub nach 60
Tagen Repo-Inaktivitaet alle Zeitplaene, schweigt auch er. Diese eine
Stufe Rekursion bleibt bewusst offen -- ein zweiter Waechter fuer den
Waechter waere Tuerme auf Tuermen. Praktisch faengt er den Fall trotzdem
weitgehend: bricht der Lauf (und damit der taegliche Commit) ab, schlaegt
der Waechter binnen einer Woche an, lange vor der 60-Tage-Stilllegung.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from .notify import push_lauf_ueberfaellig

Date = _dt.date

STATUS_PFAD = Path("data/status.json")

# Mehr als vier Kalendertage seit dem letzten Lauf: Alarm.
# Herleitung im Modul-Docstring -- Wochenende (3) + ein bereits selbst
# gemeldeter Einzel-Fehlschlag (4) sind normal, fuenf sind es nie.
SCHWELLE_TAGE = 4


def log(text: str) -> None:
    print(text, flush=True)


def befund(status_pfad: Path, heute: Date) -> tuple[int | None, str | None]:
    """Reine Pruefung: (Alter in Tagen oder None, Alarmgrund oder None).

    Jede Form von "kann das Alter nicht bestimmen" ist selbst ein Alarm:
    eine fehlende oder unlesbare Status-Datei heisst genauso "der Lauf
    schreibt nicht mehr" wie eine alte. Nichts davon wird still zu einem
    "wird schon passen".
    """
    if not status_pfad.exists():
        return None, (
            f"{status_pfad} existiert nicht. Entweder hat noch nie ein "
            f"Lauf geschrieben, oder die Datei wurde entfernt."
        )
    try:
        daten = json.loads(status_pfad.read_text(encoding="utf-8"))
        letzter = Date.fromisoformat(str(daten["lauf_datum"]))
    except Exception as exc:  # noqa: BLE001 - unlesbar ist unlesbar, egal wie
        return None, (
            f"{status_pfad} ist unlesbar oder traegt kein gueltiges "
            f"lauf_datum ({type(exc).__name__}: {exc})."
        )

    alter = (heute - letzter).days
    if alter > SCHWELLE_TAGE:
        return alter, (
            f"Letzter Lauf am {letzter.isoformat()} — vor {alter} "
            f"Kalendertagen. Normal sind hoechstens {SCHWELLE_TAGE} "
            f"(Wochenende plus ein bereits gemeldeter Einzel-Fehlschlag)."
        )
    return alter, None


def main(argv: list[str] | None = None, *, melder=push_lauf_ueberfaellig) -> int:
    """`melder` ist die Test-Naht -- Tests ersetzen ihn durch einen Zaehler."""
    parser = argparse.ArgumentParser(description="Totmannschalter des Momentum-Laufs")
    parser.add_argument("--heute", help="Pruefdatum JJJJ-MM-TT (nur fuer Tests)")
    parser.add_argument("--status", default=str(STATUS_PFAD), help="Pfad zur Status-Datei")
    args = parser.parse_args(argv)
    heute = Date.fromisoformat(args.heute) if args.heute else Date.today()

    alter, grund = befund(Path(args.status), heute)

    if grund is None:
        log(f"Waechter: letzter Lauf vor {alter} Tag(en) — im Rahmen, kein Push.")
        return 0

    log(f"Waechter: ALARM — {grund}")
    verschickt = melder(grund)
    log("Push verschickt." if verschickt else "Push NICHT verschickt (siehe Meldung oben).")
    # Rot enden, auch wenn der Push raus ist: der rote Waechter-Lauf in der
    # Actions-Liste ist das zweite, vom ntfy-Weg unabhaengige Signal.
    return 1


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
