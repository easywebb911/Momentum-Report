"""ZIEL-MECHANIK: ein Platzhalter-Ranking kann unter keinen Umstaenden entstehen.

Das ist der Test, auf den es ankommt. Er beweist nicht nur "es wird keins
geschrieben", sondern die staerkere Aussage: die Kursdaten, aus denen ein
Ranking entstehen koennte, werden gar nicht erst angefragt. Der Riegel liegt
VOR dem Datenabruf, nicht dahinter.

Geprueft werden alle Wege, auf denen ein ungeprueftes Universum ins Werkzeug
kommen koennte:
  * die ausgelieferte Platzhalter-Datei
  * eine Datei, der die Statuszeile fehlt (default-deny!)
  * eine Datei mit irgendeinem anderen Status
  * eine halb geschriebene Datei
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import replace

import pytest

from momentum import run as run_modul
from momentum.config import MARKETS_BY_KEY
from momentum.universe import UniverseNotReady, load_universe
from tests.conftest import index_series, make_downloader, sample_series, write_universe

Date = _dt.date
STICHTAG = Date(2026, 7, 31)

KOPF = "# Universum: HDAX\n# Herkunft: irgendwo\n# Stand: 2026-07-31\n"

UNGEPRUEFTE_DATEIEN = {
    "Platzhalter": KOPF + "# STATUS: PLACEHOLDER\n",
    "ohne Statuszeile": KOPF + "AAA\tFirma AAA\nBBB\tFirma BBB\n",
    "fremder Status": KOPF + "# STATUS: ENTWURF\nAAA\tFirma AAA\n",
    "leerer Status": KOPF + "# STATUS:\nAAA\tFirma AAA\n",
    "halb geschrieben": KOPF + "# STATUS: VERIFI\nAAA\tFirma AAA\n",
}


@pytest.mark.parametrize("beschreibung,inhalt", sorted(UNGEPRUEFTE_DATEIEN.items()))
def test_ungepruefte_universen_werden_abgelehnt(tmp_path, beschreibung, inhalt):
    pfad = tmp_path / "u.txt"
    pfad.write_text(inhalt, encoding="utf-8")
    with pytest.raises(UniverseNotReady):
        load_universe(pfad)


def test_nur_ein_ausdrueckliches_verified_kommt_durch(tmp_path):
    pfad = write_universe(tmp_path / "u.txt", ["AAA"], status="VERIFIED")
    assert load_universe(pfad).status == "VERIFIED"


def test_die_universen_im_repo_sind_entweder_geprueft_oder_gesperrt():
    """Default-deny, angewandt auf die Dateien, die wirklich im Repo liegen.

    Frueher stand hier die schaerfere Aussage „beide sind Platzhalter". Die
    war nur so lange richtig, wie noch gar kein Universum befuellt war --
    mit dem ersten erfolgreichen Bootstrap-Lauf (US, 02.08.2026, 503 Titel)
    ist sie falsch geworden, obwohl nichts kaputt war. Ein Test, der beim
    bestimmungsgemaessen Fortschritt umkippt, misst das Falsche.

    Die Aussage, die dauerhaft gelten MUSS, ist diese: kein Zwischending.
    Entweder eine Datei traegt ausdruecklich VERIFIED und ist dann auch
    wirklich befuellt -- oder sie wird abgelehnt. Ein drittes gibt es nicht.
    """
    gesehen = {}
    for pfad in ("universe/universe_us.txt", "universe/universe_de.txt"):
        try:
            universum = load_universe(pfad)
        except UniverseNotReady as abgelehnt:
            gesehen[pfad] = "abgelehnt"
            assert "STATUS" in str(abgelehnt) or "PLATZHALTER" in str(abgelehnt)
            continue
        gesehen[pfad] = "VERIFIED"
        assert universum.status == "VERIFIED"
        assert universum.tickers, f"{pfad}: VERIFIED, aber ohne einen einzigen Titel"
        assert universum.origin and "NOCH NICHT" not in universum.origin
    assert set(gesehen.values()) <= {"VERIFIED", "abgelehnt"}


# --------------------------------------------------------------------------
# Der eigentliche Beweis
# --------------------------------------------------------------------------


@pytest.mark.parametrize("beschreibung,inhalt", sorted(UNGEPRUEFTE_DATEIEN.items()))
def test_kein_ranking_und_kein_einziger_kursabruf(tmp_path, monkeypatch, beschreibung, inhalt):
    """Der Riegel liegt VOR dem Datenabruf — nicht dahinter."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    for key in ("us", "de"):
        (tmp_path / "universe" / f"universe_{key}.txt").write_text(inhalt, encoding="utf-8")
    maerkte = tuple(
        replace(MARKETS_BY_KEY[k], universe_file=f"universe/universe_{k}.txt")
        for k in ("us", "de")
    )
    monkeypatch.setattr(run_modul, "MARKETS", maerkte)

    abrufe: list[list[str]] = []
    echt = make_downloader({**sample_series(), "^SP500TR": index_series()})

    def mitschnitt(batch, start, end):
        abrufe.append(list(batch))
        return echt(batch, start, end)

    with pytest.raises(UniverseNotReady):
        run_modul.main(["--today", STICHTAG.isoformat()], downloader=mitschnitt)

    assert abrufe == [], f"{beschreibung}: es wurden Kurse abgerufen"
    assert not (tmp_path / "data").exists(), f"{beschreibung}: data/ entstand"
    assert not list(tmp_path.glob("data/rankings/*.json"))
    assert not (tmp_path / "docs").exists(), f"{beschreibung}: eine Seite entstand"


