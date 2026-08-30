"""DESIGN-CHECK auf 390 px Breite (iPhone) — gemessen, nicht geschaetzt.

Geprueft wird im echten Browser:
  * die Seite scrollt NICHT seitwaerts (kein Umbruch-Bruch)
  * kein einzelnes Element ragt ueber den Rand hinaus
  * eine Karte mit sehr langem Firmennamen bleibt heil
  * die Kacheln stehen in zwei sauberen Reihen (3 Kennzahlen + 2 Teil-Raenge)
  * auch bei groesster Textgroesse (20px) bleibt alles im Rahmen
  * das Kopf-Banner skaliert ueber sein viewBox-Verhaeltnis
  * jede Unterseite hat einen sichtbaren Rueckweg (PWA-Standalone!)
  * die vier Ehrlichkeits-Karten stehen in der Methodik, nicht mehr
    auf der Uebersicht — und kein Verweis zeigt ins Leere

Browser, gerenderte Seite und der Oeffnen-Helfer stehen in conftest.py.
Laeuft nur, wenn Playwright samt Browser vorhanden ist (Marker "browser").
"""

from __future__ import annotations

import pytest

from .conftest import BREITE, HOEHE

pytestmark = pytest.mark.browser

UNTERSEITEN = ["methodik.html", "konfluenz.html", "evaluation.html"]


@pytest.mark.parametrize("datei", ["index.html", "methodik.html", "konfluenz.html", "evaluation.html"])
@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_kein_seitliches_scrollen(oeffne, datei, schriftgroesse):
    page = oeffne(datei, schriftgroesse)
    breite = page.evaluate("document.documentElement.scrollWidth")
    assert breite <= BREITE, (
        f"{datei} bei {schriftgroesse}px scrollt seitwaerts: {breite}px > {BREITE}px"
    )


@pytest.mark.parametrize("datei", ["index.html", "methodik.html", "konfluenz.html", "evaluation.html"])
@pytest.mark.parametrize("schriftgroesse", [16, 20])
def test_kein_element_ragt_ueber_den_rand(oeffne, datei, schriftgroesse):
    page = oeffne(datei, schriftgroesse)
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
    assert ueberstand == [], f"Elemente ausserhalb des Bildschirms: {ueberstand}"


def test_langer_firmenname_bleibt_einzeilig(oeffne):
    page = oeffne("index.html")
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


def test_die_kacheln_stehen_in_zwei_sauberen_reihen(oeffne):
    """Drei Kennzahl-Kacheln oben, zwei Teil-Rang-Kacheln darunter.

    Frueher waren es nur die drei oberen. Mit der Gleichgewichtung kamen die
    beiden Teil-Raenge dazu — sie stehen bewusst in einer EIGENEN Reihe:
    zwei Kacheln in der Dreier-Spur haetten eine Luecke gelassen.
    """
    page = oeffne("index.html")
    reihen = page.evaluate(
        """() => Array.from(document.querySelector('.card').querySelectorAll('.metrics'))
             .map(g => Array.from(g.querySelectorAll('.metric-box'))
               .map(el => Math.round(el.getBoundingClientRect().top)))"""
    )
    assert len(reihen) == 2, f"erwartet zwei Kachelreihen, gefunden {len(reihen)}"
    assert len(reihen[0]) == 3 and len(reihen[1]) == 2, reihen
    for oberkanten in reihen:
        assert len(set(oberkanten)) == 1, f"Kacheln umgebrochen: {oberkanten}"
    assert reihen[1][0] > reihen[0][0], "die Rang-Reihe steht nicht darunter"


