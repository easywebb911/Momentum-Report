"""GEWICHTS-FAHRPLAN: Score-Gewichte je Markt und je Ranking-Monat.

Entscheidung Easy, 01.11.2026: USA ab Ranking-Monat 2026-11 100 %
12-1-Momentum / 0 % 52-Wochen-Hoch, bis einschliesslich 2026-10 50/50;
Deutschland immer 50/50. Ausgewaehlt wird rein nach dem Monat des Stichtags
(asof), nie nach dem Lauf-Datum (siehe config.py, "Gewichts-Fahrplan").

Bewiesen wird hier ZUERST die Ziel-Mechanik (US rechnet ab 2026-11 wirklich
100/0, davor 50/50) und DANACH, dass sonst nichts kippt:
  * DE-Ranglisten sind byte-genau dieselben wie vor dem Fahrplan (Hash)
  * US-Ranglisten bis 2026-10 ebenso
  * ein im November NACHGEHOLTES Oktober-Ranking rechnet 50/50
  * die eingefrorenen Dateien Juli-Oktober passen zu ihrem Fahrplan-Eintrag

DIE HASHES UNTEN sind auf dem unveraenderten main (4c2a655, vor diesem
Umbau) mit genau dem Aufbau aus `_rangliste_text` erzeugt worden. Aendert
sich einer, hat sich die DE-Rechnung (oder die US-Rechnung bis 2026-10)
veraendert -- genau das, was dieser Umbau NICHT tun durfte.
"""

from __future__ import annotations

import calendar
import datetime as _dt
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import momentum.config as config
from momentum.config import (
    FAHRPLAN_BEGINN,
    MARKETS,
    MARKETS_BY_KEY,
    WEIGHT_HIGH_52W,
    WEIGHT_MOMENTUM_12_1,
    GewichtsEintrag,
)
from momentum.data import download_prices
from momentum.ranking import RANKING_DIR, build_ranking, dump_ranking, read_ranking
from momentum.run import process_market
from momentum.universe import load_universe
from tests.conftest import _INDEX, _RAW, make_downloader, write_universe

Date = _dt.date

# sha256 von dump_ranking(...) auf main 4c2a655 (vor dem Fahrplan).
HASH_VOR_DEM_UMBAU = {
    ("de", 2026, 7): "32ab2733b80278113956c49a1076f6066e2a9d73c9bdc0c9a13be07455b38b80",
    ("de", 2026, 10): "34df89eb2fbaa98208688a260bc922b3aadfa581e907fe5c841c1286a571a789",
    ("de", 2026, 11): "3325619be66b3601bd58cf5778f4278c46df611cc956f39116ece3b137f26634",
    ("de", 2026, 12): "a4f6204b83cc73dcde315dfeba0beb4728e4817e3687d15fd7af53100ee4b0d5",
    ("us", 2026, 7): "cd51ca6d97fd8826cd6e75449b49efe85063b50198d9ac3e28774c51d2b0cd9c",
    ("us", 2026, 10): "6084c9ce16b4addbc2218b82b61d3de8fd2f2cd53cf789f7b81b9911391102e7",
}


# ------------------------------------------------------------ Aufbau


def _handelstag(tag: Date) -> Date:
    while tag.weekday() >= 5:
        tag -= _dt.timedelta(days=1)
    return tag


def _monatsenden(jahr: int, monat: int) -> list[Date]:
    """Die 13 Monatsend-Handelstage bis einschliesslich jahr-monat."""
    out = []
    y, m = jahr, monat
    for _ in range(13):
        out.append(_handelstag(Date(y, m, calendar.monthrange(y, m)[1])))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def _serien(jahr: int, monat: int, index_ticker: str):
    """Das Kunst-Beispiel aus conftest, auf den Stichtag jahr-monat verschoben."""
    enden = _monatsenden(jahr, monat)
    serien = {t: dict(zip(enden, werte)) for t, werte in _RAW.items()}
    serien[index_ticker] = dict(zip(enden, _INDEX))
    return serien, enden


