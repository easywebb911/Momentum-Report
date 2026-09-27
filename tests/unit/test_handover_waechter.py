"""Der Doku-Waechter (handover_waechter.py) — geprueft ohne Netz und
ohne echtes `git`/`gh`.

Kernaussagen, die hier festgehalten werden:
  * Die Zaehlung ist deterministisch: gleicher Commit-Zeitpunkt und
    gleiche PR-Liste ergeben immer dieselbe Anzahl ungepflegter PRs.
  * Ab der Schwelle (4) kommt GENAU EIN lautloser Push, darunter bleibt
    es STILL (kein Push).
  * Jede Form von "laesst sich nicht ermitteln" ist ein eigener,
    lauter Befund (roter Lauf), nie ein Achselzucken.
  * Der reale Fall dieser Woche (#51–#57) haette angeschlagen.
  * MELDEN, NIE HANDELN: weder der Quelltext noch der Workflow duerfen
    schreiben oder einen PR oeffnen koennen.
"""

from __future__ import annotations

import datetime as _dt
import subprocess
from pathlib import Path

import pytest
import yaml

from momentum.handover_waechter import (
    PR_LISTEN_LIMIT,
    SCHWELLE_PRS,
    gemergte_prs_seit,
    letzter_handover_commit,
    main,
    stand_text,
)

DateTime = _dt.datetime


