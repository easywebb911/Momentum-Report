"""Anzeige: Kopfzeile, Ehrlichkeits-Anzeigen, Trend-Ampel, Farb-Semantik.

Der 390px-Nachweis (iPhone) steht in tests/design/test_layout_390.py und
misst im echten Browser; hier wird der Inhalt geprueft.
"""

from __future__ import annotations

import datetime as _dt
import math
import re
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
                "rank_12_1": 3,
                "rank_52w": 12,
                "rang": 1,
            },
            {
                "ticker": "BBB",
                "name": "Zweite AG",
                "score": 88.0,
                "momentum_12_1": -0.1234,
                "high_52w": 0.7,
                "kurs_stichtag": 50.0,
                "rank_12_1": 40,
                "rank_52w": 1,
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


def _view_de(**kwargs) -> MarketView:
    """Zweiter Markt — fuer die Pruefung auf eindeutige SVG-ids."""
    return MarketView(
        market=MARKETS_BY_KEY["de"],
        ranking=_ranking(**kwargs),
        price_asof=Date(2026, 8, 3),
        prices={"AAA": 1.0, "BBB": 2.0},
        next_ranking_date=Date(2026, 8, 31),
    )


def test_kopfzeile_zeigt_ranking_naechsten_stichtag_und_kursdatum():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert "Ranking vom 31.07. · nächstes am 31.08. · Kurse vom 03.08.2026" in html


def test_die_uebersicht_traegt_den_ehrlichkeits_block_nicht_mehr():
    """Produktentscheidung: die vier Karten stehen jetzt in der Methodik."""
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert 'class="disc-box"' not in html
    assert "disc-item" not in html
    for satz in ("Keine Einzelaktien-Prognose", "0,3 %", "Gewinner MINUS Verlierer"):
        assert satz not in html, satz
    # Der Haftungshinweis im Fuss bleibt, wo er ist.
    assert "Keine Anlageberatung" in html
    assert 'class="market"' in html, "es muss auch eine Markt-Sektion geben"


def test_alle_vier_ehrlichkeits_anzeigen_stehen_in_der_methodik():
    """Verlustfrei umgezogen: Titel, Text, Quelle und der Ampel-Verweis."""
    from momentum.render import HONESTY
    from momentum.sources import source

    html = render_methodik()
    assert "<h2>Ehrlich gesagt</h2>" in html
    assert 'class="disc-box" id="ehrlich-gesagt"' in html
    assert html.count('class="disc-item"') == 4

    for key, titel, text, _link in HONESTY:
        assert titel.replace("&", "&amp;") in html, titel
        # Der Text steht maskiert in der Seite (Gedankenstriche, Umlaute).
        anfang = text.split("—")[0].strip().replace("&", "&amp;")
        assert anfang in html, titel
        assert source(key).short.replace("&", "&amp;") in html, key

    # Der Verweis springt jetzt INNERHALB der Methodik zur Ampel-Erklaerung.
    assert '<a class="disc-link" href="#trend-ampel">' in html
    assert 'id="trend-ampel"' in html, "der Anker, auf den verwiesen wird"


def test_kein_verweis_zeigt_mehr_auf_den_alten_ort():
    """Nichts darf auf den Block auf der Uebersicht zeigen — den gibt es nicht."""
    index = render_index([_view(warnung=False)], Date(2026, 8, 3))
    methodik = render_methodik()
    assert "methodik.html#ehrlich-gesagt" not in index + methodik
    assert "index.html#ehrlich-gesagt" not in index + methodik
    # Die Trend-Ampel auf der Uebersicht verweist weiter auf die Methodik-Seite.
    assert 'href="methodik.html#trend-ampel"' in index


def test_die_methodik_sagt_die_beiden_haerten_nur_einmal():
    """Zusammengefuehrt statt gedoppelt: die Karten-Fassung gewinnt."""
    html = render_methodik()
    # frueher stand beides zusaetzlich als Aufzaehlungspunkt in "Klare Grenzen"
    assert "Keine Verlierer-Seite" not in html
    assert "Das steht auf der Startseite" not in html
    # ... und der Punkt verweist stattdessen nach oben
    assert '<a href="#ehrlich-gesagt">Ehrlich gesagt</a>' in html
    # Die Aussagen selbst sind weiterhin da — je einmal als Ehrlichkeits-
    # Karte. Dass sie zusaetzlich in der Quellen-Fussnote stehen, ist kein
    # Doppel, sondern der Beleg (SOURCES[...].claim).
    assert "Gewinner MINUS Verlierer" in html
    assert "0,3 %" in html
    ohne_belege = re.sub(r'<ul class="src-list">.*?</ul>', "", html, flags=re.S)
    assert ohne_belege.count("Gewinner MINUS Verlierer") == 1
    assert ohne_belege.count("0,3 %") == 1


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


def test_karte_zeigt_die_kacheln_und_das_ehrlichkeits_label():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    for label in ("12-1-Momentum", "52W-Hoch-Nähe", "Kurs (USD)"):
        assert label in html
    assert "keine Prognose für diese Aktie" in html
    assert 'class="card-ft"' in html


def test_karte_zeigt_beide_teil_raenge():
    """Bei Gleichgewichtung muss sichtbar sein, WOHER der Score kommt."""
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert 'class="metrics metrics--rang"' in html
    assert "Rang 12-1-Momentum" in html
    assert "Rang 52W-Hoch-Nähe" in html
    # AAA steht 3. in 12-1 und 12. in der 52W-Naehe, von 469 bewerteten.
    assert f"3.{NBSP}von{NBSP}469" in html
    assert f"12.{NBSP}von{NBSP}469" in html
    # BBB: 40. und 1.
    assert f"40.{NBSP}von{NBSP}469" in html
    assert f"1.{NBSP}von{NBSP}469" in html


def test_die_teil_raenge_zaehlen_gegen_die_bewerteten_titel():
    """"von N" ist die Zahl der BEWERTETEN Titel, nicht die Universumsgroesse."""
    view = _view(warnung=False)
    assert view.ranking["abdeckung"]["bewertet"] == 469
    assert view.ranking["abdeckung"]["universum"] == 500
    html = render_index([view], Date(2026, 8, 3))
    assert f"3.{NBSP}von{NBSP}469" in html
    assert f"3.{NBSP}von{NBSP}500" not in html


def test_die_methodik_erklaert_die_gleichgewichtung():
    html = render_methodik()
    assert "Beide Zutaten zählen gleich viel" in html
    assert "kein" in html and "Mischverhältnis" in html
    assert "George &amp; Hwang" in html
    assert "Gleichgewichtung die" in html
    assert "Teil-Ränge" in html
    assert "Gewicht 50 %" in html
    assert "50 × Perzentil(12-1-Momentum)" in html
    assert "50 × Perzentil(52-Wochen-Hoch-Nähe)" in html


def test_nirgends_steht_noch_ein_70_30():
    """Belegter Gegencheck ueber alles Ausgelieferte."""
    erzeugt = render_index([_view(warnung=False)], Date(2026, 8, 3)) + render_methodik()
    for datei in ("index.html", "methodik.html", "style.css", "app.js"):
        erzeugt += Path("docs", datei).read_text(encoding="utf-8")
    erzeugt += Path("README.md").read_text(encoding="utf-8")
    for verboten in ("Gewicht 70", "Gewicht 30", "70 × Perzentil", "30 × Perzentil", "70/30"):
        assert verboten not in erzeugt, verboten


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
    # Erlaubt ist --disc ausschliesslich an Ehrlichkeits-Aussagen. Das sind
    # drei: die Labels der vier Karten (.disc-title), der Fusssatz auf jeder
    # Titel-Karte (.card-ft) und der feste Satz auf der Konfluenz-Seite
    # (.konf-regel: "Hier wird nichts verrechnet"). Die Liste waechst NUR um
    # Stellen, die wirklich eine Einschraenkung aussprechen -- an Dekoration
    # hat diese Farbe nichts verloren.
    erlaubt = (".disc-title", ".card-ft", ".konf-regel")
    abschnitte = [
        block for block in css.split("}") if "var(--disc)" in block
    ]
    for block in abschnitte:
        selektor = block.split("{")[0].strip().splitlines()[-1].strip()
        assert selektor in erlaubt, selektor


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


# ------------------------------------------------------------- Rueckweg


def test_jede_unterseite_traegt_den_rueckweg():
    """In der PWA gibt es keine Zurueck-Taste — der Weg muss auf der Seite sein.

    Der Nachweis, dass er auch gross genug und sichtbar ist, steht im
    Browser-Test; hier wird geprueft, dass er ueberhaupt gerendert wird.
    """
    html = render_methodik()
    assert 'class="back" href="./index.html"' in html
    assert "Zurück zur Übersicht" in html
    assert 'class="hdr hdr--sub"' in html


def test_die_uebersicht_selbst_hat_keinen_rueckweg():
    """Sie IST das Ziel — ein Rueckweg auf sich selbst waere sinnlos."""
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    assert 'class="back"' not in html
    assert "hdr--sub" not in html


# --------------------------------------------------- Fernsteuerung des Laufs


@pytest.mark.parametrize("seite", ["index", "methodik"])
def test_beide_seiten_tragen_die_bedienelemente(seite):
    """Das Menue steht auf jeder Seite — also auch alles, was es braucht."""
    html = (
        render_index([_view(warnung=False)], Date(2026, 8, 3))
        if seite == "index"
        else render_methodik()
    )
    assert 'id="reload-btn"' in html and "Neu laden" in html
    assert 'id="recalc-btn"' in html and "Neu berechnen" in html
    assert 'id="lock-btn"' in html and "Sperren" in html
    assert 'id="tok-overlay"' in html
    assert 'id="runbar"' in html


@pytest.mark.parametrize("seite", ["index", "methodik"])
def test_das_ziel_des_dispatches_kommt_aus_der_konfiguration(seite):
    """Eine Wahrheit: Repository und Workflow stehen in config.py."""
    from momentum.config import REPO_SLUG, WORKFLOW_LAUF

    html = (
        render_index([_view(warnung=False)], Date(2026, 8, 3))
        if seite == "index"
        else render_methodik()
    )
    assert f'data-repo="{REPO_SLUG}"' in html
    assert f'data-workflow="{WORKFLOW_LAUF}"' in html


def test_der_dialog_erklaert_die_noetigen_rechte_und_verspricht_nichts_falsches():
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    for satz in (
        "Fine-grained",
        "Only select repositories",
        "Read and write",
        "IndexedDB",
        "28 Tage",
        "api.github.com",
    ):
        assert satz in html, satz
    # Das Eingabefeld darf den Token nicht offen zeigen und nicht vervollstaendigen.
    assert 'id="tok-input" type="password"' in html
    assert 'autocomplete="off"' in html


def test_im_ausgelieferten_stand_liegt_kein_echter_token():
    """Kein Token im Repo — als Muster geprueft, nicht als Vorsatz erklaert.

    Gesucht wird ein Token-KOERPER, nicht das Wort: der Dialog zeigt
    absichtlich `github_pat_…` als Platzhalter im Eingabefeld, und das ist
    ein Hinweis, kein Geheimnis.
    """
    import re

    echt = re.compile(r"(github_pat_|ghp_|gho_|ghs_)[A-Za-z0-9_]{20,}")
    erzeugt = render_index([_view(warnung=False)], Date(2026, 8, 3)) + render_methodik()
    assert echt.search(erzeugt) is None
    for datei in ("index.html", "methodik.html", "app.js", "style.css"):
        text = Path("docs", datei).read_text(encoding="utf-8")
        assert echt.search(text) is None, datei


def test_der_token_wird_nie_an_eine_adresse_gehaengt():
    """Textueller Gegencheck zu app.js — der Token gehoert in die Kopfzeile.

    Der Nachweis im laufenden Browser steht in tests/design; hier faellt
    schon beim Lesen auf, wenn jemand ihn in eine URL schreibt.
    """
    quelle = Path("docs/app.js").read_text(encoding="utf-8")
    assert '"Authorization": "Bearer " + token' in quelle
    for zeile in quelle.splitlines():
        gestutzt = zeile.strip()
        if gestutzt.startswith("//") or gestutzt.startswith("*"):
            continue
        if "token" in gestutzt and ("?" in gestutzt or "&" in gestutzt):
            assert "Authorization" in gestutzt, f"Token an einer Adresse: {gestutzt}"
    # Und nirgends eine Ausgabe, die ihn mitnehmen koennte.
    for verboten in ("console.log", "console.warn", "console.error", "alert("):
        assert verboten not in quelle, verboten


# --------------------------------------------------------------------------
# TREND-TACHO — reine Anzeige, nachgerechnet
# --------------------------------------------------------------------------


def test_null_prozent_stellt_die_nadel_exakt_senkrecht():
    """0 % ist der Umschlagpunkt rot/gruen — dort steht die Nadel oben."""
    from momentum.render import tacho_nadel, tacho_winkel

    assert tacho_winkel(0.0) == pytest.approx(90.0)
    x, y = tacho_nadel(0.0)
    assert x == pytest.approx(60.0, abs=1e-9), "Nadel nicht senkrecht"
    assert y == pytest.approx(64.0 - 46.0, abs=1e-9)


def test_plus_18_1_prozent_zeigt_nach_rechts_unter_45_grad():
    from momentum.render import tacho_nadel, tacho_winkel

    winkel = tacho_winkel(0.181)
    assert 0 < winkel < 45, winkel
    x, y = tacho_nadel(0.181)
    assert x > 60, "positive Rendite muss nach rechts zeigen"
    # unter 45 Grad heisst: tiefer als der 45-Grad-Punkt
    assert y > 64 - 46 * math.sin(math.radians(45))


def test_minus_7_4_prozent_zeigt_nach_links():
    from momentum.render import tacho_nadel, tacho_winkel

    assert tacho_winkel(-0.074) > 90
    x, _y = tacho_nadel(-0.074)
    assert x < 60, "negative Rendite muss nach links zeigen"


@pytest.mark.parametrize(
    "rendite,soll_winkel",
    [(0.40, 0.0), (0.25, 0.0), (1.5, 0.0), (-0.40, 180.0), (-0.25, 180.0), (-9.9, 180.0)],
)
def test_werte_ausserhalb_der_skala_werden_geklemmt(rendite, soll_winkel):
    """Die Nadel verlaesst den Bogen nie — Anschlag statt Zeigen ins Nichts."""
    from momentum.render import tacho_nadel, tacho_winkel

    assert tacho_winkel(rendite) == pytest.approx(soll_winkel)
    x, y = tacho_nadel(rendite)
    assert y == pytest.approx(64.0), "am Anschlag liegt die Nadel waagerecht"
    assert x == pytest.approx(106.0 if soll_winkel == 0 else 14.0)


def test_die_nadel_bleibt_immer_innerhalb_des_bogens():
    """Ueber die ganze Skala hinweg: nie ausserhalb des viewBox."""
    from momentum.render import tacho_nadel

    for tausendstel in range(-600, 601, 7):
        x, y = tacho_nadel(tausendstel / 1000)
        assert 0 <= x <= 120, (tausendstel, x)
        assert 0 <= y <= 72, (tausendstel, y)


def test_gleicher_wert_ergibt_zeichen_fuer_zeichen_dasselbe_svg():
    from momentum.render import _trend_tacho

    a = _trend_tacho("us", "S&P 500", 0.181, False)
    b = _trend_tacho("us", "S&P 500", 0.181, False)
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")
    # ... und ein anderer Wert ergibt ein anderes SVG
    assert _trend_tacho("us", "S&P 500", 0.182, False) != a


def test_der_tacho_liest_nur_vorhandene_felder():
    """Kein zweites Kriterium: die Zahl im Bogen ist die des Reports."""
    from momentum.render import _trend_tacho

    svg = _trend_tacho("us", "S&P 500", 0.181, False)
    assert f"+18,1{NBSP}%" in svg
    ampel = _ranking(warnung=False)["trend_ampel"]
    html = render_index([_view(warnung=False)], Date(2026, 8, 3))
    from momentum.render import de_pct

    assert de_pct(ampel["rendite_12m"]) in html


def test_tacho_zustand_ohne_alarm():
    from momentum.render import _trend_tacho

    svg = _trend_tacho("us", "S&P 500", 0.152, False)
    assert 'class="tta"' in svg
    assert "tta--warn" not in svg
    assert 'stroke="#4ade80"\n            stroke-width="9" stroke-linecap="round"\n            opacity="0.85"' in svg
    assert 'stroke="#ef4444"\n            stroke-width="9" stroke-linecap="round"\n            opacity="0.55"' in svg
    assert 'fill="#4ade80"' in svg, "die Zahl ist gruen"
    assert "kein Alarm" in svg


def test_tacho_zustand_warnung():
    from momentum.render import _trend_tacho

    svg = _trend_tacho("de", "DAX", -0.084, True)
    assert 'class="tta tta--warn"' in svg
    assert 'opacity="0.9"' in svg and 'opacity="0.45"' in svg
    assert 'fill="#f87171"' in svg, "die Zahl ist rot"
    assert "Warnung" in svg


def test_die_vorlage_wird_unveraendert_uebernommen():
    """Bogen, Nabe und Strichbreiten stehen genau so in Easys Vorlage."""
    from momentum.render import _trend_tacho

    svg = _trend_tacho("us", "S&P 500", 0.0, False)
    assert 'viewBox="0 0 120 72"' in svg
    assert 'd="M12,64 A48,48 0 0 1 60,16"' in svg
    assert 'd="M60,16 A48,48 0 0 1 108,64"' in svg
    assert 'stroke-width="9" stroke-linecap="round"' in svg
    assert 'stroke="#e7ecf4" stroke-width="3.5" stroke-linecap="round"' in svg
    assert '<circle cx="60" cy="64" r="5" fill="#e7ecf4"/>' in svg
    assert 'x="60" y="60" text-anchor="middle"' in svg


def test_jeder_markt_bekommt_eine_eigene_id_ohne_kollision():
    html = render_index(
        [_view(warnung=False), _view_de(warnung=True)], Date(2026, 8, 3)
    )
    assert html.count('id="tta-us"') == 1
    assert html.count('id="tta-de"') == 1
    # INNEN keine einzige id — was nichts referenziert, kann nicht kollidieren.
    for svg in re.findall(r"<svg class=\"tta.*?</svg>", html, flags=re.S):
        assert svg.count("id=") == 1, svg[:200]
        assert "url(#" not in svg
    # und kein Zusammenstoss mit dem, was es sonst auf der Seite gibt
    ids = set(re.findall(r'id="([^"]+)"', html))
    assert "tta-us" in ids and "tta-de" in ids
    assert len(ids) == len(re.findall(r'id="([^"]+)"', html)), f"doppelte id: {ids}"


def test_der_tacho_traegt_eine_sprechende_beschriftung():
    from momentum.render import _trend_tacho

    svg = _trend_tacho("us", "S&P 500", 0.181, False)
    assert 'role="img"' in svg
    assert "aria-label=\"Trend-Kriterium S&amp;P 500: +18,1" in svg
    assert "kein Alarm" in svg