def test_verweigerung_ist_laut_log_zeile_und_fehlschlag_push(tmp_path, monkeypatch, capsys):
    """Laut heisst: deutliche Zeile im Protokoll UND Push mit dem echten Grund."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    for key in ("us", "de"):
        (tmp_path / "universe" / f"universe_{key}.txt").write_text(
            UNGEPRUEFTE_DATEIEN["Platzhalter"], encoding="utf-8"
        )
    monkeypatch.setattr(
        run_modul,
        "MARKETS",
        tuple(
            replace(MARKETS_BY_KEY[k], universe_file=f"universe/universe_{k}.txt")
            for k in ("us", "de")
        ),
    )
    gemeldet: list[str] = []
    monkeypatch.setattr(run_modul, "push_run_failed", lambda grund, **kw: gemeldet.append(grund))
    monkeypatch.setattr("sys.argv", ["momentum.run"])

    assert run_modul.cli() == 2

    ausgabe = capsys.readouterr().out
    assert "LAUF ABGEBROCHEN" in ausgabe
    assert "PLATZHALTER" in ausgabe
    assert "nichts veroeffentlicht und nichts eingefroren" in ausgabe

    assert len(gemeldet) == 1, "genau ein Fehlschlag-Push"
    assert "PLATZHALTER" in gemeldet[0]
    assert "universe_us.txt" in gemeldet[0], "der Push nennt die konkrete Datei"


def test_in_actions_erscheint_zusaetzlich_eine_fehler_annotation(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    (tmp_path / "universe" / "universe_us.txt").write_text(
        UNGEPRUEFTE_DATEIEN["Platzhalter"], encoding="utf-8"
    )
    monkeypatch.setattr(
        run_modul,
        "MARKETS",
        (replace(MARKETS_BY_KEY["us"], universe_file="universe/universe_us.txt"),),
    )
    monkeypatch.setattr(run_modul, "push_run_failed", lambda *a, **k: True)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr("sys.argv", ["momentum.run"])

    assert run_modul.cli() == 2
    assert "::error title=Lauf abgebrochen::" in capsys.readouterr().out


def test_nach_dem_universum_lauf_entsteht_das_ranking_rueckwirkend(tmp_path, monkeypatch):
    """Die Gegenprobe: mit geprueftem Universum kommt der 31.07. rueckwirkend.

    Der Lauf findet am 05.08. statt — der Stichtag bleibt trotzdem der letzte
    Handelstag im Juli, und das Ergebnis ist dasselbe wie bei einem Lauf am
    Stichtag selbst.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    ticker = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    maerkte = []
    for key in ("us", "de"):
        pfad = write_universe(tmp_path / "universe" / f"universe_{key}.txt", ticker)
        maerkte.append(replace(MARKETS_BY_KEY[key], universe_file=str(pfad)))
    monkeypatch.setattr(run_modul, "MARKETS", tuple(maerkte))
    monkeypatch.setattr(run_modul, "push_new_ranking", lambda *a, **k: True)

    serien = sample_series()
    serien["^SP500TR"] = index_series()
    serien["^GDAXI"] = index_series()

    assert run_modul.main(["--today", "2026-08-05"], downloader=make_downloader(serien)) == 0
    datei = tmp_path / "data/rankings/us_2026-07.json"
    assert datei.exists()
    nachtraeglich = datei.read_bytes()

    # Gegenprobe in einem zweiten Verzeichnis: Lauf am Stichtag selbst
    zweit = tmp_path / "zweit"
    (zweit / "universe").mkdir(parents=True)
    maerkte2 = []
    for key in ("us", "de"):
        pfad = write_universe(zweit / "universe" / f"universe_{key}.txt", ticker)
        maerkte2.append(replace(MARKETS_BY_KEY[key], universe_file=str(pfad)))
    monkeypatch.chdir(zweit)
    monkeypatch.setattr(run_modul, "MARKETS", tuple(maerkte2))
    assert run_modul.main(["--today", "2026-07-31"], downloader=make_downloader(serien)) == 0

    am_stichtag = (zweit / "data/rankings/us_2026-07.json").read_bytes()
    assert nachtraeglich == am_stichtag, (
        "rueckwirkend gebildet muss Zeichen fuer Zeichen dasselbe ergeben "
        "wie am Stichtag gebildet"
    )


