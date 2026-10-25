"""Der Daten-Abdeckungs-Wächter (datenabdeckung_waechter.py) — geprueft
ohne echtes Git (die Test-Naht `laeufer`/`ermittle_datenlage` ersetzt
jeden Zugriff), ohne Netz.

Kernaussagen: (A) Kursabruf und (B) iShares-Kursvergleich warnen nur,
wenn ALLE auswertbaren Laeufe eines Fensters schlecht waren UND
mindestens MINDEST_BEOBACHTUNGEN davon vorliegen -- ein einzelner
schlechter Lauf allein ist noch kein Befund. (C) Universum-Alter und
Sektor-Abdeckung werten den aktuellen Stand direkt aus. Der Push kommt
AUSSCHLIESSLICH beim Uebergang gesund->Warnung oder bei einer faelligen
woechentlichen Erinnerung -- beides ZUSTANDSLOS aus derselben Historie
berechnet, ohne jede Persistenz. Und: MELDEN, NIE HANDELN -- dieses
Modul schreibt nirgends.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest
import yaml

from momentum.datenabdeckung_waechter import (
    ERINNERUNG_TAGE,
    FENSTER_STUNDEN_KURSABRUF,
    FENSTER_TAGE_KURSVERGLEICH,
    MINDEST_BEOBACHTUNGEN,
    PRAKTISCH_KEINE_ANTEIL,
    UNIVERSUM_WARNSCHWELLE_TAGE,
    Datenlage,
    _git_log,
    _git_show,
    _historie_json,
    ermittle_datenlage,
    ermittle_signale,
    faellige_bloecke,
    fehlende_sektoren_anzahl,
    kursabruf_ist_praktisch_leer,
    kursabruf_warnung_zum_zeitpunkt,
    kursvergleich_ist_abgelehnt,
    kursvergleich_warnung_zum_zeitpunkt,
    main,
    push_ist_faellig,
    sektor_warnung_zum_zeitpunkt,
    tage_in_warnung_davor,
    universum_alter_warnung_zum_tag,
    universum_stand_lesen,
)

UTC = _dt.timezone.utc


def dt(s: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(s).replace(tzinfo=UTC)


def status(markt: str, *, daten: dict | None = None, kursvergleich: dict | None = None) -> dict:
    eintrag = {"markt": markt}
    if daten is not None:
        eintrag["daten"] = daten
    if kursvergleich is not None:
        eintrag["kursvergleich"] = kursvergleich
    return {"maerkte": [eintrag]}


def daten(angefragt: int, geliefert: int) -> dict:
    return {"angefragt": angefragt, "geliefert": geliefert}


# ------------------------------------------------------- Pruefung A: Kursabruf


def test_kursabruf_praktisch_leer_bei_null_geliefert():
    assert kursabruf_ist_praktisch_leer(daten(503, 0)) is True


def test_kursabruf_praktisch_leer_unterhalb_der_toleranz():
    # 1% von 503 liefert noch Praktisch-keine, 50% nicht.
    assert kursabruf_ist_praktisch_leer(daten(503, 5)) is True
    assert kursabruf_ist_praktisch_leer(daten(503, 250)) is False


def test_kursabruf_nichts_angefragt_ist_kein_befund_dieses_moduls():
    assert kursabruf_ist_praktisch_leer(daten(0, 0)) is False


def test_kursabruf_gesund_bei_mehreren_guten_laeufen():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T22:00:00"), status("us", daten=daten(503, 503))),
        (dt("2026-10-25T05:00:00"), status("us", daten=daten(503, 500))),
    ]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is False


def test_kursabruf_warnung_wenn_alle_laeufe_im_fenster_leer():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T22:00:00"), status("us", daten=daten(503, 0))),
        (dt("2026-10-25T05:00:00"), status("us", daten=daten(503, 2))),
    ]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is True


def test_kursabruf_ein_einzelner_leerer_lauf_loest_keine_warnung_aus():
    """MINDEST_BEOBACHTUNGEN verlangt mehr als einen Lauf -- ein
    einzelner schlechter Lauf ist Rauschen, kein Befund."""
    assert MINDEST_BEOBACHTUNGEN >= 2
    bezug = dt("2026-10-25T06:00:00")
    historie = [(dt("2026-10-25T05:00:00"), status("us", daten=daten(503, 0)))]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is None


def test_kursabruf_historie_zu_kurz_oder_datei_fehlt_ist_fail_soft():
    bezug = dt("2026-10-25T06:00:00")
    assert kursabruf_warnung_zum_zeitpunkt(bezug, [], "us") is None


def test_kursabruf_laeufe_ausserhalb_des_fensters_zaehlen_nicht():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-20T06:00:00"), status("us", daten=daten(503, 0))),
        (dt("2026-10-21T06:00:00"), status("us", daten=daten(503, 0))),
    ]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is None


def test_kursabruf_ein_guter_lauf_unter_mehreren_schlechten_verhindert_warnung():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T20:00:00"), status("us", daten=daten(503, 0))),
        (dt("2026-10-25T02:00:00"), status("us", daten=daten(503, 0))),
        (dt("2026-10-25T05:00:00"), status("us", daten=daten(503, 480))),
    ]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is False


def test_kursabruf_andere_maerkte_werden_nicht_vermischt():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T22:00:00"), status("de", daten=daten(102, 0))),
        (dt("2026-10-25T05:00:00"), status("de", daten=daten(102, 0))),
    ]
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "us") is None
    assert kursabruf_warnung_zum_zeitpunkt(bezug, historie, "de") is True


def test_fenster_stunden_kursabruf_startwert():
    assert FENSTER_STUNDEN_KURSABRUF == 24.0
    assert PRAKTISCH_KEINE_ANTEIL == 0.02


# ------------------------------------------------ Pruefung B: Kursvergleich


def test_kursvergleich_abgelehnt_bei_entfallen_und_verweigert():
    assert kursvergleich_ist_abgelehnt({"verdikt": "entfallen"}) is True
    assert kursvergleich_ist_abgelehnt({"verdikt": "verweigert"}) is True
    assert kursvergleich_ist_abgelehnt({"verdikt": "ok"}) is False


def test_kursvergleich_laeufe_ohne_das_feld_zaehlen_nicht_mit():
    """Ein gewoehnlicher Anzeige-Lauf-Tag ohne 'kursvergleich'-Feld ist
    KEIN Treffer -- weder gut noch schlecht, einfach nicht auswertbar
    fuer diese Pruefung (siehe Modul-Docstring)."""
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T06:00:00"), status("us", daten=daten(503, 503))),
        (dt("2026-10-25T06:00:00"), status("us", daten=daten(503, 503))),
    ]
    assert kursvergleich_warnung_zum_zeitpunkt(bezug, historie, "us") is None


def test_kursvergleich_warnung_bei_zwei_abgelehnten_laeufen_im_fenster():
    bezug = dt("2026-10-02T00:00:00")
    historie = [
        (dt("2026-09-30T00:00:00"), status("us", kursvergleich={"verdikt": "entfallen"})),
        (dt("2026-10-01T00:00:00"), status("us", kursvergleich={"verdikt": "verweigert"})),
    ]
    assert kursvergleich_warnung_zum_zeitpunkt(bezug, historie, "us") is True


def test_kursvergleich_ein_einzelner_abgelehnter_lauf_loest_keine_warnung_aus():
    bezug = dt("2026-10-02T00:00:00")
    historie = [(dt("2026-10-01T00:00:00"), status("us", kursvergleich={"verdikt": "entfallen"}))]
    assert kursvergleich_warnung_zum_zeitpunkt(bezug, historie, "us") is None


def test_kursvergleich_gesund_wenn_mindestens_ein_lauf_ok_war():
    bezug = dt("2026-10-02T00:00:00")
    historie = [
        (dt("2026-08-31T00:00:00"), status("us", kursvergleich={"verdikt": "ok"})),
        (dt("2026-10-01T00:00:00"), status("us", kursvergleich={"verdikt": "entfallen"})),
    ]
    # Ausserhalb eines 7-Tage-Fensters ist der August-Lauf gar nicht
    # auswertbar -- hier bewusst beide INNERHALB eines weiten Fensters.
    assert kursvergleich_warnung_zum_zeitpunkt(
        bezug, historie, "us", fenster_tage=60
    ) is False


def test_kursvergleich_historie_zu_kurz_oder_datei_fehlt_ist_fail_soft():
    bezug = dt("2026-10-02T00:00:00")
    assert kursvergleich_warnung_zum_zeitpunkt(bezug, [], "us") is None


def test_fenster_tage_kursvergleich_startwert():
    assert FENSTER_TAGE_KURSVERGLEICH == 7


# --------------------------------------------- Pruefung C: Universum-Alter


def test_universum_alter_exakt_an_der_grenze():
    stand = _dt.date(2026, 1, 1)
    genau_an_schwelle = stand + _dt.timedelta(days=UNIVERSUM_WARNSCHWELLE_TAGE)
    einen_tag_darueber = genau_an_schwelle + _dt.timedelta(days=1)
    assert universum_alter_warnung_zum_tag(genau_an_schwelle, stand) is False
    assert universum_alter_warnung_zum_tag(einen_tag_darueber, stand) is True


def test_universum_stand_lesen(tmp_path):
    pfad = tmp_path / "universum_us.txt"
    pfad.write_text("# Universum: S&P 500\n# Stand: 2026-08-03\nAAPL\n", encoding="utf-8")
    assert universum_stand_lesen(pfad) == _dt.date(2026, 8, 3)


def test_universum_stand_ohne_kopfzeile_wirft(tmp_path):
    pfad = tmp_path / "universum_us.txt"
    pfad.write_text("AAPL\n", encoding="utf-8")
    with pytest.raises(ValueError):
        universum_stand_lesen(pfad)


# --------------------------------------------- Pruefung C: Sektor-Abdeckung


def test_fehlende_sektoren_anzahl_null_vs_mehr():
    voll = {"AAPL": {"sektor": "Tech"}, "ABBV": {"sektor": "Health"}}
    assert fehlende_sektoren_anzahl(voll) == 0
    luecke = {"AAPL": {"sektor": "Tech"}, "ABBV": {"sektor": ""}, "XYZ": {}}
    assert fehlende_sektoren_anzahl(luecke) == 2


def test_sektor_warnung_null_vs_mehr_als_null():
    bezug = dt("2026-10-25T06:00:00")
    gesund = [(dt("2026-08-18T21:56:00"), {"AAPL": {"sektor": "Tech"}})]
    assert sektor_warnung_zum_zeitpunkt(bezug, gesund) is False
    kaputt = [(dt("2026-08-18T21:56:00"), {"AAPL": {"sektor": ""}})]
    assert sektor_warnung_zum_zeitpunkt(bezug, kaputt) is True


def test_sektor_warnung_ohne_jeden_commit_ist_fail_soft():
    bezug = dt("2026-10-25T06:00:00")
    assert sektor_warnung_zum_zeitpunkt(bezug, []) is None


def test_sektor_warnung_nimmt_den_juengsten_commit_bis_bezug():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-08-18T21:56:00"), {"AAPL": {"sektor": ""}}),
        (dt("2026-10-01T00:00:00"), {"AAPL": {"sektor": "Tech"}}),
    ]
    assert sektor_warnung_zum_zeitpunkt(bezug, historie) is False
    # Ein Bezugszeitpunkt VOR der Korrektur sieht noch die Luecke.
    assert sektor_warnung_zum_zeitpunkt(dt("2026-09-01T00:00:00"), historie) is True


# ---------------------------------------------- Uebergang und Erinnerung


def test_tage_in_warnung_davor_null_beim_uebergang():
    def ist_warnung(punkt):
        return punkt >= dt("2026-10-25T00:00:00")

    assert tage_in_warnung_davor(ist_warnung, dt("2026-10-25T06:00:00")) == 0


def test_tage_in_warnung_davor_zaehlt_anhaltende_tage():
    beginn = dt("2026-10-18T00:00:00")

    def ist_warnung(punkt):
        return punkt >= beginn

    # 25.10. minus 18.10. = 7 Tage VOR dem 25.10. waren bereits Warnung.
    assert tage_in_warnung_davor(ist_warnung, dt("2026-10-25T06:00:00")) == 7


def test_tage_in_warnung_davor_bricht_an_der_obergrenze_ab():
    def immer_warnung(_punkt):
        return True

    ergebnis = tage_in_warnung_davor(immer_warnung, dt("2026-10-25T06:00:00"), max_tage=5)
    assert ergebnis == 5


def test_push_ist_faellig_nur_beim_uebergang_oder_an_der_erinnerung():
    assert push_ist_faellig(True, 0) is True
    for tag in range(1, ERINNERUNG_TAGE):
        assert push_ist_faellig(True, tag) is False
    assert push_ist_faellig(True, ERINNERUNG_TAGE) is True
    assert push_ist_faellig(True, 2 * ERINNERUNG_TAGE) is True
    assert push_ist_faellig(False, 0) is False


def test_erinnerung_tage_startwert():
    assert ERINNERUNG_TAGE == 7


# --------------------------------------------------------- ermittle_signale


def _datenlage(*, status_historie=None, ticker_meta_us=None, ticker_meta_de=None, stand_us=None, stand_de=None):
    return Datenlage(
        status_historie=status_historie or [],
        ticker_meta_historie={
            "us": ticker_meta_us or [(dt("2026-08-18T00:00:00"), {"AAPL": {"sektor": "Tech"}})],
            "de": ticker_meta_de or [(dt("2026-08-18T00:00:00"), {"SAP.DE": {"sektor": "Tech"}})],
        },
        universum_stand={
            "us": stand_us or _dt.date(2026, 8, 3),
            "de": stand_de or _dt.date(2026, 8, 3),
        },
    )


def test_ermittle_signale_alles_gesund_ergibt_keine_faelligen_bloecke():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (dt("2026-10-24T05:00:00"), {"maerkte": [status("us", daten=daten(503, 500))["maerkte"][0], status("de", daten=daten(102, 100))["maerkte"][0]]}),
        (dt("2026-10-25T05:00:00"), {"maerkte": [status("us", daten=daten(503, 500))["maerkte"][0], status("de", daten=daten(102, 100))["maerkte"][0]]}),
    ]
    datenlage = _datenlage(status_historie=historie)
    signale = ermittle_signale(datenlage, bezug)
    assert faellige_bloecke(signale) == []


def test_ermittle_signale_frischer_uebergang_erzeugt_einen_block_mit_zahlen():
    bezug = dt("2026-10-25T06:00:00")
    # Beide schlechten Laeufe liegen bewusst INNERHALB der letzten 24
    # Stunden vor bezug -- das Fenster einen Tag frueher (bezug - 1 Tag)
    # sieht dagegen NULL Laeufe, ist also nicht auswertbar: genau der
    # UEBERGANG, den dieser Test nachweisen soll.
    historie = [
        (bezug - _dt.timedelta(hours=20), status("us", daten=daten(503, 0))),
        (bezug - _dt.timedelta(hours=4), status("us", daten=daten(503, 0))),
    ]
    datenlage = _datenlage(status_historie=historie)
    signale = ermittle_signale(datenlage, bezug)
    bloecke = faellige_bloecke(signale)
    [(name, text)] = [b for b in bloecke if b[0] == "Kursabruf US"]
    assert "US" in text
    assert "24" in text


def test_ermittle_signale_universum_alt_erzeugt_befund():
    # GENAU ein Tag nach dem Ueberschreiten der Schwelle: ein frischer
    # Uebergang (anhaltend_seit == 0), nicht erst mehrere Tage spaeter.
    stand = _dt.date(2026, 1, 1)
    bezug_tag = stand + _dt.timedelta(days=UNIVERSUM_WARNSCHWELLE_TAGE + 1)
    bezug = _dt.datetime.combine(bezug_tag, _dt.time(6, 0), tzinfo=UTC)
    datenlage = _datenlage(stand_us=stand, stand_de=stand)
    signale = ermittle_signale(datenlage, bezug)
    namen = [n for n, _ in faellige_bloecke(signale)]
    assert "Universum-Alter US" in namen
    assert "Universum-Alter DE" in namen


def test_ermittle_signale_sektor_luecke_erzeugt_befund():
    bezug = dt("2026-10-25T06:00:00")
    # Commit-Zeit knapp VOR bezug: ein Tag frueher (bezug - 1 Tag) findet
    # noch keinen Commit -- nicht auswertbar, also der UEBERGANG.
    datenlage = _datenlage(
        ticker_meta_us=[(bezug - _dt.timedelta(hours=1), {"AAPL": {"sektor": ""}})]
    )
    signale = ermittle_signale(datenlage, bezug)
    namen = [n for n, _ in faellige_bloecke(signale)]
    assert "Sektor-Abdeckung US" in namen
    assert "Sektor-Abdeckung DE" not in namen


# ---------------------------------------------------------------- main()


def test_main_still_und_gruen_wenn_alles_gesund():
    bezug = dt("2026-10-25T06:00:00")
    datenlage = _datenlage()
    gerufen = []
    code = main(
        ["--jetzt", bezug.isoformat()],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_datenlage=lambda *, bezug: (datenlage, None),
    )
    assert code == 0
    assert gerufen == []


def test_main_pusht_bei_einem_frischen_uebergang():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (bezug - _dt.timedelta(hours=20), status("us", daten=daten(503, 0))),
        (bezug - _dt.timedelta(hours=4), status("us", daten=daten(503, 0))),
    ]
    datenlage = _datenlage(status_historie=historie)
    gerufen = []
    code = main(
        ["--jetzt", bezug.isoformat()],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_datenlage=lambda *, bezug: (datenlage, None),
    )
    assert code == 0, "der Push IST das Signal -- kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "Kursabruf US" in gerufen[0]


def test_main_bleibt_waehrend_anhaltender_warnung_zwischen_den_erinnerungen_still():
    """Tag 1 (Uebergang) pusht, Tage 2-6 bleiben still, Tag 7 (Woche
    spaeter) pusht erneut -- hoechstens eine Erinnerung je Woche, ohne
    jede Persistenz. Ueber Pruefung C (Universum-Alter) getestet: die
    Warnung haengt rein von (Bezugstag - Stand) ab und bleibt damit ueber
    viele Tage anhaltend, ohne dass die Historie dafuer mitwachsen muss."""
    stand = _dt.date(2026, 1, 1)
    uebergangstag = stand + _dt.timedelta(days=UNIVERSUM_WARNSCHWELLE_TAGE + 1)

    ergebnisse = {}
    for versatz in range(0, 9):
        bezug = _dt.datetime.combine(
            uebergangstag + _dt.timedelta(days=versatz), _dt.time(6, 0), tzinfo=UTC
        )
        datenlage = _datenlage(stand_us=stand, stand_de=stand)
        gerufen = []
        main(
            ["--jetzt", bezug.isoformat()],
            melder=lambda text: gerufen.append(text) or True,
            ermittle_datenlage=lambda *, bezug, dl=datenlage: (dl, None),
        )
        ergebnisse[versatz] = bool(gerufen)

    assert ergebnisse[0] is True  # Uebergang
    for versatz in range(1, ERINNERUNG_TAGE):
        assert ergebnisse[versatz] is False, f"Tag {versatz} haette still bleiben muessen"
    assert ergebnisse[ERINNERUNG_TAGE] is True  # faellige Erinnerung


def test_main_technischer_fehlschlag_ist_rot_und_wird_trotzdem_gemeldet():
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_datenlage=lambda *, bezug: (None, "git liess sich nicht aufrufen."),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "nicht ermitteln" in gerufen[0]


def test_main_ein_gescheiterter_push_aendert_den_exit_code_nie():
    bezug = dt("2026-10-25T06:00:00")
    historie = [
        (bezug - _dt.timedelta(hours=20), status("us", daten=daten(503, 0))),
        (bezug - _dt.timedelta(hours=4), status("us", daten=daten(503, 0))),
    ]
    datenlage = _datenlage(status_historie=historie)

    def wirft(_text):
        raise OSError("keine Verbindung")

    code = main(
        ["--jetzt", bezug.isoformat()],
        melder=wirft,
        ermittle_datenlage=lambda *, bezug: (datenlage, None),
    )
    assert code == 0


def test_main_nachricht_laeuft_ueber_begrenze_bloecke():
    import momentum.notify as notify

    quelltext = Path("src/momentum/datenabdeckung_waechter.py").read_text(encoding="utf-8")
    assert "begrenze_bloecke" in quelltext
    assert notify.push_datenabdeckung_warnung  # importierbar


# --------------------------------------------------------- Git-Zugriff


class _ErgebnisAttrapp:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_git_log_liest_hash_und_zeit_aeltester_zuerst():
    def laeufer(cmd, **kw):
        assert cmd[:2] == ["git", "log"]
        assert "--since=2026-10-01T00:00:00+00:00" in cmd
        assert cmd[-2:] == ["--", "data/status.json"]
        return _ErgebnisAttrapp(
            0,
            stdout="bbb|2026-10-02T00:00:35+00:00\naaa|2026-10-01T00:00:35+00:00\n",
        )

    commits, grund = _git_log(
        "data/status.json", seit=dt("2026-10-01T00:00:00"), laeufer=laeufer
    )
    assert grund is None
    assert [h for h, _ in commits] == ["aaa", "bbb"]


def test_git_log_fehlschlag_wird_gemeldet():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(1, stderr="fatal: not a git repository")

    commits, grund = _git_log("data/status.json", seit=dt("2026-10-01T00:00:00"), laeufer=laeufer)
    assert commits is None
    assert grund is not None and "not a git repository" in grund


def test_git_log_ohne_aufrufbares_git_wird_gemeldet():
    def laeufer(cmd, **kw):
        raise OSError("No such file or directory: 'git'")

    commits, grund = _git_log("data/status.json", seit=dt("2026-10-01T00:00:00"), laeufer=laeufer)
    assert commits is None
    assert grund is not None


def test_git_show_liefert_inhalt():
    def laeufer(cmd, **kw):
        assert cmd == ["git", "show", "aaa:data/status.json"]
        return _ErgebnisAttrapp(0, stdout='{"lauf_datum": "2026-10-01"}')

    inhalt, grund = _git_show("aaa", "data/status.json", laeufer=laeufer)
    assert grund is None
    assert json.loads(inhalt)["lauf_datum"] == "2026-10-01"


def test_git_show_fehlschlag_wird_gemeldet():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(128, stderr="fatal: path does not exist")

    inhalt, grund = _git_show("aaa", "data/status.json", laeufer=laeufer)
    assert inhalt is None
    assert grund is not None


def test_historie_json_kombiniert_log_und_show():
    aufrufe = []

    def laeufer(cmd, **kw):
        aufrufe.append(cmd)
        if cmd[1] == "log":
            return _ErgebnisAttrapp(0, stdout="aaa|2026-10-01T00:00:35+00:00\n")
        return _ErgebnisAttrapp(0, stdout='{"lauf_datum": "2026-10-01"}')

    ergebnisse, grund = _historie_json(
        "data/status.json", seit=dt("2026-09-01T00:00:00"), laeufer=laeufer
    )
    assert grund is None
    [(zeit, daten_)] = ergebnisse
    assert daten_["lauf_datum"] == "2026-10-01"


def test_historie_json_kaputtes_json_wird_gemeldet():
    def laeufer(cmd, **kw):
        if cmd[1] == "log":
            return _ErgebnisAttrapp(0, stdout="aaa|2026-10-01T00:00:35+00:00\n")
        return _ErgebnisAttrapp(0, stdout="{halb geschrie")

    ergebnisse, grund = _historie_json(
        "data/status.json", seit=dt("2026-09-01T00:00:00"), laeufer=laeufer
    )
    assert ergebnisse is None
    assert grund is not None


def test_historie_json_leere_historie_ist_kein_fehlschlag():
    """Datei nie angelegt -- `git log` liefert nichts, das ist fail-soft,
    kein Fehler (siehe Modul-Docstring)."""
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(0, stdout="")

    ergebnisse, grund = _historie_json(
        "data/status.json", seit=dt("2026-09-01T00:00:00"), laeufer=laeufer
    )
    assert grund is None
    assert ergebnisse == []


def test_ermittle_datenlage_meldet_fehlende_universum_datei(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    (tmp_path / "universe" / "universe_us.txt").write_text("# Stand: 2026-08-03\n", encoding="utf-8")
    # universe_de.txt fehlt absichtlich.

    def laeufer(cmd, **kw):
        if cmd[1] == "log":
            return _ErgebnisAttrapp(0, stdout="")
        return _ErgebnisAttrapp(0, stdout="{}")

    datenlage, grund = ermittle_datenlage(bezug=dt("2026-10-25T06:00:00"), laeufer=laeufer)
    assert datenlage is None
    assert grund is not None and "universe_de.txt" in grund


def test_ermittle_datenlage_meldet_git_fehlschlag():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(1, stderr="fatal: not a git repository")

    datenlage, grund = ermittle_datenlage(bezug=dt("2026-10-25T06:00:00"), laeufer=laeufer)
    assert datenlage is None
    assert grund is not None and "data/status.json" in grund


# -------------------------------------------------------- Melden, nie Handeln


def test_der_waechter_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu den anderen Waechtern
    dieses Projekts."""
    quelltext = Path("src/momentum/datenabdeckung_waechter.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "git commit", "git push", "git add", "git checkout", "git rm",
        "gh pr", "gh api", "merge",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"
    assert "git log" in code and "git show" in code


def test_kein_schreibender_aufruf_als_code_konstante():
    """AST-Test (Auftrag: ausdruecklich gefordert): kein `ast.Constant`
    im Quelltext traegt den Wert eines schreibenden Git-/gh-Unterbefehls
    oder eines Merge-Arguments."""
    import ast

    baum = ast.parse(Path("src/momentum/datenabdeckung_waechter.py").read_text(encoding="utf-8"))
    verboten = {
        "commit", "push", "add", "rm", "checkout", "merge",
        "--auto", "--squash", "--merge", "rebase",
    }
    treffer = [
        knoten.value
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Constant) and knoten.value in verboten
    ]
    assert treffer == [], f"verbotenes Argument als Code-Konstante gefunden: {treffer}"


