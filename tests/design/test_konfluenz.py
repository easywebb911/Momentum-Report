"""Die Konfluenz-Sicht: der Abgleich selbst und beide Zustaende der Seite.

Zwei Ebenen werden geprueft:

  1. Der ABGLEICH als reine Funktion (`MR.konfluenz`, `MR.elliottLong`) mit
     Kunstdaten: Treffer, kein Treffer, Short-Kandidat zaehlt nicht, Elliott
     leer, Elliott kaputt. Dafuer braucht es kein Netz und keine Seite --
     nur den geladenen Code.

  2. Die SEITE in beiden Zustaenden: mit eingespieltem Elliott-Bericht und
     ohne. Der zweite Fall ist der wichtigere -- eine fremde Datei auf einer
     fremden Seite ist regelmaessig nicht da, und dann muss die Seite
     trotzdem vollstaendig und ehrlich aussehen.

KEIN Test geht nach draussen: die Elliott-URL wird im Kontext abgefangen
(conftest.oeffne) und entweder abgebrochen oder aus `ELLIOTT` beantwortet.
Das ist dieselbe Sperre, die beim Kurs-Dienst gelernt wurde.
"""

from __future__ import annotations

import pytest

from .conftest import BREITE, ELLIOTT, TOP5

pytestmark = pytest.mark.browser


def js(page, ausdruck, daten):
    """Einen Ausdruck mit Kunstdaten auswerten -- ohne Netz, ohne Seite."""
    return page.evaluate(ausdruck, daten)


# ------------------------------------------------------- 1. Der Abgleich
#
# Reine Funktion, reine Kunstdaten. Gepruft wird, was die Funktion RECHNET
# -- und vor allem, was sie NICHT rechnet.


@pytest.fixture
def rein(oeffne):
    """Nur der geladene Code, keine Seite, kein Netz."""
    return oeffne("index.html")


def test_ein_titel_in_beiden_listen_ist_ein_treffer(rein):
    treffer = js(
        rein,
        """([top5, kand]) => window.MR.konfluenz(top5, kand)""",
        [
            [{"ticker": "TICK1", "rang": 2, "score": 96.3}],
            [{"ticker": "TICK1", "name": "Gallagher", "score": 7.25}],
        ],
    )
    assert len(treffer) == 1
    t = treffer[0]
    assert t["ticker"] == "TICK1"
    assert t["name"] == "Gallagher"
    # Die beiden Zahlen stehen NEBENEINANDER und bleiben unveraendert.
    assert t["momentum_rang"] == 2
    assert t["momentum_score"] == 96.3
    assert t["elliott_score"] == 7.25
    # Es entsteht KEIN dritter Wert. Waere hier ein weiteres Feld, waere es
    # ein Misch-Wert -- genau das, was diese Seite nie behaupten darf.
    assert set(t) == {"ticker", "name", "momentum_rang", "momentum_score",
                      "elliott_score"}


def test_ohne_gemeinsamen_titel_gibt_es_keinen_treffer(rein):
    treffer = js(
        rein,
        """([top5, kand]) => window.MR.konfluenz(top5, kand)""",
        [
            [{"ticker": "TICK1", "rang": 1, "score": 100.0}],
            [{"ticker": "NVDA", "name": "NVIDIA", "score": 6.1}],
        ],
    )
    assert treffer == []


def test_ein_short_kandidat_zaehlt_nicht(rein):
    """Dieses Werkzeug ist long-only. Ein Short ist das Gegenteil eines
    gemeinsamen Befunds -- er darf nie als Ueberschneidung erscheinen."""
    longs = js(rein, """b => window.MR.elliottLong(b, 'us')""", ELLIOTT)
    tickers = [k["ticker"] for k in longs]
    assert "TICK2" not in tickers, "Short-Kandidat als Long gelesen"
    assert tickers == ["TICK1", "NVDA"]

    # Und ueber den ganzen Weg: TICK2 steht in den Momentum-Top-5 UND im
    # Elliott-Bericht -- trotzdem ist es kein Treffer.
    treffer = js(
        rein,
        """([top5, b]) => window.MR.konfluenz(top5, window.MR.elliottLong(b, 'us'))""",
        [TOP5["maerkte"]["us"]["top5"], ELLIOTT],
    )
    assert [t["ticker"] for t in treffer] == ["TICK1"]


