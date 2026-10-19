"""Stichtags-Mechanik: wann ein Ranking faellig ist und auf welchen Tag.

Der Marktindex dient als Handelskalender — deshalb braucht das Werkzeug
keine gepflegte Feiertagsliste und kann auch keinen Feiertag "verpassen".
"""

from __future__ import annotations

import datetime as _dt

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.ranking import (
    RankingNotPossible,
    due_months,
    is_last_weekday_of_month,
    resolve_asof,
    zu_frueh_fuer_stichtag,
)
from momentum.render import last_weekday_of_month
from momentum.scoring import shift_month

Date = _dt.date


@pytest.mark.parametrize(
    "tag,erwartet",
    [
        (Date(2026, 7, 31), True),   # Freitag, letzter Tag des Monats
        (Date(2026, 7, 30), False),  # Donnerstag, der Freitag kommt noch
        (Date(2026, 8, 31), True),   # Montag, letzter Tag des Monats
        (Date(2026, 5, 29), True),   # Freitag; 30./31. Mai sind Sa/So
        (Date(2026, 5, 31), True),   # Sonntag nach dem letzten Werktag
        (Date(2026, 5, 28), False),  # Donnerstag
    ],
)
def test_letzter_werktag_erkennung(tag, erwartet):
    assert is_last_weekday_of_month(tag) is erwartet


def test_erster_stichtag_ist_juli_2026():
    """Das Werkzeug beginnt rueckwirkend mit dem letzten Handelstag Juli 2026."""
    assert due_months(Date(2026, 7, 31)) == [(2026, 7)]
    assert due_months(Date(2026, 7, 30)) == []


def test_lauf_anfang_august_holt_juli_nach():
    """Auch ohne Lauf am 31.07. entsteht das Juli-Ranking — mit korrektem Stichtag."""
    assert due_months(Date(2026, 8, 2)) == [(2026, 7)]
    assert due_months(Date(2026, 8, 20)) == [(2026, 7)]


def test_abgeschlossene_monate_werden_nachgeholt():
    assert due_months(Date(2026, 9, 15)) == [(2026, 7), (2026, 8)]
    assert due_months(Date(2026, 10, 1)) == [(2026, 7), (2026, 8), (2026, 9)]


def test_laufender_monat_erst_am_letzten_werktag():
    assert (2026, 8) not in due_months(Date(2026, 8, 28))
    assert (2026, 8) in due_months(Date(2026, 8, 31))


def test_stichtag_faellt_bei_feiertag_auf_den_letzten_handelstag():
    """Ist der letzte Werktag geschlossen, ist der Stichtag der Tag davor."""
    index = {
        Date(2026, 7, 29): 4000.0,
        Date(2026, 7, 30): 4010.0,
        # 31.07. fehlt: Boerse geschlossen
    }
    assert resolve_asof(index, 2026, 7, Date(2026, 7, 31)) == Date(2026, 7, 30)


def test_stichtag_ohne_indexdaten_bricht_laut_ab():
    with pytest.raises(RankingNotPossible, match="Stichtag"):
        resolve_asof({Date(2026, 6, 30): 1.0}, 2026, 7, Date(2026, 7, 31))


def test_stichtag_greift_nie_in_die_zukunft():
    index = {Date(2026, 7, 29): 1.0, Date(2026, 7, 30): 1.0, Date(2026, 7, 31): 1.0}
    assert resolve_asof(index, 2026, 7, Date(2026, 7, 30)) == Date(2026, 7, 30)


def test_der_reale_31_08_fall_waere_als_zu_frueh_erkannt_worden():
    """Regressionsbeleg: Lauf 48, 31.08.2026 08:46 UTC (manueller Dispatch).

    Der damals fuer DE eingefrorene Kurs war nachweislich untertaegig
    (siehe SESSION_HANDOVER.md, Zahlenbeleg aus der letzten Diagnose) --
    mit der neuen Pruefung waere das erkannt worden. 31.08.2026 ist selbst
    ein Montag (Werktag) -- der Handelstag UND das Laufdatum fallen auf
    denselben Kalendertag, PR #53s Normalfall.
    """
    de = MARKETS_BY_KEY["de"]
    assert zu_frueh_fuer_stichtag(de, Date(2026, 8, 31), _dt.time(8, 46)) is True


