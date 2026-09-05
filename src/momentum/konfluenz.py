"""Serverseitiger Konfluenz-Abgleich -- NUR fuer den Push, nicht fuer die
Seite.

Die Konfluenz-SEITE (docs/konfluenz.html) bleibt unveraendert: sie laedt
Top-5 und Elliott-Bericht weiterhin selbst im Browser und rechnet dort den
Abgleich (app.js, Funktionen `elliottLong`/`konfluenz`). Dieses Modul
dupliziert dieselbe, rein additive Vergleichslogik ein zweites Mal -- in
Python, fuer den Lauf -- weil ein Push aus dem Browser heraus nicht
verschickt werden kann. Beide Fassungen muessen bei gleichen Eingaben
dasselbe Ergebnis liefern; tests/unit/test_konfluenz_python.py haelt das
fest -- mit DENSELBEN Kunstdaten (TOP5, ELLIOTT), die auch
tests/design/test_konfluenz.py fuer die JS-Fassung importiert (aus
tests/design/conftest.py), nicht mit einer zweiten, abgeschriebenen
Kopie.

WOZU: Easy soll erfahren, wenn ein Titel NEU gleichzeitig im
Momentum-Top-5 und bei Elliott als Long-Kandidat steht -- ohne die Seite
selbst regelmaessig zu oeffnen. Ein bereits bekannter, weiterhin
bestehender Treffer loest NIE erneut einen Push aus (Ermuedungseffekt);
nur ein Treffer, der beim UNMITTELBAR VORHERIGEN Lauf noch nicht da war,
zaehlt als neu. Taucht ein einmal verschwundener Treffer spaeter wieder
auf, zaehlt das erneut als neu -- es wird bewusst KEINE Vollhistorie
gefuehrt, nur der jeweils letzte bekannte Stand (Easys Entscheid).

WANN GEPRUEFT WIRD: bei JEDEM werktaeglichen Lauf, nicht nur an einem
neuen Monats-Stichtag (Easys Entscheid) -- Elliotts Bericht kann sich
jederzeit aendern, auch wenn das Momentum-Top-5 zwischen zwei Stichtagen
unveraendert bleibt.

WOHER DIE ELLIOTT-DATEN KOMMEN: ein einfacher HTTPS-GET auf dieselbe
bereits oeffentliche JSON-Datei, die auch der Browser laedt
(ELLIOTT_URL unten) -- KEIN Zugriff auf das Elliott-GitHub-Repository
(kein Clone, keine Repo-API), exakt wie das Projekt es bei
iShares-CSVs, der EZB-Reihe und Yahoo-Kursen bereits tut.

FAIL-SOFT, unbedingt: schlaegt der Abruf fehl oder ist die Antwort nicht
lesbar, wird NICHTS verglichen, NICHTS geschrieben und NICHTS
verschickt -- der zuletzt bekannte Stand bleibt exakt so stehen, wie er
war. Wuerde stattdessen ein leerer Stand geschrieben, saehe der naechste
ERFOLGREICHE Lauf jeden bisherigen Treffer faelschlich als "neu" und
loeste einen falschen Push aus.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ELLIOTT_URL = "https://easywebb911.github.io/Elliott-Report/data/report.json"
STAND_PFAD = Path("data/konfluenz_stand.json")
TIMEOUT_SECONDS = 20


def _feld(objekt, namen, ersatz=None):
    """Erstes belegtes Feld aus einer Liste von Namen -- tolerant.

    Spiegelbild von app.js:feld().
    """
    if not isinstance(objekt, dict):
        return ersatz
    for name in namen:
        wert = objekt.get(name)
        if wert not in (None, ""):
            return wert
    return ersatz


def elliott_long(bericht: dict | None, markt_key: str) -> list[dict]:
    """Die Long-Kandidaten EINES Marktes aus dem Elliott-Bericht.

    Spiegelbild von app.js:elliottLong() -- dieselbe tolerante Feldwahl,
    nur direction/richtung == "long" zaehlt.
    """
    if not isinstance(bericht, dict):
        return []
    maerkte = bericht.get("markets") or bericht.get("maerkte")
    if not isinstance(maerkte, dict):
        return []
    eintrag = maerkte.get(markt_key.upper()) or maerkte.get(markt_key)
    if not isinstance(eintrag, dict):
        return []
    liste = eintrag.get("candidates") or eintrag.get("kandidaten")
    if not isinstance(liste, list):
        return []
    raus = []
    for kandidat in liste:
        if not isinstance(kandidat, dict):
            continue
        ticker = _feld(kandidat, ["ticker", "symbol"])
        if not isinstance(ticker, str) or not ticker:
            continue
        richtung = str(_feld(kandidat, ["direction", "richtung"], "")).lower()
        if richtung != "long":
            continue
        raus.append(
            {
                "ticker": ticker,
                "name": str(_feld(kandidat, ["company_name", "name", "firma"], "")),
                "score": _feld(kandidat, ["score_heuristic", "score", "confidence"]),
            }
        )
    return raus


def konfluenz(top5: list[dict], longs: list[dict]) -> list[dict]:
    """Der Abgleich -- Spiegelbild von app.js:konfluenz(). Rein, ohne
    Seiteneffekte: nur zusammenlegen, nichts verrechnen."""
    nach_ticker = {k["ticker"]: k for k in longs}
    treffer = []
    for m in top5:
        e = nach_ticker.get(m["ticker"])
        if not e:
            continue
        treffer.append(
            {
                "ticker": m["ticker"],
                "name": e.get("name", ""),
                "momentum_rang": m["rang"],
                "momentum_score": m["score"],
                "elliott_score": e.get("score"),
            }
        )
    treffer.sort(key=lambda t: t["ticker"])
    return treffer


def hole_elliott_bericht(*, opener=urllib.request.urlopen) -> dict | None:
    """Fail-soft: liefert None bei JEDEM Fehler, wirft nie. `opener` ist die
    Test-Naht -- ohne sie der echte Netzabruf."""
    try:
        anfrage = urllib.request.Request(
            ELLIOTT_URL, headers={"Accept": "application/json"}
        )
        with opener(anfrage, timeout=TIMEOUT_SECONDS) as antwort:
            rohdaten = antwort.read()
        geparst = json.loads(rohdaten.decode("utf-8"))
        return geparst if isinstance(geparst, dict) else None
    except Exception:  # noqa: BLE001 - die fremde Seite darf nie den Lauf reissen
        return None


def schluessel(markt_key: str, ticker: str) -> str:
    return f"{markt_key}:{ticker}"


def lies_stand(pfad: Path = STAND_PFAD) -> set[str]:
    """Der zuletzt bekannte Konfluenz-Stand. Fehlt die Datei oder ist sie
    unlesbar, gilt das als "noch nie ein Treffer gesehen" -- NICHT als
    Fehler, der den Lauf stoppen muesste."""
    if not pfad.exists():
        return set()
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return set()
    return set(daten.get("treffer") or [])


def schreibe_stand(schluessel_menge: set[str], pfad: Path = STAND_PFAD) -> None:
    """Ueberschreibt den Stand vollstaendig mit der AKTUELLEN Menge -- das
    ist kein Archiv, sondern eine Momentaufnahme fuer den naechsten
    Vergleich (Easys Entscheid: Wiederauftauchen zaehlt erneut als neu)."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(
            {"schema": 1, "treffer": sorted(schluessel_menge)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def neue_konfluenz_treffer(
    top5_je_markt: dict[str, list[dict]],
    markt_namen: dict[str, str],
    bericht: dict,
    bisheriger_stand: set[str],
) -> tuple[list[dict], set[str]]:
    """Vergleicht den aktuellen Konfluenz-Stand gegen den letzten bekannten.

    Gibt (neue_treffer, aktueller_gesamt_stand) zurueck. `bericht` muss
    bereits erfolgreich geholt sein (siehe hole_elliott_bericht) -- diese
    Funktion selbst greift nicht ins Netz und ist damit ohne Netz testbar.
    Ein weggefallener Treffer taucht in `aktueller_gesamt_stand` einfach
    nicht mehr auf; er loest NIE einen Push aus, nur ein neu hinzugekommener
    tut das.
    """
    aktuell: set[str] = set()
    neu: list[dict] = []
    for markt_key, top5 in top5_je_markt.items():
        longs = elliott_long(bericht, markt_key)
        for treffer in konfluenz(top5, longs):
            eigener_schluessel = schluessel(markt_key, treffer["ticker"])
            aktuell.add(eigener_schluessel)
            if eigener_schluessel not in bisheriger_stand:
                neu.append(
                    {
                        **treffer,
                        "markt": markt_key,
                        "markt_name": markt_namen.get(markt_key, markt_key),
                    }
                )
    neu.sort(key=lambda t: (t["markt"], t["ticker"]))
    return neu, aktuell