def test_die_teil_raenge_stehen_auf_der_karte(oeffne):
    """Die Mischung soll sichtbar sein, nicht behauptet."""
    page = oeffne("index.html")
    befund = page.evaluate(
        """() => {
          const g = document.querySelector('.card').querySelector('.metrics--rang');
          const kacheln = Array.from(g.querySelectorAll('.metric-box'));
          return kacheln.map(k => ({
            wert: k.querySelector('.m-val').textContent,
            label: k.querySelector('.m-lbl').textContent,
            breite: k.getBoundingClientRect().width,
            abgeschnitten: k.querySelector('.m-val').scrollWidth
                         > k.querySelector('.m-val').clientWidth,
          }));
        }"""
    )
    assert len(befund) == 2
    assert "Rang 12-1-Momentum" in befund[0]["label"]
    assert "Rang 52W-Hoch-Nähe" in befund[1]["label"]
    for kachel in befund:
        assert "von" in kachel["wert"], kachel
        assert kachel["abgeschnitten"] is False, f"Wert abgeschnitten: {kachel}"
        assert kachel["breite"] >= 150, kachel


@pytest.mark.parametrize("schriftgroesse", [16, 20])
def test_der_eingefrorene_stichtag_kurs_ist_lesbar_und_bricht_nicht_um(oeffne, schriftgroesse):
    """Transparenz-Zusatz: der Stichtag-Kurs steht als eigener Satz unter
    der Karte -- klar getrennt vom Live-Kurs-Feld weiter oben, das per
    JavaScript aktualisiert wird. Geprueft wird hier NUR das Layout; dass
    der Wert stimmt, prueft tests/unit/test_render.py."""
    page = oeffne("index.html", schriftgroesse)
    befund = page.evaluate(
        """() => Array.from(document.querySelectorAll('.card')).map(karte => {
             const satz = karte.querySelector('.card-ft--stichtag');
             const kurs = karte.querySelector('[data-quote]');
             return {
               text: satz ? satz.textContent : null,
               eigenes_element: satz !== kurs && !kurs.closest('.card-ft--stichtag'),
               rechts: satz ? satz.getBoundingClientRect().right : null,
               karten_rechts: karte.getBoundingClientRect().right,
             };
           })"""
    )
    assert befund, "keine Karte gefunden"
    for eintrag in befund:
        assert eintrag["text"], "kein Stichtag-Satz auf der Karte gefunden"
        assert "eingefroren" in eintrag["text"], eintrag
        assert eintrag["eigenes_element"] is True, (
            "der Stichtag-Kurs sitzt im selben Element wie der Live-Kurs", eintrag
        )
        assert eintrag["rechts"] <= eintrag["karten_rechts"] + 0.5, \
            f"der Satz tritt aus der Karte aus: {eintrag}"


def test_karte_und_kacheln_haben_sinnvolle_breiten(oeffne):
    """Bei 390 px: Karte ~358 px, Kacheln je gut 110 px — nichts wird gequetscht."""
    page = oeffne("index.html")
    masse = page.evaluate(
        """() => {
          const karte = document.querySelector('.card').getBoundingClientRect();
          const kachel = document.querySelector('.metric-box').getBoundingClientRect();
          return {karte: karte.width, kachel: kachel.width};
        }"""
    )
    assert 340 <= masse["karte"] <= 366, masse
    assert masse["kachel"] >= 100, masse


# --------------------------------------------------------------- Banner


def test_banner_skaliert_ueber_das_viewbox_verhaeltnis(oeffne):
    """Volle Inhaltsbreite, Hoehe rein aus dem viewBox — kein festes Mass."""
    page = oeffne("index.html")
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


