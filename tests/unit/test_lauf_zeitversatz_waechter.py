"""Die Lauf-Zeitversatz-Wächter (lauf_zeitversatz_waechter.py) —
geprueft ohne Netz (gh wird ueber die Test-Naht `laeufer`/`ermittle_laeufe`
ersetzt).

Die Kernaussage: mehr als SCHWELLE_STUNDEN Verzoegerung bei MINDESTENS
EINEM der letzten ANZAHL_LETZTE_LAEUFE `schedule`-ausgeloesten Laeufe
loest eine LAUTLOSE Beobachtungs-Meldung aus. `workflow_dispatch`-Laeufe
(manuelle Nachlaeufe) gehen NIE in die Auswertung ein -- sie haben
keinen nominellen Zeitpunkt. Und: MELDEN, NIE HANDELN -- dieses Modul
schreibt nirgends.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest
import yaml

from momentum.lauf_zeitversatz_waechter import (
    ANZAHL_LETZTE_LAEUFE,
    SCHWELLE_STUNDEN,
    _letzte_laeufe,
    main,
    nominal_vor,
    stand_text,
    verzoegerungen_stunden,
)

UTC = _dt.timezone.utc


def lauf(id_: int, start_iso: str, *, event: str = "schedule") -> dict:
    return {"id": id_, "event": event, "run_started_at": start_iso}


# --------------------------------------------------------------- nominal_vor()


def test_reale_faelle_aus_der_sitzung():
    """Drei echte, per `gh api` abgefragte schedule-Laeufe (02.10.2026) --
    jeder kalendarisch am Tag NACH seinem nominellen 21:45-UTC-Zeitpunkt."""
    faelle = [
        ("2026-09-30T00:45:02Z", "2026-09-29T21:45:00+00:00"),
        ("2026-10-01T00:49:22Z", "2026-09-30T21:45:00+00:00"),
        ("2026-10-02T01:04:16Z", "2026-10-01T21:45:00+00:00"),
    ]
    for start_s, erwartet_s in faelle:
        start = _dt.datetime.fromisoformat(start_s.replace("Z", "+00:00"))
        erwartet = _dt.datetime.fromisoformat(erwartet_s)
        assert nominal_vor(start) == erwartet, start_s


def test_puenktlicher_lauf_noch_vor_mitternacht():
    """Startet der Lauf NOCH am selben Kalendertag nach 21:45, ist der
    nominelle Zeitpunkt derselbe Tag, keine Rueckrechnung noetig."""
    start = _dt.datetime(2026, 9, 29, 22, 10, tzinfo=UTC)  # Dienstag
    assert start.weekday() == 1
    erwartet = _dt.datetime(2026, 9, 29, 21, 45, tzinfo=UTC)
    assert nominal_vor(start) == erwartet


def test_cron_kann_sich_nur_verspaeten_nie_vorauseilen():
    """Ein Start VOR 21:45 desselben Tages darf NIE denselben Tag als
    nominellen Zeitpunkt liefern -- das waere eine negative Verzoegerung."""
    start = _dt.datetime(2026, 9, 29, 5, 0, tzinfo=UTC)  # Dienstag, frueh
    nominal = nominal_vor(start)
    assert nominal is not None
    assert nominal <= start


def test_wochenende_wird_uebersprungen():
    """Ein Lauf, der (hypothetisch) erst Montag kurz nach Mitternacht
    tatsaechlich startet, kann unmoeglich Montags eigener (noch gar
    nicht erreichter) Zeitpunkt sein -- cron eilt nie vor. Der naechste
    gueltige WERKTAG rueckwaerts ist Freitag, nicht Samstag/Sonntag."""
    montag_frueh = _dt.datetime(2026, 10, 5, 0, 43, tzinfo=UTC)
    assert montag_frueh.weekday() == 0
    nominal = nominal_vor(montag_frueh)
    assert nominal is not None
    assert nominal.weekday() == 4  # Freitag
    assert nominal <= montag_frueh


def test_kein_gueltiger_werktag_im_rueckblick_liefert_none():
    start = _dt.datetime(2026, 9, 29, 5, 0, tzinfo=UTC)
    assert nominal_vor(start, rueckblick_tage=0) is None


# ------------------------------------------------------- verzoegerungen_stunden


def test_workflow_dispatch_wird_ausgeschlossen():
    """Widerspruch gemeldet, nicht uebergangen (Kriterium 2): ein
    manueller Nachlauf hat keinen nominellen Zeitpunkt."""
    laeufe = [
        lauf(1, "2026-10-01T00:49:22Z", event="schedule"),
        lauf(2, "2026-10-01T21:13:30Z", event="workflow_dispatch"),
    ]
    ergebnis = verzoegerungen_stunden(laeufe)
    assert [id_ for id_, _ in ergebnis] == [1]


def test_verzoegerung_wird_in_stunden_berechnet():
    laeufe = [lauf(1, "2026-10-01T00:49:22Z")]
    [(id_, stunden)] = verzoegerungen_stunden(laeufe)
    assert id_ == 1
    assert 3.0 < stunden < 3.2  # ~3h04m, siehe nominal_vor()-Docstring


def test_fehlendes_run_started_at_wird_uebersprungen():
    laeufe = [{"id": 1, "event": "schedule"}]
    assert verzoegerungen_stunden(laeufe) == []


def test_unlesbares_datum_wird_uebersprungen():
    laeufe = [lauf(1, "nicht-ein-datum")]
    assert verzoegerungen_stunden(laeufe) == []


# ------------------------------------------------------------------- stand_text


def test_stand_text_nennt_die_groesste_verzoegerung():
    text = stand_text(5.3)
    assert "5.3 Std" in text
    assert str(ANZAHL_LETZTE_LAEUFE) in text
    assert "21:45" in text
    assert "keine Handlungsaufforderung" in text


# --------------------------------------------------------------- main(): Push/Exit


def test_unterhalb_der_schwelle_bleibt_still():
    laeufe = [lauf(1, "2026-10-01T00:49:22Z")]  # ~3h, unter SCHWELLE_STUNDEN
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (laeufe, None),
    )
    assert code == 0
    assert gerufen == []


def test_ein_simulierter_alter_lauf_mit_ueber_4h_verzoegerung_loest_aus():
    """Nachweis statt Behauptung (Kriterium 3): ein Lauf mit
    nachweislich mehr als SCHWELLE_STUNDEN Verzoegerung loest die
    Meldung tatsaechlich aus."""
    assert SCHWELLE_STUNDEN == 4.0
    # Dienstag, 21:45 UTC nominell -- tatsaechlicher Start 6 Stunden spaeter.
    verspaetet = (
        _dt.datetime(2026, 9, 29, 21, 45, tzinfo=UTC) + _dt.timedelta(hours=6)
    ).isoformat().replace("+00:00", "Z")
    laeufe = [lauf(1, verspaetet)]
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (laeufe, None),
    )
    assert code == 0, "der Push IST das Signal -- kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "6.0 Std" in gerufen[0]


def test_nur_die_groesste_verzoegerung_wird_genannt():
    basis = _dt.datetime(2026, 9, 29, 21, 45, tzinfo=UTC)
    laeufe = [
        lauf(1, (basis + _dt.timedelta(hours=5)).isoformat().replace("+00:00", "Z")),
        lauf(2, (basis + _dt.timedelta(days=1, hours=9)).isoformat().replace("+00:00", "Z")),
    ]
    gerufen = []
    main([], melder=lambda text: gerufen.append(text) or True, ermittle_laeufe=lambda: (laeufe, None))
    assert len(gerufen) == 1
    assert "9.0 Std" in gerufen[0]


def test_keine_auswertbaren_laeufe_bleibt_still_und_gruen():
    laeufe = [lauf(1, "2026-10-01T21:13:30Z", event="workflow_dispatch")]
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (laeufe, None),
    )
    assert code == 0
    assert gerufen == []


def test_technischer_fehlschlag_ist_rot_und_wird_trotzdem_gemeldet():
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (None, "gh liess sich nicht aufrufen (OSError: ...)"),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "nicht ermitteln" in gerufen[0]


def test_ein_gescheiterter_push_aendert_den_exit_code_nie():
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie bei den anderen vier Waechtern."""
    verspaetet = (
        _dt.datetime(2026, 9, 29, 21, 45, tzinfo=UTC) + _dt.timedelta(hours=6)
    ).isoformat().replace("+00:00", "Z")
    laeufe = [lauf(1, verspaetet)]
    assert main([], melder=lambda _t: False, ermittle_laeufe=lambda: (laeufe, None)) == 0

    def wirft(_text):
        raise OSError("keine Verbindung")

    assert main([], melder=wirft, ermittle_laeufe=lambda: (laeufe, None)) == 0


