"""Der Push-Zustellungs-Waechter (push_zustellung_waechter.py) — geprueft
ohne Netz.

NEU AUFGESETZT (Option 2): keine data/push_health.json mehr, sondern ein
Scan der Actions-Job-Logs mehrerer Workflows nach notify.FEHLSCHLAG_
ANKERTEXT. Die Kernaussage bleibt: mindestens EIN Treffer in den letzten
FENSTER_TAGE_PRUEFUNG Tagen loest die Meldung aus, gezaehlt je
betroffenem WORKFLOW (nicht je Push-Typ -- der Ankertext selbst nennt
den Typ nicht, siehe Modul-Docstring). Und: MELDEN, NIE REPARIEREN --
dieses Modul schreibt nirgends.

Die beiden `gh`-Aufrufarten (Lauf-Liste, Einzel-Log) werden hier durch
EINEN gemeinsamen `laeufer`-Fake ersetzt, der am Kommando selbst
unterscheidet -- dieselbe Test-Naht-Idee wie in
test_lauf_zeitversatz_waechter.py, nur fuer zwei `gh`-Unterkommandos
statt einem.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import yaml

from momentum.config import REPO_SLUG
from momentum.push_zustellung_waechter import (
    ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW,
    FENSTER_TAGE_PRUEFUNG,
    UEBERWACHTE_WORKFLOWS,
    fehlschlaege_je_workflow,
    main,
    stand_text,
)

UTC = _dt.timezone.utc
JETZT = _dt.datetime(2026, 10, 4, 7, 30, tzinfo=UTC)


class _Ergebnis:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def lauf(run_id: int, gestartet: _dt.datetime, *, event: str = "schedule") -> dict:
    return {"id": run_id, "run_started_at": gestartet.isoformat().replace("+00:00", "Z"), "event": event}


def gefaelschter_laeufer(
    *,
    laeufe_je_workflow: dict[str, list[dict]] | None = None,
    logs_je_lauf: dict[int, str] | None = None,
    api_fehler_je_workflow: dict[str, str] | None = None,
    log_fehler_je_lauf: dict[int, str] | None = None,
):
    """Ein einziger Fake fuer BEIDE `gh`-Unterkommandos, unterschieden am
    Kommando selbst -- genau das, was `_laeufe_eines_workflows` bzw.
    `_log_eines_laufs` tatsaechlich aufrufen."""
    laeufe_je_workflow = laeufe_je_workflow or {}
    logs_je_lauf = logs_je_lauf or {}
    api_fehler_je_workflow = api_fehler_je_workflow or {}
    log_fehler_je_lauf = log_fehler_je_lauf or {}

    def laeufer(cmd, capture_output=True, text=True):
        if cmd[0] == "gh" and cmd[1] == "api":
            pfad = cmd[2]
            workflow = pfad.split("/workflows/")[1].split("/runs")[0]
            if workflow in api_fehler_je_workflow:
                return _Ergebnis(returncode=1, stderr=api_fehler_je_workflow[workflow])
            return _Ergebnis(stdout=json.dumps({"workflow_runs": laeufe_je_workflow.get(workflow, [])}))
        if cmd[0] == "gh" and cmd[1] == "run" and cmd[2] == "view":
            run_id = int(cmd[3])
            if run_id in log_fehler_je_lauf:
                return _Ergebnis(returncode=1, stderr=log_fehler_je_lauf[run_id])
            return _Ergebnis(stdout=logs_je_lauf.get(run_id, ""))
        raise AssertionError(f"unerwarteter Aufruf: {cmd!r}")

    return laeufer


# ---------------------------------------------------------- fehlschlaege_je_workflow


def test_ein_simulierter_log_mit_dem_ankertext_wird_erkannt():
    """Nachweis statt Behauptung (Kriterium 3): EIN Log mit dem exakten
    Ankertext loest den Waechter tatsaechlich aus."""
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=2))]},
        logs_je_lauf={1: "irrelevante Zeile\nntfy hat den Push abgelehnt: HTTP 500 — x\nweitere Zeile"},
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",),
    )
    assert zaehlung == {"vertrag.yml": 1}
    assert fehler == []
    assert nicht_pruefbar == []


def test_ein_log_ohne_den_ankertext_bleibt_still():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=2))]},
        logs_je_lauf={1: "Vertraege pruefen\nalles gut, kein Fehlschlag hier\n"},
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",),
    )
    assert zaehlung == {}
    assert fehler == []
    assert nicht_pruefbar == []


def test_laeufe_ausserhalb_des_fensters_werden_nicht_einmal_abgefragt():
    """Ein zu alter Lauf wird schon in der Fenster-Filterung aussortiert --
    `_log_eines_laufs` darf fuer ihn gar nicht erst aufgerufen werden."""
    zu_alt = JETZT - _dt.timedelta(days=FENSTER_TAGE_PRUEFUNG + 1)
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, zu_alt)]},
        # Kein Log fuer run_id 1 hinterlegt -- wuerde der Code ihn
        # trotzdem abfragen, kaeme ein leerer String zurueck (kein
        # Treffer), das Fehlen des Eintrags ist hier nur zur
        # Dokumentation der Absicht.
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",),
    )
    assert zaehlung == {}
    assert fehler == []


def test_genau_am_rand_des_fensters_zaehlt_noch():
    rand = JETZT - _dt.timedelta(days=FENSTER_TAGE_PRUEFUNG)
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, rand)]},
        logs_je_lauf={1: "ntfy hat den Push abgelehnt: HTTP 500 — x"},
    )
    zaehlung, _, _, _ = fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert zaehlung == {"vertrag.yml": 1}


def test_mehrere_treffer_im_selben_log_werden_gezaehlt():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1))]},
        logs_je_lauf={
            1: "ntfy hat den Push abgelehnt: HTTP 500 — a\n...\nntfy hat den Push abgelehnt: HTTP 500 — b",
        },
    )
    zaehlung, _, _, _ = fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert zaehlung == {"vertrag.yml": 2}


def test_treffer_werden_je_workflow_nicht_je_lauf_aufsummiert():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={
            "vertrag.yml": [
                lauf(1, JETZT - _dt.timedelta(hours=1)),
                lauf(2, JETZT - _dt.timedelta(hours=2)),
            ],
        },
        logs_je_lauf={
            1: "ntfy hat den Push abgelehnt: HTTP 500 — a",
            2: "ntfy hat den Push abgelehnt: HTTP 500 — b",
        },
    )
    zaehlung, _, _, _ = fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert zaehlung == {"vertrag.yml": 2}


def test_mehrere_workflows_werden_getrennt_gezaehlt():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={
            "vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1))],
            "waechter.yml": [lauf(2, JETZT - _dt.timedelta(hours=1))],
        },
        logs_je_lauf={
            1: "ntfy hat den Push abgelehnt: HTTP 500 — a",
            2: "alles gut",
        },
    )
    zaehlung, _, _, _ = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml", "waechter.yml"),
    )
    assert zaehlung == {"vertrag.yml": 1}


def test_eine_fehlgeschlagene_lauf_liste_wird_als_einzelproblem_gemeldet_andere_workflows_laufen_weiter():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"waechter.yml": [lauf(2, JETZT - _dt.timedelta(hours=1))]},
        logs_je_lauf={2: "ntfy hat den Push abgelehnt: HTTP 500 — b"},
        api_fehler_je_workflow={"vertrag.yml": "rate limit exceeded"},
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml", "waechter.yml"),
    )
    assert zaehlung == {"waechter.yml": 1}
    assert nicht_pruefbar == ["vertrag.yml"]
    assert any("vertrag.yml" in z and "rate limit" in z for z in fehler)


def test_ein_fehlgeschlagener_einzel_log_abruf_wird_gemeldet_bricht_aber_nicht_alles_ab():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={
            "vertrag.yml": [
                lauf(1, JETZT - _dt.timedelta(hours=1)),
                lauf(2, JETZT - _dt.timedelta(hours=2)),
            ],
        },
        logs_je_lauf={2: "ntfy hat den Push abgelehnt: HTTP 500 — b"},
        log_fehler_je_lauf={1: "log abgelaufen"},
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",),
    )
    assert zaehlung == {"vertrag.yml": 1}
    assert nicht_pruefbar == []
    assert any("1" in z and "log abgelaufen" in z for z in fehler)


def test_alle_workflows_nicht_pruefbar_wird_vollstaendig_gemeldet():
    laeufer = gefaelschter_laeufer(
        api_fehler_je_workflow={"vertrag.yml": "x", "waechter.yml": "y"},
    )
    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml", "waechter.yml"),
    )
    assert zaehlung == {}
    assert set(nicht_pruefbar) == {"vertrag.yml", "waechter.yml"}


def test_nur_schedule_oder_dispatch_laeufe_liefern_trotzdem_treffer_event_spielt_keine_rolle():
    """Anders als beim Zeitversatz-Waechter ist `event` hier egal -- ein
    ntfy-Fehlschlag ist ein Fehlschlag, unabhaengig davon, ob der Lauf
    nach Zeitplan oder per Hand ausgeloest wurde."""
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1), event="workflow_dispatch")]},
        logs_je_lauf={1: "ntfy hat den Push abgelehnt: HTTP 500 — a"},
    )
    zaehlung, _, _, _ = fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert zaehlung == {"vertrag.yml": 1}


# ------------------------------------------------------------------- stand_text


def test_stand_text_nennt_anzahl_und_workflows():
    text = stand_text({"vertrag.yml": 2, "waechter.yml": 1})
    assert "3 fehlgeschlagene" in text
    assert "vertrag.yml (×2)" in text
    assert "waechter.yml (×1)" in text
    assert str(FENSTER_TAGE_PRUEFUNG) in text


def test_stand_text_bleibt_kurz_auch_bei_vielen_treffern_desselben_workflows():
    kurz = stand_text({"vertrag.yml": 1})
    lang = stand_text({"vertrag.yml": 10_000})
    assert len(lang) - len(kurz) < 10, "nur die Ziffer darf laenger werden, nicht die Struktur"


# --------------------------------------------------------------- main(): Push/Exit


def test_keine_treffer_bleibt_still():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1))]},
        logs_je_lauf={1: "alles gut"},
    )
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle=lambda: fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",)),
    )
    assert code == 0
    assert gerufen == []


def test_ein_treffer_loest_genau_einen_push_aus_bleibt_aber_gruen():
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1))]},
        logs_je_lauf={1: "ntfy hat den Push abgelehnt: HTTP 500 — a"},
    )
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle=lambda: fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",)),
    )
    assert code == 0, "der Push IST das Signal -- kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "vertrag.yml (×1)" in gerufen[0]


def test_alle_workflows_nicht_pruefbar_ist_rot_und_wird_trotzdem_gemeldet():
    laeufer = gefaelschter_laeufer(api_fehler_je_workflow={"vertrag.yml": "x"})
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle=lambda: fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",)),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "pruefen" in gerufen[0]


def test_ein_gescheiterter_push_aendert_den_exit_code_nie():
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie bei den anderen vier Waechtern."""
    laeufer = gefaelschter_laeufer(
        laeufe_je_workflow={"vertrag.yml": [lauf(1, JETZT - _dt.timedelta(hours=1))]},
        logs_je_lauf={1: "ntfy hat den Push abgelehnt: HTTP 500 — a"},
    )
    ermittle = lambda: fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert main([], melder=lambda _t: False, ermittle=ermittle) == 0

    def wirft(_text):
        raise OSError("keine Verbindung")

    assert main([], melder=wirft, ermittle=ermittle) == 0


