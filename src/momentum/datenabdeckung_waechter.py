"""Daten-Abdeckungs-Wächter: liest AUSSCHLIESSLICH bereits geschriebene
Artefakte (die Git-Historie von data/status.json und der Ticker-Meta-
Dateien, plus den aktuellen Stand der Universum-Dateien) -- NIE run.py's
LAUFENDE Ausfuehrung selbst. Sechstes/siebtes Modul nach demselben
Grundmuster wie die anderen Waechter dieses Projekts, auf drei neue
Symptome angewandt: eine Fremdquelle, die ohne Fehler antwortet, aber
LEER bleibt, faellt heute NIEMANDEM auf, der nicht gezielt misst.

DREI PRUEFUNGEN, nicht mehr (bewusst eng gehalten, Auftrag):

  A) KURSABRUF (yfinance): aus der Historie von data/status.json (je
     Markt, Feld "daten") erkennen, ob in ALLEN Laeufen eines Fensters
     KEINE oder PRAKTISCH KEINE Kursdaten ankamen.
  B) ISHARES-KURSVERGLEICH: aus derselben Historie (Feld "kursvergleich")
     erkennen, ob in ALLEN Laeufen eines Fensters das Verdikt "entfallen"
     oder "verweigert" war.
  C) UNIVERSUM-ALTER UND SEKTOR-ABDECKUNG: der "# Stand:"-Kopf der
     Universum-Dateien gegen heute, UND der Anteil der Ticker ohne
     Sektor in den Ticker-Meta-Dateien.

AUSDRUECKLICH NICHT TEIL DIESES MODULS: die Elliott-Quelle (braucht einen
Zaehler in run.py -- Folgeauftrag nach dem Stichtag 30.10.2026) und alles
weitere aus der frueheren Bestandsaufnahme.

DIE DATENQUELLE, WARUM GIT UND NICHT DIE LIVE-AUSFUEHRUNG: data/
status.json wird JEDEN Lauf ueberschrieben (siehe lauf.yml, "Ergebnisse
zurueckschreiben") -- die Git-Historie DIESER EINEN Datei ist bereits
das vollstaendige Protokoll aller vergangenen Laeufe, ohne dass dieses
Modul run.py selbst anstossen oder dessen Zustand live abfragen muesste.
EIN Commit, der status.json beruehrt, ENTSPRICHT genau einem Lauf (siehe
lauf.yml: "git add -A data docs" + ein Commit je Lauf, niemals mehrere).

DATENLAGE, EMPIRISCH BELEGT (Kriterium 4, hier nachgemessen statt
angenommen -- Sitzung vom 25.10.2026, echtes Repository):

  * 55 Commits beruehren data/status.json, SIE laufen Werktags (Mo-Fr)
    einmal taeglich -- siehe lauf.yml, `cron: "45 21 * * 1-5"`. Keine
    Wochenend-Laeufe, kein Hinweis auf mehrere Laeufe am selben Tag im
    beobachteten Zeitraum.
  * Das Feld "kursvergleich" steht NUR dann im Status (siehe run.py,
    `if needed:`-Zweig -- ein Stichtags-Lauf), wenn fuer den jeweiligen
    Markt ein noch offener faelliger Monat existiert. In der gesamten
    beobachteten Historie kam das GENAU ZWEIMAL vor: 2026-08-31
    (Verdikt "ok"/"ok") und 2026-10-01 (Verdikt "entfallen"/"entfallen").
    WIDERSPRUCH GEMELDET statt stillschweigend uebergangen (Kriterium 2):
    die urspruengliche Annahme dieses Moduls war ein haeufigerer,
    mehrtaegiger Wiederholungsversuch rund um den Stichtag (siehe
    lauf.yml-Kommentar zu Lauf 48, 31.08.2026, "zu_frueh_fuer_stichtag") --
    tatsaechlich beobachtet wurde bislang je Monatsgrenze nur EIN
    einzelner Treffer. Das 7-Tage-Fenster von Pruefung B wird unter
    dieser Kadenz im Normalfall 0 oder 1 Treffer sehen, NIE mehrere --
    und MINDEST_BEOBACHTUNGEN (siehe unten) verlangt mindestens zwei.
    FOLGE, EHRLICH BENANNT: Pruefung B wird unter der heutigen Kadenz
    nahezu nie ausloesen -- nur dann, wenn tatsaechlich mehrere
    Stichtags-Versuche innerhalb von sieben Tagen aufeinanderfolgen
    (z. B. ein durch "zu_frueh_fuer_stichtag" verschobener Nachlauf).
    Das ist kein verstecktes Versagen dieses Moduls, sondern eine
    Eigenschaft der realen Lauf-Kadenz -- hier dokumentiert, damit der
    erste echte Alarm (oder dessen Ausbleiben) niemanden ueberrascht.
  * Sowohl universe/universe_us.txt als auch universe/universe_de.txt
    tragen "# Stand: 2026-08-03" und wurden seither nicht erneut gebaut
    (ein einziger Commit je Datei, 2026-08-18). Kein Hinweis auf eine
    automatische Rebuild-Kadenz -- `tools/build_universe.py` ist ein von
    Hand angestossenes Werkzeug.
  * universe/ticker_meta_us.json (503 Ticker) und ticker_meta_de.json
    (102 Ticker) haben HEUTE beide null fehlende Sektoren.
  * Alle Commit-Zeitstempel (`%cI`) liegen bereits in UTC (Actions-
    Runner) -- keine Zeitzonen-Umrechnung noetig.

WARUM EIN NEUER SCHWELLENWERT FUER DIE UNIVERSUM-FRISCHE, NICHT
MAX_ALTER_HANDELSTAGE (Kriterium 4/6): MAX_ALTER_HANDELSTAGE (10
Handelstage, siehe ishares.py) misst, ob eine INTRADAY ABGERUFENE
iShares-Bestandsliste noch taufrisch genug fuer den Kursvergleich EINES
Laufs ist -- eine Groessenordnung von TAGEN fuer eine Datei, die mehrmals
woechentlich neu abgerufen wird. Die Universum-Dateien dagegen werden nur
von Hand neu gebaut (keine beobachtete automatische Kadenz) und sollen
Index-Umschichtungen/Wikipedia-Spaltenumbenennungen einfangen, nicht
taegliche Frische -- eine voellig andere Groessenordnung. Direkt
uebernommen waere MAX_ALTER_HANDELSTAGE hier witzlos (die Universum-
Dateien sind bereits seit ihrem einzigen Commit 10 Handelstage alt).
UNIVERSUM_WARNSCHWELLE_TAGE = 180 (Kalendertage, nicht Handelstage) ist
deshalb EIN EIGENER, selbst festgelegter Wert, hier begruendet: S&P-500-
Umschichtungen folgen ueblicherweise einem vierteljaehrlichen Rhythmus;
180 Tage lassen zwei solche Zyklen verstreichen, bevor gewarnt wird --
grosszuegig genug, um den noch nie beobachteten Rebuild-Rhythmus dieses
Projekts nicht faelschlich zu alarmieren (heutiger Stand: 83 Kalendertage
alt, WEIT unter der Schwelle), aber nicht so grosszuegig, dass eine
jahrealte Liste unbemerkt bliebe.

STATUS-GRENZE, ehrlich benannt (Kriterium 6): keiner der Commits in der
beobachteten Historie zeigt ein `markt`-Eintrag ganz ohne "daten" (z. B.
ein fruehzeitig abgebrochener Lauf) -- dieses Modul behandelt einen
solchen Eintrag konservativ als "nicht auswertbar" fuer DIESEN einen
Lauf (siehe kursabruf_warnung_zum_zeitpunkt), statt ihn als Fund zu
werten oder den ganzen Lauf abzulehnen.

ZUSTANDSLOSE UEBERGANGSERKENNUNG (Regel 2, Kriterium 7 -- hier OHNE
jede Persistenz geloest): es gibt KEINE gespeicherte "letzter Zustand"-
Datei. Stattdessen wird fuer jedes der vier Signale (Kursabruf je Markt,
Kursvergleich je Markt, Universum-Alter, Sektor-Abdeckung) bei JEDEM Lauf
rueckwaerts durch dieselbe Historie gezaehlt, wie viele Tage IN FOLGE vor
`bezug` ebenfalls schon eine Warnung bestanden haette (`tage_in_
warnung_davor`) -- eine reine Funktion von `bezug` und der Historie,
IMMER aus denselben Daten dasselbe Ergebnis, kein `datetime.now()`
irgendwo in der Entscheidungslogik (nur an der einzigen Stelle, an der
main() den Standardwert fuer `--jetzt` bildet). Ergebnis 0 bedeutet:
gestern war noch gesund -- GENAU DER UEBERGANG, der den Push ausloest.
Ein Ergebnis > 0, das durch ERINNERUNG_TAGE teilbar ist, loest eine
Erinnerung aus -- hoechstens eine je Woche, ohne je einen "letzten Push"
irgendwo abzulegen.

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich `git log`/`git show` und den
aktuellen Arbeitsbaum -- es schreibt NIRGENDS (kein `git commit`, kein
`git push`, kein `gh pr merge`, keine Datei). Abgesichert auf zwei
Ebenen: das Workflow-Token traegt nur `contents: read` UND ein
statischer AST-Test (tests/unit/test_datenabdeckung_waechter.py)
durchsucht den Quelltext nach jedem schreibenden Aufruf.

DIE PUSH-MECHANIK: EIN gebuendelter Push ueber begrenze_bloecke(), NUR
bei Warnung (Uebergang oder woechentliche Erinnerung) -- NIE ein "alles
ok". Prioritaet "default" mit Tag "warning" (wie push_vertrag_gebrochen/
push_split_verdacht): eine echte Daten-Luecke, aber noch keine Sirene.
Der Lauf bleibt GRUEN (Exit 0), solange sich der Zustand ermitteln
liess -- ROT (Exit 1) nur bei technischem Unvermoegen (Git nicht
aufrufbar, Universum-/Ticker-Meta-Datei fehlt oder unlesbar), und dieser
Fehlschlag bleibt NIE stumm (fail-soft: der Lauf schlaegt rot aus UND
versucht, das selbst per Push zu melden -- derselbe Grundsatz wie bei
jedem anderen Waechter dieses Projekts).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .notify import push_datenabdeckung_warnung

DateTime = _dt.datetime
Date = _dt.date
UTC = _dt.timezone.utc

STATUS_JSON_PFAD = "data/status.json"
TICKER_META_PFADE = {"us": "universe/ticker_meta_us.json", "de": "universe/ticker_meta_de.json"}
UNIVERSUM_PFADE = {"us": Path("universe/universe_us.txt"), "de": Path("universe/universe_de.txt")}
MAERKTE = ("us", "de")

# --------------------------------------------------------- Pruefung A: Kursabruf

# Fenster, in dem ALLE Laeufe praktisch leer sein muessen, um als Warnung
# zu zaehlen. Startwert, Feintuning nach ca. 10 Handelstagen Baseline.
FENSTER_STUNDEN_KURSABRUF = 24.0

# "Praktisch keine" Kursdaten: hoechstens dieser Anteil von "angefragt"
# kam tatsaechlich an. Nicht exakt 0, damit ein einzelner uebrig
# gebliebener Ticker (z. B. ein kurzfristiger yfinance-Hickup bei einem
# von hunderten Titeln) eine ECHTE Totalstoerung nicht verdeckt, aber
# auch keinen Fehlalarm ausloest, wo praktisch alles ankam. Startwert,
# Feintuning nach ca. 10 Handelstagen Baseline.
PRAKTISCH_KEINE_ANTEIL = 0.02

# ----------------------------------------------- Pruefung B: iShares-Kursvergleich

# Fenster, in dem ALLE auswertbaren Laeufe (d. h. mit vorhandenem Feld
# "kursvergleich", siehe Modul-Docstring) entfallen/verweigert gewesen
# sein muessen. Startwert, Feintuning nach ca. 10 Handelstagen Baseline.
FENSTER_TAGE_KURSVERGLEICH = 7

# --------------------------------------------- gemeinsam fuer Pruefung A und B

# Mindestens so viele auswertbare Laeufe muessen im Fenster liegen, damit
# ueberhaupt eine Warnung entstehen kann -- ein EINZELNER schlechter Lauf
# allein ist noch kein Befund (Rauschen), sondern erst die WIEDERHOLUNG.
# Startwert, Feintuning nach ca. 10 Handelstagen Baseline.
MINDEST_BEOBACHTUNGEN = 2

# -------------------------------------- Pruefung C: Universum-Alter/Sektoren

# Siehe Modul-Docstring ("WARUM EIN NEUER SCHWELLENWERT ...") fuer die
# Begruendung gegenueber MAX_ALTER_HANDELSTAGE. Startwert, Feintuning
# nach ca. 10 Handelstagen Baseline.
UNIVERSUM_WARNSCHWELLE_TAGE = 180

# ------------------------------------------------------- Uebergang/Erinnerung

# Hoechstens eine Erinnerung je so viele Tage anhaltender Warnung.
# Startwert, Feintuning nach ca. 10 Handelstagen Baseline.
ERINNERUNG_TAGE = 7

# Obergrenze fuer den rueckwaertigen "wie lange schon"-Zaehler und fuer
# den Historie-Abruf (git log --since) -- eine reine Rechengrenze, kein
# fachlicher Schwellenwert: begrenzt die Zahl der `git show`-Aufrufe je
# Lauf, unabhaengig davon, wie alt das Repository insgesamt wird.
# Startwert, Feintuning nach ca. 10 Handelstagen Baseline.
RUECKBLICK_TAGE_MAX = 120


def log(text: str) -> None:
    print(text, flush=True)


# --------------------------------------------------------------- Git-Zugriff


def _git_log(
    pfad: str, *, seit: DateTime, laeufer=subprocess.run
) -> tuple[list[tuple[str, DateTime]] | None, str | None]:
    """(Hash, Commit-Zeit UTC) je Commit, der `pfad` seit `seit` beruehrt
    hat -- AELTESTER ZUERST. Genau einer der beiden Rueckgabewerte ist
    None. Liest NUR (`git log`), schreibt nichts."""
    try:
        ergebnis = laeufer(
            [
                "git", "log",
                f"--since={seit.isoformat()}",
                "--format=%H|%cI",
                "--", pfad,
            ],
            capture_output=True, text=True,
        )
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, f"git log endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
    commits: list[tuple[str, DateTime]] = []
    for zeile in ergebnis.stdout.splitlines():
        if not zeile.strip():
            continue
        hash_, _, zeit_roh = zeile.partition("|")
        try:
            zeit = _dt.datetime.fromisoformat(zeit_roh)
        except ValueError as exc:
            return None, f"git log lieferte ein unlesbares Datum ({exc})."
        commits.append((hash_, zeit))
    commits.reverse()
    return commits, None


def _git_show(commit: str, pfad: str, *, laeufer=subprocess.run) -> tuple[str | None, str | None]:
    """Inhalt von `pfad` bei `commit`. Genau einer der beiden
    Rueckgabewerte ist None. Liest NUR (`git show`), schreibt nichts."""
    try:
        ergebnis = laeufer(["git", "show", f"{commit}:{pfad}"], capture_output=True, text=True)
    except OSError as exc:
        return None, f"git liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, f"git show endete mit rc={ergebnis.returncode}: {ergebnis.stderr.strip()}"
    return ergebnis.stdout, None


def _historie_json(
    pfad: str, *, seit: DateTime, laeufer=subprocess.run
) -> tuple[list[tuple[DateTime, dict]] | None, str | None]:
    """(Commit-Zeit, geparstes JSON) je Commit seit `seit`, AELTESTER
    ZUERST. Fehlt `pfad` in der gesamten Historie (nie angelegt), ist das
    Ergebnis eine LEERE Liste -- kein Fehlschlag, siehe "Historie zu kurz
    oder Datei fehlt" im Auftrag."""
    commits, grund = _git_log(pfad, seit=seit, laeufer=laeufer)
    if grund is not None:
        return None, grund
    ergebnisse: list[tuple[DateTime, dict]] = []
    for hash_, zeit in commits:
        inhalt, grund = _git_show(hash_, pfad, laeufer=laeufer)
        if grund is not None:
            return None, grund
        try:
            ergebnisse.append((zeit, json.loads(inhalt)))
        except json.JSONDecodeError as exc:
            return None, f"{pfad} bei Commit {hash_[:8]}: kein gueltiges JSON ({exc})."
    return ergebnisse, None


