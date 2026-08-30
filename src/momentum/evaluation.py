"""Monats-Rueckblick: was aus den eingefrorenen Top-5 seit ihrem Stichtag
bis zum naechsten Stichtag geworden ist.

REIN INFORMATIV -- KEIN WIRKSAMKEITSNACHWEIS UND KEINE VALIDIERUNG DER
METHODE. Die Literatur (Jegadeesh/Titman 1993, George/Hwang 2004) ist
bereits belegt (siehe sources.py); dieses Modul beweist nichts nach,
sondern haelt nur fest, was tatsaechlich passiert ist -- wie ein
Kontoauszug. Bei 5 Werten je Markt und Monat ist jede einzelne
Monats-Klassifikation statistisch reines Rauschen; der Pflicht-Hinweis
dazu steht in render.py (EVALUATION_HINWEIS) und auf der Seite selbst.

ZEITPUNKT DER ERFASSUNG: automatisches Nebenprodukt des Laufs, der das
NAECHSTE Monats-Ranking baut (siehe run.py, process_market). Der
Monatsende-Kurs eines Top-5-Titels aus Monat N ist exakt der Kurs, den
das Kurs-Bundle des Monats N+1 an dessen eigenem Stichtag ohnehin schon
enthaelt -- kein zusaetzlicher Abruf, kein zweiter Termin. Faellt ein
Titel bis dahin aus dem aktuellen Universum (delistet, aussortiert), hat
das Bundle keinen Kurs fuer ihn -- das wird ehrlich als "unbekannt"
gefuehrt, nicht als 0 % oder stillschweigend weggelassen.

Wie eingefrorene Rankings (siehe ranking.py) wird ein einmal geschriebener
Rueckblick NIE wieder ueberschrieben.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .config import TOP_N, Market
from .data import PriceBundle

Date = _dt.date

EVAL_DIR = Path("data/evaluation")

# Klassifikations-Schwelle, per Rueckfrage von Easy festgelegt (nicht vom
# Werkzeug geraten): |Veraenderung| <= 2 % zaehlt neutral, der Randwert
# selbst zaehlt zu neutral (siehe klassifiziere() unten -- deterministisch,
# keine Grauzone).
NEUTRAL_SCHWELLE = 0.02


class EvaluationBereitsVorhanden(Exception):
    """Ein Monats-Rueckblick ist eingefroren und wird nie neu geschrieben."""


def klassifiziere(veraenderung: float | None, schwelle: float = NEUTRAL_SCHWELLE) -> str:
    """"positiv" / "neutral" / "negativ" / "unbekannt" -- immer dasselbe
    Ergebnis bei denselben Eingaben, kein Sonderfall.

    Randwert |Veraenderung| == schwelle zaehlt zu "neutral" (abgeschlossenes
    Intervall [-schwelle, +schwelle]); "unbekannt" ausschliesslich bei
    fehlendem Monatsende-Kurs (veraenderung is None), NIE als 0 % gewertet.
    """
    if veraenderung is None:
        return "unbekannt"
    if veraenderung > schwelle:
        return "positiv"
    if veraenderung < -schwelle:
        return "negativ"
    return "neutral"


def build_evaluation(
    prev_ranking: dict,
    market: Market,
    bundle: PriceBundle,
    end_asof: Date,
) -> dict:
    """Der Rueckblick auf EIN abgeschlossenes Monats-Ranking (`prev_ranking`).

    `end_asof` ist der Stichtag des NAECHSTEN Rankings -- sowohl das Datum,
    an dem der Kurs in `bundle` nachgeschlagen wird, als auch der Wert, der
    als `end_stichtag` im Ergebnis steht (siehe Modul-Docstring: beides ist
    absichtlich derselbe Tag).
    """
    titel = []
    for row in prev_ranking["rangliste"][:TOP_N]:
        ticker = row["ticker"]
        kurs_start = row["kurs_stichtag"]
        prices = bundle.adjusted.get(ticker) or {}
        kurs_end = prices.get(end_asof)
        # ERST runden, DANN klassifizieren -- sonst kann Gleitkomma-Rauschen
        # (z.B. 51/50-1 == 0.020000000000000018 statt exakt 0.02) einen
        # Titel, der als "+2,0 %" angezeigt wird, unsichtbar ueber die
        # Schwelle kippen. Klassifikation und Anzeige sehen so IMMER
        # denselben Wert (siehe klassifiziere() -- deterministisch, aber
        # nur bezogen auf den Wert, den es auch bekommt).
        veraenderung = (
            None if kurs_end is None else round(kurs_end / kurs_start - 1, 8)
        )
        titel.append(
            {
                "ticker": ticker,
                "name": row["name"],
                "kurs_start": kurs_start,
                "kurs_end": None if kurs_end is None else round(float(kurs_end), 4),
                "veraenderung": veraenderung,
                "klasse": klassifiziere(veraenderung),
            }
        )
    year, month = (int(x) for x in prev_ranking["ranking_monat"].split("-"))
    return {
        "schema": 1,
        "markt": market.key,
        "ausgewerteter_monat": f"{year:04d}-{month:02d}",
        "start_stichtag": prev_ranking["stichtag"],
        "end_stichtag": end_asof.isoformat(),
        "neutral_schwelle": NEUTRAL_SCHWELLE,
        "titel": titel,
    }


# --------------------------------------------------------------------------
# Einfrieren / Persistenz -- Spiegelbild von ranking.py
# --------------------------------------------------------------------------


def evaluation_path(market_key: str, year: int, month: int, root: Path = EVAL_DIR) -> Path:
    return Path(root) / f"{market_key}_{year:04d}-{month:02d}.json"


def dump_evaluation(evaluation: dict) -> str:
    return json.dumps(evaluation, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_evaluation(evaluation: dict, root: Path = EVAL_DIR) -> Path:
    """Rueckblick schreiben -- und einen bestehenden NIE ueberschreiben."""
    year, month = (int(x) for x in evaluation["ausgewerteter_monat"].split("-"))
    path = evaluation_path(evaluation["markt"], year, month, root)
    if path.exists():
        raise EvaluationBereitsVorhanden(
            f"{path} existiert bereits. Ein gebildeter Monats-Rueckblick ist "
            f"eingefroren und wird nicht neu geschrieben."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_evaluation(evaluation), encoding="utf-8")
    return path


def read_evaluation(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def all_evaluations(market_key: str, root: Path = EVAL_DIR) -> list[dict]:
    """Alle vorhandenen Rueckblicke eines Marktes, chronologisch aufsteigend."""
    root = Path(root)
    if not root.exists():
        return []
    files = sorted(root.glob(f"{market_key}_*.json"))
    return [read_evaluation(f) for f in files]
