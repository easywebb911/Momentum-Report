"""Alle Stellschrauben als benannte Konstanten -- keine Magic Numbers im Code.

Wer hier etwas aendert, aendert eine dokumentierte Groesse. Jede gewichtete
Score-Komponente muss in sources.SCORE_COMPONENT_SOURCES einen Beleg haben;
das wird beim Import geprueft und bricht sonst sofort ab.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .sources import SCORE_COMPONENT_SOURCES

# 1 -> 2: die Ranking-Datei traegt zusaetzlich den Block "kursvergleich"
# (Verdikt der zweiten, unabhaengigen Kursquelle). Rein additiv -- kein
# bestehendes Feld hat sich geaendert. Die Zahl wird trotzdem erhoeht: ein
# Leser, der Monate vergleicht, soll am Wert sehen koennen, ab wann es den
# Block gibt, statt sein Fehlen als "kein Vergleich gelaufen" zu deuten.
SCHEMA_VERSION = 2

# --- Score-Zusammensetzung ------------------------------------------------
# 50/50 = Konvention der Komposit-Literatur; ein belegtes optimales
# Verhaeltnis existiert nicht.
#
# Ausfuehrlich, weil hier zuvor eine unbelegte Setzung stand (70/30):
# Kein Paper liefert ein Mischverhaeltnis fuer 12-1-Momentum und
# 52-Wochen-Hoch-Naehe -- die Literatur vergleicht beide als GETRENNTE
# Strategien. George & Hwang (2004) fanden die 52-Wochen-Naehe in den USA
# sogar dominant; international bestehen beide Effekte unabhaengig
# voneinander. Wer mischt, mischt in dieser Literatur gleichgewichtet.
# Die frueheren 70/30 gewichteten damit ausgerechnet das in der
# Vergleichsstudie schwaechere Signal hoeher -- ohne Beleg dafuer.
#
# Belege: momentum_12_1 (Jegadeesh & Titman 1993) + skip_month
# (Jegadeesh 1990); high_52w (George & Hwang 2004).
WEIGHT_MOMENTUM_12_1 = 0.50
WEIGHT_HIGH_52W = 0.50
SCORE_SCALE = 100.0

# Messfenster der 12-1-Rendite, in Monaten, relativ zum Stichtag-Monat M.
# Zaehler = Ende Monat M-1, Nenner = Ende Monat M-12. Der juengste Monat (M)
# faellt damit heraus -- Beleg skip_month, NICHT optional.
MOMENTUM_LOOKBACK_MONTHS = 12
MOMENTUM_SKIP_MONTHS = 1

# 52 Wochen = 364 Kalendertage, Fenster inklusive Stichtag.
HIGH_52W_WINDOW_DAYS = 364

# --- Handelbarkeits-Filter (KEIN Signal) ----------------------------------
# Median-Tagesumsatz (Kurs wie gehandelt x Stueck) der letzten 3 Monate.
LIQUIDITY_MIN_MEDIAN_TURNOVER = 5_000_000
LIQUIDITY_WINDOW_MONTHS = 3

# --- Anzeige --------------------------------------------------------------
TOP_N = 5

# --- Fernsteuerung des Laufs aus der Seite heraus -------------------------
# Die Seite kann den Momentum-Lauf per workflow_dispatch anstossen. Damit
# das Frontend nicht raten muss, wohin, stehen Ziel-Repository und
# Workflow-Datei HIER und werden als data-Attribute in die Seite gerendert
# -- eine Wahrheit, kein zweiter Ort in JavaScript.
REPO_SLUG = "easywebb911/Momentum-Report"
WORKFLOW_LAUF = "lauf.yml"
# Agenten-Kontrolle (siehe agenten_kontrolle.py) liest hierueber die
# Laeufe des ntfy-Relays, um das Lebenszeichen des Waechter-Agenten zu
# pruefen.
WORKFLOW_NTFY_RELAY = "ntfy_relay.yml"

# --- Datenbeschaffung -----------------------------------------------------
# Puffer: der Nenner der 12-1-Rendite liegt bis zu ~395 Tage zurueck.
HISTORY_DAYS = 430
DOWNLOAD_CHUNK_SIZE = 40
DOWNLOAD_RETRIES = 3
DOWNLOAD_BACKOFF_SECONDS = 5

# Ein Ranking wird nur gebildet, wenn mindestens dieser Anteil des
# liquiditaetsgefilterten Universums verwertbare Kurse geliefert hat.
# Darunter: kein Ranking, lauter Fehlschlag -- lieber kein Stichtag als ein
# Stichtag auf Luecken.
MIN_UNIVERSE_COVERAGE = 0.90


# --- Gewichts-Fahrplan je Markt -------------------------------------------
# Die Score-Gewichte gelten JE MARKT und JE RANKING-MONAT. Ein Fahrplan ist
# eine aufsteigende Folge von Eintraegen "ab Ranking-Monat X gelten diese
# Gewichte"; es gilt der juengste Eintrag, dessen Beginn nicht nach dem
# Ranking-Monat liegt. Ausgewaehlt wird AUSSCHLIESSLICH nach dem Monat des
# Stichtags (asof) -- NIE nach dem Lauf-Datum. Ein im November nachgeholtes
# Oktober-Ranking rechnet deshalb mit den Oktober-Gewichten, und der
# Merge-Zeitpunkt einer Fahrplan-Aenderung spielt fuer die Rechnung keine
# Rolle.
#
# Der erste Eintrag jedes Fahrplans beginnt bei FAHRPLAN_BEGINN ("von
# Anfang an") -- damit gibt es fuer JEDEN Monat genau einen gueltigen
# Eintrag, nie eine Luecke, die still auf einen Ersatzwert fallen muesste.
#
# Entscheidung Easy, 01.11.2026 (Begruendung und Quellen samt ihrer
# Grenzen: SESSION_HANDOVER.md §4 Punkt 8):
#   USA: bis einschliesslich Ranking 2026-10 50/50, ab Ranking 2026-11
#        100 % 12-1-Momentum, 0 % 52-Wochen-Hoch.
#   Deutschland: unveraendert 50/50, ohne Wechsel.
# Keine Zwischenwerte (60/40 o. ae.) -- ausdruecklich als Parametersuche
# verworfen. Die 50/50-Eintraege verwenden die Konstanten WEIGHT_* oben
# selbst, damit DE und die US-Monate bis 2026-10 mit exakt denselben
# Gleitkommazahlen rechnen wie vor der Einfuehrung des Fahrplans.
FAHRPLAN_BEGINN: tuple[int, int] = (1, 1)


@dataclass(frozen=True)
class GewichtsEintrag:
    """Ab Ranking-Monat `ab` (Jahr, Monat) gelten diese beiden Gewichte."""

    ab: tuple[int, int]
    momentum_12_1: float
    high_52w: float


@dataclass(frozen=True)
class Market:
    key: str
    name: str
    flag: str
    currency: str
    currency_symbol: str
    # Beleg trend_filter (Moskowitz/Ooi/Pedersen 2012)
    index_ticker: str
    index_name: str
    universe_file: str
    # Fruehester UTC-Zeitpunkt, ab dem ein Lauf am letzten Werktag des
    # Monats ueberhaupt einen echten Tages-SCHLUSSkurs geliefert bekommen
    # haben kann -- siehe ranking.zu_frueh_fuer_stichtag(). BEWUSST kein
    # Handelskalender und keine Feiertagsliste (siehe resolve_asof): nur
    # ein grober Riegel gegen einen zu frueh ausgeloesten manuellen Lauf,
    # der sonst einen untertaegigen Zwischenkurs als Monats-Stichtag
    # einfrieren wuerde (realer Fall: Lauf 48, 31.08.2026 08:46 UTC,
    # DE-Kurs nachweislich untertaegig -- siehe SESSION_HANDOVER.md).
    stichtag_lauf_nicht_vor_utc: _dt.time
    # Score-Gewichte je Ranking-Monat -- siehe "Gewichts-Fahrplan" oben.
    # Bewusst OHNE Vorgabewert: jeder Markt nennt seinen Fahrplan selbst.
    gewichts_fahrplan: tuple[GewichtsEintrag, ...]

    def gewichte_fuer(self, year: int, month: int) -> tuple[float, float]:
        """(Gewicht 12-1, Gewicht 52W-Naehe) fuer den Ranking-Monat year-month.

        Rein aus (year, month) -- kein Zugriff auf Uhr oder Lauf-Datum.
        """
        gueltig = [g for g in self.gewichts_fahrplan if g.ab <= (year, month)]
        if not gueltig:
            raise RuntimeError(
                f"{self.key}: kein Gewichts-Eintrag fuer {year:04d}-{month:02d}"
            )
        eintrag = gueltig[-1]
        return eintrag.momentum_12_1, eintrag.high_52w


MARKETS: tuple[Market, ...] = (
    Market(
        key="us",
        name="USA",
        flag="\U0001F1FA\U0001F1F8",
        currency="USD",
        currency_symbol="$",
        # Performance-Index (Total Return), symmetrisch zum DAX: der DAX
        # rechnet Dividenden ein, ^GSPC nicht. Ein Kursindex gegen einen
        # Performance-Index zu stellen, waere ein Vergleich zweier
        # verschiedener Dinge -- und haette die US-Ampel systematisch zu
        # gutmuetig gemacht.
        index_ticker="^SP500TR",
        index_name="S&P 500",
        universe_file="universe/universe_us.txt",
        # NYSE schliesst lokal immer 16:00 ET -- in UTC je nach Jahreszeit
        # 20:00 (EDT, Sommer) oder 21:00 (EST, Winter). Absichtlich die
        # SPAETERE (Winter-)Zeit als Schwelle: im Sommer bis zu eine Stunde
        # konservativer als noetig, aber nie zu frueh -- unkritisch, da nur
        # den seltenen, verfrueht ausgeloesten Lauf betrifft.
        stichtag_lauf_nicht_vor_utc=_dt.time(21, 0),
        gewichts_fahrplan=(
            GewichtsEintrag(FAHRPLAN_BEGINN, WEIGHT_MOMENTUM_12_1, WEIGHT_HIGH_52W),
            GewichtsEintrag((2026, 11), 1.0, 0.0),
        ),
    ),
    Market(
        key="de",
        name="Deutschland",
        flag="\U0001F1E9\U0001F1EA",
        currency="EUR",
        currency_symbol="€",
        index_ticker="^GDAXI",
        index_name="DAX",
        universe_file="universe/universe_de.txt",
        # Xetra schliesst lokal immer 17:30 MEZ/MESZ -- in UTC je nach
        # Jahreszeit 15:30 (MESZ, Sommer) oder 16:30 (MEZ, Winter). Wie bei
        # den USA die SPAETERE (Winter-)Zeit als Schwelle.
        stichtag_lauf_nicht_vor_utc=_dt.time(16, 30),
        gewichts_fahrplan=(
            GewichtsEintrag(FAHRPLAN_BEGINN, WEIGHT_MOMENTUM_12_1, WEIGHT_HIGH_52W),
        ),
    ),
)

MARKETS_BY_KEY = {m.key: m for m in MARKETS}


def _pruefe_gewichtspaar(wo: str, w_momentum: float, w_high_52w: float) -> None:
    """Ein Gewichtspaar: Belege fuer jede Komponente mit Gewicht > 0, beide
    Gewichte in [0, 1], Summe 1. Gewicht 0 ist zulaessig (die Komponente
    zaehlt dann nicht und braucht fuer dieses Paar keinen Beleg)."""
    weighted = {"momentum_12_1": w_momentum, "high_52w": w_high_52w}
    missing = [k for k, w in weighted.items() if w and k not in SCORE_COMPONENT_SOURCES]
    if missing:
        raise RuntimeError(
            f"{wo}: Score-Komponente ohne Primaerquelle: "
            + ", ".join(missing)
            + " -- Eintrag in sources.SCORE_COMPONENT_SOURCES fehlt."
        )
    ausserhalb = [k for k, w in weighted.items() if not 0.0 <= w <= 1.0]
    if ausserhalb:
        raise RuntimeError(f"{wo}: Gewicht ausserhalb [0, 1]: {', '.join(ausserhalb)}")
    total = round(w_momentum + w_high_52w, 10)
    if total != 1.0:
        raise RuntimeError(f"{wo}: Score-Gewichte summieren auf {total}, erwartet 1.0")


def _check_weights_are_backed() -> None:
    """Jede gewichtete Komponente braucht Belege -- sonst Importfehler.

    Geprueft werden die Standard-Konstanten UND jeder Eintrag jedes
    Markt-Fahrplans; dazu die Form des Fahrplans selbst (nicht leer, erster
    Eintrag ab FAHRPLAN_BEGINN, Beginn-Monate streng aufsteigend und
    gueltig).
    """
    _pruefe_gewichtspaar("Standard", WEIGHT_MOMENTUM_12_1, WEIGHT_HIGH_52W)
    for market in MARKETS:
        plan = market.gewichts_fahrplan
        if not plan:
            raise RuntimeError(f"{market.key}: Gewichts-Fahrplan ist leer")
        if plan[0].ab != FAHRPLAN_BEGINN:
            raise RuntimeError(
                f"{market.key}: erster Fahrplan-Eintrag muss ab {FAHRPLAN_BEGINN} gelten"
            )
        for vorher, nachher in zip(plan, plan[1:]):
            if not vorher.ab < nachher.ab:
                raise RuntimeError(
                    f"{market.key}: Fahrplan nicht streng aufsteigend "
                    f"({vorher.ab} vor {nachher.ab})"
                )
        for eintrag in plan:
            if not 1 <= eintrag.ab[1] <= 12:
                raise RuntimeError(f"{market.key}: ungueltiger Monat in {eintrag.ab}")
            _pruefe_gewichtspaar(
                f"{market.key} ab {eintrag.ab[0]:04d}-{eintrag.ab[1]:02d}",
                eintrag.momentum_12_1,
                eintrag.high_52w,
            )


_check_weights_are_backed()
