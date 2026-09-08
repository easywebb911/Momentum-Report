"""Reparatur-Agent, Stufe 3 -- erste, bewusst SCHMALE Ausbaustufe.

Deckt AUSSCHLIESSLICH eine einzige Fehlerklasse ab: ein neues, dem
bestehenden Parser unbekanntes Datumsformat im Vorspann einer der drei
DE-iShares-Bestandslisten (EXS1/DAX, EXS3/MDAX, EXS2/TecDAX). Kein anderer
Fehlertyp -- nicht die US-Fondslisten, nicht Anzahl-/Veraltungs-Gatter,
nicht Kursvergleich-Abweichler, nicht Toleranzschwellen -- fuehrt hier zu
irgendeiner Aktion. Das ist Absicht, nicht Unvollstaendigkeit: siehe die
Diagnose, auf der dieser Bau aufsetzt (nur diese eine Fehlerklasse ist
mechanisch eng genug, um ohne Domaenenurteil sicher zu sein).

DER GANZE WEG, in drei Schritten:
  1. `tools/vertragstest.py` hat bereits erkannt UND unterschieden: ein
     Fund landet in `agent_befund()` NUR, wenn `Verdikt.vorspann_zeilen`
     nicht leer ist -- das ist strukturell garantiert nur bei "im Vorspann
     steht kein lesbarer Bestands-Stichtag" der Fall, bei KEINEM anderen
     Abbruchgrund. Dieses Modul rät an KEINER Stelle im Log-Text.
  2. `leite_muster_ab()` (hier) versucht, aus der rohen Vorspann-Zeile
     GENAU EIN unzweideutiges Tag/Monat/Jahr-Tripel zu lesen -- ueber
     DIESELBE Monatstabelle (`momentum.ishares.MONATE`), die der
     bestehende Parser auch verwendet, keine neu erfundene. Gelingt das
     nicht zweifelsfrei (kein Jahr, kein bekannter Monatsname, mehr als
     ein Tages-Kandidat, ungueltiges Kalenderdatum, ...), ist das Ergebnis
     `None` -- KEIN Rateversuch, sondern der "unklar"-Pfad.
  3. Ein erfolgreiches Tripel wird NIE zu einem generischen Muster
     verallgemeinert. Das neue Regex-Muster wird buchstaeblich AUS der
     beobachteten Zeile gebaut: Tag-, Monats- und Jahres-Teilstring werden
     durch ihre Erfassungsgruppe ersetzt, ALLES andere bleibt als exakt
     escapeter Literaltext stehen. Das neue Muster kann also nicht mehr
     "erraten" haben als das, was tatsaechlich vorlag -- der Beleg dafuer
     ist die rohe Zeile selbst, die im PR-Text wörtlich zitiert wird.

HARTE GRENZEN (siehe Auftrag):
  * Ausschliesslich additiv: das erzeugte Muster wird als NEUER Block vor
    dem AGENT-ANKER in `_datum_aus_text` eingefuegt (siehe ishares.py).
    Kein bestehendes Muster wird angefasst, ersetzt oder umsortiert.
  * Keine Toleranzschwelle, kein Gatter-Kriterium, keine Score-/Filter-
    Logik wird je beruehrt -- dieses Modul kennt nur `_datum_aus_text`.
  * Bei jeder Unsicherheit: `leite_muster_ab()` gibt `None` zurueck, die
    aufrufende Seite (Workflow) meldet nur per ntfy, oeffnet KEINEN PR.
  * Der Agent MERGT NIE. Dieses Modul erzeugt hoechstens den Inhalt eines
    PRs (Branch-Diff, Titel, Text mit woertlichem Zitat) -- das Oeffnen
    selbst und jedes Schreiben ins Repository geschieht ausschliesslich
    im Workflow-Schritt (`gh pr create`), NIE mit Merge-Recht.

DETERMINISMUS: `leite_muster_ab()` ist eine reine Funktion derselben
Roh-Zeile -- keine Zeit, kein Zufall, kein Netz. Dieselbe Zeile ergibt
immer denselben Vorschlag, byte-gleich (siehe Tests).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from momentum.ishares import MONATE, _datum_aus_text  # noqa: E402

Date = _dt.date

ISHARES_PY_PFAD = Path("src/momentum/ishares.py")

AGENT_ANKER = (
    "    # --- AGENT-ANKER (Stufe 3, siehe tools/agent_datumsformat.py): ein\n"
)

# Nur Jahre in diesem Fenster gelten als Jahres-Kandidat. Eng genug, um eine
# zufaellige zweistellige Zahl (Fondsgroesse, ISIN-Fragment) nicht als Jahr
# misszudeuten; weit genug fuer jeden realistischen Bestands-Stichtag.
_JAHR_MUSTER = re.compile(r"(?<!\d)(20[0-4]\d)(?!\d)")
_ZAHL_MUSTER = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")
_WORT_MUSTER = re.compile(r"[A-Za-zÄÖÜäöüß]{3,9}")


@dataclass(frozen=True)
class Ableitung:
    """Das Ergebnis eines gelungenen, eindeutigen Ableitungsversuchs."""

    rohzeile: str        # die Zeile, WIE SIE IN DER DATEI STAND
    aufbereitet: str      # nach derselben Vorbehandlung wie _datum_aus_text
    datum: Date
    muster: str           # das neue, additive Regex-Muster (roher String)
    gruppen: tuple[str, ...]   # Reihenfolge der Erfassungsgruppen im Muster


def _ueberlappt(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def leite_muster_ab(zeile: str) -> Ableitung | None:
    """Versucht, aus EINER rohen Vorspann-Zeile ein neues, additives Muster
    abzuleiten. `None` heisst: nicht zweifelsfrei moeglich, NICHT geraten."""
    if _datum_aus_text(zeile) is not None:
        # Verteidigungslinie: laut Vertragstest sollte diese Zeile an ALLEN
        # vier bestehenden Mustern gescheitert sein. Liest sie doch schon
        # jemand, ist das kein neuer Fall -- eher ein Widerspruch, den man
        # sich ansehen sollte, aber sicher kein Grund, etwas zu aendern.
        return None

    aufbereitet = zeile.lstrip("﻿").strip().strip('"')

    jahr_treffer = list(_JAHR_MUSTER.finditer(aufbereitet))
    if len(jahr_treffer) != 1:
        return None
    jahr_span = jahr_treffer[0].span()
    jahr = int(jahr_treffer[0].group(1))

    monat_kandidaten = [
        (m.span(), MONATE[m.group(0)[:3].lower()])
        for m in _WORT_MUSTER.finditer(aufbereitet)
        if m.group(0)[:3].lower() in MONATE
    ]
    if len(monat_kandidaten) != 1:
        return None
    monat_span, monat = monat_kandidaten[0]
    if _ueberlappt(monat_span, jahr_span):
        return None

    tag_kandidaten = []
    for m in _ZAHL_MUSTER.finditer(aufbereitet):
        span = m.span()
        if _ueberlappt(span, jahr_span) or _ueberlappt(span, monat_span):
            continue
        wert = int(m.group(1))
        if 1 <= wert <= 31:
            tag_kandidaten.append((span, wert))
    if len(tag_kandidaten) != 1:
        return None
    tag_span, tag = tag_kandidaten[0]

    try:
        datum = Date(jahr, monat, tag)
    except ValueError:
        return None

    spannen = sorted(
        [("tag", tag_span), ("monat", monat_span), ("jahr", jahr_span)],
        key=lambda paar: paar[1][0],
    )
    muster_teile: list[str] = []
    gruppen: list[str] = []
    position = 0
    ersatz = {
        "tag": r"(\d{1,2})",
        "monat": r"([A-Za-zÄÖÜäöüß]{3,9})",
        "jahr": r"(\d{4})",
    }
    for name, (start, ende) in spannen:
        muster_teile.append(re.escape(aufbereitet[position:start]))
        muster_teile.append(ersatz[name])
        gruppen.append(name)
        position = ende
    muster_teile.append(re.escape(aufbereitet[position:]))
    muster = "".join(muster_teile)

    # Letzte Verteidigungslinie: das abgeleitete Muster muss die Zeile,
    # aus der es kommt, tatsaechlich treffen und exakt dasselbe Datum
    # liefern wie oben ermittelt -- sonst lieber gar kein Vorschlag als
    # ein widerspruechlicher.
    probe = re.search(muster, aufbereitet)
    if probe is None:
        return None
    werte = {name: probe[i + 1] for i, name in enumerate(gruppen)}
    monat_probe = MONATE.get(werte["monat"][:3].lower())
    if monat_probe is None:
        return None
    try:
        if Date(int(werte["jahr"]), monat_probe, int(werte["tag"])) != datum:
            return None
    except ValueError:
        return None

    return Ableitung(
        rohzeile=zeile, aufbereitet=aufbereitet, datum=datum,
        muster=muster, gruppen=tuple(gruppen),
    )


def erzeuge_codeschnipsel(ableitung: Ableitung, quelle: str, stichtag: Date) -> str:
    """Der neue, additive Python-Block fuer `_datum_aus_text` -- Text, kein
    Diff. Kommentar zitiert die rohe Zeile woertlich, exakt das, was der
    PR-Text ebenfalls tut (dieselbe Quelle, keine zweite Abschrift)."""
    idx = {name: i + 1 for i, name in enumerate(ableitung.gruppen)}
    zeile_kommentar = ableitung.rohzeile.replace("\n", "\\n")
    return f"""    # Neu am {stichtag.isoformat()} bei {quelle} beobachtet, vom
    # Reparatur-Agenten (Stufe 3) additiv ergaenzt -- woertliche Vorspann-
    # Zeile: {zeile_kommentar!r}
    treffer = re.search(r"{ableitung.muster}", aufbereitet)
    if treffer:
        monat = MONATE.get(treffer[{idx["monat"]}][:3].lower())
        if monat:
            return _dt.date(int(treffer[{idx["jahr"]}]), monat, int(treffer[{idx["tag"]}]))