def test_das_banner_steht_direkt_unter_der_ueberschrift(oeffne):
    """Reihenfolge: Ueberschrift → Banner → Hinweis-Bereich → Inhalt."""
    page = oeffne("index.html")
    reihenfolge = page.evaluate(
        """() => [...document.querySelector('main').children]
             .map(el => el.className.split(' ')[0])"""
    )
    assert reihenfolge[0] == "banner", reihenfolge
    assert reihenfolge.index("banner") < reihenfolge.index("market"), reihenfolge
    # Der Ehrlichkeits-Block stand frueher dazwischen; er ist in die
    # Methodik gezogen und darf hier nicht mehr auftauchen.
    assert "disc-box" not in reihenfolge, reihenfolge

    # ... und zwar UNTER dem Kopf, nicht darin.
    lage = page.evaluate(
        """() => {
          const kopf = document.querySelector('.hdr');
          const band = document.querySelector('.banner');
          return {
            im_kopf: kopf.contains(band),
            kopf_unten: kopf.getBoundingClientRect().bottom,
            band_oben: band.getBoundingClientRect().top,
          };
        }"""
    )
    assert lage["im_kopf"] is False, "das Banner steckt im sticky Kopf"
    assert lage["band_oben"] >= lage["kopf_unten"] - 0.5, lage


def test_das_banner_klebt_beim_scrollen_nicht(oeffne):
    """Nur der Kopf bleibt stehen — das Band scrollt weg wie jeder Inhalt."""
    page = oeffne("index.html")
    vorher = page.evaluate(
        """() => ({
          kopf: document.querySelector('.hdr').getBoundingClientRect().top,
          band: document.querySelector('.banner').getBoundingClientRect().top,
        })"""
    )
    page.evaluate("window.scrollTo(0, 900)")
    nachher = page.evaluate(
        """() => ({
          kopf: document.querySelector('.hdr').getBoundingClientRect().top,
          band: document.querySelector('.banner').getBoundingClientRect().top,
          gescrollt: window.scrollY,
        })"""
    )
    assert nachher["gescrollt"] > 500, "die Seite hat gar nicht gescrollt"
    # Der Kopf bleibt oben stehen — sticky-Verhalten unveraendert ...
    assert abs(nachher["kopf"] - vorher["kopf"]) < 1, (vorher, nachher)
    # ... das Banner ist nach oben aus dem Bild gewandert.
    assert nachher["band"] < vorher["band"] - 500, (vorher, nachher)


def test_das_banner_laedt_nichts_nach(oeffne):
    """Inline und autark: kein Bild, kein Fetch, keine Schriftdatei."""
    page = oeffne("index.html")
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


# --------------------------------------------- Ehrlichkeits-Block (Umzug)


def test_die_uebersicht_zeigt_den_ehrlichkeits_block_nicht_mehr(oeffne):
    page = oeffne("index.html")
    assert page.locator(".disc-box").count() == 0
    assert page.locator(".disc-item").count() == 0
    # Der Haftungshinweis im Fuss bleibt.
    assert "Keine Anlageberatung" in page.inner_text("footer")


def test_alle_vier_karten_stehen_samt_quellen_in_der_methodik(oeffne):
    page = oeffne("methodik.html")
    karten = page.evaluate(
        """() => [...document.querySelectorAll('#ehrlich-gesagt .disc-item')]
             .map(li => ({
               titel: li.querySelector('.disc-title').textContent.trim(),
               text: li.querySelector('.disc-text').textContent.trim(),
               quelle: li.querySelector('.disc-src').textContent.trim(),
               sichtbar: li.getBoundingClientRect().height > 0,
             }))"""
    )
    assert len(karten) == 4, karten
    titel = [k["titel"] for k in karten]
    assert titel == [
        "Staerkstes Momentum nach belegter Methode",
        "Momentum kann abrupt einbrechen",
        "Der Effekt ist geschrumpft",
        "Hier fehlt die halbe Studie",
    ], titel
    for karte in karten:
        assert karte["sichtbar"], karte
        assert karte["text"], karte
        # Jede Karte nennt Autoren, Jahr und Journal.
        assert "(" in karte["quelle"] and ")" in karte["quelle"], karte
        assert len(karte["quelle"]) > 20, karte


