# Session-Handover — Momentum-Report

**Nachtrag 03.11.2026:** PR #86 (Beleg-Zähler) gemergt (`5f6ccd8`).
Erster Messpunkt (Lauf 97): DE 0 mit / 5 ohne Rohkurs — V3-Annahme für DE
widerlegt (1 Messpunkt, §4 Punkt 16). PR #87 (Workflow-Hygiene:
Injektions-Fix §4 Punkt 14c, Node-24-Actions §5 Punkt 1) liegt vor —
MANUAL, Merge durch Easy nach der Zähler-Auswertung am 05.11. Handover
aufgeräumt: Ranking-Verlauf entschieden (nicht bauen), §4 Punkte 2, 5,
7, 9, 11, 12 geschlossen (Volltext in §10), 6 und 10 bewusst offen
gelassen, 1, 3, 14d, 14e geparkt.

**Nachtrag 01.11.2026, abends:** PR #85 (Evaluation, PR 3 von 3) ist
**gemergt** (`d457924`) — der Methodenwechsel-Umbau ist vollständig.
Diagnose zur nächtlichen Kurs-Lücke und zu den Abbrüchen 94/95 liegt vor
(§4 Punkt 16: Ursache Yahoo-Verzögerung belegt, Lücke „stiller falscher
Stichtag" in `resolve_asof`, Design V1–V3, Entscheidung Easy: V3 erst
nach Beleg ab 02.12.). Dazu ein reiner **Beleg-Zähler** in `data.py`
(PR #86, siehe §2) — keine Verhaltensänderung.

**Stand: 01.11.2026, später noch:** PR #84 (Methodik-Seite und Karten
zeigen den Methodenwechsel) ist **gemergt** (Merge-Commit `022c8ff`).
PR 3 von 3 (Evaluation: Gesamtrückblick zählt verschiedene Regeln nie
zusammen, Methodenwechsel-Hinweis) liegt als **PR #85** vor — MANUAL,
Easy liest vor dem Merge. Damit ist der Methodenwechsel-Umbau (§4
Punkt 8, §6 Punkt 0) inhaltlich vollständig, fehlt nur noch der Merge
von PR #85.

**Nachtrag 01.11.2026, später:** PR #83 (Rechnung, Gewichts-Fahrplan)
ist **gemergt** (Merge-Commit `f5a21b3`). PR 2 von 3 (Methodik-Seite und
Karten zeigen den Wechsel, neue Quellen, erweiterter Lit-Check in §4
Punkt 8) liegt als **PR #84** vor — MANUAL, Easy liest vor dem Merge.

**Nachtrag 01.11.2026:** Entscheidung Easy zu den Score-Gewichten —
**USA ab Ranking-Monat 2026-11: 100 % 12-1-Momentum, 0 % 52-Wochen-Hoch;
Deutschland unverändert 50/50** (Begründung und Quellen: §4 Punkt 8).
Gebaut als **Gewichts-Fahrplan je Markt** (PR 1 von 3, MANUAL, PR #83
— siehe §2, §7.6); Methodik/Karten (PR 2) und Evaluation (PR 3) folgen,
Fristen in §3. Außerdem: die drei geplanten Tasks senden seit 01.11.
direkt an ntfy.sh (§4 Punkt 15).

**Stand davor: 31.10.2026, nachmittags**, nach PR #81 (Evaluation-Seite:
Gesamtrückblick vor Monatsrückblick — **gemergt**, Merge-Commit
`0972fe7`, 31.10.2026 10:58 UTC) und der **Umstellung der drei geplanten
Claude-Tasks auf Nur-Lesen + App-Push samt Abschaltung der
Agenten-Kontrolle** (31.10.2026, Entscheidung Easy, siehe §4 Punkt 15).
Das Oktober-Ranking (Stichtag 30.10.) liegt vor, die Wiedervorlagen vom
30./31.10. sind ausgewertet (§3, §10). Nachgezogen: PR #76 (Wiedervorlagen-Wächter — `faellig`-Kommentare in
§3 plus eigener Wächter, Schritt 2 der am 24.10.2026 festgelegten
Automatisierung), PR #77 (Schutz-Sperre — PR-Check gegen geschützte
Zonen, Schritt 3 desselben Plans, **ausnahmsweise trotz rotem
Eigen-Check gemergt** — das Label ließ sich am iPhone nicht setzen,
ohne Ruleset nicht blockierend), PR #78 (Schutz-Sperre: Label-Freigabe
entfernt, reine Ampel statt Sperre — Grund: Code/Agenten handeln als
easywebb911, siehe §4 Punkt 14 und §7.8, **gemergt**), PR #79
(Agenten-Kontrolle — Alarm, wenn der geplante Wächter-Agent sich seit
über 48 Std. nicht mehr gemeldet hat, siehe §4 Punkt 15 — **gemergt**,
Merge-Commit `9f0238c`, 25.10.2026, 20:22 UTC, per `gh`/API
gegenprüft), PR #80 (Abbruchpfad-Meldung, siehe §4 Punkt 16 —
**gemergt**, Merge-Commit `569e385`, 31.10.2026, 10:42 UTC, per
`gh`/API gegenprüft), PR #81 (Evaluation-Reihenfolge, siehe §2 —
**gemergt**, `0972fe7`, per `gh`/API gegenprüft).
Repo `easywebb911/Momentum-Report`, Branch `main` — den aktuellen Stand
nennt `git log -1`, er steht hier bewusst nicht als Zahl.

Dieses Dokument ist der Übergabepunkt zwischen zwei Arbeits-Sitzungen. Es
beantwortet drei Fragen: *Was läuft gerade?*, *Was ist offen?*, *Was darf
man nicht kaputtmachen?*

**Belegregel für dieses Dokument:** Jede Aussage hier ist am Repo
nachprüfbar — durch einen Commit-Hash, eine Datei oder ein Lauf-Protokoll.
Der Beleg steht jeweils dabei. Was sich nicht belegen lässt, steht als
*ungeprüft* markiert und nicht als Tatsache.

**Und eine zweite Regel, aus Schaden klug:** Zahlen, die sich von selbst
ändern — Lauf-Zähler, Deployment-Zähler, Kurs-Stände, der Kopf-Commit —
stehen hier NICHT wörtlich, sondern als Verweis auf ihre Quelle. Ein
abgeschriebener Zähler ist am Tag nach dem Schreiben falsch, und ein
Dokument mit falschen Zahlen wird nicht mehr gelesen.

