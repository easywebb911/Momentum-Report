"""Statische Seiten neu erzeugen, ohne Kursdaten und ohne Netz.

Aufruf:  python -m momentum.build_pages
Erzeugt: docs/methodik.html  (aus sources.SOURCES — daher immer deckungs-
gleich mit den Belegen im Code)
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from .render import render_evaluation, render_index, render_konfluenz, render_methodik

DOCS_DIR = Path("docs")


def main() -> int:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ziel = DOCS_DIR / "methodik.html"
    ziel.write_text(render_methodik(), encoding="utf-8")
    print(f"geschrieben: {ziel}")

    # Die Konfluenz-Seite ist ein statisches Geruest ohne Lauf-Daten --
    # sie wird wie die Methodik immer neu erzeugt.
    konf = DOCS_DIR / "konfluenz.html"
    konf.write_text(render_konfluenz(), encoding="utf-8")
    print(f"geschrieben: {konf}")

    # Startseite nur anlegen, wenn es noch keine gibt: eine vorhandene
    # Seite traegt echte Ranking-Daten und darf hier nicht ueberbuegelt
    # werden.
    start = DOCS_DIR / "index.html"
    if not start.exists():
        start.write_text(render_index([], _dt.date.today()), encoding="utf-8")
        print(f"geschrieben: {start} (Platzhalter, noch kein Ranking)")

    # Dasselbe fuer die Evaluations-Seite: sie traegt echte Monats-
    # Rueckblicke aus data/evaluation/ und darf hier nicht ueberbuegelt
    # werden. Ohne vorhandene Datei entsteht der Leerzustand.
    eval_seite = DOCS_DIR / "evaluation.html"
    if not eval_seite.exists():
        eval_seite.write_text(render_evaluation({}), encoding="utf-8")
        print(f"geschrieben: {eval_seite} (Platzhalter, noch keine Rueckblicke)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
