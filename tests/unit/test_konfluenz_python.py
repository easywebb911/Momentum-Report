"""Der serverseitige Konfluenz-Abgleich (src/momentum/konfluenz.py).

Wiederverwendet dieselben Kunstdaten (TOP5, ELLIOTT) wie die Browser-Tests
in tests/design/test_konfluenz.py -- das ist der Beleg, dass die Python-
Fassung bei gleichen Eingaben dasselbe rechnet wie app.js:konfluenz()/
elliottLong(), nicht nur behauptet wird, es zu tun.
"""

from __future__ import annotations

import json

import pytest

from momentum import konfluenz
from tests.design.conftest import ELLIOTT, TOP5


def _top5_je_markt():
    return {
        key: eintrag["top5"] for key, eintrag in TOP5["maerkte"].items()
    }


# --------------------------------------------------- Der Abgleich selbst


def test_elliott_long_liest_nur_long_kandidaten():
    """Spiegelt tests/design/test_konfluenz.py::test_ein_short_kandidat_zaehlt_nicht."""
    longs = konfluenz.elliott_long(ELLIOTT, "us")
    tickers = [k["ticker"] for k in longs]
    assert tickers == ["TICK1", "NVDA"], "Short-Kandidat (TICK2) als Long gelesen"


def test_elliott_long_liest_score_faellt_zurueck_auf_score_feld():
    """NVDA traegt nur `score`, nicht `score_heuristic` -- muss trotzdem
    ankommen (Rueckfallebene, wie im echten Bericht dokumentiert)."""
    longs = konfluenz.elliott_long(ELLIOTT, "us")
    nvda = next(k for k in longs if k["ticker"] == "NVDA")
    assert nvda["score"] == 61.2


def test_konfluenz_findet_den_gemeinsamen_titel():
    top5 = _top5_je_markt()["us"]
    longs = konfluenz.elliott_long(ELLIOTT, "us")
    treffer = konfluenz.konfluenz(top5, longs)
    assert [t["ticker"] for t in treffer] == ["TICK1"]
    t = treffer[0]
    assert t["momentum_rang"] == 2  # TICK1 ist der zweite Titel in TOP5["us"]
    assert t["elliott_score"] == 76.4
    assert t["momentum_stichtag"] == "2026-07-31"
    assert t["elliott_close"] == 12.5
    assert set(t) == {
        "ticker", "name", "momentum_rang", "momentum_score", "momentum_stichtag",
        "elliott_score", "elliott_close",
    }


def test_elliott_long_liest_den_kurs():
    """Die Historie braucht den Kurs zum Zeitpunkt des Treffers -- er kommt
    aus Elliotts eigenem `close`, nicht aus einer zweiten Quelle."""
    longs = konfluenz.elliott_long(ELLIOTT, "us")
    tick1 = next(k for k in longs if k["ticker"] == "TICK1")
    assert tick1["close"] == 12.5


def test_de_markt_ohne_ueberschneidung_bleibt_leer():
    """DE-Bericht fuehrt nur Titel ausserhalb der Top-5 -- der Regelfall."""
    top5 = _top5_je_markt()["de"]
    longs = konfluenz.elliott_long(ELLIOTT, "de")
    assert konfluenz.konfluenz(top5, longs) == []


def test_kaputter_bericht_ergibt_leere_liste_statt_absturz():
    assert konfluenz.elliott_long({"markets": "nicht-dict"}, "us") == []
    assert konfluenz.elliott_long(None, "us") == []
    assert konfluenz.elliott_long({}, "us") == []


# -------------------------------------------------- Stand lesen/schreiben


def test_stand_ohne_datei_ist_eine_leere_menge(tmp_path):
    assert konfluenz.lies_stand(tmp_path / "fehlt.json") == set()


def test_stand_schreiben_und_wieder_lesen(tmp_path):
    pfad = tmp_path / "konfluenz_stand.json"
    konfluenz.schreibe_stand({"us:TICK1", "de:SAP.DE"}, pfad)
    wieder = konfluenz.lies_stand(pfad)
    assert wieder == {"us:TICK1", "de:SAP.DE"}
    # Deterministisch lesbar/committerbar: sortierte Schluessel.
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    assert roh["treffer"] == sorted(roh["treffer"])


def test_kaputte_stand_datei_zaehlt_als_leer_nicht_als_fehler(tmp_path):
    pfad = tmp_path / "kaputt.json"
    pfad.write_text("{das ist kein json", encoding="utf-8")
    assert konfluenz.lies_stand(pfad) == set()


# ------------------------------------------------------- Neue Treffer


def test_kein_bisheriger_stand_macht_den_ersten_treffer_neu():
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    neu, aktuell = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    assert [t["ticker"] for t in neu] == ["TICK1"]
    assert neu[0]["markt"] == "us"
    assert neu[0]["markt_name"] == "USA"
    assert aktuell == {"us:TICK1"}


def test_automatisch_erfasste_treffer_tragen_die_quelle_automatisch():
    """Unterscheidet sie von manuell nachgetragenen Historie-Eintraegen
    (quelle == "manuell_rekonstruiert", siehe render.py) -- nur so bleiben
    beide Arten auf der Seite auseinanderhaltbar, nie stillschweigend
    vermischt."""
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    neu, _ = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    assert neu[0]["quelle"] == "automatisch"


def test_bekannter_treffer_bleibt_bestehen_aber_loest_nichts_aus():
    """DER Kernfall: derselbe Treffer wie beim letzten Lauf darf NIE wieder
    als 'neu' gelten -- sonst gaebe es bei jedem Lauf denselben Alarm."""
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    neu, aktuell = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand={"us:TICK1"}
    )
    assert neu == [], "ein unveraenderter Treffer hat erneut ausgeloest"
    assert aktuell == {"us:TICK1"}