def test_der_elliott_score_kommt_aus_score_heuristic(rein):
    """Im Bericht heisst das Feld `score_heuristic`. `score` bleibt als
    Rueckfallebene stehen; fehlt beides, wird nichts geraten."""
    us = js(rein, """b => window.MR.elliottLong(b, 'us')""", ELLIOTT)
    nach = {k["ticker"]: k["score"] for k in us}
    assert nach["TICK1"] == 76.4, "score_heuristic nicht gelesen"
    assert nach["NVDA"] == 61.2, "Rueckfall auf score greift nicht"

    de = js(rein, """b => window.MR.elliottLong(b, 'de')""", ELLIOTT)
    ohne = {k["ticker"]: k["score"] for k in de}
    assert ohne["DTE.DE"] == 76.95
    assert ohne["BAYN.DE"] is None, "ohne beide Felder darf nichts entstehen"


def test_elliott_leer_ergibt_leere_liste(rein):
    for leer in (
        {"markets": {}},
        {"markets": {"US": {}}},
        {"markets": {"US": {"candidates": []}}},
    ):
        assert js(rein, """b => window.MR.elliottLong(b, 'us')""", leer) == []
    assert js(rein, """([a, b]) => window.MR.konfluenz(a, b)""",
              [TOP5["maerkte"]["us"]["top5"], []]) == []


def test_elliott_kaputt_wirft_nicht_und_liefert_nichts(rein):
    """Fremde Datei, fremdes Schema: was nicht passt, wird ignoriert --
    nicht geraten und nicht mit einer Ausnahme quittiert."""
    kaputt = [
        None,
        "kein objekt",
        42,
        {},
        {"markets": "kein objekt"},
        {"markets": {"US": {"candidates": "keine liste"}}},
        {"markets": {"US": {"candidates": [None, 7, {}, {"direction": "long"}]}}},
    ]
    for fall in kaputt:
        ergebnis = js(rein, """b => window.MR.elliottLong(b, 'us')""", fall)
        assert ergebnis == [], f"{fall!r} ergab {ergebnis!r}"


def test_der_abgleich_ordnet_alphabetisch_und_nicht_nach_guete(rein):
    """Jede andere Reihenfolge waere eine Aussage darueber, welcher Treffer
    der bessere ist. Die gibt es hier nicht."""
    treffer = js(
        rein,
        """([top5, kand]) => window.MR.konfluenz(top5, kand)""",
        [
            [
                {"ticker": "ZZZ", "rang": 1, "score": 100.0},
                {"ticker": "AAA", "rang": 5, "score": 12.0},
                {"ticker": "MMM", "rang": 3, "score": 55.0},
            ],
            [
                {"ticker": "ZZZ", "name": "Z", "score": 1.0},
                {"ticker": "AAA", "name": "A", "score": 9.9},
                {"ticker": "MMM", "name": "M", "score": 5.0},
            ],
        ],
    )
    assert [t["ticker"] for t in treffer] == ["AAA", "MMM", "ZZZ"]


def test_der_abgleich_veraendert_seine_eingaben_nicht(rein):
    """Rein heisst rein: keine Seiteneffekte auf den uebergebenen Listen."""
    unveraendert = js(
        rein,
        """([top5, kand]) => {
             const vorher = JSON.stringify([top5, kand]);
             window.MR.konfluenz(top5, kand);
             return JSON.stringify([top5, kand]) === vorher;
           }""",
        [
            [{"ticker": "TICK1", "rang": 1, "score": 100.0}],
            [{"ticker": "TICK1", "name": "G", "score": 7.0}],
        ],
    )
    assert unveraendert is True


# ------------------------------------------- 2. Die Seite, beide Zustaende


def aufbauen(page):
    """Den Aufbau abwarten. Die Seite startet ihn selbst; hier wird er
    erneut angestossen, damit der Test nicht auf ein Rennen hofft."""
    return page.evaluate("() => window.MR.konfluenzAufbauen()")


@pytest.fixture
def mit_elliott(oeffne, server):
    page = oeffne("konfluenz.html", basis=server, elliott=ELLIOTT)
    assert aufbauen(page) == "fertig"
    return page