def test_regulaerer_abend_lauf_bleibt_unveraendert():
    """Der planmaessige 21:45-UTC-Lauf (nach Schluss beider Maerkte) darf
    von der Haertung NIE ausgeloest werden -- fuer keinen der beiden
    Maerkte."""
    for markt in MARKETS_BY_KEY.values():
        assert zu_frueh_fuer_stichtag(markt, Date(2026, 8, 31), _dt.time(21, 45)) is False


@pytest.mark.parametrize(
    "markt_key,zu_frueh,gerade_rechtzeitig",
    [
        ("de", _dt.time(16, 29), _dt.time(16, 30)),
        ("us", _dt.time(20, 59), _dt.time(21, 0)),
    ],
)
def test_schwelle_je_markt_greift_exakt_an_der_grenze(markt_key, zu_frueh, gerade_rechtzeitig):
    markt = MARKETS_BY_KEY[markt_key]
    heute = Date(2026, 8, 31)  # Montag, Handelstag == Laufdatum
    assert zu_frueh_fuer_stichtag(markt, heute, zu_frueh) is True
    assert zu_frueh_fuer_stichtag(markt, heute, gerade_rechtzeitig) is False


# --------------------------------------------------------------------------
# Mitternachts-/Wochenend-Rutsch -- Diagnose vom 19.10.2026 (SESSION_HANDOVER)
#
# Befund: zu_frueh_fuer_stichtag() verglich nur jetzt_utc.time(), nie das
# Datum. Rutscht ein Lauf ueber Mitternacht UTC auf einen Tag, der noch im
# selben Monat liegt und fuer den is_last_weekday_of_month() True ist (z. B.
# nominell Fr 30.10.2026 21:45 UTC, Start Sa 31.10. 02:45 UTC), hielt die
# alte Fassung "02:45" IMMER fuer "vor 21:00/16:30" -- unabhaengig vom
# Kalendertag. Testfaelle a-g, wie im Auftrag benannt.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("markt_key", ["us", "de"])
def test_testfall_a_mitternachtsrutsch_ist_nicht_mehr_zu_frueh(markt_key):
    """Testfall a: Sa 31.10.2026 02:45 UTC, Oktober faellig -- NICHT zu frueh.

    Das ist der reale Befund: Oktober endet auf Fr 30.10./Sa 31.10.2026,
    ein verzoegerter Lauf rutscht ueblicherweise in die fruehen
    Samstagsstunden (siehe Drift-Diagnose: Freitags Ø 2,7 Std., Max 5,6 Std.
    Verspaetung)."""
    markt = MARKETS_BY_KEY[markt_key]
    assert zu_frueh_fuer_stichtag(markt, Date(2026, 10, 31), _dt.time(2, 45)) is False


@pytest.mark.parametrize("markt_key", ["us", "de"])
def test_testfall_b_pr53_fall_bleibt_geschuetzt(markt_key):
    """Testfall b: Fr 30.10.2026 08:46 UTC -- zu frueh, wie PR #53 es
    vorsieht. Handelstag UND Laufdatum sind hier identisch (30.10. selbst
    ist der letzte Werktag) -- die Haertung darf dadurch nicht aufgeweicht
    werden."""
    markt = MARKETS_BY_KEY[markt_key]
    assert zu_frueh_fuer_stichtag(markt, Date(2026, 10, 30), _dt.time(8, 46)) is True


@pytest.mark.parametrize("markt_key", ["us", "de"])
def test_testfall_c_regulaerer_abend_lauf_am_30_10(markt_key):
    """Testfall c: Fr 30.10.2026 21:45 UTC (der planmaessige Cron-Zeitpunkt
    selbst) -- nicht zu frueh, fuer beide Maerkte."""
    markt = MARKETS_BY_KEY[markt_key]
    assert zu_frueh_fuer_stichtag(markt, Date(2026, 10, 30), _dt.time(21, 45)) is False