# --------------------------------------------------------------------------
# Widerspruchs-Pruefung: kollidiert das Status-Gatter mit anderen Regeln?
# --------------------------------------------------------------------------


def test_gatter_kommt_vor_der_mindestabdeckung(tmp_path, monkeypatch):
    """Kein Konflikt mit der 90-%-Regel — das Gatter greift frueher.

    Die Mindestabdeckung vergleicht gelieferte Kurse mit der Universumsgroesse.
    Sie kann per Bauart nie auf ein ungepruefte Universum angewandt werden,
    weil ohne VERIFIED gar keine Kurse geholt werden.
    """
    from momentum.config import MIN_UNIVERSE_COVERAGE

    assert 0 < MIN_UNIVERSE_COVERAGE <= 1
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    pfad = tmp_path / "universe" / "u.txt"
    pfad.write_text(UNGEPRUEFTE_DATEIEN["Platzhalter"], encoding="utf-8")
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(pfad))

    with pytest.raises(UniverseNotReady):
        run_modul.process_market(markt, STICHTAG, downloader=make_downloader({}))


def test_zurueckgesetztes_universum_stoppt_AUCH_die_kursanzeige(tmp_path, monkeypatch):
    """DOKUMENTIERTE FOLGE, kein Versehen.

    Wird ein Universum spaeter wieder auf PLACEHOLDER gesetzt, obwohl bereits
    ein echtes Ranking existiert, verweigert auch der gewoehnliche Anzeige-Lauf
    den Dienst — die Kurse werden dann NICHT mehr aktualisiert, und die Seite
    friert auf dem letzten guten Stand ein.

    Das ist gewollt: ein Universum, dem man nicht mehr traut, soll keine
    lebende Seite weiter befeuern. Wer nur die Anzeige einfrieren will, ohne
    das Universum anzufassen, schaltet stattdessen den Workflow ab.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "universe").mkdir()
    pfad = write_universe(
        tmp_path / "universe" / "u.txt", ["AAA", "BBB", "CCC", "DDD", "EEE"]
    )
    markt = replace(MARKETS_BY_KEY["us"], universe_file=str(pfad))
    serien = {**sample_series(), "^SP500TR": index_series()}

    # 1. Echtes Ranking entsteht
    view, neu, _ = run_modul.process_market(
        markt, STICHTAG, downloader=make_downloader(serien)
    )
    assert neu is not None
    gesichert = (tmp_path / "data/rankings/us_2026-07.json").read_bytes()

    # 2. Universum wird zurueckgesetzt
    pfad.write_text(UNGEPRUEFTE_DATEIEN["Platzhalter"], encoding="utf-8")

    # 3. Auch der reine Anzeige-Lauf verweigert jetzt
    with pytest.raises(UniverseNotReady):
        run_modul.process_market(
            markt, Date(2026, 8, 5), downloader=make_downloader(serien)
        )

    # ... und das bestehende Ranking bleibt unangetastet
    assert (tmp_path / "data/rankings/us_2026-07.json").read_bytes() == gesichert
