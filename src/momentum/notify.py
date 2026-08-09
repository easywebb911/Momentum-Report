"""Push ueber ntfy.

Drei Ereignisse, von Tag 1 an ehrlich getrennt (die Trennung selbst
passiert im Workflow, hier stehen nur die Formulierungen):

  1. NEUES MONATS-RANKING  -- der eigentliche Zweck des Werkzeugs
  2. LAUF-FEHLSCHLAG       -- und zwar unterschieden in:
       a) "Daten-Push-Konflikt — Analyse lief fehlerfrei"
          nur der Commit-Schritt ist rot, Prioritaet default, keine Sirene
       b) "Lauf fehlgeschlagen"
          die Analyse selbst ist rot, Prioritaet high, mit Sirene

  3. VERDRAHTUNGSPROBE     -- "Momentum: Push-Verdrahtung ok", leise.
       Kommt AUSSCHLIESSLICH auf ausdrueckliche Anforderung ueber das
       Feld "testpush" des Workflows.

Kein Herzschlag-Push in dieser Fassung: es gibt keinen Zeitplan und
keine Bedingung, unter der von selbst ein "alles ok" kaeme. Die Probe
oben ist keine Ausnahme davon -- sie kommt nur, wenn jemand sie anfordert.

ALLE DREI gehen durch dasselbe push(). Einen zweiten Sendeweg gibt es
nicht, und das ist der Punkt: eine Probe, die ihren eigenen Weg nimmt,
prueft nicht den Weg, auf den es ankommt.

Fehlt NTFY_TOPIC, wird NICHT still zurueckgefallen: die fehlende
Einstellung erscheint als deutliche Zeile im Lauf-Log und als
GitHub-Warnung im Schritt-Protokoll.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request

NTFY_BASE = os.environ.get("NTFY_BASE", "https://ntfy.sh")
TIMEOUT_SECONDS = 20

# Was ntfy als Thema akzeptiert. Alles andere lehnt die JSON-Schnittstelle
# mit HTTP 400 "topic invalid" ab -- und zwar BEVOR irgendetwas zugestellt
# wird. Genau das ist am 02.08.2026 passiert: im Secret steckte ein
# unsichtbarer Rest vom Kopieren.
#
# \A und \Z statt ^ und $, und das ist hier KEINE Kosmetik: Pythons $ passt
# auch VOR einem abschliessenden Zeilenumbruch. Mit ^...$ haette
# "thema\n" als gueltig gegolten -- ausgerechnet der Fall, um den es geht.
TOPIC_MUSTER = re.compile(r"\A[-_A-Za-z0-9]{1,64}\Z")
TOPIC_MAX = 64

# Wie viel vom Antwortkoerper des Servers ins Protokoll darf.
FEHLERTEXT_MAX = 500

# ntfy-Prioritaeten: 3 = normal, 4 = hoch (loest auf dem iPhone die
# auffaellige Zustellung aus). Mehr braucht dieses Werkzeug nicht.
PRIORITIES = {"default": 3, "high": 4}

MISSING_TOPIC_BANNER = (
    "PUSH NICHT VERSCHICKT: Das Repository-Secret NTFY_TOPIC ist nicht "
    "gesetzt. Die Analyse ist davon unberuehrt gelaufen. Ohne dieses Secret "
    "gibt es KEINE Benachrichtigungen — weder fuer ein neues Monats-Ranking "
    "noch fuer einen Fehlschlag."
)


def _loud(message: str, *, titel: str = "NTFY_TOPIC fehlt", art: str = "warning") -> None:
    """Immer sichtbar: im Log UND als GitHub-Annotation."""
    bar = "=" * 72
    print(f"\n{bar}\n{message}\n{bar}\n", file=sys.stderr, flush=True)
    if os.environ.get("GITHUB_ACTIONS"):
        einzeilig = " ".join(message.split())
        print(f"::{art} title={titel}::{einzeilig}", flush=True)


# Unsichtbare Zeichen beim Namen nennen -- das sind die Faelle, die man
# sonst stundenlang sucht, weil man sie im Secret-Feld schlicht nicht sieht.
_UNSICHTBAR = {
    " ": "ein Leerzeichen",
    "\n": "ein Zeilenumbruch",
    "\r": "ein Wagenruecklauf",
    "\t": "ein Tabulator",
    "\v": "ein Vertikaltabulator",
    "\f": "ein Seitenvorschub",
    " ": "ein geschuetztes Leerzeichen (U+00A0)",
    "​": "ein Zeichen ohne Breite (U+200B)",
    "‌": "ein Zeichen ohne Breite (U+200C)",
    "‍": "ein Zeichen ohne Breite (U+200D)",
    "﻿": "eine Byte-Order-Mark (U+FEFF)",
}

_KATEGORIEN = {
    "Z": "ein Leerraum-Zeichen",
    "C": "ein unsichtbares Steuerzeichen",
    "P": "ein Satzzeichen",
    "S": "ein Symbol",
    "L": "ein Buchstabe ausserhalb A-Z",
    "N": "eine Ziffer ausserhalb 0-9",
    "M": "ein kombinierendes Zeichen",
}


def _zeichen_beschreiben(zeichen: str) -> str:
    """Ein verbotenes Zeichen benennen, OHNE es auszugeben.

    Unsichtbare Zeichen bekommen ihren Codepunkt genannt -- sie sind der
    haeufige Fall und tragen nichts vom Geheimnis. Sichtbare Zeichen werden
    nur ihrer Art nach beschrieben: der Hinweis reicht zum Finden, und das
    Thema selbst bleibt vollstaendig im Dunkeln.
    """
    if zeichen in _UNSICHTBAR:
        return _UNSICHTBAR[zeichen]
    kategorie = unicodedata.category(zeichen)
    if kategorie[0] in ("Z", "C"):
        return f"{_KATEGORIEN[kategorie[0]]} (U+{ord(zeichen):04X})"
    return _KATEGORIEN.get(kategorie[0], "ein unerlaubtes Zeichen")


def pruefe_topic(topic: str) -> str | None:
    """Das Thema pruefen. None = in Ordnung, sonst die Diagnose im Klartext.

    Die Diagnose enthaelt NIE das Thema selbst -- nur seine Laenge und
    Position und Art des ersten unerlaubten Zeichens. Ein Secret gehoert
    nicht ins Lauf-Protokoll, auch nicht bruchstueckweise.
    """
    if TOPIC_MUSTER.match(topic):
        return None
    for stelle, zeichen in enumerate(topic, start=1):
        if not re.match(r"[-_A-Za-z0-9]", zeichen):
            return (
                f"NTFY_TOPIC ungueltig: Zeichen an Position {stelle} ist "
                f"{_zeichen_beschreiben(zeichen)}. Laenge des Wertes: "
                f"{len(topic)} Zeichen. Erlaubt sind nur Buchstaben A-Z/a-z, "
                f"Ziffern, Bindestrich und Unterstrich (1 bis {TOPIC_MAX} "
                f"Zeichen). Haeufigste Ursache: ein Rest vom Kopieren am Ende "
                f"des Secrets. Abhilfe: Settings -> Secrets and variables -> "
                f"Actions -> NTFY_TOPIC neu setzen, ohne Leerzeichen und ohne "
                f"Zeilenumbruch."
            )
    # Alle Zeichen erlaubt -- dann kann es nur an der Laenge liegen.
    return (
        f"NTFY_TOPIC ungueltig: Der Wert ist {len(topic)} Zeichen lang, "
        f"erlaubt sind 1 bis {TOPIC_MAX}. Es wurde NICHTS verschickt."
    )


def _lies(antwort) -> bytes:
    """Den Koerper einer Antwort holen, ohne daran zu scheitern."""
    try:
        return antwort.read() or b""
    except Exception:  # noqa: BLE001 - ein unlesbarer Koerper darf nichts kippen
        return b""


def _antworttext(rohdaten: bytes, topic: str) -> str:
    """Den Antwortkoerper lesbar machen -- und das Thema darin schwaerzen.

    ntfy antwortet auf Fehler mit JSON wie
    {"code":40009,"http":400,"error":"invalid request: topic invalid"}.
    Der Grund steht also im Koerper; nur "HTTP 400" war zu stumm.
    """
    text = rohdaten.decode("utf-8", "replace").strip()
    try:
        daten = json.loads(text)
    except (ValueError, TypeError):
        daten = None
    if isinstance(daten, dict) and daten.get("error"):
        text = f"{daten['error']} (code {daten.get('code', '?')})"
    if topic:
        text = text.replace(topic, "<topic>")
    if len(text) > FEHLERTEXT_MAX:
        text = text[:FEHLERTEXT_MAX] + " …"
    return text or "(leere Antwort)"


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
    # .strip() auf BEIDEN Wegen: ein Secret-Feld nimmt beim Einfuegen gern
    # einen Zeilenumbruch mit, und der ist im Formular nicht zu sehen.
    roh = topic if topic is not None else os.environ.get("NTFY_TOPIC", "")
    topic = roh.strip()
    if not topic:
        _loud(MISSING_TOPIC_BANNER)
        return False

    # Erst pruefen, dann senden. Ein ungueltiges Thema wuerde ntfy ohnehin
    # mit HTTP 400 ablehnen -- dann aber erst nach dem Absenden und mit
    # einer Meldung, die nicht sagt, WAS am Thema falsch ist.
    diagnose = pruefe_topic(topic)
    if diagnose is not None:
        _loud(diagnose, titel="NTFY_TOPIC ungueltig", art="error")
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
            status = getattr(response, "status", 200)
            ok = 200 <= status < 300
            koerper = b"" if ok else _lies(response)
    except urllib.error.HTTPError as exc:
        # DER Fall, der zaehlt: urlopen wirft bei 4xx/5xx. Der Grund steht
        # im Koerper der Antwort -- ohne ihn stand frueher nur "HTTP 400"
        # im Protokoll, und das half niemandem weiter.
        print(
            f"ntfy hat den Push abgelehnt: HTTP {exc.code} — "
            f"{_antworttext(_lies(exc), topic)}",
            file=sys.stderr,
            flush=True,
        )
        return False
    except (urllib.error.URLError, OSError) as exc:
        print(f"ntfy nicht erreichbar: {exc}", file=sys.stderr, flush=True)
        return False
    if not ok:
        print(
            f"ntfy hat den Push abgelehnt: HTTP {status} — "
            f"{_antworttext(koerper, topic)}",
            file=sys.stderr,
            flush=True,
        )
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


def push_lauf_ueberfaellig(grund: str, **kwargs) -> bool:
    """Push (4): der Totmannschalter hat angeschlagen (siehe waechter.py).

    Das ist die EINE Nachricht, die kein Lauf je selbst schicken kann:
    sie sagt, dass der Lauf gar nicht mehr stattfindet. Deshalb kommt sie
    aus einem eigenen, unabhaengigen Workflow -- und deshalb mit Sirene:
    ohne diesen Push wuerde der Stillstand erst auffallen, wenn jemand
    zufaellig auf die Seite schaut.
    """
    return push(
        "Momentum-Lauf ueberfaellig",
        (
            "Der werktaegliche Momentum-Lauf hat laenger nicht geschrieben "
            "als jede normale Luecke erklaert.\n\n"
            f"{grund}\n\n"
            "Die Seite friert derweil auf dem letzten guten Stand ein. "
            "Nachsehen: Actions -> Momentum-Lauf (laeuft der Zeitplan "
            "noch? Ist der Workflow deaktiviert?)."
        ),
        priority="high",
        tags="rotating_light",
        **kwargs,
    )


def push_vertrag_gebrochen(bericht: str, **kwargs) -> bool:
    """Push (5): mindestens eine Fremdquelle haelt ihre Form nicht mehr.

    EIN Push mit allen Bruechen als Liste, nicht einer je Bruch: verhagelt
    ein Anbieter mehrere Dateien gleichzeitig, ist das EIN Ereignis. Ein
    Push-Gewitter wuerde nur dazu erziehen, sie wegzuwischen.

    Prioritaet bewusst "default", nicht "high": Es ist noch nichts kaputt.
    Es ist eine Ankuendigung mit Vorlauf -- genau dafuer laeuft der Test
    im Fenster vor dem Stichtag und nicht an ihm.
    """
    return push(
        "Vertragstest: Fremdquelle haelt ihre Form nicht mehr",
        bericht,
        priority="default",
        tags="warning",
        **kwargs,
    )


def push_test(**kwargs) -> bool:
    """Push (3): Verdrahtungsprobe. Leise, ohne jede Aussage ueber Kurse.

    Sie geht durch DENSELBEN push() wie jeder echte Push -- gleiche
    Schnittstelle, gleiche Thema-Pruefung, gleiche Fehlerbehandlung. Ein
    eigener Sendeweg waere wertlos: er wuerde beweisen, dass der EIGENE
    Sendeweg funktioniert, und genau das ist nicht die Frage.

    Ausgeloest wird sie ausschliesslich von Hand ueber das Eingabefeld
    "testpush" des Workflows. Es gibt keinen Zeitplan und keine Bedingung,
    unter der sie von selbst kaeme -- ein Herzschlag-Push ist das also
    ausdruecklich nicht.
    """
    return push(
        "Momentum: Push-Verdrahtung ok",
        (
            "Diese Nachricht ist eine Probe. Sie wurde von Hand ueber das "
            "Feld 'testpush' des Momentum-Laufs ausgeloest und sagt NICHTS "
            "ueber Kurse, Ranking oder Marktlage.\n\n"
            "Kommt sie an, ist die Kette Lauf -> ntfy -> Geraet in Ordnung."
        ),
        priority="default",
        tags="white_check_mark",
        **kwargs,
    )