def universum_stand_lesen(pfad: Path) -> Date:
    """Das Datum aus der "# Stand:"-Kopfzeile. Wirft ValueError, wenn die
    Zeile fehlt oder unlesbar ist -- vom Aufrufer als Fehlschlag (fail-
    soft, nicht stumm) behandelt, kein geratener Rueckfall."""
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if zeile.startswith("# Stand:"):
            roh = zeile.split(":", 1)[1].strip()
            return Date.fromisoformat(roh)
    raise ValueError(f"{pfad}: keine '# Stand:'-Kopfzeile gefunden.")


@dataclass(frozen=True)
class Datenlage:
    """Alles, was die drei Pruefungen brauchen -- einmal eingesammelt,
    damit main() nicht bei jeder Pruefung erneut `git` aufruft."""

    status_historie: list[tuple[DateTime, dict]]
    ticker_meta_historie: dict[str, list[tuple[DateTime, dict]]]
    universum_stand: dict[str, Date]


def ermittle_datenlage(
    *, bezug: DateTime, laeufer=subprocess.run
) -> tuple[Datenlage | None, str | None]:
    """Alle drei Datenquellen einsammeln. Genau einer der beiden
    Rueckgabewerte ist None."""
    seit = bezug - _dt.timedelta(days=RUECKBLICK_TAGE_MAX + FENSTER_TAGE_KURSVERGLEICH + 1)

    status_historie, grund = _historie_json(STATUS_JSON_PFAD, seit=seit, laeufer=laeufer)
    if grund is not None:
        return None, f"{STATUS_JSON_PFAD}: {grund}"

    ticker_meta_historie: dict[str, list[tuple[DateTime, dict]]] = {}
    for markt, pfad in TICKER_META_PFADE.items():
        historie, grund = _historie_json(pfad, seit=seit, laeufer=laeufer)
        if grund is not None:
            return None, f"{pfad}: {grund}"
        ticker_meta_historie[markt] = historie

    universum_stand: dict[str, Date] = {}
    for markt, pfad in UNIVERSUM_PFADE.items():
        try:
            universum_stand[markt] = universum_stand_lesen(pfad)
        except (OSError, ValueError) as exc:
            return None, f"{pfad}: Stand nicht lesbar ({type(exc).__name__}: {exc})."

    return Datenlage(status_historie, ticker_meta_historie, universum_stand), None


