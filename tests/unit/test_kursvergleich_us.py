"""Das US-Vergleichsgatter (Stufe 2b) — Geschwister von test_kursvergleich.py.

Die fuenf Zusagen, die hier festgehalten werden:

  1. Alle drei Verdikt-Stufen greifen, wie bei DE: durchgewinkt, VERWEIGERT,
     entfallen.
  2. Ein Aktien-Split wird NICHT als Abweichler gezaehlt, wenn Verhaeltnis
     UND Kalender-Beleg zusammenpassen ("MNST-Muster", Mess-Tag 2).
  3. Der Split-Filter ist KEIN Schlupfloch: ein manipulierter Kurs, der nur
     zufaellig wie ein Split-Verhaeltnis aussieht, aber keinen
     Kalender-Beleg hat, zaehlt weiterhin als Abweichler.
  4. Die Ziel-Mechanik: ein manipulierter Kurs OHNE Split-Beleg stoppt den
     Stichtags-Lauf wirklich, bevor irgendein Ranking geschrieben ist.
  5. Die Zweitquelle speist NIEMALS eine Ranking-Zahl -- auch nicht die des
     ANDEREN Marktes: der DE-Lauf bleibt Zeichen fuer Zeichen gleich, egal
     was das US-Gatter sagt.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import build_universe as bu  # noqa: E402

from momentum import kursvergleich_us as kv_us  # noqa: E402
from momentum import run as run_modul  # noqa: E402
from momentum.config import MARKETS_BY_KEY  # noqa: E402
from momentum.ishares import us_symbol_zu_yahoo  # noqa: E402
from momentum.ranking import RankingNotPossible  # noqa: E402
from tests.conftest import (  # noqa: E402
    MONTH_ENDS,
    index_series,
    make_downloader,
    sample_series,
    write_universe,
)

Date = _dt.date
STICHTAG = Date(2026, 7, 31)
TICKER = ["AAA", "BBB", "CCC", "DDD", "EEE"]
# US-Symbole tragen (anders als Xetra-Kuerzel) keine Ziffern und brauchen
# keine Uebersetzung -- dieselben Buchstaben-Ticker wie im Kunst-Beispiel
# sind hier bereits gueltige Yahoo-Ticker.
KURSE_AM_STICHTAG = {
    "AAA": 160.00, "BBB": 125.00, "CCC": 90.00, "DDD": 250.00, "EEE": 75.00,
}

KOPFZEILE = (
    "Ticker,Name,Sektor,Anlageklasse,Marktwert,Gewichtung (%),"
    "Nominalwert,Nominale,Kurs,Standort,Börse,Marktwährung"
)


def bestandsdatei(kurse: dict[str, float], *, stand: str = "31.Juli2026",
                  waehrung: str = "USD", kurs_text: dict[str, str] | None = None) -> str:
    """Eine SXR8/IUSA-Bestandsliste im echten Format -- Geschwister von
    test_kursvergleich.bestandsdatei, nur mit US-Symbolen und USD."""
    zeilen = [KOPFZEILE]
    for ticker, kurs in kurse.items():
        text = (kurs_text or {}).get(ticker, f"{kurs:.2f}")
        zeilen.append(
            f"{ticker},{ticker} Inc,Information Technology,Equity,"
            f"1234567.89,1.23,10000,10000,{text},USA,NASDAQ,{waehrung}"
        )
    return f'Fondsposition per,"{stand}"\n \n' + "\n".join(zeilen) + "\n"


def befund_aus(kurse: dict[str, float], **kw):
    """Der ECHTE Parser, mit ausgesetztem Anzahl-Gatter (5 Kunst-Titel)."""
    return bu.parse_ishares_holdings(
        bestandsdatei(kurse, **kw), "SXR8", heute=Date(2026, 8, 3),
        erwartete_anzahl=(0, 1000), ticker_uebersetzer=us_symbol_zu_yahoo,
    )


def roh_kurse(am: Date = STICHTAG) -> dict[str, dict[Date, float]]:
    """Was `PriceBundle.close` liefern wuerde -- Yahoo-Ticker, roher Kurs."""
    return {t: {am: k} for t, k in KURSE_AM_STICHTAG.items()}


def keine_splits(_ticker: str) -> dict:
    return {}


# ==========================================================================
# Stufe (a): durchgewinkt
# ==========================================================================


def test_uebereinstimmende_kurse_sind_ein_ok():
    vergleich = kv_us.vergleiche(
        befund_aus(KURSE_AM_STICHTAG), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert vergleich.verdikt == "ok"
    assert len(vergleich.verglichen) == 5
    assert vergleich.abweichler == ()
    assert vergleich.split_erkannt == ()
    assert vergleich.stichtag == STICHTAG
    assert vergleich.fonds == "SXR8"


def test_bis_zum_zulass_laeuft_es_normal_weiter():
    verbogen = dict(KURSE_AM_STICHTAG)
    for ticker in ("AAA", "BBB", "CCC"):
        verbogen[ticker] *= 1.01  # deutlich ueber 0,25 %, aber kein Split-Verhaeltnis
    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert vergleich.verdikt == "ok"
    assert len(vergleich.abweichler) == kv_us.ZULASS_ABWEICHLER == 3
    protokoll = "\n".join(vergleich.protokoll())
    for ticker in ("AAA", "BBB", "CCC"):
        assert ticker in protokoll


def test_knapp_innerhalb_der_toleranz_ist_kein_abweichler():
    knapp = {t: k * (1 + kv_us.TOLERANZ * 0.9) for t, k in KURSE_AM_STICHTAG.items()}
    vergleich = kv_us.vergleiche(
        befund_aus(knapp), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert vergleich.abweichler == ()


def test_knapp_ausserhalb_der_toleranz_ist_einer():
    daneben = dict(KURSE_AM_STICHTAG)
    daneben["AAA"] = KURSE_AM_STICHTAG["AAA"] * (1 + kv_us.TOLERANZ * 1.1)
    vergleich = kv_us.vergleiche(
        befund_aus(daneben), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert [a.ticker for a in vergleich.abweichler] == ["AAA"]


# ==========================================================================
# Stufe (b): VERWEIGERT
# ==========================================================================


def test_zu_viele_abweichler_verweigern():
    verbogen = {t: k * 1.05 for t, k in KURSE_AM_STICHTAG.items()}
    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert vergleich.verdikt == "verweigert"
    assert vergleich.verweigert is True
    assert len(vergleich.abweichler) == 5


def test_der_abbruchtext_nennt_jeden_titel_mit_beiden_kursen():
    verbogen = {t: k * 1.05 for t, k in KURSE_AM_STICHTAG.items()}
    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    text = kv_us.abbruchtext(vergleich, "us")
    assert "VERWEIGERT" in text
    assert "KEIN Ranking geschrieben" in text
    for ticker in KURSE_AM_STICHTAG:
        assert ticker in text
    assert "bleibt offen" in text


# ==========================================================================
# Stufe (c): entfallen — nie still
# ==========================================================================


def test_ohne_kurs_spalte_entfaellt_der_vergleich_mit_grund():
    ohne = befund_aus(KURSE_AM_STICHTAG, kurs_text={t: "-" for t in KURSE_AM_STICHTAG})
    vergleich = kv_us.vergleiche(ohne, "SXR8", roh_kurse(), splits_oeffner=keine_splits)
    assert vergleich.verdikt == "entfallen"
    assert "keine lesbare Kurs-Spalte" in vergleich.grund


def test_fremde_marktwaehrung_wird_nicht_verglichen_und_gilt_nicht_als_bruch():
    befund = befund_aus(KURSE_AM_STICHTAG, waehrung="EUR")
    vergleich = kv_us.vergleiche(befund, "SXR8", roh_kurse(), splits_oeffner=keine_splits)
    assert vergleich.verdikt == "entfallen"
    assert all("EUR" in eintrag for eintrag in vergleich.ohne_vergleich)


def test_das_universum_grenzt_ein():
    vergleich = kv_us.vergleiche(
        befund_aus(KURSE_AM_STICHTAG), "SXR8", roh_kurse(),
        universum={"AAA", "BBB"}, splits_oeffner=keine_splits,
    )
    assert set(vergleich.verglichen) == {"AAA", "BBB"}


# ==========================================================================
# Der Split-Filter — die eigentliche Neuerung dieser Stufe
# ==========================================================================


def test_ein_echter_split_zaehlt_nicht_als_abweichler():
    """Das MNST-Muster (Mess-Tag 2, 11.08.2026): der Fonds hat einen 4:1-
    Split noch nicht nachvollzogen, die Kursquelle schon. Verhaeltnis UND
    Kalender-Beleg passen zusammen -- kein Befund, kein Abbruch."""
    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] = KURSE_AM_STICHTAG["AAA"] * 4  # Fonds zeigt den Alt-Kurs (vor 4:1-Split)

    def splits(ticker):
        return {"AAA": {STICHTAG: 4.0}}.get(ticker, {})

    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=splits,
    )
    assert vergleich.verdikt == "ok"
    assert vergleich.abweichler == ()
    assert [s.ticker for s in vergleich.split_erkannt] == ["AAA"]
    assert vergleich.split_erkannt[0].verhaeltnis == 4.0
    assert vergleich.split_erkannt[0].split_datum == STICHTAG
    protokoll = "\n".join(vergleich.protokoll())
    assert "SPLIT ERKANNT" in protokoll and "AAA" in protokoll


def test_split_ausserhalb_des_zeitfensters_zaehlt_nicht():
    """Ein Split-Kalendereintrag, der weit vom Stichtag entfernt liegt, ist
    kein Beleg FUER DIESE Abweichung."""
    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] = KURSE_AM_STICHTAG["AAA"] * 4

    def splits(ticker):
        weit_weg = STICHTAG - _dt.timedelta(days=90)
        return {"AAA": {weit_weg: 4.0}}.get(ticker, {})

    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=splits,
    )
    # Ein einzelner Abweichler bleibt unter dem Zulass "ok" -- der Punkt
    # hier ist, DASS er als Abweichler zaehlt, nicht das Gesamtverdikt.
    assert vergleich.verdikt == "ok"
    assert [a.ticker for a in vergleich.abweichler] == ["AAA"]
    assert vergleich.split_erkannt == ()


def test_der_split_filter_ist_kein_schlupfloch_fuer_echte_fehler():
    """DIE Selbstpruefung aus dem Auftrag: ein manipulierter Kurs, der
    zufaellig ein Split-Verhaeltnis trifft, aber KEINEN Kalender-Beleg hat,
    zaehlt weiterhin als Abweichler -- der Split-Filter darf so etwas nicht
    durchwinken."""
    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] = KURSE_AM_STICHTAG["AAA"] * 4  # passendes Verhaeltnis ...

    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(),
        splits_oeffner=keine_splits,  # ... aber KEIN Kalender-Beleg
    )
    assert vergleich.split_erkannt == ()
    assert [a.ticker for a in vergleich.abweichler] == ["AAA"]
    assert vergleich.verdikt == "ok"  # ein einzelner Abweichler bleibt unter dem Zulass


def test_ein_passendes_verhaeltnis_ohne_beleg_kann_den_lauf_stoppen():
    """Dieselbe Aussage, aber ueber den Zulass hinaus: der Split-Filter
    verhindert den Abbruch NICHT, wenn der Kalender-Beleg fehlt."""
    verbogen = {t: k * 4 for t, k in KURSE_AM_STICHTAG.items()}  # alle 5 "wie ein Split"
    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=keine_splits,
    )
    assert vergleich.verdikt == "verweigert"
    assert len(vergleich.abweichler) == 5
    assert vergleich.split_erkannt == ()


def test_ein_fehlschlag_des_split_kalenders_ist_fail_soft_nicht_still():
    """Ein Netzfehler beim Split-Kalender ist kein Beleg -- fail-soft in
    Richtung "normaler Abweichler", nie in Richtung "wird durchgewunken"."""
    def kaputt(_ticker):
        raise ConnectionError("kein Netz")

    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] = KURSE_AM_STICHTAG["AAA"] * 4
    vergleich = kv_us.vergleiche(
        befund_aus(verbogen), "SXR8", roh_kurse(), splits_oeffner=kaputt,
    )
    assert vergleich.split_erkannt == ()
    assert [a.ticker for a in vergleich.abweichler] == ["AAA"]


# ==========================================================================
# Der Lauf: greift das Gatter wirklich, und laesst es DE unberuehrt?
# ==========================================================================


@pytest.fixture
def welt(tmp_path, monkeypatch):
    """Dasselbe Miniatur-Projekt wie in test_kursvergleich.py, aber mit
    US-Bestandslisten statt Xetra-Kuerzeln: hier existiert der Vergleich
    fuer BEIDE Maerkte."""
    (tmp_path / "universe").mkdir()
    (tmp_path / "docs").mkdir()
    for datei in ("style.css", "app.js"):
        (tmp_path / "docs" / datei).write_text("/* Platzhalter */", encoding="utf-8")

    maerkte = []
    for key in ("us", "de"):
        pfad = write_universe(
            tmp_path / "universe" / f"universe_{key}.txt", TICKER, label=f"Test {key.upper()}"
        )
        maerkte.append(replace(MARKETS_BY_KEY[key], universe_file=str(pfad)))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_modul, "MARKETS", tuple(maerkte))
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)
    # Die Kunst-Welt hat 5 Titel, das echte ANZAHL-Gatter erwartet 480-520.
    monkeypatch.setattr(run_modul, "ANZAHL_ERWARTET_US", (0, 1000))

    serien = sample_series()
    serien["^SP500TR"] = index_series()
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}
    serien["^GDAXI"] = index_series()
    return tmp_path, make_downloader(serien)


def oeffner_us_mit(kurse: dict[str, float], **kw):
    """Liefert die US-Bestandsdatei fuer SXR8/IUSA, sonst (DE) eine leere
    Zeile -- in diesen Tests interessiert nur der US-Vergleich, und der
    DE-Vergleich soll dabei fail-soft entfallen, nicht mitreden."""
    inhalt = bestandsdatei(kurse, **kw)

    def oeffner(quelle):
        if quelle.index_name in ("SXR8", "IUSA"):
            return inhalt
        raise ConnectionError("DE-Bestandslisten sind in diesem Test nicht geruestet")

    return oeffner


def test_der_lauf_laeuft_normal_wenn_die_us_kurse_zusammenpassen(welt):
    tmp_path, downloader = welt
    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        bestand_oeffner=oeffner_us_mit(KURSE_AM_STICHTAG),
        splits_oeffner=keine_splits,
    )
    assert code == 0
    us = json.loads((tmp_path / "data/rankings/us_2026-07.json").read_text(encoding="utf-8"))
    assert us["kursvergleich"]["verdikt"] == "ok"
    assert us["kursvergleich"]["verglichen"] == 5
    assert us["kursvergleich"]["abweichler"] == []
    assert us["kursvergleich"]["fonds"] == "SXR8"


def test_ein_manipulierter_kurs_ohne_split_beleg_stoppt_den_lauf_wirklich(welt):
    """DIE ZIEL-MECHANIK aus dem Auftrag: vier von fuenf Titeln weit
    daneben, kein Split-Beleg -- der Lauf muss abbrechen, BEVOR ein
    US-Ranking entstanden ist."""
    tmp_path, downloader = welt
    verbogen = dict(KURSE_AM_STICHTAG)
    for ticker in ("AAA", "BBB", "CCC", "DDD"):
        verbogen[ticker] *= 1.20

    with pytest.raises(RankingNotPossible) as fehler:
        run_modul.main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader,
            bestand_oeffner=oeffner_us_mit(verbogen),
            splits_oeffner=keine_splits,
        )

    text = str(fehler.value)
    assert "VERWEIGERT" in text
    assert "AAA" in text and "DDD" in text
    assert not (tmp_path / "data/rankings/us_2026-07.json").exists(), \
        "es wurde ein US-Ranking geschrieben, obwohl der Vergleich verweigert hat"


def test_ein_echter_split_stoppt_den_lauf_nicht(welt):
    """Derselbe manipulierte Kurs wie oben, aber diesmal MIT Split-Beleg
    fuer alle vier Titel -- der Lauf laeuft durch, die Titel stehen als
    "Split erkannt" im Report, nicht als Abweichler."""
    tmp_path, downloader = welt
    verbogen = dict(KURSE_AM_STICHTAG)
    betroffene = ("AAA", "BBB", "CCC", "DDD")
    for ticker in betroffene:
        verbogen[ticker] *= 2  # 2:1 ist ein gaengiges Split-Verhaeltnis

    def splits(ticker):
        return {STICHTAG: 2.0} if ticker in betroffene else {}

    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        bestand_oeffner=oeffner_us_mit(verbogen),
        splits_oeffner=splits,
    )
    assert code == 0
    us = json.loads((tmp_path / "data/rankings/us_2026-07.json").read_text(encoding="utf-8"))
    assert us["kursvergleich"]["verdikt"] == "ok"
    assert us["kursvergleich"]["abweichler"] == []
    assert sorted(s["ticker"] for s in us["kursvergleich"]["split_erkannt"]) == sorted(betroffene)


def test_die_zweitquelle_veraendert_keine_us_ranking_zahl(welt):
    """DER MUTATIONS-NACHWEIS fuer US, Geschwister des DE-Tests: derselbe
    Lauf, einmal unauffaellig und einmal (unterhalb des Zulasses)
    manipuliert. Alles ausser dem Vergleichsblock bleibt Zeichen fuer
    Zeichen gleich."""
    tmp_path, downloader = welt

    def lauf(kurse):
        for datei in (tmp_path / "data" / "rankings").glob("*.json"):
            datei.unlink()
        run_modul.main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader,
            bestand_oeffner=oeffner_us_mit(kurse),
            splits_oeffner=keine_splits,
        )
        return json.loads(
            (tmp_path / "data/rankings/us_2026-07.json").read_text(encoding="utf-8")
        )

    sauber = lauf(KURSE_AM_STICHTAG)
    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] *= 1.30
    manipuliert = lauf(verbogen)

    assert manipuliert["kursvergleich"]["verdikt"] == "ok"
    assert [a["ticker"] for a in manipuliert["kursvergleich"]["abweichler"]] == ["AAA"]

    del sauber["kursvergleich"], manipuliert["kursvergleich"]
    assert json.dumps(sauber, sort_keys=True) == json.dumps(manipuliert, sort_keys=True)


def test_das_us_gatter_laesst_den_de_lauf_unberuehrt(welt):
    """Die Aussage, auf die es beim Bau eines GESCHWISTER-Gatters ankommt:
    was auch immer im US-Vergleich steht (hier: ein Abweichler unterhalb
    des Zulasses -- der Lauf laeuft in beiden Faellen durch, siehe die
    Markt-Reihenfolge in config.MARKETS), das DE-Ranking desselben Laufs
    ist Zeichen fuer Zeichen dasselbe wie ohne US-Manipulation. Ein US-
    VERWEIGERT wuerde den ganzen Lauf abbrechen, bevor DE dran ist -- das
    ist eine bekannte, andernorts akzeptierte Eigenschaft von run.py
    (keine Markt-Isolierung bei einem Abbruch), keine neue Luecke dieses
    Gatters, und deshalb hier bewusst NICHT der gepruefte Fall."""
    tmp_path, downloader = welt

    def de_ranking_nach(kurse):
        for datei in (tmp_path / "data" / "rankings").glob("*.json"):
            datei.unlink()
        run_modul.main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader,
            bestand_oeffner=oeffner_us_mit(kurse),
            splits_oeffner=keine_splits,
        )
        return json.loads(
            (tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8")
        )

    ruhig = de_ranking_nach(KURSE_AM_STICHTAG)
    mit_abweichler = dict(KURSE_AM_STICHTAG)
    mit_abweichler["AAA"] *= 1.30  # ein einzelner Abweichler, unter dem US-Zulass
    unruhig = de_ranking_nach(mit_abweichler)

    assert json.dumps(ruhig, sort_keys=True) == json.dumps(unruhig, sort_keys=True)
