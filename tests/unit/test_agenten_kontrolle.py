"""Die Agenten-Kontrolle (agenten_kontrolle.py) — geprueft ohne Netz
(`gh`/`git` werden ueber die Test-Naehte `ermittle_laeufe`/
`ermittle_eingefuehrt_am` ersetzt).

Die Kernaussage: gab es in den letzten FENSTER_STUNDEN (48) mindestens
einen ERFOLGREICHEN ntfy_relay.yml-Lauf, dessen Titel mit
"ntfy: Momentum-Waechter" beginnt? Wenn nein -- UND der Anlaufschutz
nicht (mehr) greift -- ein lauter Alarm (Prioritaet high). MELDEN, NIE
HANDELN -- dieses Modul schreibt nirgends.
"""

from __future__ import annotations

import ast
import datetime as _dt
from pathlib import Path

import yaml

from momentum.agenten_kontrolle import (
    FENSTER_STUNDEN,
    TITEL_PRAEFIX,
    alarm_faellig,
    juengstes_lebenszeichen,
    main,
)

UTC = _dt.timezone.utc


def lauf(id_: int, titel: str, start_iso: str, *, erfolgreich: bool = True) -> dict:
    return {
        "id": id_,
        "display_title": titel,
        "conclusion": "success" if erfolgreich else "failure",
        "run_started_at": start_iso,
    }


LEBENSZEICHEN_TITEL = f"{TITEL_PRAEFIX} OK 25.10."
# Lange vor jedem betrachteten Fenster eingefuehrt -- in den meisten
# Tests soll der Anlaufschutz NICHT mehr greifen, nur die eigentliche
# Kernlogik.
LANGE_EINGEFUEHRT = _dt.datetime(2026, 1, 1, tzinfo=UTC)


# --------------------------------------------------------- juengstes_lebenszeichen


def test_kein_treffer_ohne_laeufe():
    assert juengstes_lebenszeichen([]) is None


def test_fehlgeschlagener_lauf_mit_passendem_titel_zaehlt_nicht():
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z", erfolgreich=False)]
    assert juengstes_lebenszeichen(laeufe) is None


def test_andersartiger_titel_zaehlt_nicht():
    """Ein Lit-Check-Lauf loest ntfy_relay.yml ebenfalls aus, aber unter
    einem voellig anderen Titel -- er darf das Lebenszeichen des
    Waechter-Agenten nicht ersetzen."""
    laeufe = [lauf(1, "ntfy: Lit-Check", "2026-10-26T09:56:00Z")]
    assert juengstes_lebenszeichen(laeufe) is None


def test_passender_erfolgreicher_lauf_zaehlt():
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]
    treffer = juengstes_lebenszeichen(laeufe)
    assert treffer == _dt.datetime(2026, 10, 25, 11, 40, tzinfo=UTC)


def test_nur_der_juengste_treffer_zaehlt():
    laeufe = [
        lauf(1, LEBENSZEICHEN_TITEL, "2026-10-23T11:40:00Z"),
        lauf(2, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z"),
    ]
    treffer = juengstes_lebenszeichen(laeufe)
    assert treffer == _dt.datetime(2026, 10, 25, 11, 40, tzinfo=UTC)


# -------------------------------------------------------------------- alarm_faellig


def test_lebenszeichen_vor_20_stunden_bleibt_still():
    jetzt = _dt.datetime(2026, 10, 26, 7, 40, tzinfo=UTC)
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]  # ~20h
    alarm, text = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=LANGE_EINGEFUEHRT)
    assert alarm is False
    assert "20.0 Std" in text


def test_lebenszeichen_vor_50_stunden_loest_alarm_aus():
    assert FENSTER_STUNDEN == 48.0
    jetzt = _dt.datetime(2026, 10, 27, 13, 40, tzinfo=UTC)
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]  # 50h
    alarm, text = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=LANGE_EINGEFUEHRT)
    assert alarm is True
    assert "50.0 Std" in text


def test_nur_fehlgeschlagene_relay_laeufe_loesen_alarm_aus():
    jetzt = _dt.datetime(2026, 10, 27, 13, 0, tzinfo=UTC)
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-26T11:40:00Z", erfolgreich=False)]
    alarm, _ = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=LANGE_EINGEFUEHRT)
    assert alarm is True


def test_nur_andersartige_titel_loesen_alarm_aus():
    jetzt = _dt.datetime(2026, 10, 27, 13, 0, tzinfo=UTC)
    laeufe = [lauf(1, "ntfy: Lit-Check", "2026-10-26T09:56:00Z")]
    alarm, _ = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=LANGE_EINGEFUEHRT)
    assert alarm is True


