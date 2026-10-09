"""split_waechter.py: Erkennung + Meldung einer vermutlich nicht
nachbereinigten Split-Vorgeschichte -- NUR Erkennen und Melden, siehe
Modul-Docstring fuer die volle Begruendung (Herleitung aus dem MNST-
Vorfall, Verhaeltnisliste, Toleranz).

Fuenf Nachweise, wie vom Auftrag gefordert:
  1. Fund-Fall, NACH dem MNST-Muster (nicht nur "nichts kaputt")
  2. Kein-Fund-Fall (normale Reihe)
  3. Reverse-Split-Fall (aeltere Teilreihe zu NIEDRIG statt zu HOCH)
  4. Fail-soft bei ntfy-Fehler (und bei einem Fehler in der Erkennung selbst)
  5. Determinismus (dieselbe Reihe -> immer dieselbe Meldung)
"""

from __future__ import annotations

import datetime as _dt

import pytest

from momentum import split_waechter as sw

Date = _dt.date


def _reihe_ohne_sprung(start: Date, tage: int, *, start_preis: float = 100.0) -> dict[Date, float]:
    """Eine ruhige Reihe: taegliche Schritte deutlich unter jeder Toleranz."""
    reihe = {}
    preis = start_preis
    tag = start
    for i in range(tage):
        # Kleine, deterministische Zickzack-Bewegung -- nie mehr als 1 %.
        preis *= 1.001 if i % 2 == 0 else 0.9995
        reihe[tag] = preis
        tag = tag + _dt.timedelta(days=1)
    return reihe


def _mnst_muster(*, naht: Date, faktor: float, tage_davor: int = 300, tage_danach: int = 60) -> dict[Date, float]:
    """Synthetische Reihe nach dem MNST-Muster: die aeltere Teilreihe (vor
    `naht`) steht auf dem um `faktor` ZU HOHEN Niveau (Split noch nicht
    nachbereinigt), die juengere Teilreihe (ab `naht`) auf dem korrekten
    Niveau -- exakt das Muster aus dem Modul-Docstring ("DER MECHANISMUS").
    """
    start = naht - _dt.timedelta(days=tage_davor)
    davor = _reihe_ohne_sprung(start, tage_davor, start_preis=50.0 * faktor)
    danach_start = naht + _dt.timedelta(days=1)
    letzter_davor_preis = davor[max(davor)]
    danach = _reihe_ohne_sprung(
        danach_start, tage_danach, start_preis=letzter_davor_preis / faktor
    )
    reihe = dict(davor)
    reihe[naht] = letzter_davor_preis / faktor  # der Tag der Naht selbst, korrekt
    reihe.update(danach)
    return reihe


# --------------------------------------------------------------- 1. Fund-Fall


def test_erkennt_mnst_muster():
    """Belegt das Ziel-Verhalten, nicht nur 'nichts kaputt': eine Reihe, die
    GENAU dem rekonstruierten MNST-Muster folgt (Split 2:1, aeltere
    Teilreihe exakt Faktor 2 zu hoch), muss als Fund mit Ziel 2.0 erkannt
    werden, am exakt richtigen Tagespaar.
    """
    naht = Date(2026, 8, 11)
    reihe = _mnst_muster(naht=naht, faktor=2.0)
    fund = sw.erkenne("MNST", reihe)
    assert fund is not None
    assert fund.ticker == "MNST"
    assert fund.ziel == 2.0
    assert fund.tag_danach == naht
    assert abs(fund.verhaeltnis - 2.0) / 2.0 <= sw.TOLERANZ_RELATIV


@pytest.mark.parametrize("faktor", [3.0, 4.0, 5.0, 10.0])
def test_erkennt_jedes_ziel_verhaeltnis(faktor):
    naht = Date(2026, 8, 11)
    reihe = _mnst_muster(naht=naht, faktor=faktor)
    fund = sw.erkenne("X", reihe)
    assert fund is not None
    assert fund.ziel == faktor


# ----------------------------------------------------------- 2. Kein-Fund-Fall


def test_kein_fund_bei_ruhiger_reihe():
    reihe = _reihe_ohne_sprung(Date(2026, 1, 1), 400)
    assert sw.erkenne("RUHIG", reihe) is None


def test_kein_fund_bei_3_zu_2_ausdruecklich_ausgeschlossen():
    """3:2 (1,5) ist ausdruecklich NICHT in ZIEL_VERHAELTNISSE -- ein
    Kurseinbruch um ein Drittel darf keinen Fund auslösen, auch wenn er
    exakt diesem Verhaeltnis entspricht (Begruendung: Modul-Docstring,
    'DIE VERHAELTNISLISTE')."""
    assert 1.5 not in sw.ZIEL_VERHAELTNISSE
    naht = Date(2026, 8, 11)
    reihe = _mnst_muster(naht=naht, faktor=1.5)
    assert sw.erkenne("CRASH", reihe) is None


def test_pruefe_universum_ohne_fund_liefert_leere_liste():
    adjusted = {
        "A": _reihe_ohne_sprung(Date(2026, 1, 1), 100),
        "B": _reihe_ohne_sprung(Date(2026, 1, 1), 100, start_preis=250.0),
    }
    assert sw.pruefe_universum(adjusted) == []


# --------------------------------------------------------- 3. Reverse-Split