def test_der_workflow_kann_nur_lesen():
    daten_ = yaml.safe_load(
        Path(".github/workflows/datenabdeckung_waechter.yml").read_text(encoding="utf-8")
    )
    assert daten_["permissions"] == {"contents": "read"}
    assert "write" not in yaml.dump(daten_["permissions"])
    ausloeser = daten_[True] if True in daten_ else daten_["on"]
    zeitplaene = ausloeser["schedule"]
    assert len(zeitplaene) == 1
    minute, stunde = zeitplaene[0]["cron"].split()[:2]
    assert minute not in ("0", "30"), "Zeitpunkt darf nicht zur vollen/halben Stunde liegen"
    assert "workflow_dispatch" in ausloeser
    text = Path(".github/workflows/datenabdeckung_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text
    assert "fetch-depth: 0" in text


def test_der_workflow_laeuft_deutlich_nach_dem_spaetesten_beobachteten_lauf_ende():
    """Lauf.yml: 21:45 UTC + bis zu ~8 Std. dokumentierte Verzoegerung =
    spaetestens 05:45 UTC Lauf-START am naechsten Tag. Dieser Workflow
    muss klar danach liegen."""
    daten_ = yaml.safe_load(
        Path(".github/workflows/datenabdeckung_waechter.yml").read_text(encoding="utf-8")
    )
    ausloeser = daten_[True] if True in daten_ else daten_["on"]
    minute, stunde = ausloeser["schedule"][0]["cron"].split()[:2]
    uhrzeit = _dt.time(int(stunde), int(minute))
    spaetestes_lauf_ende = _dt.time(5, 45)
    assert uhrzeit > spaetestes_lauf_ende


def test_die_parameter_passen_zum_auftrag():
    assert FENSTER_STUNDEN_KURSABRUF == 24.0
    assert FENSTER_TAGE_KURSVERGLEICH == 7
    assert ERINNERUNG_TAGE == 7