# ------------------------------------------------------------------- Pruefung A


def kursabruf_ist_praktisch_leer(markt_daten: dict) -> bool:
    """True, wenn hoechstens PRAKTISCH_KEINE_ANTEIL von "angefragt"
    tatsaechlich "geliefert" wurde. Nichts angefragt (z. B. ein leeres
    Universum) ist hier bewusst KEIN Befund dieses Moduls -- das waere
    ein eigenes Problem, keine Fremdquellen-Stoerung."""
    angefragt = markt_daten.get("angefragt", 0) or 0
    geliefert = markt_daten.get("geliefert", 0) or 0
    if angefragt <= 0:
        return False
    return geliefert / angefragt <= PRAKTISCH_KEINE_ANTEIL


def kursabruf_warnung_zum_zeitpunkt(
    bezug: DateTime,
    historie: list[tuple[DateTime, dict]],
    markt: str,
    *,
    fenster_stunden: float = FENSTER_STUNDEN_KURSABRUF,
) -> bool | None:
    """True = Warnung (alle auswertbaren Laeufe im Fenster praktisch
    leer), False = gesund, None = nicht auswertbar (weniger als
    MINDEST_BEOBACHTUNGEN Laeufe im Fenster -- Historie zu kurz oder nur
    ein einzelner Lauf, siehe Auftrag)."""
    fenster_start = bezug - _dt.timedelta(hours=fenster_stunden)
    treffer: list[bool] = []
    for zeit, status in historie:
        if not (fenster_start < zeit <= bezug):
            continue
        for eintrag in status.get("maerkte", []):
            if eintrag.get("markt") == markt and "daten" in eintrag:
                treffer.append(kursabruf_ist_praktisch_leer(eintrag["daten"]))
    if len(treffer) < MINDEST_BEOBACHTUNGEN:
        return None
    return all(treffer)


