"""TREND-AMPEL: ehrliche Aussage auf der Methodik-Seite (Lit-Check 14.11.2026).

Die Ampel misst die 12-Monats-Richtung des GESAMTMARKTS (Moskowitz/Ooi/
Pedersen 2012). Die bekannten Momentum-Crashes (Daniel & Moskowitz 2016)
gingen ueberwiegend auf die VERLIERER-Seite zurueck; Goyal, Jegadeesh &
Subrahmanyam (2025) bestaetigen das international. Fuer die Gewinner
allein ist ein Crash-Effekt nicht belegt -- die Seite darf die Ampel also
nicht als Crash-Schutz fuer die Top-5 darstellen.

Bewiesen wird:
  * die Methodik-Seite enthaelt den neuen Kern (Gesamtmarkt; Crash vor
    allem bei den schwaechsten Aktien; fuer Gewinner allein nicht belegt);
  * die alte Behauptung "Genau davor warnt die Trend-Ampel" ist weg;
  * die neue Quelle steht mit Journal-Angabe in sources.py und auf der Seite;
  * der Text ist fest -- er haengt weder an Datum noch an Daten.
"""

from __future__ import annotations

import datetime as _dt
import re

import momentum.render as render
from momentum.render import HONESTY, render_methodik
from momentum.sources import SOURCES


def _text(html: str) -> str:
    ohne_tags = re.sub(r"<[^>]+>", " ", html)
    ohne_tags = ohne_tags.replace("&amp;", "&")
    return re.sub(r"\s+", " ", ohne_tags)


def _ampel_karte(html: str) -> str:
    treffer = re.search(r'<article class="card mcard" id="trend-ampel">.*?</article>', html, re.S)
    assert treffer, "Ampel-Karte fehlt"
    return treffer.group(0)


def test_kern_satz_gesamtmarkt_und_crash_vor_allem_bei_verlierern():
    karte = _text(_ampel_karte(render_methodik()))
    assert "ob der Gesamtmarkt in einem Abwärtstrend ist" in karte
    assert "Das betrifft auch die Top-5" in karte
    assert "trafen vor allem die schwächsten Aktien" in karte
    assert "Für die Gewinner allein, also für eine Liste wie die Top-5, ist ein solcher Crash-Effekt nicht belegt" in karte
    assert "kein Crash-Schutz für die Top-5" in karte


def test_alte_behauptungen_sind_weg():
    html = render_methodik()
    assert "Genau davor warnt die Trend-Ampel" not in html
    assert "In genau solchen Phasen häuften sich historisch" not in html
    assert "Die schweren Einbrueche haeuften sich nach fallenden Maerkten." not in html
    assert "Genau davor" not in SOURCES["momentum_crash"].claim


def test_ehrlichkeits_hinweis_nennt_die_verlierer_seite():
    eintrag = {k: (t, x, l) for k, t, x, l in HONESTY}["momentum_crash"]
    assert "vor allem die schwaechsten Aktien" in eintrag[1]
    assert "fuer die Gewinner allein ist ein solcher Crash nicht belegt" in eintrag[1]
    assert eintrag[2] == "#trend-ampel"


def test_neue_quelle_mit_journal_und_auf_der_seite():
    q = SOURCES["momentum_states_intl"]
    assert q.authors == "Goyal, Jegadeesh & Subrahmanyam"
    assert q.year == 2025
    assert q.journal == "Review of Finance 29(1), 2025"
    assert "Verlierer" in q.claim
    karte = _ampel_karte(render_methodik())
    assert render.e(q.authors) in karte
    assert render.e(q.journal) in karte
    # Daniel & Moskowitz bleibt Quelle, mit korrigierter Aussage
    assert render.e(SOURCES["momentum_crash"].authors) in karte
    assert "Verlierer-Seite" in SOURCES["momentum_crash"].claim


def test_text_haengt_nicht_an_datum_oder_uhr(monkeypatch):
    vorher = render_methodik()

    class KaputteUhr(_dt.date):
        @classmethod
        def today(cls):
            raise AssertionError("render_methodik darf das Datum nicht lesen")

    class KaputteZeit(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("render_methodik darf die Uhr nicht lesen")

    monkeypatch.setattr(render._dt, "date", KaputteUhr)
    monkeypatch.setattr(render._dt, "datetime", KaputteZeit)
    assert render_methodik() == vorher