"""


def wende_an(quelltext: str, codeschnipsel: str) -> str:
    """Fuegt `codeschnipsel` additiv VOR dem Agent-Anker in `_datum_aus_text`
    ein. Findet der Anker sich nicht (Datei anders als erwartet umgebaut),
    wird NICHTS veraendert -- ein KeyError ist hier sicherer als ein
    Einfuegen an falscher Stelle."""
    if AGENT_ANKER not in quelltext:
        raise RuntimeError(
            "AGENT-ANKER nicht gefunden — ishares.py wurde vermutlich "
            "seit dem Bau dieses Agenten umgebaut. Nichts eingefuegt."
        )
    if quelltext.count(AGENT_ANKER) != 1:
        raise RuntimeError(
            "AGENT-ANKER kommt nicht genau einmal vor — mehrdeutig, "
            "nichts eingefuegt."
        )
    return quelltext.replace(AGENT_ANKER, codeschnipsel + AGENT_ANKER)


@dataclass(frozen=True)
class Vorschlag:
    quelle: str
    rohzeile: str
    datum: Date
    codeschnipsel: str
    neuer_quelltext: str


@dataclass(frozen=True)
class Unklar:
    quelle: str
    rohzeilen: tuple[str, ...]


def verarbeite_befund(befund: dict, *, ishares_quelltext: str) -> list[Vorschlag | Unklar]:
    """Ein einzelner Fund aus dem Vertragstest-Artefakt (siehe
    vertragstest.agent_befund) -> entweder ein oder mehrere Vorschlaege
    (i.d.R. einer, eine Zeile traegt meist genau einen Stichtag) oder,
    wenn keine Zeile eindeutig lesbar war, ein einziges Unklar."""
    quelle = befund["quelle"]
    stichtag = Date.fromisoformat(befund.get("stichtag") or Date.today().isoformat())
    ergebnisse: list[Vorschlag | Unklar] = []
    text = ishares_quelltext
    for zeile in befund["vorspann_zeilen"]:
        ableitung = leite_muster_ab(zeile)
        if ableitung is None:
            continue
        schnipsel = erzeuge_codeschnipsel(ableitung, quelle, stichtag)
        try:
            text = wende_an(text, schnipsel)
        except RuntimeError:
            continue
        ergebnisse.append(Vorschlag(
            quelle=quelle, rohzeile=zeile, datum=ableitung.datum,
            codeschnipsel=schnipsel, neuer_quelltext=text,
        ))
    if not ergebnisse:
        return [Unklar(quelle=quelle, rohzeilen=tuple(befund["vorspann_zeilen"]))]
    return ergebnisse


def pr_text(vorschlag: Vorschlag) -> tuple[str, str]:
    """(Titel, Text) fuer den PR -- die rohe Zeile steht woertlich drin,
    "CI ist gruen" taucht als Begruendung nirgends auf (siehe Auftrag)."""
    titel = f"Agent: iShares-Datumsformat {vorschlag.quelle}"
    text = f"""## Was