def test_der_ampel_verweis_ist_kein_toter_anker(oeffne):
    """Der Link zeigt jetzt INNERHALB der Methodik — das Ziel muss es geben."""
    page = oeffne("methodik.html")
    ziel = page.get_attribute("#ehrlich-gesagt .disc-link", "href")
    assert ziel == "#trend-ampel", ziel
    assert page.locator("#trend-ampel").count() == 1, "Ankerziel fehlt"

    page.click("#ehrlich-gesagt .disc-link")
    assert page.url.endswith("#trend-ampel"), page.url
    oben = page.evaluate(
        "document.querySelector('#trend-ampel').getBoundingClientRect().top"
    )
    assert -1 <= oben <= HOEHE, f"Sprungziel nicht im Bild (top={oben})"


def test_kein_link_der_seiten_zeigt_ins_leere(oeffne):
    """Jeder Sprungmarken-Verweis muss auf ein vorhandenes Ziel zeigen."""
    for datei in ("index.html", "methodik.html", "konfluenz.html", "evaluation.html"):
        page = oeffne(datei)
        tot = page.evaluate(
            """() => [...document.querySelectorAll('a[href]')]
                 .map(a => a.getAttribute('href'))
                 .filter(h => h.startsWith('#'))
                 .filter(h => h.length > 1 && !document.querySelector(h))"""
        )
        assert tot == [], f"{datei}: tote Anker {tot}"


# ------------------------------------------------------- Rueckweg (PWA)
#
# In der installierten PWA laeuft die Seite im Standalone-Modus: KEINE
# Adresszeile, KEINE Zurueck-Taste. Eine Unterseite ohne sichtbaren
# Rueckweg waere dort eine Sackgasse, aus der nur ein Neustart der App
# herausfuehrt. Deshalb wird der Rueckweg hier gemessen, nicht behauptet.


@pytest.mark.parametrize("datei", UNTERSEITEN)
@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_jede_unterseite_hat_einen_sichtbaren_rueckweg(oeffne, datei, schriftgroesse):
    page = oeffne(datei, schriftgroesse)
    befund = page.evaluate(
        """() => {
          const a = document.querySelector('.back');
          if (!a) { return null; }
          const r = a.getBoundingClientRect();
          const stil = getComputedStyle(a);
          return {
            ziel: a.getAttribute('href'),
            text: a.textContent.trim(),
            breite: r.width, hoehe: r.height,
            oben: r.top,
            sichtbar: stil.display !== 'none' && stil.visibility !== 'hidden',
          };
        }"""
    )
    assert befund is not None, f"{datei} hat keinen Rueckweg"
    assert befund["ziel"] == "./index.html", befund
    assert "Zurück" in befund["text"], befund
    assert befund["sichtbar"] is True
    # 44 px sind die Untergrenze fuer eine Tippflaeche (Apple HIG).
    assert befund["hoehe"] >= 44, f"Tippflaeche nur {befund['hoehe']}px hoch"
    assert befund["breite"] >= 44, f"Tippflaeche nur {befund['breite']}px breit"
    # Er muss im ersten Bildschirm stehen, nicht erst nach dem Scrollen.
    assert befund["oben"] < 200, befund


@pytest.mark.parametrize("datei", UNTERSEITEN)
def test_der_rueckweg_fuehrt_wirklich_zur_uebersicht(oeffne, datei):
    """Ohne Browser-Zurueck: einmal tippen muss reichen."""
    page = oeffne(datei)
    page.click(".back")
    page.wait_for_load_state()
    assert page.url.endswith("index.html"), page.url
    assert page.locator(".card").count() > 0, "die Uebersicht zeigt keine Karten"
    # Die Uebersicht selbst braucht keinen Rueckweg — sie IST das Ziel.
    assert page.locator(".back").count() == 0


def test_der_rueckweg_bleibt_beim_scrollen_stehen(oeffne):
    """Der Kopf ist sticky — sonst waere der Rueckweg nach unten weg."""
    page = oeffne("methodik.html")
    page.evaluate("window.scrollTo(0, 1200)")
    oben = page.evaluate(
        "document.querySelector('.back').getBoundingClientRect().top"
    )
    assert oben >= -0.5, f"Rueckweg aus dem Bild gescrollt (top={oben})"
    assert oben < 200, oben


