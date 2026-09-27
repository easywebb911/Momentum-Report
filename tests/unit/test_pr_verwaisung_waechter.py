"""Der PR-Verwaisungs-Waechter (pr_verwaisung_waechter.py) — geprueft
ohne Netz und ohne echtes `gh`.

Kernaussagen, die hier festgehalten werden:
  * "Unangetastet" zaehlt Commits, Kommentare UND Reviews -- nicht nur
    Commits/Kommentare woertlich wie im Auftrag genannt (bewusste,
    gemeldete Erweiterung, siehe Modul-Docstring).
  * Werktage, nicht Kalendertage -- Sa/So zaehlen nie.
  * Ab der Schwelle (5 Werktage) kommt GENAU EIN lautloser Push,
    darunter bleibt es STILL.
  * Jede Form von "laesst sich nicht ermitteln" ist ein eigener, lauter
    Befund (roter Lauf).
  * MELDEN, NIE HANDELN: weder Quelltext noch Workflow duerfen
    kommentieren, mergen oder schliessen koennen.
"""

from __future__ import annotations

import datetime as _dt
import subprocess
from pathlib import Path

import pytest
import yaml

from momentum.pr_verwaisung_waechter import (
    SCHWELLE_WERKTAGE,
    letzter_kontakt,
    main,
    offene_prs,
    stand_text,
    verwaiste_prs,
    werktage_seit,
)

Date = _dt.date
DateTime = _dt.datetime


