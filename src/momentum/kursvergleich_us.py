"""US-Kursvergleich: Geschwister von kursvergleich.py, andere Quelle,
anderer Anker, andere Toleranz -- gemessen statt angenommen.

WOZU
Dasselbe Loch wie bei DE, nur fuer den US-Markt: das Ranking haengt an
EINER Kursquelle (Yahoo). Die S&P-500-UCITS-Fonds SXR8 (primaer) und IUSA
(dokumentierter Ausweich) fuehren -- wie die DE-Bestandslisten -- eine
Spalte "Kurs" mit dem BlackRock-Bewertungskurs je Titel. Derselbe
gemeinsame Parser (momentum/ishares.py) liest beide Fondsarten; nur die
Symbol-Uebersetzung unterscheidet sich (US-Symbol -> Yahoo-Ticker statt
Xetra-Kuerzel -> ".DE").

DIE HARTE REGEL gilt unveraendert: DIE ZWEITQUELLE SPEIST NIEMALS DEN
SCORE UND NIEMALS DIE KURSE. Sie vergleicht, mehr nicht.

ANKER UND TOLERANZ, HERGELEITET (nicht geraten) -- Wegwerf-Messung #28,
10.-12.08.2026, Ergebnis gesichert in #31 und uebernommen von Easy am
14.08.2026:
  Anker = Bestands-Stichtag der Fonds-Datei selbst (NICHT der US-
  Handelstag davor). Gegen diesen Anker lag die Abweichung bei Median/p90/
  p99 0,000 %, Maximum 0,002-0,004 % -- gegen den Vortag dagegen bei
  Median 1,0-1,3 %, Maximum bis 28 %. Ein Faktor-250-Unterschied, stabil
  an beiden gemessenen Stichtagen.
  Toleranz = 0,25 % -- hergeleitet aus der Rundung der zweistelligen
  Kurs-Spalte: bei einem 2-Dollar-Titel sind 0,005 Dollar bereits 0,25 %.

DIE SPLIT-AUSNAHME, aus Mess-Tag 2 gelernt (11.08.2026): Ohne sie zerreisst
das Gatter bei jedem Aktien-Split. Der Fonds und die Kursquelle koennen
den Split-Tag um einen Handelstag versetzt nachvollziehen -- fuer EINEN
Tag zeigt der Vergleich dann einen "Fehler" in exakt der Groesse des
Split-Verhaeltnisses. Das ist kein Widerspruch zweier Quellen, sondern
eine Kapitalmassnahme, die beide Quellen richtig, nur zeitversetzt
abbilden. Ein Titel zaehlt deshalb NUR dann als "Split erkannt -- kein
Befund" statt als Abweichler, wenn BEIDE Bedingungen zutreffen:
  1. das Kursverhaeltnis entspricht (innerhalb der Erkennungstoleranz)
     einem gaengigen Split-Verhaeltnis (2:1, 3:1, 3:2, 4:1, 10:1, je
     Richtung), UND
  2. der Yahoo-Split-Kalender fuehrt fuer diesen Titel tatsaechlich einen
     Split im Fenster um den Bestands-Stichtag.
Ein zufaellig passendes Verhaeltnis OHNE Kalender-Beleg zaehlt weiterhin
als normaler Abweichler -- sonst waere die Ausnahme ein Schlupfloch fuer
jeden echten Fehler, der zufaellig in die Naehe eines Split-Verhaeltnisses
faellt (tests/unit/test_kursvergleich_us.py haelt das fest).

DAS VERDIKT IST DREISTUFIG, genau wie bei DE (ok / verweigert / entfallen)
-- siehe kursvergleich.py fuer die Begruendung der drei Stufen. "Split
erkannt" ist keine vierte Stufe: die betroffenen Titel zaehlen weder als
Abweichler noch als "ohne Vergleich", sie stehen als eigene, benannte
Kategorie im Protokoll und Report.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .ishares import Befund, handelstage_zwischen
from .kursvergleich import Abweichung, kurzfassung_aus_report

Date = _dt.date

QUELLE = "iShares S&P-500-UCITS-Bestandslisten (SXR8/IUSA), Spalte „Kurs“"

# --------------------------------------------------------------------------
# Die Stellschrauben -- Herleitung im Moduldocstring.
# --------------------------------------------------------------------------

TOLERANZ = 0.0025
ZULASS_ABWEICHLER = 3
MIN_VERGLEICHSQUOTE = 0.80
ERWARTETE_WAEHRUNG = "USD"

# Gaengige Split-Verhaeltnisse. "Je Richtung" (siehe Moduldocstring) heisst:
# geprueft wird das Verhaeltnis der beiden Kurse in BEIDE Richtungen
# (max/min), nicht nur eine -- ein 10:1-Split zeigt sich unabhaengig
# davon, welche der beiden Quellen ihn schon nachvollzogen hat.
SPLIT_VERHAELTNISSE: tuple[float, ...] = (2.0, 3.0, 1.5, 4.0, 10.0)

# Wie nah ein gemessenes Kursverhaeltnis an einem Split-Verhaeltnis liegen
# muss, um als Treffer zu gelten. Kurse runden auf den Cent; bei einem
# knapp zweistelligen Titel darf das schon ein paar Prozent ausmachen.
SPLIT_ERKENNUNG_TOLERANZ = 0.03

# Zeitfenster um den Bestands-Stichtag, in dem ein Split-Kalendereintrag
# noch "im relevanten Zeitraum" liegt. Der beobachtete Fall (Mess-Tag 2)
# war ein Versatz von einem Handelstag; ein paar Tage Sicherheitsabstand
# fangen zusaetzlich ein Wochenende oder einen Feiertag ab.
SPLIT_FENSTER_HANDELSTAGE = 5


@dataclass(frozen=True)
class SplitErkannt:
    """Ein Titel, dessen Abweichung als Aktien-Split erklaert ist -- KEIN
    Befund, deshalb eine eigene Kategorie statt eines Abweichlers."""

    ticker: str
    name: str
    kurs_ishares: float
    kurs_yahoo: float
    abweichung: float
    verhaeltnis: float
    split_datum: Date

    def zeile(self) -> str:
        return (
            f"{self.ticker} ({self.name}): iShares {self.kurs_ishares:.4f} "
            f"vs. Kursquelle {self.kurs_yahoo:.4f} — "
            f"{self.abweichung * 100:+.2f} % — SPLIT ERKANNT "
            f"(~{self.verhaeltnis:g}:1, Ex-Datum {self.split_datum.isoformat()}) "
            f"— kein Befund"
        )

    def als_report(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "kurs_ishares": round(self.kurs_ishares, 4),
            "kurs_kursquelle": round(self.kurs_yahoo, 4),
            "abweichung": round(self.abweichung, 8),
            "verhaeltnis": self.verhaeltnis,
            "split_datum": self.split_datum.isoformat(),
        }


@dataclass(frozen=True)
class Vergleich:
    """Das Ergebnis -- Geschwister von kursvergleich.Vergleich. Enthaelt
    bewusst keinen Kurs, der weiterverwendbar waere."""

    verdikt: str
    grund: str = ""
    fonds: str = ""
    stichtag: Date | None = None
    verglichen: tuple[str, ...] = ()
    ohne_vergleich: tuple[str, ...] = ()
    abweichler: tuple[Abweichung, ...] = ()
    split_erkannt: tuple[SplitErkannt, ...] = ()

    @classmethod
    def entfaellt(cls, grund: str) -> "Vergleich":
        return cls(verdikt="entfallen", grund=grund)

    @property
    def verweigert(self) -> bool:
        return self.verdikt == "verweigert"

    def als_report(self) -> dict:
        return {
            "verdikt": self.verdikt,
            "quelle": QUELLE,
            "fonds": self.fonds,
            "grund": self.grund,
            "stichtag": self.stichtag.isoformat() if self.stichtag else None,
            "toleranz": TOLERANZ,
            "zulass_abweichler": ZULASS_ABWEICHLER,
            "verglichen": len(self.verglichen),
            "ohne_vergleich": list(self.ohne_vergleich),
            "abweichler": [a.als_report() for a in self.abweichler],
            "split_erkannt": [s.als_report() for s in self.split_erkannt],
        }

    def protokoll(self) -> list[str]:
        if self.verdikt == "entfallen":
            return [f"[kursvergleich-us] entfiel: {self.grund}"]
        kopf = (
            f"[kursvergleich-us] Fonds {self.fonds}, Stichtag {self.stichtag}, "
            f"{len(self.verglichen)} Titel verglichen, "
            f"{len(self.ohne_vergleich)} ohne Vergleich, "
            f"{len(self.abweichler)} ueber {TOLERANZ * 100:.2f} % "
            f"(zugelassen: {ZULASS_ABWEICHLER}) — {self.verdikt.upper()}"
        )
        zeilen = [kopf]
        if self.split_erkannt:
            zeilen.append(
                f"[kursvergleich-us] {len(self.split_erkannt)} Titel als "
                f"Split erkannt (kein Befund): "
                + ", ".join(s.ticker for s in self.split_erkannt)
            )
        zeilen += [f"[kursvergleich-us]   {a.zeile()}" for a in self.abweichler]
        zeilen += [f"[kursvergleich-us]   {s.zeile()}" for s in self.split_erkannt]
        return zeilen

    def kurzfassung(self) -> str | None:
        """Dieselbe Formulierung wie bei DE -- `kurzfassung_aus_report` ist
        generisch ueber den Report-Block, keine zweite Fassung noetig."""
        return kurzfassung_aus_report(self.als_report())

    def als_status(self) -> dict:
        return {
            "verdikt": self.verdikt,
            "grund": self.grund,
            "fonds": self.fonds,
            "stichtag": self.stichtag.isoformat() if self.stichtag else None,
            "verglichen": len(self.verglichen),
            "abweichler": [a.ticker for a in self.abweichler],
            "split_erkannt": [s.ticker for s in self.split_erkannt],
        }


def _abweichung(ishares: float, yahoo: float) -> float:
    return (yahoo - ishares) / ishares


def _verhaeltnis_treffer(a: float, b: float) -> float | None:
    """Passt das Kursverhaeltnis a:b (oder b:a) zu einem gaengigen
    Split-Verhaeltnis? Gibt das getroffene Verhaeltnis zurueck, sonst None."""
    if a <= 0 or b <= 0:
        return None
    quotient = max(a, b) / min(a, b)
    for verhaeltnis in SPLIT_VERHAELTNISSE:
        if abs(quotient - verhaeltnis) / verhaeltnis <= SPLIT_ERKENNUNG_TOLERANZ:
            return verhaeltnis
    return None


def _split_im_fenster(splits: dict[Date, float], stichtag: Date) -> Date | None:
    """Ex-Datum eines Splits, falls eines im Fenster um den Stichtag liegt."""
    for datum in sorted(splits):
        frueher, spaeter = (datum, stichtag) if datum <= stichtag else (stichtag, datum)
        if handelstage_zwischen(frueher, spaeter) <= SPLIT_FENSTER_HANDELSTAGE:
            return datum
    return None


def _pruefe_split(
    ticker: str, name: str, kurs_ishares: float, kurs_yahoo: float,
    stichtag: Date, splits: dict[Date, float],
) -> SplitErkannt | None:
    """Beide Bedingungen muessen zutreffen -- siehe Moduldocstring. Eine
    allein (passendes Verhaeltnis OHNE Kalender-Beleg, oder umgekehrt)
    zaehlt NICHT als Split und faellt zurueck auf den normalen Abweichler."""
    verhaeltnis = _verhaeltnis_treffer(kurs_ishares, kurs_yahoo)
    if verhaeltnis is None:
        return None
    beleg = _split_im_fenster(splits, stichtag)
    if beleg is None:
        return None
    return SplitErkannt(
        ticker, name, kurs_ishares, kurs_yahoo,
        _abweichung(kurs_ishares, kurs_yahoo), verhaeltnis, beleg,
    )


def vergleiche(
    befund: Befund,
    fonds: str,
    roh_kurse: dict[str, dict[Date, float]],
    *,
    universum: set[str] | None = None,
    splits_oeffner=None,
) -> Vergleich:
    """Die Fonds-Bestandsliste gegen die (unbereinigten!) Schlusskurse
    stellen -- Geschwister von kursvergleich.vergleiche, mit derselben
    Begruendung fuer "unbereinigt" und "je Titel gegen den Stichtag SEINER
    Datei" (siehe dort). `befund` ist EIN Fonds (SXR8 primaer, IUSA
    Ausweich -- die Wahl trifft der Aufrufer, nicht dieses Modul), nicht
    eine Liste wie bei DE: die beiden US-Fonds bilden denselben Index ab,
    es gibt hier keine Vereinigung mehrerer Indizes zu bilden.

    `splits_oeffner(ticker) -> dict[Date, float]` ist die Test-Naht fuer
    den Yahoo-Split-Kalender; ohne Angabe der echte Netz-Abruf.
    """
    if befund.bestand_stand is None:
        return Vergleich.entfaellt(
            f"{fonds}: im Vorspann steht kein lesbarer Bestands-Stichtag."
        )
    stichtag = befund.bestand_stand

    gefunden: dict[str, object] = {}
    for kandidat in befund.kandidaten:
        if universum is not None and kandidat.ticker not in universum:
            continue
        gefunden.setdefault(kandidat.ticker, kandidat)

    if not gefunden:
        return Vergleich.entfaellt(
            f"kein einziger Titel der {fonds}-Bestandsliste liegt im "
            f"Universum — passen Universum und Bestandsliste noch zusammen?"
        )

    mit_kurs = {t: k for t, k in gefunden.items() if k.kurs is not None}
    if not mit_kurs:
        return Vergleich.entfaellt(
            f"die {fonds}-Bestandsliste fuehrt keine lesbare Kurs-Spalte "
            f"({len(gefunden)} Titel geprueft). Entweder ist die Spalte weg "
            f"oder ihre Zahlenschreibweise ist nicht eindeutig bestimmbar."
        )

    splits_oeffner = splits_oeffner or lade_splits_yahoo

    verglichen: list[str] = []
    ohne: list[str] = []
    abweichler: list[Abweichung] = []
    split_erkannt: list[SplitErkannt] = []

    for ticker in sorted(mit_kurs):
        kandidat = mit_kurs[ticker]
        if kandidat.waehrung and kandidat.waehrung != ERWARTETE_WAEHRUNG:
            ohne.append(f"{ticker} (Marktwaehrung {kandidat.waehrung})")
            continue
        reihe = roh_kurse.get(ticker)
        if not reihe:
            ohne.append(f"{ticker} (keine Kursreihe)")
            continue
        yahoo = reihe.get(stichtag)
        if yahoo is None:
            ohne.append(f"{ticker} (kein Kurs am {stichtag.isoformat()})")
            continue
        verglichen.append(ticker)
        delta = _abweichung(kandidat.kurs, yahoo)
        if abs(delta) <= TOLERANZ:
            continue
        try:
            splits = splits_oeffner(ticker) or {}
        except Exception:  # noqa: BLE001 - der Split-Kalender ist Beiwerk,
            # nie der Grund fuer einen Abbruch: ein Fehlschlag hier faellt
            # zurueck auf "kein Beleg" -- also normaler Abweichler, nicht
            # stillschweigend durchgewinkt.
            splits = {}
        treffer = _pruefe_split(
            ticker, kandidat.name, kandidat.kurs, yahoo, stichtag, splits
        )
        if treffer is not None:
            split_erkannt.append(treffer)
        else:
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
        fonds=fonds,
        stichtag=stichtag,
        verglichen=tuple(verglichen),
        ohne_vergleich=tuple(ohne),
        abweichler=tuple(abweichler),
        split_erkannt=tuple(split_erkannt),
    )


def abbruchtext(vergleich: Vergleich, markt: str) -> str:
    """Der Grund, mit dem der Stichtags-Lauf abbricht -- Geschwister von
    kursvergleich.abbruchtext, mit den US-eigenen Schwellen."""
    zeilen = [
        f"[{markt}] Kursvergleich VERWEIGERT den Stichtag: "
        f"{len(vergleich.abweichler)} von {len(vergleich.verglichen)} Titeln "
        f"weichen um mehr als {TOLERANZ * 100:.2f} % ab "
        f"(zugelassen sind {ZULASS_ABWEICHLER}).",
        "",
        f"Fonds: {vergleich.fonds}. Bestands-Stichtag: {vergleich.stichtag}.",
        "Verglichen wurde der BlackRock-Bewertungskurs gegen den "
        "unbereinigten Schlusskurs der Kursquelle.",
        "",
    ]
    zeilen += [f"  {a.zeile()}" for a in vergleich.abweichler]
    if vergleich.split_erkannt:
        zeilen += [
            "",
            f"({len(vergleich.split_erkannt)} weitere Titel wurden als "
            f"Aktien-Split erkannt und zaehlen NICHT als Abweichler: "
            + ", ".join(s.ticker for s in vergleich.split_erkannt) + ")",
        ]
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


def lade_splits_yahoo(ticker: str) -> dict[Date, float]:  # pragma: no cover - Netzpfad
    """Der Yahoo-Split-Kalender eines Titels -- Ex-Datum -> Verhaeltnis.

    Fail-soft: liefert die Bibliothek nichts Brauchbares, kommt ein leeres
    Dict zurueck statt einer Ausnahme. `vergleiche()' behandelt "kein
    Beleg" ohnehin wie einen Fehlschlag hier -- ein normaler Abweichler,
    nie ein stilles Durchwinken.
    """
    import yfinance as yf

    try:
        serie = yf.Ticker(ticker).splits
    except Exception:  # noqa: BLE001 - Netzpfad, siehe Docstring
        return {}
    ergebnis: dict[Date, float] = {}
    for zeitpunkt, verhaeltnis in serie.items():
        try:
            datum = zeitpunkt.date()
        except AttributeError:
            continue
        try:
            ergebnis[datum] = float(verhaeltnis)
        except (TypeError, ValueError):
            continue
    return ergebnis
