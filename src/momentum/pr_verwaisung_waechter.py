"""PR-Verwaisungs-Waechter: erkennt offene PRs, die laenger als fuenf
Werktage unangetastet liegen bleiben.

Drittes Modul nach demselben Grundmuster wie waechter.py (Lauf) und
handover_waechter.py (Doku), auf ein drittes Symptom angewandt:
insbesondere MANUAL-MERGE-PRs warten auf Easys bewusste Entscheidung
(siehe SESSION_HANDOVER.md §7.4) -- niemand ausser Easy selbst stoesst
das Mergen an, und ein liegen gebliebener PR meldet sich nie von selbst.

Geprueft werden ALLE offenen PRs, nicht nur Manual-Merge-Klasse: die
Merge-Klasse steht nur als Freitext im PR-Titel/-Text (seit #14, siehe
SESSION_HANDOVER.md §2), ein Textmuster-Abgleich darauf waere eine
fragile Annahme ueber eine Formulierung, die sich jederzeit aendern
kann, ohne dass dieser Waechter etwas davon mitbekommt. Ein liegen
gebliebener SELF-MERGE-PR (sollte er je vorkommen -- Claude merged sie
sonst selbst nach gruenem CI) waere ebenfalls ein echter Befund, keine
Fehlmeldung. "insbesondere Manual-Merge" aus dem Auftrag beschreibt den
HAEUFIGSTEN, nicht den EINZIGEN Fall.

DIE ZAEHLWEISE, exakt: "unangetastet" heisst kein neuer Commit, kein
Kommentar UND keine Review seit dem letzten Kontakt -- eine Review ohne
begleitenden PR-Kommentar (z. B. eine reine Genehmigung) ist trotzdem
ein echtes Lebenszeichen und zaehlt deshalb mit; eine rein woertliche
Lesart von "Commit oder Kommentar" haette das ignoriert und waere
weniger nuetzlich gewesen (bewusste Erweiterung, hier gemeldet statt
stillschweigend entschieden). "Letzter Kontakt" ist das spaeteste
Datum aus: Erstellung des PR, jedem Commit (`committedDate`), jedem
PR-Kommentar (`createdAt`) und jeder Review (`submittedAt`).

WERKTAGE, nicht Kalendertage: Samstag/Sonntag zaehlen nie. Gezaehlt wird
das halboffene Intervall (letzter Kontakt, heute] -- 0, wenn heute genau
der Kontakttag ist oder frueher liegt.

WIDERSPRUCH GEMELDET (Kriterium 2), nicht stillschweigend hingenommen:
5 Werktage entsprechen ungefaehr einer Kalenderwoche. Bei einem rein
WOECHENTLICHEN Cron (wie hier vorgegeben) bedeutet das: ein PR, der am
Montag zuletzt beruehrt wurde, zeigt beim naechsten woechentlichen Lauf
(sieben Tage spaeter) exakt 5 Werktage -- NICHT MEHR als 5, also noch
KEINE Meldung. Die tatsaechliche Erkennungsverzoegerung liegt dadurch
bei ZWEI woechentlichen Laeufen (ca. 10-14 Kalendertage), nicht bei
einem. Das ist eine mechanische Folge der Kombination aus Schwelle (5
Werktage) und Rhythmus (woechentlich), beides unveraendert aus dem
Auftrag uebernommen -- hier nur benannt, nicht durch eine eigenmaechtig
geaenderte Schwelle "kompensiert".

HARTE GRENZE, wie bei jedem Waechter dieses Projekts: MELDEN, NIE
HANDELN. Dieses Modul liest ausschliesslich (`gh pr list`) und schreibt
NIRGENDS einen PR-Kommentar, mergt nichts, schliesst nichts. Abgesichert
auf zwei Ebenen wie bei handover_waechter.py: das Workflow-Token traegt
nur `contents: read`, `pull-requests: read` und `issues: read` (PR-
Kommentare laufen ueber die Issues-API) -- ein `gh pr comment`/`gh pr
merge`/`gh pr close` waere damit bereits am Token abgelehnt -- UND ein
statischer Test durchsucht diese Datei nach jedem entsprechenden Aufruf.

DIE PUSH-MECHANIK: EIN lautloser Push (Prioritaet "min", wie
push_waechter_ok/push_handover_pflege_faellig), NIE eine Sirene --
dieselbe Begruendung wie beim Doku-Waechter: eine Erinnerung, kein
Alarmzustand. Der Lauf bleibt GRUEN (Exit 0), solange sich der Zustand
ermitteln liess -- egal ob verwaiste PRs gefunden wurden oder nicht.
ROT (Exit 1) nur bei technischem Unvermoegen, den Zustand ueberhaupt zu
ermitteln (dasselbe Prinzip wie bei den anderen beiden Waechtern).

GRENZE, ehrlich benannt: gezaehlt werden PRs, die `gh pr list --state
open` liefert. Ein PR, der zwischenzeitlich per Draft/Ready-Wechsel
oder Label beruehrt wurde, aber ohne Commit/Kommentar/Review, zaehlt
weiterhin als unangetastet -- das ist so gewollt (ein Label-Wechsel ist
kein inhaltlicher Fortschritt).

ZWEI-SCHRITT-ABFRAGE (behoben nach echtem Fehlschlag, Actions-Run
36446094919 am 28.09.2026, Zeitpunkt der Behebung): `gh pr list --json
...,commits,...` bricht mit `GraphQL: ... requesting up to 1,000,000
possible nodes which exceeds the maximum limit of 500,000` ab -- und
zwar UNABHAENGIG von der tatsaechlichen PR-Zahl (bewiesen: der
Fehlschlag trat auch bei null offenen PRs auf). Ursache: `Commit.
authors` ist im GitHub-GraphQL-Schema selbst eine Connection (ein
Commit kann mehrere Autoren haben), keine einfache Referenz. Die von
`gh` intern gebaute Abfrage schaetzt die maximale Knotenzahl als
PRODUKT der verschachtelten Seitengroessen (PRs x Commits je PR x
Autoren je Commit) -- bei `--limit 200` weit ueber der 500.000-Grenze,
egal wie viele PRs es wirklich gibt. `comments`/`reviews` loesen das
NICHT aus: beide sind zwar auch Connections, ihre Autor-Unterfelder
sind aber einfache Referenzen, keine weitere Connection (die
Fehlermeldung nennt explizit "authors", nicht "comments"/"reviews").

Deshalb jetzt zweistufig: Schritt 1 (`_offene_prs_ohne_commits`) holt
ALLE offenen PRs in einem Rutsch, aber OHNE `commits` -- bleibt bei
`number,title,createdAt,comments,reviews`, alles unproblematisch.
Schritt 2 (`_commits_nachladen`) laedt die Commit-Liste JE OFFENEM PR
EINZELN nach (`gh pr view <n> --json commits`), nur fuer die PRs, die
Schritt 1 tatsaechlich liefert -- typischerweise 0-3, nie alle 200 auf
einmal. Selbst im unguenstigsten Einzelfall (ein PR mit 250 Commits x
100 Autoren = 25.000 Knoten) bleibt das weit unter der 500.000-Grenze.

Rate-Limit-Ueberlegung (Kriterium 2, hier durchgerechnet statt
angenommen): Schritt 2 braucht einen zusaetzlichen `gh`-Aufruf JE
offenem PR. Selbst bei (fuer dieses Repo unrealistisch hohen) 50
gleichzeitig offenen PRs waeren das 51 Aufrufe in einem Lauf -- gegen
das REST-/GraphQL-Rate-Limit von 5.000 Anfragen/Stunde des
GITHUB_TOKEN vernachlaessigbar. Kein Grund, vorsorglich zu bremsen.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path

from .notify import push_pr_verwaist

Date = _dt.date

# Laenger als fuenf Werktage unangetastet -> Meldung faellig. Unveraendert
# aus dem Auftrag uebernommen, nicht selbst hergeleitet.
SCHWELLE_WERKTAGE = 5

# Grosszuegig ueber der realistischen Zahl gleichzeitig offener PRs dieses
# Repos -- dasselbe Prinzip wie PR_LISTEN_LIMIT in handover_waechter.py.
PR_LISTEN_LIMIT = 200


def log(text: str) -> None:
    print(text, flush=True)


def _als_datetime(rohwert: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(str(rohwert).replace("Z", "+00:00"))


def letzter_kontakt(pr: dict) -> _dt.datetime:
    """Spaetester Zeitpunkt aus Erstellung, Commits, Kommentaren und
    Reviews. Ein PR ganz ohne jede Aktivitaet seit der Erstellung faellt
    dadurch auf sein `createdAt` zurueck -- nie auf einen geratenen Wert."""
    kandidaten = [pr["createdAt"]]
    for commit in pr.get("commits") or []:
        if commit.get("committedDate"):
            kandidaten.append(commit["committedDate"])
    for kommentar in pr.get("comments") or []:
        if kommentar.get("createdAt"):
            kandidaten.append(kommentar["createdAt"])
    for review in pr.get("reviews") or []:
        if review.get("submittedAt"):
            kandidaten.append(review["submittedAt"])
    return max(_als_datetime(z) for z in kandidaten)


def werktage_seit(letzter: Date, heute: Date) -> int:
    """Anzahl Werktage (Mo-Fr) im halboffenen Intervall (letzter, heute].

    0, falls `heute` auf denselben Tag faellt wie `letzter` oder davor
    liegt (kann bei Uhrzeit-Rundungsdifferenzen zwischen `createdAt` und
    einer per --heute erzwungenen Pruefzeit vorkommen -- dann ist
    schlicht noch kein Werktag vergangen)."""
    if heute <= letzter:
        return 0
    werktage = 0
    tag = letzter + _dt.timedelta(days=1)
    while tag <= heute:
        if tag.weekday() < 5:
            werktage += 1
        tag += _dt.timedelta(days=1)
    return werktage


def _offene_prs_ohne_commits(
    *, laeufer=subprocess.run, limit: int = PR_LISTEN_LIMIT
) -> tuple[list[dict] | None, str | None]:
    """Schritt 1: alle offenen PRs in einem Rutsch, OHNE `commits` --
    dieses Feld allein loeste den echten GraphQL-Node-Limit-Fehlschlag
    aus (siehe Modul-Docstring). `number,title,createdAt,comments,
    reviews` sind ausschliesslich Skalare bzw. unproblematische
    Connections und bleiben deshalb in der Sammel-Abfrage."""
    try:
        ergebnis = laeufer(
            [
                "gh", "pr", "list",
                "--state", "open",
                "--limit", str(limit),
                "--json", "number,title,createdAt,comments,reviews",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"gh pr list endete mit rc={ergebnis.returncode}: "
            f"{ergebnis.stderr.strip()}"
        )
    try:
        return json.loads(ergebnis.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh pr list lieferte kein gueltiges JSON ({exc})."


def _commits_nachladen(
    nummer: int, *, laeufer=subprocess.run
) -> tuple[list[dict] | None, str | None]:
    """Schritt 2: die Commit-Liste EINES einzelnen PR nachladen. Bei
    genau einem PR pro Aufruf bleibt selbst der unguenstigste Fall (250
    Commits x 100 Autoren = 25.000 Knoten) weit unter der 500.000-
    Knoten-Grenze -- die Multiplikation mit der PR-Zahl aus der alten
    Sammel-Abfrage entfaellt dadurch vollstaendig."""
    try:
        ergebnis = laeufer(
            ["gh", "pr", "view", str(nummer), "--json", "commits"],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return None, f"gh liess sich nicht aufrufen ({type(exc).__name__}: {exc})."
    if ergebnis.returncode != 0:
        return None, (
            f"gh pr view {nummer} endete mit rc={ergebnis.returncode}: "
            f"{ergebnis.stderr.strip()}"
        )
    try:
        daten = json.loads(ergebnis.stdout)
    except json.JSONDecodeError as exc:
        return None, f"gh pr view {nummer} lieferte kein gueltiges JSON ({exc})."
    return daten.get("commits") or [], None


def offene_prs(
    *, laeufer=subprocess.run, limit: int = PR_LISTEN_LIMIT
) -> tuple[list[dict] | None, str | None]:
    """(rohe PR-Datensaetze aller offenen PRs, je PR bereits mit
    nachgeladener `commits`-Liste, Fehlergrund). Genau einer der beiden
    ist None.

    Ruft Schritt 2 NUR fuer PRs auf, die Schritt 1 tatsaechlich liefert
    -- bei null offenen PRs (der reale, bisher fehlschlagende Fall)
    passiert also genau EIN `gh`-Aufruf, kein einziger mehr."""
    prs, grund = _offene_prs_ohne_commits(laeufer=laeufer, limit=limit)
    if grund is not None:
        return None, grund
    for pr in prs:
        commits, grund = _commits_nachladen(pr["number"], laeufer=laeufer)
        if grund is not None:
            return None, grund
        pr["commits"] = commits
    return prs, None


def verwaiste_prs(
    offene: list[dict], heute: Date
) -> tuple[list[tuple[int, str, int, int]] | None, str | None]:
    """(sortierte Liste (Nummer, Titel, Werktage seit Kontakt,
    Kalendertage seit Erstellung) je verwaistem PR, Fehlergrund).

    Ein PR ohne verwertbares `createdAt` ist selbst ein Befund (Kriterium
    2) -- er wuerde sich sonst nicht sauber gegen `heute` abgrenzen
    lassen, genau wie ein PR ohne `mergedAt` bei gemergte_prs_seit()
    in handover_waechter.py."""
    verwaist: list[tuple[int, str, int, int]] = []
    for pr in offene:
        if not pr.get("createdAt"):
            return None, f"PR #{pr.get('number', '?')} traegt kein createdAt."
        try:
            kontakt = letzter_kontakt(pr)
            erstellt = _als_datetime(pr["createdAt"])
        except ValueError as exc:
            return None, f"PR #{pr.get('number', '?')}: unlesbares Datum ({exc})."
        werktage = werktage_seit(kontakt.date(), heute)
        if werktage > SCHWELLE_WERKTAGE:
            kalendertage = (heute - erstellt.date()).days
            verwaist.append((pr["number"], pr.get("title", ""), werktage, kalendertage))
    verwaist.sort(key=lambda eintrag: eintrag[0])
    return verwaist, None


def stand_text(verwaist: list[tuple[int, str, int, int]]) -> str:
    """Die Nutzlast des Push -- je PR Nummer, Werktage seit Kontakt UND
    Kalendertage seit Erstellung (damit klar ist, ob es sich um einen
    frischen oder einen laengst betagten PR handelt)."""
    zeilen = [
        f"#{nummer} ({titel}): {werktage} Werktag(e) ohne Commit/Kommentar/"
        f"Review, seit {kalendertage} Kalendertag(en) offen"
        for nummer, titel, werktage, kalendertage in verwaist
    ]
    return (
        f"{len(verwaist)} offene(r) PR(s) laenger als {SCHWELLE_WERKTAGE} "
        f"Werktage unangetastet:\n" + "\n".join(zeilen)
    )


def _melden(melder, text: str) -> None:
    """Der Push ist NIE wichtiger als das Wachen selbst -- dasselbe
    Prinzip wie in den beiden anderen Waechtern."""
    try:
        verschickt = melder(text)
    except Exception as exc:  # noqa: BLE001 - der Push ist Beiwerk
        log(f"Waechter: Push fehlgeschlagen ({type(exc).__name__}: {exc}).")
        return
    log(
        "Waechter: Push (lautlos) verschickt."
        if verschickt
        else "Waechter: Push NICHT verschickt (siehe Meldung oben)."
    )


def main(
    argv: list[str] | None = None,
    *,
    melder=push_pr_verwaist,
    ermittle_prs=offene_prs,
) -> int:
    """`melder`/`ermittle_prs` sind die Test-Naehte, wie bei den anderen
    beiden Waechtern."""
    parser = argparse.ArgumentParser(description="PR-Verwaisungs-Waechter")
    parser.add_argument("--heute", help="Pruefdatum JJJJ-MM-TT (nur fuer Tests)")
    args = parser.parse_args(argv)
    heute = Date.fromisoformat(args.heute) if args.heute else Date.today()

    offene, grund = ermittle_prs()
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte offene PRs nicht ermitteln: {grund}")
        return 1

    verwaist, grund = verwaiste_prs(offene, heute)
    if grund is not None:
        log(f"Waechter: Zustand nicht ermittelbar — {grund}")
        _melden(melder, f"Konnte offene PRs nicht ermitteln: {grund}")
        return 1

    if not verwaist:
        log(f"Waechter: {len(offene)} offene PR(s), keiner ueber der Schwelle — still.")
        return 0

    text = stand_text(verwaist)
    log(f"Waechter: Meldung faellig — {text}")
    _melden(melder, text)
    # Bewusst gruen: der Push IST das Signal (siehe Modul-Docstring).
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
