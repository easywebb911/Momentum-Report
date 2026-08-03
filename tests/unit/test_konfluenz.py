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
from momentum.render import (
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