def test_erkennt_reverse_split_aeltere_reihe_zu_niedrig():
    """Reverse-Split (Konsolidierung): die aeltere Teilreihe steht auf dem
    um `faktor` ZU NIEDRIGEN Niveau -- die Naht zeigt dann einen Sprung
    NACH OBEN statt nach unten. Dieselbe max/min-Formel muss das genauso
    erkennen wie den MNST-Fall (siehe erkenne()-Docstring)."""
    naht = Date(2026, 8, 11)
    start = naht - _dt.timedelta(days=200)
    davor = _reihe_ohne_sprung(start, 200, start_preis=20.0)
    letzter_davor = davor[max(davor)]
    danach_start = naht + _dt.timedelta(days=1)
    danach = _reihe_ohne_sprung(danach_start, 60, start_preis=letzter_davor * 4.0)
    reihe = dict(davor)
    reihe[naht] = letzter_davor * 4.0
    reihe.update(danach)

    fund = sw.erkenne("REV", reihe)
    assert fund is not None
    assert fund.ziel == 4.0
    assert fund.tag_danach == naht


# ------------------------------------------------------------- 4. Fail-soft


def test_pruefe_und_melde_ruft_melder_nur_bei_fund():
    aufrufe = []

    def melder(eintraege):
        aufrufe.append(eintraege)
        return True

    protokoll = []
    ohne_fund = {"RUHIG": _reihe_ohne_sprung(Date(2026, 1, 1), 100)}
    befunde = sw.pruefe_und_melde("us", ohne_fund, melder=melder, log=protokoll.append)
    assert befunde == []
    assert aufrufe == []


def test_pruefe_und_melde_bei_fund_bildet_einen_gebuendelten_push():
    aufrufe = []

    def melder(eintraege):
        aufrufe.append(eintraege)
        return True

    naht = Date(2026, 8, 11)
    mit_fund = {"MNST": _mnst_muster(naht=naht, faktor=2.0)}
    protokoll = []
    befunde = sw.pruefe_und_melde("us", mit_fund, melder=melder, log=protokoll.append)

    assert len(befunde) == 1
    # Genau EIN Aufruf des melders, mit ALLEN Funden gebuendelt -- nicht
    # einer je Fund.
    assert len(aufrufe) == 1
    eintraege = aufrufe[0]
    assert len(eintraege) == 1
    name, block = eintraege[0]
    assert name == "MNST"
    assert "MNST" in block and "evtl. unzuverlaessig" in block
    assert any("Split-Wächter" in z for z in protokoll)


def test_fail_soft_bei_melder_fehler():
    """Scheitert der Push (ntfy-Fehler), muss der Lauf trotzdem normal
    weiterlaufen: keine Ausnahme nach aussen, Fund bleibt im Rueckgabewert."""

    def kaputter_melder(eintraege):
        raise RuntimeError("ntfy nicht erreichbar")

    naht = Date(2026, 8, 11)
    mit_fund = {"MNST": _mnst_muster(naht=naht, faktor=2.0)}
    protokoll = []
    befunde = sw.pruefe_und_melde("us", mit_fund, melder=kaputter_melder, log=protokoll.append)

    assert len(befunde) == 1  # die Erkennung selbst bleibt unberuehrt
    assert any("fehlgeschlagen" in z for z in protokoll)


def test_fail_soft_bei_fehler_in_der_erkennung_selbst():
    """Auch ein Fehler VOR dem Melden (z. B. ein unerwarteter Datentyp in
    der Eingabereihe) darf nicht nach aussen durchschlagen."""

    class KaputteReihe(dict):
        def __iter__(self):
            raise ValueError("kaputte Eingabe")

    protokoll = []
    befunde = sw.pruefe_und_melde(
        "us", {"X": KaputteReihe({Date(2026, 1, 1): 1.0})}, melder=lambda e: True, log=protokoll.append
    )
    assert befunde == []
    assert any("fehlgeschlagen" in z for z in protokoll)


# ----------------------------------------------------------- 5. Determinismus


def test_determinismus_unabhaengig_von_dict_reihenfolge():
    naht = Date(2026, 8, 11)
    reihe = _mnst_muster(naht=naht, faktor=2.0)
    reihe_umsortiert = dict(reversed(list(reihe.items())))

    fund1 = sw.erkenne("MNST", reihe)
    fund2 = sw.erkenne("MNST", reihe_umsortiert)
    assert fund1 == fund2


def test_determinismus_wiederholter_aufruf_liefert_identische_meldung():
    naht = Date(2026, 8, 11)
    mit_fund = {"MNST": _mnst_muster(naht=naht, faktor=2.0)}

    protokoll1, protokoll2 = [], []
    sw.pruefe_und_melde("us", mit_fund, melder=lambda e: True, log=protokoll1.append)
    sw.pruefe_und_melde("us", mit_fund, melder=lambda e: True, log=protokoll2.append)
    assert protokoll1 == protokoll2


def test_pruefe_universum_sortiert_alphabetisch_nach_ticker():
    naht = Date(2026, 8, 11)
    adjusted = {
        "ZZZ": _mnst_muster(naht=naht, faktor=2.0),
        "AAA": _mnst_muster(naht=naht, faktor=3.0),
    }
    befunde = sw.pruefe_universum(adjusted)
    assert [f.ticker for f in befunde] == ["AAA", "ZZZ"]


# --------------------------------------------------- Statischer Nie-Handeln-Test


def test_der_waechter_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu den anderen Waechtern dieses
    Projekts: dieses Modul darf NUR lesen und melden."""
    from pathlib import Path

    quelltext = Path("src/momentum/split_waechter.py").read_text(encoding="utf-8")
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "git commit", "git push", "git add",
    ]
    for muster in verboten:
        assert muster not in quelltext, f"verbotenes Muster im Code gefunden: {muster!r}"