def _ranking(key: str, jahr: int, monat: int, tmp_path: Path) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    uni = write_universe(tmp_path / "u.txt", list(_RAW))
    markt = replace(MARKETS_BY_KEY[key], universe_file=str(uni))
    universum = load_universe(uni)
    serien, enden = _serien(jahr, monat, markt.index_ticker)
    index = serien.pop(markt.index_ticker)
    bundle = download_prices(
        list(universum.tickers),
        enden[0] - _dt.timedelta(days=200),
        enden[-1],
        downloader=make_downloader(serien),
    )
    return build_ranking(markt, universum, bundle, index, enden[-1])


def _rangliste_text(key: str, jahr: int, monat: int, tmp_path: Path) -> str:
    return dump_ranking(_ranking(key, jahr, monat, tmp_path))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --------------------------------------------- 1. Ziel-Mechanik (zuerst)


def test_us_oktober_2026_rechnet_50_50(tmp_path):
    ranking = _ranking("us", 2026, 10, tmp_path)
    assert ranking["ranking_monat"] == "2026-10"
    assert ranking["methode"]["gewicht_momentum_12_1"] == 0.5
    assert ranking["methode"]["gewicht_high_52w"] == 0.5
    for row in ranking["rangliste"]:
        soll = 100.0 * (0.5 * row["perzentil_momentum"] + 0.5 * row["perzentil_high_52w"])
        assert row["score"] == pytest.approx(soll, abs=1e-6), row["ticker"]


def test_us_november_2026_rechnet_100_0(tmp_path):
    ranking = _ranking("us", 2026, 11, tmp_path)
    assert ranking["ranking_monat"] == "2026-11"
    assert ranking["methode"]["gewicht_momentum_12_1"] == 1.0
    assert ranking["methode"]["gewicht_high_52w"] == 0.0
    for row in ranking["rangliste"]:
        # Score = Momentum-Perzentil x 100, die 52W-Naehe zaehlt nicht mit.
        assert row["score"] == round(100.0 * row["perzentil_momentum"], 6), row["ticker"]
        # Bei 100/0 ist der Gesamtrang genau der 12-1-Rang.
        assert row["rang"] == row["rank_12_1"], row["ticker"]


def test_der_wechsel_veraendert_die_us_rangfolge_wirklich(tmp_path):
    """Nicht nur "nichts kaputt": auf denselben (verschobenen) Kursen ergibt
    der November eine ANDERE Reihenfolge als der Oktober -- die neue Regel
    wirkt also tatsaechlich."""
    okt = _ranking("us", 2026, 10, tmp_path / "okt")
    nov = _ranking("us", 2026, 11, tmp_path / "nov")
    # Gleiche Kennzahlen (dieselben Kurse, nur verschoben) ...
    assert [r["momentum_12_1"] for r in sorted(okt["rangliste"], key=lambda r: r["ticker"])] == [
        r["momentum_12_1"] for r in sorted(nov["rangliste"], key=lambda r: r["ticker"])
    ]
    # ... aber andere Rangfolge.
    assert okt["top"] != nov["top"]
    # November: absteigend nach 12-1-Momentum (Gleichstand: Ticker A->Z
    # ueber das Perzentil, siehe percentile_ranks).
    nach_momentum = sorted(
        nov["rangliste"], key=lambda r: (-r["perzentil_momentum"], r["ticker"])
    )
    assert nov["top"] == [r["ticker"] for r in nach_momentum]


def test_us_dezember_2026_bleibt_bei_100_0(tmp_path):
    ranking = _ranking("us", 2026, 12, tmp_path)
    assert ranking["methode"]["gewicht_momentum_12_1"] == 1.0
    assert ranking["methode"]["gewicht_high_52w"] == 0.0


@pytest.mark.parametrize(
    "jahr,monat,soll",
    [
        (2026, 7, (0.5, 0.5)),
        (2026, 10, (0.5, 0.5)),
        (2026, 11, (1.0, 0.0)),
        (2026, 12, (1.0, 0.0)),
        (2027, 1, (1.0, 0.0)),
        (2030, 6, (1.0, 0.0)),
    ],
)
def test_us_fahrplan_tabelle(jahr, monat, soll):
    assert MARKETS_BY_KEY["us"].gewichte_fuer(jahr, monat) == soll