# ------------------------------------------------------------- _letzte_laeufe()


class _ErgebnisAttrapp:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_gh_aufruf_nutzt_die_rohe_rest_api_nicht_gh_run_list():
    """Widerspruch gemeldet statt angenommen (Kriterium 2/6): dieses
    Projekt kann die `--json`-Feldnamen der echten gh-CLI hier nicht
    gegenpruefen. `gh api` (roher REST-Pfad, empirisch gegen das echte
    Repository bestaetigt) ist deshalb die zuverlaessigere Wahl als
    `gh run list --json startedAt`."""
    aufrufe = []

    def laeufer(cmd, **kw):
        aufrufe.append(cmd)
        return _ErgebnisAttrapp(0, stdout='{"workflow_runs": []}')

    laeufe, grund = _letzte_laeufe(laeufer=laeufer)
    assert grund is None
    assert laeufe == []
    [cmd] = aufrufe
    assert cmd[:2] == ["gh", "api"]
    assert "actions/workflows/lauf.yml/runs" in cmd[2]
    assert "run list" not in " ".join(cmd)


def test_gh_fehlschlag_wird_gemeldet():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(1, stderr="HTTP 404")

    laeufe, grund = _letzte_laeufe(laeufer=laeufer)
    assert laeufe is None
    assert grund is not None and "404" in grund


