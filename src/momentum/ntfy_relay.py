"""ntfy-Relay: eine bewusst DUeNNE Weiterleitung von Text zu
`notify.push()`, ausgeloest NUR per Hand (`workflow_dispatch`) — damit
spaetere geplante Agenten (Auftrag 5 der Automatisierung vom 24.10.2026)
Easy benachrichtigen koennen, OHNE das ntfy-Topic selbst zu kennen oder
eine zweite Versand-Implementierung zu brauchen.

KEINE ZWEITE NTFY-IMPLEMENTIERUNG (Auftrag, Regel 3): dieses Modul ruft
`notify.push()` direkt auf -- dieselbe JSON-Schnittstelle, dieselbe
Themen-Pruefung, dieselbe Fehlerbehandlung wie jeder andere Push dieses
Projekts. Es gibt bewusst KEINE eigene `push_relay_xxx`-Huelle in
notify.py: anders als jede bestehende `push_*`-Funktion (siehe
notify.py, `test_kein_herzschlag_push_vorhanden`) trägt dieser Aufruf
einen vom AUFRUFER frei gewaehlten Titel, keinen festen -- er passt
damit nicht in die geschlossene Menge der Herzschlag-Pruefung und
wuerde sie nur verwaessern.

INJEKTION, WARUM SIE HIER STRUKTURELL AUSGESCHLOSSEN IST (Regel 2): kein
`${{ inputs.* }}` steht in `.github/workflows/ntfy_relay.yml` jemals
direkt in einer `run:`-Zeile -- jeder Eingabewert laeuft NUR ueber
`env:` (siehe Workflow-Datei), und dieses Skript liest sie als
gewoehnliche Umgebungsvariablen (`RELAY_TITLE`/`RELAY_MESSAGE`/
`RELAY_TAGS`/`RELAY_PRIORITY`). Dieses Skript selbst ruft an KEINER
Stelle eine Shell, `subprocess`, `eval` oder `exec` auf einen
Eingabewert auf -- ein Text wie `$(whoami)` oder ein Backtick-Ausdruck
bleibt reine Zeichenkette, die als JSON-Feld `message` an ntfy geht,
niemals als Befehl ausgefuehrt. Ein statischer Test
(tests/unit/test_ntfy_relay.py) prueft BEIDES: die Workflow-Datei auf
das verbotene Muster, UND dieses Modul auf jeden schreibenden/
ausfuehrenden Aufruf.

HEADER-BEREINIGUNG (Regel 4): Titel und Tags laufen durch
`bereinige_kopf()` -- Zeilenumbrueche/Tabulatoren werden zu Leerzeichen,
jedes andere Unicode-Steuerzeichen (Kategorie "C*") faellt ganz weg,
mehrfache Leerzeichen werden zusammengefasst. Umlaute und Satzzeichen
bleiben unangetastet: `push()` sendet ueber die JSON-Schnittstelle, NIE
ueber HTTP-Kopfzeilen (siehe notify.py, `push()`-Docstring,
"Latin-1 begrenzt") -- es gibt deshalb KEIN Kodierungsrisiko fuer
Umlaute im Titel, anders als bei einer Header-basierten ntfy-Anbindung.
Der Nachrichtentext selbst laeuft durch `begrenze_bloecke()` (dieselbe
2.000-Zeichen-Haertung wie bei jedem anderen laengeren Push dieses
Projekts, siehe notify.py, NACHRICHT_BLOCK_GRENZE).

PRIORITAET, WIDERSPRUCH GEMELDET STATT STILL UEBERGANGEN (Kriterium 2):
der Auftrag verlangt die Wahl "min/low/default/high" als Workflow-
Eingabe -- `notify.PRIORITIES` kannte "low" bisher nicht (ein Aufruf mit
`priority="low"` haette `push()` mit einem KeyError abbrechen lassen,
VOR jeder Versand-Pruefung). Behoben direkt in notify.py (additiv,
`"low": 2`, an der von ntfy selbst vorgesehenen Stelle zwischen "min"
und "default") -- kein bestehender Aufrufer uebergibt "low", also
aendert sich an keinem vorhandenen Push dieses Projekts etwas.

FEHLERBEHANDLUNG, NICHT STUMM (Regel 5): ein leerer Titel/leere
Nachricht NACH der Bereinigung oder eine unbekannte Prioritaet ist ein
KLARER Fehler im Log, OHNE jeden Versandversuch -- kein Rateschlag, kein
Ersatztext. Scheitert der Versand selbst (ntfy lehnt ab, ntfy nicht
erreichbar, `push()` liefert `False`): Exit 1, DAMIT der Push-
Zustellungs-Wächter (`push_zustellung_waechter.py`, der nach dem
woertlichen `FEHLSCHLAG_ANKERTEXT` in den Actions-Logs sucht) diesen
Lauf unter den ueberwachten Workflows mitzaehlt.

DETERMINISMUS (Kriterium 7): bei gleichen Eingaben (Umgebungsvariablen)
entsteht immer exakt derselbe Titel/Tags/Body -- keine Zeitstempel,
keine Zufallsanteile. Dieses Modul greift an keiner Stelle auf
`datetime.now()` zu.
"""