@pytest.mark.parametrize("jahr,monat", [(2026, 7), (2026, 10), (2026, 11), (2027, 1), (2030, 6)])
def test_de_fahrplan_ist_immer_50_50_mit_denselben_konstanten(jahr, monat):
    w_mom, w_high = MARKETS_BY_KEY["de"].gewichte_fuer(jahr, monat)
    # Dieselben Objekte wie die Standard-Konstanten -- nicht nur gleich viel.
    assert w_mom is WEIGHT_MOMENTUM_12_1
    assert w_high is WEIGHT_HIGH_52W


def test_de_fahrplan_hat_genau_einen_eintrag():
    assert MARKETS_BY_KEY["de"].gewichts_fahrplan == (
        GewichtsEintrag(FAHRPLAN_BEGINN, WEIGHT_MOMENTUM_12_1, WEIGHT_HIGH_52W),
    )


def test_us_fahrplan_genau_wie_entschieden():
    assert MARKETS_BY_KEY["us"].gewichts_fahrplan == (
        GewichtsEintrag(FAHRPLAN_BEGINN, WEIGHT_MOMENTUM_12_1, WEIGHT_HIGH_52W),
        GewichtsEintrag((2026, 11), 1.0, 0.0),
    )


def test_keine_zwischenwerte_im_fahrplan():
    """Entscheidung 01.11.2026: nur 50/50 oder 100/0, keine Parametersuche."""
    erlaubt = {(0.5, 0.5), (1.0, 0.0)}
    for markt in MARKETS:
        for eintrag in markt.gewichts_fahrplan:
            assert (eintrag.momentum_12_1, eintrag.high_52w) in erlaubt, markt.key


# --------------------------------------------- 2. Nichts sonst kippt


@pytest.mark.parametrize("key,jahr,monat", sorted(HASH_VOR_DEM_UMBAU))
def test_rangliste_byte_genau_wie_vor_dem_umbau(key, jahr, monat, tmp_path):
    ist = _sha(_rangliste_text(key, jahr, monat, tmp_path))
    assert ist == HASH_VOR_DEM_UMBAU[(key, jahr, monat)], (key, jahr, monat)


def test_zweimal_rechnen_ist_identisch(tmp_path):
    for key in ("us", "de"):
        for monat in (10, 11):
            a = _rangliste_text(key, 2026, monat, tmp_path / f"{key}{monat}a")
            b = _rangliste_text(key, 2026, monat, tmp_path / f"{key}{monat}b")
            assert a == b, (key, monat)


def test_nachgeholtes_oktober_ranking_im_november_rechnet_50_50(tmp_path):
    """Lauf am 03.11.2026, Oktober-Ranking fehlt noch -> wird nachgeholt.
    Massgeblich ist der Stichtag (30.10.), nicht das Lauf-Datum."""
    uni = write_universe(tmp_path / "universe_us.txt", list(_RAW))
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(uni))
    serien, enden = _serien(2026, 10, markt.index_ticker)
    wurzel = tmp_path / "rankings"
    wurzel.mkdir()
    auswertung = tmp_path / "evaluation"
    auswertung.mkdir()
    # Juli-September gelten als vorhanden; der September-Rueckblick auch,
    # damit der Lauf hier wirklich nur den Oktober nachholt.
    for monat in (7, 8, 9):
        (wurzel / f"us_2026-{monat:02d}.json").write_text("{}\n", encoding="utf-8")
    (auswertung / "us_2026-09.json").write_text("{}\n", encoding="utf-8")

    _view, neu, _status = process_market(
        markt,
        Date(2026, 11, 3),
        downloader=make_downloader(serien),
        ranking_root=wurzel,
        data_root=tmp_path / "data",
        evaluation_root=auswertung,
        kursvergleich_aktiv=False,
    )
    assert neu is not None
    assert neu["ranking_monat"] == "2026-10"
    assert neu["stichtag"] == "2026-10-30"
    assert neu["methode"]["gewicht_momentum_12_1"] == 0.5
    assert neu["methode"]["gewicht_high_52w"] == 0.5
    geschrieben = read_ranking(wurzel / "us_2026-10.json")
    assert geschrieben["methode"] == neu["methode"]


