"""Gemeinsames Geruest der Browser-Tests: Browser, gerenderte Seite, Server.

Drei Testdateien teilen sich das:
  * test_layout_390.py    — Masse und Layout, geoeffnet ueber file://
  * test_lauf_steuerung.py — Bedienung (Neu laden, Lauf anstossen, Token).
    Die braucht einen echten HTTP-Ursprung: unter file:// sind fetch und
    IndexedDB in Chromium gesperrt, und genau die werden dort geprueft.
  * test_konfluenz.py     — der Abgleich zweier Werkzeuge. Braucht ebenfalls
    HTTP (die Seite laedt zwei JSON-Dateien) und den eingespielten
    Elliott-Bericht aus `ELLIOTT`.
"""

from __future__ import annotations

import datetime as _dt
import functools
import http.server
import json
import os
import shutil
import threading
from pathlib import Path

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.render import MarketView, render_index, render_konfluenz, render_methodik

Date = _dt.date
BREITE = 390
HOEHE = 844  # iPhone-Format

LANGER_NAME = (
    "Verwaltungs- und Beteiligungsgesellschaft für internationale "
    "Halbleitertechnologie & Anlagenbau SE & Co. KGaA"
)


def ranking(name: str, warnung: bool) -> dict:
    return {
        "markt": "us",
        "markt_name": "USA",
        "waehrung": "USD",
        "ranking_monat": "2026-07",
        "stichtag": "2026-07-31",
        "universum": {
            "bezeichnung": "S&P 500",
            "herkunft": "Test",
            "stand": "2026-07-31",
            "titel_gesamt": 500,
        },
        # Beide Zustaende des Zins-Abzugs stehen auf der Testseite: der
        # Warnmarkt rechnet MIT Geldmarktsatz (laengster Satz), der ruhige
        # ohne -- dort muss der Ausfall-Hinweis sichtbar sein. So messen die
        # 390-px-Tests beide Textlaengen, ohne eine zweite Seite zu bauen.
        "trend_ampel": {
            "index_ticker": "^SP500TR",
            "index_name": "S&P 500",
            "rendite_12m": -0.084 if warnung else 0.152,
            "riskfree_12m": 0.037 if warnung else None,
            "riskfree_quelle": (
                "^IRX (13-Wochen-T-Bill), Tagesmittel über 12 Monate"
                if warnung
                else "nicht erreichbar"
            ),
            "ueberschuss_12m": -0.121 if warnung else 0.152,
            "warnung": warnung,
        },
        "abdeckung": {
            "universum": 500,
            "mit_kursen": 498,
            "nach_handelbarkeit": 470,
            "ohne_handelbarkeit": 28,
            "ohne_ausreichende_historie": [],
            "bewertet": 470,
        },
        "rangliste": [
            {
                "ticker": "BRK-B" if i == 0 else f"TICK{i}",
                "name": name if i == 0 else f"Beispielgesellschaft {i} AG",
                "score": 100.0 - i * 3.7,
                "momentum_12_1": 1.2345 if i % 2 == 0 else -0.4321,
                "high_52w": 0.9876,
                "kurs_stichtag": 1234.56,
                "rank_12_1": i + 1,
                "rank_52w": 470 - i,
                "rang": i + 1,
            }
            for i in range(5)
        ],
        "top": ["BRK-B", "TICK1", "TICK2", "TICK3", "TICK4"],
    }


# Beschreibende Angaben, wie sie der Bootstrap schreibt. TICK4 fehlt in der
# DE-Fassung mit Absicht — der Gedankenstrich-Fall gehoert auf die Testseite.
META = {
    # Der lange Name bleibt beim ersten Titel — der Ellipsis-Fall soll auf
    # der Testseite stehen bleiben, auch wenn der Name jetzt aus der
    # Meta-Datei kommt statt aus dem Ranking.
    "BRK-B": {"name": LANGER_NAME, "sektor": "Financials"},
    "TICK1": {"name": "Arthur J. Gallagher & Co.", "sektor": "Informationstechnologie"},
    "TICK2": {"name": "Beispielgesellschaft 2 AG", "sektor": "Health Care"},
    "TICK3": {"name": "Beispielgesellschaft 3 AG", "sektor": "Industrials"},
    "TICK4": {"name": "Beispielgesellschaft 4 AG", "sektor": "Consumer Staples"},
}


