"""Push-Verhalten — inklusive der ehrlichen Trennung der Fehlerfaelle.

Der springende Punkt: ein fehlendes NTFY_TOPIC ist NIE ein stiller
Rueckfall. Es steht als deutliche Zeile im Lauf-Log.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    """v0 hat bewusst keinen 'alles ok'-Push, der von selbst kommt.

    push_test ist keiner: sie hat keinen Zeitplan und keine Bedingung, sie
    kommt ausschliesslich auf ausdrueckliche Anforderung ueber das
    Workflow-Feld "testpush". Ein Herzschlag waere eine Nachricht, die man
    NICHT bestellt hat.
    """
    funktionen = [name for name in dir(notify) if name.startswith("push_")]
    # push_lauf_ueberfaellig ist ebenfalls KEIN Herzschlag: sie kommt zwar
    # aus einem Zeitplan (waechter.yml), aber ausschliesslich im ALARMFALL.
    # Ein Herzschlag waere die Gegenrichtung -- eine Nachricht, die kommt,
    # wenn alles gut ist. Genau die gibt es weiterhin nicht; der Waechter
    # schweigt im Normalfall (tests/unit/test_waechter.py haelt das fest).
    assert sorted(funktionen) == [
        "push_data_conflict",
        "push_lauf_ueberfaellig",
        "push_new_ranking",
        "push_run_failed",
        "push_test",
        # Auch kein Herzschlag: der Vertragstest laeuft zwar nach
        # Zeitplan, meldet sich aber ausschliesslich, wenn ein Vertrag
        # gebrochen ist (tests/unit/test_vertragstest.py haelt fest, dass
        # er im Normalfall schweigt).
        "push_vertrag_gebrochen",
    ]
    quelle = Path("src/momentum/notify.py").read_text(encoding="utf-8")
    assert "schedule" not in quelle and "cron" not in quelle
    lauf = Path("src/momentum/run.py").read_text(encoding="utf-8")
    assert "args.testpush" in lauf, "die Probe haengt an einem ausdruecklichen Schalter"


def test_unerreichbares_ntfy_wird_nicht_zum_absturz(monkeypatch, capsys):
    def kaputt(request, timeout=None):
        raise OSError("keine Verbindung")

    assert notify.push("T", "B", topic="t", opener=kaputt) is False
    assert "ntfy nicht erreichbar" in capsys.readouterr().err


@pytest.mark.parametrize("leer", ["", "   "])
def test_leeres_secret_zaehlt_als_fehlend(monkeypatch, leer):
    monkeypatch.setenv("NTFY_TOPIC", leer)
    assert notify.push("T", "B") is False


# --------------------------------------------------------------------------
# NTFY_TOPIC haerten
#
# Am 02.08.2026 scheiterte der Push mit HTTP 400 "topic invalid": im Secret
# steckte ein unsichtbarer Rest vom Kopieren. Der Lauf sagte nur "HTTP 400"
# -- zu stumm, um daraus etwas zu lernen.
# --------------------------------------------------------------------------

GUELTIG = ["momentum-report", "abc", "A_b-9", "x" * 64, "0"]
UNGUELTIG_UNSICHTBAR = {
    "momentum-report ": ("Position 16", "Leerzeichen"),
    "momentum-report\n": ("Position 16", "Zeilenumbruch"),
    "momentum-report\r\n": ("Position 16", "Wagenruecklauf"),
    "momentum-report\t": ("Position 16", "Tabulator"),
    "momen tum": ("Position 6", "Leerzeichen"),
}


@pytest.mark.parametrize("topic", GUELTIG)
def test_gueltige_themen_kommen_durch(topic):
    assert notify.pruefe_topic(topic) is None
    gesammelt = []
    assert notify.push("T", "B", topic=topic, opener=_sammler(gesammelt)) is True
    assert _payload(gesammelt[0])["topic"] == topic


@pytest.mark.parametrize("topic,erwartet", sorted(UNGUELTIG_UNSICHTBAR.items()))
def test_unsichtbare_reste_werden_benannt(topic, erwartet):
    """Das Zeichen wird nach Position UND Art genannt -- sonst sucht man ewig."""
    stelle, art = erwartet
    diagnose = notify.pruefe_topic(topic)
    assert diagnose is not None
    assert stelle in diagnose, diagnose
    assert art in diagnose, diagnose


def test_anhaengsel_am_ende_werden_vorher_abgeschnitten(monkeypatch):
    """Leerzeichen und Zeilenumbruch AM RAND kosten keinen Push.

    Genau das ist der haeufige Paste-Rest. Er wird geputzt, nicht bemaengelt
    -- der Push geht raus, und zwar an das saubere Thema.
    """
    for roh in ("momentum-report ", " momentum-report", "momentum-report\n", "\tmomentum-report\r\n"):
        monkeypatch.setenv("NTFY_TOPIC", roh)
        gesammelt = []
        assert notify.push("T", "B", opener=_sammler(gesammelt)) is True, roh
        assert _payload(gesammelt[0])["topic"] == "momentum-report"


def test_ein_rest_MITTEN_drin_bricht_ab_und_schickt_nichts(monkeypatch, capsys):
    """Was .strip() nicht wegbekommt, muss VOR dem Senden auffallen."""
    monkeypatch.setenv("NTFY_TOPIC", "momen tum-report")
    gesammelt = []
    assert notify.push("T", "B", opener=_sammler(gesammelt)) is False
    assert gesammelt == [], "es wurde trotz ungueltigem Thema gesendet"
    fehler = capsys.readouterr().err
    assert "NTFY_TOPIC ungueltig" in fehler
    assert "Position 6" in fehler
    assert "Leerzeichen" in fehler


@pytest.mark.parametrize(
    "topic,art",
    [
        ("momentum report", "geschuetztes Leerzeichen"),
        ("momentum​report", "ohne Breite"),
        ("﻿momentum", "Byte-Order-Mark"),
        ("momentum.report", "Satzzeichen"),
        ("momentum/report", "Satzzeichen"),
        ("momentum+report", "Symbol"),
        ("momentüm", "Buchstabe ausserhalb A-Z"),
    ],
)
def test_auch_die_hinterhaeltigen_zeichen_werden_erkannt(topic, art):
    """U+00A0 und U+200B ueberleben .strip() teilweise bzw. ganz."""
    diagnose = notify.pruefe_topic(topic)
    assert diagnose is not None, topic
    assert art in diagnose, (topic, diagnose)


def test_zu_langes_thema_wird_an_der_laenge_erkannt():
    diagnose = notify.pruefe_topic("x" * 65)
    assert diagnose is not None
    assert "65 Zeichen" in diagnose
    assert "1 bis 64" in diagnose


def test_leeres_thema_gilt_weiter_als_fehlend(monkeypatch, capsys):
    monkeypatch.setenv("NTFY_TOPIC", "   \n")
    assert notify.push("T", "B") is False
    assert "PUSH NICHT VERSCHICKT" in capsys.readouterr().err


@pytest.mark.parametrize(
    "topic",
    ["geheim-thema ", "geheim-thema\n", "gehe im-thema", "geheim.thema", "geheim​thema"],
)
def test_die_diagnose_verraet_das_thema_NICHT(topic, monkeypatch, capsys):
    """Ein Secret gehoert nicht ins Protokoll -- auch nicht bruchstueckweise."""
    monkeypatch.setenv("NTFY_TOPIC", topic)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    notify.push("T", "B")
    ausgabe = capsys.readouterr()
    gesamt = ausgabe.out + ausgabe.err
    geputzt = topic.strip()
    assert geputzt not in gesamt, "das Thema steht im Klartext im Protokoll"
    # auch kein laengeres Bruchstueck
    assert "geheim" not in gesamt, gesamt
    assert "thema" not in gesamt, gesamt


def test_ungueltiges_thema_erzeugt_eine_fehler_annotation(monkeypatch, capsys):
    monkeypatch.setenv("NTFY_TOPIC", "mit leerzeichen")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    notify.push("T", "B")
    ausgabe = capsys.readouterr().out
    assert "::error title=NTFY_TOPIC ungueltig::" in ausgabe
    # Die Annotation muss einzeilig sein, sonst zeigt GitHub sie nicht an.
    zeile = [z for z in ausgabe.splitlines() if z.startswith("::error")][0]
    assert "Position 4" in zeile and "Leerzeichen" in zeile


# ------------------------------------------------------- Antwort des Servers


class _Fehlerantwort:
    def __init__(self, status, koerper):
        self.status = status
        self._koerper = koerper

    def read(self):
        return self._koerper

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_der_grund_des_servers_steht_im_protokoll(capsys):
    """"HTTP 400" allein war zu stumm — der Koerper nennt den Grund."""
    koerper = b'{"code":40009,"http":400,"error":"invalid request: topic invalid"}'

    def opener(request, timeout=None):
        return _Fehlerantwort(400, koerper)

    assert notify.push("T", "B", topic="gueltig", opener=opener) is False
    fehler = capsys.readouterr().err
    assert "HTTP 400" in fehler
    assert "invalid request: topic invalid" in fehler
    assert "40009" in fehler


def test_auch_die_geworfene_http_ausnahme_wird_ausgelesen(capsys):
    """urlopen wirft bei 4xx — der echte Weg. Auch da muss der Grund raus."""
    import io
    import urllib.error

    def opener(request, timeout=None):
        raise urllib.error.HTTPError(
            "https://ntfy.sh",
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"code":40009,"http":400,"error":"topic invalid"}'),
        )

    assert notify.push("T", "B", topic="gueltig", opener=opener) is False
    fehler = capsys.readouterr().err
    assert "HTTP 400" in fehler
    assert "topic invalid" in fehler


def test_der_antworttext_schwaerzt_das_thema(capsys):
    """Falls ein Server das Thema zurueckspiegelt: nicht ins Protokoll."""

    def opener(request, timeout=None):
        return _Fehlerantwort(400, b'{"error":"topic geheimnis unbekannt"}')

    notify.push("T", "B", topic="geheimnis", opener=opener)
    fehler = capsys.readouterr().err
    assert "geheimnis" not in fehler
    assert "<topic>" in fehler


def test_unlesbare_antwort_kippt_nichts(capsys):
    class Kaputt(_Fehlerantwort):
        def read(self):
            raise OSError("Verbindung weg")

    def opener(request, timeout=None):
        return Kaputt(503, b"")

    assert notify.push("T", "B", topic="gueltig", opener=opener) is False
    assert "HTTP 503" in capsys.readouterr().err


# --------------------------------------------------------------------------
# VERDRAHTUNGSPROBE
#
# Die Frage, die sie beantwortet: kommt ueberhaupt etwas an? Deshalb muss
# sie denselben Weg nehmen wie ein echter Push. Eine Probe mit eigenem
# Sendeweg wuerde beweisen, dass der eigene Sendeweg geht -- und sonst
# nichts.
# --------------------------------------------------------------------------


def test_die_probe_nimmt_denselben_weg_wie_ein_echter_push(monkeypatch):
    """Kein zweiter Sende-Code: push_test ruft push() auf, sonst nichts."""
    gerufen = []

    def statt_push(*args, **kwargs):
        gerufen.append((args, kwargs))
        return True

    monkeypatch.setattr(notify, "push", statt_push)
    assert notify.push_test() is True
    assert len(gerufen) == 1, "push() wurde nicht genau einmal gerufen"


def test_die_probe_geht_ueber_die_gleiche_schnittstelle():
    """Gleiches Ziel, gleiches Format, gleiche Thema-Pruefung."""
    gesammelt = []
    assert notify.push_test(topic="t", opener=_sammler(gesammelt)) is True
    assert len(gesammelt) == 1
    nachricht = _payload(gesammelt[0])
    assert nachricht["topic"] == "t"
    assert nachricht["title"] == "Momentum: Push-Verdrahtung ok"
    # leise
    assert nachricht["priority"] == notify.PRIORITIES["default"]
    # und ohne jede Aussage ueber Kurse
    for verboten in ("Score", "Ranking vom", "Top", "Rendite"):
        assert verboten not in nachricht["message"], verboten
    assert "sagt NICHTS" in nachricht["message"]


def test_die_probe_faellt_unter_dieselbe_thema_pruefung(monkeypatch, capsys):
    monkeypatch.setenv("NTFY_TOPIC", "mit leerzeichen")
    assert notify.push_test() is False
    assert "NTFY_TOPIC ungueltig" in capsys.readouterr().err


def test_die_probe_ohne_secret_ist_ebenso_laut(monkeypatch, capsys):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert notify.push_test() is False
    assert "PUSH NICHT VERSCHICKT" in capsys.readouterr().err