def test_testfall_d_monatswechsel_unter_der_woche_unveraendert():
    """Testfall d: September endet unter der Woche (Mi 30.09.2026), ein
    Lauf rutscht in den Folgemonat (Do 01.10.). due_months() behandelt das
    unveraendert -- September bleibt faellig, Oktober wird NICHT
    vorzeitig als faellig betrachtet (dessen eigener letzter Werktag ist
    erst der 30.10.). Realer Beleg: Lauf 71/72 (01.10.2026) haben
    tatsaechlich den September-Stichtag geschrieben, siehe
    SESSION_HANDOVER.md."""
    assert Date(2026, 9, 30).weekday() == 2  # Mittwoch, zur Kontrolle
    faellig = due_months(Date(2026, 10, 1))
    assert (2026, 9) in faellig
    assert (2026, 10) not in faellig


@pytest.mark.parametrize("markt_key", ["us", "de"])
def test_testfall_e_monatsende_auf_sonntag_samstag_und_sonntag_nicht_zu_frueh(markt_key):
    """Testfall e: Januar 2027 endet auf einen Sonntag (31.01., letzter
    Werktag Fr 29.01.). Sowohl ein Sa- als auch ein So-Lauf nach
    Mitternacht duerfen nicht als "zu frueh" gelten -- der Handelstag
    (Freitag) liegt für beide bereits in der Vergangenheit."""
    markt = MARKETS_BY_KEY[markt_key]
    assert Date(2027, 1, 29).weekday() == 4  # Freitag, zur Kontrolle
    assert Date(2027, 1, 31).weekday() == 6  # Sonntag, zur Kontrolle
    for tag in (Date(2027, 1, 30), Date(2027, 1, 31)):
        assert zu_frueh_fuer_stichtag(markt, tag, _dt.time(2, 45)) is False


def test_testfall_f_nachholender_lauf_am_montag_unveraendert():
    """Testfall f: der nachholende Lauf am Montag, 02.11.2026 -- Oktober
    ist dann ein abgeschlossener Vormonat (nicht mehr der "aktuelle
    Monat"), die Haertung greift fuer ihn gar nicht erst (unabhaengig von
    dieser Aenderung, unveraendertes Verhalten)."""
    assert Date(2026, 11, 2).weekday() == 0  # Montag, zur Kontrolle
    faellig = due_months(Date(2026, 11, 2))
    assert (2026, 10) in faellig
    assert (2026, 11) not in faellig


def test_testfall_g_oktober_stichtag_bleibt_der_30_10_unabhaengig_vom_start():
    """Testfall g: resolve_asof liefert den 30.10.2026 unabhaengig davon,
    ob der Lauf noch am 30.10. oder erst am 31.10. (nach Mitternacht)
    gestartet ist -- diese Funktion war nie Teil des Fundes und bleibt
    unveraendert richtig."""
    index = {
        Date(2026, 10, 29): 4000.0,
        Date(2026, 10, 30): 4010.0,
        # 31.10. fehlt: Samstag, Boerse geschlossen
    }
    assert resolve_asof(index, 2026, 10, Date(2026, 10, 30)) == Date(2026, 10, 30)
    assert resolve_asof(index, 2026, 10, Date(2026, 10, 31)) == Date(2026, 10, 30)


@pytest.mark.parametrize(
    "start,delta,erwartet",
    [
        ((2026, 7), -1, (2026, 6)),
        ((2026, 7), -12, (2025, 7)),
        ((2026, 1), -1, (2025, 12)),
        ((2025, 12), +1, (2026, 1)),
        ((2026, 3), -14, (2025, 1)),
    ],
)
def test_monatsarithmetik(start, delta, erwartet):
    assert shift_month(start[0], start[1], delta) == erwartet


@pytest.mark.parametrize(
    "jahr,monat,erwartet",
    [
        (2026, 7, Date(2026, 7, 31)),
        (2026, 8, Date(2026, 8, 31)),
        (2026, 5, Date(2026, 5, 29)),
        (2026, 1, Date(2026, 1, 30)),
    ],
)
def test_naechster_stichtag_fuer_die_kopfzeile(jahr, monat, erwartet):
    assert last_weekday_of_month(jahr, monat) == erwartet
