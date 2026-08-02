"""Push ueber ntfy.

Zwei Ereignisse, von Tag 1 an ehrlich getrennt (die Trennung selbst
passiert im Workflow, hier stehen nur die Formulierungen):

  1. NEUES MONATS-RANKING  -- der eigentliche Zweck des Werkzeugs
  2. LAUF-FEHLSCHLAG       -- und zwar unterschieden in:
       a) "Daten-Push-Konflikt — Analyse lief fehlerfrei"
          nur der Commit-Schritt ist rot, Prioritaet default, keine Sirene
       b) "Lauf fehlgeschlagen"
          die Analyse selbst ist rot, Prioritaet high, mit Sirene

Kein Herzschlag-Push in dieser Fassung.

Fehlt NTFY_TOPIC, wird NICHT still zurueckgefallen: die fehlende
Einstellung erscheint als deutliche Zeile im Lauf-Log und als
GitHub-Warnung im Schritt-Protokoll.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

NTFY_BASE = os.environ.get("NTFY_BASE", "https://ntfy.sh")
TIMEOUT_SECONDS = 20

# ntfy-Prioritaeten: 3 = normal, 4 = hoch (loest auf dem iPhone die
# auffaellige Zustellung aus). Mehr braucht dieses Werkzeug nicht.
PRIORITIES = {"default": 3, "high": 4}

MISSING_TOPIC_BANNER = (
    "PUSH NICHT VERSCHICKT: Das Repository-Secret NTFY_TOPIC ist nicht "
    "gesetzt. Die Analyse ist davon unberuehrt gelaufen. Ohne dieses Secret "
    "gibt es KEINE Benachrichtigungen — weder fuer ein neues Monats-Ranking "
    "noch fuer einen Fehlschlag."
)


def _loud(message: str) -> None:
    """Immer sichtbar: im Log UND als GitHub-Annotation."""
    bar = "=" * 72
    print(f"\n{bar}\n{message}\n{bar}\n", file=sys.stderr, flush=True)
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::warning title=NTFY_TOPIC fehlt::{message}", flush=True)


def push(
    title: str,
    body: str,
    *,
    priority: str = "default",
    tags: str = "",
    topic: str | None = None,
    opener=urllib.request.urlopen,
) -> bool:
    """Eine Nachricht schicken. True nur bei tatsaechlich verschicktem Push."""
    topic = topic if topic is not None else os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        _loud(MISSING_TOPIC_BANNER)
        return False

    # Bewusst die JSON-Schnittstelle statt der Header-Schnittstelle:
    # HTTP-Kopfzeilen sind auf Latin-1 begrenzt, und die Titel enthalten
    # Gedankenstriche und Umlaute. Ueber JSON bleibt alles sauber UTF-8.
    payload = {
        "topic": topic,
        "title": title,
        "message": body,
        "priority": PRIORITIES[priority],
    }
    if tags:
        payload["tags"] = [t for t in tags.split(",") if t]
    request = urllib.request.Request(
        NTFY_BASE.rstrip("/"),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            ok = 200 <= getattr(response, "status", 200) < 300
    except (urllib.error.URLError, OSError) as exc:
        print(f"ntfy nicht erreichbar: {exc}", file=sys.stderr, flush=True)
        return False
    if not ok:
        print("ntfy hat den Push abgelehnt.", file=sys.stderr, flush=True)
    return ok


def push_new_ranking(entries: list[dict], **kwargs) -> bool:
    """Push (1): neues Monats-Ranking, mit Top-Titel je Markt.

    entries: [{"markt": "USA", "stichtag": "2026-07-31", "top": "NVDA",
               "top_name": "NVIDIA", "score": 100.0}, ...]
    """
    if not entries:
        return False
    stichtag = entries[0]["stichtag"]
    lines = [f"Neues Monats-Ranking, Stichtag {stichtag}.", ""]
    for entry in entries:
        lines.append(
            f"{entry['markt']}: {entry['top']} — {entry['top_name']} "
            f"(Score {entry['score']:.1f})"
        )
    lines += [
        "",
        "Rangfolge bleibt bis zum naechsten Stichtag eingefroren.",
        "Keine Einzelaktien-Prognose — Portfolio-Statistik.",
    ]
    return push(
        "Momentum-Report: neues Monats-Ranking",
        "\n".join(lines),
        priority="default",
        tags="chart_with_upwards_trend",
        **kwargs,
    )


def push_data_conflict(detail: str, **kwargs) -> bool:
    """Push (2a): nur der Commit-Schritt ist rot. Ohne Sirene."""
    return push(
        "Daten-Push-Konflikt — Analyse lief fehlerfrei",
        (
            "Die Analyse ist vollstaendig und fehlerfrei durchgelaufen. "
            "Nur das Zurueckschreiben der Ergebnisse ins Repository hat nicht "
            "geklappt.\n\n"
            f"{detail}\n\n"
            "Die Seite zeigt weiterhin den letzten erfolgreich "
            "geschriebenen Stand. Der naechste Lauf schreibt erneut."
        ),
        priority="default",
        tags="arrows_counterclockwise",
        **kwargs,
    )


def push_run_failed(detail: str, **kwargs) -> bool:
    """Push (2b): die Analyse selbst ist rot. Mit Sirene, hohe Prioritaet."""
    return push(
        "Lauf fehlgeschlagen",
        (
            "Der Momentum-Lauf ist NICHT durchgelaufen. Es wurde bewusst "
            "nichts veroeffentlicht — lieber kein Stand als ein falscher.\n\n"
            f"{detail}"
        ),
        priority="high",
        tags="rotating_light",
        **kwargs,
    )


def summary_line(payload: dict) -> str:
    """Kompakte Zeile fuer das Lauf-Protokoll."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
