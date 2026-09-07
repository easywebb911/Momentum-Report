"""Konfluenz: der additive Export und das Geruest der Seite.

Der Abgleich selbst lebt im Browser und wird dort geprueft
(tests/design/test_konfluenz.py). Hier steht, was ohne Browser pruefbar ist:

  * die Export-Datei hat genau die zugesagte Form -- und nur die
  * der Export ist ADDITIV: er fasst nichts Bestehendes an
  * die Seite spricht die feste Regel aus und verrechnet nirgends etwas
  * der leere Zustand ist an beiden Stellen wortgleich hinterlegt
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

from momentum.config import MARKETS_BY_KEY
from momentum.konfluenz import ELLIOTT_SEITE
from momentum.render import (
    KONFLUENZ_HISTORIE_LEER,
    KONFLUENZ_HISTORIE_REKONSTRUIERT_LABEL,
    KONFLUENZ_HISTORIE_REKONSTRUIERT_TEXT,
    KONFLUENZ_LEER,
    KONFLUENZ_SATZ,
    MarketView,
    render_konfluenz,
)
from momentum.run import _schreibe_top5

Date = _dt.date


def view(key: str, tickers: list[str]) -> MarketView:
    return MarketView(
        MARKETS_BY_KEY[key],
        {
            "stichtag": "2026-07-31",
            "rangliste": [
                {
                    "ticker": t,
                    "name": f"Firma {t}",
                    "rang": i + 1,
                    "score": 100.0 - i,
                    "momentum_12_1": 0.5,
                    "high_52w": 0.9,
                }
                for i, t in enumerate(tickers)
            ],
        },
        Date(2026, 8, 3),
        {},
        Date(2026, 8, 31),
    )


ACHT = [f"T{i}" for i in range(1, 9)]


def test_der_export_enthaelt_je_markt_genau_die_top_fuenf(tmp_path):
    _schreibe_top5([view("us", ACHT), view("de", ACHT)], tmp_path)
    daten = json.loads((tmp_path / "data" / "top5.json").read_text(encoding="utf-8"))

    assert daten["schema"] == 1
    assert sorted(daten["maerkte"]) == ["de", "us"]
    for markt in ("us", "de"):
        eintrag = daten["maerkte"][markt]
        assert eintrag["stichtag"] == "2026-07-31"
        assert [z["ticker"] for z in eintrag["top5"]] == ACHT[:5]
        assert [z["rang"] for z in eintrag["top5"]] == [1, 2, 3, 4, 5]
        # Jede Zeile traegt genau vier Angaben. Mehr waere eine Einladung,
        # spaeter etwas zu verrechnen, was hier nichts zu suchen hat.
        for zeile in eintrag["top5"]:
            assert set(zeile) == {"ticker", "rang", "score", "stichtag"}
            assert zeile["stichtag"] == "2026-07-31"


def test_der_export_ist_deterministisch(tmp_path):
    """Ohne Zeitstempel: zweimal derselbe Inhalt, zweimal dieselbe Datei.
    Sonst entstuende bei jedem Lauf ein Commit ohne Aenderung."""
    ziel = tmp_path / "data" / "top5.json"
    _schreibe_top5([view("us", ACHT)], tmp_path)
    erst = ziel.read_text(encoding="utf-8")
    _schreibe_top5([view("us", ACHT)], tmp_path)
    assert ziel.read_text(encoding="utf-8") == erst
    assert "2026" in erst  # der Stichtag steht drin ...
    assert not re.search(r"\d{2}:\d{2}:\d{2}", erst)  # ... eine Uhrzeit nicht


def test_ohne_ranking_entsteht_keine_datei(tmp_path):
    """Fail-soft: lieber gar keine Datei als eine leere Behauptung."""
    leer = MarketView(MARKETS_BY_KEY["us"], {}, None, {}, Date(2026, 8, 31))
    _schreibe_top5([leer], tmp_path)
    assert not (tmp_path / "data" / "top5.json").exists()


def test_der_export_fasst_nichts_bestehendes_an(tmp_path):
    """ADDITIV heisst: alles, was vorher da war, ist nachher unveraendert da.
    Das ist zugleich der Rueckweg -- ein `git revert` laesst nichts zurueck
    ausser dieser einen zusaetzlichen Datei."""
    (tmp_path / "data").mkdir()
    fremd = tmp_path / "data" / "sonst.json"
    fremd.write_text('{"nicht": "anfassen"}', encoding="utf-8")
    (tmp_path / "index.html").write_text("<html>alt</html>", encoding="utf-8")

    _schreibe_top5([view("us", ACHT)], tmp_path)

    assert fremd.read_text(encoding="utf-8") == '{"nicht": "anfassen"}'
    assert (tmp_path / "index.html").read_text(encoding="utf-8") == "<html>alt</html>"
    assert sorted(p.name for p in (tmp_path / "data").iterdir()) == [
        "sonst.json", "top5.json",
    ]


# ------------------------------------------------------------- die Seite


def test_die_seite_spricht_die_regel_aus():
    html = render_konfluenz()
    assert "Hier wird nichts verrechnet" in html
    assert "kein doppelter Beleg" in html
    assert "keine höhere Trefferwahrscheinlichkeit" in html
    # Der Satz steht als Ganzes da, nicht in Bruchstuecken.
    assert KONFLUENZ_SATZ in html


def test_die_seite_verrechnet_nirgends_etwas():
    """Selbstkontrolle: kein gemeinsamer Wert, auch nicht in Worten. Was
    hier steht, sind zwei getrennte Zahlen -- nie eine dritte."""
    html = render_konfluenz().lower()
    for wort in ("kombiniert", "gewichtet", "gesamtscore", "gesamt-score",
                 "konfluenz-score", "trefferwahrscheinlichkeit von",
                 "bestätigt", "signalstärke"):
        assert wort not in html, f"Misch-Vokabel auf der Konfluenz-Seite: {wort}"


def test_die_seite_hat_einen_rueckweg_und_die_beiden_anker():
    html = render_konfluenz()
    # In der installierten PWA gibt es keine Zurueck-Taste.
    assert 'class="back" href="./index.html"' in html or 'href="./index.html"' in html
    assert 'class="back"' in html
    for anker in ('id="stand-momentum"', 'id="stand-elliott"',
                  'id="konf-hinweis"', 'id="konf-inhalt"'):
        assert anker in html, anker
    # Der Hinweis ist im Normalfall unsichtbar und meldet sich als Status.
    assert 'id="konf-hinweis" role="status" hidden' in html


def test_die_seite_holt_nichts_beim_laden_nach():
    """Kein fremdes Skript, kein fremdes Bild -- die Elliott-Daten kommen
    ausschliesslich als JSON aus app.js, und zwar erst im Browser."""
    html = render_konfluenz()
    # Gemeint sind Nachladungen (script/img/link), nicht Verweise zum
    # Antippen -- ein <a> holt von sich aus nichts.
    fremd = re.findall(r'<(?:script|img)[^>]+src="(https?://[^"]+)"', html)
    fremd += re.findall(r'<link[^>]+href="(https?://[^"]+)"', html)
    assert fremd == [], f"Die Seite laedt von aussen: {fremd}"


def test_der_leere_zustand_steht_an_beiden_stellen_wortgleich():
    """Der Text lebt zweimal: in render.py (fuer die Nachlese) und in app.js
    (wo er tatsaechlich gesetzt wird). Wenn er auseinanderlaeuft, faellt es
    hier auf und nicht erst auf der Seite."""
    js = Path("docs/app.js").read_text(encoding="utf-8")
    treffer = re.search(r'var LEER_TEXT\s*=\s*((?:"[^"]*"\s*\+?\s*)+);', js)
    assert treffer, "LEER_TEXT nicht gefunden"
    aus_js = "".join(re.findall(r'"([^"]*)"', treffer.group(1)))
    assert aus_js == KONFLUENZ_LEER

    # Und er bleibt, was er ist: eine Feststellung, keine Warnung.
    assert "Regelfall" in KONFLUENZ_LEER
    assert "!" not in KONFLUENZ_LEER


def test_das_menue_fuehrt_zur_konfluenz_seite():
    from momentum.render import render_methodik

    assert 'href="konfluenz.html"' in render_konfluenz()
    assert 'href="konfluenz.html"' in render_methodik()


# --------------------------------------------------------------- Historie


NEUER_TREFFER = {
    "markt": "us",
    "markt_name": "USA",
    "ticker": "NVDA",
    "name": "NVIDIA Corp",
    "momentum_rang": 2,
    "momentum_score": 91.3,
    "momentum_stichtag": "2026-08-31",
    "elliott_score": 76.4,
    "elliott_close": 180.0,
}


def test_ohne_historie_erscheint_der_leerzustand_nicht_als_fehler():
    """Eine leere Historie ist der Regelfall zu Beginn -- kein Fehlerbild,
    keine Warnfarbe."""
    for historie in (None, []):
        html = render_konfluenz(historie)
        assert KONFLUENZ_HISTORIE_LEER in html
        assert "<h2>Historie</h2>" in html
        assert 'class="konf-hist-leer"' in html
        assert "konf-hist-karte" not in html


def test_ein_historie_eintrag_zeigt_alle_zugesagten_werte():
    html = render_konfluenz([NEUER_TREFFER])
    assert KONFLUENZ_HISTORIE_LEER not in html
    assert "NVDA" in html
    assert "NVIDIA Corp" in html
    assert "August 2026" in html
    assert "Momentum Rang 2" in html
    assert "91,3" in html
    assert "76,4" in html
    assert "180,00" in html
    assert f'href="{ELLIOTT_SEITE}"' in html
    # Kein Elliott-Wellen-Hinweistext -- der lebt im fremden Repo, das
    # dieses Projekt nicht anfassen darf (Easys Entscheid).
    assert "welle" not in html.lower()


def test_historie_fehlende_werte_faellen_nicht_auf_null_zurueck():
    """Fehlt ein Kurs, steht das ausdruecklich da -- nie eine erfundene
    Zahl."""
    treffer = {**NEUER_TREFFER, "elliott_close": None, "elliott_score": None}
    html = render_konfluenz([treffer])
    assert "Kurs unbekannt" in html
    assert "Elliott-Score" not in html


def test_historie_zeigt_neuestes_zuerst_und_bleibt_deterministisch():
    aelter = {**NEUER_TREFFER, "ticker": "ALT", "momentum_stichtag": "2026-06-30"}
    neuer = {**NEUER_TREFFER, "ticker": "NEU", "momentum_stichtag": "2026-08-31"}
    html_1 = render_konfluenz([aelter, neuer])
    html_2 = render_konfluenz([aelter, neuer])
    assert html_1 == html_2
    assert html_1.index("NEU") < html_1.index("ALT")


def test_ein_automatischer_treffer_zeigt_nie_das_rekonstruiert_label():
    """Ohne quelle-Feld ODER mit quelle == "automatisch" darf das
    Rekonstruiert-Label nie erscheinen -- weder heutiger Datenstand (Feld
    fehlt noch ueberall) noch kuenftige automatisch erfasste Treffer."""
    for treffer in (NEUER_TREFFER, {**NEUER_TREFFER, "quelle": "automatisch"}):
        html = render_konfluenz([treffer])
        assert KONFLUENZ_HISTORIE_REKONSTRUIERT_LABEL not in html
        assert "konf-hist-karte--rekonstruiert" not in html
        assert "Live gesehen" not in html


def test_ein_manuell_rekonstruierter_treffer_ist_klar_gekennzeichnet():
    """Kernanforderung: kein stillschweigendes Vermischen mit automatisch
    erfassten Treffern -- weder in der Rohdaten- noch in der Anzeige-
    Ebene."""
    treffer = {
        "markt": "de", "markt_name": "Deutschland", "ticker": "TKA.DE",
        "name": "THYSSENKRUPP AG", "momentum_rang": 4,
        "momentum_score": 82.738095, "momentum_stichtag": "2026-07-31",
        "elliott_score": None, "elliott_close": None,
        "quelle": "manuell_rekonstruiert",
        "sichtungsdaten": ["2026-08-17", "2026-08-24"],
    }
    html = render_konfluenz([treffer])
    assert 'class="konf-hist-karte konf-hist-karte--rekonstruiert"' in html
    assert KONFLUENZ_HISTORIE_REKONSTRUIERT_LABEL in html
    assert KONFLUENZ_HISTORIE_REKONSTRUIERT_TEXT in html
    assert "Kurs unbekannt" in html
    assert "Elliott-Score" not in html
    assert "Live gesehen: 17.08.2026, 24.08.2026" in html


def test_manuell_rekonstruierte_kurs_und_score_werden_nie_erfunden():
    """Die Elliott-Seite ist fuer rekonstruierte Treffer nicht belegbar --
    selbst wenn jemand versehentlich Werte einsetzt, bleibt der Karten-Bau
    tolerant; hier wird nur der zugesagte Fail-soft-Pfad (None) geprueft,
    das ist der einzige Zustand, den der Nachtrag tatsaechlich schreibt."""
    treffer = {
        "markt": "de", "markt_name": "Deutschland", "ticker": "SIE.DE",
        "name": "SIEMENS N AG", "momentum_rang": 5,
        "momentum_score": 81.547619, "momentum_stichtag": "2026-07-31",
        "elliott_score": None, "elliott_close": None,
        "quelle": "manuell_rekonstruiert", "sichtungsdaten": ["2026-08-27"],
    }
    html = render_konfluenz([treffer])
    assert "Kurs unbekannt" in html
    assert "None" not in html
    assert "Live gesehen: 27.08.2026" in html


def test_historie_verrechnet_nichts():
    html = render_konfluenz([NEUER_TREFFER]).lower()
    for wort in ("kombiniert", "gewichtet", "gesamtscore", "gesamt-score",
                 "konfluenz-score", "trefferwahrscheinlichkeit von",
                 "bestätigt", "signalstärke"):
        assert wort not in html, f"Misch-Vokabel in der Historie: {wort}"
