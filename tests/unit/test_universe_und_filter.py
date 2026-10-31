"""Universum, Handelbarkeits-Filter und Mindestabdeckung.

Grundsatz: lieber lauter Abbruch als stiller Rueckfall.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from dataclasses import replace

import pytest

from momentum.config import LIQUIDITY_MIN_MEDIAN_TURNOVER, MARKETS_BY_KEY
from momentum.data import download_prices
from momentum.ranking import RankingNotPossible, build_ranking, dump_ranking, median_turnover
from momentum.universe import UniverseNotReady, load_universe
from tests.conftest import ASOF, index_series, make_downloader, sample_series, write_universe

Date = _dt.date


# ------------------------------------------------------------------ Universum


# Platzhalter und Status-Gatter: siehe tests/unit/test_kein_platzhalter_ranking.py


def test_fehlende_herkunft_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Stand: 2026-07-31\n# STATUS: VERIFIED\nAAA\tFirma\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="herkunft"):
        load_universe(datei)


def test_unplausibles_stand_datum_ist_ein_fehler(tmp_path):
    # Status-Gatter kommt zuerst -- hier soll die Datumspruefung greifen.
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Herkunft: y\n# Stand: irgendwann\n"
        "# STATUS: VERIFIED\nAAA\tFirma\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="Stand"):
        load_universe(datei)


def test_doppelter_ticker_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Herkunft: y\n# Stand: 2026-07-31\n# STATUS: VERIFIED\n"
        "AAA\tEins\nAAA\tZwei\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="doppelt"):
        load_universe(datei)


def test_leeres_universum_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Herkunft: y\n# Stand: 2026-07-31\n# STATUS: VERIFIED\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="keine Ticker"):
        load_universe(datei)


def test_universum_liest_ticker_namen_und_kopf(tmp_path):
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB"], label="HDAX", origin="Quelle Z")
    universum = load_universe(datei)
    assert universum.label == "HDAX"
    assert universum.origin == "Quelle Z"
    assert universum.as_of == "2026-07-31"
    assert universum.tickers == ("AAA", "BBB")
    assert universum.name_of("AAA") == "Firma AAA"


# --------------------------------------------------- Handelbarkeits-Filter


def test_median_umsatz_der_letzten_drei_monate():
    umsatz = {
        Date(2026, 3, 31): 1.0,       # ausserhalb des Fensters
        Date(2026, 4, 30): 10_000_000.0,
        Date(2026, 5, 31): 4_000_000.0,
        Date(2026, 6, 30): 6_000_000.0,
        Date(2026, 7, 31): 8_000_000.0,
    }
    # Fenster ab 01.04.2026: 10, 4, 6, 8 Mio -> Median (6+8)/2 = 7 Mio
    assert median_turnover(umsatz, ASOF) == pytest.approx(7_000_000.0)


def test_schwelle_ist_eine_benannte_konstante():
    assert LIQUIDITY_MIN_MEDIAN_TURNOVER == 5_000_000


def test_illiquider_titel_faellt_vor_jeder_rechnung_raus(tmp_path):
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    serien = sample_series()
    # CCC handelt fast nicht: 100 Stueck am Tag
    bundle = download_prices(
        list(universum.tickers),
        Date(2025, 1, 1),
        ASOF,
        downloader=make_downloader(serien, volumes={"CCC": 100.0}),
    )
    ranking = build_ranking(markt, universum, bundle, index_series(), ASOF)
    assert "CCC" not in [r["ticker"] for r in ranking["rangliste"]]
    assert ranking["abdeckung"]["ohne_handelbarkeit"] == 1
    # und die verbliebenen vier werden neu perzentiliert (n = 4 -> Schritte 1/3)
    assert ranking["abdeckung"]["bewertet"] == 4


# ------------------------------------------- Ausscheidegruende in der Abbruchmeldung
#
# Anlass: Lauf #94/#95, 31.10.2026 -- der Oktober-Stichtag brach bei DE ab
# ("de: kein Titel mit vollstaendiger Historie"), ohne dass aus der
# Meldung hervorging, WARUM. Die drei Faelle hier bilden je einen der drei
# moeglichen Ausscheidegruende synthetisch nach (siehe ranking.py, Zeilen
# um 236-271).


def test_abbruchmeldung_nennt_ausscheidegruende_ohne_stichtagskurs(tmp_path):
    """DE-aehnlicher Fall: jeder Titel hat einen Monatsendkurs, aber
    keinen Kurs GENAU am Stichtag selbst (high_52w_ratio schlaegt zuerst
    an, momentum_12_1 braucht den Stichtag nicht direkt)."""
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    ohne_stichtagskurs = {
        ticker: {tag: kurs for tag, kurs in serie.items() if tag != ASOF}
        for ticker, serie in sample_series().items()
    }
    bundle = download_prices(
        list(universum.tickers), Date(2025, 1, 1), ASOF,
        downloader=make_downloader(ohne_stichtagskurs),
    )
    with pytest.raises(
        RankingNotPossible,
        match=(
            r"us: kein Titel mit vollstaendiger Historie \(Universum 5, "
            r"mit Kursen 5, liquide 5, ohne Stichtagskurs 5, "
            r"ohne Monatsendkurs 0, sonstige 0\)"
        ),
    ):
        build_ranking(markt, universum, bundle, index_series(), ASOF)


def test_abbruchmeldung_nennt_ausscheidegruende_alle_illiquide(tmp_path):
    """Jeder Titel scheitert schon am Handelbarkeits-Filter -- die
    Historie-Schleife laeuft dann gar nicht erst, alle drei
    Historie-Zaehler bleiben bei 0."""
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    serien = sample_series()
    bundle = download_prices(
        list(universum.tickers), Date(2025, 1, 1), ASOF,
        downloader=make_downloader(serien, volumes={t: 100.0 for t in serien}),
    )
    with pytest.raises(
        RankingNotPossible,
        match=(
            r"us: kein Titel mit vollstaendiger Historie \(Universum 5, "
            r"mit Kursen 5, liquide 0, ohne Stichtagskurs 0, "
            r"ohne Monatsendkurs 0, sonstige 0\)"
        ),
    ):
        build_ranking(markt, universum, bundle, index_series(), ASOF)


def test_abbruchmeldung_nennt_ausscheidegruende_ohne_monatsendkurs(tmp_path):
    """Der Zaehlermonat M-1 (30.06.2026) fehlt bei jedem Titel komplett --
    momentum_12_1 schlaegt ueber month_end_close an, BEVOR high_52w_ratio
    ueberhaupt den Stichtag selbst prueft."""
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    ohne_monatsendkurs = {
        ticker: {tag: kurs for tag, kurs in serie.items() if tag != Date(2026, 6, 30)}
        for ticker, serie in sample_series().items()
    }
    bundle = download_prices(
        list(universum.tickers), Date(2025, 1, 1), ASOF,
        downloader=make_downloader(ohne_monatsendkurs),
    )
    with pytest.raises(
        RankingNotPossible,
        match=(
            r"us: kein Titel mit vollstaendiger Historie \(Universum 5, "
            r"mit Kursen 5, liquide 5, ohne Stichtagskurs 0, "
            r"ohne Monatsendkurs 5, sonstige 0\)"
        ),
    ):
        build_ranking(markt, universum, bundle, index_series(), ASOF)


def test_erfolgsfall_bleibt_byte_identisch(tmp_path):
    """Beweis, dass die neue Zaehl-Logik im except-Zweig den Erfolgsfall
    NICHT beruehrt: dasselbe Kunst-Beispiel wie in test_scoring_values.py
    (von Hand nachgerechnet) liefert exakt dieselbe kanonische JSON-Form
    (dump_ranking) wie vor dieser Aenderung -- ausserhalb dieses Tests per
    `git stash` gegen den unveraenderten Stand verglichen: identischer
    SHA-256-Hash (siehe PR-Text)."""
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    bundle = download_prices(
        list(universum.tickers), Date(2025, 1, 1), ASOF,
        downloader=make_downloader(sample_series()),
    )
    ranking = build_ranking(markt, universum, bundle, index_series(), ASOF)
    # Von Hand nachgerechnet in test_scoring_values.py (Kopf-Kommentar
    # "HANDRECHNUNG ENDSCORE"): DDD 75,0 (1.) | AAA/EEE je 62,5 (2./3.,
    # AAA vor EEE alphabetisch) | BBB 50,0 (4.) | CCC 0,0 (5.).
    reihenfolge = [(r["ticker"], r["score"], r["rang"]) for r in ranking["rangliste"]]
    assert reihenfolge == [
        ("DDD", 75.0, 1),
        ("AAA", 62.5, 2),
        ("EEE", 62.5, 3),
        ("BBB", 50.0, 4),
        ("CCC", 0.0, 5),
    ]
    assert ranking["abdeckung"] == {
        "universum": 5,
        "mit_kursen": 5,
        "nach_handelbarkeit": 5,
        "ohne_handelbarkeit": 0,
        "ohne_ausreichende_historie": [],
        "bewertet": 5,
    }
    kanonisch = dump_ranking(ranking)
    assert (
        hashlib.sha256(kanonisch.encode("utf-8")).hexdigest()
        == "cd51ca6d97fd8826cd6e75449b49efe85063b50198d9ac3e28774c51d2b0cd9c"
    )


# ------------------------------------------------------- Mindestabdeckung


def test_zu_wenig_kurse_verhindert_das_ranking(tmp_path):
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    serien = {k: v for k, v in sample_series().items() if k in ("AAA", "BBB", "CCC")}
    bundle = download_prices(
        list(universum.tickers), Date(2025, 1, 1), ASOF, downloader=make_downloader(serien)
    )
    with pytest.raises(RankingNotPossible, match="Mindestabdeckung"):
        build_ranking(markt, universum, bundle, index_series(), ASOF)


def test_trend_ampel_warnt_bei_zwoelfmonats_minus(tmp_path):
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    bundle = download_prices(
        list(universum.tickers),
        Date(2025, 1, 1),
        ASOF,
        downloader=make_downloader(sample_series()),
    )
    fallend = index_series([5000.0 - 30.0 * i for i in range(13)])
    ranking = build_ranking(markt, universum, bundle, fallend, ASOF)
    assert ranking["trend_ampel"]["warnung"] is True
    assert ranking["trend_ampel"]["rendite_12m"] < 0
    # ... und veraendert die Rangfolge NICHT
    steigend = build_ranking(markt, universum, bundle, index_series(), ASOF)
    assert steigend["trend_ampel"]["warnung"] is False
    assert ranking["rangliste"] == steigend["rangliste"]