# ------------------------------------------------------------------- Pruefung B


def kursvergleich_ist_abgelehnt(kursvergleich: dict) -> bool:
    return kursvergleich.get("verdikt") in ("entfallen", "verweigert")


def kursvergleich_warnung_zum_zeitpunkt(
    bezug: DateTime,
    historie: list[tuple[DateTime, dict]],
    markt: str,
    *,
    fenster_tage: int = FENSTER_TAGE_KURSVERGLEICH,
) -> bool | None:
    """Wie kursabruf_warnung_zum_zeitpunkt, aber nur ueber Laeufe, die
    ueberhaupt ein "kursvergleich"-Feld tragen (siehe Modul-Docstring --
    das ist nur bei Stichtags-Laeufen der Fall, ein Anzeige-Lauf-Tag
    liefert hier schlicht KEINEN Treffer, keinen Fehlschlag)."""
    fenster_start = bezug - _dt.timedelta(days=fenster_tage)
    treffer: list[bool] = []
    for zeit, status in historie:
        if not (fenster_start < zeit <= bezug):
            continue
        for eintrag in status.get("maerkte", []):
            if eintrag.get("markt") == markt and "kursvergleich" in eintrag:
                treffer.append(kursvergleich_ist_abgelehnt(eintrag["kursvergleich"]))
    if len(treffer) < MINDEST_BEOBACHTUNGEN:
        return None
    return all(treffer)