# ----------------------------------------------- Menue, Dialog, Banner


def test_menue_laesst_sich_oeffnen_und_schliessen(oeffne):
    page = oeffne("index.html")
    assert page.is_hidden("#overlay")
    page.click("#menu-btn")
    assert page.is_visible("#overlay")
    page.click(".sheet-close")
    assert page.is_hidden("#overlay")


def test_die_menue_knoepfe_sind_gross_genug_zum_tippen(oeffne):
    page = oeffne("index.html")
    page.click("#menu-btn")
    hoehen = page.evaluate(
        """() => [...document.querySelectorAll('.sheet-item--btn')]
             .map(el => ({id: el.id, h: el.getBoundingClientRect().height}))"""
    )
    assert [h["id"] for h in hoehen] == ["reload-btn", "recalc-btn", "lock-btn"]
    for eintrag in hoehen:
        assert eintrag["h"] >= 44, eintrag


def test_der_token_dialog_passt_auf_den_schirm(oeffne):
    page = oeffne("index.html")
    page.evaluate("window.MR.dialogOeffnen(null)")
    masse = page.evaluate(
        """() => {
          const d = document.querySelector('.tok-dlg');
          const r = d.getBoundingClientRect();
          const feld = document.querySelector('.tok-input').getBoundingClientRect();
          const knopf = document.querySelector('#tok-save').getBoundingClientRect();
          return {links: r.left, rechts: r.right, hoehe: r.height,
                  feldhoehe: feld.height, knopfhoehe: knopf.height,
                  scroll: document.documentElement.scrollWidth};
        }"""
    )
    assert masse["links"] >= -0.5 and masse["rechts"] <= BREITE + 0.5, masse
    assert masse["hoehe"] <= 844, "Dialog hoeher als der Schirm"
    assert masse["feldhoehe"] >= 44 and masse["knopfhoehe"] >= 44, masse
    assert masse["scroll"] <= BREITE, masse


def test_der_lauf_banner_passt_auf_den_schirm(oeffne):
    page = oeffne("index.html")
    page.evaluate(
        "window.MR.bannerZeigen('fehler',"
        "'Der Lauf ist fehlgeschlagen (failure). Der Grund steht im Actions-Protokoll.',"
        "'https://github.com/x/y/actions/runs/1')"
    )
    masse = page.evaluate(
        """() => {
          const r = document.querySelector('#runbar').getBoundingClientRect();
          const zu = document.querySelector('#runbar-close').getBoundingClientRect();
          return {links: r.left, rechts: r.right, unten: r.bottom,
                  zu_h: zu.height, zu_b: zu.width,
                  scroll: document.documentElement.scrollWidth};
        }"""
    )
    assert masse["links"] >= -0.5 and masse["rechts"] <= BREITE + 0.5, masse
    assert masse["unten"] <= 844.5, masse
    assert masse["zu_h"] >= 44 and masse["zu_b"] >= 44, masse
    assert masse["scroll"] <= BREITE, masse


def test_textgroesse_skaliert_die_gesamte_oberflaeche(oeffne):
    page = oeffne("index.html")
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


def test_kontrast_der_gedimmten_schrift_ist_ausreichend(oeffne):
    """--txt-dim #8b97a8 auf --bg #0a0c12 muss WCAG AA (4,5:1) schaffen."""
    page = oeffne("index.html")
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


# ------------------------------------------------------------ Trend-Tacho
#
# Die Testseite traegt beide Zustaende: USA mit Warnung (synthetischer
# Report), Deutschland ohne. So sind sie in EINEM Seitenaufbau messbar.


