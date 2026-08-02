"""Anzeige: Kopfzeile, Ehrlichkeits-Anzeigen, Trend-Ampel, Farb-Semantik.

Der 390px-Nachweis (iPhone) steht in tests/design/test_layout_390.py und
misst im echten Browser; hier wird der Inhalt geprueft.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.render import NBSP, MarketView, render_index, render_methodik

Date = _dt.date

LANGER_NAME = (
    "Verwaltungs- und Beteiligungsgesellschaft für internationale "
    "Halbleitertechnologie & Anlagenbau SE & Co. KGaA"
)


def _ranking(*, warnung: bool, name: str = "Beispiel AG") -> dict:
    return {
        "schema": 1,
        "markt": "us",
        "markt_name": "USA",
        "waehrung": "USD",
        "ranking_monat": "2026-07",
        "stichtag": "2026-07-31",
        "universum": {
            "bezeichnung": "S&P 500",
            "herkunft": "Testquelle",
            "stand": "2026-07-31",
            "titel_gesamt": 500,
        },
        "methode": {},
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
            "ohne_ausreichende_historie": ["XYZ"],
            "bewertet": 469,
        },
        "rangliste": [
            {
                "ticker": "AAA",
                "name": name,
                "score": 97.53,
                "momentum_12_1": 0.4211,
                "high_52w": 0.9812,
                "kurs_stichtag": 123.45,
                "rang": 1,
            },
            {
                "ticker": "BBB",
                "name": "Zweite AG",
                "score": 88.0,
                "momentum_12_1": -0.1234,
                "high_52w": 0.7,
                "kurs_stichtag": 50.0,
                "rang": 2,
            },
        ],
        "top": ["AAA", "BBB"],
    }


def _view(**kwargs) -> MarketView:
    return MarketView(
        market=MARKETS_BY_KEY["us"],
        ranking=_ranking(**kwargs),
        price_asof=Date(2026, 8, 3),
        prices={"AAA": 130.5, "BBB": 48.25},
        next_ranking_date=Date(2026, 8, 31),
    )


def test_kopfzeile_zeigt_ranking_naechsten_stichtag_und_kursdatum():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert "Ranking vom 31.07. · nächstes am 31.08. · Kurse vom 03.08.2026" in html


def test_alle_vier_ehrlichkeits_anzeigen_stehen_prominent_auf_der_seite():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    kopf, _, rest = html.partition('<section class="market">')
    assert "Keine Einzelaktien-Prognose" in kopf
    assert "Portfolio-Statistik" in kopf
    assert "0,3 %" in kopf
    assert "Gewinner MINUS Verlierer" in kopf
    assert 'href="methodik.html#trend-ampel"' in kopf
    assert rest, "es muss auch eine Markt-Sektion geben"


def test_trend_ampel_warnung_traegt_den_beauftragten_wortlaut():
    html = render_index([_view(warnung=True)], Date(2026, 8, 3))
    assert "Momentum-Gefahrenlage:" in html
    assert "Markt im 12-Monats-Minus" in html
    assert "Momentum-Einbrüche" in html
    assert "ampel--warn" in html
    assert "Daniel &amp; Moskowitz (2016)" in html


def test_ohne_warnung_dezente_ok_zeile():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert "ampel--ok" in html
    assert "Momentum-Gefahrenlage" not in html


def test_farb_semantik_gruen_nur_positiv_rot_nur_negativ():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    # AAA: +42,1 % -> pos ; BBB: -12,3 % -> neg
    assert f'<span class="m-val pos">+42,1{NBSP}%</span>' in html
    assert f'<span class="m-val neg">-12,3{NBSP}%</span>' in html
    # 52W-Naehe ist nie vorzeichenbehaftet und bekommt keine Farbe
    assert f'<span class="m-val">98,1{NBSP}%</span>' in html


def test_karte_zeigt_die_drei_kacheln_und_das_ehrlichkeits_label():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    for label in ("12-1-Momentum", "52W-Hoch-Nähe", "Kurs (USD)"):
        assert label in html
    assert "keine Prognose für diese Aktie" in html
    assert 'class="card-ft"' in html


def test_anzeige_kurs_kommt_aus_dem_tagesabruf_nicht_aus_dem_ranking():
    """Die Kurs-Kachel zeigt den aktuellen Kurs, nicht den vom Stichtag."""
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert f"${NBSP}130,50" in html      # aktueller Kurs
    assert f"${NBSP}123,45" not in html  # Kurs vom Stichtag


def test_langer_firmenname_bleibt_in_einer_zeile_mit_ellipsis():
    html = render_index([_view(warnung=False, name=LANGER_NAME)], Date(2026, 8, 3))
    assert LANGER_NAME.replace("&", "&amp;") in html
    css = Path("docs/style.css").read_text(encoding="utf-8")
    block = css.split(".cname {", 1)[1].split("}", 1)[0]
    assert "white-space: nowrap" in block
    assert "text-overflow: ellipsis" in block
    assert "overflow: hidden" in block


def test_sonderzeichen_werden_maskiert():
    html = render_index([_view(warnung=False, name='A & B <script>"x"')], Date(2026, 8, 3))
    assert "<script>" not in html.split("</head>")[1]
    assert "A &amp; B &lt;script&gt;" in html


def test_handelbarkeits_filter_wird_als_nicht_signal_ausgewiesen():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert "Handelbarkeits-Filter, kein Signal" in html


def test_ohne_ranking_wird_bewusst_nichts_gezeigt():
    leer = MarketView(MARKETS_BY_KEY["de"], {}, None, {}, Date(2026, 8, 31))
    html = render_index([leer], Date(2026, 8, 3))
    assert "Kein Ranking vorhanden" in html
    assert "Noch kein Ranking gebildet" in html


def test_design_tokens_stehen_exakt_so_im_stylesheet():
    css = Path("docs/style.css").read_text(encoding="utf-8")
    tokens = {
        "--bg": "#0a0c12",
        "--bg-card": "#141929",
        "--bg-hdr": "#0d1117",
        "--bg-met": "#1a2035",
        "--txt": "#e2e8f0",
        "--txt-sub": "#94a3b8",
        "--txt-dim": "#8b97a8",
        "--brd": "#1e2d4a",
        "--accent": "#3b82f6",
        "--radius": "14px",
        "--red": "#ef4444",
        "--ora": "#f59e0b",
        "--grn": "#22c55e",
        "--disc": "#ca8a04",
    }
    for token, wert in tokens.items():
        assert f"{token}: {wert};" in css, token
    assert "--shadow: 0 2px 12px rgba(0, 0, 0, .35);" in css
    assert "font-size: var(--app-fs, 16px)" in css


def test_karten_sheen_ist_das_familien_markenzeichen():
    css = Path("docs/style.css").read_text(encoding="utf-8")
    block = css.split(".card {", 1)[1].split("}", 1)[0]
    assert "linear-gradient(180deg, rgba(255, 255, 255, .05) 0%, rgba(0, 0, 0, .10) 100%)" in block
    assert "var(--bg-card)" in block
    assert "box-shadow: var(--shadow)" in block


def test_disc_farbe_nur_fuer_ehrlichkeits_labels():
    """--disc darf ausschliesslich an Ehrlichkeits-Labels haengen."""
    css = Path("docs/style.css").read_text(encoding="utf-8")
    treffer = [
        zeile.strip()
        for zeile in css.splitlines()
        if "var(--disc)" in zeile
    ]
    assert treffer
    # nur in den Regeln .disc-title und .card-ft
    abschnitte = [
        block for block in css.split("}") if "var(--disc)" in block
    ]
    for block in abschnitte:
        selektor = block.split("{")[0].strip().splitlines()[-1].strip()
        assert selektor in (".disc-title", ".card-ft"), selektor


@pytest.mark.parametrize("seite", ["index", "methodik"])
def test_pwa_einbindung_auf_beiden_seiten(seite):
    html = (
        render_index([_view(warnung=False)], Date(2026, 8, 3))
        if seite == "index"
        else render_methodik()
    )
    assert '<link rel="manifest" href="manifest.webmanifest">' in html
    assert '<meta name="theme-color" content="#0d1117">' in html
    assert 'href="icon.svg"' in html
    assert 'lang="de"' in html
    assert 'name="viewport"' in html


def test_menue_bietet_methodik_und_textgroesse():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert 'href="methodik.html"' in html
    assert "Textgröße" in html
    assert 'data-fs="16"' in html
    assert 'id="menu-btn"' in html
