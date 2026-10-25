"""Wiedervorlagen-Wächter: liest §3 ("Wiedervorlagen") von
SESSION_HANDOVER.md und meldet, wenn eine Zeile heute faellig oder
ueberfaellig ist -- Auftrag 2 der Automatisierung vom 24.10.2026.

DIE DATENQUELLE: jede Datenzeile der §3-Tabelle traegt am Ende ihrer
"Wann"-Zelle einen unsichtbaren HTML-Kommentar `<!-- faellig: JJJJ-MM-TT
-->` oder `<!-- faellig: offen -->` (Teil A desselben Auftrags, bereits
in dieser Sitzung eingetragen). Dieses Modul liest NUR diesen
Kommentar -- nie den sichtbaren Freitext der Zelle selbst, der bleibt
fuer Menschen lesbar und bewusst uneinheitlich formuliert ("25.–
31.10.2026", "ca. 10 Handelstage nach Merge von PR #74", "offen, keine
Frist" ...). Zeilen mit `faellig: offen` werden NIE gemeldet -- "offen"
heisst ausdruecklich "kein Termin".

ERLEDIGTE WIEDERVORLAGEN: dieses Modul hat KEIN eigenes Gedaechtnis
dafuer. Es liest §3 bei JEDEM Lauf frisch vom aktuellen Stand der Datei
-- wird eine Zeile erledigt und (wie in diesem PR selbst vorgemacht)
aus §3 entfernt bzw. nach §10 verschoben, verschwindet sie damit von
selbst aus der Auswertung. Kein Abgleich gegen eine fruehere Fassung
noetig oder gewollt.

ZUSTANDSLOSE FAELLIGKEITS-/ERINNERUNGS-LOGIK (Regel 2, Kriterium 7):
`status_am_tag()` ist eine REINE Funktion von (`faellig`-Datum, `heute`)
-- keine Persistenz, kein `datetime.now()` in der Entscheidungslogik
(nur an der einen Stelle, an der `main()` den Standardwert fuer `--heute`
bildet). Die Differenz in Tagen entscheidet:
  * 0 Tage      -> "Heute faellig" (immer gemeldet)
  * < 0 Tage     -> noch nicht faellig, nie gemeldet
  * > 0 Tage, Rest modulo ERINNERUNG_TAGE == 1 -> "Ueberfaellig seit N
    Tagen" (Tag 1, 8, 15, 22, ... -- die Zaehlung beginnt am ERSTEN
    ueberfaelligen Tag, nicht am Faelligkeitstag selbst, siehe Auftrag:
    "ab dem Folgetag")
  * jeder andere positive Tag -> stumm (zwischen zwei Erinnerungen)
Dieselbe Eingabe liefert deshalb IMMER dieselbe Meldung, unabhaengig
davon, wie oft oder wann dieser Wächter zuvor gelaufen ist.

HARTE GRENZE, wie bei jedem Wächter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich SESSION_HANDOVER.md und
schreibt NIRGENDS -- keine Zeile wird entfernt, kein Kommentar ergaenzt
oder geaendert, kein Commit. Abgesichert auf zwei Ebenen: das Workflow-
Token traegt nur `contents: read`, UND ein statischer Test
(tests/unit/test_wiedervorlagen_waechter.py) durchsucht diese Datei nach
jedem schreibenden Aufruf.

DIE PUSH-MECHANIK: EIN gebuendelter Push ueber `begrenze_bloecke()`, NUR
wenn mindestens eine Zeile heute faellig/faellig zur Erinnerung ist --
NIE ein "alles ok" (kein Herzschlag, siehe notify.py,
`test_kein_herzschlag_push_vorhanden`). Prioritaet "min" (lautlos), wie
`push_pr_verwaist`/`push_handover_pflege_faellig`: eine Erinnerung, kein
Alarm -- das eigentliche Nachsehen/Handeln bleibt Easys Entscheidung.
Der Lauf bleibt GRUEN (Exit 0), solange sich der Zustand ermitteln
liess. ROT (Exit 1) nur bei technischem Unvermoegen (Datei fehlt/
unlesbar, Abschnitt §3 nicht gefunden, eine Zeile ohne gueltigen
`faellig`-Kommentar) -- und dieser Fehlschlag bleibt NIE stumm (fail-
soft: Exit 1 UND ein Versuch, das selbst per Push zu melden).

FRAGILE ANNAHME, ehrlich benannt (Kriterium 6): die Datums-Zuordnung bei
Zeitfenstern ("25.–31.10.2026" -> faellig am ERSTEN Tag) und bei
Freitext-Terminen ("ca. 10 Handelstage nach Merge ...", "Herbst 2026 (ab
~Nov, ...)") ist nicht aus der Zelle selbst algorithmisch ableitbar --
genau deshalb liegt die Zuordnung ausschliesslich im separat gepflegten
`faellig`-Kommentar, von einem Menschen gesetzt, nicht von diesem Modul
hergeleitet. Zeilen ohne klares Kalenderdatum tragen bewusst
`faellig: offen`, statt dass dieses Modul ein Datum raet.

ZEITZONE: Kalendertag in UTC, nicht Berlin-Zeit. `main()` nimmt `--heute`
als reines Datum (kein Zeitstempel) -- ein Tageswechsel um Mitternacht
UTC statt um Mitternacht Berlin-Zeit kann die Meldung je nach Laufzeit-
punkt um bis zu zwei Stunden (Winterzeit) bzw. drei Stunden (Sommerzeit)
verschieben, nie um einen ganzen Tag, weil der Workflow selbst morgens
Berlin-Zeit laeuft (siehe `.github/workflows/wiedervorlagen_waechter.yml`)
-- zu einem Zeitpunkt, an dem UTC- und Berlin-Kalendertag bereits
uebereinstimmen.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

from .notify import begrenze_bloecke, push_wiedervorlage_faellig

Date = _dt.date

HANDOVER_PFAD = Path("SESSION_HANDOVER.md")
ABSCHNITT_UEBERSCHRIFT = "## 3. Wiedervorlagen"

FAELLIG_MUSTER = re.compile(r"<!--\s*faellig:\s*([^>]+?)\s*-->")
ERSTES_FETT = re.compile(r"\*\*(.+?)\*\*")

# Hoechstens eine Erinnerung je so viele Tage anhaltender Ueberfaelligkeit
# (Tag 1, 8, 15, ... -- "ab dem Folgetag", siehe Auftrag). Startwert,
# Feintuning nach ca. 10 Handelstagen Baseline.
ERINNERUNG_TAGE = 7

# Wie lang der angezeigte Kurztitel je Zeile hoechstens wird, damit eine
# Haeufung faelliger Zeilen begrenze_bloecke() nicht allein schon durch
# lange Titel sprengt.
KURZTITEL_MAX = 80


class FormatFehler(ValueError):
    """Eine Zeile in §3 hat keinen oder einen ungueltigen
    `faellig`-Kommentar."""


@dataclass(frozen=True)
class Eintrag:
    wann_sichtbar: str
    was: str
    faellig: Date | None  # None heisst "offen" -- nie gemeldet


def log(text: str) -> None:
    print(text, flush=True)


def _abschnitt_herausschneiden(text: str) -> str:
    beginn = text.find(ABSCHNITT_UEBERSCHRIFT)
    if beginn == -1:
        raise FormatFehler(f"Abschnitt {ABSCHNITT_UEBERSCHRIFT!r} nicht gefunden.")
    rest = text[beginn:]
    ende = rest.find("\n---", 1)
    return rest[:ende] if ende != -1 else rest


def _ist_datenzeile(zeile: str) -> bool:
    if not zeile.startswith("|"):
        return False
    erste_zelle = zeile.split("|", 2)[1].strip()
    return erste_zelle not in ("", "Wann") and not erste_zelle.startswith("-")


def _zellen(zeile: str) -> list[str]:
    return [z.strip() for z in zeile.strip().strip("|").split("|")]


def _faellig_parsen(roh: str, *, zeilen_nr: int) -> Date | None:
    if roh == "offen":
        return None
    try:
        return Date.fromisoformat(roh)
    except ValueError as exc:
        raise FormatFehler(
            f"Zeile {zeilen_nr}: 'faellig: {roh}' ist kein gueltiges Datum "
            f"(JJJJ-MM-TT) und nicht 'offen' ({exc})."
        ) from exc


def parse_eintraege(text: str) -> list[Eintrag]:
    """Alle Datenzeilen von §3, mit geparstem `faellig`-Kommentar.

    Wirft `FormatFehler`, sobald EINE Zeile keinen oder einen ungueltigen
    Kommentar traegt -- bewusst kompromisslos: eine stillschweigend
    uebersprungene Zeile waere eine Wiedervorlage, die nie mehr gemeldet
    werden kann, ohne dass es auffaellt.
    """
    abschnitt = _abschnitt_herausschneiden(text)
    eintraege: list[Eintrag] = []
    zeilen_nr = 0
    for zeile in abschnitt.splitlines():
        if not _ist_datenzeile(zeile):
            continue
        zeilen_nr += 1
        zellen = _zellen(zeile)
        if len(zellen) < 2:
            raise FormatFehler(f"Zeile {zeilen_nr}: weniger als zwei Spalten.")
        wann_zelle, was_zelle = zellen[0], zellen[1]
        treffer = FAELLIG_MUSTER.search(wann_zelle)
        if treffer is None:
            raise FormatFehler(
                f"Zeile {zeilen_nr} ({wann_zelle!r}): kein 'faellig'-Kommentar."
            )
        faellig = _faellig_parsen(treffer.group(1).strip(), zeilen_nr=zeilen_nr)
        wann_sichtbar = FAELLIG_MUSTER.sub("", wann_zelle).strip()
        eintraege.append(Eintrag(wann_sichtbar, was_zelle, faellig))
    return eintraege


def lies_eintraege(
    *, pfad: Path = HANDOVER_PFAD
) -> tuple[list[Eintrag] | None, str | None]:
    """(Eintraege, Fehlergrund). Genau einer der beiden ist None."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{pfad} nicht lesbar ({type(exc).__name__}: {exc})."
    try:
        return parse_eintraege(text), None
    except FormatFehler as exc:
        return None, str(exc)


