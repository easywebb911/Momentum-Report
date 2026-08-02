"""DESIGN-CHECK auf 390 px Breite (iPhone) — gemessen, nicht geschaetzt.

Geprueft wird im echten Browser:
  * die Seite scrollt NICHT seitwaerts (kein Umbruch-Bruch)
  * kein einzelnes Element ragt ueber den Rand hinaus
  * eine Karte mit sehr langem Firmennamen bleibt heil
  * die drei Kennzahl-Kacheln stehen nebeneinander in einer Reihe
  * auch bei groesster Textgroesse (20px) bleibt alles im Rahmen

Laeuft nur, wenn Playwright samt Browser vorhanden ist (Marker "browser").
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
from pathlib import Path

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.render import MarketView, render_index, render_methodik

Date = _dt.date
BREITE = 390
HOEHE = 844  # iPhone-Format

pytestmark = pytest.mark.browser

LANGER_NAME = (
    "Verwaltungs- und Beteiligungsgesellschaft für internationale "
    "Halbleitertechnologie & Anlagenbau SE & Co. KGaA"
)


def _ranking(name: str, warnung: bool) -> dict:
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
        "trend_ampel": {
            "index_ticker": "^GSPC",
            "index_name": "S&P 500",
            "rendite_12m": -0.084 if warnung else 0.152,
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
                "rang": i + 1,
            }
            for i in range(5)
        ],
        "top": ["BRK-B", "TICK1", "TICK2", "TICK3", "TICK4"],
    }


@pytest.fixture(scope="module")
def seite(tmp_path_factory):
    """Vollstaendige Seite mit allen Kanten: langer Name, Warnlage, grosse Zahlen."""
    ziel = tmp_path_factory.mktemp("site")
    for datei in ("style.css", "app.js", "manifest.webmanifest", "icon.svg", "icon-maskable.svg"):
        shutil.copy(Path("docs") / datei, ziel / datei)
    views = [
        MarketView(
            MARKETS_BY_KEY["us"],
            _ranking(LANGER_NAME, warnung=True),
            Date(2026, 8, 3),
            {"BRK-B": 987654.32, "TICK1": 12.5, "TICK2": 1234.56, "TICK3": 9.99, "TICK4": 100.0},
            Date(2026, 8, 31),
        ),
        MarketView(
            MARKETS_BY_KEY["de"],
            _ranking("Kurz AG", warnung=False),
            Date(2026, 8, 3),
            {"BRK-B": 1.0, "TICK1": 2.0, "TICK2": 3.0, "TICK3": 4.0, "TICK4": 5.0},
            Date(2026, 8, 31),
        ),
    ]
    (ziel / "index.html").write_text(render_index(views, Date(2026, 8, 3)), encoding="utf-8")
    (ziel / "methodik.html").write_text(render_methodik(), encoding="utf-8")
    return ziel


def _chromium_pfad() -> str | None:
    """Vorinstalliertes Chromium finden, ohne etwas nachzuladen."""
    wurzel = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    for muster in ("chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell"):
        treffer = sorted(wurzel.glob(muster))
        if treffer:
            return str(treffer[-1])
    return None


@pytest.fixture(scope="module")
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


def _oeffne(browser, seite, datei, schriftgroesse=None):
    kontext = browser.new_context(
        viewport={"width": BREITE, "height": HOEHE}, device_scale_factor=3
    )
    page = kontext.new_page()
    page.goto((seite / datei).as_uri())
    if schriftgroesse:
        page.evaluate(
            "px => document.documentElement.style.setProperty('--app-fs', px + 'px')",
            schriftgroesse,
        )
    return kontext, page


@pytest.mark.parametrize("datei", ["index.html", "methodik.html"])
@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_kein_seitliches_scrollen(browser, seite, datei, schriftgroesse):
    kontext, page = _oeffne(browser, seite, datei, schriftgroesse)
    try:
        breite = page.evaluate("document.documentElement.scrollWidth")
        assert breite <= BREITE, (
            f"{datei} bei {schriftgroesse}px scrollt seitwaerts: {breite}px > {BREITE}px"
        )
    finally:
        kontext.close()


@pytest.mark.parametrize("schriftgroesse", [16, 20])
def test_kein_element_ragt_ueber_den_rand(browser, seite, schriftgroesse):
    kontext, page = _oeffne(browser, seite, "index.html", schriftgroesse)
    try:
        ueberstand = page.evaluate(
            """() => {
              const raus = [];
              document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && (r.right > window.innerWidth + 0.5 || r.left < -0.5)) {
                  raus.push(el.className + '|' + Math.round(r.left) + '..' + Math.round(r.right));
                }
              });
              return raus;
            }"""
        )
        assert ueberstand == [], f"Elemente ausserhalb des Bildschirms: {ueberstand}"
    finally:
        kontext.close()


def test_langer_firmenname_bleibt_einzeilig(browser, seite):
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        masse = page.evaluate(
            """() => {
              const el = document.querySelector('.cname');
              const stil = getComputedStyle(el);
              const r = el.getBoundingClientRect();
              return {
                zeilenhoehe: parseFloat(stil.lineHeight) || r.height,
                hoehe: r.height,
                abgeschnitten: el.scrollWidth > el.clientWidth,
                text: el.textContent.slice(0, 20),
              };
            }"""
        )
        assert masse["hoehe"] <= masse["zeilenhoehe"] * 1.35, "Firmenname bricht um"
        assert masse["abgeschnitten"] is True, "der lange Name muesste ellipsiert werden"
    finally:
        kontext.close()


def test_die_drei_kacheln_stehen_in_einer_reihe(browser, seite):
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        oberkanten = page.evaluate(
            """() => Array.from(document.querySelector('.card').querySelectorAll('.metric-box'))
                 .map(el => Math.round(el.getBoundingClientRect().top))"""
        )
        assert len(oberkanten) == 3
        assert len(set(oberkanten)) == 1, f"Kacheln umgebrochen: {oberkanten}"
    finally:
        kontext.close()


def test_karte_und_kacheln_haben_sinnvolle_breiten(browser, seite):
    """Bei 390 px: Karte ~358 px, Kacheln je gut 110 px — nichts wird gequetscht."""
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        masse = page.evaluate(
            """() => {
              const karte = document.querySelector('.card').getBoundingClientRect();
              const kachel = document.querySelector('.metric-box').getBoundingClientRect();
              return {karte: karte.width, kachel: kachel.width};
            }"""
        )
        assert 340 <= masse["karte"] <= 366, masse
        assert masse["kachel"] >= 100, masse
    finally:
        kontext.close()


def test_banner_skaliert_ueber_das_viewbox_verhaeltnis(browser, seite):
    """Volle Inhaltsbreite, Hoehe rein aus dem viewBox — kein festes Mass."""
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        masse = page.evaluate(
            """() => {
              const svg = document.querySelector('.banner > svg');
              const r = svg.getBoundingClientRect();
              const karte = document.querySelector('.card').getBoundingClientRect();
              return {
                breite: r.width, hoehe: r.height,
                inhaltsbreite: karte.width,
                links: r.left, rechts: r.right,
                hat_width: svg.hasAttribute('width'),
                hat_height: svg.hasAttribute('height'),
                anzeige: getComputedStyle(svg).display,
              };
            }"""
        )
        # Ohne width/height-Attribute traegt allein das viewBox die Hoehe.
        assert masse["hat_width"] is False and masse["hat_height"] is False
        assert masse["anzeige"] == "block"
        assert abs(masse["breite"] - masse["inhaltsbreite"]) < 1, masse
        assert masse["links"] >= -0.5 and masse["rechts"] <= BREITE + 0.5, masse
        soll = 1170 / 190
        ist = masse["breite"] / masse["hoehe"]
        assert abs(ist - soll) < 0.02, f"Seitenverhaeltnis verzogen: {ist:.3f} statt {soll:.3f}"
    finally:
        kontext.close()


def test_warnungen_stehen_ueber_dem_schmuckband(browser, seite):
    """Dekoration darf die vier Ehrlichkeits-Anzeigen nicht nach unten druecken."""
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        reihenfolge = page.evaluate(
            """() => [...document.querySelector('main').children]
                 .map(el => el.className.split(' ')[0])"""
        )
        assert reihenfolge.index("disc-box") < reihenfolge.index("banner"), reihenfolge
        assert reihenfolge.index("banner") < reihenfolge.index("market"), reihenfolge
    finally:
        kontext.close()


def test_das_banner_laedt_nichts_nach(browser, seite):
    """Inline und autark: kein Bild, kein Fetch, keine Schriftdatei."""
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        befund = page.evaluate(
            """() => {
              const svg = document.querySelector('.banner > svg');
              return {
                fremdverweise: [...svg.querySelectorAll('image, use, [href], [xlink\\\\:href]')].length,
                versteckt: svg.getAttribute('aria-hidden'),
                schriften: [...svg.querySelectorAll('[font-family]')]
                  .map(el => el.getAttribute('font-family')),
              };
            }"""
        )
        assert befund["fremdverweise"] == 0, "das Banner verweist nach draussen"
        assert befund["versteckt"] == "true", "dekoratives SVG muss aria-hidden sein"
        # Nur systemeigene Schriften — nichts, was nachgeladen werden muesste.
        for familie in befund["schriften"]:
            assert "Helvetica, Arial, sans-serif" == familie, familie
    finally:
        kontext.close()


def test_menue_laesst_sich_oeffnen_und_schliessen(browser, seite):
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        assert page.is_hidden("#overlay")
        page.click("#menu-btn")
        assert page.is_visible("#overlay")
        page.click(".sheet-close")
        assert page.is_hidden("#overlay")
    finally:
        kontext.close()


def test_textgroesse_skaliert_die_gesamte_oberflaeche(browser, seite):
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        vorher = page.evaluate(
            "document.querySelector('.score-val').getBoundingClientRect().height"
        )
        page.click("#menu-btn")
        page.click('.fs-btn[data-fs="20"]')
        nachher = page.evaluate(
            "document.querySelector('.score-val').getBoundingClientRect().height"
        )
        assert nachher > vorher * 1.15, (vorher, nachher)
        assert page.evaluate("document.documentElement.scrollWidth") <= BREITE
    finally:
        kontext.close()


def test_kontrast_der_gedimmten_schrift_ist_ausreichend(browser, seite):
    """--txt-dim #8b97a8 auf --bg #0a0c12 muss WCAG AA (4,5:1) schaffen."""
    kontext, page = _oeffne(browser, seite, "index.html")
    try:
        verhaeltnis = page.evaluate(
            """() => {
              const lum = hex => {
                const c = [1,3,5].map(i => parseInt(hex.substr(i,2),16)/255)
                  .map(v => v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4));
                return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
              };
              const wert = n => getComputedStyle(document.documentElement)
                .getPropertyValue(n).trim();
              const a = lum(wert('--txt-dim')), b = lum(wert('--bg'));
              return (Math.max(a,b)+0.05) / (Math.min(a,b)+0.05);
            }"""
        )
        assert verhaeltnis >= 4.5, f"Kontrast nur {verhaeltnis:.2f}:1"
    finally:
        kontext.close()