def test_eingefrorene_rankings_passen_zu_ihrem_fahrplan_eintrag():
    """Jede eingefrorene Datei traegt die Gewichte, die der Fahrplan fuer
    ihren Monat nennt -- fuer Juli-Oktober also 50/50 in BEIDEN Maerkten.
    Gelesen wird nur; geschrieben wird hier nichts."""
    dateien = sorted(Path(RANKING_DIR).glob("*_*.json"))
    assert dateien, "keine eingefrorenen Rankings gefunden"
    for datei in dateien:
        ranking = json.loads(datei.read_text(encoding="utf-8"))
        jahr, monat = (int(x) for x in ranking["ranking_monat"].split("-"))
        soll = MARKETS_BY_KEY[ranking["markt"]].gewichte_fuer(jahr, monat)
        ist = (
            ranking["methode"]["gewicht_momentum_12_1"],
            ranking["methode"]["gewicht_high_52w"],
        )
        assert ist == soll, datei.name
        if (jahr, monat) <= (2026, 10):
            assert ist == (0.5, 0.5), datei.name


def test_auswahl_haengt_nicht_an_der_uhr(monkeypatch):
    """gewichte_fuer liest weder Uhr noch Datum: eine verbogene Uhr aendert nichts."""

    class KaputteUhr(_dt.date):
        @classmethod
        def today(cls):
            raise AssertionError("gewichte_fuer darf das heutige Datum nicht lesen")

    monkeypatch.setattr(config._dt, "date", KaputteUhr)
    assert MARKETS_BY_KEY["us"].gewichte_fuer(2026, 10) == (0.5, 0.5)
    assert MARKETS_BY_KEY["us"].gewichte_fuer(2026, 11) == (1.0, 0.0)


# --------------------------------------------- 3. Pruefung beim Import


def _markt_mit(plan):
    return replace(MARKETS_BY_KEY["us"], gewichts_fahrplan=plan)


@pytest.mark.parametrize(
    "plan,meldung",
    [
        ((), "leer"),
        ((GewichtsEintrag((2026, 7), 0.5, 0.5),), "erster Fahrplan-Eintrag"),
        (
            (GewichtsEintrag(FAHRPLAN_BEGINN, 0.5, 0.5), GewichtsEintrag(FAHRPLAN_BEGINN, 1.0, 0.0)),
            "streng aufsteigend",
        ),
        (
            (GewichtsEintrag(FAHRPLAN_BEGINN, 0.5, 0.5), GewichtsEintrag((2026, 13), 1.0, 0.0)),
            "ungueltiger Monat",
        ),
        ((GewichtsEintrag(FAHRPLAN_BEGINN, 0.7, 0.5),), "summieren"),
        ((GewichtsEintrag(FAHRPLAN_BEGINN, 1.5, -0.5),), "ausserhalb"),
    ],
)
def test_kaputter_fahrplan_bricht_beim_import_ab(monkeypatch, plan, meldung):
    monkeypatch.setattr(config, "MARKETS", (_markt_mit(plan),))
    with pytest.raises(RuntimeError, match=meldung):
        config._check_weights_are_backed()


def test_gewicht_null_ist_zulaessig(monkeypatch):
    plan = (GewichtsEintrag(FAHRPLAN_BEGINN, 1.0, 0.0),)
    monkeypatch.setattr(config, "MARKETS", (_markt_mit(plan),))
    config._check_weights_are_backed()  # kein Fehler


def test_komponente_ohne_beleg_bricht_ab(monkeypatch):
    monkeypatch.setattr(config, "SCORE_COMPONENT_SOURCES", {"momentum_12_1": ("momentum_12_1",)})
    plan = (GewichtsEintrag(FAHRPLAN_BEGINN, 0.5, 0.5),)
    monkeypatch.setattr(config, "MARKETS", (_markt_mit(plan),))
    with pytest.raises(RuntimeError, match="ohne Primaerquelle"):
        config._check_weights_are_backed()
    # Mit Gewicht 0 braucht die belegfreie Komponente fuer DIESES Paar
    # keinen Beleg (die Standard-Konstanten 50/50 brauchen ihn weiterhin).
    config._pruefe_gewichtspaar("Test", 1.0, 0.0)  # kein Fehler
    with pytest.raises(RuntimeError, match="ohne Primaerquelle: high_52w"):
        config._pruefe_gewichtspaar("Test", 0.5, 0.5)
