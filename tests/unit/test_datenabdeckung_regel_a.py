"""Pruefung A (Kursabruf) mit ECHTEN Lauf-Staenden.

Seit der Baseline-Auswertung 26.10.-12.11.2026 zaehlt Pruefung A die
letzten MINDEST_BEOBACHTUNGEN Lauf-Staende statt eines 24-Std.-Fensters
(siehe "REGEL A" im Modul-Docstring). Die Werte unten sind wortgleich aus
data/status.json der Laeufe 96-104 abgeschrieben (Commit, Commit-Zeit,
je Markt: angefragt, geliefert, zeilen_verworfen_nicht_endlich), damit
dieser Test ohne Git-Historie laeuft. Bewiesen wird:

  * echt (alle 5 von 5 Titeln geliefert, aber jeweils der juengste Tag
    verworfen -- die bekannte Yahoo-Verzoegerung): KEINE Warnung;
  * "0 Kurse geliefert" an ZWEI aufeinanderfolgenden Laeufen eingesetzt:
    Warnung, und der Push ist faellig (Uebergang);
  * "0 Kurse geliefert" an nur EINEM Lauf: noch keine Warnung;
  * die Wochenend-Luecke (Fr-Lauf 07.11. -> Di-Lauf 10.11.) stoert nicht.
"""

from __future__ import annotations

import copy
import datetime as _dt

import pytest

import momentum.datenabdeckung_waechter as w

UTC = _dt.timezone.utc

# (Commit-Zeit, Commit, {markt: (angefragt, geliefert, verworfen)})
ECHTE_LAEUFE = [
    ("2026-10-31T09:16:31+00:00", "8e29c5d", {"us": (503, 503, 2071), "de": (102, 102, 227)}),
    ("2026-11-03T03:03:41+00:00", "32221f7", {"us": (5, 5, 0), "de": (5, 5, 5)}),
    ("2026-11-04T01:39:12+00:00", "ec8ba91", {"us": (5, 5, 5), "de": (5, 5, 5)}),
    ("2026-11-05T01:47:41+00:00", "d6618ef", {"us": (5, 5, 5), "de": (5, 5, 5)}),
    ("2026-11-06T01:47:51+00:00", "329fbf2", {"us": (5, 5, 5), "de": (5, 5, 5)}),
    ("2026-11-07T01:11:52+00:00", "fc2026a", {"us": (5, 5, 5), "de": (5, 5, 5)}),
    ("2026-11-10T03:48:06+00:00", "969b3fc", {"us": (5, 5, 0), "de": (5, 5, 5)}),
    ("2026-11-11T01:28:46+00:00", "904cfa8", {"us": (5, 5, 5), "de": (5, 5, 5)}),
    ("2026-11-12T02:31:03+00:00", "b722d55", {"us": (5, 5, 5), "de": (5, 5, 5)}),
]

# Startzeiten der echten Waechter-Laeufe 9-17 (Actions-Uebersicht) plus
# 12.11. 14:00 (typische Startzeit, heutiger Lauf nicht abgerufen).
WAECHTER_LAEUFE = [
    "2026-11-03T14:35:31", "2026-11-04T14:49:33", "2026-11-05T14:54:10",
    "2026-11-06T14:32:25", "2026-11-07T13:27:42", "2026-11-08T13:47:12",
    "2026-11-09T16:46:51", "2026-11-10T15:10:40", "2026-11-11T14:40:04",
    "2026-11-12T14:00:00",
]


def _zeit(s: str) -> _dt.datetime:
    t = _dt.datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _historie(null_bei: tuple[str, ...] = ()) -> list[tuple[_dt.datetime, dict]]:
    """Echte Lauf-Staende; fuer die Commits in `null_bei` wird in BEIDEN
    Maerkten "geliefert" auf 0 gesetzt (simulierter Totalausfall)."""
    out = []
    for zeit, commit, maerkte in ECHTE_LAEUFE:
        eintraege = []
        for markt, (angefragt, geliefert, verworfen) in maerkte.items():
            daten = {
                "angefragt": angefragt,
                "geliefert": 0 if commit in null_bei else geliefert,
                "zeilen_verworfen_nicht_endlich": verworfen,
            }
            eintraege.append({"markt": markt, "daten": daten})
        out.append((_zeit(zeit), {"maerkte": copy.deepcopy(eintraege)}))
    return out


