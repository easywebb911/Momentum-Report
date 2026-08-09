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


def ishares_csv(index: str, zeilen: int, stand: Date | None) -> str:
    kopfzeile = (
        "Emittententicker;Name;Sektor;Anlageklasse;Marktwert;Gewichtung (%);"
        "Nominalwert;Nominale;ISIN;Kurs;Standort;Boerse;Waehrung\n"
    )
    vorspann = f"Fondsposition per {stand.strftime('%d.%b%Y')}\n\n" if stand else "\n\n"
    reihen = "".join(
        f"AKT{i:03d};Firma {i};Industrie;Aktien;1.000,00;1,00;1;1;DE000{i:07d};"
        f"10,00;Deutschland;Xetra;EUR\n"
        for i in range(zeilen)
    )
    bargeld = "XEUR;EUR CASH;Bargeld;Bargeld und/oder Derivate;1,00;0,01;1;1;-;1;-;-;EUR\n"
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
    """Alle vier Quellen antworten vertragsgemaess — ohne Netz."""
    return {
        "hole_us": lambda: us_html(503),
        "hole_ishares": lambda q: ishares_csv(
            q.index_name, {"DAX": 40, "MDAX": 50, "TecDAX": 30}[q.index_name],
            Date(2026, 8, 26),
        ),
        "hole_estr": lambda: estr_csv([HEUTE - _dt.timedelta(days=1)]),
        "downloader": _kurs_stub(alle=True),
    }


def _kurs_stub(*, alle: bool):
    import pandas as pd

    def downloader(batch, start, end):
        frames = {}
        for ticker in batch:
            if not alle and ticker not in vt.TRAGENDE_REIHEN:
                continue
            frames[ticker] = pd.DataFrame(
                {"Close": [10.0], "Adj Close": [10.0], "Volume": [1000.0]},
                index=pd.DatetimeIndex([pd.Timestamp(end)]),
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
