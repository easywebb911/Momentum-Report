"""Das Trend-Kriterium als UEBERSCHUSS ueber den Geldmarkt.

Beleg: trend_filter (Moskowitz/Ooi/Pedersen 2012) misst die
Zwoelf-Monats-Rendite ueber dem Geldmarktsatz, nicht den reinen Kursgewinn.

Geprueft wird -- wie ueberall in diesem Projekt -- NICHT, ob die Zahlen
"gut" aussehen, sondern ob exakt die dokumentierte Rechnung passiert:

  * die EZB-CSV wird ueber die Kopfzeile gelesen, nie ueber die Position
  * das Zins-Fenster ist dasselbe wie das der Indexrendite: (Basistag, Stichtag]
  * Ueberschuss = Indexrendite - Geldmarktsatz, Warnung bei < 0
  * faellt die Zinsquelle aus, wird NICHTS geschaetzt: kein Abzug, und die
    Anzeige sagt es sichtbar
  * Score, Perzentile und Rangfolge sehen den Zins NIE

Kein Test geht nach draussen; die EZB-Verbindung ist in tests/conftest.py
gesperrt und wird hier ueber `oeffner` eingespielt.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import replace

import pytest

from momentum.config import MARKETS_BY_KEY
from momentum.data import download_prices
from momentum.ranking import build_ranking
from momentum.render import (
    MarketView,
    ZINS_ALT_HINWEIS,
    ZINS_FEHLT_HINWEIS,
    _trend_banner,
    ampel_wert,
)
from momentum.riskfree import (
    QUELLE_DE,
    QUELLE_FEHLT,
    QUELLE_US,
    hole_ezb,
    mittel_rate,
    parse_ezb_csv,
    riskfree_12m,
)
from momentum.scoring import index_12m_basis
from momentum.universe import load_universe
from tests.conftest import (
    ASOF,
    MONTH_ENDS,
    index_series,
    make_downloader,
    sample_series,
    write_universe,
)

Date = _dt.date

# Das echte Antwortformat der EZB-Reihe, wie am 05.08. geprueft: Kopfzeile
# plus Datenzeilen. Spalte 5 ist das Datum, Spalte 6 der Satz in Prozent --
# aber genau darauf verlaesst sich der Parser NICHT.
EZB_KOPF = "KEY,FREQ,REF_AREA,PROVIDER_FM_ID,TIME_PERIOD,OBS_VALUE,OBS_STATUS"
EZB_ZEILE = "EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,{tag},{wert},A"


def ezb_csv(werte: dict[Date, float], kopf: str = EZB_KOPF) -> str:
    zeilen = [kopf] + [
        EZB_ZEILE.format(tag=tag.isoformat(), wert=wert)
        for tag, wert in sorted(werte.items())
    ]
    return "\n".join(zeilen) + "\n"


def irx_reihe(satz: float) -> dict[Date, float]:
    """^IRX liefert den annualisierten Satz IN PROZENT als "Kurs"."""
    return {tag: satz for tag in MONTH_ENDS}


# ----------------------------------------------------------- EZB-CSV lesen


def test_die_ezb_csv_wird_ueber_die_kopfzeile_gelesen():
    werte = parse_ezb_csv(ezb_csv({Date(2026, 8, 4): 2.185, Date(2026, 8, 5): 2.19}))
    assert werte == {Date(2026, 8, 4): 2.185, Date(2026, 8, 5): 2.19}


def test_vertauschte_spalten_aendern_nichts():
    """Die Position ist nicht zugesichert -- der Name ist es."""
    text = (
        "OBS_VALUE,TIME_PERIOD,KEY\n"
        "2.185,2026-08-04,EST.B.EU000A2X2A25.WT\n"
        "2.190,2026-08-05,EST.B.EU000A2X2A25.WT\n"
    )
    assert parse_ezb_csv(text) == {Date(2026, 8, 4): 2.185, Date(2026, 8, 5): 2.19}


def test_ohne_kopfzeile_wird_nichts_geraten():
    """Lieber gar kein Zins als ein aus der Position geratener."""
    ohne = "EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,2026-08-04,2.185,A\n"
    assert parse_ezb_csv(ohne) == {}
    assert parse_ezb_csv("") == {}
    assert parse_ezb_csv("<html>Fehlerseite</html>") == {}


def test_unbrauchbare_zeilen_fallen_einzeln_heraus():
    text = (
        f"{EZB_KOPF}\n"
        "EST,B,EU,WT,2026-08-04,2.185,A\n"
        "EST,B,EU,WT,2026-08-05,,A\n"          # Feiertag ohne Wert
        "EST,B,EU,WT,kein-datum,2.2,A\n"
        "zu,kurz\n"
        "EST,B,EU,WT,2026-08-06,2.2,A\n"
    )
    assert parse_ezb_csv(text) == {Date(2026, 8, 4): 2.185, Date(2026, 8, 6): 2.2}


def test_ein_ausfall_der_verbindung_ergibt_ein_leeres_dict():
    def kaputt(_url):
        raise OSError("Name or service not known")

    assert hole_ezb(Date(2025, 7, 31), oeffner=kaputt) == {}


def test_die_abgefragte_adresse_traegt_das_startdatum():
    gesehen = []

    def merker(url):
        gesehen.append(url)
        return ezb_csv({Date(2026, 8, 4): 2.0})

    hole_ezb(Date(2025, 7, 31), oeffner=merker)
    assert "startPeriod=2025-07-31" in gesehen[0]
    assert "format=csvdata" in gesehen[0]


# ------------------------------------------------------------- Mittelung


def test_der_mittelwert_ist_das_arithmetische_mittel_geteilt_durch_hundert():
    reihe = {Date(2026, 1, 31): 3.0, Date(2026, 2, 28): 4.0, Date(2026, 3, 31): 5.0}
    # (3 + 4 + 5) / 3 = 4 Prozent -> 0.04
    assert mittel_rate(reihe, Date(2025, 12, 31), Date(2026, 3, 31)) == pytest.approx(0.04)


def test_das_fenster_ist_links_offen_und_rechts_geschlossen():
    """Dasselbe Fenster wie die Indexrendite: der Basistag zaehlt nicht mit."""
    reihe = {Date(2026, 1, 31): 100.0, Date(2026, 2, 28): 2.0, Date(2026, 3, 31): 4.0}
    # Basistag 31.01. faellt heraus, 31.03. ist drin: (2 + 4) / 2 = 3 %
    assert mittel_rate(reihe, Date(2026, 1, 31), Date(2026, 3, 31)) == pytest.approx(0.03)
    # Alles nach dem Stichtag bleibt draussen.
    assert mittel_rate(reihe, Date(2026, 1, 31), Date(2026, 2, 28)) == pytest.approx(0.02)


def test_ohne_wert_im_fenster_gibt_es_None_und_keine_null():
    assert mittel_rate({}, Date(2025, 1, 1), Date(2026, 1, 1)) is None
    weit_weg = {Date(2020, 1, 2): 3.0}
    assert mittel_rate(weit_weg, Date(2025, 1, 1), Date(2026, 1, 1)) is None
    # NaN-artige Eintraege zaehlen nicht als Wert.
    assert mittel_rate({Date(2026, 1, 31): None}, Date(2025, 1, 1), ASOF) is None


# --------------------------------------------------- Zins je Waehrungsraum


def test_der_dollar_satz_kommt_aus_der_kursreihe():
    satz, quelle = riskfree_12m(
        "USD", index_series(), ASOF, irx_series=irx_reihe(3.73)
    )
    assert satz == pytest.approx(0.0373)
    assert quelle == QUELLE_US


def test_der_euro_satz_kommt_aus_der_ezb():
    reihe = {tag: 2.0 for tag in MONTH_ENDS}
    satz, quelle = riskfree_12m(
        "EUR", index_series(), ASOF, oeffner=lambda _url: ezb_csv(reihe)
    )
    assert satz == pytest.approx(0.02)
    assert quelle == QUELLE_DE


def test_das_zins_fenster_ist_das_fenster_der_indexrendite():
    """Nicht zwei Zeitraeume, sondern einer -- sonst laufen sie auseinander."""
    basis = index_12m_basis(index_series(), ASOF)
    assert basis == Date(2025, 7, 31)
    # Ein hoher Wert AM Basistag darf den Schnitt nicht anheben.
    reihe = {**{tag: 1.0 for tag in MONTH_ENDS}, basis: 99.0}
    satz, _ = riskfree_12m("USD", index_series(), ASOF, irx_series=reihe)
    assert satz == pytest.approx(0.01)


@pytest.mark.parametrize(
    "waehrung, kwargs",
    [
        ("USD", {"irx_series": {}}),
        ("EUR", {"oeffner": lambda _url: ""}),
        ("CHF", {}),  # Waehrung ohne hinterlegte Quelle
    ],
)
def test_ohne_zinsquelle_gibt_es_None_und_den_ausfalltext(waehrung, kwargs):
    satz, quelle = riskfree_12m(waehrung, index_series(), ASOF, **kwargs)
    assert satz is None
    assert quelle == QUELLE_FEHLT


def test_ohne_stichtag_im_index_bricht_nichts_ab():
    satz, quelle = riskfree_12m("USD", {}, ASOF, irx_series=irx_reihe(3.0))
    assert (satz, quelle) == (None, QUELLE_FEHLT)


# ----------------------------------------------------- Das Kriterium selbst


@pytest.fixture
def welt(tmp_path):
    """Universum und Kursbuendel des Kunst-Beispiels."""
    datei = write_universe(tmp_path / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"])
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(datei))
    universum = load_universe(datei)
    bundle = download_prices(
        list(universum.tickers),
        Date(2025, 1, 1),
        ASOF,
        downloader=make_downloader(sample_series()),
    )
    return markt, universum, bundle


def bau(welt, index, riskfree):
    markt, universum, bundle = welt
    return build_ranking(markt, universum, bundle, index, ASOF, riskfree=riskfree)


def test_der_ueberschuss_ist_rendite_minus_zins(welt):
    # Index 4000 -> 4240 ueber zwoelf Monate: genau +6 %.
    index = index_series([4000.0 + 20.0 * i for i in range(13)])
    ranking = bau(welt, index, (0.0373, QUELLE_US))
    ampel = ranking["trend_ampel"]
    assert ampel["rendite_12m"] == pytest.approx(0.06)
    assert ampel["riskfree_12m"] == pytest.approx(0.0373)
    assert ampel["ueberschuss_12m"] == pytest.approx(0.06 - 0.0373)
    assert ampel["riskfree_quelle"] == QUELLE_US
    assert ampel["warnung"] is False


def test_zwei_prozent_rendite_bei_drei_prozent_zins_ist_eine_warnung(welt):
    """Die Ziel-Mechanik des Auftrags, als Test festgenagelt."""
    # 4000 -> 4080 ueber zwoelf Monate: +2 %.
    steigt_leicht = index_series([4000.0 + (80.0 / 12.0) * i for i in range(13)])
    ranking = bau(welt, steigt_leicht, (0.03, QUELLE_US))
    ampel = ranking["trend_ampel"]
    assert ampel["rendite_12m"] > 0, "der Markt ist im Plus ..."
    assert ampel["ueberschuss_12m"] < 0, "... aber unter dem Geldmarkt"
    assert ampel["warnung"] is True
    # Ohne den Zins-Abzug haette derselbe Markt NICHT gewarnt -- genau das
    # war der Befund, der diese Aenderung ausgeloest hat.
    ohne = bau(welt, steigt_leicht, (None, QUELLE_FEHLT))
    assert ohne["trend_ampel"]["warnung"] is False


@pytest.mark.parametrize(
    "zins, warnung",
    [
        (0.0599, False),  # knapp UNTER der Rendite: kein Alarm
        (0.0600, False),  # exakt gleich: kein Ueberschuss, aber auch kein Minus
        (0.0601, True),   # knapp darueber: Warnung
    ],
)
def test_die_warnschwelle_liegt_exakt_bei_null(welt, zins, warnung):
    index = index_series([4000.0 + 20.0 * i for i in range(13)])  # +6 %
    ranking = bau(welt, index, (zins, QUELLE_US))
    assert ranking["trend_ampel"]["warnung"] is warnung


def test_ohne_zinsquelle_rechnet_das_kriterium_wie_zuvor(welt):
    """Fail-soft: kein Abzug, kein geschaetzter Zins, sichtbarer Ausfall."""
    faellt = index_series([5000.0 - 30.0 * i for i in range(13)])
    ranking = bau(welt, faellt, (None, QUELLE_FEHLT))
    ampel = ranking["trend_ampel"]
    assert ampel["riskfree_12m"] is None
    assert ampel["riskfree_quelle"] == QUELLE_FEHLT
    assert ampel["ueberschuss_12m"] == ampel["rendite_12m"]
    assert ampel["warnung"] is True

    steigt = index_series()
    assert bau(welt, steigt, (None, QUELLE_FEHLT))["trend_ampel"]["warnung"] is False


def test_der_zins_ruehrt_score_und_rangfolge_nicht_an(welt):
    """Die Ampel ist Anzeige. Sie darf die Rangliste nicht einmal streifen."""
    index = index_series()
    ohne = bau(welt, index, (None, QUELLE_FEHLT))
    mit = bau(welt, index, (0.05, QUELLE_US))
    viel = bau(welt, index, (0.99, QUELLE_US))

    assert ohne["rangliste"] == mit["rangliste"] == viel["rangliste"]
    assert ohne["top"] == mit["top"] == viel["top"]
    assert ohne["abdeckung"] == mit["abdeckung"]
    assert ohne["methode"] == mit["methode"]
    # Und der Unterschied liegt ausschliesslich in der Trend-Ampel.
    assert {k: v for k, v in ohne.items() if k != "trend_ampel"} == {
        k: v for k, v in viel.items() if k != "trend_ampel"
    }


def test_die_preisrendite_bleibt_nachlesbar(welt):
    """Additiv: das alte Feld verschwindet nicht, es bekommt Gesellschaft."""
    index = index_series()
    ampel = bau(welt, index, (0.05, QUELLE_US))["trend_ampel"]
    assert set(ampel) == {
        "index_ticker", "index_name", "rendite_12m",
        "riskfree_12m", "riskfree_quelle", "ueberschuss_12m", "warnung",
    }


# ------------------------------------------------------------- Die Anzeige


def flach(text: str) -> str:
    """Typografische Leerzeichen zu gewoehnlichen -- die Anzeige setzt
    schmale und geschuetzte Leerzeichen, geprueft wird der Wortlaut."""
    return text.replace("\u202f", " ").replace("\u00a0", " ")


def ansicht(ampel: dict) -> MarketView:
    ranking = {
        "markt": "us", "markt_name": "USA", "waehrung": "USD",
        "ranking_monat": "2026-07", "stichtag": "2026-07-31",
        "trend_ampel": ampel, "rangliste": [], "top": [],
    }
    return MarketView(
        MARKETS_BY_KEY["us"], ranking, Date(2026, 8, 3), {}, Date(2026, 8, 31)
    )


def ampel_dict(**abweichung) -> dict:
    basis = {
        "index_ticker": "^SP500TR", "index_name": "S&P 500",
        "rendite_12m": 0.181, "riskfree_12m": 0.037,
        "riskfree_quelle": QUELLE_US, "ueberschuss_12m": 0.144,
        "warnung": False,
    }
    return {**basis, **abweichung}


def test_die_box_zeigt_die_ueberschussrendite():
    html = flach(_trend_banner(ansicht(ampel_dict())))
    assert "S&amp;P 500 auf 12 Monate +14,4 % über Geldmarkt" in html
    assert ZINS_FEHLT_HINWEIS not in html


def test_die_warnbox_nennt_den_geldmarkt():
    html = flach(_trend_banner(ansicht(ampel_dict(ueberschuss_12m=-0.021, warnung=True))))
    assert "Markt unter dem Geldmarkt" in html
    assert "2,1 % über Geldmarkt" in html


def test_ohne_zins_sagt_die_box_es_sichtbar():
    html = flach(_trend_banner(
        ansicht(ampel_dict(riskfree_12m=None, riskfree_quelle=QUELLE_FEHLT,
                           ueberschuss_12m=0.181))
    ))
    assert ZINS_FEHLT_HINWEIS in html
    # Gezeigt wird dann die PREIS-Rendite, und "über Geldmarkt" faellt weg.
    assert "+18,1 %" in html
    assert "über Geldmarkt" not in html


def test_der_tacho_widerspricht_der_box_nie():
    """Der Vorlesetext der Grafik und der Satz daneben muessen dasselbe
    behaupten -- sonst steht ein Widerspruch auf der Seite."""
    mit = flach(_trend_banner(ansicht(ampel_dict(ueberschuss_12m=-0.021, warnung=True))))
    assert "Warnung: Markt unter dem Geldmarkt" in mit
    assert 'aria-label="Trend-Kriterium S&amp;P 500: ' in mit

    ohne = flach(_trend_banner(
        ansicht(ampel_dict(riskfree_12m=None, riskfree_quelle=QUELLE_FEHLT,
                           rendite_12m=-0.021, ueberschuss_12m=-0.021, warnung=True))
    ))
    assert "Warnung: Markt im 12-Monats-Minus" in ohne
    assert "unter dem Geldmarkt" not in ohne


def test_alte_eingefrorene_rankings_werden_ehrlich_angezeigt():
    """Die Juli-Rankings kennen die neuen Felder nicht. Ihre Zahl ist eine
    Preisrendite -- und genau so muss sie beschriftet sein."""
    alt = {"index_ticker": "^GSPC", "index_name": "S&P 500",
           "rendite_12m": 0.181, "warnung": False}
    wert, mit_zins = ampel_wert(alt)
    assert (wert, mit_zins) == (0.181, False)
    html = flach(_trend_banner(ansicht(alt)))
    # ... und zwar mit dem RICHTIGEN Grund: dieses Ranking hat nie eine
    # Zinsquelle gesucht, also war auch keine unerreichbar.
    assert ZINS_ALT_HINWEIS in html
    assert ZINS_FEHLT_HINWEIS not in html
    assert "über Geldmarkt" not in html


# ------------------------------------------------------ Symmetrie der Indizes


def test_beide_maerkte_messen_einen_performance_index():
    """Der DAX rechnet Dividenden ein; fuer die USA muss es der Total-Return-
    Index sein, sonst vergleicht die Ampel zwei verschiedene Dinge."""
    assert MARKETS_BY_KEY["us"].index_ticker == "^SP500TR"
    assert MARKETS_BY_KEY["de"].index_ticker == "^GDAXI"
