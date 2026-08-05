"""Alle Stellschrauben als benannte Konstanten -- keine Magic Numbers im Code.

Wer hier etwas aendert, aendert eine dokumentierte Groesse. Jede gewichtete
Score-Komponente muss in sources.SCORE_COMPONENT_SOURCES einen Beleg haben;
das wird beim Import geprueft und bricht sonst sofort ab.
"""

from __future__ import annotations

from dataclasses import dataclass

from .sources import SCORE_COMPONENT_SOURCES

SCHEMA_VERSION = 1

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
    ),
)

MARKETS_BY_KEY = {m.key: m for m in MARKETS}


def _check_weights_are_backed() -> None:
    """Jede gewichtete Komponente braucht Belege -- sonst Importfehler."""
    weighted = {"momentum_12_1": WEIGHT_MOMENTUM_12_1, "high_52w": WEIGHT_HIGH_52W}
    missing = [k for k, w in weighted.items() if w and k not in SCORE_COMPONENT_SOURCES]
    if missing:
        raise RuntimeError(
            "Score-Komponente ohne Primaerquelle: "
            + ", ".join(missing)
            + " -- Eintrag in sources.SCORE_COMPONENT_SOURCES fehlt."
        )
    total = round(WEIGHT_MOMENTUM_12_1 + WEIGHT_HIGH_52W, 10)
    if total != 1.0:
        raise RuntimeError(f"Score-Gewichte summieren auf {total}, erwartet 1.0")


_check_weights_are_backed()
