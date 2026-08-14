"""Der Vertragstest (tools/vertragstest.py) — mit Fixtures, OHNE Netz.

Geprueft wird die VERDIKT-LOGIK je Quelle: gesund, Format-Bruch, veraltet,
leer. Dazu der Push-Baustein, der Determinismus (gleiche Fixture, gleiches
Verdikt) und der Nachweis, dass dieser Pfad nie in data/ oder docs/
schreibt.

Die Fixtures sind bewusst dieselben Formate, an denen der Universums-Lauf
haengt -- Beispiele mit deutschem Vorspann, Semikolon-Trenner und
Bargeld-Zeilen. Wer hier ein Kunstformat einsetzte, pruefte einen anderen
Vertrag als den echten.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import build_universe as bu  # noqa: E402
import vertragstest as vt  # noqa: E402

Date = _dt.date
HEUTE = Date(2026, 8, 27)  # Donnerstag, im Pruef-Fenster


# --------------------------------------------------------------------------
# Fixtures im echten Format
# --------------------------------------------------------------------------


def us_html(zeilen: int = 503, symbol_spalte: str = "Symbol") -> str:
    kopf = f"<tr><th>{symbol_spalte}</th><th>Security</th><th>GICS Sector</th></tr>"
    koerper = "".join(
        f"<tr><td>T{i:03d}</td><td>Firma {i}</td><td>Industrials</td></tr>"
        for i in range(zeilen)
    )
    return f"<html><body><table>{kopf}{koerper}</table></body></html>"


def ishares_csv(
    index: str,
    zeilen: int,
    stand: Date | None,
    *,
    kurs: str = "10,00",
    ohne_kurs_spalte: bool = False,
) -> str:
    """Eine Bestandsliste im deutschen Format.

    `kurs` setzt die Kurs-Spalte (ein String, damit auch unlesbare
    Schreibweisen pruefbar sind); `ohne_kurs_spalte` laesst sie ganz weg --
    der Fall, den der Vertragstest seit dem DE-Vergleichsgatter fangen soll.
    """
    spalten = ["Emittententicker", "Name", "Sektor", "Anlageklasse", "Marktwert",
               "Gewichtung (%)", "Nominalwert", "Nominale", "ISIN"]
    if not ohne_kurs_spalte:
        spalten.append("Kurs")
    spalten += ["Standort", "Boerse", "Waehrung"]
    kopfzeile = ";".join(spalten) + "\n"

    vorspann = f"Fondsposition per {stand.strftime('%d.%b%Y')}\n\n" if stand else "\n\n"

    def zeile(kennung, name, sektor, klasse, marktwert, gewicht, isin, preis, ort, boerse):
        felder = [kennung, name, sektor, klasse, marktwert, gewicht, "1", "1", isin]
        if not ohne_kurs_spalte:
            felder.append(preis)
        felder += [ort, boerse, "EUR"]
        return ";".join(felder) + "\n"

    reihen = "".join(
        zeile(f"AKT{i:03d}", f"Firma {i}", "Industrie", "Aktien", "1.000,00", "1,00",
              f"DE000{i:07d}", kurs, "Deutschland", "Xetra")
        for i in range(zeilen)
    )
    bargeld = zeile("XEUR", "EUR CASH", "Bargeld", "Bargeld und/oder Derivate",
                    "1,00", "0,01", "-", "1", "-", "-")
    return vorspann + kopfzeile + reihen + bargeld


def _us_ticker(i: int) -> str:
    """Rein alphabetisches Kuerzel -- echte US-Symbole tragen (anders als
    Xetra-Kuerzel wie 1COV, VOW3) keine Ziffern; US_SYMBOL_MUSTER laesst
    keine zu."""
    buchstaben = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    a, rest = divmod(i, 26 * 26)
    b, c = divmod(rest, 26)
    return buchstaben[a % 26] + buchstaben[b] + buchstaben[c]


def ishares_csv_us(
    zeilen: int, stand: Date | None, *,
    kurs: str = "10.00", ohne_kurs_spalte: bool = False, waehrung: str = "USD",
) -> str:
    """Eine US-Fonds-Bestandsliste (SXR8/IUSA) -- dieselbe Form wie
    `ishares_csv`, nur mit US-Symbolen (keine Ziffern) und USD/NASDAQ."""
    spalten = ["Ticker", "Name", "Sektor", "Anlageklasse", "Marktwert",
               "Gewichtung (%)", "Nominalwert", "Nominale", "ISIN"]
    if not ohne_kurs_spalte:
        spalten.append("Kurs")
    spalten += ["Standort", "Boerse", "Waehrung"]
    kopfzeile = ";".join(spalten) + "\n"

    vorspann = f"Fondsposition per {stand.strftime('%d.%b%Y')}\n\n" if stand else "\n\n"

    def zeile(kennung, name, sektor, klasse, marktwert, gewicht, isin, preis, ort, boerse, waehr):
        felder = [kennung, name, sektor, klasse, marktwert, gewicht, "1", "1", isin]
        if not ohne_kurs_spalte:
            felder.append(preis)
        felder += [ort, boerse, waehr]
        return ";".join(felder) + "\n"

    reihen = "".join(
        zeile(_us_ticker(i), f"Firma {i}", "Industrials", "Equity", "1.000,00", "1,00",
              f"US{i:09d}", kurs, "USA", "NASDAQ", waehrung)
        for i in range(zeilen)
    )
    bargeld = zeile("XUSD", "USD CASH", "Bargeld", "Bargeld und/oder Derivate",
                    "1,00", "0,01", "-", "1", "-", "-", waehrung)
    return vorspann + kopfzeile + reihen + bargeld


def estr_csv(taege: list[Date]) -> str:
    kopf = "KEY,FREQ,REF_AREA,PROVIDER_FM_ID,TIME_PERIOD,OBS_VALUE,OBS_STATUS"
    zeilen = [
        f"EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,{t.isoformat()},2.185,A" for t in taege
    ]
    return "\n".join([kopf, *zeilen]) + "\n"


# --------------------------------------------------------- 1. Wikipedia / US


def test_us_gesund():
    v = vt.pruefe_us_tabelle(us_html(503))
    assert v.ok and "503" in v.befund


def test_us_format_bruch_ist_rot():
    """Die Symbol-Spalte heisst ploetzlich anders — genau der Bruch, an dem
    der Universums-Lauf abbraeche."""
    v = vt.pruefe_us_tabelle(us_html(503, symbol_spalte="Kuerzel"))
    assert not v.ok
    assert "erwartet" in v.befund and "vorgefunden" in v.befund


def test_us_anzahl_ausserhalb_ist_rot():
    """Halbe Tabelle geliefert: parsebar, aber unplausibel."""
    v = vt.pruefe_us_tabelle(us_html(250))
    assert not v.ok and "250" in v.befund


def test_us_leer_ist_rot():
    assert not vt.pruefe_us_tabelle("<html><body></body></html>").ok


def test_die_tabellenlose_seite_ergibt_ein_sauberes_verdikt():
    """Dieselbe Fixture, die den Parser frueher mit einer nackten
    Bibliotheks-Ausnahme verlassen liess (#24-Nebenbefund, behoben): Sie
    muss ein ordentliches Verdikt ergeben -- und die Begruendung darf nicht
    auf ein fehlendes Paket zeigen."""
    v = vt.pruefe_us_tabelle("<html><body><p>Nur Text</p></body></html>")
    assert not v.ok
    assert "QuelleUnbrauchbar" in v.befund, "der Parser lehnt jetzt sauber ab"
    assert "html5lib" not in v.befund
    # Und der Push-Text traegt es weiter, mit Handreichung.
    text = vt.bericht([v], HEUTE)
    assert "Wikipedia S&P 500" in text and "Was tun:" in text


# ------------------------------------------------------------- 2. iShares


@pytest.fixture
def dax():
    return next(q for q in bu.ISHARES_DE if q.index_name == "DAX")


def test_ishares_gesund(dax):
    v = vt.pruefe_ishares(ishares_csv("DAX", 40, Date(2026, 8, 26)), dax, HEUTE)
    assert v.ok and "40 Aktien-Zeilen" in v.befund


def test_ishares_veraltet_ist_rot(dax):
    """Das VERALTUNGS-GATTER, mit dem echten Gatter geprueft."""
    v = vt.pruefe_ishares(ishares_csv("DAX", 40, Date(2026, 7, 1)), dax, HEUTE)
    assert not v.ok and "Handelstage alt" in v.befund


def test_ishares_ohne_stichtag_ist_rot(dax):
    v = vt.pruefe_ishares(ishares_csv("DAX", 40, None), dax, HEUTE)
    assert not v.ok and "Stichtag" in v.befund


def test_ishares_falsche_anzahl_ist_rot(dax):
    """Vertauschte URL: 50 Zeilen unter der DAX-Adresse — das ANZAHL-GATTER
    nennt sogar den vermuteten Index."""
    v = vt.pruefe_ishares(ishares_csv("DAX", 50, Date(2026, 8, 26)), dax, HEUTE)
    assert not v.ok and "MDAX" in v.befund


def test_ishares_leer_ist_rot(dax):
    """Der real beobachtete Wochenend-Zustand: Stichtag '-', keine Zeilen.
    Er MUSS rot sein — deshalb laeuft der Workflow nur werktags, statt das
    Verdikt weichzuspuelen."""
    v = vt.pruefe_ishares(ishares_csv("DAX", 0, None), dax, HEUTE)
    assert not v.ok


# ------------------------------------------------- 2b. Die Kurs-Spalte
#
# Seit dem DE-Vergleichsgatter ist sie tragend: ohne sie gibt es am
# Stichtag keine zweite Meinung. Sie hier zu pruefen ist genau der Zweck
# dieses Tests -- der Ausfall wird angekuendigt statt am Stichtag entdeckt.


def test_ishares_ohne_kurs_spalte_ist_rot(dax):
    v = vt.pruefe_ishares(
        ishares_csv("DAX", 40, Date(2026, 8, 26), ohne_kurs_spalte=True), dax, HEUTE
    )
    assert not v.ok
    assert "Kurs" in v.vertrag
    assert "0 von 40" in v.befund


def test_ishares_mit_unlesbarer_zahlenschreibweise_ist_rot(dax):
    """"1,234" ist im deutschen Format 1,234 und im englischen 1234. Der
    Parser raet nicht — und der Vertragstest meldet, dass er nicht kann."""
    v = vt.pruefe_ishares(
        ishares_csv("DAX", 40, Date(2026, 8, 26), kurs="1,234"), dax, HEUTE
    )
    assert not v.ok
    assert "NICHT eindeutig" in v.befund


def test_ishares_gesund_zaehlt_die_kurse_mit(dax):
    v = vt.pruefe_ishares(ishares_csv("DAX", 40, Date(2026, 8, 26)), dax, HEUTE)
    assert v.ok and "40 Kurse" in v.befund


def test_ein_einzelner_titel_ohne_kurs_bricht_den_vertrag_nicht(dax):
    """Eine ausgesetzte Position darf keinen Alarm ausloesen — der Vertrag
    haengt an der SPALTE, nicht an jeder einzelnen Zelle."""
    csv = ishares_csv("DAX", 40, Date(2026, 8, 26))
    csv = csv.replace(";10,00;Deutschland;Xetra;EUR\n", ";-;Deutschland;Xetra;EUR\n", 1)
    v = vt.pruefe_ishares(csv, dax, HEUTE)
    assert v.ok and "39 Kurse" in v.befund


# ---------------------------------------------------------- 3. Kursquelle


def test_kurse_gesund():
    geliefert = set(vt.TRAGENDE_REIHEN) | {"AAPL", "MSFT", "JNJ", "SAP.DE", "SIE.DE", "ALV.DE"}
    verdikte = vt.pruefe_kurse(geliefert)
    assert all(v.ok for v in verdikte)


def test_eine_fehlende_tragende_reihe_ist_rot():
    """Ohne ^GDAXI gibt es fuer Deutschland keinen Handelskalender — jede
    einzelne tragende Reihe zaehlt."""
    geliefert = set(vt.TRAGENDE_REIHEN) - {"^GDAXI"}
    tragend = [v for v in vt.pruefe_kurse(geliefert) if "Index- und Zins" in v.vertrag]
    assert len(tragend) == 1 and not tragend[0].ok
    assert "^GDAXI" in tragend[0].befund


def test_ein_einzelner_ausfall_in_der_stichprobe_ist_kein_bruch():
    """Die Stichprobe prueft das FORMAT, nicht die einzelne Firma. Ein
    umbenannter Titel darf keinen Fehlalarm ausloesen."""
    geliefert = set(vt.TRAGENDE_REIHEN) | {"AAPL", "MSFT", "SAP.DE", "SIE.DE"}
    assert all(v.ok for v in vt.pruefe_kurse(geliefert))


def test_wenn_die_stichprobe_verstummt_ist_es_rot():
    """Liefert kein einziger Titel mehr, ist es kein Einzelfall."""
    us = [v for v in vt.pruefe_kurse(set(vt.TRAGENDE_REIHEN)) if v.quelle.endswith("US")]
    assert len(us) == 1 and not us[0].ok


# --------------------------------------------------------------- 4. EZB


def test_estr_gesund():
    v = vt.pruefe_estr(estr_csv([HEUTE - _dt.timedelta(days=1)]), HEUTE)
    assert v.ok


def test_estr_veraltet_ist_rot():
    v = vt.pruefe_estr(estr_csv([HEUTE - _dt.timedelta(days=30)]), HEUTE)
    assert not v.ok and "Handelstage alt" in v.befund


def test_estr_ohne_kopfzeile_ist_rot():
    ohne = "EST.B.EU000A2X2A25.WT,B,EU000A2X2A25,WT,2026-08-26,2.185,A\n"
    assert not vt.pruefe_estr(ohne, HEUTE).ok


def test_estr_leer_ist_rot():
    assert not vt.pruefe_estr("", HEUTE).ok


# ------------------------------------------------------ Bericht und Lauf


def test_der_bericht_nennt_quelle_bruch_und_handreichung():
    verdikte = [
        vt.pruefe_us_tabelle(us_html(503)),
        vt.pruefe_estr("", HEUTE),
    ]
    text = vt.bericht(verdikte, HEUTE)
    assert "1 von 2 Vertraegen gebrochen" in text
    assert "EZB €STR" in text
    assert "Was tun:" in text and "riskfree.py" in text
    # Die gesunde Quelle taucht im Push NICHT auf -- er soll den Bruch
    # zeigen, nicht eine Bestandsliste.
    assert "Wikipedia" not in text


def test_der_bericht_ist_deterministisch():
    """Gleiche Verdikte, gleicher Text — keine Uhrzeit, keine Reihenfolge
    aus einer Menge."""
    verdikte = [vt.pruefe_estr("", HEUTE), vt.pruefe_us_tabelle(us_html(1))]
    a = vt.bericht(verdikte, HEUTE)
    b = vt.bericht(verdikte, HEUTE)
    assert a == b
    assert hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()


def gesunde_naehte():
    """Alle fuenf Quellen antworten vertragsgemaess — ohne Netz."""
    groessen = {"DAX": 40, "MDAX": 50, "TecDAX": 30}
    return {
        "hole_us": lambda: us_html(503),
        "hole_ishares": lambda q: (
            ishares_csv_us(504, Date(2026, 8, 26))
            if q.index_name in ("SXR8", "IUSA")
            else ishares_csv(q.index_name, groessen[q.index_name], Date(2026, 8, 26))
        ),
        "hole_estr": lambda: estr_csv([HEUTE - _dt.timedelta(days=1)]),
        "downloader": _kurs_stub(alle=True),
        "splits_oeffner": lambda ticker: {},
    }


def _kurs_stub(*, alle: bool, close: float = 10.0):
    """Kursquelle ohne Netz.

    Sie liefert das gesamte angefragte Fenster und nicht nur den letzten
    Tag: der Kursvergleich braucht den Kurs am STICHTAG DER BESTANDSLISTE,
    und der liegt regelmaessig ein bis zwei Handelstage vor dem Lauftag.
    Mit einer Ein-Tages-Reihe waere der Vergleich in jedem Test still
    "nicht moeglich" -- also nie wirklich geprueft.
    """
    import pandas as pd

    def downloader(batch, start, end):
        tage = [start + _dt.timedelta(days=i) for i in range((end - start).days + 1)]
        frames = {}
        for ticker in batch:
            if not alle and ticker not in vt.TRAGENDE_REIHEN:
                continue
            frames[ticker] = pd.DataFrame(
                {
                    "Close": [close] * len(tage),
                    "Adj Close": [close] * len(tage),
                    "Volume": [1000.0] * len(tage),
                },
                index=pd.DatetimeIndex([pd.Timestamp(d) for d in tage]),
            )
        if not frames:
            return pd.DataFrame()
        if len(batch) == 1 and batch[0] in frames:
            return frames[batch[0]]
        return pd.concat(frames, axis=1)

    return downloader


def test_im_normalfall_kein_push_und_exit_null(capsys):
    """STILL im Normalfall — die Waechter-Philosophie, kein Herzschlag."""
    gerufen = []
    code = vt.main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda text: gerufen.append(text) or True,
        **gesunde_naehte(),
    )
    assert code == 0
    assert gerufen == [], "der Vertragstest hat ohne Bruch gefunkt"
    assert "Kein Push" in capsys.readouterr().out


def test_bei_bruch_genau_ein_push_und_exit_eins():
    """Mehrere Brueche, EIN Push — kein Push-Gewitter."""
    naehte = gesunde_naehte()
    naehte["hole_us"] = lambda: "<html></html>"
    naehte["hole_estr"] = lambda: ""
    gerufen = []
    code = vt.main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda text: gerufen.append(text) or True,
        **naehte,
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "Wikipedia" in gerufen[0] and "EZB" in gerufen[0]


def test_auch_ein_gescheiterter_push_laesst_den_lauf_rot_enden():
    naehte = gesunde_naehte()
    naehte["hole_estr"] = lambda: ""
    assert vt.main(["--heute", HEUTE.isoformat()], melder=lambda _t: False, **naehte) == 1


def test_der_kursvergleich_wird_vor_dem_stichtag_mitgeprueft():
    """Der ganze Sinn: Widersprechen sich die beiden Kursquellen, erfaehrt
    man es am 27. — nicht am 31., wenn kein Ranking mehr entsteht."""
    verdikte = vt.sammle_verdikte(HEUTE, **gesunde_naehte())
    vergleich = [v for v in verdikte if v.quelle == "Kursvergleich DE"]
    assert len(vergleich) == 1, "der Kursvergleich fehlt in der Pruefliste"
    assert vergleich[0].ok
    assert "Titel verglichen" in vergleich[0].befund
    assert "0 ueber der Toleranz" in vergleich[0].befund


def test_ein_widerspruch_zwischen_den_kursquellen_ist_rot():
    """Bestandsliste sagt 10,00, die Kursquelle sagt 20,00 — bei jedem
    Titel. Genau der Fall, der den Stichtag verweigern wuerde."""
    naehte = gesunde_naehte()
    naehte["downloader"] = _kurs_stub(alle=True, close=20.0)
    verdikte = vt.sammle_verdikte(HEUTE, **naehte)
    vergleich = next(v for v in verdikte if v.quelle == "Kursvergleich DE")
    assert not vergleich.ok
    assert "iShares 10.0000 vs. Kursquelle 20.0000" in vergleich.befund
    # Und die Handreichung nennt den Notausgang.
    assert "ohne_kursvergleich" in vt.handreichung("Kursvergleich DE")


def test_ein_nicht_moeglicher_vergleich_ist_kein_bruch():
    """Fehlt die Kurs-Spalte, ist das ein Bruch der EINZELNEN Datei (oben
    geprueft) — der Vergleich selbst meldet dann "nicht durchfuehrbar" und
    nicht "die Quellen widersprechen sich". Zwei verschiedene Aussagen."""
    naehte = gesunde_naehte()
    naehte["hole_ishares"] = lambda q: (
        ishares_csv_us(504, Date(2026, 8, 26), ohne_kurs_spalte=True)
        if q.index_name in ("SXR8", "IUSA")
        else ishares_csv(
            q.index_name, {"DAX": 40, "MDAX": 50, "TecDAX": 30}[q.index_name],
            Date(2026, 8, 26), ohne_kurs_spalte=True,
        )
    )
    verdikte = vt.sammle_verdikte(HEUTE, **naehte)
    vergleich = next(v for v in verdikte if v.quelle == "Kursvergleich DE")
    assert vergleich.ok
    assert "nicht durchfuehrbar" in vergleich.befund
    # Derselbe Fall, US-Seite: SXR8 parst trotzdem (es fehlt nur die
    # Kurs-Spalte, nicht der Ticker) -- der Vergleich meldet ebenfalls
    # "nicht durchfuehrbar", nicht "die Quellen widersprechen sich".
    vergleich_us = next(v for v in verdikte if v.quelle == "Kursvergleich US")
    assert vergleich_us.ok
    assert "nicht durchfuehrbar" in vergleich_us.befund


def test_die_bestandslisten_werden_genau_einmal_geholt():
    """Zwei Abrufe derselben Datei koennten zwei verschiedene Staende
    erwischen — dann verglichen wir gegen etwas, das wir nie geprueft haben."""
    naehte = gesunde_naehte()
    gerufen = []
    echt = naehte["hole_ishares"]

    def zaehlend(quelle):
        gerufen.append(quelle.index_name)
        return echt(quelle)

    naehte["hole_ishares"] = zaehlend
    vt.sammle_verdikte(HEUTE, **naehte)
    assert gerufen == ["DAX", "MDAX", "TecDAX", "SXR8", "IUSA"]


def test_ein_abrufaussetzer_ist_selbst_ein_bruch():
    """Eine Quelle, die nicht antwortet, haelt ihren Vertrag nicht."""
    naehte = gesunde_naehte()

    def kaputt():
        raise OSError("Name or service not known")

    naehte["hole_us"] = kaputt
    verdikte = vt.sammle_verdikte(HEUTE, **naehte)
    us = [v for v in verdikte if v.quelle.startswith("Wikipedia")]
    assert len(us) == 1 and not us[0].ok and "OSError" in us[0].befund


# --------------------------------------------------- Schreibt nichts, nie


def abdruck(wurzel: Path) -> dict[str, str]:
    return {
        str(p.relative_to(wurzel)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(wurzel.rglob("*"))
        if p.is_file()
    }


def test_der_vertragstest_schreibt_weder_in_data_noch_in_docs():
    vorher = (abdruck(Path("data")), abdruck(Path("docs")))
    vt.main(["--heute", HEUTE.isoformat()], melder=lambda _t: True, **gesunde_naehte())
    naehte = gesunde_naehte()
    naehte["hole_estr"] = lambda: ""
    vt.main(["--heute", HEUTE.isoformat()], melder=lambda _t: True, **naehte)
    assert (abdruck(Path("data")), abdruck(Path("docs"))) == vorher


# ------------------------------------------- Das Fenster deckt den Stichtag


def test_der_stichtag_liegt_immer_im_pruef_fenster():
    """Der Zeitplan laeuft am 25.-31.; der Monats-Stichtag ist der letzte
    WERKTAG des Monats. Diese beiden muessen zusammenpassen, sonst kuendigt
    der Test nichts an. Nachgerechnet ueber 25 Jahre statt behauptet.
    """
    from momentum.render import last_weekday_of_month

    for jahr in range(2026, 2051):
        for monat in range(1, 13):
            stichtag = last_weekday_of_month(jahr, monat)
            assert stichtag.day >= 25, f"{jahr}-{monat}: Stichtag am {stichtag.day}."
            assert stichtag.weekday() < 5


def test_august_2026_die_konkrete_abdeckung():
    """Der naechste scharfe Stichtag: Montag, 31.08.2026."""
    from momentum.render import last_weekday_of_month

    stichtag = last_weekday_of_month(2026, 8)
    assert stichtag == Date(2026, 8, 31) and stichtag.weekday() == 0
    laeufe = [
        Date(2026, 8, t) for t in range(25, 32)
        if Date(2026, 8, t).weekday() < 5
    ]
    # Fuenf Laeufe: Di 25., Mi 26., Do 27., Fr 28. und der Stichtag selbst.
    assert laeufe == [Date(2026, 8, t) for t in (25, 26, 27, 28, 31)]
    assert stichtag in laeufe


# ------------------------------------------------------------ Der Workflow


def test_der_workflow_kann_nicht_schreiben_und_faellt_nicht_auf_die_cron_falle():
    import yaml

    pfad = Path(".github/workflows/vertrag.yml")
    text = pfad.read_text(encoding="utf-8")
    daten = yaml.safe_load(text)

    assert daten["permissions"] == {"contents": "read"}
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "workflow_dispatch" in ausloeser

    # DIE FALLE: cron verknuepft Tag-des-Monats und Wochentag mit ODER,
    # sobald beide gesetzt sind. Im Zeitplan darf deshalb NUR der
    # Tag-des-Monats stehen; der Wochentag gehoert in den Riegel.
    (plan,) = ausloeser["schedule"]
    felder = plan["cron"].split()
    assert felder[2] == "25-31", "Tag-des-Monats-Fenster fehlt"
    assert felder[4] == "*", "Wochentag im cron gesetzt — das waere ein ODER!"
    assert "date -u +%u" in text, "Wochentag-Riegel fehlt"

    # Und der Riegel muss jeden inhaltlichen Schritt bewachen.
    (job,) = daten["jobs"].values()
    schritte = [s for s in job["steps"] if s.get("id") != "riegel"]
    assert schritte and all(
        s.get("if") == "steps.riegel.outputs.laufen == 'ja'" for s in schritte
    )
