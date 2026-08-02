"""Universum, Handelbarkeits-Filter und Mindestabdeckung.

Grundsatz: lieber lauter Abbruch als stiller Rueckfall.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import replace

import pytest

from momentum.config import LIQUIDITY_MIN_MEDIAN_TURNOVER, MARKETS_BY_KEY
from momentum.data import download_prices
from momentum.ranking import RankingNotPossible, build_ranking, median_turnover
from momentum.universe import UniverseNotReady, load_universe
from tests.conftest import ASOF, index_series, make_downloader, sample_series, write_universe

Date = _dt.date


# ------------------------------------------------------------------ Universum


def test_platzhalter_bricht_laut_ab(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: S&P 500\n# Herkunft: x\n# Stand: 2026-07-31\n# STATUS: PLACEHOLDER\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="PLATZHALTER"):
        load_universe(datei)


def test_die_ausgelieferten_universen_sind_noch_platzhalter():
    """Bis der Bootstrap-Workflow lief, MUSS das Werkzeug den Dienst verweigern."""
    for pfad in ("universe/universe_us.txt", "universe/universe_de.txt"):
        with pytest.raises(UniverseNotReady):
            load_universe(pfad)


def test_fehlende_herkunft_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text("# Universum: X\n# Stand: 2026-07-31\nAAA\tFirma\n", encoding="utf-8")
    with pytest.raises(UniverseNotReady, match="herkunft"):
        load_universe(datei)


def test_unplausibles_stand_datum_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Herkunft: y\n# Stand: irgendwann\nAAA\tFirma\n", encoding="utf-8"
    )
    with pytest.raises(UniverseNotReady, match="Stand"):
        load_universe(datei)


def test_doppelter_ticker_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text(
        "# Universum: X\n# Herkunft: y\n# Stand: 2026-07-31\nAAA\tEins\nAAA\tZwei\n",
        encoding="utf-8",
    )
    with pytest.raises(UniverseNotReady, match="doppelt"):
        load_universe(datei)


def test_leeres_universum_ist_ein_fehler(tmp_path):
    datei = tmp_path / "u.txt"
    datei.write_text("# Universum: X\n# Herkunft: y\n# Stand: 2026-07-31\n", encoding="utf-8")
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