from __future__ import annotations

import os
import unicodedata

from .notify import PRIORITIES, begrenze_bloecke, push

STANDARD_PRIORITAET = "default"


def log(text: str) -> None:
    print(text, flush=True)


def bereinige_kopf(text: str) -> str:
    """Zeilenumbrueche/Tabulatoren werden zu Leerzeichen, jedes andere
    Unicode-Steuerzeichen (Kategorie "C*", z. B. NUL, Escape) faellt ganz
    weg, mehrfache/fuehrende/abschliessende Leerzeichen werden
    zusammengefasst. Umlaute, Satzzeichen, Emoji bleiben unangetastet --
    das ist NICHT dieselbe Pruefung wie `pruefe_topic()` (die ist fuer
    das streng eingeschraenkte ntfy-Thema gedacht, nicht fuer frei
    lesbaren Text)."""
    ohne_zeilenumbrueche = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    ohne_steuerzeichen = "".join(
        zeichen for zeichen in ohne_zeilenumbrueche if unicodedata.category(zeichen)[0] != "C"
    )
    return " ".join(ohne_steuerzeichen.split())


def main(*, umgebung: dict | None = None, pusher=push, log=log) -> int:
    """`umgebung`/`pusher` sind die Test-Naehte. `umgebung` ersetzt
    `os.environ` komplett (kein Zugriff auf echte Umgebungsvariablen in
    Tests); `pusher` ersetzt `notify.push()` (kein echtes ntfy/Netz)."""
    umgebung = umgebung if umgebung is not None else os.environ

    titel = bereinige_kopf(umgebung.get("RELAY_TITLE", ""))
    nachricht = umgebung.get("RELAY_MESSAGE", "").strip()
    tags = bereinige_kopf(umgebung.get("RELAY_TAGS", ""))
    prioritaet = umgebung.get("RELAY_PRIORITY", STANDARD_PRIORITAET) or STANDARD_PRIORITAET

    if not titel:
        log("ntfy-Relay: Fehler — Titel ist leer (nach Bereinigung). Kein Versand.")
        return 1
    if not nachricht:
        log("ntfy-Relay: Fehler — Nachricht ist leer. Kein Versand.")
        return 1
    if prioritaet not in PRIORITIES:
        log(
            f"ntfy-Relay: Fehler — unbekannte Prioritaet {prioritaet!r}. "
            f"Erlaubt: {', '.join(sorted(PRIORITIES, key=PRIORITIES.get))}. Kein Versand."
        )
        return 1

    body = begrenze_bloecke([("Nachricht", nachricht)])

    try:
        verschickt = pusher(titel, body, priority=prioritaet, tags=tags)
    except Exception as exc:  # noqa: BLE001 - jeder Fehlschlag muss den Lauf rot machen
        log(f"ntfy-Relay: Versand fehlgeschlagen ({type(exc).__name__}: {exc}).")
        return 1

    if not verschickt:
        log("ntfy-Relay: Push NICHT verschickt (siehe Meldung oben).")
        return 1

    log("ntfy-Relay: Push verschickt.")
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