# ------------------------------------------------------------------- Pruefung C


def universum_alter_warnung_zum_tag(
    tag: Date, stand: Date, *, schwelle_tage: int = UNIVERSUM_WARNSCHWELLE_TAGE
) -> bool:
    return (tag - stand).days > schwelle_tage


def fehlende_sektoren_anzahl(ticker_meta: dict) -> int:
    return sum(1 for eintrag in ticker_meta.values() if not eintrag.get("sektor"))


def sektor_warnung_zum_zeitpunkt(
    bezug: DateTime, historie: list[tuple[DateTime, dict]]
) -> bool | None:
    """Der juengste Commit AM ODER VOR `bezug` entscheidet. None, wenn es
    in der (beschnittenen) Historie keinen solchen Commit gibt --
    konservativ "nicht auswertbar", kein Fehlalarm."""
    passende = [(zeit, daten) for zeit, daten in historie if zeit <= bezug]
    if not passende:
        return None
    _, daten = max(passende, key=lambda eintrag: eintrag[0])
    return fehlende_sektoren_anzahl(daten) > 0


# ---------------------------------------------------- Uebergang und Erinnerung


def tage_in_warnung_davor(
    ist_warnung, bezug, *, max_tage: int = RUECKBLICK_TAGE_MAX
) -> int:
    """Wie viele Tage VOR `bezug` in Folge ebenfalls schon eine Warnung
    bestanden haette -- 0, wenn der Vortag bereits gesund/nicht
    auswertbar war (das ist der UEBERGANG). Reine Funktion von `bezug`
    und `ist_warnung`, ohne jede Persistenz (Regel 2)."""
    n = 0
    punkt = bezug - _dt.timedelta(days=1)
    while n < max_tage and ist_warnung(punkt) is True:
        n += 1
        punkt -= _dt.timedelta(days=1)
    return n


