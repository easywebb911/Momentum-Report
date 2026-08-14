"""Das DE-Vergleichsgatter — alle drei Verdikt-Stufen, ohne Netz.

Die vier Zusagen, die hier festgehalten werden:

  1. Alle drei Stufen greifen: durchgewinkt, VERWEIGERT, entfallen.
  2. Ein manipulierter Kurs, der ueber Toleranz UND Zulass liegt, stoppt
     den Stichtags-Lauf wirklich — und zwar bevor irgendetwas geschrieben
     ist (Mutations-Nachweis in die eine Richtung).
  3. Die Zweitquelle speist NIEMALS eine Ranking-Zahl. Derselbe
     manipulierte Kurs, unterhalb der Schwelle, laesst jede Zahl des
     Rankings Zeichen fuer Zeichen unveraendert und dreht ausschliesslich
     das Verdikt (Mutations-Nachweis in die andere Richtung).
  4. "Nicht moeglich" ist nie still: Grund im Report, Grund im Push.
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

from momentum import kursvergleich as kv  # noqa: E402
from momentum import run as run_modul  # noqa: E402
from momentum.config import MARKETS_BY_KEY  # noqa: E402
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
# Der DE-Markt fuehrt Yahoo-Ticker mit ".DE" -- genau die Form, die der
# Parser aus den Xetra-Kuerzeln der Bestandsliste macht. Ohne sie waere die
# Verbindung zwischen Universum und Bestandsliste in diesem Test gar keine.
TICKER_DE = [f"{t}.DE" for t in TICKER]

# Die Kurse des Kunst-Beispiels am Stichtag (siehe tests/conftest.py).
KURSE_AM_STICHTAG = {
    "AAA": 160.00, "BBB": 125.00, "CCC": 90.00, "DDD": 250.00, "EEE": 75.00,
}

KOPFZEILE = (
    "Emittententicker,Name,Sektor,Anlageklasse,Marktwert,Gewichtung (%),"
    "Nominalwert,Nominale,Kurs,Standort,Börse,Marktwährung"
)


def bestandsdatei(kurse: dict[str, float], *, stand: str = "31.Juli2026",
                  waehrung: str = "EUR", kurs_text: dict[str, str] | None = None) -> str:
    """Eine Bestandsliste im echten Format, mit frei setzbarer Kurs-Spalte."""
    zeilen = [KOPFZEILE]
    for ticker, kurs in kurse.items():
        text = (kurs_text or {}).get(ticker, f"{kurs:.2f}")
        zeilen.append(
            f"{ticker},{ticker} AG,Informationstechnologie,Aktien,"
            f"1234567.89,1.23,10000,10000,{text},Deutschland,Xetra,{waehrung}"
        )
    return f'Fondsposition per,"{stand}"\n \n' + "\n".join(zeilen) + "\n"


def befund_aus(kurse: dict[str, float], **kw):
    """Der ECHTE Parser, mit ausgesetztem Anzahl-Gatter (5 Kunst-Titel)."""
    return bu.parse_ishares_holdings(
        bestandsdatei(kurse, **kw), "DAX", heute=Date(2026, 8, 3),
        erwartete_anzahl=(0, 1000),
    )


def roh_kurse(am: Date = STICHTAG) -> dict[str, dict[Date, float]]:
    """Was `PriceBundle.close` liefern wuerde -- Yahoo-Ticker, roher Kurs."""
    return {f"{t}.DE": {am: k} for t, k in KURSE_AM_STICHTAG.items()}


# ==========================================================================
# Der Parser: die Kurs-Spalte und ihre Zahlenschreibweise
# ==========================================================================


def test_die_kurs_spalte_wird_gelesen():
    befund = befund_aus(KURSE_AM_STICHTAG)
    nach_ticker = {k.ticker: k for k in befund.kandidaten}
    assert nach_ticker["AAA.DE"].kurs == pytest.approx(160.00)
    assert nach_ticker["DDD.DE"].waehrung == "EUR"
    assert befund.kurs_konvention == "punkt"


def test_deutsches_zahlenformat_wird_gelesen():
    """1.234,56 — die Schreibweise, die ein englischer Leser um Faktor 1000
    verfehlen wuerde."""
    befund = bu.parse_ishares_holdings(
        bestandsdatei(
            {"XYZ": 0}, kurs_text={"XYZ": '"1.234,56"'}
        ),
        "DAX", heute=Date(2026, 8, 3), erwartete_anzahl=(0, 1000),
    )
    assert befund.kurs_konvention == "komma"
    assert befund.kandidaten[0].kurs == pytest.approx(1234.56)


def test_englisches_zahlenformat_wird_gelesen():
    befund = bu.parse_ishares_holdings(
        bestandsdatei({"XYZ": 0}, kurs_text={"XYZ": '"1,234.56"'}),
        "DAX", heute=Date(2026, 8, 3), erwartete_anzahl=(0, 1000),
    )
    assert befund.kurs_konvention == "punkt"
    assert befund.kandidaten[0].kurs == pytest.approx(1234.56)


def test_eine_nicht_entscheidbare_schreibweise_liefert_gar_keinen_kurs():
    """"1,234" kann 1,234 oder 1234 heissen. Raten waere hier Faktor 1000 —
    also wird nicht geraten."""
    befund = bu.parse_ishares_holdings(
        bestandsdatei({"XYZ": 0, "ABC": 0},
                      kurs_text={"XYZ": '"1,234"', "ABC": '"5,678"'}),
        "DAX", heute=Date(2026, 8, 3), erwartete_anzahl=(0, 1000),
    )
    assert befund.kurs_konvention is None
    assert all(k.kurs is None for k in befund.kandidaten)


def test_widersprechende_schreibweisen_liefern_gar_keinen_kurs():
    befund = bu.parse_ishares_holdings(
        bestandsdatei({"XYZ": 0, "ABC": 0},
                      kurs_text={"XYZ": '"1.234,56"', "ABC": '"9,876.54"'}),
        "DAX", heute=Date(2026, 8, 3), erwartete_anzahl=(0, 1000),
    )
    assert befund.kurs_konvention is None
    assert all(k.kurs is None for k in befund.kandidaten)


def test_die_kurs_spalte_aendert_das_universum_nicht():
    """Der Umbau darf am eigentlichen Zweck der Datei nichts drehen."""
    ohne_kurs = befund_aus(KURSE_AM_STICHTAG, kurs_text={t: "-" for t in KURSE_AM_STICHTAG})
    mit_kurs = befund_aus(KURSE_AM_STICHTAG)
    assert [k.ticker for k in ohne_kurs.kandidaten] == [k.ticker for k in mit_kurs.kandidaten]
    assert all(k.kurs is None for k in ohne_kurs.kandidaten)


# ==========================================================================
# Stufe (a): durchgewinkt
# ==========================================================================


def test_uebereinstimmende_kurse_sind_ein_ok():
    vergleich = kv.vergleiche([befund_aus(KURSE_AM_STICHTAG)], roh_kurse())
    assert vergleich.verdikt == "ok"
    assert len(vergleich.verglichen) == 5
    assert vergleich.abweichler == ()
    assert vergleich.stichtag == STICHTAG


def test_bis_zum_zulass_laeuft_es_normal_weiter():
    """Genau drei Ausreisser: Lauf laeuft, aber sie stehen namentlich da."""
    verbogen = dict(KURSE_AM_STICHTAG)
    for ticker in ("AAA", "BBB", "CCC"):
        verbogen[ticker] *= 1.05
    vergleich = kv.vergleiche([befund_aus(verbogen)], roh_kurse())
    assert vergleich.verdikt == "ok"
    assert len(vergleich.abweichler) == kv.ZULASS_ABWEICHLER == 3
    protokoll = "\n".join(vergleich.protokoll())
    for ticker in ("AAA.DE", "BBB.DE", "CCC.DE"):
        assert ticker in protokoll, "ein Abweichler fehlt im Protokoll"


def test_knapp_innerhalb_der_toleranz_ist_kein_abweichler():
    knapp = {t: k * (1 + kv.TOLERANZ * 0.9) for t, k in KURSE_AM_STICHTAG.items()}
    assert kv.vergleiche([befund_aus(knapp)], roh_kurse()).abweichler == ()


def test_knapp_ausserhalb_der_toleranz_ist_einer():
    daneben = dict(KURSE_AM_STICHTAG)
    daneben["AAA"] = KURSE_AM_STICHTAG["AAA"] * (1 + kv.TOLERANZ * 1.1)
    abweichler = kv.vergleiche([befund_aus(daneben)], roh_kurse()).abweichler
    assert [a.ticker for a in abweichler] == ["AAA.DE"]


# ==========================================================================
# Stufe (b): VERWEIGERT
# ==========================================================================


def test_zu_viele_abweichler_verweigern():
    vergleich = kv.vergleiche(
        [befund_aus({t: k * 1.5 for t, k in KURSE_AM_STICHTAG.items()})], roh_kurse()
    )
    assert vergleich.verdikt == "verweigert"
    assert vergleich.verweigert is True
    assert len(vergleich.abweichler) == 5


def test_der_abbruchtext_nennt_jeden_titel_mit_beiden_kursen():
    vergleich = kv.vergleiche(
        [befund_aus({t: k * 1.5 for t, k in KURSE_AM_STICHTAG.items()})], roh_kurse()
    )
    text = kv.abbruchtext(vergleich, "de")
    assert "VERWEIGERT" in text
    assert "KEIN Ranking geschrieben" in text
    for ticker in KURSE_AM_STICHTAG:
        assert f"{ticker}.DE" in text
    # Beide Seiten stehen da — sonst kann man am Telefon nicht entscheiden,
    # welche Quelle luegt.
    assert "iShares 240.0000 vs. Kursquelle 160.0000" in text
    # Und der Weg zurueck: der Stichtag geht nicht verloren.
    assert "bleibt offen" in text


# ==========================================================================
# Stufe (c): entfallen — nie still
# ==========================================================================


def test_ohne_kurs_spalte_entfaellt_der_vergleich_mit_grund():
    ohne = befund_aus(KURSE_AM_STICHTAG, kurs_text={t: "-" for t in KURSE_AM_STICHTAG})
    vergleich = kv.vergleiche([ohne], roh_kurse())
    assert vergleich.verdikt == "entfallen"
    assert "keine lesbare Kurs-Spalte" in vergleich.grund
    assert vergleich.kurzfassung().startswith("Kursvergleich entfiel:")


def test_ohne_kurs_am_stichtag_der_datei_entfaellt_der_vergleich():
    """Die Kursquelle hat den Tag der Bestandsliste nicht — dann gibt es
    nichts zu vergleichen, und das wird gesagt statt gewunken."""
    vergleich = kv.vergleiche([befund_aus(KURSE_AM_STICHTAG)], roh_kurse(Date(2026, 7, 30)))
    assert vergleich.verdikt == "entfallen"
    assert "vergleichbar" in vergleich.grund


def test_fremde_marktwaehrung_wird_nicht_verglichen_und_gilt_nicht_als_bruch():
    """Ein Dollar-Kurs gegen einen Euro-Kurs waere eine riesige Abweichung —
    und ein voellig grundloser Abbruch."""
    befund = befund_aus(KURSE_AM_STICHTAG, waehrung="USD")
    vergleich = kv.vergleiche([befund], roh_kurse())
    assert vergleich.verdikt == "entfallen"
    assert all("USD" in eintrag for eintrag in vergleich.ohne_vergleich)


def test_ein_einzelner_fremdwaehrungs_titel_faellt_nur_selbst_heraus():
    zeilen = bestandsdatei(KURSE_AM_STICHTAG).splitlines()
    zeilen = [z.replace(",EUR", ",USD") if z.startswith("AAA,") else z for z in zeilen]
    befund = bu.parse_ishares_holdings(
        "\n".join(zeilen) + "\n", "DAX", heute=Date(2026, 8, 3),
        erwartete_anzahl=(0, 1000),
    )
    vergleich = kv.vergleiche([befund], roh_kurse())
    assert vergleich.verdikt == "ok"
    assert vergleich.ohne_vergleich == ("AAA.DE (Marktwaehrung USD)",)
    assert "AAA.DE" not in vergleich.verglichen


def test_ein_leerer_befund_entfaellt_statt_gruen_zu_zeigen():
    assert kv.vergleiche([], {}).verdikt == "entfallen"


def test_das_universum_grenzt_ein():
    """Nur Titel des Universums werden verglichen — sonst schlaegt ein
    Fonds-Sonderposten das Gatter."""
    vergleich = kv.vergleiche(
        [befund_aus(KURSE_AM_STICHTAG)], roh_kurse(), universum={"AAA.DE", "BBB.DE"}
    )
    assert set(vergleich.verglichen) == {"AAA.DE", "BBB.DE"}


# ==========================================================================
# Der Lauf: greift das Gatter wirklich?
# ==========================================================================


@pytest.fixture
def welt(tmp_path, monkeypatch):
    """Dasselbe Miniatur-Projekt wie im Ende-zu-Ende-Test, aber mit
    DE-Tickern: der Vergleich existiert nur fuer Deutschland."""
    (tmp_path / "universe").mkdir()
    (tmp_path / "docs").mkdir()
    for datei in ("style.css", "app.js"):
        (tmp_path / "docs" / datei).write_text("/* Platzhalter */", encoding="utf-8")

    maerkte = []
    for key, titel in (("us", TICKER), ("de", TICKER_DE)):
        pfad = write_universe(
            tmp_path / "universe" / f"universe_{key}.txt", titel, label=f"Test {key.upper()}"
        )
        maerkte.append(replace(MARKETS_BY_KEY[key], universe_file=str(pfad)))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_modul, "MARKETS", tuple(maerkte))
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    serien = sample_series()
    # Dieselben Kursreihen noch einmal unter dem .DE-Namen: der DE-Markt
    # rechnet mit ihnen, und der Vergleich stellt ihren unbereinigten
    # Schlusskurs gegen die Kurs-Spalte der Bestandsliste.
    serien.update({f"{t}.DE": reihe for t, reihe in list(serien.items())})
    serien["^SP500TR"] = index_series()
    serien["^IRX"] = {tag: 3.0 for tag in MONTH_ENDS}
    serien["^GDAXI"] = index_series()
    return tmp_path, make_downloader(serien)


def oeffner_mit(kurse: dict[str, float], **kw):
    """Ein `bestand_oeffner`, der fuer alle drei Dateien dieselbe Liste
    liefert. Das Anzahl-Gatter greift dabei nicht, weil die Kunst-Welt nur
    fuenf Titel hat — deshalb wird es hier ueber die Umgebung nicht
    ausgesetzt, sondern der Lauf ueber `parse` gefuehrt, das die echten
    Bereiche kennt. Fuer diesen Test wird es bewusst umgangen, indem der
    Vergleich die Datei direkt bekommt."""
    inhalt = bestandsdatei(kurse, **kw)
    return lambda quelle: inhalt


@pytest.fixture
def kleines_anzahl_gatter(monkeypatch):
    """Die Kunst-Welt hat fuenf Titel, die echten Indizes 40/50/30. Fuer den
    Lauf-Test wird das ANZAHL-GATTER deshalb auf die Kunst-Groesse gesetzt
    — geprueft wird hier das Vergleichsgatter, nicht das Anzahl-Gatter (das
    hat seine eigenen Tests)."""
    from momentum import ishares

    monkeypatch.setattr(
        ishares, "ANZAHL_ERWARTET", {"DAX": (1, 9), "MDAX": (1, 9), "TecDAX": (1, 9)}
    )


def test_der_lauf_laeuft_normal_wenn_die_kurse_zusammenpassen(welt, kleines_anzahl_gatter):
    tmp_path, downloader = welt
    code = run_modul.main(
        ["--today", STICHTAG.isoformat()],
        downloader=downloader,
        bestand_oeffner=oeffner_mit(KURSE_AM_STICHTAG),
    )
    assert code == 0
    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    assert de["kursvergleich"]["verdikt"] == "ok"
    assert de["kursvergleich"]["verglichen"] == 5
    assert de["kursvergleich"]["abweichler"] == []


def test_ein_manipulierter_kurs_stoppt_den_stichtags_lauf_wirklich(
    welt, kleines_anzahl_gatter
):
    """DIE Ziel-Mechanik, und der eigentliche Zweck dieses ganzen PRs.

    Vier von fuenf Titeln weit daneben -- mehr als der Zulass. Der Lauf
    muss abbrechen, und zwar BEVOR eine Ranking-Datei entstanden ist.
    """
    tmp_path, downloader = welt
    verbogen = dict(KURSE_AM_STICHTAG)
    for ticker in ("AAA", "BBB", "CCC", "DDD"):
        verbogen[ticker] *= 1.20

    with pytest.raises(RankingNotPossible) as fehler:
        run_modul.main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader,
            bestand_oeffner=oeffner_mit(verbogen),
        )

    text = str(fehler.value)
    assert "VERWEIGERT" in text
    assert "AAA.DE" in text and "DDD.DE" in text
    assert not (tmp_path / "data/rankings/de_2026-07.json").exists(), \
        "es wurde ein DE-Ranking geschrieben, obwohl der Vergleich verweigert hat"


def test_der_verweigerte_lauf_meldet_sich_laut(welt, kleines_anzahl_gatter, monkeypatch):
    """`cli()` macht aus dem Abbruch Code 2 und EINEN Fehlschlag-Push mit
    dem echten Grund -- nicht mit einem allgemeinen "Job rot"."""
    tmp_path, downloader = welt
    gemeldet = []
    monkeypatch.setattr(run_modul, "push_run_failed",
                        lambda text: gemeldet.append(text) or True)

    echtes_main = run_modul.main
    oeffner = oeffner_mit({t: k * 1.2 for t, k in KURSE_AM_STICHTAG.items()})
    monkeypatch.setattr(
        run_modul, "main",
        lambda *a, **k: echtes_main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader, bestand_oeffner=oeffner,
        ),
    )
    assert run_modul.cli() == 2
    assert len(gemeldet) == 1, "genau ein Push, nicht keiner und nicht zwei"
    assert "VERWEIGERT" in gemeldet[0]
    assert "nicht entscheidbar, welche recht hat" in gemeldet[0]


def test_die_zweitquelle_veraendert_keine_einzige_ranking_zahl(
    welt, kleines_anzahl_gatter
):
    """DER MUTATIONS-NACHWEIS: derselbe Lauf, einmal mit unauffaelliger und
    einmal mit (unterhalb des Zulasses) manipulierter Kurs-Spalte. Alles
    ausser dem Vergleichsblock muss Zeichen fuer Zeichen gleich sein."""
    tmp_path, downloader = welt

    def lauf(kurse):
        for datei in (tmp_path / "data" / "rankings").glob("*.json"):
            datei.unlink()
        run_modul.main(
            ["--today", STICHTAG.isoformat()],
            downloader=downloader,
            bestand_oeffner=oeffner_mit(kurse),
        )
        return json.loads(
            (tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8")
        )

    sauber = lauf(KURSE_AM_STICHTAG)
    verbogen = dict(KURSE_AM_STICHTAG)
    verbogen["AAA"] *= 1.30          # weit ausserhalb der Toleranz ...
    manipuliert = lauf(verbogen)     # ... aber nur EIN Titel: kein Abbruch

    assert manipuliert["kursvergleich"]["verdikt"] == "ok"
    assert [a["ticker"] for a in manipuliert["kursvergleich"]["abweichler"]] == ["AAA.DE"]

    # Und jetzt der Punkt: alles andere ist identisch.
    del sauber["kursvergleich"], manipuliert["kursvergleich"]
    assert json.dumps(sauber, sort_keys=True) == json.dumps(manipuliert, sort_keys=True)


def test_ohne_erreichbare_bestandsliste_laeuft_der_lauf_und_sagt_es(welt):
    """Fail-soft, aber sichtbar: die Sperre in conftest verhindert jeden
    echten Abruf — genau der Pfad, der auch bei einem Ausfall greift."""
    tmp_path, downloader = welt
    assert run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader) == 0
    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    assert de["kursvergleich"]["verdikt"] == "entfallen"
    assert de["kursvergleich"]["grund"], "entfallen ohne Grund waere still"


def test_der_schalter_setzt_das_gatter_sichtbar_aus(welt, kleines_anzahl_gatter):
    """Notausgang — aber nicht heimlich."""
    tmp_path, downloader = welt
    code = run_modul.main(
        ["--today", STICHTAG.isoformat(), "--ohne-kursvergleich"],
        downloader=downloader,
        bestand_oeffner=oeffner_mit({t: k * 5 for t, k in KURSE_AM_STICHTAG.items()}),
    )
    assert code == 0, "der Schalter muss den Lauf durchlassen"
    de = json.loads((tmp_path / "data/rankings/de_2026-07.json").read_text(encoding="utf-8"))
    assert de["kursvergleich"]["verdikt"] == "entfallen"
    assert de["kursvergleich"]["grund"] == kv.ABGESCHALTET


def test_der_us_markt_traegt_den_grund_statt_eines_leeren_blocks(welt):
    """Seit Stufe 2b hat auch der US-Markt ein echtes Gatter (siehe
    tests/unit/test_kursvergleich_us.py) -- ohne eigenen `bestand_oeffner`
    greift hier dieselbe Sperre wie bei DE (keine echten Netzabrufe in
    Tests) und der Vergleich entfaellt mit einem ECHTEN Grund, nicht mehr
    mit dem festen "fuer diesen Markt nicht vorgesehen"."""
    tmp_path, downloader = welt
    run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader)
    us = json.loads((tmp_path / "data/rankings/us_2026-07.json").read_text(encoding="utf-8"))
    assert us["kursvergleich"]["verdikt"] == "entfallen"
    assert us["kursvergleich"]["grund"] != kv.NICHT_VORGESEHEN
    assert "SXR8" in us["kursvergleich"]["grund"] and "IUSA" in us["kursvergleich"]["grund"]


def test_der_anzeige_lauf_ruehrt_die_bestandslisten_nicht_an(welt, kleines_anzahl_gatter):
    """Die iShares-Kurse sind Stichtags-Bewertungen — an einem gewoehnlichen
    Tag gibt es nichts zu vergleichen, also wird auch nichts geholt."""
    tmp_path, downloader = welt
    gerufen = []

    def oeffner(quelle):
        gerufen.append(quelle.index_name)
        return bestandsdatei(KURSE_AM_STICHTAG)

    run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader,
                   bestand_oeffner=oeffner)
    nach_stichtag = len(gerufen)
    # 3 DE-Dateien + SXR8 + IUSA (der US-Ausweich wird ebenfalls versucht,
    # weil die Kunst-Datei mit 5 Zeilen das US-ANZAHL-Gatter nicht besteht).
    assert nach_stichtag == 5, "am Stichtag werden alle fuenf Dateien geholt"

    run_modul.main(["--today", "2026-08-05"], downloader=downloader,
                   bestand_oeffner=oeffner)
    assert len(gerufen) == nach_stichtag, "der Anzeige-Lauf hat Dateien geholt"


# ==========================================================================
# Der Push
# ==========================================================================


def test_der_push_traegt_den_entfallenen_vergleich(welt, monkeypatch):
    tmp_path, downloader = welt
    verschickt = []
    monkeypatch.setattr(
        run_modul, "push_new_ranking",
        lambda entries, **kw: verschickt.append(kw.get("hinweise")) or True,
    )
    run_modul.main(["--today", STICHTAG.isoformat()], downloader=downloader)
    hinweise = verschickt[0]
    assert any("Kursvergleich entfiel" in h for h in hinweise)
    assert any(h.startswith("Deutschland:") for h in hinweise)
    # Seit Stufe 2b hat auch der US-Markt ein echtes Gatter -- entfaellt
    # es (hier: kein bestand_oeffner, also gesperrter Netzabruf), gehoert
    # der Grund genauso in den Push wie bei DE. Nur der alte, dauerhaft
    # feste "nicht vorgesehen"-Text sollte NIE einen Push fuellen.
    usa_hinweis = next((h for h in hinweise if h.startswith("USA:")), None)
    assert usa_hinweis is not None
    assert "Kursvergleich entfiel" in usa_hinweis
    assert kv.NICHT_VORGESEHEN not in usa_hinweis


def test_der_push_text_enthaelt_die_hinweise():
    from momentum.notify import push_new_ranking

    gesehen = {}

    def opener(request, timeout=None):  # noqa: ARG001
        gesehen["body"] = json.loads(request.data.decode("utf-8"))["message"]

        class Antwort:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        return Antwort()

    push_new_ranking(
        [{"markt": "Deutschland", "stichtag": "2026-07-31", "top": "SAP.DE",
          "top_name": "SAP SE", "score": 99.0}],
        hinweise=["Deutschland: Kursvergleich entfiel: Testgrund"],
        topic="probe",
        opener=opener,
    )
    assert "Kursvergleich entfiel: Testgrund" in gesehen["body"]


# ==========================================================================
# Die Konstanten
# ==========================================================================


def test_die_schwellen_stehen_wie_hergeleitet():
    """Wer sie aendert, muss die Herleitung im Modul mitaendern — dieser
    Test zwingt zumindest dazu, dort vorbeizukommen."""
    assert kv.TOLERANZ == 0.010
    assert kv.ZULASS_ABWEICHLER == 3
    assert kv.MIN_VERGLEICHSQUOTE == 0.80
    assert kv.ERWARTETE_WAEHRUNG == "EUR"