def _run(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ------------------------------------------------ letzter_handover_commit


def test_liest_das_committer_datum_aus_git_log():
    laeufer = lambda *a, **kw: _run(stdout="2026-09-17T13:01:47+02:00\n")
    zeitpunkt, grund = letzter_handover_commit(Path("SESSION_HANDOVER.md"), laeufer=laeufer)
    assert grund is None
    assert zeitpunkt == DateTime.fromisoformat("2026-09-17T13:01:47+02:00")


def test_git_fehlschlag_ist_ein_befund_kein_ratewert():
    laeufer = lambda *a, **kw: _run(returncode=128, stderr="fatal: not a git repository")
    zeitpunkt, grund = letzter_handover_commit(laeufer=laeufer)
    assert zeitpunkt is None
    assert grund is not None and "rc=128" in grund


def test_leere_ausgabe_ist_ein_befund():
    """Kein Commit gefunden (z. B. flacher Klon) -- niemals stillschweigend
    ein Datum raten."""
    laeufer = lambda *a, **kw: _run(stdout="\n")
    zeitpunkt, grund = letzter_handover_commit(laeufer=laeufer)
    assert zeitpunkt is None
    assert grund is not None and "keinen Commit" in grund


def test_unlesbares_datum_ist_ein_befund():
    laeufer = lambda *a, **kw: _run(stdout="nicht-mal-ein-datum\n")
    zeitpunkt, grund = letzter_handover_commit(laeufer=laeufer)
    assert zeitpunkt is None and grund is not None


def test_git_ist_der_exakte_befehl():
    """Der Aufruf muss `--` vor dem Pfad tragen (kein Flag-Verwechsler)
    und genau die Datei nennen, die geprueft wird."""
    gesehen = []

    def laeufer(cmd, **kw):
        gesehen.append(cmd)
        return _run(stdout="2026-09-11T05:25:33+00:00\n")

    letzter_handover_commit(Path("SESSION_HANDOVER.md"), laeufer=laeufer)
    assert gesehen == [["git", "log", "-1", "--format=%cI", "--", "SESSION_HANDOVER.md"]]


# ----------------------------------------------------- gemergte_prs_seit


SEIT = DateTime.fromisoformat("2026-09-11T05:25:33+00:00")


def _pr(nummer: int, merged_at: str, titel: str = "irgendein PR") -> dict:
    return {"number": nummer, "title": titel, "mergedAt": merged_at}


def test_zaehlt_nur_prs_nach_dem_stichzeitpunkt():
    daten = [
        _pr(50, "2026-09-11T05:25:33+00:00", "vor/am Stichzeitpunkt"),  # nicht >, faellt raus
        _pr(51, "2026-09-11T06:00:00+00:00"),
        _pr(49, "2026-08-10T00:00:00+00:00"),  # laengst vorher
    ]
    import json

    laeufer = lambda *a, **kw: _run(stdout=json.dumps(daten))
    ungepflegt, grund = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert grund is None
    assert ungepflegt == [(51, "irgendein PR")]


def test_z_mit_utc_wird_verstanden():
    """gh liefert mergedAt mit 'Z'-Suffix -- muss trotzdem vergleichbar sein."""
    import json

    laeufer = lambda *a, **kw: _run(stdout=json.dumps([_pr(51, "2026-09-11T06:00:00Z")]))
    ungepflegt, grund = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert grund is None
    assert ungepflegt == [(51, "irgendein PR")]


def test_ergebnis_ist_nach_pr_nummer_sortiert():
    import json

    daten = [
        _pr(57, "2026-09-17T13:00:00Z"),
        _pr(53, "2026-09-17T04:49:32Z"),
        _pr(55, "2026-09-17T13:05:00Z"),
    ]
    laeufer = lambda *a, **kw: _run(stdout=json.dumps(daten))
    ungepflegt, _ = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert [n for n, _ in ungepflegt] == [53, 55, 57]


def test_gh_fehlschlag_ist_ein_befund():
    laeufer = lambda *a, **kw: _run(returncode=1, stderr="HTTP 403: rate limit exceeded")
    ungepflegt, grund = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert ungepflegt is None
    assert grund is not None and "rate limit" in grund


def test_kaputtes_json_ist_ein_befund():
    laeufer = lambda *a, **kw: _run(stdout="{nicht valide")
    ungepflegt, grund = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert ungepflegt is None and grund is not None


def test_fehlendes_mergedat_ist_ein_befund():
    """Widerspruch gemeldet statt geraten (Kriterium 2): ein PR ohne
    brauchbares mergedAt laesst sich nicht sauber gegen den
    Stichzeitpunkt abgrenzen -- das wird als Befund sichtbar, nicht als
    0 oder 'egal' behandelt."""
    import json

    laeufer = lambda *a, **kw: _run(stdout=json.dumps([{"number": 99, "title": "x", "mergedAt": None}]))
    ungepflegt, grund = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert ungepflegt is None
    assert grund is not None and "#99" in grund


def test_gh_befehl_fragt_gemergte_prs_gegen_main_ab():
    gesehen = []

    def laeufer(cmd, **kw):
        gesehen.append(cmd)
        return _run(stdout="[]")

    gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert gesehen == [[
        "gh", "pr", "list",
        "--state", "merged",
        "--base", "main",
        "--limit", str(PR_LISTEN_LIMIT),
        "--json", "number,title,mergedAt",
    ]]


# --------------------------------------------------------- stand_text


def test_stand_text_nennt_anzahl_und_nummern():
    text = stand_text([(51, "a"), (52, "b"), (53, "c"), (54, "d")])
    assert "4 gemergte PR(s)" in text
    assert "#51" in text and "#52" in text and "#53" in text and "#54" in text
    assert str(SCHWELLE_PRS) in text


def test_stand_text_ist_deterministisch():
    ungepflegt = [(51, "a"), (57, "b")]
    assert stand_text(ungepflegt) == stand_text(list(ungepflegt))


# -------------------------------------------------------------- main()


def _main_mit(ungepflegt_prs, *, melder):
    """main() mit festgenagelten Ermittlungs-Ergebnissen -- kein
    Subprozess beteiligt."""
    seit = SEIT
    return main(
        [],
        melder=melder,
        ermittle_commit=lambda _pfad: (seit, None),
        ermittle_prs=lambda _seit: (ungepflegt_prs, None),
    )


def test_unter_der_schwelle_bleibt_es_still():
    gerufen = []
    code = _main_mit([(51, "a"), (52, "b")], melder=lambda t: gerufen.append(t) or True)
    assert code == 0
    assert gerufen == [], "unter der Schwelle darf kein Push gehen"


def test_ab_der_schwelle_kommt_genau_ein_push():
    fuenf = [(51, "a"), (52, "b"), (53, "c"), (54, "d"), (55, "e")]
    gerufen = []
    code = _main_mit(fuenf, melder=lambda t: gerufen.append(t) or True)
    assert code == 0, "der Push ist das Signal, kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "5 gemergte PR(s)" in gerufen[0]
    for nummer in (51, 52, 53, 54, 55):
        assert f"#{nummer}" in gerufen[0]


def test_genau_an_der_schwelle_loest_bereits_aus():
    vier = [(51, "a"), (52, "b"), (53, "c"), (54, "d")]
    gerufen = []
    code = _main_mit(vier, melder=lambda t: gerufen.append(t) or True)
    assert code == 0
    assert len(gerufen) == 1


def test_ein_darunter_bleibt_still():
    drei = [(51, "a"), (52, "b"), (53, "c")]
    gerufen = []
    code = _main_mit(drei, melder=lambda t: gerufen.append(t) or True)
    assert code == 0
    assert gerufen == []


def test_commit_nicht_ermittelbar_ist_ein_lauter_befund():
    gerufen = []
    code = main(
        [],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_commit=lambda _pfad: (None, "git ist kaputt"),
        ermittle_prs=lambda _seit: pytest.fail("darf bei kaputtem Commit nie aufgerufen werden"),
    )
    assert code == 1, "kann den Zustand nicht bestimmen -> roter Lauf"
    assert len(gerufen) == 1
    assert "git ist kaputt" in gerufen[0]


def test_prs_nicht_ermittelbar_ist_ein_lauter_befund():
    gerufen = []
    code = main(
        [],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_commit=lambda _pfad: (SEIT, None),
        ermittle_prs=lambda _seit: (None, "gh ist am Limit"),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "gh ist am Limit" in gerufen[0]


def test_ein_gescheiterter_push_aendert_den_exit_code_nicht(capsys):
    """Der Push ist das eine Signal in diesem Waechter -- schlaegt er
    fehl, bleibt trotzdem geloggt, was dagewesen waere (kein zweites,
    verstecktes Signal noetig, anders als beim Lauf-Waechter mit seinem
    unabhaengigen roten Lauf im Alarmfall)."""
    code = _main_mit(
        [(51, "a"), (52, "b"), (53, "c"), (54, "d")],
        melder=lambda _t: False,
    )
    assert code == 0
    assert "NICHT verschickt" in capsys.readouterr().out


def test_ein_werfender_push_laesst_den_waechter_nicht_abstuerzen(capsys):
    """Der Push ist NIE wichtiger als das Wachen selbst (dasselbe Prinzip
    wie beim Lauf-Waechter): ein Melder, der wirft statt False
    zurueckzugeben, darf den Waechter nicht mit einer Exception beenden."""

    def wirft(_text):
        raise OSError("keine Verbindung")

    code = _main_mit([(51, "a"), (52, "b"), (53, "c"), (54, "d")], melder=wirft)
    assert code == 0
    assert "Push fehlgeschlagen" in capsys.readouterr().out


def test_ein_werfender_push_im_alarmfall_laesst_trotzdem_rot_enden(capsys):
    def wirft(_text):
        raise OSError("keine Verbindung")

    code = main(
        [],
        melder=wirft,
        ermittle_commit=lambda _pfad: (None, "git ist kaputt"),
        ermittle_prs=lambda _seit: pytest.fail("darf hier nie aufgerufen werden"),
    )
    assert code == 1
    assert "Push fehlgeschlagen" in capsys.readouterr().out


def test_der_gesund_push_geht_durch_dieselbe_leise_stufe():
    """Dieselbe Verbindung wie beim Lauf-Waechter: die Meldung darf nie
    ueber den klingelnden Kanal gehen."""
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    koerper = quelltext.split("def push_handover_pflege_faellig")[1].split("\ndef ")[0]
    assert 'priority="min"' in koerper
    assert "urllib" not in koerper, "kein eigener Sendeweg"
    assert notify.PRIORITIES["min"] == 1


def test_der_push_geht_durch_denselben_weg_wie_alles_andere():
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    koerper = quelltext.split("def push_handover_pflege_faellig")[1].split("\ndef ")[0]
    assert "return push(" in koerper
    assert notify.push_handover_pflege_faellig  # importierbar


# ------------------------------------- Regressionsbeleg: der reale Fall


def test_der_reale_51_bis_57_fall_haette_angeschlagen():
    """Nachweis (Kriterium 3): mit den echten Commit-Zeitpunkten dieser
    Woche (per `git log --format=%cI` auf den tatsaechlichen Merge-
    Landungs-Commits nachgemessen, siehe SESSION_HANDOVER.md §2-Tabelle)
    haette dieser Waechter VOR PR #57 -- naemlich bereits beim vierten
    ungepflegten PR (#54) -- Meldung erstattet, nicht erst nachtraeglich
    beim Aufraeumen.

    Committer-Datum statt GitHub-`mergedAt` verwendet, weil in dieser
    Umgebung kein Live-API-Zugriff besteht -- fuer Squash-/Fast-Forward-
    Merges (das durchgaengige Muster dieser sieben PRs) faellt das
    Committer-Datum mit dem tatsaechlichen Landungszeitpunkt zusammen,
    genau das, was `gemergte_prs_seit` im echten Lauf ueber `mergedAt`
    vergleicht."""
    # Commit, der SESSION_HANDOVER.md zuletzt auf den Stand nach PR #49
    # brachte (PR #50, Merge-Commit dfb17fa, Committer-Datum real).
    letzter_handover = DateTime.fromisoformat("2026-09-11T05:25:33+00:00")

    # Die sieben seither gemergten PRs, reale Committer-Daten der
    # jeweiligen Merge-Landungs-Commits (2b648c3/37cfcb2/62223af/72d301e/
    # 4c822dd/9538477/4782de8), per `git log --format=%cI` nachgemessen.
    reale_prs = [
        (51, "2026-09-11T07:30:58+02:00"),
        (52, "2026-09-12T00:40:31+02:00"),
        (53, "2026-09-17T13:33:56+02:00"),
        (54, "2026-09-17T13:45:44+02:00"),
        (55, "2026-09-17T15:09:39+02:00"),
        (56, "2026-09-17T15:59:46+02:00"),
        (57, "2026-09-17T20:06:48+02:00"),
    ]

    gerufen = []
    code = main(
        [],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_commit=lambda _pfad: (letzter_handover, None),
        ermittle_prs=lambda seit: (
            [(n, f"PR #{n}") for n, merged in reale_prs
             if DateTime.fromisoformat(merged) > seit],
            None,
        ),
    )
    assert code == 0
    assert len(gerufen) == 1
    for nummer in (51, 52, 53, 54, 55, 56, 57):
        assert f"#{nummer}" in gerufen[0]
    assert "7 gemergte PR(s)" in gerufen[0]


def test_determinismus_gleiche_eingaben_gleiche_zaehlung():
    """Kriterium 7: derselbe Commit-Zeitpunkt und dieselbe PR-Liste
    ergeben bei jedem Aufruf exakt dieselbe Anzahl und Reihenfolge."""
    import json

    daten = [
        {"number": 55, "title": "b", "mergedAt": "2026-09-17T13:09:39Z"},
        {"number": 51, "title": "a", "mergedAt": "2026-09-11T05:41:12Z"},
    ]
    laeufer = lambda *a, **kw: _run(stdout=json.dumps(daten))
    erg1, _ = gemergte_prs_seit(SEIT, laeufer=laeufer)
    erg2, _ = gemergte_prs_seit(SEIT, laeufer=laeufer)
    assert erg1 == erg2 == [(51, "a"), (55, "b")]


def test_die_schwelle_ist_die_aus_dem_auftrag():
    assert SCHWELLE_PRS == 4


# --------------------------------------------- Melden, nie Handeln


def test_der_workflow_kann_nicht_schreiben_und_keinen_pr_oeffnen():
    daten = yaml.safe_load(
        Path(".github/workflows/handover_waechter.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read", "pull-requests": "read"}
    zeitplaene = daten[True]["schedule"] if True in daten else daten["on"]["schedule"]
    assert len(zeitplaene) == 1
    # Derselbe Cron-Slot wie der Lauf-Waechter -- gemeinsamer Rhythmus.
    lauf_waechter = yaml.safe_load(Path(".github/workflows/waechter.yml").read_text(encoding="utf-8"))
    lauf_zeitplaene = lauf_waechter[True]["schedule"] if True in lauf_waechter else lauf_waechter["on"]["schedule"]
    assert zeitplaene[0]["cron"] == lauf_zeitplaene[0]["cron"]
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "workflow_dispatch" in ausloeser
    text = Path(".github/workflows/handover_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text
    # Keine Schreibrechte irgendeiner Art -- kein "write" im ganzen Block.
    assert "write" not in yaml.dump(daten["permissions"])


def test_der_waechter_code_kann_weder_schreiben_noch_einen_pr_oeffnen():
    """Statischer Nie-Handeln-Test, analog zum Lauf-Waechter (dort ueber
    die Workflow-Rechte allein) -- hier zusaetzlich direkt am Quelltext,
    weil dieses Modul (anders als waechter.py) `subprocess` importiert
    und deshalb technisch in der Lage WAERE, git/gh-Schreibbefehle
    abzusetzen. Der Test verbietet genau das."""
    quelltext = Path("src/momentum/handover_waechter.py").read_text(encoding="utf-8")
    # Modul-Docstring abschneiden: er ERKLAERT die Grenze in Prosa (und
    # nennt "gh pr create" dabei woertlich als Beispiel dessen, was NICHT
    # passieren darf) -- geprueft wird nur der tatsaechliche Code danach.
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",  # kein Dateizugriff zum Schreiben
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "pr create", "pr merge", "pr edit",
        "create_pull_request", "merge_pull_request",
        "git commit", "git push", "git add",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"
    # Positiv-Gegenprobe: der Test selbst darf nicht versehentlich nichts
    # pruefen, weil z. B. die Datei leer waere.
    assert "gh pr list" in code
    assert "git log" in code