def test_weggefallener_treffer_loest_keinen_push_aus():
    """Ein Treffer, der nicht mehr da ist, verschwindet aus `aktuell` --
    aber `neu` bleibt leer, es gibt keinen 'Treffer weg'-Push."""
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    # Stand behauptet einen Treffer, der es laut ELLIOTT/TOP5 nicht (mehr) ist.
    neu, aktuell = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT,
        bisheriger_stand={"us:TICK1", "de:SIE.DE"},
    )
    assert neu == []
    assert aktuell == {"us:TICK1"}, "de:SIE.DE ist keine echte Ueberschneidung mehr und muss verschwinden"


def test_wiederauftauchen_zaehlt_erneut_als_neu():
    """Easys Entscheid: keine Vollhistorie, nur der letzte bekannte Stand.
    Ein Treffer, der beim VORHERIGEN Lauf fehlte, ist neu -- auch wenn er
    vor Wochen schon einmal da war (das weiss dieser Vergleich gar nicht)."""
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    # bisheriger_stand ist LEER, obwohl TICK1 "frueher" (nicht mehr bekannt)
    # schon mal Treffer war -- muss trotzdem wieder als neu gelten.
    neu, _ = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    assert [t["ticker"] for t in neu] == ["TICK1"]


def test_mehrere_gleichzeitige_neue_treffer_kommen_sortiert():
    top5_je_markt = {
        "us": [{"ticker": "TICK1", "rang": 1, "score": 90.0}],
        "de": [{"ticker": "DTE.DE", "rang": 1, "score": 80.0}],
    }
    markt_namen = {"us": "USA", "de": "Deutschland"}
    neu, aktuell = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    assert [(t["markt"], t["ticker"]) for t in neu] == [
        ("de", "DTE.DE"), ("us", "TICK1"),
    ]
    assert aktuell == {"us:TICK1", "de:DTE.DE"}


def test_determinismus_gleiche_eingabe_immer_gleiches_ergebnis():
    top5_je_markt = _top5_je_markt()
    markt_namen = {"us": "USA", "de": "Deutschland"}
    lauf1 = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    lauf2 = konfluenz.neue_konfluenz_treffer(
        top5_je_markt, markt_namen, ELLIOTT, bisheriger_stand=set()
    )
    assert lauf1 == lauf2


# ------------------------------------------------------------- Historie


def test_historie_ohne_datei_ist_eine_leere_liste(tmp_path):
    assert konfluenz.lies_historie(tmp_path / "fehlt.json") == []


def test_historie_anhaengen_schreibt_und_haengt_an(tmp_path):
    pfad = tmp_path / "konfluenz_historie.json"
    treffer_1 = [{"markt": "us", "ticker": "TICK1", "momentum_stichtag": "2026-07-31"}]
    treffer_2 = [{"markt": "de", "ticker": "DTE.DE", "momentum_stichtag": "2026-08-31"}]

    ergebnis_1 = konfluenz.historie_anhaengen(treffer_1, pfad)
    assert ergebnis_1 == treffer_1
    assert konfluenz.lies_historie(pfad) == treffer_1

    ergebnis_2 = konfluenz.historie_anhaengen(treffer_2, pfad)
    assert len(ergebnis_2) == 2, "der erste Eintrag darf nicht verloren gehen"
    assert konfluenz.lies_historie(pfad) == ergebnis_2


def test_historie_ist_sortiert_nach_stichtag_markt_ticker(tmp_path):
    pfad = tmp_path / "konfluenz_historie.json"
    konfluenz.historie_anhaengen(
        [{"markt": "us", "ticker": "ZZZ", "momentum_stichtag": "2026-08-31"}], pfad
    )
    konfluenz.historie_anhaengen(
        [{"markt": "de", "ticker": "AAA", "momentum_stichtag": "2026-07-31"}], pfad
    )
    ergebnis = konfluenz.lies_historie(pfad)
    assert [t["ticker"] for t in ergebnis] == ["AAA", "ZZZ"]


def test_historie_kaputte_datei_zaehlt_als_leer_nicht_als_fehler(tmp_path):
    pfad = tmp_path / "kaputt.json"
    pfad.write_text("{das ist kein json", encoding="utf-8")
    assert konfluenz.lies_historie(pfad) == []


def test_historie_anhaengen_ist_additiv_und_der_rueckweg_ist_klar(tmp_path):
    """Wie schreibe_stand fuer den Stand: hier gibt's KEIN Ueberschreiben --
    ein `git revert` dieser Funktion liesse nur die neue Datei zurueck,
    nichts Bestehendes wuerde angefasst."""
    pfad = tmp_path / "konfluenz_historie.json"
    fremd = tmp_path / "sonst.json"
    fremd.write_text('{"nicht": "anfassen"}', encoding="utf-8")
    konfluenz.historie_anhaengen(
        [{"markt": "us", "ticker": "TICK1", "momentum_stichtag": "2026-07-31"}], pfad
    )
    assert fremd.read_text(encoding="utf-8") == '{"nicht": "anfassen"}'


# ------------------------------------------------------- Elliott-Abruf


def test_abruf_scheitert_ergibt_none_nie_eine_ausnahme():
    def kaputter_opener(*_args, **_kwargs):
        raise OSError("kein Netz")

    assert konfluenz.hole_elliott_bericht(opener=kaputter_opener) is None


def test_unlesbare_antwort_ergibt_ebenfalls_none():
    class Antwort:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"das ist kein json"

    def opener(*_args, **_kwargs):
        return Antwort()

    assert konfluenz.hole_elliott_bericht(opener=opener) is None