def push_ist_faellig(
    ist_warnung_jetzt: bool, anhaltend_seit: int, *, erinnerung_tage: int = ERINNERUNG_TAGE
) -> bool:
    """True nur beim Uebergang (anhaltend_seit == 0) oder bei einer
    faelligen woechentlichen Erinnerung -- hoechstens eine je
    ERINNERUNG_TAGE Tage anhaltender Warnung, ohne gespeicherten
    "letzter Push"-Zeitpunkt."""
    if not ist_warnung_jetzt:
        return False
    return anhaltend_seit == 0 or anhaltend_seit % erinnerung_tage == 0


@dataclass(frozen=True)
class Signal:
    name: str
    ist_warnung_jetzt: bool | None
    anhaltend_seit: int
    text: str


def _signal(name: str, ist_warnung, bezug, text_wenn_warnung) -> Signal:
    jetzt = ist_warnung(bezug)
    anhaltend = tage_in_warnung_davor(ist_warnung, bezug) if jetzt else 0
    text = text_wenn_warnung(jetzt, anhaltend) if jetzt else ""
    return Signal(name, jetzt, anhaltend, text)


def ermittle_signale(datenlage: Datenlage, bezug: DateTime) -> list[Signal]:
    """Alle vier Signale (Kursabruf je Markt, Kursvergleich je Markt,
    Universum-Alter, Sektor-Abdeckung) gegen `bezug` auswerten -- eine
    reine Funktion der Datenlage, keine Seiteneffekte."""
    signale: list[Signal] = []

    for markt in MAERKTE:
        def ist_warnung(punkt, markt=markt):
            return kursabruf_warnung_zum_zeitpunkt(punkt, datenlage.status_historie, markt)

        def text(jetzt, anhaltend, markt=markt):
            return (
                f"Kursabruf {markt.upper()}: seit {FENSTER_STUNDEN_KURSABRUF:.0f} Std. "
                f"praktisch keine Kursdaten angekommen (<= {PRAKTISCH_KEINE_ANTEIL:.0%} "
                f"von 'angefragt'), anhaltend {anhaltend + 1}. Tag."
            )

        signale.append(_signal(f"Kursabruf {markt.upper()}", ist_warnung, bezug, text))

    for markt in MAERKTE:
        def ist_warnung(punkt, markt=markt):
            return kursvergleich_warnung_zum_zeitpunkt(punkt, datenlage.status_historie, markt)

        def text(jetzt, anhaltend, markt=markt):
            return (
                f"iShares-Kursvergleich {markt.upper()}: in den letzten "
                f"{FENSTER_TAGE_KURSVERGLEICH} Tagen durchgehend 'entfallen'/"
                f"'verweigert', anhaltend {anhaltend + 1}. Tag."
            )

        signale.append(_signal(f"Kursvergleich {markt.upper()}", ist_warnung, bezug, text))

    for markt in MAERKTE:
        stand = datenlage.universum_stand[markt]

        def ist_warnung(punkt, stand=stand):
            tag = punkt.date() if isinstance(punkt, DateTime) else punkt
            return universum_alter_warnung_zum_tag(tag, stand)

        def text(jetzt, anhaltend, markt=markt, stand=stand):
            alter = (bezug.date() - stand).days
            return (
                f"Universum {markt.upper()}: Stand {stand.isoformat()} ist "
                f"{alter} Kalendertage alt (Schwelle {UNIVERSUM_WARNSCHWELLE_TAGE}), "
                f"anhaltend {anhaltend + 1}. Tag."
            )

        signale.append(_signal(f"Universum-Alter {markt.upper()}", ist_warnung, bezug, text))

    for markt in MAERKTE:
        def ist_warnung(punkt, markt=markt):
            return sektor_warnung_zum_zeitpunkt(punkt, datenlage.ticker_meta_historie[markt])

        def text(jetzt, anhaltend, markt=markt):
            aktuell = max(
                datenlage.ticker_meta_historie[markt], key=lambda eintrag: eintrag[0]
            )[1]
            fehlend = fehlende_sektoren_anzahl(aktuell)
            return (
                f"Sektor-Abdeckung {markt.upper()}: {fehlend} Ticker ohne Sektor, "
                f"anhaltend {anhaltend + 1}. Tag."
            )

        signale.append(_signal(f"Sektor-Abdeckung {markt.upper()}", ist_warnung, bezug, text))

    return signale


