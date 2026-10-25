"""Das ntfy-Relay (ntfy_relay.py) — geprueft ohne echtes Netz (`pusher`
ersetzt `notify.push()`) und ohne echte Umgebungsvariablen (`umgebung`
ersetzt `os.environ`).

Kernaussagen: Eingaben laufen NUR ueber Umgebungsvariablen (nie ueber
Argumente, die aus einer Shell-Zeile staemmen); Titel/Tags werden von
Zeilenumbruechen und Steuerzeichen bereinigt; die Nachricht laeuft durch
`begrenze_bloecke()`; eine unbekannte Prioritaet oder ein leerer Titel/
leere Nachricht fuehrt zu einem klaren Fehler OHNE Versandversuch;
scheitert der Versand, macht das den Lauf rot (Exit 1); ein
Injektionsversuch (`$(...)`, Backticks) bleibt reiner Text, wird nie
ausgefuehrt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from momentum.notify import NACHRICHT_BLOCK_GRENZE, PRIORITIES
from momentum.ntfy_relay import bereinige_kopf, main


def umgebung(**kwargs) -> dict:
    basis = {
        "RELAY_TITLE": "Titel",
        "RELAY_MESSAGE": "Nachricht",
        "RELAY_TAGS": "",
        "RELAY_PRIORITY": "default",
    }
    basis.update(kwargs)
    return basis


# ------------------------------------------------------------- bereinige_kopf


def test_bereinige_kopf_ersetzt_zeilenumbrueche_durch_leerzeichen():
    assert bereinige_kopf("Zeile 1\nZeile 2") == "Zeile 1 Zeile 2"
    assert bereinige_kopf("Tab\tgetrennt") == "Tab getrennt"
    assert bereinige_kopf("Wagenruecklauf\r\nhier") == "Wagenruecklauf hier"


def test_bereinige_kopf_entfernt_steuerzeichen():
    assert bereinige_kopf("A\x00B\x1bC") == "ABC"


def test_bereinige_kopf_laesst_umlaute_und_satzzeichen_unberuehrt():
    assert bereinige_kopf("Prüfung läuft — alles ok, Grüße!") == "Prüfung läuft — alles ok, Grüße!"


def test_bereinige_kopf_fasst_mehrfache_leerzeichen_zusammen_und_trimmt():
    assert bereinige_kopf("  zu   viele    Leerzeichen  ") == "zu viele Leerzeichen"


def test_bereinige_kopf_ist_deterministisch():
    text = "Immer\ndasselbe\tErgebnis"
    assert bereinige_kopf(text) == bereinige_kopf(text)


# ------------------------------------------------- Injektion bleibt reiner Text


def test_injektionsversuch_kommt_unausgefuehrt_als_text_im_body_an():
    """`$(...)`/Backticks sind keine Steuerzeichen -- sie werden NICHT
    entfernt, sondern unveraendert als Text weitergegeben. Die Sicherheit
    kommt daher, dass nirgends eine Shell/subprocess/eval auf diesen
    Text angewendet wird (siehe test_der_code_fuehrt_nichts_aus unten)."""
    bekommen = {}

    def pusher(titel, body, **kwargs):
        bekommen["titel"] = titel
        bekommen["body"] = body
        return True

    text = "harmlos $(rm -rf /) und `whoami` als reiner Text"
    code = main(umgebung=umgebung(RELAY_MESSAGE=text), pusher=pusher)
    assert code == 0
    assert "$(rm -rf /)" in bekommen["body"]
    assert "`whoami`" in bekommen["body"]


def test_injektionsversuch_im_titel_wird_nur_bereinigt_nicht_blockiert():
    bekommen = {}

    def pusher(titel, body, **kwargs):
        bekommen["titel"] = titel
        return True

    code = main(umgebung=umgebung(RELAY_TITLE="böse\nZeile $(id)"), pusher=pusher)
    assert code == 0
    assert bekommen["titel"] == "böse Zeile $(id)"
    assert "\n" not in bekommen["titel"]


# ------------------------------------------------------- Kuerzung des Bodys


def test_ueberlanger_body_wird_gekuerzt():
    bekommen = {}

    def pusher(titel, body, **kwargs):
        bekommen["body"] = body
        return True

    lange_nachricht = "x" * (NACHRICHT_BLOCK_GRENZE + 500)
    code = main(umgebung=umgebung(RELAY_MESSAGE=lange_nachricht), pusher=pusher)
    assert code == 0
    assert len(bekommen["body"]) < len(lange_nachricht)


def test_kurzer_body_bleibt_unveraendert():
    bekommen = {}

    def pusher(titel, body, **kwargs):
        bekommen["body"] = body
        return True

    main(umgebung=umgebung(RELAY_MESSAGE="Kurzer Text."), pusher=pusher)
    assert bekommen["body"] == "Kurzer Text."


# ------------------------------------------------------- Validierung/Fehler


def test_leerer_titel_nach_bereinigung_wird_abgelehnt():
    aufgerufen = []
    code = main(
        umgebung=umgebung(RELAY_TITLE="\n\t  "),
        pusher=lambda *a, **k: aufgerufen.append(1) or True,
    )
    assert code == 1
    assert aufgerufen == []


def test_leere_nachricht_wird_abgelehnt():
    aufgerufen = []
    code = main(
        umgebung=umgebung(RELAY_MESSAGE="   "),
        pusher=lambda *a, **k: aufgerufen.append(1) or True,
    )
    assert code == 1
    assert aufgerufen == []


def test_unbekannte_prioritaet_wird_abgelehnt_ohne_versandversuch():
    aufgerufen = []
    code = main(
        umgebung=umgebung(RELAY_PRIORITY="urgent"),
        pusher=lambda *a, **k: aufgerufen.append(1) or True,
    )
    assert code == 1
    assert aufgerufen == []


@pytest.mark.parametrize("prioritaet", sorted(PRIORITIES))
def test_jede_erlaubte_prioritaet_wird_durchgereicht(prioritaet):
    bekommen = {}

    def pusher(titel, body, *, priority, **kwargs):
        bekommen["priority"] = priority
        return True

    code = main(umgebung=umgebung(RELAY_PRIORITY=prioritaet), pusher=pusher)
    assert code == 0
    assert bekommen["priority"] == prioritaet


def test_tags_werden_bereinigt_und_durchgereicht():
    bekommen = {}

    def pusher(titel, body, *, tags, **kwargs):
        bekommen["tags"] = tags
        return True

    main(umgebung=umgebung(RELAY_TAGS="warning,\nbell"), pusher=pusher)
    assert bekommen["tags"] == "warning, bell"


# ------------------------------------------------------- Versand-Fehlschlag


def test_fehlgeschlagener_versand_macht_den_lauf_rot():
    code = main(umgebung=umgebung(), pusher=lambda *a, **k: False)
    assert code == 1


def test_ausnahme_beim_versand_macht_den_lauf_rot():
    def wirft(*a, **k):
        raise OSError("ntfy nicht erreichbar")

    code = main(umgebung=umgebung(), pusher=wirft)
    assert code == 1


def test_erfolgreicher_versand_ist_gruen():
    code = main(umgebung=umgebung(), pusher=lambda *a, **k: True)
    assert code == 0


# ------------------------------------------------------- Determinismus


def test_main_ist_deterministisch_bei_gleicher_umgebung():
    ergebnisse = []

    def pusher(titel, body, **kwargs):
        ergebnisse.append((titel, body, kwargs.get("tags"), kwargs.get("priority")))
        return True

    env = umgebung(RELAY_TITLE="Fix", RELAY_MESSAGE="Immer gleich", RELAY_TAGS="a,b")
    main(umgebung=env, pusher=pusher)
    main(umgebung=env, pusher=pusher)
    assert ergebnisse[0] == ergebnisse[1]


# ------------------------------------------------------- Melden, nie Handeln


def test_der_code_fuehrt_nichts_aus_und_schreibt_nichts():
    """Statischer Nie-Handeln-Test: kein subprocess/eval/exec/os.system,
    keine Datei-Schreibfunktion -- ein Injektionsversuch kann hier
    strukturell nicht zum Befehl werden."""
    quelltext = Path("src/momentum/ntfy_relay.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "subprocess", "os.system", "eval(", "exec(",
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "git commit", "git push", "gh pr",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"


def test_der_workflow_hat_kein_inputs_in_einer_run_zeile():
    """Statischer Injektions-Test: `${{ inputs.` darf an KEINER Stelle in
    einem `run:`-Block dieser Workflow-Datei stehen -- jeder Eingabewert
    laeuft ausschliesslich ueber `env:`."""
    text = Path(".github/workflows/ntfy_relay.yml").read_text(encoding="utf-8")
    daten = yaml.safe_load(text)
    job = daten["jobs"]["relay"]
    for schritt in job["steps"]:
        run_zeile = schritt.get("run", "")
        assert "inputs." not in run_zeile, f"${{ inputs. }} in run: gefunden: {run_zeile!r}"
    # Zusaetzlich, zeilenbasiert gegen die rohe Datei (deckt auch einen
    # kuenftigen mehrzeiligen `run:`-Block ab, den YAML-Laden allein
    # nicht als verdaechtig markieren wuerde).
    innerhalb_run = False
    for zeile in text.splitlines():
        blank = zeile.strip()
        if blank.startswith("run:") or blank.startswith("run: |"):
            innerhalb_run = True
            assert "${{ inputs." not in zeile
            continue
        if innerhalb_run and (not zeile.strip() or zeile.startswith(" " * 8)):
            assert "${{ inputs." not in zeile
        else:
            innerhalb_run = False


def test_der_workflow_kann_nur_lesen():
    daten = yaml.safe_load(
        Path(".github/workflows/ntfy_relay.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read"}
    assert "write" not in yaml.dump(daten["permissions"])
    ausloeser = daten[True] if True in daten else daten["on"]
    assert "schedule" not in ausloeser, "nur workflow_dispatch, kein Zeitplan"
    assert "workflow_dispatch" in ausloeser
    eingaben = ausloeser["workflow_dispatch"]["inputs"]
    assert set(eingaben) == {"title", "message", "tags", "priority"}
    assert eingaben["priority"]["type"] == "choice"
    assert eingaben["priority"]["options"] == ["min", "low", "default", "high"]
    text = Path(".github/workflows/ntfy_relay.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text


def test_die_prioritaeten_liste_passt_zum_workflow():
    daten = yaml.safe_load(
        Path(".github/workflows/ntfy_relay.yml").read_text(encoding="utf-8")
    )
    ausloeser = daten[True] if True in daten else daten["on"]
    optionen = ausloeser["workflow_dispatch"]["inputs"]["priority"]["options"]
    assert set(optionen) == set(PRIORITIES)
