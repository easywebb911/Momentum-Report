"""Das Default-Deny des Browser-Testkontexts (siehe conftest.py).

Vorsorge, kein akuter Fehler: bis hierher wurden nur zwei BEKANNTE Hosts
geblockt (Kurs-Worker, Elliott-Quelle) -- jeder andere externe Host durfte
durch. Eine neue externe Abhaengigkeit haette denselben blinden Fleck
erzeugt wie bei #12: sie faellt nur auf, wenn jemand aktiv daran denkt,
sie zu blocken. Jetzt gilt eine kleine, begruendete Allowlist -- alles
andere wird abgebrochen UND sichtbar gemeldet, nicht still verschluckt.

Zwei Ebenen werden geprueft:
  1. `pruefe_host()` selbst -- eine reine Funktion, schnell und ohne
     Flakiness-Risiko durch einen echten Browser.
  2. Die tatsaechliche Playwright-Verdrahtung -- ein echter, absichtlich
     an einen fremden Host gerichteter `fetch()`-Aufruf muss wirklich
     scheitern, nicht nur in der Theorie der Funktion oben.
"""

from __future__ import annotations

import pytest

from .conftest import ERLAUBTE_URL_PRAEFIXE, pruefe_host

# ==========================================================================
# Ebene 1: die reine Entscheidung, ohne Browser.
# ==========================================================================


@pytest.mark.parametrize(
    "url",
    [
        "file:///home/user/Momentum-Report/docs/index.html",
        "http://127.0.0.1:54321/index.html",
        "http://127.0.0.1:1/style.css",
        "https://quote-proxy.easywebb.workers.dev/?ticker=AAPL",
        "https://easywebb911.github.io/Elliott-Report/data/report.json",
    ],
)
def test_erlaubte_urls(url):
    erlaubt, grund = pruefe_host(url)
    assert erlaubt is True, (url, grund)
    assert grund, "eine Erlaubnis ohne Begruendung waere selbst ein Verstoss gegen die Regel"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.invalid/nichts-damit-zu-tun",
        "https://api.github.com/repos/easywebb911/Momentum-Report",
        "https://quote-proxy.easywebb.workers.dev.evil.example/?ticker=AAPL",
        # Derselbe Host, aber ein Pfad AUSSERHALB dessen, was die eigene
        # Route abfaengt -- genau die Luecke, die eine reine
        # Hostnamen-Pruefung (statt URL-Praefix) offen liesse.
        "https://easywebb911.github.io/ein-anderes-projekt/index.html",
        "http://192.168.1.1/",
        "http://localhost:8080/",
    ],
)
def test_fremde_urls_werden_abgelehnt(url):
    erlaubt, grund = pruefe_host(url)
    assert erlaubt is False, (url, grund)


def test_die_allowlist_ist_klein_und_jeder_eintrag_zeigt_auf_eine_eigene_route():
    """Wächter gegen das langsame Anwachsen der Allowlist: zwei Eintraege,
    beide mit Begruendung, beide URL-PRAEFIXE (nicht nur Hostnamen)."""
    assert len(ERLAUBTE_URL_PRAEFIXE) == 2, sorted(ERLAUBTE_URL_PRAEFIXE)
    for praefix, grund in ERLAUBTE_URL_PRAEFIXE.items():
        assert praefix.startswith("https://"), praefix
        assert praefix.endswith("/"), (
            praefix, "ein Praefix ohne trennenden Schraegstrich wuerde auch "
            "'https://quote-proxy.easywebb.workers.dev.evil.example/...' treffen"
        )
        assert grund, praefix


# ==========================================================================
# Ebene 2: die echte Playwright-Verdrahtung -- Nachweis statt Behauptung.
# ==========================================================================

pytestmark = pytest.mark.browser


def test_ein_fremder_fetch_wird_wirklich_blockiert(oeffne, server):
    """Der Beweis: eine absichtlich an einen unbekannten Host gerichtete
    Anfrage scheitert TATSAECHLICH im Browser -- nicht nur laut der
    Funktion oben. `erwarte_blockiert` bestaetigt der Fixture, dass genau
    dieser eine Host absichtlich blockiert werden soll; jeder andere
    unerwartete Block waere weiterhin ein Testfehler."""
    fremder_host = "example.invalid"
    page = oeffne("index.html", basis=server, erwarte_blockiert={fremder_host})

    ergebnis = page.evaluate(
        """() => fetch('https://example.invalid/nichts-damit-zu-tun')
             .then(() => 'DURCHGEKOMMEN')
             .catch(e => 'ABGELEHNT: ' + e.name)"""
    )
    assert ergebnis.startswith("ABGELEHNT"), (
        "ein Fremd-Host haette am Default-Deny scheitern muessen: " + ergebnis
    )


def test_erlaubte_hosts_werden_nicht_grundlos_mitblockiert(oeffne, server):
    """Gegenprobe: der lokale Test-Server bleibt erreichbar -- das
    Default-Deny ist kein Deny-Alles. Kein `erwarte_blockiert` noetig,
    weil hier gar nichts blockiert werden soll; scheitert das doch, faellt
    das automatisch am Fixture-Abschluss auf."""
    page = oeffne("index.html", basis=server)
    ergebnis = page.evaluate(
        f"""() => fetch({server!r} + '/style.css')
              .then(r => 'STATUS ' + r.status)
              .catch(e => 'ABGELEHNT: ' + e.name)"""
    )
    assert ergebnis == "STATUS 200", ergebnis