def test_anlaufschutz_greift_ohne_treffer_kurz_nach_einfuehrung():
    """Realer Fall (siehe Modul-Docstring): der EINE bisherige Lauf von
    ntfy_relay.yml (Lauf-ID 40191482916, display_title "ntfy-Relay",
    VOR run-name) zaehlt nicht als Treffer -- ohne Anlaufschutz waere das
    sofort ein Fehlalarm."""
    eingefuehrt_am = _dt.datetime(2026, 10, 25, 13, 0, tzinfo=UTC)
    jetzt = eingefuehrt_am + _dt.timedelta(hours=20)
    laeufe = [lauf(1, "ntfy-Relay", "2026-10-25T12:03:48Z")]  # alter Titel, zaehlt nicht
    alarm, text = alarm_faellig(laeufe, jetzt=jetzt, eingefuehrt_am=eingefuehrt_am)
    assert alarm is False
    assert "Anlaufschutz aktiv" in text


def test_anlaufschutz_laeuft_nach_48h_ab():
    eingefuehrt_am = _dt.datetime(2026, 10, 25, 13, 0, tzinfo=UTC)
    jetzt = eingefuehrt_am + _dt.timedelta(hours=49)
    alarm, text = alarm_faellig([], jetzt=jetzt, eingefuehrt_am=eingefuehrt_am)
    assert alarm is True
    assert "Anlaufschutz abgelaufen" in text


# ------------------------------------------------------------------- main(): Push/Exit


def test_main_still_wenn_lebenszeichen_im_rahmen():
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]
    gerufen = []
    code = main(
        ["--jetzt", "2026-10-26T07:40:00+00:00"],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (laeufe, None),
        ermittle_eingefuehrt_am=lambda: (LANGE_EINGEFUEHRT, None),
    )
    assert code == 0
    assert gerufen == []


def test_main_alarm_bei_altem_lebenszeichen():
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]
    gerufen = []
    code = main(
        ["--jetzt", "2026-10-27T13:40:00+00:00"],  # 50h
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (laeufe, None),
        ermittle_eingefuehrt_am=lambda: (LANGE_EINGEFUEHRT, None),
    )
    assert code == 0, "der Push IST das Signal -- kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "über 48 Std." in gerufen[0]


def test_main_laeufe_nicht_ermittelbar_ist_rot_ohne_push():
    """FAIL-SOFT, bewusst ANDERS als bei den anderen Waechtern dieses
    Projekts (siehe Modul-Docstring): technische Unsicherheit macht den
    Lauf rot, aber sie loest KEINEN Push aus -- dieses Modul ist ein
    Alarm, kein Herzschlag."""
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: (None, "gh liess sich nicht aufrufen (OSError: ...)."),
        ermittle_eingefuehrt_am=lambda: (LANGE_EINGEFUEHRT, None),
    )
    assert code == 1
    assert gerufen == []


def test_main_einfuehrungszeitpunkt_nicht_ermittelbar_ist_rot_ohne_push():
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_laeufe=lambda: ([], None),
        ermittle_eingefuehrt_am=lambda: (None, "kein Commit fuehrt 'run-name:' ein."),
    )
    assert code == 1
    assert gerufen == []


def test_main_jetzt_ist_injizierbar_und_deterministisch():
    laeufe = [lauf(1, LEBENSZEICHEN_TITEL, "2026-10-25T11:40:00Z")]
    ergebnisse = set()
    for _ in range(3):
        gerufen = []
        code = main(
            ["--jetzt", "2026-10-27T13:40:00+00:00"],
            melder=lambda text: gerufen.append(text) or True,
            ermittle_laeufe=lambda: (laeufe, None),
            ermittle_eingefuehrt_am=lambda: (LANGE_EINGEFUEHRT, None),
        )
        ergebnisse.add((code, tuple(gerufen)))
    assert len(ergebnisse) == 1, "dieselbe Historie + dasselbe 'jetzt' muss immer dieselbe Entscheidung ergeben"


# --------------------------------------------------- run-name ist keine Shell-Injektion