def test_kaputtes_json_wird_gemeldet():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(0, stdout="{halb geschrie")

    laeufe, grund = _letzte_laeufe(laeufer=laeufer)
    assert laeufe is None
    assert grund is not None


def test_fehlendes_workflow_runs_feld_wird_gemeldet():
    def laeufer(cmd, **kw):
        return _ErgebnisAttrapp(0, stdout="{}")

    laeufe, grund = _letzte_laeufe(laeufer=laeufer)
    assert laeufe is None
    assert grund is not None and "workflow_runs" in grund


# -------------------------------------------------------- Melden, nie Handeln


def test_der_waechter_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu den anderen drei
    `gh`-nutzenden Waechtern."""
    quelltext = Path("src/momentum/lauf_zeitversatz_waechter.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "run create", "run rerun", "run cancel", "run delete",
        "workflow run", "workflow enable", "workflow disable",
        "git commit", "git push", "git add",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"
    assert "gh api" in code


def test_der_workflow_kann_nur_lesen():
    daten = yaml.safe_load(
        Path(".github/workflows/lauf_zeitversatz_waechter.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read", "actions": "read"}
    assert "write" not in yaml.dump(daten["permissions"])
    zeitplaene = daten[True]["schedule"] if True in daten else daten["on"]["schedule"]
    assert len(zeitplaene) == 1
    lauf_waechter = yaml.safe_load(Path(".github/workflows/waechter.yml").read_text(encoding="utf-8"))
    lauf_zeitplaene = lauf_waechter[True]["schedule"] if True in lauf_waechter else lauf_waechter["on"]["schedule"]
    assert zeitplaene[0]["cron"] == lauf_zeitplaene[0]["cron"]
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "workflow_dispatch" in ausloeser
    text = Path(".github/workflows/lauf_zeitversatz_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text


def test_die_meldung_geht_durch_denselben_push_wie_alles_andere_und_ist_lautlos():
    """Kein Sonderweg: push_zeitversatz_beobachtet ruft notify.push --
    LAUTLOS (Prioritaet min), reine Beobachtung ohne Sirene."""
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    koerper = quelltext.split("def push_zeitversatz_beobachtet")[1].split("\ndef ")[0]
    assert "return push(" in koerper
    assert "urllib" not in koerper
    assert 'priority="min"' in koerper
    assert notify.PRIORITIES["min"] == 1
    assert notify.push_zeitversatz_beobachtet  # importierbar


def test_die_nominelle_zeit_passt_zum_cron_in_lauf_yml():
    """Die feste 21:45-UTC-Annahme muss zum tatsaechlichen Cron in
    lauf.yml passen -- sonst misst dieses Modul gegen einen falschen
    Bezugspunkt."""
    from momentum.lauf_zeitversatz_waechter import NOMINELLE_UHRZEIT_UTC

    text = Path(".github/workflows/lauf.yml").read_text(encoding="utf-8")
    assert 'cron: "45 21 * * 1-5"' in text
    assert NOMINELLE_UHRZEIT_UTC == _dt.time(21, 45)


def test_die_parameter_passen_zum_auftrag():
    assert ANZAHL_LETZTE_LAEUFE == 10
    assert SCHWELLE_STUNDEN == 4.0