def test_beide_zustaende_stehen_auf_der_seite(oeffne):
    page = oeffne("index.html")
    befund = page.evaluate(
        """() => [...document.querySelectorAll('.tta')].map(svg => ({
             id: svg.id,
             warn: svg.classList.contains('tta--warn'),
             label: svg.getAttribute('aria-label'),
             zahl: svg.querySelector('.tta-zahl').textContent,
             farbe: svg.querySelector('.tta-zahl').getAttribute('fill'),
             nadel: {
               x: +svg.querySelector('.tta-nadel').getAttribute('x2'),
               y: +svg.querySelector('.tta-nadel').getAttribute('y2'),
             },
           }))"""
    )
    assert len(befund) == 2, befund
    assert [b["id"] for b in befund] == ["tta-us", "tta-de"]

    warn = [b for b in befund if b["warn"]]
    ruhig = [b for b in befund if not b["warn"]]
    assert len(warn) == 1 and len(ruhig) == 1, befund

    # Warnfall: Rendite negativ -> Nadel links, Zahl rot.
    assert warn[0]["nadel"]["x"] < 60, warn
    assert warn[0]["farbe"] == "#f87171", warn
    assert "Warnung" in warn[0]["label"], warn

    # Ruhiger Fall: Rendite positiv -> Nadel rechts, Zahl gruen.
    assert ruhig[0]["nadel"]["x"] > 60, ruhig
    assert ruhig[0]["farbe"] == "#4ade80", ruhig
    assert "kein Alarm" in ruhig[0]["label"], ruhig


def test_der_tacho_passt_neben_den_text_und_laeuft_nicht_ueber(oeffne):
    page = oeffne("index.html")
    masse = page.evaluate(
        """() => [...document.querySelectorAll('.ampel')].map(box => {
             const svg = box.querySelector('.tta');
             const text = box.querySelector('.ampel-body');
             const b = box.getBoundingClientRect();
             const s = svg.getBoundingClientRect();
             const t = text.getBoundingClientRect();
             return {links: s.left, rechts: s.right, breite: s.width,
                     hoehe: s.height, box_links: b.left, box_rechts: b.right,
                     text_links: t.left, text_breite: t.width,
                     gestapelt: t.top >= s.bottom - 1};
           })"""
    )
    assert len(masse) == 2
    for m in masse:
        assert m["links"] >= m["box_links"] - 0.5, m
        assert m["rechts"] <= m["box_rechts"] + 0.5, m
        assert m["breite"] > 60, "der Tacho ist zu klein zum Ablesen"
        # Seitenverhaeltnis 120:72 = 1,667
        assert abs(m["breite"] / m["hoehe"] - 120 / 72) < 0.05, m
        # nebeneinander ODER sauber gestapelt — nur nicht gequetscht
        assert m["text_breite"] >= 150, m
    assert page.evaluate("document.documentElement.scrollWidth") <= BREITE


@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_die_trend_box_bleibt_bei_jeder_textgroesse_heil(oeffne, schriftgroesse):
    page = oeffne("index.html", schriftgroesse)
    ueberstand = page.evaluate(
        """() => {
          const raus = [];
          document.querySelectorAll('.ampel, .ampel *').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && (r.right > window.innerWidth + 0.5 || r.left < -0.5)) {
              raus.push((el.className.baseVal ?? el.className) + '|'
                        + Math.round(r.left) + '..' + Math.round(r.right));
            }
          });
          return raus;
        }"""
    )
    assert ueberstand == [], ueberstand
    assert page.evaluate("document.documentElement.scrollWidth") <= BREITE