# Der additive Export, wie ihn der Lauf schreibt. Dieselben Ticker wie oben --
# so laesst sich der Abgleich gegen echte Kunstdaten pruefen.
TOP5 = {
    "schema": 1,
    "maerkte": {
        "us": {
            "name": "USA",
            "stichtag": "2026-07-31",
            "top5": [
                {"ticker": t, "rang": i + 1, "score": 100.0 - i * 3.7,
                 "stichtag": "2026-07-31"}
                for i, t in enumerate(["BRK-B", "TICK1", "TICK2", "TICK3", "TICK4"])
            ],
        },
        "de": {
            "name": "Deutschland",
            "stichtag": "2026-07-31",
            "top5": [
                {"ticker": t, "rang": i + 1, "score": 90.0 - i * 2.5,
                 "stichtag": "2026-07-31"}
                for i, t in enumerate(["SAP.DE", "SIE.DE", "ALV.DE", "BAS.DE", "BMW.DE"])
            ],
        },
    },
}

# Der fremde Bericht -- Schema wie extern geprueft, NICHT aus dem fremden Repo
# gelesen. US enthaelt einen Treffer (TICK1), einen Short auf einem Titel, der
# in den Top-5 steht (TICK2 -- zaehlt NICHT) und einen Long ausserhalb der
# Top-5. DE enthaelt nur Titel ausserhalb der Top-5: der leere Zustand, also
# der Regelfall, steht damit auf derselben Testseite wie der Treffer.
#
# Der Score heisst im echten Bericht `score_heuristic`. Genau so steht er
# hier. NVDA traegt bewusst das alte `score` (die Rueckfallebene), BAYN.DE
# traegt keins von beidem -- daraus muss ein Gedankenstrich werden.
ELLIOTT = {
    "generated_at": "2026-08-02T22:10:00Z",
    "markets": {
        "US": {
            "candidates": [
                {"ticker": "TICK1", "direction": "long", "company_name":
                 "Arthur J. Gallagher & Co.", "close": 12.5,
                 "score_heuristic": 76.4},
                {"ticker": "TICK2", "direction": "short", "company_name":
                 "Beispielgesellschaft 2 AG", "close": 1234.56,
                 "score_heuristic": 88.9},
                {"ticker": "NVDA", "direction": "long", "company_name":
                 "NVIDIA Corporation", "close": 180.0, "score": 61.2},
            ]
        },
        "DE": {
            "candidates": [
                {"ticker": "DTE.DE", "direction": "long", "company_name":
                 "Deutsche Telekom AG", "close": 30.1,
                 "score_heuristic": 76.95},
                {"ticker": "BAYN.DE", "direction": "long", "company_name":
                 "Bayer AG", "close": 24.0},
            ]
        },
    },
}


@pytest.fixture(scope="session")
def seite(tmp_path_factory):
    """Vollstaendige Seite mit allen Kanten: langer Name, Warnlage, grosse Zahlen."""
    ziel = tmp_path_factory.mktemp("site")
    for datei in ("style.css", "app.js", "manifest.webmanifest", "icon.svg", "icon-maskable.svg"):
        shutil.copy(Path("docs") / datei, ziel / datei)
    views = [
        MarketView(
            MARKETS_BY_KEY["us"],
            ranking(LANGER_NAME, warnung=True),
            Date(2026, 8, 3),
            {"BRK-B": 987654.32, "TICK1": 12.5, "TICK2": 1234.56, "TICK3": 9.99, "TICK4": 100.0},
            Date(2026, 8, 31),
            META,
        ),
        MarketView(
            MARKETS_BY_KEY["de"],
            ranking("Kurz AG", warnung=False),
            Date(2026, 8, 3),
            {"BRK-B": 1.0, "TICK1": 2.0, "TICK2": 3.0, "TICK3": 4.0, "TICK4": 5.0},
            Date(2026, 8, 31),
            # TICK4 fehlt ABSICHTLICH: die Karte muss dann "—" zeigen.
            {t: e for t, e in META.items() if t != "TICK4"},
        ),
    ]
    (ziel / "index.html").write_text(render_index(views, Date(2026, 8, 3)), encoding="utf-8")
    (ziel / "methodik.html").write_text(render_methodik(), encoding="utf-8")
    (ziel / "konfluenz.html").write_text(render_konfluenz(), encoding="utf-8")
    (ziel / "data").mkdir(exist_ok=True)
    (ziel / "data" / "top5.json").write_text(
        json.dumps(TOP5, ensure_ascii=False), encoding="utf-8"
    )
    return ziel