def _run(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ------------------------------------------------------- letzter_kontakt


def test_faellt_auf_erstellung_zurueck_ohne_aktivitaet():
    pr = {"createdAt": "2026-09-01T10:00:00Z", "commits": [], "comments": [], "reviews": []}
    assert letzter_kontakt(pr) == DateTime.fromisoformat("2026-09-01T10:00:00+00:00")


def test_juengster_commit_zaehlt():
    pr = {
        "createdAt": "2026-09-01T10:00:00Z",
        "commits": [{"committedDate": "2026-09-05T08:00:00Z"}],
        "comments": [],
        "reviews": [],
    }
    assert letzter_kontakt(pr) == DateTime.fromisoformat("2026-09-05T08:00:00+00:00")


def test_juengster_kommentar_zaehlt():
    pr = {
        "createdAt": "2026-09-01T10:00:00Z",
        "commits": [{"committedDate": "2026-09-02T00:00:00Z"}],
        "comments": [{"createdAt": "2026-09-10T00:00:00Z"}],
        "reviews": [],
    }
    assert letzter_kontakt(pr) == DateTime.fromisoformat("2026-09-10T00:00:00+00:00")


def test_reine_review_ohne_kommentar_zaehlt_ebenfalls():
    """Bewusste Erweiterung ueber den woertlichen Auftragstext hinaus
    (Kriterium 2, siehe Modul-Docstring): eine Genehmigung ohne
    begleitenden Kommentar ist trotzdem ein echtes Lebenszeichen."""
    pr = {
        "createdAt": "2026-09-01T10:00:00Z",
        "commits": [],
        "comments": [],
        "reviews": [{"submittedAt": "2026-09-12T00:00:00Z"}],
    }
    assert letzter_kontakt(pr) == DateTime.fromisoformat("2026-09-12T00:00:00+00:00")


def test_fehlende_listen_werden_wie_leere_behandelt():
    """`commits`/`comments`/`reviews` koennen bei `gh pr list` als None
    statt als leere Liste auftauchen -- darf nicht abstuerzen."""
    pr = {"createdAt": "2026-09-01T10:00:00Z", "commits": None, "comments": None, "reviews": None}
    assert letzter_kontakt(pr) == DateTime.fromisoformat("2026-09-01T10:00:00+00:00")


# ------------------------------------------------------- werktage_seit


def test_derselbe_tag_ist_null_werktage():
    assert werktage_seit(Date(2026, 9, 7), Date(2026, 9, 7)) == 0


def test_heute_vor_kontakt_ist_null_nie_negativ():
    assert werktage_seit(Date(2026, 9, 10), Date(2026, 9, 7)) == 0


def test_freitag_bis_montag_ist_ein_werktag():
    """Sa/So dazwischen zaehlen nicht -- nur der Montag selbst."""
    freitag = Date(2026, 9, 4)
    montag = Date(2026, 9, 7)
    assert freitag.weekday() == 4 and montag.weekday() == 0
    assert werktage_seit(freitag, montag) == 1


def test_eine_kalenderwoche_ist_fuenf_werktage():
    montag = Date(2026, 9, 7)
    naechster_montag = Date(2026, 9, 14)
    assert werktage_seit(montag, naechster_montag) == 5


def test_zwei_kalenderwochen_sind_zehn_werktage():
    montag = Date(2026, 9, 7)
    uebernaechster_montag = Date(2026, 9, 21)
    assert werktage_seit(montag, uebernaechster_montag) == 10


# ------------------------------------------------------------ offene_prs


def test_offene_prs_liest_die_erwarteten_felder():
    gesehen = []

    def laeufer(cmd, **kw):
        gesehen.append(cmd)
        return _run(stdout="[]")

    offene, grund = offene_prs(laeufer=laeufer)
    assert grund is None and offene == []
    assert gesehen == [[
        "gh", "pr", "list",
        "--state", "open",
        "--limit", "200",
        "--json", "number,title,createdAt,commits,comments,reviews",
    ]]


def test_gh_fehlschlag_ist_ein_befund():
    laeufer = lambda *a, **kw: _run(returncode=1, stderr="HTTP 403: rate limit exceeded")
    offene, grund = offene_prs(laeufer=laeufer)
    assert offene is None
    assert grund is not None and "rate limit" in grund


def test_kaputtes_json_ist_ein_befund():
    laeufer = lambda *a, **kw: _run(stdout="{nicht valide")
    offene, grund = offene_prs(laeufer=laeufer)
    assert offene is None and grund is not None


def test_gh_liess_sich_nicht_aufrufen_ist_ein_befund():
    def laeufer(*a, **kw):
        raise OSError("gh nicht gefunden")

    offene, grund = offene_prs(laeufer=laeufer)
    assert offene is None
    assert grund is not None and "gh nicht gefunden" in grund


# -------------------------------------------------------- verwaiste_prs


HEUTE = Date(2026, 9, 21)  # ein Montag


def _pr(nummer: int, letzter_kontakt_iso: str, titel: str = "irgendein PR", erstellt_iso: str | None = None) -> dict:
    return {
        "number": nummer,
        "title": titel,
        "createdAt": erstellt_iso or letzter_kontakt_iso,
        "commits": [{"committedDate": letzter_kontakt_iso}],
        "comments": [],
        "reviews": [],
    }


def test_unter_der_schwelle_wird_nicht_gemeldet():
    # Montag vor HEUTE (7.9.) bis HEUTE (21.9.) = 10 Werktage -- ueber der
    # Schwelle. Ein PR, der genau 5 Werktage zurueckliegt, ist an der
    # Grenze und darf NICHT gemeldet werden (> statt >=).
    pr = _pr(1, "2026-09-14T00:00:00Z")  # Montag, genau 5 Werktage vor HEUTE
    verwaist, grund = verwaiste_prs([pr], HEUTE)
    assert grund is None
    assert verwaist == []


def test_ueber_der_schwelle_wird_gemeldet():
    pr = _pr(2, "2026-09-11T00:00:00Z", titel="knapp drueber")  # Freitag, 6 Werktage
    verwaist, grund = verwaiste_prs([pr], HEUTE)
    assert grund is None
    assert len(verwaist) == 1
    nummer, titel, werktage, kalendertage = verwaist[0]
    assert (nummer, titel) == (2, "knapp drueber")
    assert werktage == 6


def test_ergebnis_ist_nach_pr_nummer_sortiert():
    prs = [_pr(57, "2026-09-01T00:00:00Z"), _pr(53, "2026-09-01T00:00:00Z"), _pr(55, "2026-09-01T00:00:00Z")]
    verwaist, _ = verwaiste_prs(prs, HEUTE)
    assert [n for n, *_ in verwaist] == [53, 55, 57]


def test_kalendertage_seit_erstellung_werden_mitgemeldet():
    pr = _pr(3, "2026-09-11T00:00:00Z", erstellt_iso="2026-08-01T00:00:00Z")
    verwaist, _ = verwaiste_prs([pr], HEUTE)
    _, _, _, kalendertage = verwaist[0]
    assert kalendertage == (HEUTE - Date(2026, 8, 1)).days


def test_fehlendes_createdat_ist_ein_befund():
    pr = {"number": 9, "title": "x", "createdAt": None, "commits": [], "comments": [], "reviews": []}
    verwaist, grund = verwaiste_prs([pr], HEUTE)
    assert verwaist is None
    assert grund is not None and "#9" in grund


# ------------------------------------------------------------ stand_text


def test_stand_text_nennt_anzahl_nummern_und_werktage():
    text = stand_text([(51, "Titel A", 6, 30), (52, "Titel B", 12, 100)])
    assert "2 offene(r) PR(s)" in text
    assert str(SCHWELLE_WERKTAGE) in text
    assert "#51" in text and "Titel A" in text and "6 Werktag" in text and "30 Kalendertag" in text
    assert "#52" in text and "Titel B" in text and "12 Werktag" in text and "100 Kalendertag" in text


def test_stand_text_ist_deterministisch():
    verwaist = [(51, "a", 6, 10), (52, "b", 7, 20)]
    assert stand_text(verwaist) == stand_text(list(verwaist))


# -------------------------------------------------------------- main()


def _main_mit(verwaist_ergebnis, *, melder, offene=None):
    return main(
        ["--heute", HEUTE.isoformat()],
        melder=melder,
        ermittle_prs=lambda: (offene if offene is not None else [{"number": 1}], None),
    )


def test_main_bleibt_still_ohne_verwaiste_prs(monkeypatch):
    import momentum.pr_verwaisung_waechter as modul

    monkeypatch.setattr(modul, "verwaiste_prs", lambda offene, heute: ([], None))
    gerufen = []
    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_prs=lambda: ([{"number": 1, "createdAt": "2026-09-20T00:00:00Z"}], None),
    )
    assert code == 0
    assert gerufen == []