`{vorschlag.quelle}` lieferte am Vertragstest einen Vorspann, den
`_datum_aus_text` (`src/momentum/ishares.py`) nicht lesen konnte. Dieser
PR ergaenzt EIN neues, additives Muster -- kein bestehendes Muster wurde
angefasst, ersetzt oder umsortiert.

## Der Beleg -- wörtlich, nicht paraphrasiert
Die tatsächlich fehlgeschlagene Vorspann-Zeile:

    {vorschlag.rohzeile!r}

Interpretiert als: **{vorschlag.datum.isoformat()}**
(Tag {vorschlag.datum.day}, Monat {vorschlag.datum.month}, Jahr {vorschlag.datum.year})

Bitte diese Übersetzung von Hand gegenprüfen, bevor gemergt wird — das
ist genau der Schritt, den dieser Agent NICHT selbst geht.

## Was NICHT geändert wurde
Kein Gatter-Kriterium, keine Toleranzschwelle, keine Score- oder
Filter-Logik. Ausschließlich `_datum_aus_text`, ausschließlich additiv.

## Rückweg
`git revert` dieses Commits — die vier bestehenden Muster bleiben davon
unberührt, es entsteht wieder derselbe (bereits bekannte) Bruch für diese
eine Quelle beim nächsten Vertragstest.

