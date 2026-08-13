"""Die Bedienung im echten Browser: Neu laden, Lauf anstossen, Token.

Diese Tests laufen ueber HTTP (siehe conftest.server), weil fetch und
IndexedDB unter file:// gesperrt sind. Es geht KEIN einziger echter
Netzzugriff hinaus: `MR.deps.netz` wird durch einen Aufzeichner ersetzt,
der vorbereitete Antworten zurueckgibt und jede Anfrage mitschreibt.

Der wichtigste Test in dieser Datei ist der FEHLSCHLAG-Pfad. Der Lauf
verweigert derzeit zu Recht (das DE-Universum ist ein Platzhalter) — ein
Banner, das dann ewig weiterzaehlt, waere genau die Art stiller
Beschoenigung, die dieses Projekt nirgends duldet.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.browser

TOKEN = "github_pat_ZZZ_nur_fuer_den_test_0123456789"

# Der Aufzeichner. `__antworten` ist eine Warteschlange; das letzte Element
# bleibt liegen und wird wiederholt -- so laesst sich ein Dauerzustand
# ("laeuft immer noch") ohne endlose Listen abbilden.
STUB = """
window.__aufrufe = [];
window.__antworten = ANTWORTEN;
window.__zeit = ZEIT;
window.MR.deps.jetzt = function () { return window.__zeit; };
window.MR.deps.pollAbstandMs = 5;
window.MR.deps.netz = function (url, opt) {
  window.__aufrufe.push({ url: String(url), opt: opt || {} });
  var a = window.__antworten.length > 1
    ? window.__antworten.shift()
    : window.__antworten[0];
  if (!a) { a = { status: 500 }; }
  if (a.zeitsprung) { window.__zeit += a.zeitsprung; }
  return Promise.resolve({
    ok: a.status >= 200 && a.status < 300,
    status: a.status,
    headers: { get: function (n) {
      return (a.headers || {})[String(n).toLowerCase()] || null;
    } },
    json: function () { return Promise.resolve(a.json || {}); },
    text: function () { return Promise.resolve(a.text || ""); }
  });
};
// Der Rueckgabewert des Skripts darf KEINE Funktion sein: Playwright ruft
// eine solche sonst gleich auf -- und dann steht ein Phantom-Aufruf mit
// url=null in der Aufzeichnung, der alle Antworten um eins verschiebt.
window.__geruestet = true;
"""


def ruesten(page, antworten, zeit=1_000_000_000_000):
    page.evaluate(
        STUB.replace("ANTWORTEN", json.dumps(antworten)).replace("ZEIT", str(zeit))
    )


def lauf(status, conclusion, erstellt="2001-09-09T01:46:40Z", nummer=7):
    return {
        "status": status,
        "conclusion": conclusion,
        "created_at": erstellt,
        "html_url": f"https://github.com/easywebb911/Momentum-Report/actions/runs/{nummer}",
    }


def banner(page):
    return page.evaluate(
        """() => {
          const b = document.querySelector('#runbar');
          const l = document.querySelector('#runbar-link');
          return {versteckt: b.hidden, klasse: b.className,
                  text: document.querySelector('#runbar-text').textContent,
                  link: l.hidden ? null : l.getAttribute('href')};
        }"""
    )


@pytest.fixture
def app(oeffne, server):
    return oeffne("index.html", basis=server)


# ------------------------------------------------------------- Neu laden


def test_neu_laden_tauscht_den_inhalt_ohne_die_seite_zu_verlassen(app):
    """Kein Seitenwechsel: das Kennzeichen am window muss ueberleben."""
    app.evaluate("window.__ueberlebt = 'ja'; document.querySelector('main').id = 'alt'")
    app.evaluate("() => window.MR.neuLaden()")
    assert app.evaluate("window.__ueberlebt") == "ja", "die Seite wurde neu geladen"
    assert app.evaluate("document.querySelector('main').id") == "", "Inhalt nicht getauscht"
    assert app.locator(".card").count() == 10


def test_neu_laden_haengt_einen_cache_brecher_an(app):
    ruesten(app, [{"status": 200, "text": "<html><body><main>x</main></body></html>"}])
    app.evaluate("() => window.MR.neuLaden()")
    aufrufe = app.evaluate("window.__aufrufe")
    assert len(aufrufe) == 1
    assert "?t=1000000000000" in aufrufe[0]["url"], aufrufe
    assert aufrufe[0]["opt"]["cache"] == "no-store"


def test_neu_laden_meldet_einen_fehler_statt_ihn_zu_schlucken(app):
    ruesten(app, [{"status": 503}])
    app.evaluate("() => window.MR.neuLaden().catch(e => e.message)")
    app.click("#menu-btn")
    app.click("#reload-btn")
    app.wait_for_function("document.querySelector('#runbar-text').textContent.includes('503')")
    assert "runbar--fehler" in banner(app)["klasse"]


# ------------------------------------------------------------- Ohne Token


def test_ohne_token_oeffnet_der_knopf_nur_den_dialog(app):
    """Kein Token, kein Dispatch — und nichts Stilles."""
    ruesten(app, [{"status": 204}])
    app.click("#menu-btn")
    app.click("#recalc-btn")
    app.wait_for_selector("#tok-overlay:not([hidden])")
    assert app.evaluate("window.__aufrufe") == [], "es wurde trotzdem etwas geschickt"
    assert app.is_hidden("#overlay"), "das Menue haette zugehen muessen"


def test_der_dialog_nennt_die_noetigen_rechte(app):
    app.evaluate("window.MR.dialogOeffnen(null)")
    text = app.inner_text(".tok-dlg")
    assert "Fine-grained" in text
    assert "Only select repositories" in text
    assert "Actions" in text and "Contents" in text
    assert "Read and write" in text
    assert app.get_attribute("#tok-input", "type") == "password"


# ----------------------------------------------------------- Mit Token


def test_token_wird_abgelegt_und_der_lauf_angestossen(app):
    ruesten(app, [{"status": 204}, {"status": 200, "json": {"workflow_runs": []}}])
    app.evaluate("window.MR.dialogOeffnen(null)")
    app.fill("#tok-input", TOKEN)
    app.click("#tok-save")
    app.wait_for_function("window.__aufrufe.length >= 1")

    erster = app.evaluate("window.__aufrufe[0]")
    assert erster["url"] == (
        "https://api.github.com/repos/easywebb911/Momentum-Report"
        "/actions/workflows/lauf.yml/dispatches"
    )
    assert erster["opt"]["method"] == "POST"
    assert erster["opt"]["headers"]["Authorization"] == "Bearer " + TOKEN
    assert json.loads(erster["opt"]["body"]) == {"ref": "main"}

    gespeichert = app.evaluate("() => window.MR.sitzungLesen()")
    assert gespeichert["token"] == TOKEN
    # 28 Tage, gerechnet ab der gestellten Uhr.
    assert gespeichert["gueltig_bis"] == 1_000_000_000_000 + 28 * 24 * 3600 * 1000


def test_der_token_steht_in_keiner_adresszeile(app):
    """Er gehoert in die Authorization-Kopfzeile — sonst nirgendwohin."""
    ruesten(app, [
        {"status": 204},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "success")]}},
        {"status": 200, "text": "<html><body><main>neu</main></body></html>"},
    ])
    app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    aufrufe = app.evaluate("window.__aufrufe")
    assert aufrufe, "es wurde gar nichts geschickt"
    for aufruf in aufrufe:
        assert TOKEN not in aufruf["url"], aufruf["url"]
        assert TOKEN not in json.dumps(aufruf["opt"].get("body") or ""), aufruf
    # ... und in der Adresszeile des Browsers erst recht nicht.
    assert TOKEN not in app.url
    assert TOKEN not in app.content()


def test_alle_aufrufe_gehen_an_api_github_com_ueber_https(app):
    ruesten(app, [
        {"status": 204},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "failure")]}},
    ])
    app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    for aufruf in app.evaluate("window.__aufrufe"):
        assert aufruf["url"].startswith("https://api.github.com/"), aufruf["url"]


# ------------------------------------------------------- Die drei Ausgaenge


def test_erfolgreicher_lauf_holt_die_daten_neu(app):
    ruesten(app, [
        {"status": 204},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "success")]}},
        {"status": 200, "text": "<html><body><main id='frisch'>neu</main>"
                                "<p class='stand'>Stand neu</p></body></html>"},
    ])
    ergebnis = app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    assert ergebnis == "fertig"
    assert app.evaluate("document.querySelector('main').id") == "frisch"
    assert app.inner_text(".stand") == "Stand neu"
    zustand = banner(app)
    assert "runbar--fertig" in zustand["klasse"]
    assert "fertig" in zustand["text"]


def test_fehlgeschlagener_lauf_zeigt_die_wahrheit_statt_weiterzuzaehlen(app):
    """DER Test dieser Datei.

    Der Lauf verweigert heute zu Recht, solange das DE-Universum ein
    Platzhalter ist. Dann muss das Banner rot werden und aufs Protokoll
    verweisen — nicht bis zum Zeitlimit weiterzaehlen.
    """
    ruesten(app, [
        {"status": 204},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "failure", nummer=42)]}},
    ])
    ergebnis = app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    assert ergebnis == "fehlgeschlagen"

    zustand = banner(app)
    assert "runbar--fehler" in zustand["klasse"], zustand
    assert "fehlgeschlagen" in zustand["text"], zustand
    assert "Actions-Protokoll" in zustand["text"], zustand
    assert zustand["link"].endswith("/runs/42"), zustand
    assert "laeuft" not in zustand["text"], "es zaehlt weiter, obwohl der Lauf rot ist"

    # Und es wird nicht weitergefragt: genau Dispatch + eine Abfrage.
    assert app.evaluate("window.__aufrufe.length") == 2


def test_abgebrochener_lauf_zaehlt_ebenfalls_als_fehlschlag(app):
    ruesten(app, [
        {"status": 204},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "cancelled")]}},
    ])
    assert app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})") == "fehlgeschlagen"
    assert "cancelled" in banner(app)["text"]


def test_der_zaehler_laeuft_waehrend_der_lauf_laeuft(app):
    ruesten(app, [
        {"status": 204},
        {"status": 200, "zeitsprung": 12_000,
         "json": {"workflow_runs": [lauf("in_progress", None)]}},
        {"status": 200, "json": {"workflow_runs": [lauf("completed", "failure")]}},
    ])
    app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    # Der Zwischenstand mit Sekunden muss dagewesen sein; am Ende steht der
    # Fehlschlag. Geprueft wird deshalb der Endzustand plus die Zahl der Runden.
    assert app.evaluate("window.__aufrufe.length") == 3
    assert "runbar--fehler" in banner(app)["klasse"]


def test_zeitlimit_beendet_das_zaehlen_ehrlich(app):
    """Nach 10 Minuten ist Schluss — mit klarer Ansage, nicht mit Schweigen."""
    ruesten(app, [
        {"status": 204},
        {"status": 200, "zeitsprung": 11 * 60 * 1000,
         "json": {"workflow_runs": [lauf("in_progress", None)]}},
    ])
    ergebnis = app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    assert ergebnis == "zeitlimit"
    zustand = banner(app)
    assert "runbar--fehler" in zustand["klasse"]
    assert "ungewoehnlich lange" in zustand["text"], zustand
    assert "Actions-Protokoll" in zustand["text"], zustand
    assert zustand["link"], "ohne Verweis aufs Protokoll nuetzt die Meldung nichts"


# --------------------------------------------------------- Abgelehnt


def test_am_rate_limit_wird_nicht_wiederholt(app):
    """Stehende Regel: am Limit kein zweiter Versuch, sofort melden."""
    ruesten(app, [{"status": 403, "headers": {"x-ratelimit-remaining": "0"}}])
    ergebnis = app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    assert ergebnis == "abgelehnt"
    assert app.evaluate("window.__aufrufe.length") == 1, "es wurde wiederholt"
    zustand = banner(app)
    assert "Limit" in zustand["text"]
    assert "Kein zweiter Versuch" in zustand["text"]


def test_abgelehnter_token_wird_verworfen_und_neu_erfragt(app):
    app.evaluate(f"() => window.MR.sitzungSchreiben({TOKEN!r})")
    ruesten(app, [{"status": 401}])
    ergebnis = app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})")
    assert ergebnis == "token-abgelehnt"
    assert app.evaluate("() => window.MR.sitzungLesen()") is None, "Token blieb liegen"
    assert app.is_visible("#tok-overlay")
    assert "401" in app.inner_text("#tok-error")


def test_fehlende_rechte_lassen_den_token_liegen(app):
    """403 ohne Limit ist ein Rechte-Problem — der Token bleibt gueltig."""
    app.evaluate(f"() => window.MR.sitzungSchreiben({TOKEN!r})")
    ruesten(app, [{"status": 403, "headers": {"x-ratelimit-remaining": "58"}}])
    assert app.evaluate(f"() => window.MR.laufStarten({TOKEN!r})") == "abgelehnt"
    assert app.evaluate("() => window.MR.sitzungLesen()") is not None
    assert "Read and write" in banner(app)["text"]


# ------------------------------------------------------------- Sitzung


def test_sperren_verwirft_die_sitzung_sofort(app):
    app.evaluate(f"() => window.MR.sitzungSchreiben({TOKEN!r})")
    app.evaluate("() => window.MR.sitzungAnzeigen()")
    app.click("#menu-btn")
    assert app.evaluate("document.querySelector('#lock-btn').disabled") is False
    app.click("#lock-btn")
    app.wait_for_function("document.querySelector('#lock-btn').disabled === true")
    assert app.evaluate("() => window.MR.sitzungLesen()") is None
    assert "Kein Token gespeichert" in app.inner_text("#lock-sub")


def test_die_sitzung_laeuft_nach_28_tagen_ab(app):
    ruesten(app, [{"status": 204}])
    app.evaluate(f"() => window.MR.sitzungSchreiben({TOKEN!r})")
    assert app.evaluate("() => window.MR.sitzungLesen()") is not None

    # Uhr um 28 Tage und eine Sekunde vorstellen.
    app.evaluate("window.__zeit += 28 * 24 * 3600 * 1000 + 1000")
    assert app.evaluate("() => window.MR.sitzungLesen()") is None

    # ... und der Eintrag ist wirklich weg, nicht bloss ignoriert.
    app.evaluate("window.__zeit -= 28 * 24 * 3600 * 1000 + 1000")
    assert app.evaluate("() => window.MR.sitzungLesen()") is None


def test_das_menue_zeigt_die_restlaufzeit(app):
    ruesten(app, [{"status": 204}])
    app.evaluate(f"() => window.MR.sitzungSchreiben({TOKEN!r})")
    app.evaluate("() => window.MR.sitzungAnzeigen()")
    assert "28 Tage" in app.inner_text("#lock-sub")
    app.evaluate("window.__zeit += 27 * 24 * 3600 * 1000")
    app.evaluate("() => window.MR.sitzungAnzeigen()")
    assert "1 Tag" in app.inner_text("#lock-sub")


def test_ohne_token_ist_sperren_gesperrt(app):
    app.evaluate("() => window.MR.sitzungAnzeigen()")
    app.click("#menu-btn")
    assert app.evaluate("document.querySelector('#lock-btn').disabled") is True
    assert "Kein Token gespeichert" in app.inner_text("#lock-sub")


# ==========================================================================
# LIVE-KURSE
#
# Der Kurs-Dienst wird gemockt — es geht kein einziger echter Abruf hinaus.
# Geprueft wird das, worauf es ankommt: aktualisiert er die Kurszeile,
# faellt er bei Stoerung sauber auf grau zurueck, und ruht er, wenn der
# Tab nicht sichtbar ist.
# ==========================================================================


def live_zustand(page):
    """Die Live-Anzeige JE KARTE — seit dem Umbau gibt es sie nicht mehr
    je Markt-Block, sondern einmal pro Titel, direkt beim Kurs."""
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-live-ticker]')].map(el => ({
             markt: el.getAttribute('data-live-markt'),
             ticker: el.getAttribute('data-live-ticker'),
             versteckt: el.hidden,
             aus: el.classList.contains('live--aus'),
             text: el.querySelector('.live-txt').textContent,
           }))"""
    )


