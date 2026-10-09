"""Split-Wächter: erkennt, ob eine Tages-Kursreihe vermutlich noch nicht
auf einen Aktiensplit nachbereinigt wurde -- NUR Erkennen und Melden,
nie Eingriff in Score, Ranking oder gespeicherte Ausgaben.

DER VORFALL, DER DIESES MODUL AUSLOEST (US 2026-08, MNST): Split 2:1 am
11.08.2026, Stichtag 28.08. Der Lauf vom 31.08. rechnete Momentum
-0,2278 statt der (im Nachhinein rekonstruierten) korrekten +0,5443 --
der aeltere Anker (Monat M-12 in momentum_12_1) war exakt um den Faktor 2
zu hoch, weil Yahoo die Vorgeschichte zu diesem Zeitpunkt noch nicht
auf den Split nachbereinigt hatte. Im September war die Reihe wieder
normal (nachbereinigt). Belegt per Handrechnung in der Sitzung vom
09.10.2026, nicht per Live-Abruf (siehe SESSION_HANDOVER.md).

DER MECHANISMUS, DER DAS SICHTBAR MACHT: Innerhalb EINER Kursreihe
bedeutet "noch nicht nachbereinigt" konkret: der aeltere Teil der Reihe
(vor Yahoos Nachbereinigungs-Stichtag) steht noch auf dem VOR-Split-
Niveau, der juengere Teil bereits auf dem NACH-Split-Niveau. Genau an
der Naht zwischen beiden Teilen -- einem einzelnen Tagespaar in der
Reihe -- springt der Kurs um den Split-Faktor, OHNE dass der Titel an
diesem Tag real so stark gestiegen oder gefallen waere. Dieses Modul
sucht exakt diese Naht: ein Tagespaar, dessen Kursverhaeltnis nahe einem
gaengigen Split-Verhaeltnis liegt.

WARUM "Roh (Close) gegen Adj Close vergleichen" NICHT der richtige Weg
ist (Easys Vorgabe, hier bestaetigt statt nur befolgt -- Kriterium 2/4):
data.py (Docstring, Zeile 6-14) und ranking.py (Zeile 209: `prices =
bundle.adjusted[ticker]`) belegen, dass momentum_12_1/high_52w_ratio
AUSSCHLIESSLICH mit `PriceBundle.adjusted` (Adj Close) rechnen --
`PriceBundle.close` (Roh-Close) geht in keine Kennzahl ein und wird nur
vom DE-Kursvergleich gebraucht (kursvergleich.py). Ein Vergleich Close
gegen Adj Close waere KEIN Split-Test: Yahoo passt bei einem echten Split
Close UND Adj Close gleich an (beide Reihen tragen denselben Split-
Faktor, weil ein Split keine Bar-Ausschuettung ist, anders als eine
Dividende). Ein Auseinanderlaufen der beiden Reihen zeigt also allenfalls
eine FAELLIGE Dividende, nicht die hier gesuchte Split-Nachbereinigungs-
Luecke. Deshalb prueft dieses Modul NUR INNERHALB von `bundle.adjusted`
selbst (ein Tag gegen den naechsten in genau der Reihe, die auch
momentum_12_1/high_52w_ratio sehen) -- nicht gegen eine zweite Reihe.

DIE VERHAELTNISLISTE (ZIEL_VERHAELTNISSE), selbst festgelegt und hier
begruendet: 2, 3, 4, 5, 10 -- Halbierung/Verdopplung, Drittelung/
Verdreifachung, Viertelung/Vervierfachung, Fuenftelung/Verfuenffachung,
Zehntelung/Verzehnfachung. Das deckt die in der Praxis gaengigen
Split-/Reverse-Split-Verhaeltnisse ab (siehe auch kursvergleich_us.py,
dieselbe Grundmenge). BEWUSST OHNE 3:2 (1,5): ein Kurseinbruch um ein
Drittel an einem einzelnen Tag ist real moeglich (Gewinnwarnung,
Herabstufung) und haeufig genug, dass 1,5 zu viele Fehlalarme ausloesen
wuerde -- explizite Vorgabe im Auftrag, hier uebernommen, weil die
uebrigen Ziel-Verhaeltnisse (2 aufwaerts) einen echten Eintages-Einbruch
oder -Sprung dieser Groesse in liquiden Standardwerten ungleich seltener
machen als einen Drittel-Verlust.

DIE TOLERANZ (TOLERANZ_RELATIV = 0,03, also ±3 % um jedes Ziel-
Verhaeltnis), selbst festgelegt und hier begruendet: Der Split-Faktor
selbst ist in Yahoos Nachbereinigung ein EXAKTER Multiplikator (2.0,
3.0, ...) auf die gesamte aeltere Teilreihe -- die MNST-Rekonstruktion
in dieser Sitzung ergab exakt Faktor 2, keine Naeherung. Ein echter,
aber zufaelliger Tagesschlusskurs-Sprung UEBERLAGERT diesen exakten
Faktor zusaetzlich mit der normalen Tagesbewegung des naechsten
Handelstags (typischerweise << 3 %) -- 3 % Toleranz deckt diese normale
Streuung ab, ohne die Ziel-Verhaeltnisse (2, 3, 4, 5, 10 -- jeweils
mindestens 33 % Abstand zueinander) jemals zu verwechseln und ohne in
die Naehe von 1,5 (ausgeschlossen) oder 1,0 (kein Sprung) zu reichen.
FRAGIL (Kriterium 6): dieser Wert ist eine Modellannahme, kein Beleg --
er beruht auf der Beobachtung eines einzigen Vorfalls (MNST). Haelt sich
diese Annahme bei kuenftigen Faellen nicht (z. B. ein Split, dessen
Nachbereinigungs-Naht zusaetzlich mit einem echten >3-%-Tagesausschlag
zusammenfaellt), gehoert das in eine Nachbesserung, nicht in ein
stillschweigendes Weiterlaufen -- deshalb der ausdrueckliche Hinweis in
der gemeldeten Nachricht, dass der Fund GEPRUEFT werden soll.

WAS DIESES MODUL NICHT TUT: Score, Perzentil, Rang, Ranking-Dateien und
status.json-Schema bleiben vollstaendig unberuehrt -- dieses Modul liest
nur `bundle.adjusted`, das run.py ohnehin schon fuer `build_ranking`
abgerufen hat, und schreibt NICHTS zurueck. Ein Fund aendert keine
einzige bestehende Ausgabe; er erzeugt ausschliesslich eine Log-Zeile
und einen Push.

FAIL-SOFT, wie jeder Waechter dieses Projekts: `pruefe_und_melde()`
faengt JEDE Ausnahme (Erkennung UND Push) selbst ab und gibt den Fehler
nur ins Protokoll -- ein Fehlschlag hier darf den eigentlichen Lauf
niemals gefaehrden. Der Aufrufer in run.py umschliesst den Aufruf
zusaetzlich mit einem eigenen try/except (Verteidigung in der Tiefe,
wie bei _zins_reihe).
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Mapping
from dataclasses import dataclass

Date = _dt.date
Series = Mapping[Date, float]

# Begruendung: siehe Modul-Docstring ("DIE VERHAELTNISLISTE").
ZIEL_VERHAELTNISSE: tuple[float, ...] = (2.0, 3.0, 4.0, 5.0, 10.0)

# Begruendung: siehe Modul-Docstring ("DIE TOLERANZ").
TOLERANZ_RELATIV = 0.03


@dataclass(frozen=True)
class SplitVerdacht:
    """Ein Fund: Tagespaar mit Kursverhaeltnis nahe einem Split-Verhaeltnis."""

    ticker: str
    tag_davor: Date
    tag_danach: Date
    verhaeltnis: float
    ziel: float


def _passendes_ziel(verhaeltnis: float) -> float | None:
    """Liefert das getroffene Ziel-Verhaeltnis, oder None bei keinem Treffer."""
    for ziel in ZIEL_VERHAELTNISSE:
        if abs(verhaeltnis - ziel) / ziel <= TOLERANZ_RELATIV:
            return ziel
    return None


def erkenne(ticker: str, prices: Series) -> SplitVerdacht | None:
    """Sucht in EINER Kursreihe die erste Naht mit split-verdaechtigem Sprung.

    Deterministisch: die Tage werden sortiert durchlaufen (die Eingabe ist
    ein Mapping, dessen Durchlaufreihenfolge nicht garantiert ist), und
    bei mehreren Treffern wird genau der CHRONOLOGISCH ERSTE zurueckgegeben
    -- derselbe Fund bei jedem Lauf mit derselben Eingabereihe, unabhaengig
    von Dict-Reihenfolge oder Python-Version.

    Das Verhaeltnis wird richtungs-unabhaengig als max/min der beiden
    Tageskurse gebildet -- das erkennt eine noch nicht nachbereinigte
    Vorgeschichte sowohl bei einem gewoehnlichen Split (die aeltere Teil-
    reihe ist zu HOCH, siehe MNST) als auch bei einem Reverse-Split (die
    aeltere Teilreihe ist zu NIEDRIG) mit derselben Formel.
    """
    tage = sorted(prices)
    for davor, danach in zip(tage, tage[1:]):
        p1, p2 = float(prices[davor]), float(prices[danach])
        if p1 <= 0 or p2 <= 0:
            continue
        verhaeltnis = max(p1, p2) / min(p1, p2)
        ziel = _passendes_ziel(verhaeltnis)
        if ziel is not None:
            return SplitVerdacht(ticker, davor, danach, verhaeltnis, ziel)
    return None


def pruefe_universum(adjusted: Mapping[str, Series]) -> list[SplitVerdacht]:
    """Prueft alle Ticker, alphabetisch sortiert -- deterministische Reihenfolge."""
    befunde = []
    for ticker in sorted(adjusted):
        fund = erkenne(ticker, adjusted[ticker])
        if fund is not None:
            befunde.append(fund)
    return befunde


def log_zeile(fund: SplitVerdacht) -> str:
    """Eine Log-Zeile je Fund -- Ticker, Datum, Verhaeltnis, keine Interpretation."""
    return (
        f"Split-Wächter: {fund.ticker} — {fund.tag_davor} -> {fund.tag_danach}: "
        f"Verhaeltnis {fund.verhaeltnis:.4f} (nahe {fund.ziel:g}:1). "
        f"Wert evtl. unzuverlaessig, pruefen."
    )


def _ntfy_block(fund: SplitVerdacht) -> tuple[str, str]:
    """(Name, Block-Text) fuer begrenze_bloecke() -- EIN Block je Fund."""
    text = (
        f"{fund.ticker}: {fund.tag_davor} -> {fund.tag_danach}, "
        f"Verhaeltnis {fund.verhaeltnis:.4f} (nahe {fund.ziel:g}:1). "
        f"Wert evtl. unzuverlaessig, pruefen."
    )
    return fund.ticker, text


def pruefe_und_melde(
    market_key: str,
    adjusted: Mapping[str, Series],
    *,
    melder=None,
    log=print,
) -> list[SplitVerdacht]:
    """Erkennen + EINE gebuendelte Meldung -- vollstaendig fail-soft.

    `melder` ist injizierbar (Test-Naht, wie bei jedem Waechter dieses
    Projekts). Importiert `push_split_verdacht` erst beim Aufruf (nicht
    am Modulkopf), damit ein Test ohne Netz/ntfy-Konfiguration das Modul
    trotzdem importieren kann.

    Jede Ausnahme -- bei der Erkennung selbst oder beim Versand -- wird
    hier abgefangen und nur protokolliert; der Rueckgabewert ist in jedem
    Fehlerfall eine leere Liste, NIE eine Ausnahme nach aussen. Das ist
    Absicht (Kriterium: fail-soft), nicht Nachlaessigkeit: dieser Wächter
    darf den eigentlichen Lauf unter keinen Umstaenden gefaehrden.
    """
    try:
        befunde = pruefe_universum(adjusted)
    except Exception as exc:  # noqa: BLE001 - der Lauf ist wichtiger als der Wächter
        log(f"[{market_key}] Split-Wächter fehlgeschlagen: {type(exc).__name__}: {exc}")
        return []

    if not befunde:
        return []

    for fund in befunde:
        log(f"[{market_key}] {log_zeile(fund)}")

    try:
        if melder is None:
            from .notify import push_split_verdacht as melder  # noqa: PLC0415

        eintraege = [_ntfy_block(f) for f in befunde]
        verschickt = melder(eintraege)
        log(
            f"[{market_key}] Split-Wächter: Push verschickt."
            if verschickt
            else f"[{market_key}] Split-Wächter: Push NICHT verschickt (siehe Meldung oben)."
        )
    except Exception as exc:  # noqa: BLE001 - ntfy darf den Lauf nie gefaehrden
        log(f"[{market_key}] Split-Wächter: Push fehlgeschlagen: {type(exc).__name__}: {exc}")

    return befunde