def test_main_meldet_ab_der_schwelle(monkeypatch):
    import momentum.pr_verwaisung_waechter as modul

    verwaist = [(51, "Titel", 6, 30)]
    monkeypatch.setattr(modul, "verwaiste_prs", lambda offene, heute: (verwaist, None))
    gerufen = []
    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_prs=lambda: ([{"number": 51}], None),
    )
    assert code == 0, "der Push ist das Signal, kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "#51" in gerufen[0]


def test_ermittlung_der_offenen_prs_fehlgeschlagen_ist_ein_lauter_befund():
    gerufen = []
    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_prs=lambda: (None, "gh ist am Limit"),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "gh ist am Limit" in gerufen[0]


def test_verwaiste_prs_fehlgeschlagen_ist_ein_lauter_befund(monkeypatch):
    import momentum.pr_verwaisung_waechter as modul

    monkeypatch.setattr(modul, "verwaiste_prs", lambda offene, heute: (None, "unlesbares Datum"))
    gerufen = []
    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_prs=lambda: ([{"number": 1}], None),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "unlesbares Datum" in gerufen[0]


def test_ein_werfender_push_laesst_den_waechter_nicht_abstuerzen(monkeypatch, capsys):
    import momentum.pr_verwaisung_waechter as modul

    monkeypatch.setattr(modul, "verwaiste_prs", lambda offene, heute: ([(51, "a", 6, 30)], None))

    def wirft(_text):
        raise OSError("keine Verbindung")

    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=wirft,
        ermittle_prs=lambda: ([{"number": 51}], None),
    )
    assert code == 0
    assert "Push fehlgeschlagen" in capsys.readouterr().out