def _chromium_pfad() -> str | None:
    """Vorinstalliertes Chromium finden, ohne etwas nachzuladen."""
    wurzel = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for muster in ("chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell"):
        treffer = sorted(wurzel.glob(muster))
        if treffer:
            return str(treffer[-1])
    return None


@pytest.fixture(scope="session")
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as pw:
        pfad = _chromium_pfad()
        try:
            b = pw.chromium.launch(executable_path=pfad) if pfad else pw.chromium.launch()
        except Exception as exc:  # pragma: no cover - kein Browser installiert
            pytest.skip(f"kein Chromium verfuegbar: {exc}")
        yield b
        b.close()


@pytest.fixture(scope="session")
def server(seite):
    """Die gerenderte Seite ueber HTTP anbieten.

    Ohne echten Ursprung kein fetch und kein IndexedDB — beides sperrt
    Chromium unter file:// ab. Port 0 laesst das Betriebssystem einen
    freien waehlen, damit parallele Laeufe sich nicht ins Gehege kommen.
    """
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(seite)
    )
    dienst = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    faden = threading.Thread(target=dienst.serve_forever, daemon=True)
    faden.start()
    try:
        yield f"http://127.0.0.1:{dienst.server_address[1]}"
    finally:
        dienst.shutdown()
        dienst.server_close()


@pytest.fixture
def oeffne(browser, seite):
    """Seite oeffnen und danach sicher wieder zumachen."""
    offen = []

    def _oeffne(datei, schriftgroesse=None, basis=None, bewegung=None, elliott=None):
        # bewegung="reduce" schaltet prefers-reduced-motion ein -- so laesst
        # sich pruefen, dass die Seite das wirklich respektiert.
        kontext = browser.new_context(
            viewport={"width": BREITE, "height": HOEHE},
            device_scale_factor=3,
            reduced_motion=bewegung,
        )
        offen.append(kontext)
        # KEIN Test geht nach draussen. Die Seite startet ihre Live-Abfrage
        # beim Aufbau von selbst -- ohne diese Sperre wuerde jeder
        # Browser-Test den echten Kurs-Dienst anrufen, und das Ergebnis
        # haenge davon ab, ob der Rechner gerade Netz hat. Genau daran ist
        # der erste CI-Lauf gescheitert.
        kontext.route("**/quote-proxy.easywebb.workers.dev/**", lambda route: route.abort())
        # Dasselbe fuer die Elliott-Quelle: die Konfluenz-Seite ruft sie beim
        # Aufbau von selbst. Ohne Einspielung wird abgebrochen -- das ist der
        # Fail-soft-Zustand und zugleich die Garantie, dass kein Test nach
        # draussen telefoniert. Mit elliott=<dict> antwortet die Sperre selbst.
        kontext.route(
            "**/easywebb911.github.io/Elliott-Report/**",
            (lambda route: route.abort())
            if elliott is None
            else (
                lambda route: route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=elliott if isinstance(elliott, str)
                    else json.dumps(elliott, ensure_ascii=False),
                )
            ),
        )
        page = kontext.new_page()
        page.goto(f"{basis}/{datei}" if basis else (seite / datei).as_uri())
        if schriftgroesse:
            page.evaluate(
                "px => document.documentElement.style.setProperty('--app-fs', px + 'px')",
                schriftgroesse,
            )
        return page

    yield _oeffne
    for kontext in offen:
        kontext.close()
