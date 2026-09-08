"""Reparatur-Agent Stufe 3, erste Ausbaustufe (tools/agent_datumsformat.py).

Drei Testfaelle, wie im Auftrag verlangt:
  1. Ein simulierter, neuer Datumsformat-Bruch fuehrt zu einem korrekten,
     additiven Vorschlag -- die bestehenden vier Muster bleiben unberuehrt.
  2. Ein Fehler AUSSERHALB der Fehlerklasse loest nichts aus (siehe
     test_vertragstest.py::test_agent_befund_erfasst_nur_datumsformat_bei_de_bestandslisten
     fuer die Filterung; hier zusaetzlich: verarbeite_befund() bekommt gar
     keinen Fund dieser Art zu sehen, wenn vertragstest ihn nicht liefert).
  3. Ein mehrdeutiger/unklarer Fall ergibt "unklar", nie einen Vorschlag.

Dazu: Determinismus (dieselbe Zeile -> derselbe Vorschlag, byte-gleich)
und die harte Vorgabe, dass der PR-Text die rohe Zeile woertlich zitiert
und "CI ist gruen" nirgends als alleinige Begruendung steht.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("tools").resolve()))

import agent_datumsformat as agent  # noqa: E402

Date = _dt.date
ISHARES_QUELLTEXT = Path("src/momentum/ishares.py").read_text(encoding="utf-8")


def _lade_gepatchte_funktion(quelltext: str, tmp_path: Path):
    """Den gepatchten Quelltext tatsaechlich importieren und ausfuehren --
    kein Textvergleich, ein echter Funktionstest."""
    pfad = tmp_path / "ishares_patched.py"
    pfad.write_text(quelltext, encoding="utf-8")
    name = f"ishares_patched_test_{abs(hash(quelltext))}"
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    # `from __future__ import annotations` macht alle Annotationen zu
    # Strings -- die dataclass-Dekorateure in ishares.py loesen sie ueber
    # sys.modules[cls.__module__] auf. Ohne diesen Eintrag schlaegt der
    # Import mit einem irrefuehrenden AttributeError fehl, der mit dem
    # eigentlichen Test nichts zu tun hat.
    sys.modules[name] = modul
    try:
        spec.loader.exec_module(modul)
    finally:
        del sys.modules[name]
    return modul._datum_aus_text


# --------------------------------------------------- 1. Neues, lesbares Format


def test_leite_muster_ab_findet_ein_neues_eindeutiges_format():
    """Jahr-zuerst-Reihenfolge -- von keinem der vier bestehenden Muster
    abgedeckt (geprueft unten explizit)."""
    zeile = "2026/Aug/06"
    assert agent._datum_aus_text(zeile) is None, "Testannahme verletzt: schon lesbar"

    ableitung = agent.leite_muster_ab(zeile)
    assert ableitung is not None
    assert ableitung.datum == Date(2026, 8, 6)
    assert ableitung.gruppen == ("jahr", "monat", "tag")


def test_wende_an_ist_additiv_bestehende_muster_bleiben_unberuehrt(tmp_path):
    ableitung = agent.leite_muster_ab("2026/Aug/06")
    schnipsel = agent.erzeuge_codeschnipsel(
        ableitung, "iShares EXS1 (DAX)", Date(2026, 9, 8)
    )
    neuer_quelltext = agent.wende_an(ISHARES_QUELLTEXT, schnipsel)
    assert neuer_quelltext != ISHARES_QUELLTEXT

    datum_aus_text = _lade_gepatchte_funktion(neuer_quelltext, tmp_path)

    # Das NEUE Format liest jetzt.
    assert datum_aus_text("2026/Aug/06") == Date(2026, 8, 6)

    # Die VIER BESTEHENDEN Muster lesen unveraendert weiter -- exakt die
    # Faelle aus tests/unit/test_universe_parse.py::test_datumsformate.
    assert datum_aus_text("as of 2026-07-31") == Date(2026, 7, 31)
    assert datum_aus_text('"31.Juli2026"') == Date(2026, 7, 31)
    assert datum_aus_text('"Jul 31, 2026"') == Date(2026, 7, 31)
    assert datum_aus_text("Stand: 31.07.2026") == Date(2026, 7, 31)
    assert datum_aus_text("06.Aug.2026") == Date(2026, 8, 6)
    assert datum_aus_text("Basiswährung;EUR") is None


def test_wende_an_fuegt_nur_einen_neuen_block_ein_kein_bestehender_wird_ersetzt():
    ableitung = agent.leite_muster_ab("2026/Aug/06")
    schnipsel = agent.erzeuge_codeschnipsel(
        ableitung, "iShares EXS1 (DAX)", Date(2026, 9, 8)
    )
    neuer_quelltext = agent.wende_an(ISHARES_QUELLTEXT, schnipsel)
    # additiv heisst hier woertlich: der komplette alte Quelltext steckt
    # unveraendert darin, nur der neue Block ist VOR dem Anker eingefuegt --
    # exakt eine Ersetzungsstelle, nichts geloescht.
    erwartet = ISHARES_QUELLTEXT.replace(agent.AGENT_ANKER, schnipsel + agent.AGENT_ANKER)
    assert neuer_quelltext == erwartet
    assert ISHARES_QUELLTEXT.count(agent.AGENT_ANKER) == 1


def test_verarbeite_befund_liefert_einen_vorschlag_fuer_eine_lesbare_zeile():
    befund = {
        "quelle": "iShares EXS1 (DAX)",
        "stichtag": "2026-09-08",
        "vorspann_zeilen": ["2026/Aug/06"],
    }
    ergebnisse = agent.verarbeite_befund(befund, ishares_quelltext=ISHARES_QUELLTEXT)
    assert len(ergebnisse) == 1
    vorschlag = ergebnisse[0]
    assert isinstance(vorschlag, agent.Vorschlag)
    assert vorschlag.rohzeile == "2026/Aug/06"
    assert vorschlag.datum == Date(2026, 8, 6)


def test_pr_text_zitiert_die_rohe_zeile_woertlich_und_nennt_ci_nie_als_begruendung():
    befund = {
        "quelle": "iShares EXS1 (DAX)",
        "stichtag": "2026-09-08",
        "vorspann_zeilen": ["2026/Aug/06"],
    }
    vorschlag = agent.verarbeite_befund(
        befund, ishares_quelltext=ISHARES_QUELLTEXT
    )[0]
    titel, text = agent.pr_text(vorschlag)
    assert "2026/Aug/06" in text, "die rohe Zeile muss woertlich im PR-Text stehen"
    assert "2026-08-06" in text, "die interpretierte Uebersetzung muss daneben stehen"
    assert "iShares EXS1 (DAX)" in titel
    tiefgestellt = text.lower()
    # "CI ist gruen" darf NIE die alleinige/erste Begruendung sein -- das
    # Wort "grün" im Kontext der Merge-Klasse ist erlaubt (siehe Text oben,
    # dort steht es als Einordnung, nicht als Beleg fuer die Korrektheit),
    # eine Formulierung wie "weil ci grün ist" bzw. "ci ist grün" als
    # Begruendung fuer den Fund selbst darf nicht vorkommen.
    assert "weil ci" not in tiefgestellt
    assert "ci ist grün" not in tiefgestellt
    assert "ci grün" not in tiefgestellt.replace("bei grünem ci", "")


def test_determinismus_gleiche_zeile_ergibt_immer_denselben_vorschlag():
    zeile = "2026/Aug/06"
    a1 = agent.leite_muster_ab(zeile)
    a2 = agent.leite_muster_ab(zeile)
    assert a1 == a2
    schnipsel_1 = agent.erzeuge_codeschnipsel(a1, "iShares EXS1 (DAX)", Date(2026, 9, 8))
    schnipsel_2 = agent.erzeuge_codeschnipsel(a2, "iShares EXS1 (DAX)", Date(2026, 9, 8))
    assert schnipsel_1 == schnipsel_2


# ------------------------------------------- 2. Ausserhalb der Fehlerklasse
#
# Der eigentliche Filter lebt in vertragstest.agent_befund() (siehe
# test_vertragstest.py) -- ohne einen Fund kommt dieses Modul nie zum
# Einsatz. Hier zusaetzlich: ein leerer Befund ergibt konsequent nichts.


def test_kein_fund_kein_vorschlag():
    befund = {"quelle": "iShares EXS1 (DAX)", "stichtag": "2026-09-08", "vorspann_zeilen": []}
    ergebnisse = agent.verarbeite_befund(befund, ishares_quelltext=ISHARES_QUELLTEXT)
    assert ergebnisse == [agent.Unklar(quelle="iShares EXS1 (DAX)", rohzeilen=())]


# --------------------------------------------------------- 3. Unklare Faelle


@pytest.mark.parametrize(
    "zeile,grund",
    [
        ("Jan Feb 2026", "zwei Monatsnamen"),
        ("06.Aug.26", "kein vierstelliges Jahr"),
        ("-", "Platzhalter, keine Datumsangabe"),
        ("31.Juli2026", "schon lesbar -- kein neuer Fall"),
        ("Fonds 12, Bestand 06.Aug.2026 Blatt 34", "zwei Tages-Kandidaten"),
        ("", "leer"),
    ],
)
def test_leite_muster_ab_liefert_none_bei_mehrdeutigkeit(zeile, grund):
    assert agent.leite_muster_ab(zeile) is None, grund


def test_verarbeite_befund_liefert_unklar_wenn_keine_zeile_eindeutig_ist():
    befund = {
        "quelle": "iShares EXS3 (MDAX)",
        "stichtag": "2026-09-08",
        "vorspann_zeilen": ["Jan Feb 2026", "-"],
    }
    ergebnisse = agent.verarbeite_befund(befund, ishares_quelltext=ISHARES_QUELLTEXT)
    assert ergebnisse == [
        agent.Unklar(quelle="iShares EXS3 (MDAX)", rohzeilen=("Jan Feb 2026", "-"))
    ]
    assert all(not isinstance(e, agent.Vorschlag) for e in ergebnisse)


# --------------------------------------------------------------- main() CLI


def test_main_schreibt_vorschlaege_und_unklare_getrennt(tmp_path):
    befund_pfad = tmp_path / "befund.json"
    befund_pfad.write_text(
        __import__("json").dumps({
            "schema": 1,
            "stichtag": "2026-09-08",
            "funde": [
                {"quelle": "iShares EXS1 (DAX)", "vorspann_zeilen": ["2026/Aug/06"]},
                {"quelle": "iShares EXS3 (MDAX)", "vorspann_zeilen": ["Jan Feb 2026"]},
            ],
        }),
        encoding="utf-8",
    )
    ausgabe_pfad = tmp_path / "vorschlaege.json"
    gemeldet = []
    code = agent.main(
        [str(befund_pfad), "--ausgabe", str(ausgabe_pfad)],
        melder=lambda befunde: gemeldet.append(befunde) or True,
    )
    assert code == 0
    ausgabe = __import__("json").loads(ausgabe_pfad.read_text(encoding="utf-8"))
    assert len(ausgabe["vorschlaege"]) == 1
    assert ausgabe["vorschlaege"][0]["rohzeile"] == "2026/Aug/06"
    assert len(ausgabe["unklar"]) == 1
    assert ausgabe["unklar"][0]["quelle"] == "iShares EXS3 (MDAX)"

    # Die "unklar"-Meldung geht ueber denselben Weg raus wie jeder andere
    # Push (siehe notify.push_agent_datumsformat_unklar) -- hier nur mit
    # der Test-Naht `melder` abgefangen, kein echter ntfy-Versand.
    assert len(gemeldet) == 1
    assert gemeldet[0] == [{"quelle": "iShares EXS3 (MDAX)", "rohzeilen": ["Jan Feb 2026"]}]


def test_main_meldet_nicht_wenn_alles_lesbar_war(tmp_path):
    befund_pfad = tmp_path / "befund.json"
    befund_pfad.write_text(
        __import__("json").dumps({
            "schema": 1,
            "stichtag": "2026-09-08",
            "funde": [
                {"quelle": "iShares EXS1 (DAX)", "vorspann_zeilen": ["2026/Aug/06"]},
            ],
        }),
        encoding="utf-8",
    )
    gemeldet = []
    agent.main(
        [str(befund_pfad), "--ausgabe", str(tmp_path / "vorschlaege.json")],
        melder=lambda befunde: gemeldet.append(befunde) or True,
    )
    assert gemeldet == []
