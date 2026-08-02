"""Push-Verhalten — inklusive der ehrlichen Trennung der Fehlerfaelle.

Der springende Punkt: ein fehlendes NTFY_TOPIC ist NIE ein stiller
Rueckfall. Es steht als deutliche Zeile im Lauf-Log.
"""

from __future__ import annotations

import json

import pytest

from momentum import notify


def _payload(request) -> dict:
    """Der Nutzinhalt geht als UTF-8-JSON raus, nicht als HTTP-Kopfzeile."""
    return json.loads(request.data.decode("utf-8"))


class _Antwort:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _sammler(gesammelt):
    def opener(request, timeout=None):
        gesammelt.append(request)
        return _Antwort()

    return opener


def test_fehlendes_secret_wird_laut_gemeldet_und_nicht_verschluckt(monkeypatch, capsys):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    ergebnis = notify.push("Titel", "Text")
    ausgabe = capsys.readouterr()
    assert ergebnis is False
    assert "NTFY_TOPIC" in ausgabe.err
    assert "PUSH NICHT VERSCHICKT" in ausgabe.err
    assert "=" * 72 in ausgabe.err


def test_fehlendes_secret_erzeugt_eine_github_warnung(monkeypatch, capsys):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    notify.push("Titel", "Text")
    ausgabe = capsys.readouterr()
    assert "::warning title=NTFY_TOPIC fehlt::" in ausgabe.out


def test_neues_ranking_nennt_top_titel_je_markt():
    gesammelt = []
    ok = notify.push_new_ranking(
        [
            {
                "markt": "USA",
                "stichtag": "2026-07-31",
                "top": "NVDA",
                "top_name": "NVIDIA Corp.",
                "score": 100.0,
            },
            {
                "markt": "Deutschland",
                "stichtag": "2026-07-31",
                "top": "SAP.DE",
                "top_name": "SAP SE",
                "score": 98.4,
            },
        ],
        topic="test-topic",
        opener=_sammler(gesammelt),
    )
    assert ok is True
    nachricht = _payload(gesammelt[0])
    body = nachricht["message"]
    assert "Stichtag 2026-07-31" in body
    assert "USA: NVDA — NVIDIA Corp. (Score 100.0)" in body
    assert "Deutschland: SAP.DE — SAP SE (Score 98.4)" in body
    assert "eingefroren" in body
    assert nachricht["priority"] == 3
    assert nachricht["title"] == "Momentum-Report: neues Monats-Ranking"


def test_datenpush_konflikt_ohne_sirene_und_ohne_hohe_prioritaet():
    gesammelt = []
    notify.push_data_conflict(
        "git push abgelehnt (non-fast-forward)", topic="t", opener=_sammler(gesammelt)
    )
    nachricht = _payload(gesammelt[0])
    assert nachricht["title"] == "Daten-Push-Konflikt — Analyse lief fehlerfrei"
    assert nachricht["priority"] == 3
    assert "rotating_light" not in nachricht["tags"]
    assert "fehlerfrei durchgelaufen" in nachricht["message"]


def test_lauf_fehlgeschlagen_mit_sirene_und_hoher_prioritaet():
    gesammelt = []
    notify.push_run_failed("Kursquelle nicht erreichbar", topic="t", opener=_sammler(gesammelt))
    nachricht = _payload(gesammelt[0])
    assert nachricht["title"] == "Lauf fehlgeschlagen"
    assert nachricht["priority"] == 4
    assert nachricht["tags"] == ["rotating_light"]
    assert "bewusst nichts veroeffentlicht" in nachricht["message"]


def test_die_beiden_fehlerfaelle_sind_klar_unterscheidbar():
    gesammelt = []
    notify.push_data_conflict("x", topic="t", opener=_sammler(gesammelt))
    notify.push_run_failed("y", topic="t", opener=_sammler(gesammelt))
    nachrichten = [_payload(r) for r in gesammelt]
    assert nachrichten[0]["title"] != nachrichten[1]["title"]
    assert [n["priority"] for n in nachrichten] == [3, 4]
    assert "Analyse lief fehlerfrei" in nachrichten[0]["title"]
    assert nachrichten[1]["title"] == "Lauf fehlgeschlagen"


def test_titel_mit_umlauten_und_gedankenstrich_bleiben_heil():
    """Ueber JSON statt HTTP-Kopfzeile — sonst wuerde "—" zu Zeichensalat."""
    gesammelt = []
    notify.push("Prüfung — Härtetest", "ähnlich", topic="t", opener=_sammler(gesammelt))
    nachricht = _payload(gesammelt[0])
    assert nachricht["title"] == "Prüfung — Härtetest"
    assert nachricht["message"] == "ähnlich"


def test_kein_herzschlag_push_vorhanden():
    """v0 hat bewusst keinen 'alles ok'-Push."""
    funktionen = [name for name in dir(notify) if name.startswith("push_")]
    assert sorted(funktionen) == ["push_data_conflict", "push_new_ranking", "push_run_failed"]


def test_unerreichbares_ntfy_wird_nicht_zum_absturz(monkeypatch, capsys):
    def kaputt(request, timeout=None):
        raise OSError("keine Verbindung")

    assert notify.push("T", "B", topic="t", opener=kaputt) is False
    assert "ntfy nicht erreichbar" in capsys.readouterr().err


@pytest.mark.parametrize("leer", ["", "   "])
def test_leeres_secret_zaehlt_als_fehlend(monkeypatch, leer):
    monkeypatch.setenv("NTFY_TOPIC", leer)
    assert notify.push("T", "B") is False