def faellige_bloecke(signale: list[Signal]) -> list[tuple[str, str]]:
    """(Name, Text) je Signal, dessen Push gerade faellig ist -- siehe
    push_ist_faellig()."""
    return [
        (s.name, s.text)
        for s in signale
        if s.ist_warnung_jetzt and push_ist_faellig(True, s.anhaltend_seit)
    ]


# --------------------------------------------------------------------- main()


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie bei jedem anderen Waechter dieses Projekts."""
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
    melder=push_datenabdeckung_warnung,
    ermittle_datenlage=ermittle_datenlage,
) -> int:
    """`melder`/`ermittle_datenlage` sind die Test-Naehte, wie bei jedem
    anderen Waechter dieses Projekts."""
    parser = argparse.ArgumentParser(description="Daten-Abdeckungs-Wächter")
    parser.add_argument(
        "--jetzt", help="Bezugszeitpunkt UTC, ISO-8601 (nur fuer Tests)"
    )
    args = parser.parse_args(argv)
    if args.jetzt:
        bezug = _dt.datetime.fromisoformat(args.jetzt)
        if bezug.tzinfo is None:
            bezug = bezug.replace(tzinfo=UTC)
    else:
        bezug = _dt.datetime.now(UTC)  # einzige Stelle, nie in der Entscheidungslogik

    datenlage, grund = ermittle_datenlage(bezug=bezug)
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte Datenlage nicht ermitteln: {grund}")
        return 1

    signale = ermittle_signale(datenlage, bezug)
    bloecke = faellige_bloecke(signale)

    if not bloecke:
        log("Waechter: keine faellige Warnung — still.")
        return 0

    log(f"Waechter: {len(bloecke)} faellige Warnung(en) — " + "; ".join(n for n, _ in bloecke))
    from .notify import begrenze_bloecke  # noqa: PLC0415 - gemeinsame Haertung

    text = begrenze_bloecke(bloecke)
    _melden(melder, text)
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