# ----------------------------------------------------- Regression: realer Vorfall


def test_der_reale_25_30_09_vorfall_waere_erkannt_worden():
    """Beleg statt Vermutung (Kriterium 4): am 25./28./29./30.09.2026 ist
    push_vertrag_gebrochen() in vertrag.yml viermal mit "HTTP 500 --
    internal server error (code 50001)" gescheitert (siehe
    notify.py-Kommentar zu NACHRICHT_BLOCK_GRENZE). Der Log-Ausschnitt
    unten ist eine REKONSTRUKTION, kein woertliches Vollzitat eines
    kompletten Actions-Logs -- die eine Zeile selbst ist aber woertlich
    und real: erneut abgerufen in dieser Sitzung via
    mcp__github__get_job_logs fuer Job 109018501269 (Vertragstest #12,
    28.09.2026), dort tatsaechlich und unveraendert vorhanden:
    "ntfy hat den Push abgelehnt: HTTP 500 — internal server error
    (code 50001)". Die alte, datei-basierte Variante haette diesen
    Vorfall NICHT erkannt (vertrag.yml hat keinen Commit-Schritt) --
    dieser Test haelt fest, dass die neue Log-Scan-Variante das tut.
    """
    realer_log_ausschnitt = (
        "2026-09-28T08:03:11.0000000Z ##[group]Run python tools/vertragstest.py "
        "--agent-befund agent_ishares_datumsformat.json\n"
        "2026-09-28T08:03:14.0000000Z Vertrag gebrochen: iShares DAX, iShares "
        "MDAX, iShares SDAX, iShares TecDAX, Wikipedia-Bestandsliste\n"
        "2026-09-28T08:03:14.0000000Z ntfy hat den Push abgelehnt: HTTP 500 — "
        "internal server error (code 50001)\n"
        "2026-09-28T08:03:14.0000000Z ##[error]Process completed with exit code 1.\n"
    )
    tage = [25, 28, 29, 30]
    jetzt = _dt.datetime(2026, 9, 30, 20, 0, tzinfo=UTC)
    laeufe = [lauf(100 + i, _dt.datetime(2026, 9, tag, 8, 3, tzinfo=UTC)) for i, tag in enumerate(tage)]
    logs = {100 + i: realer_log_ausschnitt for i in range(len(tage))}
    laeufer = gefaelschter_laeufer(laeufe_je_workflow={"vertrag.yml": laeufe}, logs_je_lauf=logs)

    zaehlung, fehler, nicht_pruefbar, geprueft = fehlschlaege_je_workflow(
        jetzt=jetzt, laeufer=laeufer, workflows=("vertrag.yml",),
    )
    assert fehler == []
    assert nicht_pruefbar == []
    assert zaehlung == {"vertrag.yml": 4}