## Merge-Klasse
Manual-Merge — jeder vom Agenten geöffnete PR, ausnahmslos. Der Agent
merged nie, unter keinen Umständen. Easy prüft die Übersetzung oben und
merged von Hand.
"""
    return titel, text


def main(argv: list[str] | None = None, *, melder=None) -> int:
    """`melder` ist die Test-Naht fuer die "unklar"-Meldung (siehe
    vertragstest.main()s `melder`-Parameter, dasselbe Muster) -- ohne sie
    der echte `notify.push_agent_datumsformat_unklar`. Import erst hier,
    nicht am Modulkopf: dieses Werkzeug soll auch ohne gesetztes
    NTFY_TOPIC importierbar und pytest-sammelbar bleiben."""
    if melder is None:
        from momentum.notify import push_agent_datumsformat_unklar as melder

    parser = argparse.ArgumentParser(
        description="Agent Stufe 3: Datumsformat-Vorschlaege aus einem Vertragstest-Befund ableiten."
    )
    parser.add_argument("befund", help="Pfad zum JSON-Befund aus vertragstest.py --agent-befund")
    parser.add_argument(
        "--ausgabe", required=True,
        help="Pfad, unter dem die abgeleiteten Vorschlaege/Unklarheiten als JSON entstehen.",
    )
    args = parser.parse_args(argv)

    daten = json.loads(Path(args.befund).read_text(encoding="utf-8"))
    quelltext = ISHARES_PY_PFAD.read_text(encoding="utf-8")

    vorschlaege = []
    unklare = []
    for befund in daten["funde"]:
        befund = {**befund, "stichtag": daten.get("stichtag")}
        for ergebnis in verarbeite_befund(befund, ishares_quelltext=quelltext):
            if isinstance(ergebnis, Vorschlag):
                titel, text = pr_text(ergebnis)
                vorschlaege.append({
                    "quelle": ergebnis.quelle,
                    "rohzeile": ergebnis.rohzeile,
                    "datum": ergebnis.datum.isoformat(),
                    "titel": titel,
                    "pr_text": text,
                    "codeschnipsel": ergebnis.codeschnipsel,
                    "neuer_quelltext": ergebnis.neuer_quelltext,
                })
            else:
                unklare.append({
                    "quelle": ergebnis.quelle,
                    "rohzeilen": list(ergebnis.rohzeilen),
                })

    if unklare:
        melder([{"quelle": u["quelle"], "rohzeilen": u["rohzeilen"]} for u in unklare])

    Path(args.ausgabe).write_text(
        json.dumps(
            {"schema": 1, "vorschlaege": vorschlaege, "unklar": unklare},
            ensure_ascii=False, indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(vorschlaege)} Vorschlag/Vorschlaege, {len(unklare)} unklar.")
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