def _datenlage(historie):
    return w.Datenlage(
        status_historie=historie,
        ticker_meta_historie={
            "us": [(_zeit("2026-08-18T00:00:00"), {"AAA": {"sektor": "X"}})],
            "de": [(_zeit("2026-08-18T00:00:00"), {"BBB.DE": {"sektor": "Y"}})],
        },
        universum_stand={"us": _dt.date(2026, 8, 3), "de": _dt.date(2026, 8, 3)},
    )


@pytest.mark.parametrize("start", WAECHTER_LAEUFE)
def test_echte_laeufe_keine_meldung_auch_bei_yahoo_verzoegerung(start):
    """In fast allen echten Laeufen wurde der juengste Tag verworfen
    (verworfen = 5), geliefert waren trotzdem 5 von 5 Titeln -> gesund."""
    bezug = _zeit(start)
    historie = _historie()
    for markt in ("us", "de"):
        assert w.kursabruf_warnung_zum_zeitpunkt(bezug, historie, markt) is False
    assert w.faellige_bloecke(w.ermittle_signale(_datenlage(historie), bezug)) == []


def test_die_yahoo_verzoegerung_ist_in_den_echten_daten_enthalten():
    """Gegenprobe, dass der Test oben wirklich den Verzoegerungs-Fall sieht."""
    verworfen = [m[2] for _, _, maerkte in ECHTE_LAEUFE for m in maerkte.values()]
    assert verworfen.count(5) >= 10


def test_zwei_aufeinanderfolgende_laeufe_ohne_kurse_melden():
    historie = _historie(null_bei=("904cfa8", "b722d55"))
    bezug = _zeit("2026-11-12T14:00:00")
    for markt in ("us", "de"):
        assert w.kursabruf_warnung_zum_zeitpunkt(bezug, historie, markt) is True
    bloecke = w.faellige_bloecke(w.ermittle_signale(_datenlage(historie), bezug))
    namen = [n for n, _ in bloecke]
    assert namen == ["Kursabruf US", "Kursabruf DE"]
    assert "in den letzten 2 Laeufen praktisch keine Kursdaten" in bloecke[0][1]
    # Am Vortag (nach nur einem leeren Lauf) war es noch keine Warnung ->
    # der heutige Push ist der Uebergang.
    vortag = _zeit("2026-11-11T14:40:04")
    assert w.kursabruf_warnung_zum_zeitpunkt(vortag, historie, "us") is False


def test_nur_ein_lauf_ohne_kurse_meldet_noch_nicht():
    historie = _historie(null_bei=("b722d55",))
    bezug = _zeit("2026-11-12T14:00:00")
    for markt in ("us", "de"):
        assert w.kursabruf_warnung_zum_zeitpunkt(bezug, historie, markt) is False
    assert w.faellige_bloecke(w.ermittle_signale(_datenlage(historie), bezug)) == []


def test_wochenend_luecke_stoert_nicht():
    """Fr-Lauf (Sa 07.11. 01:11) und Di-Lauf (10.11. 03:48) liegen ueber
    74 Std. auseinander -- mit dem alten 24-Std.-Fenster nicht auswertbar,
    jetzt schon."""
    historie = _historie(null_bei=("fc2026a", "969b3fc"))
    for start in ("2026-11-08T13:47:12", "2026-11-09T16:46:51"):
        # Sonntag/Montag: letzte zwei Laeufe sind 06.11. (gut) und 07.11. (0)
        assert w.kursabruf_warnung_zum_zeitpunkt(_zeit(start), historie, "us") is False
    assert w.kursabruf_warnung_zum_zeitpunkt(_zeit("2026-11-10T15:10:40"), historie, "us") is True


def test_auswahl_haengt_nur_an_der_reihenfolge_nicht_an_der_uhrzeit():
    """Jeder Bezug NACH dem letzten Lauf liefert dasselbe Ergebnis --
    die Uhrzeit des Waechter-Laufs spielt keine Rolle."""
    historie = _historie(null_bei=("904cfa8", "b722d55"))
    ergebnisse = {
        w.kursabruf_warnung_zum_zeitpunkt(_zeit(s), historie, "de")
        for s in ("2026-11-12T03:00:00", "2026-11-12T14:00:00", "2026-11-12T23:59:59",
                  "2026-11-14T10:00:00", "2026-12-24T10:00:00")
    }
    assert ergebnisse == {True}