@pytest.fixture
def ohne_elliott(oeffne, server):
    page = oeffne("konfluenz.html", basis=server)
    assert aufbauen(page) == "ohne elliott"
    return page


def test_der_treffer_steht_als_karte_mit_beiden_zahlen(mit_elliott):
    karten = mit_elliott.locator(".konf-treffer")
    assert karten.count() == 1, "genau ein Treffer erwartet (US: TICK1)"
    text = karten.first.inner_text()
    assert "TICK1" in text
    assert "Arthur J. Gallagher" in text
    # Beide Zahlen sind getrennt beschriftet — man sieht, welche woher kommt.
    # (Die Kachel-Labels stehen per CSS in Grossbuchstaben.)
    assert "MOMENTUM: RANG · SCORE" in text.upper()
    assert "ELLIOTT: SCORE" in text.upper()
    assert "2." in text and "96,3" in text  # Momentum-Rang und -Score
    assert "76,4" in text                   # Elliott-Score, unverrechnet


def test_der_treffer_verlinkt_beide_werkzeuge(mit_elliott):
    karte = mit_elliott.locator(".konf-treffer").first
    ziele = karte.locator("a").evaluate_all("a => a.map(x => x.getAttribute('href'))")
    assert "./index.html" in ziele
    assert any("Elliott-Report" in z for z in ziele), ziele
    # Fremdes Ziel oeffnet in neuem Tab und ohne Rueckkanal.
    fremd = karte.locator('a[target="_blank"]')
    assert fremd.count() == 1
    assert "noopener" in (fremd.get_attribute("rel") or "")


def test_der_leere_zustand_ist_der_regelfall_und_steht_wortgleich_da(mit_elliott):
    """DE hat keine Ueberschneidung. Der Satz dazu ist festgelegt und darf
    nicht im Laufe der Zeit in einen Alarmton kippen."""
    leer = mit_elliott.locator(".konf-leer")
    assert leer.count() == 1, "genau ein leerer Markt erwartet (DE)"
    text = leer.first.inner_text()
    erwartet = (
        "Keine Überschneidung — das ist der Regelfall. Beide Werkzeuge messen "
        "Verschiedenes; ein gemeinsamer Treffer ist selten."
    )
    assert text.strip() == erwartet
    # Kein Alarmton: weder Warn- noch Negativfarbe, kein Ausrufezeichen.
    farbe = leer.first.evaluate("el => getComputedStyle(el).color")
    assert farbe == "rgb(148, 163, 184)", farbe  # --txt-sub, die ruhige Farbe
    assert "!" not in text


def test_beide_top_listen_stehen_nebeneinander_und_treffer_sind_markiert(mit_elliott):
    us = mit_elliott.locator("section.market").first
    spalten = us.locator(".konf-spalte")
    assert spalten.count() == 2
    assert "MOMENTUM-TOP-5" in spalten.nth(0).inner_text().upper()
    assert "ELLIOTT" in spalten.nth(1).inner_text().upper()
    # Fuenf Momentum-Zeilen, zwei Elliott-Long-Zeilen (der Short fehlt).
    assert spalten.nth(0).locator(".konf-zeile").count() == 5
    assert spalten.nth(1).locator(".konf-zeile").count() == 2
    # Markiert ist genau der gemeinsame Titel -- auf beiden Seiten.
    markiert = us.locator(".konf-zeile--treffer")
    assert markiert.count() == 2
    assert all("TICK1" in markiert.nth(i).inner_text() for i in range(2))


def test_der_elliott_score_steht_deutsch_und_einstellig_da(mit_elliott):
    """Eine Nachkommastelle, Komma statt Punkt -- und ein Gedankenstrich,
    wo der Bericht keinen Score liefert."""
    us = mit_elliott.locator("section.market").first
    elliott_spalte = us.locator(".konf-spalte").nth(1)
    zeilen = elliott_spalte.inner_text()
    assert "76,4" in zeilen and "61,2" in zeilen
    assert "76.4" not in zeilen, "englisches Format"

    de = mit_elliott.locator("section.market").nth(1)
    de_spalte = de.locator(".konf-spalte").nth(1)
    werte = de_spalte.locator(".konf-wert").evaluate_all(
        "n => n.map(x => x.textContent)"
    )
    assert "77,0" in werte or "76,9" in werte, werte  # DTE.DE, eine Stelle
    assert "—" in werte, f"fehlender Score muss ein Gedankenstrich sein: {werte}"