def kurse(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('[data-quote]')].map(el => ({
             ticker: el.getAttribute('data-quote'),
             wert: el.textContent,
             aenderung: (document.querySelector(
               '[data-quote-change="' + el.getAttribute('data-quote') + '"]') || {}).textContent,
           }))"""
    )


def test_der_live_kurs_ersetzt_die_kurszeile(app):
    vorher = kurse(app)
    ruesten(app, [{"status": 200, "json": {"price": 42.5, "changePercent": -1.25}}])
    app.evaluate("() => window.MR.liveRunde()")

    nachher = kurse(app)
    assert vorher != nachher
    for eintrag in nachher:
        assert "42,50" in eintrag["wert"], eintrag
        assert "-1,3" in eintrag["aenderung"], eintrag
    # Das Waehrungszeichen der Karte bleibt erhalten.
    assert nachher[0]["wert"].strip()[0] in "$€", nachher[0]


def test_live_ruehrt_score_und_rang_nicht_an(app):
    """Die Trennung, auf die es ankommt — belegt am laufenden Objekt."""
    vorher = app.evaluate(
        """() => ({
             score: [...document.querySelectorAll('.score-val')].map(e => e.textContent),
             raenge: [...document.querySelectorAll('.metrics--rang .m-val')]
               .map(e => e.textContent),
             momentum: [...document.querySelectorAll('.metrics .metric-box:first-child .m-val')]
               .map(e => e.textContent),
           })"""
    )
    ruesten(app, [{"status": 200, "json": {"price": 999.99, "changePercent": 50}}])
    app.evaluate("() => window.MR.liveRunde()")
    nachher = app.evaluate(
        """() => ({
             score: [...document.querySelectorAll('.score-val')].map(e => e.textContent),
             raenge: [...document.querySelectorAll('.metrics--rang .m-val')]
               .map(e => e.textContent),
             momentum: [...document.querySelectorAll('.metrics .metric-box:first-child .m-val')]
               .map(e => e.textContent),
           })"""
    )
    assert nachher == vorher, "die Live-Schicht hat Rechenwerte veraendert"


def test_der_punkt_wird_gruen_und_nennt_die_uhrzeit(app):
    ruesten(app, [{"status": 200, "json": {"price": 42.5, "changePercent": 1.0}}])
    app.evaluate("() => window.MR.liveRunde()")
    for eintrag in live_zustand(app):
        assert eintrag["versteckt"] is False
        assert eintrag["aus"] is False, eintrag
        assert eintrag["text"].startswith("Live · "), eintrag
        assert ":" in eintrag["text"], "die Uhrzeit fehlt"


@pytest.mark.parametrize(
    "antwort,warum",
    [
        ({"status": 503}, "Dienst nicht erreichbar"),
        ({"status": 200, "json": {"unbekannt": True}}, "Format passt nicht"),
        ({"status": 200, "json": {"price": "keine Zahl"}}, "Kurs unbrauchbar"),
        ({"status": 200, "json": []}, "gar kein Objekt"),
    ],
)
def test_bei_stoerung_wird_der_punkt_grau_und_die_karte_bleibt(app, antwort, warum):
    """FAIL-SOFT: nie eine kaputte Karte, immer nur eine ehrliche Auskunft."""
    vorher = kurse(app)
    stand_vorher = {(e["markt"], e["ticker"]): e["text"] for e in live_zustand(app)}
    ruesten(app, [antwort])
    app.evaluate("() => window.MR.liveRunde()")

    for eintrag in live_zustand(app):
        assert eintrag["aus"] is True, (warum, eintrag)
        # Der Zeitstempel bleibt stehen — er sagt, wann zuletzt etwas
        # Gutes kam, nicht wann zuletzt gefragt wurde.
        assert eintrag["text"] == stand_vorher[(eintrag["markt"], eintrag["ticker"])], \
            (warum, eintrag)
    assert kurse(app) == vorher, f"{warum}: die Kurse wurden angetastet"


def test_der_zeitstempel_bleibt_nach_einer_stoerung_stehen(app):
    ruesten(app, [{"status": 200, "json": {"price": 42.5}}])
    app.evaluate("() => window.MR.liveRunde()")
    gut = live_zustand(app)[0]["text"]
    assert gut != "Live · —"

    ruesten(app, [{"status": 500}])
    app.evaluate("() => window.MR.liveRunde()")
    nach_stoerung = live_zustand(app)[0]
    assert nach_stoerung["aus"] is True
    assert nach_stoerung["text"] == gut, "der Zeitstempel muss stehen bleiben"


def test_eine_stoerung_loest_keinen_anfragensturm_aus(app):
    """Kein Nachfassen ausser der Reihe — der naechste Versuch kommt im Takt."""
    ruesten(app, [{"status": 500}])
    app.evaluate("() => window.MR.liveRunde()")
    erste_runde = app.evaluate("window.__aufrufe.length")
    # genau ein Abruf je sichtbarem Titel, kein zweiter Anlauf
    sichtbare = app.evaluate("document.querySelectorAll('[data-quote]').length")
    assert erste_runde == sichtbare, (erste_runde, sichtbare)


def test_bei_verstecktem_tab_wird_nichts_abgefragt(app):
    ruesten(app, [{"status": 200, "json": {"price": 42.5}}])
    app.evaluate("Object.defineProperty(document, 'hidden', {value: true, configurable: true})")
    ergebnis = app.evaluate("() => window.MR.liveRunde()")
    assert ergebnis == "pausiert"
    assert app.evaluate("window.__aufrufe") == [], "im Hintergrund wurde abgefragt"

    # Sichtbar wieder da: es geht sofort weiter.
    app.evaluate("Object.defineProperty(document, 'hidden', {value: false, configurable: true})")
    app.evaluate("() => window.MR.liveRunde()")
    assert app.evaluate("window.__aufrufe.length") > 0


def test_der_abruf_geht_an_den_kurs_dienst(app):
    ruesten(app, [{"status": 200, "json": {"price": 1.0}}])
    app.evaluate("() => window.MR.liveRunde()")
    aufrufe = app.evaluate("window.__aufrufe")
    assert aufrufe, "es wurde gar nichts abgefragt"
    for aufruf in aufrufe:
        assert aufruf["url"].startswith("https://quote-proxy.easywebb.workers.dev?ticker="), aufruf
    gefragt = {a["url"].split("ticker=")[1] for a in aufrufe}
    assert "BRK-B" in gefragt


def test_de_ticker_werden_mit_endung_abgefragt(app):
    """Der Dienst kann .DE-Symbole — sie werden unveraendert weitergereicht."""
    app.evaluate(
        """() => {
             const el = document.querySelector('[data-quote]');
             el.setAttribute('data-quote', 'SAP.DE');
           }"""
    )
    ruesten(app, [{"status": 200, "json": {"price": 1.0}}])
    app.evaluate("() => window.MR.liveRunde()")
    assert any("ticker=SAP.DE" in a["url"] for a in app.evaluate("window.__aufrufe"))


@pytest.mark.parametrize(
    "daten,preis,prozent",
    [
        ({"price": 42.5, "changePercent": -1.25}, 42.5, -1.25),
        ({"regularMarketPrice": 7, "regularMarketChangePercent": 2}, 7, 2),
        ({"c": 10, "dp": 0.5}, 10, 0.5),
        ({"quote": {"price": 3.5, "changePercent": 1}}, 3.5, 1),
        ({"data": {"last": 8, "previousClose": 4}}, 8, 100),
        ({"price": "42,50", "changePercent": "-1,25 %"}, 42.5, -1.25),
        ({"price": 5}, 5, None),
    ],
)
def test_das_antwortformat_wird_tolerant_gelesen(app, daten, preis, prozent):
    """Das Format ist nicht zugesichert — es wird aus der Antwort abgelesen."""
    gelesen = app.evaluate("d => window.MR.leseKurs(d)", daten)
    assert gelesen is not None, daten
    assert gelesen["preis"] == pytest.approx(preis), daten
    if prozent is None:
        assert gelesen["prozent"] is None, daten
    else:
        assert gelesen["prozent"] == pytest.approx(prozent, abs=0.01), daten


@pytest.mark.parametrize(
    "daten", [None, [], "text", 5, {}, {"foo": "bar"}, {"price": None}, {"price": "abc"}]
)
def test_unverstaendliche_antworten_ergeben_null(app, daten):
    assert app.evaluate("d => window.MR.leseKurs(d)", daten) is None, daten


# ==========================================================================
# DIE LIVE-ANZEIGE JE KARTE
#
# Bis zum 13.08.2026 gab es Punkt und Uhrzeit genau zweimal — einmal je
# Markt-Block. Damit sagte eine graue Anzeige nur "irgendeiner der fuenf
# Titel klemmt", und ein gruener Punkt stand auch ueber vier stehenden
# Kursen, solange einer frisch war. Jetzt haengt jede Anzeige an genau
# dem Kurs, neben dem sie steht.
# ==========================================================================


def netz_je_ticker(page, fehlschlag):
    """Die Kursquelle antwortet je nach TICKER — genau ein Titel klemmt.

    Der Reihen-Stub oben taugt dafuer nicht: er gibt die Antworten in der
    Aufrufreihenfolge aus, und die ist bei parallelen Abrufen kein
    verlaesslicher Zeiger auf einen bestimmten Titel.
    """
    page.evaluate(
        """(kaputt) => {
          window.MR.deps.netz = function (url) {
            var treffer = /ticker=([^&]+)/.exec(String(url));
            var ticker = treffer ? decodeURIComponent(treffer[1]) : "";
            if (ticker === kaputt) {
              return Promise.resolve({ ok: false, status: 503,
                json: function () { return Promise.resolve({}); } });
            }
            return Promise.resolve({ ok: true, status: 200,
              json: function () {
                return Promise.resolve({ price: 42.5, changePercent: 1.0 });
              } });
          };
        }""",
        fehlschlag,
    )


def test_jede_karte_hat_ihre_eigene_live_anzeige(app):
    """So viele Anzeigen wie Kurse — nicht zwei fuer zehn Karten."""
    zustand = live_zustand(app)
    kurs_felder = app.evaluate("document.querySelectorAll('[data-quote]').length")
    assert len(zustand) == kurs_felder > 2, zustand
    # Und jede ist eindeutig: Markt plus Ticker, keine Kollision.
    schluessel = [(e["markt"], e["ticker"]) for e in zustand]
    assert len(set(schluessel)) == len(schluessel), schluessel
    assert all(e["markt"] for e in zustand), "eine Karte ohne Markt-Zuordnung"


def test_im_startzustand_steht_ueberall_der_gedankenstrich(app):
    for eintrag in live_zustand(app):
        assert eintrag["text"] == "Live · —", eintrag


def test_ein_klemmender_titel_faerbt_NUR_seine_eigene_karte_grau(app):
    """DIE Zusage dieses Umbaus: die Karten haengen nicht mehr aneinander."""
    ruesten(app, [{"status": 200, "json": {"price": 42.5, "changePercent": 1.0}}])
    app.evaluate("() => window.MR.liveRunde()")
    for eintrag in live_zustand(app):
        assert eintrag["aus"] is False, ("Vorlauf misslungen", eintrag)
    vorher = {(e["markt"], e["ticker"]): e["text"] for e in live_zustand(app)}

    kaputt = live_zustand(app)[0]["ticker"]
    netz_je_ticker(app, kaputt)
    app.evaluate("() => window.MR.liveRunde()")

    grau = [e for e in live_zustand(app) if e["aus"]]
    assert [e["ticker"] for e in grau] == [kaputt] or all(
        e["ticker"] == kaputt for e in grau
    ), f"nicht nur {kaputt} wurde grau: {grau}"
    for eintrag in live_zustand(app):
        if eintrag["ticker"] == kaputt:
            # Stehengeblieben, nicht zurueckgesetzt: der Zeitstempel sagt,
            # wann zuletzt etwas Gutes kam.
            assert eintrag["text"] == vorher[(eintrag["markt"], eintrag["ticker"])]
        else:
            assert eintrag["aus"] is False, eintrag
            assert ":" in eintrag["text"], eintrag


def test_die_alte_anzeige_je_markt_block_ist_weg(app):
    """Dieselbe Aussage zweimal waere eine zu viel."""
    assert app.evaluate("document.querySelectorAll('[data-live]').length") == 0


def test_die_live_zeile_bricht_auf_390_px_nicht_um(app):
    """Die Zusatzzeile darf die Karte nicht sprengen."""
    app.set_viewport_size({"width": 390, "height": 900})
    ruesten(app, [{"status": 200, "json": {"price": 1234.56, "changePercent": -12.3}}])
    app.evaluate("() => window.MR.liveRunde()")
    befund = app.evaluate(
        """() => [...document.querySelectorAll('.live--karte')].map(el => ({
             hoehe: el.getBoundingClientRect().height,
             zeilen: el.querySelector('.live-txt').getClientRects().length,
             rechts: el.getBoundingClientRect().right,
           }))"""
    )
    assert befund, "keine Live-Zeile gefunden"
    for eintrag in befund:
        assert eintrag["zeilen"] == 1, f"die Zeile bricht um: {eintrag}"
        assert eintrag["rechts"] <= 390, f"sie ragt ueber den Rand: {eintrag}"
    assert app.evaluate(
        "document.documentElement.scrollWidth <= 390"
    ), "die Seite scrollt seitwaerts"