def test_der_gesund_push_geht_durch_dieselbe_leise_stufe():
    import momentum.notify as notify

    quelltext = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    koerper = quelltext.split("def push_pr_verwaist")[1].split("\ndef ")[0]
    assert 'priority="min"' in koerper
    assert "urllib" not in koerper
    assert notify.PRIORITIES["min"] == 1
    assert "return push(" in koerper
    assert notify.push_pr_verwaist


# ------------------------------------- Regressionsbeleg: simulierter Fall


def test_ein_simulierter_alt_liegen_gebliebener_pr_loest_aus():
    """Nachweis (Kriterium 3): ein PR, dessen letzter Kontakt ueber zwei
    volle Kalenderwochen zurueckliegt (10 Werktage), muss zuverlaessig
    erkannt werden -- der reale Fall, den dieser Waechter abdecken soll
    (ein liegen gebliebener Manual-Merge-PR)."""
    alter_pr = _pr(
        40,
        "2026-09-07T09:00:00Z",  # Montag, zwei Wochen vor HEUTE
        titel="fix: zu frueh ausgeloesten Lauf haerten",
        erstellt_iso="2026-09-05T09:00:00Z",
    )
    gerufen = []
    code = main(
        ["--heute", HEUTE.isoformat()],
        melder=lambda t: gerufen.append(t) or True,
        ermittle_prs=lambda: ([alter_pr], None),
    )
    assert code == 0
    assert len(gerufen) == 1
    assert "#40" in gerufen[0]
    assert "10 Werktag" in gerufen[0]


def test_determinismus_gleiche_eingaben_gleiche_zaehlung():
    prs = [_pr(51, "2026-09-01T00:00:00Z"), _pr(52, "2026-09-11T00:00:00Z")]
    erg1, _ = verwaiste_prs(prs, HEUTE)
    erg2, _ = verwaiste_prs(list(prs), HEUTE)
    assert erg1 == erg2


def test_die_schwelle_ist_die_aus_dem_auftrag():
    assert SCHWELLE_WERKTAGE == 5


# --------------------------------------------- Melden, nie Handeln


def test_der_workflow_kann_nur_lesen_nie_kommentieren_mergen_schliessen():
    daten = yaml.safe_load(
        Path(".github/workflows/pr_verwaisung_waechter.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {
        "contents": "read", "pull-requests": "read", "issues": "read",
    }
    assert "write" not in yaml.dump(daten["permissions"])
    zeitplaene = daten[True]["schedule"] if True in daten else daten["on"]["schedule"]
    assert len(zeitplaene) == 1
    lauf_waechter = yaml.safe_load(Path(".github/workflows/waechter.yml").read_text(encoding="utf-8"))
    lauf_zeitplaene = lauf_waechter[True]["schedule"] if True in lauf_waechter else lauf_waechter["on"]["schedule"]
    assert zeitplaene[0]["cron"] == lauf_zeitplaene[0]["cron"]
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "workflow_dispatch" in ausloeser
    text = Path(".github/workflows/pr_verwaisung_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text


def test_der_waechter_code_kann_weder_schreiben_noch_pr_beruehren():
    """Statischer Nie-Handeln-Test, analog zu handover_waechter.py."""
    quelltext = Path("src/momentum/pr_verwaisung_waechter.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "pr comment", "pr merge", "pr close", "pr edit", "pr review",
        "create_pull_request", "merge_pull_request", "add_issue_comment",
        "git commit", "git push", "git add",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"
    assert "gh pr list" in code