def test_nur_die_nadel_pulsiert_und_nur_im_warnfall(oeffne):
    page = oeffne("index.html")
    animationen = page.evaluate(
        """() => [...document.querySelectorAll('.tta')].map(svg => ({
             warn: svg.classList.contains('tta--warn'),
             nadel: getComputedStyle(svg.querySelector('.tta-nadel')).animationName,
             boegen: [...svg.querySelectorAll('path')]
               .map(p => getComputedStyle(p).animationName),
             zahl: getComputedStyle(svg.querySelector('.tta-zahl')).animationName,
             nabe: getComputedStyle(svg.querySelector('circle')).animationName,
           }))"""
    )
    for eintrag in animationen:
        assert eintrag["nadel"] == ("tta-puls" if eintrag["warn"] else "none"), eintrag
        assert eintrag["boegen"] == ["none", "none"], eintrag
        assert eintrag["zahl"] == "none" and eintrag["nabe"] == "none", eintrag


def test_bei_reduzierter_bewegung_pulsiert_nichts(oeffne):
    """prefers-reduced-motion wird respektiert — die Anzeige bleibt statisch."""
    page = oeffne("index.html", bewegung="reduce")
    animationen = page.evaluate(
        """() => [...document.querySelectorAll('.tta .tta-nadel')]
             .map(el => getComputedStyle(el).animationName)"""
    )
    assert animationen == ["none", "none"], animationen
    # Gegenprobe: ohne die Einstellung pulsiert der Warnfall sehr wohl.
    normal = oeffne("index.html")
    assert "tta-puls" in normal.evaluate(
        """() => [...document.querySelectorAll('.tta .tta-nadel')]
             .map(el => getComputedStyle(el).animationName).join(',')"""
    )


# ---------------------------------------------------- Ueberschuss-Kriterium
#
# Die Satz-Box ist mit dem Zins-Abzug laenger geworden ("... über
# Geldmarkt") und traegt im Ausfall eine zusaetzliche Zeile. Beides wird
# hier auf 390 px gemessen, nicht geschaetzt.


def test_beide_zins_zustaende_stehen_auf_der_seite(oeffne):
    page = oeffne("index.html")
    boxen = page.evaluate(
        """() => [...document.querySelectorAll('.ampel')].map(box => ({
             text: box.querySelector('.ampel-body').innerText,
             hinweis: box.querySelector('.ampel-hinweis')?.innerText ?? null,
             label: box.querySelector('.tta').getAttribute('aria-label'),
           }))"""
    )
    assert len(boxen) == 2, boxen

    mit = [b for b in boxen if b["hinweis"] is None]
    ohne = [b for b in boxen if b["hinweis"] is not None]
    assert len(mit) == 1 and len(ohne) == 1, boxen

    # Mit Zins-Abzug: die Zahl ist ausdruecklich eine Ueberschussrendite.
    assert "über Geldmarkt" in mit[0]["text"], mit
    assert "Geldmarkt" in mit[0]["label"], mit

    # Ohne Zins-Abzug: sichtbarer Hinweis -- und dann darf NIRGENDS
    # "über Geldmarkt" stehen, weder im Satz noch im Vorlesetext.
    assert ohne[0]["hinweis"] == "ohne Zins-Abzug — Zinsquelle nicht erreichbar"
    assert "über Geldmarkt" not in ohne[0]["text"], ohne
    assert "Geldmarkt" not in ohne[0]["label"], ohne


@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_der_zins_hinweis_bleibt_im_rahmen(oeffne, schriftgroesse):
    page = oeffne("index.html", schriftgroesse)
    masse = page.evaluate(
        """() => [...document.querySelectorAll('.ampel-hinweis')].map(el => {
             const r = el.getBoundingClientRect();
             return {links: r.left, rechts: r.right, hoehe: r.height,
                     sichtbar: getComputedStyle(el).display !== 'none'};
           })"""
    )
    assert masse, "der Ausfall-Hinweis fehlt auf der Testseite"
    for m in masse:
        assert m["sichtbar"] is True, m
        assert m["hoehe"] > 0, "ein Hinweis mit Hoehe 0 ist versteckt"
        assert m["links"] >= -0.5 and m["rechts"] <= BREITE + 0.5, m
    assert page.evaluate("document.documentElement.scrollWidth") <= BREITE