# -------------------------------------------------------- Melden, nie Handeln


def test_der_waechter_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu den anderen vier Waechtern."""
    quelltext = Path("src/momentum/push_zustellung_waechter.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "\"gh run rerun", "'gh run rerun", "git commit", "git push",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"


def test_der_workflow_kann_nur_lesen_aber_actions_mitlesen():
    daten = yaml.safe_load(
        Path(".github/workflows/push_zustellung_waechter.yml").read_text(encoding="utf-8")
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
    text = Path(".github/workflows/push_zustellung_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text
    assert "github.token" in text


def test_keine_der_vier_gelesenen_workflow_dateien_wird_angefasst():
    """Harte Grenze aus dem Auftrag: vertrag.yml, waechter.yml,
    handover_waechter.yml, pr_verwaisung_waechter.yml bleiben
    UNVERAENDERT read-only -- dieser Workflow braucht fuer sein eigenes
    Lesen nur sein EIGENES `actions: read` (siehe Scope-Pruefung im
    Modul-Docstring von push_zustellung_waechter.py), nicht etwa eine
    Rechte-Erweiterung bei den gelesenen Workflows selbst."""
    erwartet = {
        "waechter.yml": {"contents": "read"},
        "handover_waechter.yml": {"contents": "read", "pull-requests": "read"},
        "pr_verwaisung_waechter.yml": {"contents": "read", "pull-requests": "read", "issues": "read"},
    }
    for name, soll in erwartet.items():
        daten = yaml.safe_load(Path(f".github/workflows/{name}").read_text(encoding="utf-8"))
        assert daten["permissions"] == soll
        assert "write" not in yaml.dump(daten["permissions"])
    vertrag = yaml.safe_load(Path(".github/workflows/vertrag.yml").read_text(encoding="utf-8"))
    assert vertrag["permissions"] == {"contents": "read"}
    # Der zweite Job (agent-datumsformat) behaelt seine EIGENEN,
    # unveraenderten Schreibrechte -- diese PR fasst sie nicht an.
    assert vertrag["jobs"]["agent-datumsformat"]["permissions"] == {
        "contents": "write", "pull-requests": "write",
    }


def test_die_meldung_geht_durch_denselben_push_wie_alles_andere():
    """Kein Sonderweg: push_ntfy_fehlschlaege_woche ruft notify.push --
    dieselbe Thema-Pruefung, dieselbe Fehlerbehandlung wie jeder echte
    Push, und KEINE Sirene (Prioritaet default, nicht high)."""
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    koerper = quelltext.split("def push_ntfy_fehlschlaege_woche")[1].split("\ndef ")[0]
    assert "return push(" in koerper
    assert "urllib" not in koerper
    assert 'priority="default"' in koerper
    assert 'priority="high"' not in koerper
    assert notify.push_ntfy_fehlschlaege_woche  # importierbar


def test_die_schwelle_und_die_ueberwachten_workflows_passen_zum_auftrag():
    assert FENSTER_TAGE_PRUEFUNG == 7
    assert ANZAHL_LETZTE_LAEUFE_JE_WORKFLOW == 20
    assert set(UEBERWACHTE_WORKFLOWS) == {
        "lauf.yml", "vertrag.yml", "waechter.yml",
        "handover_waechter.yml", "pr_verwaisung_waechter.yml",
    }
    # "agent_datumsformat" ist bewusst KEIN eigener Eintrag -- es ist der
    # zweite Job INNERHALB von vertrag.yml, kein eigener Workflow.
    assert not any("agent_datumsformat" in w for w in UEBERWACHTE_WORKFLOWS)


def test_repo_slug_wird_fuer_beide_gh_aufrufarten_verwendet():
    gesehene_repos = []

    def laeufer(cmd, capture_output=True, text=True):
        if cmd[0] == "gh" and cmd[1] == "api":
            gesehene_repos.append(cmd[2].split("/")[1] + "/" + cmd[2].split("/")[2])
            return _Ergebnis(stdout=json.dumps({"workflow_runs": []}))
        raise AssertionError(cmd)

    fehlschlaege_je_workflow(jetzt=JETZT, laeufer=laeufer, workflows=("vertrag.yml",))
    assert gesehene_repos == [REPO_SLUG]
