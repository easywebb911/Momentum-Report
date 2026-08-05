"""Kurzfrist-Zins fuer das Trend-Kriterium — Ueberschuss statt Preisrendite.

Beleg: trend_filter (Moskowitz/Ooi/Pedersen 2012). Die Arbeit misst die
Zwoelf-Monats-Rendite UEBER dem Geldmarkt, nicht die reine Preisrendite.
Ohne den Abzug meldet ein Markt "kein Alarm", der ueber zwoelf Monate
weniger abgeworfen hat als Tagesgeld — und das ist nicht, was dort steht.

Zwei Quellen, je Waehrungsraum eine:
  * USD -- ^IRX (13-Wochen-T-Bill-Satz) ueber dieselbe Kursquelle wie die
    Indizes. Der "Kurs" dieser Reihe IST der annualisierte Satz in Prozent.
  * EUR -- die offizielle EZB-Datenschnittstelle, Reihe €STR
    (EST.B.EU000A2X2A25.WT), schluessellos als CSV.

NAEHERUNG, ausdruecklich benannt: Aus der taeglichen, annualisierten Rate
wird der arithmetische MITTELWERT ueber das Zwoelf-Monats-Fenster gebildet
und als Jahres-Zinssatz vom Index-Ertrag abgezogen. Das ist nicht dasselbe
wie die tatsaechlich aufgezinste Geldmarkt-Rendite desselben Zeitraums
(kein Zinseszins, keine Taggewichtung nach Kalendertagen). Bei den hier
auftretenden Groessenordnungen liegt der Unterschied im Bereich von
Zehntel-Prozentpunkten; die Naeherung steht so auch auf der Methodik-Seite.

FAIL-SOFT, aber niemals still: Ist eine Zinsquelle nicht erreichbar oder
unlesbar, rechnet das Kriterium wie zuvor (Rendite gegen null) und die
Anzeige sagt sichtbar, dass der Zins-Abzug fehlt. Der Lauf bricht dafuer
NIE ab -- die Ampel ist Anzeige, kein Gatter.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import urllib.request
from collections.abc import Mapping

from .scoring import index_12m_basis, is_finite

Date = _dt.date

# --- Quellen --------------------------------------------------------------

IRX_TICKER = "^IRX"

# Schluessellose CSV-Schnittstelle der EZB. `startPeriod` wird eingesetzt;
# ein Enddatum wird bewusst NICHT gesetzt -- gefiltert wird ohnehin auf das
# Fenster, und so faellt ein fehlender letzter Tag nicht durch ein zu enges
# Intervall unter den Tisch.
EZB_URL = (
    "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT"
    "?startPeriod={start}&format=csvdata"
)
EZB_TIMEOUT_SEKUNDEN = 20

QUELLE_US = "^IRX (13-Wochen-T-Bill), Tagesmittel über 12 Monate"
QUELLE_DE = "€STR (EZB, EST.B.EU000A2X2A25.WT), Tagesmittel über 12 Monate"

# Genau EIN Text fuer den Ausfall -- er steht im Report, in der Anzeige und
# im Log, damit niemand drei Formulierungen gegeneinander lesen muss.
QUELLE_FEHLT = "nicht erreichbar"


# --- Rechnen (rein, ohne Netz) --------------------------------------------


def mittel_rate(reihe: Mapping[Date, float], von: Date, bis: Date) -> float | None:
    """Mittlere annualisierte Rate im Fenster (von, bis], als Dezimalzahl.

    Fenster wie bei der Indexrendite: der Basistag selbst zaehlt NICHT mit,
    der Stichtag schon -- sonst waeren es zwei verschiedene Zeitraeume.

    Eingabe in Prozent (so liefern beide Quellen), Ausgabe geteilt durch
    100. Kein Wert im Fenster -> None, nicht 0: eine fehlende Quelle darf
    nie als "Zins war null" durchgehen.
    """
    werte = [
        float(wert)
        for tag, wert in reihe.items()
        if von < tag <= bis and is_finite(wert)
    ]
    if not werte:
        return None
    return sum(werte) / len(werte) / 100.0


def parse_ezb_csv(text: str) -> dict[Date, float]:
    """Die EZB-CSV lesen — Spalten ueber die Kopfzeile, nie ueber Position.

    Beispielzeile der Reihe:
        EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,2026-08-04,2.185,...

    Die Position von Datum und Wert ist NICHT zugesichert. Fehlt die
    Kopfzeile oder eine der beiden Spalten, wird nichts geraten: dann ist
    die Antwort unlesbar und der Fail-soft-Pfad greift.
    """
    if not text:
        return {}
    try:
        zeilen = list(csv.reader(io.StringIO(text)))
    except Exception:  # noqa: BLE001 - fremde Datei, jede Form ist moeglich
        return {}
    if not zeilen:
        return {}
    kopf = [feld.strip().upper() for feld in zeilen[0]]
    try:
        i_datum = kopf.index("TIME_PERIOD")
        i_wert = kopf.index("OBS_VALUE")
    except ValueError:
        return {}
    raus: dict[Date, float] = {}
    for zeile in zeilen[1:]:
        if len(zeile) <= max(i_datum, i_wert):
            continue
        try:
            tag = _dt.date.fromisoformat(zeile[i_datum].strip())
            wert = float(zeile[i_wert].strip())
        except ValueError:
            continue  # Leerzeilen, Feiertage ohne Wert, Fussnoten
        if is_finite(wert):
            raus[tag] = wert
    return raus


# --- Holen (Netz, fail-soft) ----------------------------------------------


def hole_ezb(start: Date, *, oeffner=None) -> dict[Date, float]:
    """€STR-Reihe ab `start` holen. Jeder Fehler ergibt ein leeres Dict."""
    url = EZB_URL.format(start=start.isoformat())
    if oeffner is None:  # pragma: no cover - echter Netzpfad

        def oeffner(adresse: str) -> str:
            with urllib.request.urlopen(adresse, timeout=EZB_TIMEOUT_SEKUNDEN) as antwort:
                return antwort.read().decode("utf-8", errors="replace")

    try:
        return parse_ezb_csv(oeffner(url))
    except Exception:  # noqa: BLE001 - Netz, DNS, Zertifikat, Format: alles fail-soft
        return {}


def riskfree_12m(
    waehrung: str,
    index_series: Mapping[Date, float],
    asof: Date,
    *,
    irx_series: Mapping[Date, float] | None = None,
    oeffner=None,
) -> tuple[float | None, str]:
    """Der Zinssatz fuer das Fenster der Indexrendite plus seine Herkunft.

    Entschieden wird nach WAEHRUNG, nicht nach Markt: der Geldmarktsatz
    gehoert zur Waehrung, in der der Index notiert. Kaeme je ein dritter
    Markt in derselben Waehrung dazu, braucht er hier keine Zeile.

    Rueckgabe (wert, quelle). `wert is None` heisst: keine Zahl bekommen --
    dann traegt `quelle` den Ausfalltext, und der Aufrufer rechnet ohne
    Abzug weiter.
    """
    try:
        von = index_12m_basis(index_series, asof)
    except Exception:  # noqa: BLE001 - ohne Fenster kein Zins, aber auch kein Abbruch
        return None, QUELLE_FEHLT

    if waehrung == "USD":
        satz = mittel_rate(irx_series or {}, von, asof)
        return (satz, QUELLE_US) if satz is not None else (None, QUELLE_FEHLT)
    if waehrung == "EUR":
        satz = mittel_rate(hole_ezb(von, oeffner=oeffner), von, asof)
        return (satz, QUELLE_DE) if satz is not None else (None, QUELLE_FEHLT)
    # Unbekannte Waehrung: lieber ohne Abzug und sichtbar, als mit dem
    # falschen Geldmarktsatz.
    return None, QUELLE_FEHLT