**Und eine dritte, inzwischen mit einem echten Gegenmittel (siehe §8,
Lesson 11):** Dieses Dokument brauchte bisher immer einen Anlass zum
Nachziehen, nie einen eigenen Automatismus — und stand deshalb zweimal
unbemerkt zu lange still: 16.08.–11.09.2026 (drei Wochen, zehn PRs, ein
echter Betriebsvorfall) und erneut 11.09.–27.09.2026 (16 Tage, sieben
PRs, #51–#57). **Diese dritte Lücke (27.09.–05.10.2026, 8 Tage, sieben
PRs, #59–#65) ist die erste, die NICHT erst durch einen zufälligen
Auftrag auffiel:** der in genau dieser Lücke selbst gebaute Doku-Wächter
(PR #59, `SCHWELLE_PRS = 4`) hat sie am 05.10.2026 real erkannt und
lautlos gemeldet (Actions-Run `37339845773`, Job-Log „Waechter: Push
(lautlos) verschickt.") — und genau dieser Push ist der Anlass für diese
Nachziehung. Lesson 11 ist damit nicht mehr nur beschrieben, sondern
einmal real bestätigt wirksam.

---

## 1. Betriebszustand (11.09.2026; Lauf-, Ranking-, Top-5-, Ampel-, Konfluenz- und PR-Zeilen auf 31.10.2026 nachgezogen)

| Sache | Zustand | Beleg |
|---|---|---|
| GitHub Pages | **aktiv** seit 02.08., deployt bei jedem Push auf `main` | Workflow `pages-build-deployment`, angelegt 02.08.2026 16:11 — Zähler und letzter Lauf in Actions |
| Momentum-Lauf | läuft werktäglich, **vier Fehlschläge insgesamt**, alle fail-soft (nichts veröffentlicht, nichts eingefroren) | Run 1 (02.08.2026, Datumsformat-Bruch iShares, §8 Lesson 3) — **kein** „Lauf 1"-Commit, Zählung beginnt bei „Lauf 2" (`07cbedd`). Lauf 71 (01.10.2026, 00:49 UTC, Yahoo-Rate-Limit auf `^SP500TR`, Actions-Run `36798080643`), noch am selben Tag per manuellem Dispatch nachgeholt (Lauf 72, Actions-Run `36927209332`), siehe §4 Punkt 5. Lauf 94 und Lauf 95 (31.10.2026, Actions-Runs `41153318736`/`41183266440`, „kein Titel mit vollstaendiger Historie"), per manuellem Lauf 96 nachgeholt (Actions-Run `41187870579`, Commit `8e29c5d`), siehe §4 Punkt 16. Sonst durchgehend grün. |
| Ranking | eingefroren zum **30.10.2026** (vierter scharfer Stichtag), beide Märkte — Juli-/August-/September-Stand bleiben parallel als eigene, nie überschriebene Dateien stehen; geschrieben von Lauf 96 (manueller Nachlauf, siehe Zeile oben), nicht vom planmäßigen Lauf | `data/rankings/us_2026-10.json`, `de_2026-10.json` (und weiterhin `*_2026-09.json`, `*_2026-08.json`, `*_2026-07.json`) |
| Score-Gewichte | **je Markt und Ranking-Monat** (Fahrplan, seit 01.11.2026 im Code): US bis 2026-10 50/50, **ab 2026-11 100/0**; DE immer 50/50. Alle eingefrorenen Rankings Juli–Oktober tragen 0.5/0.5. Erstes echtes 100/0-Ranking: US-Stichtag 30.11.2026 (**noch nicht eingetreten**) | `config.py` (`gewichts_fahrplan`), `data/rankings/*.json` → `methode`, §7.6 |
| US-Top-5 (Okt.) | TRGP, APA, XOM, VTRS, DVN — 496 von 503 im Universum bewertet; **4 von 5 im Sektor Energy** (Sektor-Hinweis aus PR #72 erscheint auf der Seite) | `us_2026-10.json` → `top`, `abdeckung`; Kursvergleich `ok` (SXR8, 492 verglichen, 0 über Toleranz); Hinweis in `docs/index.html` (`sektor-hinweis`) |
| DE-Top-5 (Okt.) | DHL.DE, EVK.DE, BAYN.DE, DB1.DE, DHER.DE — 81 von 102 im Universum bewertet (21 am Handelbarkeits-Filter) | `de_2026-10.json` → `top`, `abdeckung`; Kursvergleich `ok` (100 verglichen, 0 über Toleranz) |
| Überschuss-Ampel | weiterhin live, keine Warnung in beiden Märkten | US: Rendite +12,11 %, Geldmarkt (`^IRX`) **+3,69 %**, Überschuss **+8,41 %**. DE: Rendite +7,76 %, Geldmarkt (€STR/EZB) **+2,06 %**, Überschuss **+5,70 %**. Beide `trend_ampel` in den Oktober-Rankings |
| Universen | **beide VERIFIED**, Stand 03.08.2026 (seither nicht neu gezogen) | `universe/universe_us.txt`, `universe_de.txt` (Kopfzeile `# STATUS: VERIFIED`) |
| Beschreibende Angaben | vorhanden (Name + Sektor je Ticker) | `universe/ticker_meta_us.json`, `ticker_meta_de.json` |
| Konfluenz — Export | `docs/data/top5.json`, schreibt sich bei jedem neuen Ranking neu | `run.py::_schreibe_top5`, seit `e695b54` (Lauf 9) |
| Konfluenz — Push/Stand | **live**; erster echter Treffer war `de:TKA.DE`; Stand 31.10.2026: `de:DHL.DE`, `de:EVK.DE` | PR #46 (`62257b4`); `data/konfluenz_stand.json` — der erste Produktionslauf, der die Mechanik überhaupt scharf prüfte, war Lauf 54 (07.09., nach PR #46/#47/#48). Ob der Stand schon auf die Oktober-Top-5 reagiert hat, ist **ungeprüft** (hängt an der Elliott-Seite) |
| Konfluenz — Historie | wächst automatisch; die zwei manuell rekonstruierten Juli-Einträge (TKA.DE, SIE.DE — Elliott-Seite nicht belegbar) stehen weiterhin drin, alle übrigen sind `"automatisch"` (Stichtage 31.08. und 30.09.); Anzahl bewusst nicht abgeschrieben | PR #47 (`ba99293`), PR #48 (`c9e5688`); `data/konfluenz_historie.json` — jeder Eintrag trägt `quelle`: `"automatisch"` oder `"manuell_rekonstruiert"`. Einige Ticker stehen je Stichtag doppelt (z. B. TKA.DE 31.08., DHL.DE 30.09.) — ob das gewollt ist (mehrere Elliott-Treffer) oder ein Doppel-Eintrag, ist **ungeprüft** |
| Reparatur-Agent (Stufe 3) | **erste, bewusst schmale Ausbaustufe gebaut** — nur Datumsformat-Drift bei den drei DE-iShares-Bestandslisten; noch nie ausgelöst (kein passender Fund seit Einführung) | PR #49 (`a2343cc`); `tools/agent_datumsformat.py`, `tools/agent_datumsformat_oeffnen.py`, zweiter Job in `vertrag.yml` |
| ntfy-Push | verdrahtet, **zwei Push-Arten inzwischen live bewiesen**: Ranking-Push (Probe 08.08.) und Konfluenz-Push (siehe Zeile oben) | Lauf 19 (Probe); `konfluenz_stand.json`/`konfluenz_historie.json` als Nebenbeweis für den Konfluenz-Push (Zustellung selbst nicht am Gerät nachgeprüft, nur die serverseitige Wirkung) |
| Kurse | Stand je Markt in `kurse_vom` | `data/status.json` |
| Tests | vollständig grün (unit + design/Playwright) | `pytest` (Zähler bewusst nicht abgeschrieben — er wächst mit jedem PR) |
| Offene PRs | **keine** außer diesem Doku-PR (#82) | `gh api repos/easywebb911/Momentum-Report/pulls?state=open`, geprüft 31.10.2026 |

*Hinweis zu dieser Tabelle:* Am 31.10.2026 nachgezogen wurden die Zeilen
Momentum-Lauf, Ranking, US-/DE-Top-5, Überschuss-Ampel, Konfluenz und
Offene PRs — ausgelöst durch den Oktober-Stichtag (§4 Punkt 16). Die
übrigen Zeilen (Universen, Reparatur-Agent, ntfy, Kurse, Tests) bleiben
auf ihrem früheren Stand — kein Anlass gefunden, sie erneut zu prüfen.

**Cron-Fahrplan** (`.github/workflows/`):

| Workflow | Auslöser | Datei |
|---|---|---|
| Momentum-Lauf | `45 21 * * 1-5` (werktags 21:45 UTC) + manuell | `lauf.yml` — ein manueller Dispatch am letzten Werktag des Monats vor Marktschluss hält das Einfrieren für den betroffenen Markt seit PR #53 still zurück (siehe §4 Punkt 2, §7.2) |
| Datenquelle prüfen | `15 6 * * 1` (montags 06:15 UTC) + manuell | `datenquelle.yml` |
| Vertragstest | `0 8 25-31 * *` + Wochentag-Riegel im Job + manuell | `vertrag.yml` — Job `vertrag` schweigt im Normalfall, ein Push mit allen Brüchen; seit PR #49 ein zweiter Job `agent-datumsformat` im selben Run (eigene, sonst nirgends vergebene Schreib-/PR-Rechte, siehe §2 #49) |
| Wächter (Totmannschalter) | `30 7 * * 1` (montags 07:30 UTC) + manuell | `waechter.yml` — schweigt im Normalfall, Alarm-Push + roter Lauf ab > 4 Tagen Stille |
| Universum aktualisieren | **nur manuell** | `universum.yml` |
| Tests | jeder Push und jeder PR | `tests.yml` |
| Agenten-Kontrolle | **in Actions abgeschaltet seit 31.10.2026** (Status `disabled_manually`) | `agenten_kontrolle.yml` — Code und Datei bleiben unverändert im Repo; Grund und Rückweg siehe §4 Punkt 15 |

Diese Tabelle nennt nur die Kern-Workflows. Weitere Wächter mit eigenem
Fahrplan in der jeweiligen Datei (Stand 31.10.2026 alle aktiv, per `gh
api .../actions/workflows` geprüft): `handover_waechter.yml`,
`pr_verwaisung_waechter.yml`, `lauf_zeitversatz_waechter.yml`,
`push_zustellung_waechter.yml`, `datenabdeckung_waechter.yml`,
`wiedervorlagen_waechter.yml`, `schutz_sperre.yml`, `ntfy_relay.yml`
(Letzterer seit der Umstellung vom 31.10. ohne Aufrufer, bleibt als
Werkzeug stehen).

Am Wochenende läuft nichts. Ist der letzte Lauf von Freitag, ist das
kein Ausfall, sondern der Fahrplan.

---

## 2. Gemergte Arbeit (#1–#21, #40–#65 vollständig)

**Kontext #51–#57 (nicht wiederholt, nur einmal hier vermerkt):** Easy
ließ Mitte September einen externen Qualitäts-Check auf Repo und
Methodik-Seite laufen. Dessen Befunde sind der Auslöser für #51 (Kurs-
vergleich-Entkopplung), #52 (Zweitquellen-Doku), #54 (Kopfzeile),
#56/#57 (Formulierungsschärfungen) und mittelbar für #55 (Benchmark-
Vergleich, Top-5-Prozentzahl ohne Maßstab). #53 hat einen eigenen,
unabhängigen Auslöser (Lauf 48, siehe §4 Punkt 2). Der volle Bericht
lebt außerhalb dieses Repos und wird hier nicht reproduziert — jeder
einzelne Befund steht stattdessen konkret im jeweiligen PR-Text.

**Kontext #58–#65 (nicht wiederholt, nur einmal hier vermerkt):** #58
selbst ist die vorletzte Handover-Pflege (Stand nach #57). #59–#61 sind
drei neue bzw. reparierte Wächter nach demselben Prinzip wie der
Totmannschalter (`waechter.py`), angewandt auf zwei neue Symptome:
Doku-Rückstand (#59) und PR-Verwaisung (#60, mit einem realen
GraphQL-Fix in #61). #62–#64 sind die vollständige Diagnose- und
Reparaturkette eines einzigen realen Vorfalls — iShares-Totalausfall
seit 25.09., siehe §4 Punkt 6: Wegwerf-Verifikation der Ersatz-URLs
(#62), der eigentliche URL-Fix (#63), und die Härtung gegen ein dabei
aufgetretenes ntfy-Längenproblem (#64). #65 sind zwei weitere,
unabhängige Wächter (Push-Zustellung per Log-Scan, Lauf-Zeitversatz-
Beobachtung).

**Kontext #66–#70 (nicht wiederholt, nur einmal hier vermerkt):** #66
ist die vorletzte Handover-Pflege (Stand nach #65). #67 ist der längst
überfällige Rückbau von `probe_ishares_neu.yml` (#62) — schließt den in
§5/§10 selbst gemeldeten Hygiene-Rückstand. #68–#69 sind eine
abgeschlossene Erkundung nach demselben Wegwerf-Muster wie #62/#67:
#68 berechnet die Information Discreteness (Da/Gurun/Warachka 2014)
für beide Universen rein zur Diagnose (nur Job-Log, kein Einfluss auf
Score/Ranking), #69 baut sie nach Auswertung der Befunde wieder zurück
(siehe §4 Punkt 7). #70 ist der eigentliche Produktionscode aus dieser
Serie — der Split-Wächter, ausgelöst durch den real aufgetretenen
MNST-Vorfall (siehe §4 Punkt 9).

Alle Merge-Commits liegen auf `main`. Die Merge-Klasse steht ab #14 im
PR-Titel; davor wurde sie je Auftrag im Chat vereinbart und ist im Repo
nicht dokumentiert (bei #1–#3 deshalb „—"). **#22–#39 sind nicht erneut
tabelliert** — sie liegen zeitlich zwischen der letzten Handover-Pflege
(#21, 09.08.) und dieser Nachziehung und sind bereits an anderer Stelle
in diesem Dokument mit Inhalt belegt: #28/#31/#34/#35 in §6 (Herleitung
der Stufe-2b-Werte), #36/#37/#38 ebenda und in §7.7, #40 unten. Wer die
volle Liste braucht: `git log --oneline --merges main`.

| PR | Merge-Commit | Datum | Was | Klasse |
|---|---|---|---|---|
| #1 | `63f30f9` | 02.08. | v0: Kern, Anzeige, Läufe, Nachweise | — |
| #2 | `86669f7` | 02.08. | DE-Universum aus iShares-Bestandslisten statt Wikipedia | — |
| #3 | `1c6116d` | 02.08. | Push-Schleife: Regelverstoß nicht fünfmal wiederholen | — |
| #4 | `3e2481c` | 02.08. | Anzahl-Gatter statt Fondsname; echtes iShares-CSV-Format | MANUAL |
| #5 | `a648c16` | 02.08. | Kopf-Banner in `docs/index.html` | SELF |
| #6 | `9a9a90a` | 02.08. | Rückweg auf Unterseiten, „Neu laden", „Neu berechnen" | MANUAL |
| #7 | `7ea1209` | 02.08. | Banner direkt unter die Überschrift | SELF |
| #8 | `f10dad9` | 02.08. | Score 50/50 statt 70/30, Teil-Ränge sichtbar | MANUAL |
| #9 | `98d0b13` | 02.08. | ntfy: Thema prüfen statt blind senden | SELF |
| #10 | `557f469` | 02.08. | Ehrlichkeits-Block zieht in die Methodik | SELF |
| #11 | `85035d5` | 03.08. | Trend-Tacho in der Trend-Box | SELF |
| #12 | `166b49a` | 03.08. | Karten: Chart-Verweis, Beschreibung, Live-Kurs | MANUAL |
| #13 | `383544c` | 03.08. | Verdrahtungsprobe: Eingabefeld `testpush` | SELF |
| #14 | `d0925b5` | 03.08. | Konfluenz-Sicht: zwei Blickwinkel, nichts verrechnet | MANUAL |
| #15 | `6fe3a40` | 03.08. | Konfluenz: Elliott-Score aus `score_heuristic` | SELF |
| #16 | `22cc559` | 05.08. | Trend-Kriterium: Überschuss statt Preisrendite | MANUAL |
| #17 | `5058831` | 08.08. | Handover angelegt, README entstaubt | SELF |
| #18 | `c7a8bf7` | 08.08. | Handover: ntfy-Push belegt angekommen | SELF |
| #19 | `b7abc81` | 09.08. | Wegwerf-Probe: Zins-Pfad und Korrekturweg | MANUAL |
| #20 | `42f5653` | 09.08. | Rückbau der Wegwerf-Probe | SELF |
| #21 | `645401e` | 09.08. | CI-Hygiene: Pins, beide Seiten geprüft, Zeit-Deckel | SELF |
| #40 | `21a8e7f`→`6c15c59` | 16./17.08. | Browser-Testkontext: echtes Default-Deny (Allowlist) statt Blockliste für externe Hosts | SELF |
| #41 | `163ab35` | 18.08. | Karte zeigt zusätzlich den eingefrorenen Stichtag-Kurs (mit Datum, `--disc`-Satz) | SELF |
| #42 | `784a9df` | 21.08. | Karte: Rang-Erklärsatz entfernt, Betrag im Stichtag-Hinweis fett | SELF |
| #43 | `9d6d93e`→`629849a` | 21./22.08. | Karten: dezente Markt-Tönung US/DE, Kontrast auf 16 % Deckkraft justiert (WCAG-Rechnung im PR-Text, siehe §7.7) | SELF |
| #44 | `1255da3`→`dc87e5a` | 30.08. | Neue Seite „Evaluation" — Monats-/Gesamtrückblick, Farbbalken, Pflicht-Hinweistext gegen Fehldeutung als Erfolgsnachweis | MANUAL |
| #45 | `d5e7055`→`8035cd2` | 02.09. | Neu berechnen: Sekundenanzeige vom Poll-Takt entkoppelt (eigener Ticker) | SELF |
| #46 | `ab366e5`→`62257b4` | 05.09. | Konfluenz-Push bei neuem Treffer — serverseitige Persistenz (`konfluenz_stand.json`), Python-Spiegel der Browser-Logik | MANUAL |
| #47 | `353f7b9`→`ba99293` | 06.09. | Konfluenz-Historie-Sektion — alle je gesehenen Treffer, unterhalb der Top-5-Listen | MANUAL |
| #48 | `1f1bd47`→`c9e5688` | 07.09. | Zwei rekonstruierte, klar gekennzeichnete Konfluenz-Nachträge (TKA.DE, SIE.DE) + neues Schema-Feld `quelle` | MANUAL |
| #49 | `0f2702b`→`a2343cc` | 08.09. | Reparatur-Agent Stufe 3, erste Ausbaustufe — schmal auf Datumsformat-Drift bei iShares begrenzt | MANUAL |
| #50 | `f24b868`→`932f73f` | 11.09. | SESSION_HANDOVER.md auf Stand nach PR #49 gebracht | SELF |
| #51 | `610c033`→`2b648c3` | 11.09. | `series_roh`/Adj-Close-Kopplung entkoppelt — score-unabhängiger DE-Kursvergleichspfad härtend, Kausalität zum 31.08.-Vorfall weiterhin unbewiesen | SELF |
| #52 | `cdf1d87`→`37cfcb2` | 11./12.09. | Kursvergleichs-Zweitquellen (Stufe 2a/2b) auf der Methodik-Seite ergänzt — schließt die in §4 Punkt 5/§7.5 selbst gemeldete Doku-Lücke | SELF |
| #53 | `819e155`→`62223af` | 17.09. | Zu früh ausgelösten Lauf gegen untertägigen Monats-Stichtag gehärtet (realer Anlass: Lauf 48, 31.08., DE-Kurs untertägig eingefroren) | MANUAL |
| #54 | `87a313c`→`72d301e` | 17.09. | Kopfzeile zeigt beide Stichtage, wenn US/DE tatsächlich abweichen (statt eines gemeinsamen `max()`-Datums) | SELF |
| #55 | `4f7c96d`→`4c822dd` | 17.09. | Index-Benchmark-Vergleich auf der Evaluation-Seite (additives Schema 1→2, Juli-Eintrag bewusst nicht rückwirkend ergänzt) | MANUAL |
| #56 | `cddef36`→`9538477` | 17.09. | Handelbarkeits-Filter-Text auf der Methodik-Seite präzisiert (Rangwirkung statt pauschalem „kein Signal") | SELF |
| #57 | `fda07b0`→`4782de8` | 17.09. | Drei weitere Formulierungsschärfungen auf der Methodik-Seite (Tie-Breaking, Methoden-Anspruch, bereinigte Kurse beim 52W-Hoch) | SELF |
| #58 | `f6e0a72`→`60a58b9` | 27.09. | SESSION_HANDOVER.md auf Stand nach PR #57 gebracht (#51–#57 nachgezogen) | SELF |
| #59 | `d9853d4`→`068b8e8` | 27.09. | Doku-Wächter für SESSION_HANDOVER.md gegen den PR-Rückstand (`SCHWELLE_PRS = 4`) | MANUAL |
| #60 | `78bbb03`→`f9570df` | 27.09. | Drei read-only Sicherheits-Checks: PR-Verwaisungs-Wächter (neu gebaut), Workflow-Timeout-Abdeckung (keine Lücke gefunden), Requirements-Vollständigkeit (keine Lücke gefunden) | MANUAL |
| #61 | `92433bf`→`689d7a7` | 29.09. | PR-Verwaisungs-Wächter: realer GraphQL-Node-Limit-Fehlschlag behoben (zweistufiger Abruf statt einer Sammel-Abfrage) | MANUAL |
| #62 | `c0d84ac`/`66d3c1c`→`a5c363c` | 02.10. | Wegwerf-Workflow `probe_ishares_neu.yml` zur Verifikation der neuen BlackRock-URLs — zurückgebaut durch #67 (06.10., siehe §5) | MANUAL¹ |
| #63 | `155b47a`→`ea27893` | 02.10. | iShares-Download auf neuen BlackRock-Endpunkt umgestellt (ishares.com seit 25.09. tot), `asOfDate` bewusst weggelassen | MANUAL¹ |
| #64 | `f53594c`→`170f03e` | 03.10. | ntfy-Nachrichtenkürzung (`begrenze_bloecke()`, 2.000-Zeichen-Grenze) gegen HTTP 500/50001 bei vielen gleichzeitig gebrochenen Verträgen | ¹ |
| #65 | `70f45d2`→`2c6c0e0` | 04./05.10. | Zwei neue Wächter: ntfy-Zustellung per Log-Scan (`gh api`/`gh run view --log`, bewusst keine Datei-Persistenz) + Lauf-Zeitversatz-Beobachtung (> 4 Std. gegenüber nominellem Cron) | MANUAL¹ |
| #66 | `e7c7b70`→`34017e8` | 05.10. | SESSION_HANDOVER.md auf Stand nach PR #65 gebracht (#59–#65 nachgezogen) | SELF |
| #67 | `764b8b6`→`6ad14b5` | 06.10. | Rückbau des Wegwerf-Workflows `probe_ishares_neu.yml` (PR #62) — schließt Hygiene-Backlog Punkt 2 (siehe §5, §10) | SELF |
| #68 | `fbb6786`→`77d6f45` | 09.10. | Wegwerf-Probe `probe_id_diagnose.yml`/`tools/probe_id_diagnose.py`: Information Discreteness (Da/Gurun/Warachka 2014) für beide Universen vom Runner berechnet, nur Job-Log | MANUAL |
| #69 | `72f3636`→`e4cfdee` | 09.10. | Rückbau der ID-Probe aus #68, wie dort selbst angekündigt — nach Auswertung (siehe §4 Punkt 7) | SELF |
| #70 | `9419671`→`c56dc64` | 09.10. | Split-Wächter (`split_waechter.py`, nur Erkennen und Melden) — Auslöser: MNST-Vorfall US 2026-08, siehe §4 Punkt 9 | SELF |
| #71 | `a5a0fe8`→`5c646ef` | 09.10. | SESSION_HANDOVER.md auf Stand nach PR #70 gebracht (#66–#70 nachgezogen) | SELF |
| #72 | `6fc76f7`→`0f94675` | 13.10. | Sektor-Konzentrations-Hinweis (reine Anzeige, je Markt getrennt, Schwelle 3 von 5) — siehe §4 Punkt 11 | SELF |
| #73 | `5e932e3`→`4000b68` | 19.10. | Stichtag-Schutz vergleicht vollen Zeitpunkt statt nur Uhrzeit (Fund: Mitternachts-Rutsch am Monatsende hielt den Stichtag fälschlich für "zu früh") — siehe §4 Punkt 13 | MANUAL |
| #80 | `2ef3679`→`569e385` | 31.10. | Abbruchmeldung "kein Titel mit vollstaendiger Historie" nennt jetzt Zahlen je Ausscheidegrund — siehe §4 Punkt 16 | MANUAL |
| #81 | `95596a9`→`0972fe7` | 31.10. | Evaluation-Seite: Gesamtrückblick vor Monatsrückblick (reine Anzeige, Blöcke vertauscht) | SELF |
| #82 | `1525888`/`ab3f10e`→`4c2a655` | 31.10. | SESSION_HANDOVER.md auf Stand 31.10. nachmittags: Oktober-Stichtag ausgewertet, Wiedervorlagen 30./31.10. geschlossen, Umstellung der geplanten Tasks und Abschaltung der Agenten-Kontrolle dokumentiert | SELF |
| #83 | `43d3115`/`3b20111`/`6f4f5fc`→`f5a21b3` | 01.11. | **Score-Gewichte je Markt als Fahrplan nach Ranking-Monat** (PR 1 von 3): US ab 2026-11 100/0, bis 2026-10 50/50; DE immer 50/50. Auswahl rein nach Stichtag-Monat, keine Anzeige-/Textänderung. Neue Tests `tests/unit/test_gewichts_fahrplan.py` (DE-Hash byte-genau wie vor dem Umbau, US-Grenze Okt/Nov, Nachholung, Determinismus). Nachtrag im selben PR: Fahrplan-Hilfen in `GESCHUETZTE_SYMBOLE` aufgenommen (§5 Punkt 3, §7.8). Schutz-Sperre erwartet ROT — siehe §4 Punkt 8, §7.6 | MANUAL |
| #84 | `ff0190d`→`022c8ff` | 01.11. | **PR 2 von 3: Methodenwechsel US auf Methodik-Seite und Karten sichtbar** — Methodik erzeugt die Gewichte je Markt aus dem Fahrplan (beide US-Regeln mit Monat, DE getrennt), Score-Karte mit Begründung (Hou/Xue/Zhang tragend, Barroso/Wang, IMC samt Gegenzahl; DE: Burghof/Prothmann, Vorbehalt Franz/Regele); fünf neue Einträge in `sources.py`; Karte liest `ranking["methode"]` und zeigt bei 52W-Gewicht 0 „nur Info, zählt nicht im Score"; README nachgezogen. Keine Rechenänderung, Schutz-Sperre GRÜN erwartet. Neue Tests `tests/unit/test_methodik_gewichte.py`, 390-px-Test für den Hinweis | MANUAL |
| #85 | `7ceee80`/`18bd7bc`→`d457924` | 01.11. | **PR 3 von 3: Evaluation-Seite zeigt den Methodenwechsel, zählt verschiedene Regeln nie zusammen** — `render_evaluation()` gruppiert den Gesamtrückblick je Markt nach den tatsächlichen Gewichten des zugehörigen Rankings (`methode.gewicht_*`, aus `data/rankings/*.json` gelesen, NICHT aus `config.py` — Zuordnung Evaluation→Ranking ist code-belegt: `ausgewerteter_monat` == `ranking_monat`, gleicher Dateiname). Kennt ein Markt nur eine Regel (heute überall so): Anzeige byte-genau wie vorher (echte `docs/evaluation.html`-Hashes vor/nach identisch, siehe PR-Text). Fehlt die Ranking-Datei/das Feld: fail-soft "Regel unbekannt", nie mit einer bekannten Gruppe zusammengezählt. Monatsrückblick/Details je Monat tragen bei mehreren Regeln eine Kennzeichnung, der erste Monat je neuer Regel einen "Methodenwechsel"-Hinweis. Kein neues Feld in `data/evaluation/*.json`, keine Änderung an `config.py`/`ranking.py`/`scoring.py`/`evaluation.py`-Rechnung/Workflows. Schutz-Sperre GRÜN (lokal geprüft). Neue Tests in `tests/unit/test_render.py` (Methodenwechsel-Gruppierung, Summen-Erhalt, Fail-soft, Byte-Identität bei einer Regel), 390-px-Fixture (`tests/design/conftest.py`) um einen zweiten Block erweitert | MANUAL |
| #86 | `82549b0`/`251a107`→`5f6ccd8` | 01.11. | **Beleg-Zähler in `data.py`, keine Verhaltensänderung:** zählt von den wegen nicht-endlichem Adj Close verworfenen Zeilen, wie viele einen gültigen Rohkurs (Close) trugen und wie viele nicht, und je Tag die Anzahl (jüngste 3 Tage). Additiv in `status.json` → `daten` (`zeilen_verworfen_mit_rohkurs`, `zeilen_verworfen_ohne_rohkurs`, `verworfen_je_tag_juengste`) plus eine Job-Log-Zeile `[daten] …` je Abruf mit verworfenen Zeilen (Index und Titel getrennt). Welche Zeilen verworfen werden, bleibt unverändert; Rankings/Kurse/Seiten mit denselben Eingaben byte-gleich. Schutz-Sperre GRÜN. Tests `tests/unit/test_beleg_zaehler.py`. Zweck: Annahme hinter V3 belegen (§4 Punkt 16) | MANUAL |
| #87 | `f578137`/`5a4f7f4`/`e6da726`/`53521d4`/`e716d09`/`ecfed34`→`f03c753` | 03.11., gemergt 06.11. | **Workflow-Hygiene:** Dispatch-Eingaben von `lauf.yml` (datum, ohne_push, testpush, ohne_kursvergleich) und `universum.yml` (markt) nur noch über `env:`, `datum` streng geprüft; `vertrag.yml` nutzt `$GITHUB_EVENT_NAME` statt `${{ github.event_name }}`; `actions/checkout@v4→v5`, `actions/setup-python@v5→v6` überall (Node 24). Keine Cron-, Rechte- oder Job-Änderung. Neuer Test `tests/unit/test_workflow_injektion.py` (statisch über alle Workflows + echte Ausführung mit bösartigem `datum`). Schließt §4 Punkt 14c, §5 Punkt 1 zum größten Teil. Dazu Handover-Aufräumen (§3/§4/§6/§10). Schutz-Sperre erwartet ROT (Workflow-Ordner) | MANUAL |
| #88 | `46d7add`→`8cad8e0` | 09.11. | SESSION_HANDOVER.md: Wiedervorlage Lit-Check 08.11. erledigt (alle drei Aufgaben auf dem direkten ntfy-Weg belegt); Lit-Check-Fund „Momentum-Wendepunkte“ (Goulding/Harvey/Mazzoleni 2023) als §4 Punkt 17, Verdikt Easy: nicht bauen | SELF |
| #90 | `6075aa3` | 12.11. | **Daten-Abdeckungs-Wächter, Prüfung A:** zählt jetzt die letzten 2 Lauf-Stände je Markt (Commit-Reihenfolge, unabhängig vom Abstand) statt 2 Läufen in 24 Std. — vorher strukturell nie auswertbar. `FENSTER_STUNDEN_KURSABRUF` entfernt, Schwellen und Prüfung B unverändert. Nachspiel 18 echter Wächter-Läufe 26.10.–12.11.: 0 Meldungen. Neue Tests `tests/unit/test_datenabdeckung_regel_a.py` (echte Lauf-Stände). Schutz-Sperre GRÜN | MANUAL |

Bei PRs mit zwei Hashes ist der erste der Inhalts-Commit (der, den ein
`git revert` tatsächlich braucht), der zweite der GitHub-Merge-Commit.
#40/#41/#42/#43/#44/#45/#50/#51/#52/#54/#56 tragen keinen eigenen „Merge
pull request"-Commit im linearen Verlauf (Squash bzw. Fast-Forward) — die
Inhalts-Hashes sind über `gh`/die PR-Ansicht verifiziert, nicht geraten.

¹ #62–#65 deklarieren — anders als #1–#61 — keine Merge-Klasse wörtlich
im PR-Text (geprüft per `gh api`); alle vier wurden von Easy persönlich
gemergt (`merged_by`), nicht nach dem Self-Merge-Kriterium. Klasse hier
aus der Art der Änderung abgeleitet (#62/#63/#65: neue/geänderte
Workflow-Datei bzw. neue externe Datenquelle, beides laut §7.4 zwingend
MANUAL; #64: reine Bug-Fix-Härtung ohne Logikänderung, laut §7.4
SELF-fähig, aber tatsächlich manuell gemergt) — nachträglich zugeordnet,
nicht im Originaltext vorgefunden. Rückwirkend nicht mehr korrigierbar
(PRs bereits gemergt), hier nur transparent gemacht.

---

## 3. Wiedervorlagen (mit Datum)

| Wann | Was | Warum |
|---|---|---|
| **laufend, montags** <!-- faellig: offen --> | `Datenquelle prüfen` läuft gegen Yahoo. | Schlägt sie fehl, ist die Kursquelle das Problem, nicht der Code. |
| **offen, keine Frist** <!-- faellig: offen --> | **Reparatur-Agent, weitere Ausbaustufen?** PR #49 deckt genau eine von sieben real aufgetretenen Fehlerklassen ab (Datumsformat-Drift bei iShares) — bewusst schmal, siehe §4 Punkt 3. Ob und welche Fehlerklasse als Nächstes drankommt, ist **Easys Entscheid**, keine automatische Fortsetzung. | Diagnose vor PR #49 (siehe Session-Historie) hat sechs weitere Fehlerklassen benannt, von denen die meisten Domänenurteil brauchen und deshalb nicht sicher automatisierbar sind. |
| **15.01.2027** <!-- faellig: 2027-01-15 --> | **Universum-Alter:** Universum ist dann 165 Tage alt; Warnung ab 31.01.2027 (180 Tage). Entscheidung Easy: neu bauen oder Warnung hinnehmen. | `UNIVERSUM_WARNSCHWELLE_TAGE` = 180 im Daten-Abdeckungs-Wächter; Universum-Stand 03.08.2026. |
| **30.11.2026** (Montag, US-Stichtag) <!-- faellig: 2026-11-30 --> | **PR #84 (Methodik/Karten) ist gemergt (`022c8ff`) — die Seite nennt den Wechsel bereits.** **Erster US-Stichtag mit 100/0 — Gewichte in `data/rankings/us_2026-11.json` prüfen:** `methode.gewicht_momentum_12_1` = 1.0, `methode.gewicht_high_52w` = 0.0, Score = 100 × `perzentil_momentum`; `de_2026-11.json` weiter 0.5/0.5. **Zusätzlich: ist PR #85 (Evaluation) bis dahin gemergt?** Sonst zählt der Gesamtrückblick November versehentlich mit den Juli-Oktober-Monaten zusammen. | Siehe §4 Punkt 8, §7.6 — die Mechanik ist per Test belegt (`tests/unit/test_gewichts_fahrplan.py`), im echten Lauf noch nicht. |
| **31.12.2026** (Donnerstag, US-Stichtag, zugleich Dezember-Lauf) <!-- faellig: 2026-12-31 --> | **Erster echter Test der Methodenwechsel-Anzeige auf der Evaluation-Seite** (PR #85) — der Dezember-Lauf erzeugt erstmals den Rückblick auf das November-Ranking (`ausgewerteter_monat` 2026-11, siehe evaluation.py: der Rückblick entsteht als Nebenprodukt des JEWEILS NÄCHSTEN Rankings). Prüfen: zeigt `docs/evaluation.html` für die USA jetzt zwei getrennte Gesamtrückblick-Blöcke ("Rankings Juli bis Oktober 2026 (50/50)" und "ab Ranking November 2026 (nur 12-1-Momentum)"), mit dem "Methodenwechsel"-Hinweis am November-Monat? Bleibt es bei einem einzigen Block oder fehlt der Hinweis: Fehler untersuchen, nicht nur hinnehmen. | Siehe §4 Punkt 8, §6 Punkt 0, PR #85 — bisher nur an synthetischen Daten geprüft, noch nie an einem echten Dezember-Lauf. |
| **01.12.2026, 09:30 UTC** <!-- faellig: 2026-12-01 --> | **Stichtagslauf November von Hand starten** (Actions → Momentum-Lauf → Run workflow) und danach den Stichtag **30.11.** in `data/rankings/us_2026-11.json` UND `de_2026-11.json` prüfen (`stichtag` = `2026-11-30`). Ist er falsch (z. B. 27.11.): Datei über den bekannten Korrekturweg (§10, „Korrekturweg + Determinismus live bewiesen") löschen und neu bauen. | Diagnose §4 Punkt 16: der planmäßige Lauf (≈ 01.12. 00–02 UTC) bricht sehr wahrscheinlich ab (Adj Close des 30.11. fehlt noch); DE-Daten erfahrungsgemäß erst ab ≈ 09:15 UTC vollständig. Restrisiko „stiller falscher Stichtag", wenn dem Index der 30.11. fehlt. |
| **ab 02.12.2026** <!-- faellig: 2026-12-02 --> | **ab 02.12.: V2 bauen (Entwurf siehe §4 Punkt 16)** (Stichtags-Vollständigkeitsprüfung) — MANUAL, Lauf-Pfad (`run.py:process_market`, neue Prüffunktion in `ranking.py` + `GESCHUETZTE_SYMBOLE`). Merge vor dem 31.12.2026 (DE-Feiertagsfall). | Entscheidung Easy, 01.11.2026. |
| **beim nächsten Abbruch** <!-- faellig: offen --> | **Beim nächsten Abbruch "kein Titel mit vollstaendiger Historie" die Zahlen-Meldung (PR #80) und die neuen Beleg-Zähler (`[daten]`-Zeile) auswerten.** | Ursache inzwischen per Diagnose belegt (§4 Punkt 16); die Meldung bestätigt sie im Einzelfall. |

**Aus der letzten Vorlage-Liste erledigt, jetzt in §10:** der 31.08.-Monats-
Stichtag selbst (samt Überschuss-Ampel-Realprobe), der erste Vergleich
zweier Monats-Ranglisten (01.09., Top-5-Wechsel real beobachtet), sowie
Hygiene-Backlog Punkt 1 (default-deny, #40). Ebenfalls erledigt: die
`series_roh`/`Adj Close`-Kopplung in `src/momentum/data.py` (#51, siehe
§4 Punkt 2) — die Kausalität zum 31.08.-Vorfall selbst bleibt dabei
unbewiesen, das war nie Teil dieser Wiedervorlage.

**Das 25.–30.09.2026-Vertragstest-Fenster selbst ist durchlaufen, aber
OHNE den erhofften Kalibrierungs-Nutzen:** alle fünf `vertrag.yml`-Läufe
in diesem Fenster (25./28./29./30.09., Actions-Runs `36138643530`,
`36448977860`, `36582489971`, `36728428301`) trafen auf einen bereits
toten iShares-Endpunkt (HTTP 404, siehe §4 Punkt 6) — der DE-
Kursvergleich blieb die ganze Woche „entfallen", keine einzige neue
Abweichungszahl. Die Wiedervorlage aus der letzten Pflege ist damit
NICHT erledigt, sondern auf das nächste Fenster verschoben (25.–31.10.,
Zeile oben).

**Das 25.–31.10.2026-Fenster hat geliefert und ist erledigt (jetzt in
§10):** fünf `vertrag.yml`-Läufe an den Werktagen 26.–30.10. (Actions-
Runs `40341359705`, `40514313168`, `40707762856`, `40894310972`,
`41073466086`), jeder mit Job-Log wörtlich „Alle 12 Vertraege halten.
Kein Push."; der DE-Kursvergleich verglich jeweils 102 bzw. 103 Titel,
größte Abweichung jedes Mal **0,00 %** (siehe §4 Punkt 1). Der 25.10.
(Sonntag) wurde vom Wochentag-Riegel korrekt übersprungen. Ebenfalls
erledigt: Split-Wächter- und Sektor-Hinweis-Beobachtung am
Oktober-Stichtag (§10).

---

## 4. Offene Punkte

**1. DE-Toleranz (`TOLERANZ = 0.010` in `kursvergleich.py`) — weiterhin
nicht neu kalibriert, jetzt aber mit echten, aber noch dünnen Messdaten.**
*(**geparkt** seit 03.11.2026 — Grund: sechs Messtage, alle 0,00 %; aus
lauter Nullen lässt sich keine engere Toleranz ableiten, und eine
engere ohne Streuungsdaten wäre eine Setzung. Wieder aufnehmen, sobald
ein Vertragsfenster echte Abweichungen > 0 zeigt.)*

Das erste reale Vertragstest-Fenster (25.–31.08.2026) liegt vor. Bild
uneinheitlich: am 28.08. lief der volle Vergleich sauber durch (102 von
102 Titeln, größte Abweichung 0,00 %, Verdikt `ok` — Actions-Run
`33205016377`); am 31.08. selbst waren **0 von 102 Titeln** vergleichbar
(„entfallen", kein Bruch — siehe Punkt 2 unten). Eine einzelne Woche mit
nur einem auffälligen Tag reicht nicht, um `TOLERANZ` gegen echte
Streuung statt gegen das gesetzte Bauchgefühl zu prüfen. Das vorgesehene
nächste Fenster (25.–30.09.2026) lieferte **keine** neue Zahl: alle fünf
iShares-Quellen waren die ganze Woche durch HTTP 404 tot (Actions-Runs
`36138643530`, `36448977860`, `36582489971`, `36728428301` — siehe §4
Punkt 6), der DE-Kursvergleich blieb durchgehend „entfallen". Nächste
reale Chance: 25.–31.10.2026, jetzt mit bereits gemergtem URL-Fix (§2
#63) — siehe §3. **Bis dahin weiterhin nichts ändern.**

**Nachtrag 31.10.2026 — das Oktober-Fenster hat geliefert:** an allen
fünf Werktagen 26.–30.10. lief der DE-Vergleich vollständig (102 bzw.
103 Titel verglichen, 0 ohne Vergleich), größte Abweichung **jedes Mal
0,00 %** (Job-Logs der Actions-Runs `40341359705` … `41073466086`, siehe
§3); dazu Lauf 96 am 31.10. mit 100 verglichenen Titeln, 0 über der
Toleranz. Zusammen mit dem 28.08. liegen damit sechs saubere Messtage
vor, alle bei 0,00 % — die Toleranz von 1,0 % wurde nie auch nur
annähernd berührt. **Einordnung:** das spricht dagegen, dass die
Toleranz zu eng ist; ob sie zu weit ist (echte Abweichungen von 0,1–
0,9 % würden nicht auffallen), lässt sich aus lauter Nullen nicht
ablesen. **Weiterhin nichts ändern**, kein Anlass. *Ungeprüft:* warum an
zwei Tagen 103 statt 102 Titel verglichen wurden (Universum: 102).

**2. Vertragstest-Vorfall 31.08.2026 — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: Punkt selbst „dokumentiert, nichts zu tun“; Befund A durch PR #51 behoben (`2b648c3`); Befund B ist dauerhaft unbeweisbar, keine Handlung möglich.

**3. Reparatur-Agent Stufe 3 — erste Ausbaustufe gebaut, keine
automatische Fortsetzung.** *(**geparkt** seit 03.11.2026 — Grund: die
übrigen sechs Fehlerklassen brauchen Domänenurteil und sind nicht sicher
automatisierbar; seit 08.09. kein einziger Fund der gebauten Klasse.
Wieder aufnehmen nur auf Easys Entscheid, siehe §3.)*

PR #49 deckt ausschließlich Datumsformat-Drift bei den drei
DE-iShares-Bestandslisten ab — die einzige von sieben real aufgetretenen
Fehlerklassen, die laut vorheriger Diagnose mechanisch eng genug ist, um
ohne Domänenurteil sicher zu sein. Harte Grenzen (im Code erzwungen, per
AST-Test nachgemessen, nicht nur behauptet): nur additive Regex-Vorschläge
an `_datum_aus_text`, nie ein `gh pr merge`-Aufruf, jeder PR zitiert die
rohe Fehlzeile wörtlich, höchstens ein offener Agent-PR je Bestandsquelle.
Noch nie ausgelöst (kein passender Fund seit Einführung 08.09.).

**4. `^SP500TR`-Historientiefe im Ernstfall.** *(beobachten, unverändert offen)*

Extern verifiziert waren 251 Tageskurse über das Jahr — genug. Reicht die
Reihe an einem künftigen Stichtag nicht, greift der laute Abbruch
(`Keine Indexdaten … ohne Handelskalender kein Stichtag`), kein stiller
Rückfall. Träte das ein, wäre die Frage: Kursindex als Notnagel (nein) oder
Stichtag verschieben (ja).

**5. Yahoo-Rate-Limit-Vorfall 01.10.2026 (Lauf 71) — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: „nichts zu tun“; September-Stichtag per Lauf 72 geschrieben (Run `36927209332`, Commit `6de1fae`); Ursache in der Diagnose 01.11. erneut bestätigt (`YFRateLimitError`, Run `36798080643`).

**6. iShares-Totalausfall, zweite Welle (25.–30.09.2026) — untersucht,
behoben, Wirksamkeit noch nicht real geprüft.** *(siehe §3, Termin
25.–31.10.2026)*

Alle fünf iShares-Zweitquellen (DAX/EXS1, MDAX/EXS3, TecDAX/EXS2, SXR8,
IUSA) lieferten ab mindestens 25.09.2026 nur noch HTTP 404 von der alten
`ishares.com`-URL — bestätigt über vier unabhängige `vertrag.yml`-Läufe
(25./28./29./30.09., Actions-Runs `36138643530`, `36448977860`,
`36582489971`, `36728428301`, je „5 von 11 Vertraegen gebrochen") sowie
denselben Befund im Lauf-72-Job-Log (01.10., siehe Punkt 5 oben). Betraf
**ausschließlich den unabhängigen Kursvergleichs-Gatter** (Stufe 2a/2b,
§7.2) — das Ranking selbst (yfinance-basiert) lief beide Male unberührt
durch, siehe September-Top-5 in §1.

Zwei Reparaturen, beide bereits gemergt:
- **PR #63:** neuer BlackRock-Endpunkt (`component=holdings`) für alle
  fünf Quellen, einzeln vom Actions-Runner aus gegengeprüft (nicht nur
  von einer Quelle auf die anderen vier abgeleitet). `asOfDate` bewusst
  weggelassen (liefert ohne Parameter zuverlässig den aktuellen Stand,
  mit falschem Datum bleibt die Antwort HTTP 200, aber das Datumsfeld
  wird leer).
- **PR #64:** `notify.begrenze_bloecke()` (2.000-Zeichen-Grenze) gegen
  ein bei dieser Häufung aufgetretenes Nebenproblem — zwei der vier
  obigen Läufe (29./30.09., Job-IDs `109454006199`/`109931272494`)
  scheiterten zusätzlich daran, dass `push_vertrag_gebrochen()` mit
  allen fünf Bruch-Details auf ~4.856 Zeichen wuchs und von ntfy mit
  `HTTP 500 — internal server error (code 50001)` abgelehnt wurde —
  zeichengenau aus dem Job-Log rekonstruiert, rein zeitlich bedingt:
  beide Läufe fanden VOR dem Merge von PR #64 (03.10., `f53594c`) statt,
  sind also kein Rückfall nach der Härtung, sondern deren ursprünglicher
  Anlass.

**Offen, explizit terminiert:** `vertrag.yml` lief seit dem Merge beider
Fixes (02./03.10.) noch **kein einziges Mal** — der Workflow feuert nur
im Fenster 25.–31. eines Monats. Ob beide Fixes unter echten Bedingungen
halten, zeigt sich frühestens 25.–31.10.2026 (siehe §3).

**Nachtrag 31.10.2026 — PR #63 real bewiesen, PR #64 nicht gebraucht:**
alle fünf `vertrag.yml`-Läufe 26.–30.10. lasen die BlackRock-Endpunkte
erfolgreich („Alle 12 Vertraege halten. Kein Push.", Kursvergleich DE
und US vollständig) — der URL-Fix aus PR #63 hält unter echten
Bedingungen. PR #64 (Nachrichtenkürzung) wurde nicht gebraucht, weil
kein Vertrag brach; seine Wirkung unter echter Last bleibt **ungeprüft**
(nur durch Tests belegt).

**7. Lit-Check Frog-in-the-Pan / Information Discreteness — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: Entscheid „nicht in den Score, kein Bau geplant“; Probe zurückgebaut (PR #69, `e4cfdee`).

**8. Lit-Check 52-Wochen-Hoch bei Large Caps — entschieden 01.11.2026
(Easy): US 100/0 ab Ranking 2026-11, DE 50/50.** *(Rechnung: PR #83,
gemergt `f5a21b3`; Methodik/Karten: PR #84, gemergt `022c8ff`;
Evaluation: PR #85, gebaut, Merge bei Easy — damit inhaltlich
abgeschlossen, Frist zum echten Dezember-Test in §3)*

*Erweiterter Lit-Check 01.11.2026 — Prüfstand je Quelle (gilt für
`sources.py` und die Methodik-Seite):*
- **Hou/Xue/Zhang (2020), „Replicating Anomalies", The Review of
  Financial Studies 33(5), S. 2019–2133 — jetzt die TRAGENDE Quelle für
  US.** Messung mit NYSE-Grenzen, wertgewichtet (große Firmen bestimmen
  das Ergebnis), 1 Monat Haltedauer, Table 3, Spalte NYSE-VW: Zeile
  „52w1" 0,13 %/Monat (t = 0,38, nicht signifikant), Zeile „R 11 1"
  1,16 %/Monat (t = 3,99). *Am Original geprüft im Sparring-Chat
  01.11.2026, aus der Code-Umgebung nicht erreichbar* — Claude hat dort
  das PDF `https://global-q.org/uploads/1/2/2/6/122679606/houxuezhang2020rfs.pdf`
  geladen und den Text daraus gezogen: Kopfzeile „The Review of Financial
  Studies 33 (2020) 2019–2133", „v 33 n 5 2020"; Table 3, Spaltenkopf in
  der Reihenfolge NYSE-VW, NYSE-EW, All-VW, All-EW, …, jeweils Rendite
  und t-Wert; „R 11 1": 1.16 / 3.99 (PDF-S. 20); „52w1": 0.13 / 0.38
  (PDF-S. 21). Heft, Seiten und Messweise zusätzlich per Katalog
  (RePEc/IDEAS) aus der Code-Umgebung bestätigt.
- **Barroso/Wang** — Arbeitspapier, EFMA-Jahrestagung 2021 Leeds (nicht
  begutachtet), „This version: February 2021", Hauptstichprobe Juli 1972 –
  Dezember 2019; „fully subsumes 52-week high momentum unconditionally"
  (PDF-S. 5); „except for small caps, price momentum is a stronger anomaly
  than 52-week high" (PDF-S. 25). *Am Original geprüft im Sparring-Chat
  01.11.2026, aus der Code-Umgebung nicht erreichbar* (efmaefm.org und
  acfr.aut.ac.nz gesperrt). **Ungeprüft und deshalb NICHT auf der Seite:**
  die frühere Angabe „bedingt (nach ruhigen Marktphasen) wirkt das
  52-Wochen-Hoch eigenständig" — sie stand nicht in der Liste der im Chat
  am PDF gegengelesenen Stellen.
- **IMC, „Buy High, Sell Higher — Evaluating the 52-week high as a
  momentum signal"** (PDF vom 13.04.2026, 32 Seiten) — Studie eines
  Vermögensverwalters, nicht begutachtet, Eigeninteresse möglich.
  Haltedauer 6 Monate (PDF-S. 5). US Large Cap (Russell-1000-Nachbildung)
  **06/1988–12/2025: IR t12m1 0,20, Mischung comp_t12m1_rng52wk 0,24,
  reines 52W-Hoch 0,18** (PDF-S. 7). Anhang B **06/2006–12/2025: IR t12m1
  0,11, Mischung 0,07**, reines 52W-Hoch (range_52wk) Mehrertrag −0,27 %
  (PDF-S. 23). Für die IR-Unterschiede keine Zufallsprüfung. *Am Original
  geprüft im Sparring-Chat 01.11.2026, aus der Code-Umgebung nicht
  erreichbar.* **Korrektur gegenüber der Fassung vom 01.11. vormittags
  (unten im Abschnitt „Weitere Quellen"):** dort stand nur der
  Teilzeitraum („Mischung schwächer, 0,07 vs. 0,11") — über den
  Gesamtzeitraum ist die Mischung leicht BESSER (0,24 vs. 0,20). Beides
  steht jetzt auf der Methodik-Seite.
- **Burghof/Prothmann (2009)**, The International Journal of Business and
  Finance Research 3(2), S. 47–69 — alle in Deutschland gehandelten Aktien,
  1980–2008: 52-Wochen-Hoch sagt besser voraus als Momentum. Heft, Seiten,
  Zeitraum und Kernaussage per Katalog (RePEc/EconPapers) aus der
  Code-Umgebung bestätigt; Volltext nicht gelesen.
- **Franz/Regele (2016)**, Financial Markets and Portfolio Management
  30(2), S. 161–204, Zeitraum 1988–2015 — Momentum-Prämie nur im SDAX,
  nicht in DAX/MDAX. Per Springer/EconBiz aus der Code-Umgebung bestätigt;
  Volltext nicht gelesen.
- **Weitere Stützen, NUR hier im Handover, nicht auf der Seite:**
  Gupta/Locke/Scrimgeour (2010) und Liu/Liu/Ma (2011) — genannt in Easys
  Lit-Check; Inhalt hier **ungeprüft** (Liu/Liu/Ma laut Lit-Check:
  52W-Hoch in 18 von 20 Ländern, nach Kosten meist nicht signifikant).

*Widersprüche, offen benannt:* (1) Hou/Xue/Zhang 1,16 %/Monat ist ein
Durchschnitt über den ganzen Untersuchungszeitraum, die Ehrlichkeits-
Anzeige „Der Effekt ist geschrumpft" nennt für die USA nach 2000 rund
0,3 %/Monat — die Seite sagt das deshalb ausdrücklich dazu. (2) IMC
(Gesamtzeitraum) spricht leicht FÜR die Mischung — auf der Seite als
Gegenzahl genannt, nicht weggelassen.

*Vorgeschichte:* Bis 31.10. stand hier „Konvention gestützt, unverändert"
— Barroso/Wang (2021) war damals nur aus zweiter Hand bekannt.

*Jetzt im Original gelesen (Angabe Easy, Deep-Lit-Check 01.11.2026):*
Pedro Barroso, Haoxu Wang: „What explains price momentum and 52-week high
momentum when they really work?" — **Arbeitspapier** (nicht
begutachtet), EFMA-Fassung Februar 2021 (Prüfstand siehe oben). Kernaussagen: „except for small
caps, price momentum is a stronger anomaly than 52-week high"; Momentum
„fully subsumes 52-week high momentum unconditionally"; **bedingt** (nach
ruhigen Marktphasen) wirkt das 52-Wochen-Hoch eigenständig.

*Weitere Quellen desselben Lit-Checks (Fassung vom 01.11. vormittags),
jeweils mit ihrer Grenze:*
- **IMC, „Buy High, Sell Higher" (2026)** — Studie eines
  **Fondsanbieters** (Eigeninteresse möglich, nicht begutachtet): US Large
  Caps 2006–2025, die Mischung war schwächer als reines Momentum
  (Information Ratio — Mehrertrag je Einheit Abweichungsrisiko — 0,07 vs.
  0,11). **Unvollständig, korrigiert oben:** über 1988–2025 war die
  Mischung leicht besser (0,24 vs. 0,20).
- **Burghof/Prothmann (2009)** — Deutschland 1980–2008: das
  52-Wochen-Hoch **dominiert** Momentum.
- **Franz/Regele (2016)** — reines Momentum wirkte in Deutschland nur im
  SDAX, nicht in DAX/MDAX.
- **Liu/Liu/Ma (2011)** — 52-Wochen-Hoch-Effekt in 18 von 20 Ländern,
  **nach Handelskosten meist nicht signifikant**.
- **Byun/Jeon (2023)** — das 52-Wochen-Hoch dämpft Momentum-Crashs, vor
  allem auf der Short-Seite (Leerverkäufe) — für dieses long-only-
  Werkzeug (nur Kauf-Seite) kaum relevant.

*Gemeinsamer Einwand:* Die Belege FÜR das 52-Wochen-Hoch stützen sich
stark auf kleine Werte; das Universum hier (S&P 500, DAX/MDAX/TecDAX)
besteht überwiegend aus Large/Mid Caps.

*Entscheidung:* **USA** ab Ranking-Monat 2026-11 100 % Perzentil
12-1-Momentum, 0 % 52-Wochen-Hoch. **Deutschland** unverändert 50/50 —
ehrlich formuliert: **„nichts Besseres belegt"**, nicht „belegt
richtig"; die deutschen Arbeiten sprechen eher für das 52-Wochen-Hoch,
liefern aber ebenfalls kein Mischverhältnis. **Zwischenwerte (60/40
usw.) ausdrücklich verworfen** — das wäre Parametersuche. Eingefrorene
Rankings Juli–Oktober bleiben unverändert (50/50).

*Umsetzung (PR 1 von 3):* `config.Market.gewichts_fahrplan` +
`Market.gewichte_fuer(jahr, monat)`; `build_ranking` wählt rein nach dem
Monat des Stichtags (asof), nie nach dem Lauf-Datum — ein im November
nachgeholtes Oktober-Ranking rechnet 50/50. Die Ranking-Datei trägt die
tatsächlich verwendeten Gewichte in den vorhandenen Feldern
`methode.gewicht_*` (kein neues Feld, Schema-Zahl unverändert 2). Belegt
durch `tests/unit/test_gewichts_fahrplan.py`.

**9. MNST-Split-Vorfall (US 2026-08) — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: Split-Wächter gebaut (PR #70, `c56dc64`); am ersten echten Stichtag 30.10. stumm, kein Fehlalarm (§10, Run `41187870579`); August-Stand bleibt bewusst eingefroren. Dass er einen echten Split erkennt, ist weiter nur per Test belegt — kein offener Auftrag.

**10. AMCR, BNY, WBD — aus der ID-Diagnose offen geblieben, Ursache
ungeklärt.** *(beobachten, ungeklärt)*

Bei derselben Diagnose (Punkt 7 oben) fielen drei Titel auf, deren
Ursache nicht abschließend geklärt werden konnte:
- **AMCR:** ein Faktor von ca. 1,031 zwischen zwei unabhängig
  berechneten Größen, sowohl im Juli- als auch im August-Stand
  identisch — Ursache unbekannt, keine erkennbare Split-/Dividenden-
  Erklärung gefunden.
- **BNY:** 0,13 Prozentpunkte Differenz in der Momentum-Berechnung
  gegenüber einer unabhängigen Gegenrechnung — zu klein, um die Ursache
  aus der verfügbaren Diagnose sicher zu benennen.
- **WBD:** dünne Tageshistorie; `high_52w_ratio` steht im September-
  Stand exakt auf 1,0 (Titel genau am 52-Wochen-Hoch am Stichtag selbst)
  — rechnerisch plausibel bei wenigen verfügbaren Handelstagen, aber
  nicht weiter verifiziert.

Keine dieser drei Beobachtungen hat bisher ein Ranking sichtbar
verzerrt; alle drei bleiben als offene, unverifizierte Randnotizen
stehen, keine davon rechtfertigt für sich allein einen eigenen Auftrag.

**11. Sektor-Konzentration der Top-5 — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: Variante (b) gebaut (PR #72, `0f94675`), am 30.10. real sichtbar (§10); Variante (c) bleibt als Roadmap §6 Punkt 4 erhalten.

**12. Automatisierte SESSION_HANDOVER.md-Pflege per Workflow — geschlossen 03.11.2026, Volltext in §10 („Geschlossene Punkte aus §4“).** Beleg: Entscheid „kein Bau“; kein offener Auftrag.

**13. Scheduler-Drift bei `lauf.yml` — wachsend, Ursache für den
Stichtag-Schutz behoben (PR #73).** *(beobachten läuft weiter, Fix
gebaut)*

Read-only-Diagnose (19.10.2026, ausgelöst durch zwei Pushes des
Lauf-Zeitversatz-Wächters, 4,1 Std. am 12.10. und 5,0 Std. am 19.10.):
die Verspätung gegenüber dem nominellen Cron-Zeitpunkt (21:45 UTC)
**wächst** — Anfang September durchgehend 1,6–2,2 Std., seit Ende
September meist 3–5 Std. Von den letzten 37 ausgewerteten Läufen sind
**18 über Mitternacht UTC gerutscht** (vorher die Ausnahme, inzwischen
der Normalfall). Freitags im Schnitt 2,7 Std., Max 5,6 Std. — Ursache
vermutlich allgemeine Last bei geplanten GitHub-Actions-Läufen,
**nicht belegt**, nur vermutet.

Dabei gefunden: `zu_frueh_fuer_stichtag()` verglich nur die Uhrzeit,
nie das Datum — ein über Mitternacht gerutschter Lauf am tatsächlichen
Monatsende (z. B. nominell Fr 30.10.2026 21:45 UTC, Start Sa 31.10.
02:45 UTC) hielt den Monats-Stichtag deshalb fälschlich für "zu früh"
und verzögerte ihn still (nur Log/`status.json`) um bis zu ~3 Tage —
kein falsches Ranking, aber eine unbemerkte Verzögerung. **Behoben in
PR #73:** der Vergleich läuft jetzt gegen den vollen Zeitpunkt (Datum +
Uhrzeit) des tatsächlichen Handelstags statt nur gegen die Uhrzeit; der
PR-#53-Normalfall (Lauf 48, untertägiger Kurs am Handelstag selbst)
bleibt dabei unverändert geschützt.

**Cron-Zeit bleibt unverändert, bewusst:** 21:45 UTC ist nicht die
Ursache der Drift — GitHub wertet Zeitpläne ausschließlich in UTC aus,
unabhängig von Zeitzone oder Sommer-/Winterzeit. Eine frühere Zeit
würde die nach PR #53 bewusst konservative (Winter-)Marge nach
Börsenschluss verkleinern; eine spätere Zeit ändert an der Drift
nichts, nur an ihrer kosmetischen Häufigkeit. Die US-Zeitumstellung
(01.11.2026, EDT→EST) verschiebt den realen NYSE-Schluss in UTC
(20:00→21:00 Uhr), ändert aber nichts an dieser Einschätzung, weil die
Drift den Lauf ausschließlich SPÄTER, nie früher startet.

**Offen, ausdrücklich:** ob die wachsende Drift ein echter Trend oder
Rauschen ist, lässt sich mit nur ca. 6 Wochen Beobachtung nicht sicher
sagen — die Beobachtung über den Lauf-Zeitversatz-Wächter läuft
unverändert weiter.

**14. Automatisierungsplan vom 24.10.2026 — Schritte 1, 2, 3 und 4
gebaut (PR #74, #76, #77+#78, #75), Auftrag 5 umdefiniert, EIN offener
Punkt verbleibt.** *(Easys Entscheid/Klärung bei Punkt (d); Punkte (a)
und (b) sind geschlossen, Punkt (c) betrifft weiterhin `lauf.yml`
selbst und bleibt bis nach dem 30.10.2026-Stichtag offen)*

**Ziel des Plans** (Easys Formulierung): Datenfehler ohne mein Zutun
finden, melden, ungefährliche reparieren; ich entscheide nur Score-/
Signal-/Methodik-Fragen. **Reihenfolge:** 1. Daten-Abdeckungs-Wächter
(**gemergt, PR #74**) — 2. Wiedervorlagen mit Fälligkeitsdatum
(**gemergt, PR #76**) — 3. Schutz-Sperre (**gemergt als Check, PR #77;
auf reine Ampel umgestellt, PR #78 — siehe Entscheidung (3) unten**) —
4. ntfy-Relay (**gemergt und per Testlauf bewiesen, PR #75**) — 5.
geplante Agenten, **umdefiniert statt gebaut** (siehe Entscheidung (4)
unten). **„Schritt 6" (eingefrorene Tests) entfällt** — geprüft, es
existieren keine Freeze-Dokumente in diesem Projekt (einziger Treffer
auf „freeze": `tests/unit/test_freeze.py`, ein gewöhnlicher Unit-Test,
kein Dokument).

**Entscheidung (5) — Identität von Code/Agenten, Grundlage für (3) und
(4):** Schritt 0 einer eigenen Diagnose-Sitzung (vor PR #78) ergab, per
`gh api user`/`get_me()` UND am realen Beispiel PR #77 (`user.login`
UND `merged_by` jeweils `"easywebb911"`, obwohl ein Agent es geöffnet
hätte) **belegt, nicht vermutet:** der Code dieses Repos — und jeder
künftige automatisiert arbeitende Agent — handelt in der GitHub-API
SELBST als `easywebb911`. Jede Freigabe "von easywebb911" (Label oder
Kommentar) wäre deshalb vom selben Agenten, der sie prüft, trivial
fälschbar.

**Entscheidung (3) — Schutz-Sperre ist eine Ampel, keine Sperre (PR
#78, korrigiert gegenüber PR #77):** die ursprüngliche Label-Freigabe
(`freigabe-easy` von `easywebb911`, nach dem letzten Push) ist wegen
Entscheidung (5) **wertlos und wurde vollständig entfernt**, kein
Ersatzweg. Die Zonenerkennung selbst (Pfad- und Symbol-Ebene,
Selbstschutz, fail-closed) bleibt unverändert — siehe §7.8. Der Check
zeigt nur noch GRÜN (keine geschützte Zone berührt) oder ROT
(geschützte Zone berührt, **Easys Entscheidung nötig** — nicht
"verboten"). `[Wächter]`-PR-Titel mit berührter Zone bleiben rot und
bekommen zusätzlich eine eigene Hinweis-Zeile in der Check-Ausgabe.
**Wichtig, unverändert gegenüber PR #77:** ohne das Main-Schutz-Ruleset
(Entscheidung (2) unten) blockiert ein roter Check ohnehin keinen
manuellen Merge — das war mit PR #78 nie der Punkt, der sich geändert
hat.

**Entscheidung (4) — Auftrag 5 umdefiniert: Agenten mergen NIE.**
Direkte Folge aus Entscheidung (5): eine technische Freigabe-Grenze
bräuchte eine vom Agenten UNTERSCHEIDBARE Identität (eigene GitHub-App
oder ein zweites Konto) — bewusst nicht gebaut. Stattdessen gilt für
geplante Agenten künftig dasselbe Prinzip wie seit PR #49 für den
Reparatur-Agenten Stufe 3: sie öffnen PRs für Klasse-A-Reparaturen
(ungefährlich, eng begrenzt) und melden per ntfy-Relay (PR #75) — Easy
sieht die Schutz-Sperre-Ampel, entscheidet und merged selbst. Kein
Auto-Merge, auch nicht bei grüner Ampel.

**Entscheidung (1) — Wiedervorlagen-Format (PR #76):** der
`faellig`-Kommentar lebt direkt in §3 von SESSION_HANDOVER.md, KEINE
zweite Datei — eine Quelle für Mensch UND Wächter. Ab jetzt gilt
verbindlich: **jede neue Zeile in §3 braucht ab sofort einen
`faellig`-Kommentar** (Datum oder `offen`), sonst schlägt der
Format-Test (`tests/unit/test_wiedervorlagen_waechter.py::
test_jede_zeile_in_paragraph_3_hat_einen_gueltigen_faellig_kommentar`)
beim nächsten Lauf der Testsuite rot an.

**Entscheidung (2) — Ruleset „Main-Schutz" bleibt bewusst disabled,
Punkt (a) aus PR #74 damit geschlossen:** seit 02.08.2026
`enforcement: disabled`, weil es Bot-Direktpushes (GH013) blockierte
und ein Bypass-Eintrag „GitHub Actions" sich am iPhone nicht einrichten
lässt. **Bleibt aus.** Folge für Auftrag 3 (Schutz-Sperre) und 5
(geplante Agenten): die harte Grenze liegt NICHT im Ruleset, sondern im
**Merge-Schritt selbst** — ein Agent ohne Merge-Recht, bzw. ein eigener
Merge-Workflow, der PRs mit geschützten Pfaden verweigert. Punkt (b)
unten (Pfad-basierte Merge-Verbote) baut direkt darauf auf.

**Festgehaltene Entscheidungen:** Nachrichten ausschließlich bei
Warnung, kein „alles ok"-Digest (bestehende Regel seit 10.08.2026, siehe
§8/notify.py-Kopf) — beide neuen Bausteine halten sich daran (das
ntfy-Relay versendet nur auf ausdrückliche Anforderung per
`workflow_dispatch`, nie nach Zeitplan). Keiner der beiden greift in
`run.py` ein; das Relay ruft `notify.push()` direkt auf, keine zweite
ntfy-Implementierung.

**Befund aus dem laufenden Betrieb von PR #74, hier ergänzt:** Prüfung B
(iShares-Kursvergleich) des Daten-Abdeckungs-Wächters greift unter der
heutigen Lauf-Kadenz **kaum** — das Feld `kursvergleich` steht nur bei
Stichtags-Läufen in `data/status.json` (ca. einmal im Monat), ein
7-Tage-Fenster sieht deshalb fast nie die geforderten mindestens zwei
Beobachtungen. Für eine **tägliche** Prüfung bräuchte es stattdessen
einen eigenen Zähler im Lauf selbst (`run.py`) — das gehört zusammen mit
dem unten unter (d) genannten Elliott-Zähler in denselben Folgeauftrag
nach dem 30.10.2026-Stichtag, weil beide `run.py` berühren würden.

**Offene Punkte, hier gemeldet statt selbst entschieden:**

*(a) ist geschlossen — siehe „Entscheidung (2)" oben.*

*(b) ist geschlossen — siehe „Entscheidung (4)" oben: die Frage
"wie fragt ein Merge-Workflow die Pfad-Prüflogik vor dem Mergen ab"
stellt sich nicht mehr, weil Agenten gar keine Merge-Rechte bekommen,
mit oder ohne Abfrage. `schutz_sperre.py` bleibt eine reine Ampel fürs
Easys eigene Entscheidung, kein serverseitiges Merge-Gatter.*

- ~~**(c) `lauf.yml` interpoliert `${{ inputs.datum }}` direkt in die
  Shell**~~ — **erledigt mit `f03c753` (Merge PR #87, 06.11.2026), siehe
  §10.**
- **(d) — geparkt seit 03.11.2026.** Grund: berührt `run.py` (Lauf-Pfad)
  und gehört zeitlich hinter V3 (§4 Punkt 16, ab 02.12.) und die
  Lauf-Pfad-Ruhe vor dem 30.11.; vorher kein Bau. Inhalt unverändert:
  **Folgeauftrag nach dem 30.10.2026-Stichtag, gebündelt:**
  **Elliott-Zähler** (Unterscheidung „Quelle unerreichbar" vs. „Quelle
  leer/veraltet", bewusst außerhalb von PR #74) UND **ein täglicher
  Kursvergleichs-Zähler im Lauf** (siehe Befund oben, macht Prüfung B
  erst wirksam) — beide berühren `run.py` und gehören deshalb in
  denselben, erst nach dem Stichtag angegangenen Auftrag.
- **(e) — geparkt seit 03.11.2026.** Grund: wirkt nur beim nächsten
  Universum-Rebuild (manuell, kein Termin geplant), und der Rebuild
  bricht bei unplausiblen Zahlen ohnehin laut ab
  (`tools/build_universe.py`). Inhalt unverändert: **Eine
  Wikipedia-Spaltenumbenennung bleibt bis zum nächsten
  Universum-Rebuild unbemerkt** — durch Prüfung C von PR #74
  (Universum-Alter) nur TEILWEISE abgedeckt: die Alters-Schwelle warnt
  irgendwann, erkennt aber keine Umbenennung selbst, nur das
  Verstreichen der Zeit. Weiterhin offen, unverändert gegenüber PR #74.

**15. Auftrag 5 konkretisiert: drei geplante Claude-Tasks (seit
25.10.2026) PLUS Agenten-Kontrolle gegen deren eigenes Ausbleiben (PR
#79, gemergt) — am 31.10.2026 umgestellt auf Nur-Lesen + App-Push,
Agenten-Kontrolle abgeschaltet (Abschnitt „Umstellung 31.10.2026" am
Ende dieses Punkts; die Beschreibung direkt darunter ist der
ursprüngliche Stand vom 25.10.).** *(Easys eigene Task-Einstellungen sind die Quelle,
hier nur dokumentiert; PR #79 Merge-Commit `9f0238c`, 25.10.2026
20:22 UTC)*

Entscheidung (4) oben ("Agenten mergen NIE") bleibt unverändert die
Grundregel. Konkret eingerichtet (25.10.2026, außerhalb dieses Repos, in
Easys Claude-Task-Einstellungen) sind drei geplante Tasks — **keiner von
ihnen merged**, Zustellung ausschließlich über `ntfy_relay.yml` (PR #75),
Claudes eigener Push-Kanal bewusst deaktiviert:

- **Wächter**, täglich 12:31 Berlin-Zeit (≈ 11:31 UTC Winterzeit) —
  prüft Läufe/Wächter/Rankings, bereitet bei Bedarf `[Wächter]`-PRs vor
  (höchstens einer pro Tag, nur wenn Tests grün, byte-identisch wo
  nötig, UND die Schutz-Sperre grün bleibt). Meldet täglich: gesund =
  lautlos (dieselbe Herzschlag-Ausnahme wie `push_waechter_ok`, siehe
  §8 Lesson, Entscheid 10.08.2026).
- **Lit-Check**, sonntags 09:56 Berlin-Zeit.
- **Monatsrundgang**, am 3. jedes Monats, 08:32 Berlin-Zeit.

Alle drei laufen ohne Rückfrage (auto) — änderbar einzig in den
Task-eigenen Einstellungen, nicht in diesem Repo.

**Entscheid, hier festgehalten:** das tägliche, lautlose Lebenszeichen
des Wächter-Agenten ist eine bewusste, ausdrückliche Ausnahme von der
Kein-Herzschlag-Regel vom 10.08.2026 — exakt dasselbe Präzedenzprinzip
wie beim Totmannschalter selbst (`push_waechter_ok`, lautlos per
Priorität `min`): die eigene Abwesenheit des Agenten muss auffallen
können. **PR #79 (Agenten-Kontrolle) ist das Werkzeug, das dieses
Lebenszeichen tatsächlich überwacht** — siehe `src/momentum/
agenten_kontrolle.py`. **Lit-Check und Monatsrundgang sind von dieser
Lebenszeichen-Prüfung ausdrücklich NICHT erfasst**: beide laufen an
einem fixen Tag im Monat/in der Woche, ihr eigenes Ausbleiben wäre schon
ohne eigenen Wächter offensichtlich (der fällige Tag vergeht sichtbar,
ohne dass etwas passiert).

**Bekannte Grenze, offen benannt statt verschwiegen:** „Agenten mergen
nie" existiert bisher nur als dem Agenten gegebene Anweisung, nicht als
technische Durchsetzung — jeder Agent handelt in der GitHub-API SELBST
als `easywebb911` (Entscheidung (5) oben), könnte also technisch auch
mergen. Das ist **„Weg B"**: ein bewusst gewählter, hier dokumentierter
Risiko-Akzept, keine übersehene Lücke. Eine technische Durchsetzung
(eigene GitHub-App/zweites Konto) wurde bereits bei Entscheidung (4)
geprüft und bewusst nicht gebaut.

**Revert-Pfad für PR #79:** ein Revert dieses einen Merge-Commits nimmt
Kontroll-Modul (`agenten_kontrolle.py`), den neuen Workflow
(`agenten_kontrolle.yml`), die zugehörigen Tests UND die eine
`run-name`-Zeile in `ntfy_relay.yml` als EINE Einheit zurück — keine
verstreuten Reste.

**Betrieb der drei Tasks, erste Woche — mit echten Störungen, belegt
wo möglich:**
- **27.10.2026:** der Wächter-Task meldete `USAGE_LIMIT_REACHED`
  (Claude-eigenes Nutzungslimit erreicht) — **ungeprüft** (das ist ein
  Easy-gemeldeter Befund aus der Task-Oberfläche, nicht aus diesem
  Repo belegbar). **Die Agenten-Kontrolle hat das Ausbleiben korrekt
  erkannt und gemeldet:** Lauf Nr. 3, 28.10.2026 23:58 UTC (Actions-
  Run `40790950697`, Job-Log wörtlich „Waechter: Push verschickt.") —
  zu diesem Zeitpunkt lag der letzte (einzige bisherige)
  `ntfy_relay.yml`-Lauf mit einem `run-name` ueberhaupt **noch nie**
  vor (siehe Modul-Docstring, Anlaufschutz-Beispiel), und der
  PR-#79-Merge selbst lag zu diesem Zeitpunkt bereits gut 75 Std.
  zurück — mehr als `FENSTER_STUNDEN` (48). Damit ist "meldete korrekt
  nach über 48 Std." nicht nur Easys Bericht, sondern per Job-Log
  belegt.
- **30.10.2026:** der Wächter-Task hatte laut Easy keinen Repo-Zugriff
  (HTTP 403, `add_repo` nicht gefunden) — **ungeprüft** (ebenfalls nur
  aus der Task-Oberfläche berichtet). Der Aufgabentext wurde
  daraufhin um „add_repo per ToolSearch laden" ergänzt — **ungeprüft**,
  ob das die Ursache behebt.
- **31.10.2026, 12:31 Berlin-Zeit:** wieder kein Repo-Zugriff — laut
  dem Bericht des Tasks selbst (von Easy weitergeleitet) endete jede
  API-Abfrage mit „HTTP 403: GitHub access to this repository is not
  enabled for this session", `add_repo` war auch per ToolSearch nicht
  verfügbar, der `gh`-Token galt als ungültig. Der Task las das
  öffentliche Repo trotzdem per Kopie, prüfte das Oktober-Ranking
  korrekt und schickte statt ntfy einen Push über die Claude-App. Die
  Ergänzung vom 30.10. hat das Problem also **nicht** behoben — Ursache
  siehe Umstellung unten.

**Bislang noch KEIN einziger `ntfy_relay.yml`-Lauf mit einem Titel, der
mit "ntfy: Momentum-Waechter" beginnt** (`gh api .../ntfy_relay.yml/runs`
zeigt weiterhin nur den einen Lauf von PR #75, 25.10., vor Einführung von
`run-name`) — die Agenten-Kontrolle hat seit ihrem Merge bei JEDEM ihrer
fünf bisherigen Läufe (26.–30.10., alle grün) entsprechend keinen
echten Treffer gefunden; ob sie seit Ablauf der 48-Std.-Anlaufschutz-
Frist (ab ca. 27.10. 20:22 UTC) bei jedem weiteren Lauf erneut gemeldet
hat, ist naheliegend, aber nur für Lauf Nr. 3 (siehe oben) tatsächlich
per Job-Log nachgeprüft — die übrigen vier Läufe **ungeprüft**.

**Umstellung 31.10.2026 (Entscheidung Easy) — warum und was genau:**

*Ursache, soweit belegt:* Die drei Tasks wurden am 25.10. aus dem
claude.ai-Chat-Projekt „Momentum-Projekt" heraus angelegt. Ihre
Bearbeiten-Ansicht (iPhone-App und claude.ai im Browser, von Easy per
Screenshot gezeigt) bietet **kein Repository-Feld** — unter „Erweiterte
Einstellungen → Allgemein" steht nur die Zuordnung zum Projekt. Das
Projekt selbst bietet unter „Kontext" nur eine GitHub-*Synchronisierung*
(Dateien als Lesestoff), keinen Repo-Zugriff für Tasks. Die
Task-Konfiguration (per `list_triggers` gelesen) enthält kein Feld für
Repositories; ein am 31.10. testweise aus einer Sitzung mit
angehängtem Repo neu angelegter Task bekam ebenfalls keins (sofort
wieder gelöscht, nie gestartet). Damit hatte der Wächter **von Anfang an
keinen GitHub-Zugriff** — passend dazu gibt es bis heute keinen einzigen
`ntfy_relay.yml`-Lauf eines Agenten (siehe oben). *Ungeprüft:* ob ein
außerhalb des Projekts direkt unter claude.ai/code/routines neu
angelegter Task ein Repository-Feld anbieten würde — nicht ausprobiert.

*Neu eingestellt (Aufgabentexte per `update_trigger` ersetzt,
31.10.2026 ca. 13:04 UTC):*
- **Alle drei Tasks** lesen das Repo nur noch über eine öffentliche
  Kopie (`git clone` der öffentlichen URL), rufen **keine** GitHub-API
  auf, bauen **keine** PRs, lösen **keine** Workflows aus und melden
  sich per **Push über die Claude-App** statt über `ntfy_relay.yml`.
- **Wächter** (täglich 12:31 Berlin-Zeit): prüft Lauf-Commits (fehlt ein
  Werktag?), `data/status.json` samt Historie, Rankings je Monat/Markt,
  §3/§4 dieses Dokuments. Push **nur bei Befund**; ohne Befund **nur
  montags** ein Lebenszeichen „Momentum-Waechter OK TT.MM.". Kennt die
  Fehlalarm-Falle `faellige_monate_offen` (Stand vor dem Lauf).
- **Lit-Check** (sonntags 09:56) und **Monatsrundgang** (3. des Monats,
  08:32): Inhalt wie bisher, Zustellung per App-Push (Kurzfassung, voller
  Bericht bleibt in der Task-Sitzung).
- **Agenten-Kontrolle** (`agenten_kontrolle.yml`, PR #79) per
  Actions-API abgeschaltet (Status `disabled_manually`, per `gh api`
  gegengeprüft) — sie hätte sonst alle 48 Std. Alarm geschlagen, weil
  kein Agent mehr über `ntfy_relay.yml` meldet. **Code, Workflow-Datei
  und Tests bleiben unverändert im Repo.** Ihre Aufgabe übernimmt das
  Montags-Lebenszeichen (Ausfall fällt binnen einer Woche statt 48 Std.
  auf).

*Was dadurch wegfällt, offen benannt:* Der Wächter sieht keine
Workflow-Läufe, Job-Logs und PRs mehr und bereitet keine
`[Wächter]`-PRs mehr vor (Klasse A entfällt). Workflow-Fehlschläge
melden weiterhin die GitHub-Wächter selbst per ntfy (Totmannschalter,
Vertragstest, Zeitversatz, Push-Zustellung, Daten-Abdeckung u. a.).
Reparaturen laufen wieder über Claude im Chat + Code. „Weg B" (Agenten
handeln als `easywebb911`) ist damit praktisch gegenstandslos — die
Tasks haben keinen Schreibzugriff mehr.

*Rückweg:* Agenten-Kontrolle auf ihrer Workflow-Seite per „Enable
workflow" wieder einschalten
(https://github.com/easywebb911/Momentum-Report/actions/workflows/agenten_kontrolle.yml);
die alten Aufgabentexte stehen sinngemäß oben in diesem Punkt und lassen
sich per `update_trigger` zurückspielen — sinnvoll erst, wenn die Tasks
tatsächlich Repo-Zugriff bekommen.

**Nachtrag 01.11.2026 (Entscheidung Easy) — Zustellung direkt an
ntfy.sh:** Die drei geplanten Tasks senden ihre Meldungen jetzt **direkt
an ntfy.sh**; das Thema steht im Aufgabentext. *Risiko, bewusst
akzeptiert:* wer den Aufgabentext sieht, kennt das Thema und könnte
mitlesen oder Meldungen einschleusen. *Rückweg:* Thema in der ntfy-App
wechseln (und im Aufgabentext nachziehen). **Wächter:** täglich lautlos
(Priorität 1), montags hörbar (Priorität 3), bei Befund Priorität 3 bzw.
4; Fallback App-Push, falls ntfy.sh nicht annimmt. Beim Test am 01.11.
einmal **HTTP 429** (zu viele Anfragen) von ntfy.sh — vermutlich wegen
der geteilten Cloud-Adresse (**ungeprüft**); die Wiederholung war
erfolgreich. **Lit-Check 01.11.:** lief korrekt, sein Push kam aber
**nicht** an (damals noch App-Push-Weg); Easy hat den Bericht aus der
Task-Sitzung kopiert. Quelle aller Angaben dieses Nachtrags: Easys
Task-Einstellungen und Bericht — aus diesem Repo nicht belegbar.

**16. Oktober-Stichtag-Vorfall 30./31.10.2026 — zwei Abbrüche,
Ursache seit der Diagnose vom 01.11. belegt (Yahoo-Verzögerung), Lücke
„stiller falscher Stichtag" erkannt, Prüfung V3 entworfen.** *(siehe §3:
Beleg-Zähler auswerten, 01.12. Handlauf, ab 02.12. V3 bauen)*

*Diagnose 01.11.2026 (read-only), Ergebnis:*
- **Ursache belegt, nicht mehr nur vermutet:** Yahoo liefert den
  bereinigten Kurs (Adj Close) des jüngsten Handelstags verspätet; die
  Zeile wird in `data.py` (Prüfung „Adj Close nicht endlich") gewollt
  verworfen. Beleg: in **jedem** Anzeige-Lauf seit 26.09. gilt
  `zeilen_verworfen_nicht_endlich = 5` (eine Zeile je Top-5-Titel) genau
  dann, wenn `kurse_vom` einen Handelstag zurückliegt, und `= 0` genau
  dann, wenn es aktuell ist (Git-Historie `data/status.json`). DE liegt
  schon seit August bei jedem Lauf nach ≈ 22:00 UTC zurück; US seit
  **Lauf 67 (25.09., erster Start nach Mitternacht UTC)** fast immer.
  Kein Code-, Versions- oder Cron-Wechsel am Startpunkt
  (`lauf.yml` Cron unverändert, `yfinance==0.2.65` seit `8f277cc`).
  Sichtbar wurde es, weil GitHub die geplanten Läufe 2–5 Std. nach
  21:45 UTC startet.
- **Zeitfenster laut Läufen 94–96:** US-Adj-Close des 30.10. fehlte um
  01:02 UTC, war um 08:07 UTC da; DE fehlte um 08:07 UTC, war um 09:14
  UTC da. *Ungeprüft:* ob es an der Uhrzeit oder am Mitternachtswechsel
  hängt — nicht sauber trennbar.
- **Lauf 71 (01.10., September-Stichtag)** scheiterte an etwas anderem
  (Yahoo-Rate-Limit beim Index, `YFRateLimitError`, Run `36798080643`),
  gerettet durch den manuellen Lauf 72.
- **Mechanik:** der Stichtag kommt aus der Index-Reihe (`resolve_asof`);
  fehlt **allen Titeln** der Tag, scheitert je Titel die 52W-Nähe an
  „kein Kurs am Stichtag" → „kein Titel mit vollstaendiger Historie"
  (laut, nichts eingefroren — so in 94/95). **Lücke:** fehlt dem
  **Index** der letzte Tag, nimmt `resolve_asof` still den Vortag —
  ein falscher Stichtag würde ohne Alarm eingefroren (bisher nie
  beobachtet).
- **Design (Varianten):** V1 Rohkurs-Abgleich (Index oder ≥ 50 % der
  Titel mit Rohkurs nach dem Index-Stichtag → zurückhalten; am Stichtag
  mehr als max(3, 2 %) Titel mit Rohkurs, aber ohne Adj Close →
  zurückhalten); V2 Werktags-Wartezeit (nur Wochentage, keine
  Feiertagsliste); **V3 = V1 plus höchstens ein Werktag Wartezeit, wenn
  ein Kalender-Werktag ganz ohne Spur ist.** Für alle: zurückhalten nur
  verhindern, nie einen anderen Stichtag wählen; nach 3 Werktagen
  „unvollständig" lauter Abbruch (bestehender Alarm). Durchgespielt u. a.
  DE 24./31.12., US Memorial Day 31.05.2027, Thanksgiving/27.11.,
  Karfreitag am Monatsende.
- **Entscheidung Easy (01.11.2026):** **V3**, gebaut **erst nach Beleg
  ab 02.12.**; vorher nur der Beleg-Zähler (PR #86), weil V3 auf der
  **ungeprüften Annahme** beruht, dass Yahoo die verspätete Zeile MIT
  Rohkurs liefert. Für den 30.11.: manueller Lauf am 01.12. ab 09:30 UTC
  plus Stichtag-Prüfung (§3).

*Erster Messpunkt des Beleg-Zählers (PR #86) — Lauf 97, 03.11.2026,
Commit `32221f7`, 03:03 UTC (`data/status.json`):* **DE** 5 Zeilen
verworfen, davon **0 mit / 5 ohne Rohkurs**, alle am **02.11.**; **US**
0 verworfen (`kurse_vom` 02.11., aktuell). Damit ist die V3-Annahme
(„Zeile mit Rohkurs, nur Adj Close fehlt") **für DE widerlegt — bei
einem einzigen Messpunkt**; für US liegt noch kein Fall vor. Folge,
falls sich das bestätigt: der Rohkurs-Teil von V3 erkennt die
DE-Verzögerung nicht, es bleibt nur die Werktags-Wartezeit (V2-Anteil).
Nebenbefund: DE `kurse_vom` stand damit auf 30.10. — einen Handelstag
zurück (Mo 02.11. fehlte) — das bekannte Muster.

*Auswertung 05.11.2026 (Läufe 97/98/99, `32221f7`, `ec8ba91`,
`d6618ef`):* in 5 von 6 Markt-Läufen je 5 Zeilen des Vortags verworfen,
alle **ohne** Rohkurs (0 mit); vollständig nur US im Lauf 97 (Handelstag
02.11.). Die Annahme hinter V3 ist damit widerlegt. Grenze: der Zähler
sieht nur die 5 Anzeige-Titel, nicht den Index und keinen Stichtagslauf.

**Entscheidung Easy (05.11.2026): V2 statt V3** — Werktags-Wartezeit,
kalenderbasiert (nur Wochentage, keine Feiertagsliste); greift auch,
wenn dem **Index** der letzte Tag fehlt (der stille-Stichtag-Fall).
**Bau ab 02.12.** (nach dem November-Stichtag), **Merge-Ziel vor dem
31.12.2026** (DE-Feiertagsfall: Xetra 24./31.12. zu). Im selben Bau:
die Absturzstelle `run.py:372` bei leerem `new_ranking` (§5 Punkt 4)
und der Alarm ab Werktag 3 („bleibt dauerhaft unvollständig" → lauter
Abbruch). Ersetzt die Entscheidung vom 01.11. (V3) oben.

*Vorgeschichte (Stand 31.10., unverändert belassen):*

Vier Läufe, alle per `gh api`/Job-Log gegengeprüft:
- **Lauf 93** (planmäßig, 30.10.2026, 01:20 UTC, Actions-Run
  `40985254613`, erfolgreich): hielt den Oktober-Stichtag für BEIDE
  Märkte erwartungsgemäß zurück — Job-Log wörtlich „Stichtag
  2026-10-30 zurueckgehalten: Lauf um 01:20 UTC liegt vor 21:00 UTC
  [US] / 16:30 UTC [DE]" (siehe `ranking.zu_frueh_fuer_stichtag`, PR
  #53/#73).
- **Lauf 94** (planmäßig, 31.10.2026, **01:02 UTC** — Actions-Run
  `41153318736`, fehlgeschlagen): lief trotz Rutsch über Mitternacht
  korrekt in die Oktober-Stichtag-Rechnung hinein (**realer
  Wirksamkeitsnachweis für PR #73**, der genau diesen Mitternachts-
  Fall gegen das volle Datum statt nur die Uhrzeit absichert), brach
  dann ab: Job-Log wörtlich „LAUF ABGEBROCHEN: us: kein Titel mit
  vollstaendiger Historie". **Korrektur gegenüber der ursprünglichen
  Angabe „02:02 UTC":** der tatsächlich geloggte Start ist 01:02 UTC
  — Widerspruch hier gemeldet, nicht stillschweigend übernommen.
- **Lauf 95** (manuell, 31.10.2026, 08:07 UTC, Actions-Run
  `41183266440`, fehlgeschlagen): US lief vollständig durch (Stichtag
  2026-10-30, Geldmarkt 3,69 %), DE brach danach ab — Job-Log wörtlich
  „LAUF ABGEBROCHEN: de: kein Titel mit vollstaendiger Historie".
- **Lauf 96** (manuell, 31.10.2026, 09:14 UTC, Actions-Run `41187870579`,
  Commit `8e29c5d`, 09:16:31 UTC, erfolgreich): schrieb
  `data/rankings/us_2026-10.json` (496 von 503 bewertet) UND
  `de_2026-10.json` (**81 von 81 liquiden Titeln bewertet — keine
  einzige Historie-Lücke mehr**, belegt per `git show origin/main:
  data/rankings/de_2026-10.json`).

**Ursache (Stand 31.10.: ungeprüft, eine Vermutung, mit Indiz — seit
01.11. belegt, siehe oben):** Yahoo liefert `Adj
Close` für den letzten Handelstag mutmaßlich verspätet (derselbe
Mechanismus wie beim 31.08.2026-Vorfall, §4 Punkt 2 — dort betraf es
den seither entkoppelten Kursvergleichspfad, der Score-Pfad bleibt
laut `data.py` bewusst an `Adj Close` gekoppelt). **Indiz, kein
Beweis:** zwischen Lauf 95 (08:07 UTC, DE-Abbruch) und Lauf 96 (09:14
UTC, DE vollständig) liegt gut eine Stunde, in der sich NICHTS am Code
änderte — nur die Zeit verging. Eine echte Belegprüfung (rohe
Yahoo-Antwort je Titel) stand nicht auf diesem Auftrag; siehe §3,
offene Wiedervorlage.

**Der Lauf ist Alles-oder-nichts, unverändert:** ein DE-Abbruch verwirft
auch ein bereits fertig gerechnetes US-Ranking im selben Lauf (Lauf 95
schrieb trotz US-Erfolg NICHTS — `main()` in `run.py` verarbeitet die
Märkte sequenziell in einer Schleife, ein `RankingNotPossible` in einem
späteren Markt bricht den gesamten Lauf ab, BEVOR irgendetwas
geschrieben wird; nur ein zuvor bereits abgeschlossener Markt-Schritt
bleibt als Seiteneffekt erhalten). Eine Änderung daran wäre
Stichtag-Logik — nicht Teil dieses Auftrags, eigener Entscheid von
Easy, falls gewünscht.

**PR #80, gemergt (Merge-Commit `569e385`, 31.10.2026, 10:42 UTC), ist
die direkte Gegenmaßnahme:** die Abbruchmeldung nennt jetzt Zahlen je
Ausscheidegrund (ohne Stichtagskurs/ohne Monatsendkurs/sonstige),
damit ein künftiger Abbruch ohne Rätselraten lesbar ist — siehe
PR-Text für die Belege.


**17. Lit-Check 08.11.2026 — „Momentum-Wendepunkte" — geprüft, nicht
gebaut.** *(entschieden, nichts zu tun)*

Fund: Goulding, Harvey & Mazzoleni (2023), „Momentum turning points",
*Journal of Financial Economics* 149(3), S. 378–406 (Heft, Seiten, Jahr
per Katalog RePEc/EconPapers bestätigt; Volltext nicht gelesen). Die
Arbeit teilt den US-Gesamtmarkt mit langsamem und schnellem
Zeitreihen-Momentum in vier Phasen ein (Bull, Correction, Bear, Rebound)
— gemessen am **Index**, nicht an einer Rangliste einzelner Aktien.

**Verdikt Easy (08.11.2026): NICHT bauen.** Begründung: Der
Rebound-Fall (12 Monate negativ, 1 Monat positiv) ist durch die
bestehende Trend-Ampel abgedeckt (12-Monats-Index, Warnlage nach
Daniel & Moskowitz). Der neue Korrektur-Fall ist nur für Index-Timing
belegt, nicht für Einzelaktien-Ranglisten. Zweiter Teil desselben
Lit-Checks (Europa/DE neu, Datenqualität Yahoo): **Nullbefund**.
Quelle der Bewertung: Easys Lit-Check-Bericht vom 08.11. (aus dem Repo
nicht belegbar).


**18. Lit-Check 14.11.2026 (Edge-Suche) — zwei Funde, geprüft, nicht
gebaut.** *(entschieden, nichts zu tun)*

**Fund 1: Residual-Momentum** — Blitz, Huij & Martens (2011), *Journal
of Empirical Finance* 18, S. 506–521. Behauptung: risikobereinigt ca.
doppelt so gut wie normales Momentum. Gegenprüfung an Hou, Xue & Zhang
(2020), *Review of Financial Studies* 33, Table 3, NYSE-VW
(wertgewichtet, große Firmen dominieren), 1 Monat Haltedauer:
Residual-Momentum ε11 1 = **0,61 %/Monat (t 3,72)** gegenüber
12-1-Momentum R11 1 = **1,16 %/Monat (t 3,99)** — am Original-PDF geprüft
im Sparring-Chat 14.11.2026 (aus dem Repo nicht belegbar). Der Vorteil
bei Blitz/Huij/Martens gilt für das Faktor-Alpha, nicht für die
Rohrendite. Weitere Vorsicht: Autoren bei Robeco (Eigeninteresse
möglich); Japan-Nachprüfung (2024) nach Kontrolle kurz- und
langfristiger Umkehr nicht signifikant. Grenze: Die Tabelle misst
Long-Short-Dezile, nicht Top-5 long-only.
**Verdikt Easy (14.11.2026): NICHT umstellen.**

**Fund 2: Momentum und Dividende** — Cannon & Lynch (2025), *Review of
Finance* 29(4), S. 1009–1042. Momentum bei Aktien ohne Dividende ca.
doppelt so stark (1,417 gegenüber 0,684 %/Monat; alle US-Aktien,
Long-Short-Quintile). Nicht auf der Large-Cap-Gewinnerseite belegt; im
S&P 500/HDAX zahlen die meisten Titel Dividende, ein Filter würde die
Auswahl schrumpfen und Richtung Tech verschieben.
**Verdikt Easy (14.11.2026): NICHT bauen.**
---

## 5. Hygiene-Backlog

Kleinarbeit ohne Dringlichkeit — jeweils ein eigener kleiner PR.

1. ~~**`Node.js 20 is deprecated`-Warnung (`actions/checkout`/
   `actions/setup-python`)**~~ — **erledigt mit `f03c753` (Merge PR #87,
   06.11.2026), siehe §10.** Der Rest (Artefakt-Actions in `vertrag.yml`)
   bleibt offen als Punkt 5 unten.
2. ~~**Wegwerf-Workflow `probe_ishares_neu.yml` (PR #62) noch nicht
   zurückgebaut**~~ — **erledigt durch PR #67 (06.10.2026, siehe §2,
   §10).** Datei und Eintrag im geschlossenen Workflow-Set
   (`tests/unit/test_workflow_hygiene.py`) sind entfernt.
3. ~~**Schutz-Sperre kannte die neuen Fahrplan-Hilfen in `config.py`
   nicht**~~ — **geschlossen im selben PR #83 (Nachtrag 01.11.2026):**
   `GewichtsEintrag`, `FAHRPLAN_BEGINN` und `_pruefe_gewichtspaar` stehen
   jetzt in `GESCHUETZTE_SYMBOLE["src/momentum/config.py"]` (bestehende
   Einträge unverändert). Beleg:
   `tests/unit/test_schutz_sperre.py::test_aenderung_an_pruefe_gewichtspaar_wird_erkannt`
   (eine abgeschwächte Summenprüfung wird jetzt als Berührung gemeldet;
   mit der alten Liste wäre das Ergebnis leer, also grün gewesen).
4. **Absturzstelle in `run.py:process_market` bei leerem `new_ranking`**
   (gefunden in der Design-Diagnose 01.11.2026): nach dem Monats-Loop
   folgt `current = new_ranking; top = current["top"]` (`run.py:372–373`).
   Heute unerreichbar (jeder Monat im Loop wird entweder geschrieben oder
   der Lauf bricht laut ab). **Wird aber erreichbar**, sobald eine
   Prüfung Monate still zurückhält (V3, §4 Punkt 16) — dann braucht es
   einen Rückfall auf `latest_ranking` wie im Anzeige-Zweig. Geschützte
   Zone (`process_market`), MANUAL; gehört in den V3-PR, nicht separat.
5. **Node-20-Warnung durch `actions/upload-artifact@v4` und
   `actions/download-artifact@v4` in `vertrag.yml`** *(offen)* — belegt
   im Job-Log Run `41073466086` (Jobs `vertrag` und
   `agent-datumsformat`); bewusst nicht in PR #87, weil nicht beauftragt.
   **Vor der Umstellung die Änderungen der neuen Major-Versionen prüfen.**
   Geschützte Zone (`.github/workflows/`), MANUAL.

Erledigt und deshalb nicht mehr aufgeführt: Punkt „Testkontext auf
default-deny umstellen" (#40, siehe §10), die Kosmetik-Punkte (tote
CSS-Regel, tote Symbole, verwaiste Fixture, doppeltes Literal, zu breite
`window.MR`-Ausfuhr, liegengebliebene Branches, `.gitignore`) sowie die
Doku-Drift durch abgeschriebene Zähler. Die README-Modulliste ist kein
Backlog-Punkt mehr, sondern eine Daueraufgabe — sie steht in den Lessons.

---

## 6. Roadmap

Ausdrücklich **keine** Zusage, nur die Liste der Dinge, die als Nächstes
sinnvoll wären — in dieser Reihenfolge:

0. **Methodenwechsel US (Score 100/0 ab Ranking 2026-11) — inhaltlich
   abgeschlossen, Merge von PR #85 offen.** PR 1 (Rechnung, Fahrplan) ist
   PR #83, **gemergt** (`f5a21b3`); **PR 2** (Methodik-Seite und Karten)
   ist PR #84, **gemergt** (`022c8ff`) — Karte zeigt bei 52W-Gewicht 0
   Wert und Rang weiter, mit „nur Info, zählt nicht im Score" (Easys
   Wahl, Variante b aus der Diagnose); **PR 3** (Evaluation: Gesamtrück-
   blick zählt verschiedene Regeln nie zusammen, Methodenwechsel-Hinweis
   am ersten Monat je neuer Regel) ist **PR #85**, gebaut, Merge bei
   Easy. Fristen zum echten Dezember-Test: §3.
1. ~~**Ranking-Verlauf**~~ — **entschieden 03.11.2026 (Easy): NICHT
   bauen.** Grund: geringer Nutzen für eine Kaufentscheidung, und der
   Verlauf mischt seit November zwei Score-Regeln (US 50/50 bis Oktober,
   100/0 ab November). Rückweg: jederzeit neu aufnehmen; die harte Grenze
   bliebe dann dieselbe (keine Rendite, keine Trefferquote, keine
   Performance-Kurve). Siehe §10.
2. **Risikogesteuerte Varianten** (Daniel & Moskowitz 2016) — in `README`
   bereits als „dokumentiert, aber erst v1" geführt.
3. **Reparatur-Agent, weitere Fehlerklassen** — offen, Easys Entscheid
   (siehe §3/§4 Punkt 3). Die vorherige Diagnose hat sechs Kandidaten
   benannt; keiner davon ist ohne Weiteres so eng wie Datumsformat-Drift.
4. **Sektor-Verteilung auf der Evaluation-Seite** (Variante c aus §4
   Punkt 11) — zurückgestellt, kein akuter Bedarf. Der reine Anzeige-
   Hinweis (Variante b) ist seit PR #72 gebaut; eine dauerhafte Sektor-
   Historie bräuchte dagegen ein additives Schema in
   `data/evaluation/*.json` und wäre damit Manual-Merge.

**Selbstwartungs-Stufenplan** (Easys Richtung vom 09.08. — „ein Tool, das
sich selbst wartet"; die Maschine arbeitet, Easy behält den Ein-Tipp-Veto):

| Stufe | Was | Stand |
|---|---|---|
| 0 | Totmannschalter (`waechter.yml`) | **gebaut** |
| 1 | Vertragstests je Fremdquelle, werktags im Fenster 25.–31. | **gebaut, jetzt einmal real durchlaufen** (25.–31.08.2026, siehe §4 Punkt 1/2) |
| 2a | Zweite Kursquelle **DE** mit Vergleichsgatter | **gebaut, scharf seit 31.08.** — realer Vorfall und Diagnose siehe §4 Punkt 2 |
| 2b | Zweite Kursquelle **US** (S&P-500-UCITS-Bestandslisten) | **gebaut, scharf seit 31.08.** (#35, MANUAL-MERGE, 14.08.). Anker = Bestands-Stichtag selbst, Toleranz 0,25 %, Zulass 3 Abweichler, Quelle SXR8 primär mit IUSA als dokumentiertem Ausweich, Split-Ausnahme mit Anti-Schlupfloch-Test, Ticker-Mapping Klassen-Titel „.“→„-“ |
| 3 | Reparatur-Agent: liest rote Läufe, öffnet einen PR, CI beweist, Easy merged | **erste Ausbaustufe gebaut** (#49, 08.09.) — schmal auf Datumsformat-Drift bei iShares begrenzt, siehe §4 Punkt 3. Weitere Fehlerklassen: offen, Easys Entscheid. |

**Weitere Wächter, außerhalb dieses Stufenplans** (der Stufenplan oben
ist Daten-/Vertragsintegrität; diese hier beobachten den Betrieb/Prozess
selbst — dasselbe „melden, nie handeln"-Muster wie Stufe 0):

| Wächter | Beobachtet | Schwelle | PR |
|---|---|---|---|
| Doku-Wächter (`handover_waechter.py`) | SESSION_HANDOVER.md-Rückstand gegenüber gemergten PRs | 4 ungepflegte PRs | #59 |
| PR-Verwaisungs-Wächter (`pr_verwaisung_waechter.py`) | offene PRs ohne Lebenszeichen | 5 Werktage seit letztem Kontakt | #60 (GraphQL-Fix: #61) |
| Push-Zustellungs-Wächter (`push_zustellung_waechter.py`) | fehlgeschlagene ntfy-Versandversuche (Log-Scan über `gh api`/`gh run view --log`, bewusst ohne Datei-Persistenz) | ≥ 1 Fehlschlag in 7 Tagen | #65 |
| Lauf-Zeitversatz-Beobachtung (`lauf_zeitversatz_waechter.py`) | Startverzug von `lauf.yml` gegenüber 21:45 UTC | > 4 Std. bei mind. einem der letzten 10 Läufe | #65 |
| Split-Wächter (`split_waechter.py`) | Tagesreihe (`bundle.adjusted`) eines Titels mit Naht nahe einem Split-Verhältnis — vermutlich noch nicht nachbereinigte Split-Vorgeschichte (siehe §4 Punkt 9) | Verhältnis innerhalb ±3 % von 2, 3, 4, 5 oder 10 (bewusst ohne 3:2) | #70 |
| Daten-Abdeckungs-Wächter (`datenabdeckung_waechter.py`) | Kursabruf und iShares-Kursvergleich (Git-Historie von `data/status.json`), Universum-Alter und Sektor-Abdeckung — Auftrag 1 des Automatisierungsplans vom 24.10.2026, siehe §4 Punkt 14 | 24h/7-Tage-Fenster, ≥ 2 Beobachtungen, 180 Tage Universum-Alter — alle als Startwert markiert | #74 |
| Wiedervorlagen-Wächter (`wiedervorlagen_waechter.py`) | §3 von SESSION_HANDOVER.md (`faellig`-Kommentare) — meldet "Heute fällig"/"Überfällig", Auftrag 2 desselben Plans, siehe §4 Punkt 14 | Erinnerung höchstens 1×/Woche (Tag 1, 8, 15, …), zustandslos aus dem Datum berechnet | #76 |

Alle sieben: lautlos bzw. ohne Sirene (ntfy-Priorität „min"/„default", nie
„high"), nur Lese-Rechte, je ein statischer Quelltext-Test gegen jeden
schreibenden Aufruf. Fünf laufen als eigener wöchentlicher Cron
(montags, teils 07:30 UTC gemeinsam mit dem Totmannschalter); der
Daten-Abdeckungs-Wächter läuft täglich (06:37 UTC, siehe PR #74), der
Wiedervorlagen-Wächter ebenfalls täglich (06:52 UTC, siehe PR #76); der
Split-Wächter ist der **einzige, der nicht als eigener Workflow läuft**
— er braucht die vollständige Tagesreihe (`bundle.adjusted`), die nur
während des eigentlichen Stichtags-Laufs existiert und nirgends
persistiert wird, und ist deshalb direkt in `run.py` eingehängt
(fail-soft, doppelt abgesichert, siehe §4 Punkt 9). Der Doku-Wächter hat
sich bereits real bewährt — siehe Dokument-Kopf.

*Herleitung der Stufe-2b-Werte* (unverändert seit der letzten Pflege):
Die Wegwerf-Messung aus #31 (drei Läufe, 10.–12.08.) verglich dieselbe
Titelmenge gegen zwei Anker — Anker A (Bestands-Stichtag selbst) ergab
Max 0,002 %/0,004 %, Anker B (US-Vortag) Median 1,04 %/1,33 % mit
Ausreißern bis 28 %, ein Faktor-250-Unterschied; die 0,25 % Toleranz
folgen aus der Rundung der zweistelligen Kurs-Spalte, Zulass 3 übernimmt
das bewährte Muster des DE-Gatters, das Ticker-Mapping schließt die in
#28 offen benannte Lücke bei Klassen-Titeln (`BRK.B`, `BF.B`). Neu
gegenüber der Messung: die **Split-Ausnahme** (ein Titel zählt nur dann
als „Split erkannt, kein Befund" statt als Abweichler, wenn
Kursverhältnis *und* Yahoo-Split-Kalender zusammenpassen).

*Im Zeitfenster 14.–16.08.* liefen daneben drei kleine, unabhängige
Frontend-PRs (Details in §7.7): Live-Punkt-Puls auf Glow (#36), ein
Regressionstest für Kurs-Beschriftung/Änderungszeile (#37), Ellipsis-
Vorsorge (#38). Keiner berührt Kursvergleich oder eine Rechengröße.

*Im Zeitfenster 16.–22.08.* (nach der letzten Handover-Pflege, jetzt
nachgezogen, siehe §2): Testkontext-Härtung (#40), zwei Kartentext-/
Anzeige-PRs (#41, #42), Markt-Tönung (#43) — alle SELF-MERGE, keiner
berührt Score, Ranking oder eine Datenquelle.

*Ende August/Anfang September:* die Evaluation-Seite (#44, MANUAL — neues
additives Schema `data/evaluation/`), ein UI-Fix an der Neuberechnen-
Anzeige (#45), und der komplette Konfluenz-Ausbau — Push (#46), Historie
(#47), manuelle Nachträge mit Quelle-Kennzeichnung (#48) — sowie die
erste Reparatur-Agent-Ausbaustufe (#49). Details in §2.

Die harte Grenze der Stufe 3 gilt **unverändert weiter**: Der Agent öffnet
PRs, die CI beweist, **Easy merged**. Kein Auto-Merge agentengeschriebener
Fixes — im Code erzwungen (siehe §4 Punkt 3), nicht nur zugesagt.

Nicht automatisieren, ausdrücklich: Auto-Merge agentengeschriebener
Fixes, Selbstreparatur des Universums (default-deny ist das Kronjuwel),
eigenmächtige Abhängigkeits-Sprünge.

**Was bewusst NICHT kommt** (steht so auf der Methodik-Seite und im README):
keine Sammlung, keine Registry, kein Backtesting, keine Trefferquoten, keine
Kursziele, kein Long-Short, kein Intraday, keine Zutat ohne Quelle, keine
Watchlist, keine KI-Kommentare, keine Neuberechnung des Rankings auf
Knopfdruck.

---

## 7. Architektur-Anker

Das sind die Stellen, an denen man beim Ändern zweimal nachdenkt.

### 7.1 Tragendes Prinzip

**Literaturtreue ersetzt Validierung.** Jede Score-Zutat hat eine
Primärquelle — im Code-Kommentar *und* auf der Methodik-Seite, beide aus
`src/momentum/sources.py` erzeugt. Die Tests beweisen „rechnet exakt die
dokumentierte Formel", niemals „trifft es". `config.py` bricht beim Import
ab, wenn eine gewichtete Komponente keinen Beleg hat
(`_check_weights_are_backed`).

### 7.2 Die Gatter

| Gatter | Regel | Ort |
|---|---|---|
| **Universum default-deny** | Gerechnet wird nur mit `# STATUS: VERIFIED`. Der Riegel greift **vor** dem Datenabruf. | `src/momentum/universe.py` |
| **Veraltung** | Bestands-Stichtag älter als **10 Handelstage** → Abbruch | `tools/build_universe.py:194` (`MAX_ALTER_HANDELSTAGE`) |
| **Anzahl (Vertauschungsschutz)** | DAX 38–42, MDAX 48–52, TecDAX 28–32 — überlappungsfrei | `tools/build_universe.py:183` (`ANZAHL_ERWARTET`) |
| **Gesamtzahl je Markt** | US 495–510, DE 95–125 | `tools/build_universe.py:165` (`ERWARTET`) |
| **Mindestabdeckung** | < 90 % verwertbare Kurse → kein Ranking, lauter Abbruch | `config.py:71` (`MIN_UNIVERSE_COVERAGE`) |
| **Handelbarkeit** | Median-Tagesumsatz ≥ 5 Mio. über 3 Monate — kein eigener Faktor im Score, verändert aber die Grundgesamtheit, aus der die Perzentil-Ränge gebildet werden (seit PR #56 so auf der Methodik-Seite präzisiert) | `config.py:46` |
| **Kursvergleich DE/US** | ≤ 3 Abweichler über Toleranz, sonst Stichtag verweigert; < 80 % vergleichbar → „entfällt", kein Bruch | `src/momentum/kursvergleich.py` (`ZULASS_ABWEICHLER`, `MIN_VERGLEICHSQUOTE`), `kursvergleich_us.py` — siehe §4 Punkt 2 für den realen Fall |
| **Einfrierung** | Eine geschriebene Ranking-Datei wird **nie** überschrieben | `ranking.write_ranking` |

**Ein Ranking korrigieren** geht nur auf einem Weg: die Datei unter
`data/rankings/` von Hand löschen. Es gibt keinen Schalter — sonst wäre die
Einfrierung keine.

### 7.3 Fail-soft-Regeln

Überall gilt: **fail-soft, aber niemals still.** Grauer Punkt, „—",
sichtbarer Hinweis — nie ein erfundener Ersatzwert, nie ein kaputtes Bild.
Konkret:

- Zinsquelle weg → Kriterium rechnet ohne Abzug, Box sagt es (`render.ZINS_FEHLT_HINWEIS`).
- Elliott-Daten weg → Momentum-Hälfte rendert voll, Hinweis daneben.
- Meta-Datei fehlt → Karten zeigen „—", Lauf läuft weiter.
- Kurs-Dienst weg → grauer Punkt, Zeitstempel bleibt stehen.
- Kursvergleich nicht durchführbar (< 80 % vergleichbar) → „entfällt",
  Lauf läuft normal weiter, Report sagt es sichtbar. **Real bewiesen** am
  31.08.2026 (§4 Punkt 2): der Vergleich fehlte, der Lauf blieb grün,
  nichts wurde stillschweigend als „geprüft, keine Abweichung" verkauft.

Ausnahme: alles, was ein **Ranking** verfälschen könnte, bricht laut ab.
Anzeige darf weich ausfallen, Rechnung nicht.

### 7.4 Merge-Klassen

| Klasse | Wer merged | Wann |
|---|---|---|
| **MANUAL-MERGE** | Easy | Score-/Warnlogik, Universums-Logik, Token-Mechanik, neue externe Datenquelle, additive Schema-Felder, **neue Workflow-Rechte/automatisierte PR-Erzeugung** (seit #49 explizit dazugehörig, unabhängig vom Umfang) |
| **SELF-MERGE bei grünem CI** | Claude, nach zwei grünen `tests`-Läufen und ohne offene Kommentare | rein dekoratives Frontend, Bug-Fixes ohne Logikänderung, Doku, reine Testinfrastruktur ohne neue Rechte |

Jeder PR nennt seine Klasse im Titel und den **Rückweg** (`git revert`) im
Text. PRs werden als Entwurf geöffnet; bei SELF-MERGE setzt Claude sie vor
dem Mergen auf „bereit".

### 7.5 Quellen (extern verifiziert)

**Universum**

| Markt | Quelle | Kennung |
|---|---|---|
| USA | Wikipedia (en) *List of S&P 500 companies* | — |
| DE | iShares-Bestandslisten, physisch replizierend | DAX = **251464** (EXS1, 40 Aktien-Zeilen), MDAX = **251845** (EXS3, 50), TecDAX = **251975** (EXS2, 30) — verifiziert 02.08.2026 |

**Indizes (Trend-Ampel)** — beide **Performance-Indizes**, sonst wäre es ein
Vergleich zweier verschiedener Dinge:

- USA: `^SP500TR` (S&P 500 Total Return) — seit #16, davor `^GSPC`
- DE: `^GDAXI` (DAX)

**Geldmarktsätze** (`src/momentum/riskfree.py`):

- USD: `^IRX` (13-Wochen-T-Bill) über dieselbe Kursquelle wie die Indizes
- EUR: €STR aus dem EZB-Datenportal, schlüssellos:
  `https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?startPeriod={start}&format=csvdata`
  CSV wird über die **Kopfzeile** gelesen (`TIME_PERIOD`, `OBS_VALUE`), nie
  über die Spaltenposition.
- Beides ist eine **Näherung**: arithmetisches Tagesmittel über das
  Zwölf-Monats-Fenster, einmal abgezogen — kein Zinseszins. So benannt im
  Code und auf der Methodik-Seite. **Erste echte Produktionszahlen** siehe
  §1 (US +3,67 %, DE +1,98 %).

**Kursvergleich-Zweitquellen** (Stufe 2a/2b — unabhängige Kontrolle,
**kein Bestandteil des Scores**, siehe §7.2; seit PR #52 auch auf der
Methodik-Seite erklärt — damit ist der zuvor an dieser Stelle selbst
gemeldete Doku-Rückstand geschlossen, siehe §10):

| Markt | Quelle | Toleranz | Zulass. Abweichler | Mindest-Vergleichsquote |
|---|---|---|---|---|
| DE | iShares-Bestandslisten, Spalte „Kurs" (BlackRock-Bewertungskurs; DAX/MDAX/TecDAX = EXS1/EXS3/EXS2) | 1,0 % | 3 | 80 % |
| US | iShares S&P-500-UCITS-Bestandslisten, Spalte „Kurs" (SXR8 primär, IUSA als dokumentierter Ausweich) | 0,25 % | 3 | 80 % |

Werte importiert aus `kursvergleich.py`/`kursvergleich_us.py` (`TOLERANZ`,
`ZULASS_ABWEICHLER`, `MIN_VERGLEICHSQUOTE`) — sowohl hier als auch auf der
Methodik-Seite, damit keine der beiden Stellen von den tatsächlichen
Gattern abweichen kann.

**Literatur** — vollständig in `src/momentum/sources.py`, wörtlich auf der
Methodik-Seite: Jegadeesh & Titman (1993), Jegadeesh (1990), George & Hwang
(2004), Rouwenhorst (1998), Moskowitz/Ooi/Pedersen (2012), Daniel &
Moskowitz (2016), Jegadeesh & Titman (2023), Fama & French (2012), Asness
(2011), Chui/Titman/Wei (2010). **Seit PR #84** zusätzlich die
Begründung der Gewichtung je Markt (`sources.WEIGHTING_SOURCES`, keine
Score-Zutat, deshalb nicht in `SCORE_COMPONENT_SOURCES`): Hou/Xue/Zhang
(2020), Barroso & Wang (Arbeitspapier 2021, nicht begutachtet), IMC
(2026, Vermögensverwalter, nicht begutachtet), Burghof & Prothmann (2009),
Franz & Regele (2016) — Kennzeichnung „nicht begutachtet" steht im Feld
`journal` und erscheint so auf der Seite. Prüfstand je Quelle: §4 Punkt 8.

### 7.6 Die Score-Formel

**Seit 01.11.2026 je Markt und je Ranking-Monat (Gewichts-Fahrplan):**
`Score 0–100 = 100 × (w₁ × Perzentil(12-1) + w₂ × Perzentil(52W-Nähe))`,
mit (w₁, w₂) aus `config.Market.gewichts_fahrplan`, gewählt **rein nach
dem Monat des Stichtags** (`Market.gewichte_fuer`, aufgerufen in
`ranking.build_ranking`) — nie nach dem Lauf-Datum:

| Markt | Ranking-Monat | w₁ (12-1) | w₂ (52W) |
|---|---|---|---|
| USA | bis einschl. 2026-10 | 0,5 | 0,5 |
| USA | ab 2026-11 | 1,0 | 0,0 |
| Deutschland | immer | 0,5 | 0,5 |

Die 50/50-Einträge sind die Konstanten `WEIGHT_MOMENTUM_12_1`/
`WEIGHT_HIGH_52W` selbst (dieselben Gleitkommazahlen wie vorher; DE-
Ranglisten per Hash byte-genau gleich, `tests/unit/test_gewichts_fahrplan.py`).
Jede Ranking-Datei trägt die tatsächlich verwendeten Gewichte in
`methode.gewicht_momentum_12_1`/`gewicht_high_52w`. Begründung: §4 Punkt 8.
Die Anzeige folgt seit PR #84: die Methodik-Seite erzeugt Gewichte und
Formeln je Markt **aus dem Fahrplan** (nicht aus `WEIGHT_*`), mit
Monatsangabe für beide US-Regeln — sie stimmt so an jedem Tag, vor und
nach dem 30.11.; die Karte liest die Gewichte aus `ranking["methode"]`
(siehe §7.7).

Bis 31.10.2026 (und für DE weiterhin) also:
`Score 0–100 = 50 × Perzentil(12-1) + 50 × Perzentil(52W-Nähe)`,
Perzentile **immer nur innerhalb eines Marktes**, Gleichstände deterministisch
(höherer Score zuerst, dann Ticker A→Z; seit PR #57 auf der Methodik-Seite
explizit als rein technischer Tie-Breaker ohne inhaltliche Bedeutung
ausgewiesen). Beide Teil-Ränge (Momentum-Rang X von N, 52W-Rang Y von N,
N = `abdeckung.bewertet`) stehen sichtbar auf jeder Karte — unverändert
seit #8, zuletzt gegen den realen VLO-Fall aus dem externen
Qualitäts-Check (Mitte September, siehe §2) nachgerechnet: Score 97,9,
Momentum-Rang 22/497, 52W-Rang 1/497, deckungsgleich mit
`data/rankings/us_2026-08.json`.

Die Trend-Ampel ist **reine Anzeige** und rührt Score, Perzentile und
Rangfolge nie an — festgehalten in
`tests/unit/test_trend_ueberschuss.py::test_der_zins_ruehrt_score_und_rangfolge_nicht_an`.

### 7.7 Anzeige

- **Gewichte auf der Karte (seit PR #84):** gelesen aus
  `ranking["methode"]`, nie aus `config.py` — das Oktober-Ranking zeigt
  im November weiter 50/50. Ist `gewicht_high_52w == 0`, bleiben 52W-Wert
  und 52W-Rang sichtbar, darunter `p.card-ft.card-ft--nur-info`
  „52W-Hoch-Nähe: nur Info, zählt nicht im Score." Bei 0.5/0.5 oder
  fehlendem Feld: Karte exakt wie vorher (byte-gleich belegt; alle
  eingefrorenen Dateien Juli–Oktober tragen das Feld). Die
  390-px-Testseite trägt dafür für die USA 100/0.
- **Gesamtrückblick auf der Evaluation-Seite (seit PR #85):** gruppiert
  je Markt nach den tatsächlichen Gewichten des zugehörigen Rankings
  (`render.py::_eval_regel`, liest `data/rankings/{markt}_{jahr}-
  {monat}.json` → `methode.gewicht_*`, NICHT `config.py` — dasselbe
  Prinzip wie die Karte seit PR #84). Zuordnung Evaluation→Ranking ist
  code-belegt, nicht geraten: `ausgewerteter_monat` ist wortgleich der
  Ranking-Monat (`evaluation.build_evaluation()` setzt es direkt aus
  `prev_ranking["ranking_monat"]`), beide Dateien teilen denselben Namen.
  Kennt ein Markt nur EINE Regel (heute überall, DE dauerhaft): Anzeige
  byte-gleich wie vor PR #85. Mehrere Regeln: je Regel ein eigener Block
  ("Rankings Juli bis Oktober 2026 (50/50)" / "ab Ranking November 2026
  (nur 12-1-Momentum)"), Monatsrückblick/Details tragen eine Kennzeichnung,
  der erste Monat je neuer Regel einen "Methodenwechsel"-Hinweis
  (`.card-ft`, keine neue CSS-Klasse). Fehlt die Ranking-Datei/das Feld:
  fail-soft "Regel unbekannt", nie mit einer bekannten Gruppe
  zusammengezählt. `render_evaluation()` nimmt dafür ein injizierbares
  `ranking_root` (Test-Naht, Vorgabe das echte `data/rankings/`) — kein
  Unit-Test liest dadurch je versehentlich echte Repo-Daten mit.
- **PWA-Standalone:** kein Browser-Zurück. Jede Unterseite braucht einen
  sichtbaren `← Zurück`-Link, jede Tippfläche ≥ 44 px
  (`max(44px, 2.75rem)`).
- **390 px** ist die Messbreite (iPhone). Kein seitliches Scrollen, kein
  Element über dem Rand — gemessen im echten Browser, nicht geschätzt.
  Bewusst **keine** `<table>` irgendwo im Projekt — feste Spalten brechen
  bei langen Namen/großer Schrift seitwärts aus (gelernt bei der
  Evaluation-Seite, #44); umbrechende Zeilen-/Karten-Listen stattdessen.
- **Farben sind Semantik:** `--grn` nur positiv, `--red` nur negativ,
  `--ora` nur Warnlage, `--disc` **ausschließlich** Ehrlichkeits-Aussagen
  (erlaubt an `.disc-title`, `.card-ft`, `.konf-regel`,
  `.konf-hist-karte--rekonstruiert`/`.konf-hist-badge` seit #48 — die
  Liste wächst nur um Stellen, die wirklich eine Einschränkung
  aussprechen). Zwei neue, ausdrücklich NICHT in dieser Palette liegende
  Variablen seit #43: `--tint-us-rgb`/`--tint-de-rgb` (Kartentönung,
  siehe unten) sowie seit #44 `--neu`/`--unk` (Evaluation: neutral/
  unbekannt, kollidieren mit keiner Ampel-Farbe).
- **Konfluenz-Seite:** zwei Werkzeuge nebeneinander. **Kein gemeinsamer
  Score, keine Wahrscheinlichkeit, keine Rangfolge der Treffer.** Treffer
  stehen alphabetisch. Seit #47 zusätzlich eine **Historie-Sektion**
  unterhalb der beiden Top-5-Listen: alle je gesehenen Treffer,
  neuester zuerst, serverseitig aus `konfluenz_historie.json` gerendert
  (`render.py::render_konfluenz`, nicht mehr nur ein leeres Gerüst).
  Manuell nachgetragene Einträge (seit #48) tragen sichtbar einen
  „Rekonstruiert"-Badge + Erklärsatz + `--disc`-Rahmen — nie mit
  automatisch erfassten vermischt.
- **Markt-Tönung der Ranking-Karten (seit #43):** jede Karte trägt
  `card--us`/`card--de` und eine sehr blasse Hintergrund-Tönung
  (`--tint-alpha: .16`, kühles Blau-Grau vs. warmes Sand-Gold) — rein zur
  Wiedererkennung, keine Signalfarbe. Ampel und Pos/Neg-Werte liegen auf
  eigenen, deckenden Flächen und sind von der Tönung nicht erreichbar.
  Kontrast rechnerisch geprüft (`--txt-dim` bleibt ≥ 5,4:1, weiterhin
  über AA), Beleg im PR-Text.
- **Eingefrorener Stichtag-Kurs auf der Karte (seit #41/#42):** ein
  eigener `--disc`-Satz unter der Karte, getrennt vom live gepollten
  Kurs im `.metric-box`-Kästchen — „Kurs vom {Datum}, **eingefroren** —
  Basis für dieses Ranking: **{Betrag}**." Betrag und „eingefroren"
  fett (#42).
- **Evaluation-Seite (seit #44):** Farbbalken (positiv/neutral/negativ/
  unbekannt) je Monat und kumuliert, Pflicht-Hinweistext gegen
  Fehldeutung als Erfolgsnachweis (`EVALUATION_HINWEIS`, `render.py`) —
  bewusst kein „Erfolgsrate"/„Trefferquote"-Vokabular, nur Zähler und
  Kurse. Eigenes, additives Schema `data/evaluation/{markt}_{jjjj-mm}.json`,
  nie überschrieben, gleiches Einfrierungsprinzip wie `data/rankings/`.
  Seit #55 zusätzlich, je Monat: Index-Benchmark-Vergleich (schema 1→2,
  `index_vergleich`-Feld) — Top-5-Rendite (gleichgewichtetes Mittel)
  neben Index-Rendite und Differenz in Prozentpunkten (`de_pp()`),
  dieselbe `index_series` wie die Trend-Ampel, fail-soft bei Datenlücke
  („Index-Vergleich nicht verfügbar"). Der bestehende Juli-Eintrag bleibt
  bewusst auf schema 1 (kein rückwirkendes Nachtragen) — Begründung:
  DE/Juli endet am 31.08.2026, demselben Tag mit dem untertägigen
  Kursvorfall (siehe §4 Punkt 2), ein rückwirkender Indexwert desselben
  Tages trüge denselben Makel.
- **Kopfzeile bei abweichenden Markt-Stichtagen (seit #54):** zeigt bei
  gleichem US-/DE-Stichtag weiterhin „Ranking vom {Datum}"; weichen beide
  ab, „Ranking je Markt: USA {Datum} · Deutschland {Datum}" — Reihenfolge
  immer US zuerst (deterministisch, nicht nach Datum). Ersetzt das alte,
  über `max()` gebildete Einzeldatum, das den realen US/DE-Unterschied
  (28.08./31.08.) verschleierte.
- **Alles rendert aus `render.py`.** Sichtbar wird eine Änderung erst, wenn
  der nächste `Momentum-Lauf` `docs/index.html` neu erzeugt.
  `docs/index.html` wird **niemals** von Hand gelöscht und neu gebaut — dort
  steht die echte, ausgelieferte Rangliste.
- **Live-Punkt (Stand 14.08., #36):** pulsiert über `box-shadow`, nicht
  mehr über `opacity` — die alte Fassung war auf dunklem Grund ohne
  Schein praktisch unsichtbar. `prefers-reduced-motion` stoppt die
  Animation, lässt den Punkt aber mit stehendem Glow sichtbar.
- **Tagesveränderungs-Zeile (`.m-chg`, Stand 16.08., #37/#38):** eigenes
  Element, Geschwister von `.m-val`/`.m-lbl`, trägt seit #38 dasselbe
  `overflow: hidden` + `text-overflow: ellipsis` — Vorsorge gegen sehr
  lange Werte.
- **Neuberechnen-Sekundenanzeige (seit #45):** eigener, vom Status-Poll
  entkoppelter Ticker (`docs/app.js`, `tickAnzeigen`) — zählt gleichmäßig
  im Sekundentakt statt sprunghaft im Poll-Abstand.

### 7.8 Geschützte Zonen (Schutz-Sperre-AMPEL, Auftrag 3 der Automatisierung vom 24.10.2026, PR #77, auf Ampel umgestellt in PR #78)

**Die einzige Quelle ist der Code** (`src/momentum/schutz_sperre.py`,
`GESCHUETZTE_DATEIEN`/`GESCHUETZTE_ORDNER`/`GESCHUETZTE_SYMBOLE`) —
diese Liste hier ist eine Abschrift zum schnellen Nachschlagen, kein
zweiter, womöglich abweichender Ort.

**Ganze Datei geschützt:** `scoring.py`, `evaluation.py`, `universe.py`
(Default-Deny-Gatter, siehe §8 „Kronjuwel"), `kursvergleich.py`,
`kursvergleich_us.py` (Vergleichsgatter, kann `RankingNotPossible`
auslösen), `data/konfluenz_historie.json`, `test_freeze.py`,
`test_scoring_values.py`, `test_konfluenz_python.py` (Golden-Tests),
`schutz_sperre.py` + seine Tests (Selbstschutz) — sowie **jeder Pfad**
unter `data/rankings/`, `data/evaluation/`, `.github/workflows/`.
CODEOWNERS existiert in diesem Repo nicht.

**Nur bestimmte Namen geschützt (AST-Vergleich Basis gegen Kopf):**
`config.py` (`WEIGHT_MOMENTUM_12_1`, `WEIGHT_HIGH_52W`, `SCORE_SCALE`,
`MOMENTUM_LOOKBACK_MONTHS`, `MOMENTUM_SKIP_MONTHS`,
`HIGH_52W_WINDOW_DAYS`, `LIQUIDITY_MIN_MEDIAN_TURNOVER`,
`LIQUIDITY_WINDOW_MONTHS`, `MIN_UNIVERSE_COVERAGE`, `TOP_N`,
`HISTORY_DAYS`, `Market`, `MARKETS`, `_check_weights_are_backed`, seit
PR #83 außerdem `GewichtsEintrag`, `FAHRPLAN_BEGINN`,
`_pruefe_gewichtspaar` — die Fahrplan-Werte stehen in `MARKETS`, die
Auswahl `gewichte_fuer` in `Market`, Form und Prüfung in den drei
Hilfen; siehe §5 Punkt 3);
`ranking.py` (`is_last_weekday_of_month`, `due_months`, `resolve_asof`,
`_juengster_werktag`, `zu_frueh_fuer_stichtag`, `median_turnover`,
`build_ranking`); `konfluenz.py` (`elliott_long`, `konfluenz`,
`neue_konfluenz_treffer`); `ishares.py` (`MAX_ALTER_HANDELSTAGE`);
`run.py` (`process_market`, `_kursvergleich`, `_download_window`,
`main`) — diese vier `run.py`-Funktionen sind eine Ergänzung über die
ursprüngliche Vorgabe hinaus (real belegt durch PR #70, deren
zwei-Zeilen-Ergänzung mitten in `process_market` ohne diese Ergänzung
spurlos durchgelaufen wäre — siehe PR #77 für den Rückblick auf
#67–#76).

**Keine Freigabe mehr, seit PR #78 — bewusst entfernt, kein Ersatzweg:**
die ursprüngliche Label-Freigabe (`freigabe-easy` von `easywebb911`,
nach dem letzten Push) wurde vollständig entfernt. Grund (siehe §4
Punkt 14, Entscheidung (5)): der Code dieses Repos — und jeder
künftige Agent — handelt in der GitHub-API selbst als `easywebb911`,
eine Freigabe "von easywebb911" wäre also vom selben Agenten fälschbar,
der sie prüft. Der Check zeigt seitdem nur noch GRÜN (keine geschützte
Zone berührt) oder ROT (geschützte Zone berührt, **Easys Entscheidung
nötig** — nicht "verboten"). Ein PR-Titel, der mit `[Wächter]` beginnt
UND eine geschützte Zone berührt, bleibt immer rot und bekommt
zusätzlich eine eigene Hinweis-Zeile in der Check-Ausgabe.

**Kein Ruleset dahinter, ausdrücklich — unverändert seit PR #77:** ein
roter Check blockiert ohne das Main-Schutz-Ruleset (bewusst disabled,
siehe §4 Punkt 14) KEINEN manuellen Merge. **Anders als ursprünglich in
PR #77 vorgesehen, entsteht daraus auch KEINE spätere harte Grenze:**
Auftrag 5 (geplante Agenten) wurde umdefiniert (§4 Punkt 14,
Entscheidung (4)) — Agenten mergen grundsätzlich nie, mit oder ohne
grüne Ampel. Diese Ampel ist und bleibt eine Melde-, keine
Durchsetzungs-Instanz; sie hilft Easy beim Hinsehen, ersetzt aber nie
Easys eigene Entscheidung.

---

## 8. Lessons (teuer bezahlt)

1. **`docs/index.html` nie regenerieren.** Am 03.08. habe ich sie aus
   Gewohnheit gelöscht und neu gebaut — und dabei die echte, ausgelieferte
   Rangliste vom 31.07. durch einen Platzhalter ersetzt. Aufgefallen ist es
   nur am Diff-Umfang (466 Löschungen statt ~24). **Immer den Diff-Umfang
   gegen die Erwartung prüfen.**
2. **Ein Gatter muss die Sache prüfen, nicht ein Symptom.** Das
   Fondsnamen-Gatter für die DE-Bestandslisten scheiterte daran, dass die
   deutschen CSVs gar keinen Fondsnamen führen. Die Anzahl der Aktien-Zeilen
   ist die Eigenschaft, die eine vertauschte Datei wirklich verrät.
3. **Fehlende Neuaufnahme ist tückischer als ein Parse-Fehler — UND: der
   allererste Lauf ist selbst schon ein scharfer Test.** Ein Ticker, den
   die Liste nicht enthält, kann in keiner Kursprüfung durchfallen. Nur
   ein Stichtag deckt so etwas auf — deshalb die ETF-Listen mit Stichtag
   statt Wikipedia. Genau ein Datumsformat („31.Juli2026", ganz ohne
   Trenner vor dem Jahr) hat trotzdem den allerersten `lauf.yml`-Lauf
   (02.08.2026) scheitern lassen — belegt in `ishares.py` und in der
   Actions-Historie (Run 1, `conclusion: failure`, kein „Lauf 1"-Commit).
   Seither tolerant gehärtet; die zweite Ausbaustufe dieser Härtung ist
   jetzt teilautomatisiert (Reparatur-Agent Stufe 3, #49).
4. **`^…$` ist in Python nicht `\A…\Z`.** `^[-_A-Za-z0-9]{1,64}$` hätte
   `"thema\n"` durchgelassen — genau den Fehler, der den ntfy-Push mit
   HTTP 400 killte. In `notify.py` steht deshalb `\A…\Z`.
5. **Tests, die nach draußen telefonieren, sind keine Tests.** Zweimal rot
   auf CI, weil die Browser-Tests lokal (Egress-Sperre) grün waren und auf
   dem Runner den echten Dienst erreichten. Behoben durch echtes
   Default-Deny (#40, 16./17.08.) — die frühere Blockliste war der
   erste, unvollständige Schritt dahin.
6. **Playwright ruft eine Funktion auf, die als letzter Ausdruck eines
   Skripts steht.** Das erzeugte einen Phantom-Aufruf und verschob jede
   vorbereitete Antwort um eins. Stub-Skripte enden deshalb auf
   `window.__geruestet = true;`.
7. **Ein Selektor ohne Geltungsbereich trifft die falsche Karte.**
   `document.querySelector('[data-quote="X"]')` fand denselben Ticker in
   beiden Märkten. Lookups laufen jetzt innerhalb der Markt-Sektion.
8. **Zwei Ausfallgründe brauchen zwei Sätze.** „Zinsquelle nicht erreichbar"
   wäre für die Juli-Rankings falsch gewesen — die haben nie eine gesucht.
   Bequemlichkeit beim Formulieren ist hier eine Unwahrheit.
9. **Ein falscher Feldname sieht aus wie ein kaputtes Feature.** Die
   Konfluenz-Seite zeigte überall „—", weil der Elliott-Score unter
   `score_heuristic` liegt, nicht unter `score`. Das tolerante Lesen hat
   richtig reagiert: nichts geraten.
10. **Das PWA-Homescreen-Symbol cacht den Seiten-CODE getrennt von den
    DATEN.** Ein Live-Befund vom 13.08. beschrieb ein Markup-Problem, das
    im Quelltext längst behoben war (#33) — gemessen wurde die noch nicht
    neu erzeugte `docs/index.html`. „Neu laden" holt per `fetch` nur die
    DATEN, nie den HTML/CSS/JS-CODE — der sitzt im Service-Worker-/
    Homescreen-Cache und wird nur bei echtem Neuaufruf ersetzt.
11. **Ein Betriebszustands-Dokument braucht einen eigenen Anlass, nicht
    nur den nächsten Auftrag, der zufällig danach fragt.** `SESSION_
    HANDOVER.md` stand vom 16.08. bis zum 11.09.2026 (drei Wochen, zehn
    gemergte PRs, ein echter Vertragstest-Vorfall) unverändert und kannte
    nichts davon — obwohl es sich selbst als „die kanonische, allein
    tragfähige Quelle für den Betriebszustand" versteht. Die Lücke ist
    kein Einzelfall auf Vorrat: sie entsteht immer dann, wenn ein Auftrag
    Code ändert, aber keiner explizit die Doku nachzieht. Zum Zeitpunkt
    dieser Formulierung war **kein Automatismus dagegen eingerichtet**
    (wäre selbst ein eigener, zu klärender Auftrag) — hier nur benannt,
    damit die nächste Lücke wenigstens auffällt. Das wiederholte sich
    exakt so ein zweites Mal (11.09.–27.09., #51–#57). **Nachtrag
    05.10.2026:** der Automatismus existiert inzwischen (Doku-Wächter,
    PR #59, `SCHWELLE_PRS = 4`) und hat die dritte Lücke
    (27.09.–05.10., #59–#65) real selbst erkannt und gemeldet (Actions-
    Run `37339845773`) — siehe Dokument-Kopf. Lesson 11 ist damit die
    erste Lesson dieses Dokuments, die sich nicht nur beschreibt, sondern
    einmal tatsächlich als behoben beobachten ließ.
12. **Ein Abbruch ohne Ausscheidegründe ist nicht diagnostizierbar.**
    Lauf #94/#95 (31.10.2026) brachen mit „kein Titel mit vollstaendiger
    Historie" ab — die Zähler dafür existierten im Code bereits, wurden
    aber nie ausgegeben. Behoben in PR #80.
13. **Ein Zugriffsweg ist erst belegt, wenn ein echter Lauf ihn benutzt
    hat.** Wächter-Agent, ntfy-Relay-Anbindung und Agenten-Kontrolle
    wurden am 25.10.2026 sauber gebaut und getestet — aber der Agent
    selbst hatte nie GitHub-Zugriff (Task aus einem Chat-Projekt, kein
    Repository-Feld). Sechs Tage lang wurde das Ausbleiben anderen
    Ursachen zugeschrieben (Nutzungslimit 27.10., dann ein Prompt-Zusatz
    am 30.10.), bis der Bericht des Agenten selbst die 403-Meldung
    zeigte. Lehre: bei jedem neuen Agenten zuerst EINEN echten Lauf
    abwarten und dessen Zugriff im Protokoll belegen, bevor darauf
    aufgebaut wird. Siehe §4 Punkt 15, Umstellung 31.10.2026.

---

## 9. Arbeitsweise (steht so seit der ersten Sitzung)

- **Absolute Vorsicht, kein Risiko.** Im Zweifel melden statt machen.
- **Keine fremden Repos lesen, nichts klonen, nichts als Vorlage nehmen** —
  auch nicht die Schwester-Werkzeuge. Fremde Schemata kommen als Befund im
  Auftrag, nicht aus einem fremden Repository.
- **Rate-Limit-Regel:** GitHub-API am Limit → **kein Retry**, sofort melden.
- **Keine Vorschau-Screenshots.** Optik beurteilt Easy am Live-Deploy.
- **Jeder PR** nennt Merge-Klasse und Rückweg und trägt eine kurze
  Exzellenz-Selbstprüfung im Text.

---

## 10. Erledigt (kompakt, nicht mehr offen)

Diese Punkte standen früher auf der Liste und sind abgehakt — sie stehen
hier, damit niemand sie erneut aufmacht.

| Punkt | Erledigt durch | Beleg |
|---|---|---|
| GitHub Pages aktivieren | Easy, 02.08. | Workflow `pages-build-deployment` seit 02.08. 16:11, seither erfolgreiche Deployments bei jedem Push |
| Universum befüllen (beide Märkte) | `Universum aktualisieren`, Lauf 7 | `c97e3f4`, beide Dateien `# STATUS: VERIFIED`, Stand 03.08. |
| Erstes Ranking bilden | `Momentum-Lauf` Lauf 2, 02.08. | `07cbedd`, `data/rankings/*_2026-07.json` |
| `ticker_meta_*.json` erzeugen (Sektor + Name auf den Karten) | Lauf 7 | `universe/ticker_meta_us.json`, `ticker_meta_de.json` |
| `docs/data/top5.json` auf die Seite bringen | Lauf 9 | `e695b54` |
| Tacho, Chart-Verweise, Sektorzeilen, Live-Anker live | Läufe ab 03.08. | `docs/index.html`: 6 × `tta-`, 20 × `stockanalysis.com`, 20 × `data-quote` |
| Konfluenz-Seite ausgeliefert | #14/#15 | `docs/konfluenz.html`, ☰-Eintrag in `docs/index.html` |
| `NTFY_TOPIC` gesetzt | Easy | `NTFY_TOPIC: ***` im Lauf-Protokoll (nur belegte Secrets werden maskiert) |
| Daten-Abdeckungs-Wächter: Schwellen gegen echte Baseline prüfen (Wiedervorlage „ca. 10 Handelstage nach Merge von PR #74“) | Auswertung 12.11.2026 + PR „Regel A“ | Baseline 26.10.–12.11. (Wächter-Läufe nachgespielt): 0 Auslösungen, 0 Fehlalarme, Schwellen belassen. Befund: Prüfung A strukturell nie auswertbar; mit diesem PR behoben. B wie dokumentiert blind. |
| ntfy-Versand nachgewiesen | Probe-Push, Lauf 19 am 08.08. | Lauf 19 `success`; Easy hat den Empfang auf dem Gerät bestätigt. Damit ist der `HTTP 400 topic invalid` aus Lauf 2 (vor #9) abgehakt. |
| Score auf 50/50 vor dem ersten Lauf | #8, gemergt 20:39 UTC, Ranking entstand 20:47 UTC | `f10dad9` vs. `07cbedd` |
| **Zins-Pfad live bewiesen** | Wegwerf-Probe #19, [Lauf 08.08. 23:15 UTC](https://github.com/easywebb911/Momentum-Report/actions/runs/31283577911) | Beide Proben grün. US: Rendite +19,56 %, Geldmarkt +3,71 %, Überschuss +15,86 %. DE: +6,50 %, +1,96 %, +4,54 %. |
| **Korrekturweg + Determinismus live bewiesen** | dieselbe Probe, Teil B | `de_2026-07.json` gelöscht und neu gebaut: bitgleich in allen Feldern; `git status` leer. |
| Wegwerf-Probe wieder entfernt | #20 | `42f5653` |
| Test-Werkzeuge gepinnt, beide erzeugten Seiten in der CI-Frischeprüfung, Zeit-Deckel in allen vier Workflows | #21 | `645401e`, `requirements-dev.txt`, `tests/unit/test_workflow_hygiene.py` |
| Kosmetik: tote CSS-Regel, tote Symbole, verwaiste Fixture, doppeltes Literal, zu breite `window.MR`-Ausfuhr, alte Branches, `.gitignore` | #22 | Suite grün als Nachweis der Verhaltens-Neutralität |
| **Testkontext auf echtes Default-Deny umgestellt** (Hygiene-Backlog Punkt 1) | #40, 16./17.08. | `21a8e7f`; `tests/design/conftest.py` — `kontext.route("**/*", default_deny)`, Allowlist statt Blockliste |
| **Umstellungs-Hinweis (Trend-Ampel ohne Zins-Abzug) verschwunden** | erster Lauf nach dem 31.08.2026-Stichtag | August-Rankings tragen `riskfree_12m`/`ueberschuss_12m` (siehe §1); der ehrliche Zwischenzustand aus der Juli-Übergangsphase betrifft nur noch die dauerhaft eingefrorenen Juli-Dateien |
| **31.08.2026-Monats-Stichtag ausgewertet** | `Momentum-Lauf` (Stichtag-Lauf) | `data/rankings/*_2026-08.json` — Überschuss-Ampel mit echten, plausiblen Zahlen (US ~3,7 %, EUR ~2,0 % — nah an der Wegwerf-Probe vom 08.08.), Kursvergleich beider Märkte `verdikt: "ok"` |
| **Erster Vergleich zweier Monats-Ranglisten (Juli → August)** | 01.09.2026 fällig, real beobachtbar seit dem August-Ranking | US: 4 von 5 Top-5-Plätzen gewechselt (nur VLO blieb). DE: SIE.DE raus, RWE.DE rein, TKA.DE von Rang 4 auf Rang 2. |
| Karten: Markt-Tönung, Stichtag-Kurs, Kartentext-Feinschliff | #41/#42/#43 | siehe §2, §7.7 |
| Neue Seite „Evaluation" | #44 | siehe §2, §7.7 |
| Neuberechnen-Sekundenanzeige entkoppelt | #45 | siehe §2, §7.7 |
| Konfluenz-Push, -Historie, manuelle Nachträge mit `quelle`-Feld | #46/#47/#48 | siehe §1, §2, §7.7 |
| Reparatur-Agent Stufe 3, erste Ausbaustufe | #49 | siehe §1, §2, §4 Punkt 3 |
| `series_roh`/Adj-Close-Kopplung entkoppelt (DE-Kursvergleichspfad gehärtet, Kausalität zum 31.08.-Vorfall bleibt unbewiesen) | #51 | siehe §2, §4 Punkt 2 |
| Kursvergleich-Zweitquellen (Stufe 2a/2b) auf der Methodik-Seite dokumentiert — vormals in §4 Punkt 5/§7.5 selbst gemeldeter Doku-Rückstand geschlossen | #52 | siehe §2, §7.5 |
| Zu früh ausgelösten Lauf gegen untertägigen Monats-Stichtag gehärtet | #53 | siehe §1, §2, §4 Punkt 2 |
| Kopfzeile zeigt beide Stichtage, wenn US/DE tatsächlich abweichen | #54 | siehe §2, §7.7 |
| Index-Benchmark-Vergleich auf der Evaluation-Seite | #55 | siehe §2, §7.7 |
| Handelbarkeits-Filter-Text auf der Methodik-Seite präzisiert (und §7.2-Zeile in diesem Dokument entsprechend korrigiert) | #56 | siehe §2, §7.2 |
| Drei weitere Formulierungsschärfungen auf der Methodik-Seite (Tie-Breaking, Methoden-Anspruch, bereinigte Kurse beim 52W-Hoch) | #57 | siehe §2, §7.6 |
| SESSION_HANDOVER.md auf Stand nach PR #57 gebracht | #58 | siehe §2 |
| Doku-Wächter für SESSION_HANDOVER.md (`SCHWELLE_PRS = 4`) — inzwischen real bewährt (05.10.2026) | #59 | siehe Dokument-Kopf, §2, §6 |
| PR-Verwaisungs-Wächter gebaut; Workflow-Timeout-Abdeckung und Requirements-Vollständigkeit geprüft, keine Lücke gefunden | #60 | siehe §2, §6 |
| PR-Verwaisungs-Wächter: realer GraphQL-Node-Limit-Fehlschlag behoben | #61 | siehe §2 |
| Neue BlackRock-URLs einzeln vom Runner aus verifiziert (Wegwerf-Workflow, inzwischen zurückgebaut, siehe darunter) | #62 | siehe §2, §4 Punkt 6 |
| iShares-Download auf den verifizierten BlackRock-Endpunkt umgestellt | #63 | siehe §2, §4 Punkt 6 |
| ntfy-Nachrichtenkürzung gegen HTTP 500/50001 bei vielen gleichzeitigen Vertragsbrüchen | #64 | siehe §2, §4 Punkt 6 |
| Zwei neue Wächter: ntfy-Zustellung (Log-Scan) und Lauf-Zeitversatz-Beobachtung | #65 | siehe §2, §6 |
| Yahoo-Rate-Limit-Vorfall (Lauf 71, 01.10.) untersucht — fail-soft bestätigt, September-Stichtag per manuellem Nachlauf (Lauf 72) geschrieben | — | siehe §1, §4 Punkt 5 |
| SESSION_HANDOVER.md auf Stand nach PR #65 gebracht | #66 | siehe §2 |
| Wegwerf-Workflow `probe_ishares_neu.yml` (#62) zurückgebaut | #67 | siehe §2, §5 |
| Information Discreteness (Da/Gurun/Warachka 2014) für beide Universen diagnostiziert, keine Aufnahme in den Score | #68/#69 | siehe §2, §4 Punkt 7 |
| Split-Wächter gebaut (MNST-Vorfall US 2026-08 als Auslöser) | #70 | siehe §2, §4 Punkt 9 |
| **Universum hatte keinen Alters-Wächter** — jetzt behoben (Kursabruf und iShares-Kursvergleich gleich mit abgedeckt) | #74 | siehe §4 Punkt 14, §6 |
| ntfy-Relay gebaut (Auftrag 4 der Automatisierung) — spätere geplante Agenten können jetzt melden, ohne das ntfy-Topic zu kennen | #75 | siehe §4 Punkt 14 |
| **Testlauf des ntfy-Relays** — über „Run workflow" ausgelöst, Nachricht real auf dem iPhone angekommen; Auftrag 4 damit vollständig abgeschlossen, nicht nur gemergt | #75 | ehemals §3-Wiedervorlage „nach Merge von PR #75", jetzt erledigt |
| Wiedervorlagen-Wächter gebaut (Auftrag 2 der Automatisierung) — §3 trägt jetzt `faellig`-Kommentare, meldet "Heute fällig"/"Überfällig" zustandslos | #76 | siehe §4 Punkt 14, §6 |
| Schutz-Sperre gebaut (Auftrag 3 der Automatisierung) — PR-Check gegen geschützte Zonen, baut nur den Check, keinen Merge-Workflow | #77 | siehe §4 Punkt 14, §7.8 |
| **PR #77 gemergt — ausnahmsweise trotz rotem Eigen-Check** (Label am iPhone nicht setzbar; ohne Ruleset nicht blockierend) | #77 | siehe §4 Punkt 14 |
| Schutz-Sperre auf reine Ampel umgestellt — Label-Freigabe entfernt, weil Code/Agenten als easywebb911 handeln (Entscheidung (5)) und jede Freigabe "von easywebb911" fälschbar wäre; Auftrag 5 umdefiniert: Agenten mergen nie | #78 | siehe §4 Punkt 14, §7.8 |
| **Agenten-Kontrolle gebaut und gemergt** (Auftrag 5, konkretisiert) — meldet laut, wenn sich der geplante Wächter-Agent seit über 48 Std. nicht mehr über `ntfy_relay.yml` gemeldet hat; eine Zeile (`run-name`) in `ntfy_relay.yml` ergänzt, damit der Lauf-Titel überhaupt geprüft werden kann. Merge-Commit `9f0238c`, 25.10.2026 20:22 UTC (per `gh`/API gegenprüft) | #79 | siehe §4 Punkt 15 |
| **Stichtag-Schutz-Fix (PR #73) real bewiesen:** Lauf 94 (31.10.2026, 01:02 UTC, über Mitternacht gerutscht) lief korrekt in die Oktober-Stichtag-Rechnung hinein statt sie fälschlich "zu früh" zurückzuhalten — exakt die Konstellation aus dem PR-#73-Fund, jetzt real eingetreten und bestanden | #73 | siehe §4 Punkt 13, §4 Punkt 16, Actions-Run `41153318736` |
| **Drittes Vertragstest-Fenster (25.–31.10.2026) ausgewertet:** fünf Werktags-Läufe, alle „Alle 12 Vertraege halten. Kein Push."; BlackRock-URL-Fix (PR #63) damit real bewiesen; DE-Kursvergleich jedes Mal vollständig, größte Abweichung 0,00 % | `vertrag.yml` | Actions-Runs `40341359705`, `40514313168`, `40707762856`, `40894310972`, `41073466086`; siehe §4 Punkt 1, §4 Punkt 6 |
| **Split-Wächter am ersten echten Stichtag (30.10.) stumm — kein Fehlalarm.** Er schreibt nur bei Fund oder Fehler eine Logzeile (`split_waechter.py`, `pruefe_und_melde`); das Lauf-96-Log enthält keine einzige solche Zeile. Ob er einen echten Split erkennen würde, bleibt nur durch die Testdatei belegt | #70 | Job-Log Actions-Run `41187870579` |
| **Sektor-Hinweis am ersten echten Stichtag (30.10.) sichtbar:** „Sektor-Häufung: 4 von 5 Top-5-Werten liegen im Sektor Energy." (US); DE ohne Hinweis | #72 | `docs/index.html` (`p.sektor-hinweis`) nach Lauf 96 |
| **Oktober-Stichtag (30.10.2026) eingefroren**, beide Märkte — nach zwei fail-soft-Abbrüchen per manuellem Lauf 96 | `Momentum-Lauf` Lauf 96 | `8e29c5d`, `data/rankings/*_2026-10.json`, siehe §1, §4 Punkt 16 |
| **Evaluation-Seite: Gesamtrückblick vor Monatsrückblick** | #81 | `0972fe7` |
| **Injektions-Fix `lauf.yml`/`universum.yml` (ehem. §4 Punkt 14c):** Dispatch-Eingaben nur noch über `env:`, `datum` streng geprüft (leer oder JJJJ-MM-TT); `vertrag.yml` nutzt `$GITHUB_EVENT_NAME` | #87, Merge `f03c753` (06.11.2026) | `tests/unit/test_workflow_injektion.py` (statisch + echte Ausführung mit bösartigem `datum`); Lauf 101 (`fc2026a`, 07.11.) lief nach dem Merge durch |
| **Node-Update `actions/checkout@v5`, `actions/setup-python@v6` (ehem. §5 Punkt 1)** — je 16 Stellen in 15 Workflow-Dateien; Rest (`upload-`/`download-artifact@v4` in `vertrag.yml`) bleibt offen als §5 Punkt 5 | #87, Merge `f03c753` (06.11.2026) | Lauf 101 (`fc2026a`, 07.11.) lief nach dem Merge durch |
| **Wiedervorlage 08.11.2026 (Lit-Check erstmals direkt an ntfy.sh):** Lit-Check kam am 08.11. per ntfy an. Damit alle drei geplanten Aufgaben (Wächter, Rundgang, Lit-Check) auf dem direkten ntfy-Weg belegt | Easy, Angabe vom 08.11. | aus dem Repo nicht belegbar, siehe §4 Punkt 15 |
| **Wiedervorlage 05.11.2026 (Beleg-Zähler auswerten):** Läufe 97/98/99 (`32221f7`, `ec8ba91`, `d6618ef`): in 5 von 6 Markt-Läufen je 5 Zeilen des Vortags verworfen, alle **ohne** Rohkurs (0 mit); vollständig nur US im Lauf 97 vom 03.11. (Handelstag 02.11.). **Annahme hinter V3 widerlegt.** Grenze: der Zähler sieht nur die 5 Anzeige-Titel, nicht den Index und keinen Stichtagslauf | Auswertung 05.11.2026 | `data/status.json` → `daten` der drei Commits; siehe §4 Punkt 16 |
| **Wiedervorlage 03.11.2026 (erster Monatsrundgang):** Rundgang lief am 03.11., Meldung kam per ntfy an, Befund sachlich korrekt (Läufe, Oktober-Ranking, erster Zählerwert, fällige Punkte); Grenze: sieht keine Workflow-Logs | Easy, Angabe vom 03.11. | aus dem Repo nicht belegbar, siehe §4 Punkt 15 |
| **Wiedervorlage 02.11.2026 (erstes Montags-Lebenszeichen des Wächters über ntfy.sh direkt):** Lebenszeichen kam am 02.11. am iPhone an | Easy, Angabe vom 03.11. | aus dem Repo nicht belegbar, siehe §4 Punkt 15 |
| **Ranking-Verlauf entschieden: nicht bauen** (ehem. Wiedervorlage 03.11., Roadmap §6 Punkt 1) — geringer Nutzen für die Kaufentscheidung, mischt seit November zwei Regeln; jederzeit neu aufnehmbar | Easy, 03.11.2026 | siehe §6 Punkt 1 |
| **Wiedervorlage 01.11.2026 (erster Lit-Check nach Umstellung) ausgewertet:** Lauf korrekt, App-Push kam nicht an, Bericht von Easy kopiert → seither Zustellung direkt an ntfy.sh; Folge-Prüfung 08.11. in §3 | Easy, 01.11. | siehe §4 Punkt 15 (Nachtrag 01.11.) — Angaben aus Easys Bericht, aus dem Repo nicht belegbar |
| **Wiedervorlage 25.11.2026 („PR 2 Methodik/Karten gemergt") — gebaut als PR #84**; der Merge selbst liegt bei Easy, deshalb fragt die 30.11.-Zeile in §3 ihn vorher ab | #84 | siehe §2, §6 Punkt 0 |
| **PR 2 (Methodik/Karten) tatsächlich gemergt** (Merge-Commit `022c8ff`) | #84 | siehe §2, §4 Punkt 8, §6 Punkt 0 |
| **Wiedervorlage 15.12.2026 („PR 3 Evaluation: Methodenwechsel sichtbar, Gesamtrückblick getrennt nach Regel") — gebaut als PR #85**; der Merge liegt bei Easy, die neue §3-Zeile (31.12.2026) prüft danach den ersten echten Dezember-Lauf | #85 | siehe §2, §4 Punkt 8, §6 Punkt 0 |
| **Lit-Check 52-Wochen-Hoch entschieden:** US 100/0 ab Ranking 2026-11, DE 50/50 | Easy, 01.11.; Rechnung: #83 | siehe §4 Punkt 8, §7.6 |

### Geschlossene Punkte aus §4 (Volltext, geschlossen 03.11.2026)

Je Punkt: der Beleg, dass nichts mehr offen ist, dann der unveränderte Text, wie er in §4 stand.

**§4 Punkt 2 — Vertragstest-Vorfall 31.08.2026.** Beleg: Punkt selbst „dokumentiert, nichts zu tun“; Befund A durch PR #51 behoben (`2b648c3`); Befund B ist dauerhaft unbeweisbar, keine Handlung möglich.

> **2. Der Vertragstest-Vorfall vom 31.08.2026 — untersucht, kein Bug,
> zwei belegte Befunde.** *(dokumentiert, nichts zu tun)*
> 
> Der Vertragstest meldete an diesem Tag `Kursvergleich DE — nicht
> durchführbar: nur 0 von 102 Titeln waren vergleichbar (0 %, nötig 80 %)`
> (Actions-Run `33409297243`, Job-Log wörtlich). Das ist **kein Bruch**: das
> Verdikt lautete `[ok]`, kein Push ging raus („Alle 12 Verträge halten.
> Kein Push.") — `MIN_VERGLEICHSQUOTE = 0.80` in `kursvergleich.py`
> behandelt einen so gut wie unvergleichbaren Tag bewusst als „nicht
> durchführbar", nicht als Widerspruch zwischen den Quellen. Am selben Tag
> lief der US-Vergleich vollständig durch (501 von 504 verglichen, 0 über
> der Toleranz) — kein allgemeiner Quellenausfall, sondern etwas
> DE-Spezifisches an genau diesem Tag.
> 
> Diagnose ergab zwei Befunde:
> - **Befund A, bewiesen:** `src/momentum/data.py` (`download_prices`,
>   Zeilen um 171–176) koppelt die Befüllung von `series_roh`/`close`
>   (der für den DE-Kursvergleich bestimmte, unbereinigte Kurs) an die
>   Gültigkeit von `Adj Close` am selben Tag — obwohl der Docstring des
>   Moduls `close` ausdrücklich als „von Yahoo vollständig unabhängig"
>   beschreibt. Ein Tag, an dem `Adj Close` für praktisch alle DE-Titel
>   gleichzeitig fehlschlägt, würde exakt das beobachtete Bild erzeugen.
>   **Code-bestätigt, seit PR #51 behoben:** die Prüfung `close_valid` wird
>   jetzt VOR und unabhängig von der Adj-Close-Prüfung ausgewertet;
>   `series_adj`/`series_turnover` (Score-Pfad) bleiben unverändert an die
>   adj-Prüfung gebunden.
> - **Befund B, unbestätigt und bleibt es dauerhaft:** dass Befund A
>   tatsächlich die Ursache des 31.08.-Vorfalls war. Das lässt sich nicht
>   mehr beweisen — die yfinance-Antwort von damals ist nicht
>   reproduzierbar, ein heutiger Abruf liefert den heutigen Stand. PR #51
>   ist deshalb eine eigenständige Härtung, keine bestätigte
>   Ursachenkorrektur (so auch im PR-Text festgehalten).

**§4 Punkt 5 — Yahoo-Rate-Limit-Vorfall 01.10.2026 (Lauf 71).** Beleg: „nichts zu tun“; September-Stichtag per Lauf 72 geschrieben (Run `36927209332`, Commit `6de1fae`); Ursache in der Diagnose 01.11. erneut bestätigt (`YFRateLimitError`, Run `36798080643`).

> **5. Yahoo-Rate-Limit-Vorfall vom 01.10.2026 (Lauf 71) — untersucht,
> kein Bug, fail-soft bestätigt.** *(dokumentiert, nichts zu tun)*
> 
> Der planmäßige Nacht-Lauf vom 01.10.2026, 00:49 UTC (Actions-Run
> `36798080643`, gedacht für den September-Monats-Stichtag) brach ab mit,
> wörtlich aus dem Job-Log: `['^SP500TR']: YFRateLimitError('Too Many
> Requests. Rate limited. Try after a while.')`, gefolgt von `LAUF
> ABGEBROCHEN: [us] Keine Indexdaten fuer ^SP500TR — ohne Handelskalender
> kein Stichtag.` Exit-Code 2, **kein** „Lauf 71"-Commit entstand (derselbe
> Mechanismus wie bei Lauf 1, siehe §8 Lesson 3). Fail-soft griff exakt wie
> vorgesehen: „Es wurde bewusst nichts veroeffentlicht und nichts
> eingefroren."
> 
> Easy hat denselben Tag, 21:13 UTC, den Lauf von Hand erneut ausgelöst
> (`workflow_dispatch`, Actions-Run `36927209332`, Lauf-Nummer 72) — **das
> war ein manueller Nachlauf, keine automatische Wiederholung** durch den
> nächsten planmäßigen Zyklus (der wäre erst am 02.10., 01:04 UTC,
> gekommen, und hätte den dann bereits eingefrorenen September-Stichtag
> nicht erneut geschrieben). Lauf 72 lief vollständig durch und schrieb den
> September-Stichtag (`data/rankings/{de,us}_2026-09.json`, Commit
> `6de1fae`). Kein Code-Fix nötig oder vorgenommen — eine Yahoo-
> Ratenbegrenzung ist ein bekanntes, bereits per Fail-soft abgedecktes
> Risiko, kein neuer Fund.

**§4 Punkt 7 — Lit-Check Frog-in-the-Pan / Information Discreteness.** Beleg: Entscheid „nicht in den Score, kein Bau geplant“; Probe zurückgebaut (PR #69, `e4cfdee`).

> **7. Lit-Check Frog-in-the-Pan / Information Discreteness — geprüft,
> nicht eingebaut.** *(dokumentiert, nichts zu tun)*
> 
> Wegwerf-Diagnose (PR #68, Rückbau PR #69) hat die Information
> Discreteness (ID, Da/Gurun/Warachka 2014 — misst, ob eine Kursbewegung
> in vielen kleinen, gleichgerichteten Schritten entstand ("kontinuierlich"/
> "frog in the pan", hohe ID) oder in wenigen großen Sprüngen
> ("sprunghaft", niedrige ID)) für beide Universen über Juli/August/
> September 2026 nachgerechnet. Befund: Top-5 im Mittel ID-Perzentil ca.
> 0,25 (0,5 = neutral, tendenziell Richtung "sprunghaft"), aber nur 1 von
> 30 Top-5-Plätzen über die drei Monate tatsächlich im "sprunghaften
> Drittel" (DVA, Juli, 0,678). Eine Umsortierung der Top-15 nach ID ändert
> 2–3 von 5 Plätzen — das ist aber überwiegend Rauschen: ein einzelner
> Handelstag verschiebt die ID bereits um ca. 0,009 ID-Einheiten, in der
> Größenordnung der beobachteten Unterschiede. **Entscheid: ID wird NICHT
> in den Score aufgenommen, kein Bau geplant** — die Literatur selbst
> (Frog-in-the-Pan) betrifft ohnehin eine andere Fragestellung
> (Kontinuität der Kursbildung) als die hier verwendeten Faktoren
> (Höhe der Rendite, Nähe zum Hoch), nicht nur die schwache Trennschärfe
> in den drei beobachteten Monaten.

**§4 Punkt 9 — MNST-Split-Vorfall (US 2026-08).** Beleg: Split-Wächter gebaut (PR #70, `c56dc64`); am ersten echten Stichtag 30.10. stumm, kein Fehlalarm (§10, Run `41187870579`); August-Stand bleibt bewusst eingefroren. Dass er einen echten Split erkennt, ist weiter nur per Test belegt — kein offener Auftrag.

> **9. MNST-Split-Vorfall (US 2026-08) — Ursache geklärt, Ranking bleibt
> eingefroren, Split-Wächter gebaut (PR #70).** *(dokumentiert + behoben
> für künftige Fälle, nichts am August-Stand zu tun)*
> 
> Split 2:1 am 11.08.2026, Stichtag 28.08.2026. Der Lauf vom 31.08.
> rechnete Momentum **-0,2278** statt der im Nachhinein rekonstruierten
> korrekten **+0,5443** (Rang 471 statt eines deutlich besseren Rangs).
> Rekonstruiert per Handrechnung in der Sitzung vom 09.10.2026 (nicht per
> Live-Abruf — Yahoo im Sandbox-Kontext nicht erreichbar): der M-12-Anker
> in `momentum_12_1` war **exakt Faktor 2 zu hoch**, weil Yahoo die
> Vorgeschichte zu diesem Zeitpunkt noch nicht auf den Split
> nachbereinigt hatte. Im September war die Reihe wieder normal. **Top-5
> vermutlich unberührt** (Schätzung ca. 80 Punkte gegen 91 bei Rang 5 —
> MNST selbst lag mit dem falschen Wert weit außerhalb der Top-15, ein
> korrigierter Wert hätte es nicht automatisch hineingehoben). Der
> eingefrorene August-Stand (`data/rankings/us_2026-08.json`) bleibt
> **unverändert eingefroren** — keine rückwirkende Korrektur, siehe das
> Einfrierungsprinzip in §7.2.
> 
> Als Gegenmaßnahme für künftige Fälle: der **Split-Wächter**
> (`split_waechter.py`, PR #70) erkennt innerhalb der für
> `momentum_12_1`/`high_52w_ratio` genutzten Tagesreihe (`Adj Close`) eine
> Naht mit einem Kursverhältnis nahe einem gängigen Split-Verhältnis (2,
> 3, 4, 5, 10 — bewusst ohne 3:2 wegen Fehlalarm-Risiko durch echte
> Kurseinbrüche, ±3 % Toleranz) und meldet den Fund (eine Zeile je Titel,
> ein gebündelter Push) — **nur Erkennen und Melden**, kein Eingriff in
> Score/Ranking. Erster echter Wirksamkeitstest: Stichtag 30.10.2026
> (siehe §3).

**§4 Punkt 11 — Sektor-Konzentration der Top-5.** Beleg: Variante (b) gebaut (PR #72, `0f94675`), am 30.10. real sichtbar (§10); Variante (c) bleibt als Roadmap §6 Punkt 4 erhalten.

> **11. Sektor-Konzentration der Top-5 — Befund, Entscheid, gebaut (PR
> #72).** *(dokumentiert + gebaut, nichts weiter zu tun)*
> 
> Diagnose (vor PR #72, read-only): US-Top-5 lag in allen drei bisherigen
> Stichtagen auffällig konzentriert — Juli 3/5 Health Care, August 3/5
> Energy, September **5/5 Information Technology**. DE lag in allen drei
> Monaten bei höchstens 2/5. Eingeordnet als **erwartbar, kein
> Konstruktionsfehler**: Momentum ist literaturbekannt sektor-korreliert
> (ein branchenweiter Trend bewegt mehrere Titel gleichzeitig), die
> September-IT-Konzentration passt sachlich zu einer Technologie-Rally.
> Wichtige Einschränkung: die Sektor-Zuordnung für Juli/August stammt aus
> der **heutigen** `ticker_meta_*.json` (Stand 03.08.2026), nicht aus
> einer historisch eingefrorenen Quelle — siehe `meta.py`-Docstring,
> Sektor ist bewusst nicht im Ranking-Schema, weil er sich ändern darf.
> Die Vergleichbarkeit von Wikipedias GICS-Sektoren (US) gegen die
> iShares-eigene Sektor-Spalte (DE) ist **nicht verifiziert** (gleiche
> Taxonomie nicht belegt, nur zufällig dieselbe Anzahl von elf Kategorien
> je Markt) — deshalb **keine Aggregation über beide Märkte**.
> 
> **Entscheid:** Variante (b) gebaut — ein Hinweis bei ≥ 3 von 5 Top-5-
> Werten im selben Sektor, je Markt getrennt geprüft, reine Render-Zeit-
> Berechnung ohne neues Schema (siehe `render.py::_sektor_konzentration`/
> `_sektor_hinweis`, Platzierung direkt über dem Kartenraster). Variante
> (c) — eine dauerhafte Sektor-Historie in `data/evaluation/*.json` mit
> eigenem Schema-Feld — **zurückgestellt**: kein akuter Bedarf, würde ein
> additives Schema und damit Manual-Merge brauchen (siehe §6, Roadmap).

**§4 Punkt 12 — Automatisierte SESSION_HANDOVER.md-Pflege per Workflow.** Beleg: Entscheid „kein Bau“; kein offener Auftrag.

> **12. Automatisierte SESSION_HANDOVER.md-Pflege per Workflow — geprüft,
> nicht gebaut.** *(dokumentiert, kein Bau geplant)*
> 
> Read-only-Diagnose (vor PR #72): geprüft, ob ein Workflow dieses
> Dokument automatisch nachführen könnte (mechanisch ableitbare Blöcke:
> PR-Nummer/Titel/Datum via `gh pr list`, Cron-Fahrplan via YAML-Parsing;
> NICHT mechanisch: Merge-Klasse — nur Freitext im PR-Titel, siehe
> `pr_verwaisung_waechter.py`-Docstring —, sowie sämtliche Urteils-Teile
> in §3/§4/§5/§6). **Kernbefund:** Jede Variante, die direkt in
> `SESSION_HANDOVER.md` schreibt (markierter AUTO-Bereich oder ein
> gemergter Auto-PR), würde den bestehenden Doku-Wächter
> (`handover_waechter.py`) **entwerten** — er misst ausschließlich das
> Committer-Datum des jüngsten Commits auf dieser Datei, ohne zwischen
> mechanischen und Urteils-Abschnitten zu unterscheiden, und ein
> automatischer Teil-Schreibvorgang würde seine Uhr auf null setzen, ohne
> dass die Urteils-Teile tatsächlich gepflegt wurden. **Entscheid: kein
> Bau.** Bei künftigem Bedarf wäre eine **getrennte, vollautomatische
> Protokolldatei** (Variante a, z. B. `data/pr_protokoll.json`, auf die
> `SESSION_HANDOVER.md` nur verlinkt) der einzige Weg, der den Doku-
> Wächter nicht berührt — das bliebe aber ein eigener, separat zu
> entscheidender Auftrag.
