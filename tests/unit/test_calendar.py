"""Stichtags-Mechanik: wann ein Ranking faellig ist und auf welchen Tag.

Der Marktindex dient als Handelskalender — deshalb braucht das Werkzeug
keine gepflegte Feiertagsliste und kann auch keinen Feiertag "verpassen".
"""

from __future__ import annotations

import datetime as _dt

import pytest

from momentum.ranking import (
    RankingNotPossible,
    due_months,
    is_last_weekday_of_month,
    resolve_asof,
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
