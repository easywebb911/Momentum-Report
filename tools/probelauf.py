"""WEGWERF-PROBE: die zwei Pfade, die im Betrieb noch nie gelaufen sind.

Diese Datei ist Zubehoer, kein Bestandteil des Werkzeugs. Sie wird nach der
erfolgreichen Probe wieder entfernt (Rueckbau-PR). Nichts unter `src/`
importiert sie; sie laeuft ausschliesslich ueber
`.github/workflows/probelauf.yml` von Hand.

WARUM ES SIE GIBT
Seit dem 05.08. rechnet die Trend-Ampel mit dem Ueberschuss ueber dem
Geldmarkt (#16). Der Code dafuer ist durch Tests belegt -- aber ALLE diese
Tests speisen Kunstdaten ein. Der Zins-Pfad (^SP500TR, ^IRX, EZB-€STR) ist
auf einem Actions-Runner noch nie gelaufen: `_zins_reihe` und
`riskfree_12m` haengen im `if needed:`-Zweig von `process_market`, und der
letzte Stichtags-Lauf war am 02.08. -- vor #16. Am 31.08. waere der
Ernstfall der erste Test. Das ist der Grund fuer PROBE A.

Ebenso ist der dokumentierte Korrekturweg ("Ranking-Datei von Hand
loeschen, der naechste Lauf baut den Monat neu") nie geprobt worden. Das
ist PROBE B -- und sie ist zugleich der Determinismus-Beweis mit ECHTEN
Kursen statt mit dem Kunst-Beispiel.

WAS SIE NICHT TUT
Sie committet nichts, schickt keinen Push und fasst `docs/` nicht an.
PROBE A schreibt ausschliesslich in ein Wegwerf-Verzeichnis. PROBE B
beruehrt genau EINE Datei im Arbeitsbaum -- `data/rankings/de_2026-07.json`
-- und stellt sie im `finally` bitgleich wieder her.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

from momentum.config import MARKETS_BY_KEY
from momentum.ranking import RANKING_DIR, RankingNotPossible, due_months
from momentum.run import process_market

Date = _dt.date

# Der Stichtag, den PROBE B nachbaut, und das Laufdatum von damals. Mit
# genau diesem Datum entstand das Original (Lauf 2, 02.08.2026) -- gleiches
# Datum, gleiches Download-Fenster, gleicher Stichtag. Nur so ist ein
# Byte-Vergleich ueberhaupt eine Aussage ueber Determinismus.
STICHTAGS_HEUTE = Date(2026, 8, 2)
PROBE_B_DATEI = "de_2026-07.json"

# ERWARTETE, ERKLAERBARE ABWEICHUNGEN in PROBE B. Sie sind KEIN Freibrief:
# jede steht hier mit Begruendung, alles Uebrige muss bitgleich sein.
#
#  1. universum.stand -- die Universums-Datei wurde am 03.08. neu gezogen
#     (Lauf 7). Die TITEL-LISTE ist dabei bitgleich geblieben (extern
#     nachgerechnet: 102 Zeilen, gleiche Pruefsumme); geaendert hat sich
#     nur das Stand-Datum im Kopf der Datei.
#  2. trend_ampel -- seit #16 drei zusaetzliche Felder, und `warnung` haengt
#     jetzt am Ueberschuss statt an der Preisrendite. Das Original entstand
#     davor und kennt die Felder nicht.
#
# Innerhalb von trend_ampel wird `rendite_12m` TROTZDEM streng verglichen:
# das ist dieselbe Groesse wie damals und damit der eigentliche
# Determinismus-Nachweis fuer die Indexreihe.
ERWARTET_ANDERS = {
    "universum.stand": "Universums-Datei am 03.08. neu gezogen (Titel-Liste bitgleich)",
    "trend_ampel": "seit #16 drei neue Felder, Warnung am Ueberschuss",
}


def sag(text: str = "") -> None:
    print(text, flush=True)


def kopf(text: str) -> None:
    sag()
    sag("=" * 72)
    sag(text)
    sag("=" * 72)


def pct(wert: float | None, stellen: int = 2) -> str:
    return "—" if wert is None else f"{wert * 100:+.{stellen}f} %"


# --------------------------------------------------------------------------
# PROBE A — der Zins-Pfad, scharf
# --------------------------------------------------------------------------


def probe_a(heute: Date) -> list[str]:
    """Beide Maerkte voll rechnen, in ein Wegwerf-Verzeichnis.

    Scharf heisst: Ein Fail-soft ist hier ein FEHLSCHLAG. Der Sinn der
    Probe ist der Nachweis, dass der NORMALPFAD traegt -- nicht, dass die
    Notbremse funktioniert. Die ist durch Tests belegt.
    """
    kopf("PROBE A — Zins-Pfad scharf (^SP500TR + ^IRX, €STR über die EZB)")
    fehler: list[str] = []

    faellig = due_months(heute)
    sag(f"Laufdatum {heute}, faellige Monate laut due_months: "
        + ", ".join(f"{j:04d}-{m:02d}" for j, m in faellig))

    with tempfile.TemporaryDirectory(prefix="probelauf-a-") as tmp:
        wurzel = Path(tmp)
        for key in ("us", "de"):
            markt = MARKETS_BY_KEY[key]
            sag()
            sag(f"--- {markt.name} ({markt.index_ticker}, {markt.currency}) ---")
            try:
                _view, neu, _status = process_market(
                    markt,
                    heute,
                    ranking_root=wurzel / "rankings",
                    data_root=wurzel / "data",
                )
            except RankingNotPossible as exc:
                fehler.append(f"[{key}] Ranking nicht moeglich: {exc}")
                sag(f"ROT: {exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - die Probe soll den Grund zeigen
                fehler.append(f"[{key}] Abbruch {type(exc).__name__}: {exc}")
                sag("ROT: " + traceback.format_exc())
                continue

            if not neu:
                fehler.append(
                    f"[{key}] Kein Stichtags-Lauf ausgeloest — der Zins-Pfad wurde "
                    f"gar nicht betreten. (Leeres Wegwerf-Verzeichnis haette "
                    f"mindestens einen faelligen Monat ergeben muessen.)"
                )
                sag("ROT: kein neues Ranking, also kein Zins-Abruf.")
                continue

            ampel = neu["trend_ampel"]
            sag(f"Stichtag            {neu['stichtag']}")
            sag(f"Index               {ampel['index_name']} ({ampel['index_ticker']})")
            sag(f"rendite_12m         {pct(ampel['rendite_12m'])}")
            sag(f"riskfree_12m        {pct(ampel.get('riskfree_12m'))}")
            sag(f"ueberschuss_12m     {pct(ampel.get('ueberschuss_12m'))}")
            sag(f"Warn-Entscheid      {'WARNUNG' if ampel['warnung'] else 'kein Alarm'}")
            sag(f"Quelle              {ampel.get('riskfree_quelle')}")

            if ampel.get("riskfree_12m") is None:
                quelle = "^IRX über die Kursquelle" if key == "us" else "€STR über die EZB-API"
                fehler.append(
                    f"[{key}] FAIL-SOFT gegriffen: kein Geldmarktsatz. "
                    f"Geklemmt hat der Abruf {quelle}. Genau das sollte die "
                    f"Probe ausschliessen."
                )
                sag(f"ROT: fail-soft — {quelle} hat nichts geliefert.")
            else:
                sag("GRUEN: Zins gezogen, Ueberschuss gerechnet.")

    return fehler


# --------------------------------------------------------------------------
# PROBE B — Korrekturweg und Determinismus mit echten Kursen
# --------------------------------------------------------------------------


def _flach(objekt, praefix: str = "") -> dict[str, object]:
    """Verschachteltes JSON zu Pfad -> Wert, damit der Vergleich benennbar wird."""
    raus: dict[str, object] = {}
    if isinstance(objekt, dict):
        for schluessel, wert in objekt.items():
            raus.update(_flach(wert, f"{praefix}.{schluessel}" if praefix else str(schluessel)))
    else:
        raus[praefix] = objekt
    return raus


def probe_b() -> list[str]:
    """Den dokumentierten Korrekturweg gehen und das Ergebnis vergleichen."""
    kopf("PROBE B — Korrekturweg + Determinismus (DE, Stichtag 31.07.2026)")
    fehler: list[str] = []

    ziel = Path(RANKING_DIR) / PROBE_B_DATEI
    if not ziel.exists():
        return [f"PROBE B: {ziel} fehlt — nichts zu vergleichen."]

    original = ziel.read_bytes()
    sag(f"Original {ziel} ({len(original)} Bytes) gesichert.")

    with tempfile.TemporaryDirectory(prefix="probelauf-b-") as tmp:
        kopie = Path(tmp) / "kopie.json"
        kopie.write_bytes(original)
        try:
            # 1. Der dokumentierte Notfall-Weg: die Datei verschwindet.
            ziel.unlink()
            sag("Original geloescht — exakt der dokumentierte Korrekturweg.")

            # 2. Der naechste Lauf baut den Monat neu. data_root zeigt ins
            #    Wegwerf-Verzeichnis: data/kurse_de.json bleibt unberuehrt.
            #    Jede Ausnahme wird hier zum BEFUND, nicht zum Rueckwurf: ein
            #    Traceback statt eines Ergebnisses waere zwar auch rot, wuerde
            #    aber die Zusammenfassung verschlucken -- und die ist der
            #    eigentliche Zweck der Probe.
            try:
                _view, neu, _status = process_market(
                    MARKETS_BY_KEY["de"],
                    STICHTAGS_HEUTE,
                    ranking_root=Path(RANKING_DIR),
                    data_root=Path(tmp) / "data",
                )
            except RankingNotPossible as exc:
                fehler.append(f"PROBE B: Neuaufbau nicht moeglich — {exc}")
                sag(f"ROT: {exc}")
                return fehler
            except Exception as exc:  # noqa: BLE001 - die Probe soll den Grund zeigen
                fehler.append(f"PROBE B: Abbruch {type(exc).__name__}: {exc}")
                sag("ROT: " + traceback.format_exc())
                return fehler
            if not neu:
                fehler.append("PROBE B: kein Ranking gebildet — Korrekturweg traegt nicht.")
                sag("ROT: der Lauf hat den geloeschten Monat nicht nachgeholt.")
                return fehler
            sag(f"Neu gebildet: Stichtag {neu['stichtag']}, {len(neu['rangliste'])} Titel bewertet.")

            neu_bytes = ziel.read_bytes()

            # 3. Vergleich. Erst bitgleich?
            if neu_bytes == original:
                sag()
                sag("GRUEN (streng): byteweise identisch — Korrekturweg UND "
                    "Determinismus mit Live-Kursen bewiesen.")
                return fehler

            sag()
            sag("Nicht byteweise identisch. Jetzt feldweise — es gibt zwei "
                "vorher benannte, erklaerbare Abweichungen:")
            for pfad, grund in ERWARTET_ANDERS.items():
                sag(f"  erwartet anders: {pfad} — {grund}")

            alt_flach = _flach(json.loads(original.decode("utf-8")))
            neu_flach = _flach(json.loads(neu_bytes.decode("utf-8")))

            def erwartet(pfad: str) -> bool:
                return any(pfad == p or pfad.startswith(p + ".") for p in ERWARTET_ANDERS)

            unerwartet = []
            for pfad in sorted(set(alt_flach) | set(neu_flach)):
                a, n = alt_flach.get(pfad, "<fehlt>"), neu_flach.get(pfad, "<fehlt>")
                if a != n and not erwartet(pfad):
                    unerwartet.append((pfad, a, n))

            sag()
            if unerwartet:
                sag(f"ROT: {len(unerwartet)} unerwartete Abweichung(en):")
                for pfad, a, n in unerwartet[:25]:
                    sag(f"  {pfad}\n      alt: {a!r}\n      neu: {n!r}")
                if len(unerwartet) > 25:
                    sag(f"  … und {len(unerwartet) - 25} weitere")
                fehler.append(
                    f"PROBE B: {len(unerwartet)} Feld(er) haben sich veraendert, "
                    f"die sich nicht veraendern duerfen — kein Determinismus."
                )
            else:
                sag("GRUEN (feldweise): ausser den zwei benannten Stellen ist "
                    "alles bitgleich — Rangliste, Top-5, Abdeckung, Methode, "
                    "Stichtag. Der Korrekturweg traegt, die Rechnung ist "
                    "deterministisch.")

            # Die eigentliche Determinismus-Aussage INNERHALB der Ampel:
            # rendite_12m ist dieselbe Groesse wie damals.
            alt_r = alt_flach.get("trend_ampel.rendite_12m")
            neu_r = neu_flach.get("trend_ampel.rendite_12m")
            sag()
            sag(f"trend_ampel.rendite_12m  alt {pct(alt_r, 4)}  neu {pct(neu_r, 4)}")
            if alt_r != neu_r:
                fehler.append(
                    f"PROBE B: rendite_12m hat sich geaendert ({alt_r} -> {neu_r}) — "
                    f"die Indexreihe liefert heute andere Zahlen als am 02.08."
                )
                sag("ROT: die Indexreihe ist nicht mehr dieselbe.")
            else:
                sag("GRUEN: unveraendert — die Indexreihe liefert dieselben Kurse.")

            neu_ampel = json.loads(neu_bytes.decode("utf-8"))["trend_ampel"]
            sag()
            sag(f"NEU in der Ampel: riskfree_12m {pct(neu_ampel.get('riskfree_12m'))}, "
                f"ueberschuss_12m {pct(neu_ampel.get('ueberschuss_12m'))}, "
                f"Quelle {neu_ampel.get('riskfree_quelle')!r}, "
                f"Warnung {neu_ampel['warnung']}")
            if neu_ampel.get("riskfree_12m") is None:
                fehler.append(
                    "PROBE B: auch hier hat das fail-soft gegriffen — der €STR-Abruf "
                    "ueber die EZB-API hat nichts geliefert."
                )
                sag("ROT: fail-soft im Neuaufbau.")

        finally:
            # 4. Wiederherstellen. Immer. Auch nach einem Absturz.
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_bytes(original)
            zurueck = ziel.read_bytes() == original
            sag()
            sag(f"Wiederhergestellt: {ziel} — bitgleich zum Original: {zurueck}")
            if not zurueck:
                fehler.append("PROBE B: Wiederherstellung misslungen!")

    return fehler


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    heute = Date.fromisoformat(argv[0]) if argv else Date.today()

    sag("PROBELAUF — Wegwerf-Nachweis, schreibt nichts ins Repository.")
    sag(f"Arbeitsverzeichnis: {Path.cwd()}")

    fehler = probe_a(heute)
    fehler += probe_b()

    kopf("ERGEBNIS")
    if fehler:
        for f in fehler:
            sag(f"ROT: {f}")
        sag()
        sag(f"{len(fehler)} Befund(e) — Probe GESCHEITERT.")
        return 1
    sag("Beide Proben GRUEN.")
    sag("  A: der Zins-Pfad traegt live, ohne fail-soft.")
    sag("  B: der Korrekturweg baut den Monat identisch nach.")
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