def test_der_stand_beider_quellen_ist_sichtbar(mit_elliott):
    """Die Werkzeuge laufen zu verschiedenen Zeiten. Wer das nicht sieht,
    vergleicht womoeglich Aepfel mit Birnen von gestern."""
    assert "2026-07-31" in mit_elliott.inner_text("#stand-momentum")
    assert "2026-08-02" in mit_elliott.inner_text("#stand-elliott")


def test_ohne_elliott_bleibt_die_momentum_haelfte_vollstaendig(ohne_elliott):
    """FAIL-SOFT: die fremde Quelle fehlt -- kein Fehlerbild, keine leere
    Seite, sondern die eigene Haelfte in voller Laenge plus ein Hinweis."""
    hinweis = ohne_elliott.locator("#konf-hinweis")
    assert hinweis.is_visible()
    assert "nicht erreichbar" in hinweis.inner_text()

    # Beide Maerkte stehen da, jeder mit seinen fuenf Momentum-Zeilen.
    maerkte = ohne_elliott.locator("section.market")
    assert maerkte.count() == 2
    for i in range(2):
        spalten = maerkte.nth(i).locator(".konf-spalte")
        assert spalten.nth(0).locator(".konf-zeile").count() == 5
        # Die Elliott-Spalte steht leer da -- als Gedankenstrich, nicht als
        # Fehlermeldung und nicht als stiller Ersatzwert.
        assert spalten.nth(1).locator(".konf-zeile--leer").count() == 1

    assert ohne_elliott.locator(".konf-treffer").count() == 0
    assert "nicht erreichbar" in ohne_elliott.inner_text("#stand-elliott")
    assert "2026-07-31" in ohne_elliott.inner_text("#stand-momentum")


def test_mit_elliott_steht_kein_hinweis_da(mit_elliott):
    assert mit_elliott.locator("#konf-hinweis").is_visible() is False


def test_die_seite_verrechnet_nirgends_etwas(mit_elliott):
    """Selbstkontrolle im Browser: kein gemeinsamer Score, keine
    Wahrscheinlichkeit, keine Rangfolge der Treffer -- auch nicht in Worten."""
    # Der feste Satz bleibt aussen vor: er ist die EINE Stelle, die die
    # Misch-Begriffe nennen darf -- weil er sie verneint.
    text = mit_elliott.evaluate(
        """() => {
             const regel = document.querySelector('.konf-regel');
             const ganz = document.body.innerText;
             return regel ? ganz.replace(regel.innerText, '') : ganz;
           }"""
    ).lower()
    for wort in ("kombiniert", "gewichtet", "gesamtscore", "gesamt-score",
                 "wahrscheinlichkeit", "signalstärke", "bestätigt"):
        assert wort not in text, f"Misch-Vokabel auf der Seite: {wort}"
    # Und der feste Satz, der genau das erklaert, steht da.
    regel = mit_elliott.inner_text(".konf-regel")
    assert "Hier wird nichts verrechnet" in regel
    assert "kein doppelter Beleg" in regel


@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_die_konfluenz_seite_passt_auf_390_px(oeffne, server, schriftgroesse):
    for daten in (ELLIOTT, None):
        page = oeffne("konfluenz.html", schriftgroesse, basis=server, elliott=daten)
        aufbauen(page)
        breite = page.evaluate("document.documentElement.scrollWidth")
        assert breite <= BREITE, f"scrollt seitwaerts: {breite}px"
        ueberstand = page.evaluate(
            """() => {
              const raus = [];
              document.querySelectorAll('body *').forEach(el => {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && (r.right > window.innerWidth + 0.5 || r.left < -0.5)) {
                  raus.push((el.className.baseVal ?? el.className) + '|'
                            + Math.round(r.left) + '..' + Math.round(r.right));
                }
              });
              return raus;
            }"""
        )
        assert ueberstand == [], f"ausserhalb des Bildschirms: {ueberstand}"