def status_am_tag(
    faellig: Date, heute: Date, *, erinnerung_tage: int = ERINNERUNG_TAGE
) -> tuple[str, int] | None:
    """(Status, Tage-Differenz) oder None, wenn heute nichts zu melden
    ist -- reine Funktion, siehe Modul-Docstring."""
    diff = (heute - faellig).days
    if diff < 0:
        return None
    if diff == 0:
        return "heute_faellig", 0
    if diff % erinnerung_tage == 1:
        return "ueberfaellig", diff
    return None


def kurztitel(was: str, *, max_laenge: int = KURZTITEL_MAX) -> str:
    treffer = ERSTES_FETT.search(was)
    text = (treffer.group(1) if treffer else was).strip()
    if len(text) > max_laenge:
        text = text[: max_laenge - 1].rstrip() + "…"
    return text


def meldetext(eintrag: Eintrag, status: str, diff: int) -> str:
    titel = kurztitel(eintrag.was)
    if status == "heute_faellig":
        return f"📅 Heute fällig ({eintrag.wann_sichtbar}): {titel}"
    return (
        f"⏰ Überfällig seit {diff} Tag(en) (fällig {eintrag.faellig.isoformat()}, "
        f"{eintrag.wann_sichtbar}): {titel}"
    )


def faellige_bloecke(eintraege: list[Eintrag], heute: Date) -> list[tuple[str, str]]:
    """(Kurztitel, Meldetext) je Zeile, die heute gemeldet werden muss --
    `offen`-Zeilen werden NIE beruecksichtigt."""
    bloecke: list[tuple[str, str]] = []
    for eintrag in eintraege:
        if eintrag.faellig is None:
            continue
        ergebnis = status_am_tag(eintrag.faellig, heute)
        if ergebnis is None:
            continue
        status, diff = ergebnis
        bloecke.append((kurztitel(eintrag.was), meldetext(eintrag, status, diff)))
    return bloecke


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie bei jedem anderen Wächter dieses Projekts."""
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
    melder=push_wiedervorlage_faellig,
    ermittle_eintraege=lies_eintraege,
) -> int:
    """`melder`/`ermittle_eintraege` sind die Test-Naehte, wie bei jedem
    anderen Wächter dieses Projekts."""
    parser = argparse.ArgumentParser(description="Wiedervorlagen-Wächter")
    parser.add_argument("--heute", help="Pruefdatum JJJJ-MM-TT (nur fuer Tests)")
    args = parser.parse_args(argv)
    heute = Date.fromisoformat(args.heute) if args.heute else Date.today()

    eintraege, grund = ermittle_eintraege()
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte §3 (Wiedervorlagen) nicht lesen: {grund}")
        return 1

    bloecke = faellige_bloecke(eintraege, heute)
    if not bloecke:
        log(f"Waechter: keine faellige Wiedervorlage am {heute.isoformat()} — still.")
        return 0

    log(f"Waechter: {len(bloecke)} faellige Wiedervorlage(n) — " + "; ".join(n for n, _ in bloecke))
    text = begrenze_bloecke(bloecke)
    _melden(melder, text)
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
