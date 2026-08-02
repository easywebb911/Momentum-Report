"""DESIGN-CHECK auf 390 px Breite (iPhone) — gemessen, nicht geschaetzt.

Geprueft wird im echten Browser:
  * die Seite scrollt NICHT seitwaerts (kein Umbruch-Bruch)
  * kein einzelnes Element ragt ueber den Rand hinaus
  * eine Karte mit sehr langem Firmennamen bleibt heil
  * die drei Kennzahl-Kacheln stehen nebeneinander in einer Reihe
  * auch bei groesster Textgroesse (20px) bleibt alles im Rahmen
  * das Kopf-Banner skaliert ueber sein viewBox-Verhaeltnis
  * jede Unterseite hat einen sichtbaren Rueckweg (PWA-Standalone!)

Browser, gerenderte Seite und der Oeffnen-Helfer stehen in conftest.py.
Laeuft nur, wenn Playwright samt Browser vorhanden ist (Marker "browser").
"""

from __future__ import annotations

import pytest

from .conftest import BREITE

pytestmark = pytest.mark.browser

UNTERSEITEN = ["methodik.html"]


@pytest.mark.parametrize("datei", ["index.html", "methodik.html"])
@pytest.mark.parametrize("schriftgroesse", [15, 16, 20])
def test_kein_seitliches_scrollen(oeffne, datei, schriftgroesse):
    page = oeffne(datei, schriftgroesse)
    breite = page.evaluate("document.documentElement.scrollWidth")
    assert breite <= BREITE, (
        f"{datei} bei {schriftgroesse}px scrollt seitwaerts: {breite}px > {BREITE}px"
    )


@pytest.mark.parametrize("datei", ["index.html", "methodik.html"])
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


def test_die_drei_kacheln_stehen_in_einer_reihe(oeffne):
    page = oeffne("index.html")
    oberkanten = page.evaluate(
        """() => Array.from(document.querySelector('.card').querySelectorAll('.metric-box'))
             .map(el => Math.round(el.getBoundingClientRect().top))"""
    )
    assert len(oberkanten) == 3
    assert len(set(oberkanten)) == 1, f"Kacheln umgebrochen: {oberkanten}"


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


def test_warnungen_stehen_ueber_dem_schmuckband(oeffne):
    """Dekoration darf die vier Ehrlichkeits-Anzeigen nicht nach unten druecken."""
    page = oeffne("index.html")
    reihenfolge = page.evaluate(
        """() => [...document.querySelector('main').children]
             .map(el => el.className.split(' ')[0])"""
    )
    assert reihenfolge.index("disc-box") < reihenfolge.index("banner"), reihenfolge
    assert reihenfolge.index("banner") < reihenfolge.index("market"), reihenfolge


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
    assert page.locator(".disc-box").count() == 1
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
