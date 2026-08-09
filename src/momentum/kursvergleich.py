"""DE-Kursvergleich: die Bestandslisten gegen die Kursquelle stellen.

WOZU
Bis hierher haengt jede Zahl des Rankings an EINER Quelle: Yahoo. Faellt
sie aus, merkt man es -- der Lauf bricht laut ab. Liefert sie dagegen
falsche Kurse, merkt es niemand. Genau diese Luecke schliesst der
Vergleich: die drei iShares-Bestandslisten fuehren eine Spalte "Kurs" mit
dem BlackRock-Bewertungskurs je Titel. Das ist ein von Yahoo vollstaendig
unabhaengiger Preis-Pfad -- anderer Anbieter, andere Zulieferkette,
andere Bewertungsmechanik.

DIE HARTE REGEL, und sie ist der eigentliche Kern dieser Datei:
DIE ZWEITQUELLE SPEIST NIEMALS DEN SCORE UND NIEMALS DIE KURSE. Sie
vergleicht, mehr nicht. Es gibt in diesem Modul keinen Rueckgabewert, der
in eine Kursreihe, eine Rendite oder einen Rang fliessen koennte -- nur
ein Verdikt und eine Liste von Namen. Wer das aendern will, muss den
Vergleich anfassen; ein Versehen kann es nicht werden.
(tests/unit/test_kursvergleich.py haelt das mit einem Mutations-Test
fest: eine manipulierte Kurs-Spalte darf JEDE Ranking-Zahl unveraendert
lassen und ausschliesslich das Verdikt drehen.)

DAS VERDIKT IST DREISTUFIG -- und die dritte Stufe ist die wichtigste:
  ok           hoechstens ZULASS_ABWEICHLER Titel liegen ausserhalb der
               Toleranz. Der Lauf laeuft normal, die Abweichler stehen
               namentlich im Protokoll.
  verweigert   mehr Abweichler. Der Stichtags-Lauf bricht ab und es
               entsteht KEIN Ranking. Der Grund ist nicht "Yahoo ist
               kaputt" -- der Grund ist: ZWEI Quellen widersprechen sich
               und wir wissen nicht, welche luegt. Auf einer Vermutung
               darf kein eingefrorenes Monats-Ranking entstehen.
  entfallen    der Vergleich war gar nicht moeglich (keine Kurs-Spalte,
               Datei nicht abrufbar, Stichtags-Luecke, unklare
               Zahlenschreibweise, per Schalter abgeschaltet). Dann laeuft
               der Lauf normal weiter -- aber Report UND Push tragen
               sichtbar "Kursvergleich entfiel: <Grund>". Niemals still.

WARUM NUR AM STICHTAG UND NUR FUER DE: Die Kurse der Bestandslisten sind
Bewertungskurse zum Stichtag der Datei, keine laufenden Kurse. Der
taegliche Anzeige-Lauf hat damit nichts zu vergleichen und bleibt
unberuehrt. Fuer den US-Markt gibt es (noch) keine zweite Quelle dieser
Art; sein Ranking traegt deshalb dauerhaft ein "entfallen" mit genau
diesem Grund.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .ishares import Befund

Date = _dt.date

QUELLE = "iShares-Bestandslisten, Spalte „Kurs“ (BlackRock-Bewertungskurs)"

# --------------------------------------------------------------------------
# Die drei Stellschrauben. Jede mit Herleitung -- keine geraten.
# --------------------------------------------------------------------------

# Wie weit duerfen die beiden Kurse auseinanderliegen, ohne dass es ein
# Widerspruch ist?
#
# HERLEITUNG, und sie ist ausdruecklich VORLAEUFIG: Beide Seiten sollten
# denselben Xetra-Schlusskurs meinen -- BlackRock bewertet deutsche Aktien
# zum Xetra-Schluss, und Yahoos "Close" fuer .DE-Titel ist ebenfalls der
# Xetra-Schluss. Legitime Restunterschiede kommen aus dem genauen
# Bewertungszeitpunkt (Schlussauktion vs. letzter fortlaufender Kurs), aus
# der Rundung der CSV-Spalte und daraus, dass ein Fonds einzelne Titel an
# einem anderen Handelsplatz bewerten kann. Eine gemessene Groesse dafuer
# gibt es NICHT -- der Vergleich hat noch nie stattgefunden. 1,0 % ist
# deshalb bewusst weit gewaehlt: weit genug, um an Bewertungsrauschen
# nicht anzuschlagen, eng genug, um einen echten Datenbruch (falscher
# Titel, falscher Tag, Faktor 10) sicher zu fangen -- die Fehler, gegen
# die dieses Gatter gebaut ist, sind um Groessenordnungen groesser als 1 %.
#
# Der Vertragstest misst die tatsaechliche Abweichung im Fenster vor dem
# Stichtag und schreibt sie ins Protokoll. Sobald dort echte Zahlen
# stehen, gehoert diese Schwelle auf Evidenz nachgezogen.
TOLERANZ = 0.010

# So viele Titel duerfen ausserhalb der Toleranz liegen, ohne dass der Lauf
# verweigert. Begruendung: ein EINZELNER Titel kann aus harmlosen Gruenden
# auseinanderlaufen -- Kapitalmassnahme am Stichtag, Handelsaussetzung,
# ein Titel, dessen Xetra-Symbol bei Yahoo auf eine andere Gattung zeigt.
# Ein SYSTEMATISCHER Bruch (falscher Tag, falscher Markt, verrutschte
# Spalte) trifft dagegen nie drei Titel, sondern alle. Drei trennt diese
# beiden Faelle, ohne dass ein einzelner Ausreisser einen Monat kostet.
ZULASS_ABWEICHLER = 3

# Unterhalb dieses Anteils vergleichbarer Titel ist "null Abweichler" keine
# Aussage mehr, sondern ein Zufall. Dann gilt der Vergleich als nicht
# moeglich (entfallen) statt als bestanden -- ein Gatter, das mangels
# Daten immer gruen zeigt, ist schlimmer als keins.
MIN_VERGLEICHSQUOTE = 0.80

# Die Bestandslisten fuehren eine Marktwaehrung je Zeile. Ein Titel, der
# nicht in Euro bewertet ist, wird NICHT verglichen (und zaehlt nicht als
# Abweichler): ein Waehrungsunterschied wuerde als riesige Abweichung
# erscheinen und den Lauf grundlos verweigern.
ERWARTETE_WAEHRUNG = "EUR"

# --------------------------------------------------------------------------
# BEFUND ZUR US-SEITE, gemessen am 09.08.2026 auf einem GitHub-Runner
# (Wegwerf-Probe, danach wieder entfernt). Er steht hier und nicht in einem
# Protokoll, weil hier gesucht wird, wer den Satz "gibt es nicht" eines
# Tages ersetzen will.
#
#   * Der amerikanische Endpunkt (IVV, .../us/products/239726/...
#     1467271812596.ajax) liefert HTTP 200 und den Content-Type
#     "text/csv;charset=UTF-8" -- und im Koerper 2,2 MB HTML, die
#     Zustimmungs-Seite. Merke: der Content-Type LUEGT. Dass
#     `lade_bestandsliste` in den Koerper schaut statt auf die Kopfzeile,
#     ist damit kein Uebereifer, sondern gemessen noetig.
#
#   * Der DEUTSCHE Endpunkt-Typ (1478358465952.ajax) liefert dagegen fuer
#     zwei europaeische S&P-500-ETFs eine echte CSV im vertrauten Format,
#     mit Kurs-Spalte, deutscher Zahlenschreibweise und demselben
#     Vorspann:
#         Produkt 253743 (SXR8/CSPX): Stichtag 07.08., 504 Aktien-Zeilen,
#             494 Ticker, 494 Kurse
#         Produkt 251900 (IUSA):      Stichtag 06.08., 504 Aktien-Zeilen,
#             494 Ticker, 494 Kurse
#
# Eine zweite US-Kursquelle ist damit ERREICHBAR. Was fehlt, sind drei
# Dinge, und jedes davon ist eine bewusste Entscheidung, kein Handgriff:
#   1. Waehrung: diese Dateien fuehren USD und Boerse NASDAQ/NYSE. Die
#      Erwartung unten ist auf EUR festgenagelt und muesste je Markt
#      gelten.
#   2. Ticker: `xetra_zu_yahoo` haengt stumpf ".DE" an. Fuer eine
#      US-Liste braucht es die Uebersetzung aus `parse_us`
#      (BRK.B -> BRK-B) -- 10 der 504 Zeilen ergaben ueberhaupt keinen
#      Ticker, vermutlich genau die Klassen-Titel.
#   3. Bewertungszeitpunkt: ein UCITS-Fonds bewertet US-Aktien nicht
#      zwingend zum US-Schluss. Das waere vor dem Scharfschalten zu
#      messen -- so, wie es der Vertragstest fuer DE tut.
# --------------------------------------------------------------------------
NICHT_VORGESEHEN = (
    "fuer diesen Markt gibt es keine zweite, unabhaengige Kursquelle "
    "(der Vergleich existiert bisher nur fuer Deutschland)"
)
ABGESCHALTET = "per Schalter abgeschaltet (--ohne-kursvergleich)"


@dataclass(frozen=True)
class Abweichung:
    """Ein Titel, bei dem sich die beiden Quellen widersprechen."""

    ticker: str
    name: str
    kurs_ishares: float
    kurs_yahoo: float
    abweichung: float   # relativ, vorzeichenbehaftet: Yahoo gegen iShares

    def zeile(self) -> str:
        return (
            f"{self.ticker} ({self.name}): iShares {self.kurs_ishares:.4f} "
            f"vs. Kursquelle {self.kurs_yahoo:.4f} — "
            f"{self.abweichung * 100:+.2f} %"
        )

    def als_report(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "kurs_ishares": round(self.kurs_ishares, 4),
            "kurs_kursquelle": round(self.kurs_yahoo, 4),
            "abweichung": round(self.abweichung, 8),
        }


@dataclass(frozen=True)
class Vergleich:
    """Das Ergebnis. Enthaelt bewusst KEINEN Kurs, der weiterverwendbar waere."""

    verdikt: str                     # "ok" | "verweigert" | "entfallen"
    grund: str = ""                  # gefuellt genau dann, wenn "entfallen"
    stichtag: Date | None = None
    verglichen: tuple[str, ...] = ()
    ohne_vergleich: tuple[str, ...] = ()
    abweichler: tuple[Abweichung, ...] = ()
    weitere_staende: tuple[Date, ...] = ()

    @classmethod
    def entfaellt(cls, grund: str) -> "Vergleich":
        return cls(verdikt="entfallen", grund=grund)

    @property
    def verweigert(self) -> bool:
        return self.verdikt == "verweigert"

    def als_report(self) -> dict:
        """Der additive Block im Ranking. Sortiert und gerundet -- damit
        zweimal derselbe Vergleich Zeichen fuer Zeichen dasselbe ergibt."""
        return {
            "verdikt": self.verdikt,
            "quelle": QUELLE,
            "grund": self.grund,
            "stichtag": self.stichtag.isoformat() if self.stichtag else None,
            "toleranz": TOLERANZ,
            "zulass_abweichler": ZULASS_ABWEICHLER,
            "verglichen": len(self.verglichen),
            "ohne_vergleich": list(self.ohne_vergleich),
            "abweichler": [a.als_report() for a in self.abweichler],
        }

    def protokoll(self) -> list[str]:
        """Die Zeilen fuers Lauf-Log. Abweichler IMMER namentlich."""
        if self.verdikt == "entfallen":
            return [f"[kursvergleich] entfiel: {self.grund}"]
        kopf = (
            f"[kursvergleich] Stichtag {self.stichtag}, {len(self.verglichen)} "
            f"Titel verglichen, {len(self.ohne_vergleich)} ohne Vergleich, "
            f"{len(self.abweichler)} ueber {TOLERANZ * 100:.1f} % "
            f"(zugelassen: {ZULASS_ABWEICHLER}) — {self.verdikt.upper()}"
        )
        zeilen = [kopf]
        if self.weitere_staende:
            zeilen.append(
                "[kursvergleich] die Bestandslisten tragen verschiedene "
                "Stichtage: "
                + ", ".join(d.isoformat() for d in self.weitere_staende)
                + " — verglichen wurde je Titel gegen den Stichtag SEINER Datei."
            )
        zeilen += [f"[kursvergleich]   {a.zeile()}" for a in self.abweichler]
        return zeilen

    def kurzfassung(self) -> str | None:
        """Eine Zeile fuer den Push -- oder None, wenn es nichts zu sagen gibt."""
        return kurzfassung_aus_report(self.als_report())

    def als_status(self) -> dict:
        """Kurzform fuer data/status.json."""
        return {
            "verdikt": self.verdikt,
            "grund": self.grund,
            "stichtag": self.stichtag.isoformat() if self.stichtag else None,
            "verglichen": len(self.verglichen),
            "abweichler": [a.ticker for a in self.abweichler],
        }


def kurzfassung_aus_report(block: dict) -> str | None:
    """Die Push-Zeile aus dem Report-Block -- die EINZIGE Formulierung dafuer.

    Bewusst aus dem geschriebenen Block und nicht aus dem Objekt: was im
    Push steht, ist damit garantiert dasselbe, was in der Ranking-Datei
    nachlesbar ist. Zwei Formulierungen desselben Sachverhalts waeren
    zwei Gelegenheiten, auseinanderzulaufen.
    """
    if block["verdikt"] == "entfallen":
        return f"Kursvergleich entfiel: {block['grund']}"
    abweichler = block.get("abweichler") or []
    if not abweichler:
        return None
    namen = ", ".join(
        f"{a['ticker']} {a['abweichung'] * 100:+.1f} %" for a in abweichler
    )
    return (
        f"Kursvergleich: {len(abweichler)} von {block['verglichen']} Titeln "
        f"ueber {block['toleranz'] * 100:.1f} % ({namen})."
    )


def _abweichung(ishares: float, yahoo: float) -> float:
    return (yahoo - ishares) / ishares


def vergleiche(
    befunde: list[Befund],
    roh_kurse: dict[str, dict[Date, float]],
    *,
    universum: set[str] | None = None,
) -> Vergleich:
    """Die Bestandslisten gegen die (unbereinigten!) Schlusskurse stellen.

    `roh_kurse` ist `PriceBundle.close` -- der Kurs WIE GEHANDELT. Der
    bereinigte Kurs waere hier falsch: Bewertungskurse sind nicht
    dividendenbereinigt, und nach jeder Dividende laege die bereinigte
    Reihe systematisch darunter. Das Gatter wuerde dann genau dort
    anschlagen, wo alles in Ordnung ist.

    Verglichen wird je Titel gegen den Stichtag SEINER Datei, nicht gegen
    den Stichtag des Rankings. Begruendung: die Bestandsliste bildet den
    Bestand ihres eigenen Stichtags ab und liegt am Lauftag regelmaessig
    ein bis zwei Handelstage zurueck (beobachtet am 09.08.2026: Datei vom
    06.08.). Gegen den Ranking-Stichtag zu vergleichen hiesse, zwei
    verschiedene Tage gegeneinander zu stellen -- und das ist kein
    Quellenvergleich mehr, sondern eine Tagesrendite.
    """
    # Je Ticker der erste Fund; ein Doppelmitglied (DAX und TecDAX) wird
    # genau einmal verglichen. Reihenfolge deterministisch ueber die
    # Reihenfolge der Befunde und die Sortierung am Ende.
    gefunden: dict[str, tuple[object, Date]] = {}
    staende: set[Date] = set()
    for befund in befunde:
        if befund.bestand_stand is None:
            continue
        staende.add(befund.bestand_stand)
        for kandidat in befund.kandidaten:
            if universum is not None and kandidat.ticker not in universum:
                continue
            gefunden.setdefault(kandidat.ticker, (kandidat, befund.bestand_stand))

    if not gefunden:
        return Vergleich.entfaellt(
            "kein einziger Titel der Bestandslisten liegt im Universum — "
            "passen Universum und Bestandslisten noch zusammen?"
        )

    mit_kurs = {t: p for t, p in gefunden.items() if p[0].kurs is not None}
    if not mit_kurs:
        return Vergleich.entfaellt(
            f"die Bestandslisten fuehren keine lesbare Kurs-Spalte "
            f"({len(gefunden)} Titel geprueft). Entweder ist die Spalte weg "
            f"oder ihre Zahlenschreibweise ist nicht eindeutig bestimmbar."
        )

    verglichen: list[str] = []
    ohne: list[str] = []
    abweichler: list[Abweichung] = []

    for ticker in sorted(mit_kurs):
        kandidat, stand = mit_kurs[ticker]
        if kandidat.waehrung and kandidat.waehrung != ERWARTETE_WAEHRUNG:
            ohne.append(f"{ticker} (Marktwaehrung {kandidat.waehrung})")
            continue
        reihe = roh_kurse.get(ticker)
        if not reihe:
            ohne.append(f"{ticker} (keine Kursreihe)")
            continue
        yahoo = reihe.get(stand)
        if yahoo is None:
            ohne.append(f"{ticker} (kein Kurs am {stand.isoformat()})")
            continue
        verglichen.append(ticker)
        delta = _abweichung(kandidat.kurs, yahoo)
        if abs(delta) > TOLERANZ:
            abweichler.append(
                Abweichung(ticker, kandidat.name, kandidat.kurs, yahoo, delta)
            )

    quote = len(verglichen) / len(mit_kurs)
    if quote < MIN_VERGLEICHSQUOTE:
        return Vergleich.entfaellt(
            f"nur {len(verglichen)} von {len(mit_kurs)} Titeln waren "
            f"vergleichbar ({quote:.0%}, noetig {MIN_VERGLEICHSQUOTE:.0%}). "
            f"Bei so wenigen Titeln waere „keine Abweichung“ kein Befund, "
            f"sondern ein Zufall."
        )

    return Vergleich(
        verdikt="ok" if len(abweichler) <= ZULASS_ABWEICHLER else "verweigert",
        # Der aelteste Stichtag steht vorn -- dieselbe Regel wie bei der
        # Vereinigung der Universums-Listen: so frisch wie die schwaechste
        # Zutat.
        stichtag=min(staende),
        verglichen=tuple(verglichen),
        ohne_vergleich=tuple(ohne),
        abweichler=tuple(abweichler),
        weitere_staende=tuple(sorted(staende)) if len(staende) > 1 else (),
    )


def abbruchtext(vergleich: Vergleich, markt: str) -> str:
    """Der Grund, mit dem der Stichtags-Lauf abbricht -- vollstaendig genug,
    dass man am Telefon entscheiden kann, welche Quelle luegt."""
    zeilen = [
        f"[{markt}] Kursvergleich VERWEIGERT den Stichtag: "
        f"{len(vergleich.abweichler)} von {len(vergleich.verglichen)} Titeln "
        f"weichen um mehr als {TOLERANZ * 100:.1f} % ab "
        f"(zugelassen sind {ZULASS_ABWEICHLER}).",
        "",
        f"Bestands-Stichtag der Bestandslisten: {vergleich.stichtag}.",
        "Verglichen wurde der BlackRock-Bewertungskurs gegen den "
        "unbereinigten Schlusskurs der Kursquelle.",
        "",
    ]
    zeilen += [f"  {a.zeile()}" for a in vergleich.abweichler]
    zeilen += [
        "",
        "Zwei unabhaengige Quellen widersprechen sich, und es ist von hier "
        "aus nicht entscheidbar, welche recht hat. Es wurde deshalb KEIN "
        "Ranking geschrieben und nichts eingefroren — ein Monats-Ranking auf "
        "einer Vermutung waere schlimmer als ein spaeteres.",
        "",
        "Der faellige Monat bleibt offen: Er wird an JEDEM spaeteren Lauf "
        "erneut versucht, und sein Stichtag ergibt sich aus dem "
        "Handelskalender des Index — nicht aus dem Lauftag. Der Stichtag "
        "geht also nicht verloren.",
    ]
    return "\n".join(zeilen)
