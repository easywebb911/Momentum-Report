"""Beschreibende Zusatzangaben je Ticker — Firmenname und Sektor.

REIN FUER DIE ANZEIGE. Diese Datei geht in keine Rechnung ein, in keinen
Score und in kein Ranking. Sie beantwortet nur die Frage „was ist das
eigentlich fuer eine Firma", die auf einer Karte mit vier Zahlen sonst
unbeantwortet bleibt.

WER SIE SCHREIBT: allein tools/build_universe.py, im selben Vorgang und
zum selben Zeitpunkt wie die Universums-Liste. Beide Quellen fuehren die
Angaben ohnehin mit -- die iShares-Bestandsliste in den Spalten „Name" und
„Sektor", der Wikipedia-Artikel in „Security" und „GICS Sector". Es wird
also nichts zusaetzlich beschafft, nur mitgeschrieben.

WARUM SIE NICHT IM EINGEFRORENEN RANKING STEHT: Ein geschriebenes Ranking
wird nie wieder angefasst -- es ist das Protokoll einer Rechnung. Der
Sektor ist aber keine Groesse dieser Rechnung, sondern eine Beschreibung,
die sich aendern darf (eine Firma wechselt die Branche, ein Name wird
angepasst). Sie liegt deshalb beim Universum und wird beim Anzeigen
nachgeschlagen. Praktischer Nebeneffekt: die Angaben erscheinen, sobald
die Datei existiert -- und nicht erst beim naechsten Monats-Ranking.

FAIL-SOFT, ausnahmslos: Fehlt die Datei, ist sie kaputt oder fehlt ein
einzelner Ticker, wird „—" angezeigt. Ein Lauf darf daran NIE scheitern.
Es waere absurd, ein geprueftes Ranking wegen einer fehlenden
Branchenbezeichnung zurueckzuhalten.
"""

from __future__ import annotations

import json
from pathlib import Path

META_DATEI = "universe/ticker_meta_{markt}.json"


def meta_pfad(markt_key: str, root: Path | str = ".") -> Path:
    return Path(root) / META_DATEI.format(markt=markt_key)


def load_meta(markt_key: str, root: Path | str = ".") -> dict[str, dict[str, str]]:
    """Ticker -> {"name": ..., "sektor": ...}. Bei jedem Problem: leeres Dict.

    Bewusst ohne jede Ausnahme nach aussen. Diese Angaben sind Beiwerk;
    ihr Fehlen ist ein Anzeige-Detail, kein Grund, irgendetwas abzubrechen.
    """
    pfad = meta_pfad(markt_key, root)
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - siehe Modul-Kopf: nie scheitern
        return {}
    if not isinstance(daten, dict):
        return {}
    sauber: dict[str, dict[str, str]] = {}
    for ticker, eintrag in daten.items():
        if not isinstance(ticker, str) or not isinstance(eintrag, dict):
            continue
        sauber[ticker] = {
            "name": str(eintrag.get("name", "") or ""),
            "sektor": str(eintrag.get("sektor", "") or ""),
        }
    return sauber


def dump_meta(eintraege: dict[str, dict[str, str]]) -> str:
    """Dateiinhalt erzeugen — bei gleichen Eingaben Zeichen fuer Zeichen gleich.

    Kein Zeitstempel, sortierte Schluessel: die Datei aendert sich nur,
    wenn sich ihr Inhalt aendert.
    """
    return (
        json.dumps(eintraege, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