def test_run_name_ist_keine_shell_interpolation():
    """Statischer Beleg (Kriterium 2/4), nicht nur Behauptung: `run-name:`
    (Zeile direkt unter `name:`) darf NIRGENDS innerhalb eines `run:`-
    Blocks der Datei auftauchen -- genau DAS waere die tatsaechliche
    Injektionsmechanik (siehe agenten_kontrolle.py Modul-Docstring,
    CVE-2023-49291). `run-name:` selbst landet nur als Anzeigetext in der
    Actions-Oberflaeche."""
    pfad = Path(".github/workflows/ntfy_relay.yml")
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    assert "run-name" in daten, "die eine erlaubte Zeile fehlt"
    assert daten["run-name"] == "ntfy: ${{ inputs.title }}"

    roh_zeilen = pfad.read_text(encoding="utf-8").splitlines()
    in_run_block = False
    for zeile in roh_zeilen:
        gestrippt = zeile.strip()
        if gestrippt.startswith("run:") or gestrippt.startswith("run: |") or gestrippt.startswith("run: >"):
            in_run_block = True
            continue
        if in_run_block and gestrippt and not zeile.startswith(" " * 8):
            in_run_block = False
        if in_run_block:
            assert "run-name" not in zeile, "run-name innerhalb eines run:-Blocks gefunden"

    for name, job in daten["jobs"].items():
        for step in job.get("steps", []):
            lauf_zeile = step.get("run", "")
            assert "run-name" not in lauf_zeile


def test_ntfy_relay_sonst_unveraendert_bis_auf_die_eine_zeile():
    """Nur EINE Zeile darf dazugekommen sein (Bau-Punkt 1 des Auftrags)."""
    pfad = Path(".github/workflows/ntfy_relay.yml")
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    treffer = [z for z in zeilen if z.strip() == 'run-name: "ntfy: ${{ inputs.title }}"']
    assert len(treffer) == 1


# --------------------------------------------------------------- Workflow-Hygiene


def test_workflow_hat_keinen_input_in_run_zeile():
    daten = yaml.safe_load(
        Path(".github/workflows/agenten_kontrolle.yml").read_text(encoding="utf-8")
    )
    ausloeser = daten[True] if True in daten else daten["on"]
    dispatch = ausloeser.get("workflow_dispatch")
    assert not dispatch, "dieser Workflow hat bewusst keine Eingabefelder"
    for job in daten["jobs"].values():
        for step in job.get("steps", []):
            assert "${{ inputs." not in step.get("run", "")


def test_workflow_zeitpunkt_liegt_klar_nach_11_31_plus_acht_stunden_drift():
    daten = yaml.safe_load(
        Path(".github/workflows/agenten_kontrolle.yml").read_text(encoding="utf-8")
    )
    ausloeser = daten[True] if True in daten else daten["on"]
    cron = ausloeser["schedule"][0]["cron"]
    minute, stunde, *_rest = cron.split()
    gewaehlter_zeitpunkt = _dt.time(int(stunde), int(minute))
    spaetester_agenten_lauf = _dt.time(19, 31)  # 11:31 UTC + 8h Drift
    assert gewaehlter_zeitpunkt > spaetester_agenten_lauf
    assert int(minute) not in (0, 30), "bewusst nicht auf voller/halber Stunde"


def test_workflow_hat_nur_lese_rechte():
    daten = yaml.safe_load(
        Path(".github/workflows/agenten_kontrolle.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read", "actions": "read"}


# -------------------------------------------------------- Harte Grenze: nie schreiben


def test_kein_schreibender_aufruf_im_quelltext():
    """Statischer Nie-Handeln-Test, analog zu jedem anderen Waechter
    dieses Projekts (z. B. test_schutz_sperre.py::
    test_der_code_kann_nirgends_schreiben)."""
    quelltext = Path("src/momentum/agenten_kontrolle.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "\"w\")", "'w')", "\"wb\"", "'wb'",
        "\"a\")", "'a')",
        "git commit", "git push", "git add", "gh pr", "gh issue",
        "gh workflow run", "gh api -X POST", "gh api -X PATCH",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"


def test_kein_merge_aufruf_existiert_im_quelltext():
    """AST-Test (Bau-Punkt 2 des Auftrags), analog zu
    test_agent_datumsformat_oeffnen.py::
    test_kein_merge_aufruf_existiert_im_quelltext -- der Modul-Docstring
    darf "gh pr merge" in Prosa ERWAEHNEN, verboten ist nur, dass der
    String als tatsaechliche Code-Konstante auftaucht."""
    baum = ast.parse(Path("src/momentum/agenten_kontrolle.py").read_text(encoding="utf-8"))
    verbotene_worte = {"merge", "--auto", "--squash", "--merge", "pr merge", "gh pr merge"}
    treffer = [
        knoten.value
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Constant) and knoten.value in verbotene_worte
    ]
    assert treffer == [], f"verbotenes Argument als Code-Konstante gefunden: {treffer}"
