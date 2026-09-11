# Session-Handover — Momentum-Report

**Stand: 11.09.2026**, nach PR #49 (Reparatur-Agent Stufe 3, erste
Ausbaustufe). Repo `easywebb911/Momentum-Report`, Branch `main` — den
aktuellen Stand nennt `git log -1`, er steht hier bewusst nicht als Zahl.

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

**Und eine dritte, neu aus dieser Nachziehung gelernt (siehe §8, Lesson
11):** Dieses Dokument selbst braucht einen Anlass zum Nachziehen, nicht
nur den nächsten Auftrag, der zufällig danach fragt — es stand vom
16.08. bis zum 11.09.2026 (drei Wochen, zehn PRs, ein echter
Betriebsvorfall) unverändert und kannte nichts davon.

---

## 1. Betriebszustand (11.09.2026)

| Sache | Zustand | Beleg |
|---|---|---|
| GitHub Pages | **aktiv** seit 02.08., deployt bei jedem Push auf `main` | Workflow `pages-build-deployment`, angelegt 02.08.2026 16:11 — Zähler und letzter Lauf in Actions |
| Momentum-Lauf | läuft werktäglich, **ein Fehlschlag insgesamt** — der allererste | Actions-Liste `lauf.yml`: Run 1 (02.08.2026, `conclusion: failure`) war ein Datumsformat-Bruch bei iShares, siehe §8 Lesson 3 und `ishares.py`-Kommentar. **Kein** „Lauf 1"-Commit existiert deshalb — die Zählung im `git log` beginnt bei „Lauf 2" (`07cbedd`). Seither durchgehend grün. |
| Ranking | eingefroren zum **31.08.2026** (zweiter scharfer Stichtag), beide Märkte — Juli-Stand bleibt parallel als eigene, nie überschriebene Datei stehen | `data/rankings/us_2026-08.json`, `de_2026-08.json` (und weiterhin `*_2026-07.json`) |
| US-Top-5 (Aug.) | VLO, MPC, PSX, STT, BNY — 497 von 503 im Universum bewertet | `us_2026-08.json` → `top`, `abdeckung` — **4 von 5 Titeln gegenüber Juli gewechselt** (nur VLO blieb), siehe §3/§10 |
| DE-Top-5 (Aug.) | DWS.DE, TKA.DE, ALV.DE, DHL.DE, RWE.DE — 84 von 102 im Universum bewertet | `de_2026-08.json` → `top`, `abdeckung` — SIE.DE fiel raus, RWE.DE kam neu rein |
| Überschuss-Ampel | **live mit echten Zahlen**, Umstellungs-Hinweis ist weg | US: Rendite +20,78 %, Geldmarkt (`^IRX`) **+3,67 %**, Überschuss **+17,10 %**, keine Warnung. DE: Rendite +10,46 %, Geldmarkt (€STR/EZB) **+1,98 %**, Überschuss **+8,48 %**, keine Warnung. Beide `trend_ampel` in den August-Rankings — siehe §4 Punkt 1 (jetzt in §10, erledigt) |
| Universen | **beide VERIFIED**, Stand 03.08.2026 (seither nicht neu gezogen) | `universe/universe_us.txt`, `universe_de.txt` (Kopfzeile `# STATUS: VERIFIED`) |
| Beschreibende Angaben | vorhanden (Name + Sektor je Ticker) | `universe/ticker_meta_us.json`, `ticker_meta_de.json` |
| Konfluenz — Export | `docs/data/top5.json`, schreibt sich bei jedem neuen Ranking neu | `run.py::_schreibe_top5`, seit `e695b54` (Lauf 9) |
| Konfluenz — Push/Stand | **live, erster echter Treffer bereits eingetreten**: `de:TKA.DE` | PR #46 (`62257b4`); `data/konfluenz_stand.json` — der erste Produktionslauf, der die Mechanik überhaupt scharf prüfte, war Lauf 54 (07.09., nach PR #46/#47/#48) |
| Konfluenz — Historie | drei Einträge: zwei manuell rekonstruiert (TKA.DE 17./24.08., SIE.DE 27.08., Stichtag Juli — Elliott-Seite nicht belegbar), **ein automatisch erfasster** (TKA.DE, Stichtag 31.08., Elliott-Score 81,54, Kurs 14,90 €) | PR #47 (`ba99293`), PR #48 (`c9e5688`); `data/konfluenz_historie.json` — jeder Eintrag trägt `quelle`: `"automatisch"` oder `"manuell_rekonstruiert"` |
| Reparatur-Agent (Stufe 3) | **erste, bewusst schmale Ausbaustufe gebaut** — nur Datumsformat-Drift bei den drei DE-iShares-Bestandslisten; noch nie ausgelöst (kein passender Fund seit Einführung) | PR #49 (`a2343cc`); `tools/agent_datumsformat.py`, `tools/agent_datumsformat_oeffnen.py`, zweiter Job in `vertrag.yml` |
| ntfy-Push | verdrahtet, **zwei Push-Arten inzwischen live bewiesen**: Ranking-Push (Probe 08.08.) und Konfluenz-Push (siehe Zeile oben) | Lauf 19 (Probe); `konfluenz_stand.json`/`konfluenz_historie.json` als Nebenbeweis für den Konfluenz-Push (Zustellung selbst nicht am Gerät nachgeprüft, nur die serverseitige Wirkung) |
| Kurse | Stand je Markt in `kurse_vom` | `data/status.json` |
| Tests | vollständig grün (unit + design/Playwright) | `pytest` (Zähler bewusst nicht abgeschrieben — er wächst mit jedem PR) |
| Offene PRs | **keine** | GitHub-PR-Liste, Status `open` = leer |

**Cron-Fahrplan** (`.github/workflows/`):

| Workflow | Auslöser | Datei |
|---|---|---|
| Momentum-Lauf | `45 21 * * 1-5` (werktags 21:45 UTC) + manuell | `lauf.yml` |
| Datenquelle prüfen | `15 6 * * 1` (montags 06:15 UTC) + manuell | `datenquelle.yml` |
| Vertragstest | `0 8 25-31 * *` + Wochentag-Riegel im Job + manuell | `vertrag.yml` — Job `vertrag` schweigt im Normalfall, ein Push mit allen Brüchen; seit PR #49 ein zweiter Job `agent-datumsformat` im selben Run (eigene, sonst nirgends vergebene Schreib-/PR-Rechte, siehe §2 #49) |
| Wächter (Totmannschalter) | `30 7 * * 1` (montags 07:30 UTC) + manuell | `waechter.yml` — schweigt im Normalfall, Alarm-Push + roter Lauf ab > 4 Tagen Stille |
| Universum aktualisieren | **nur manuell** | `universum.yml` |
| Tests | jeder Push und jeder PR | `tests.yml` |

Am Wochenende läuft nichts. Ist der letzte Lauf von Freitag, ist das
kein Ausfall, sondern der Fahrplan.

---

## 2. Gemergte Arbeit (#1–#21, #40–#49 vollständig)

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

Bei PRs mit zwei Hashes ist der erste der Inhalts-Commit (der, den ein
`git revert` tatsächlich braucht), der zweite der GitHub-Merge-Commit.
#40/#41/#42/#43/#44/#45 tragen keinen eigenen „Merge pull request"-Commit
im linearen Verlauf (Squash bzw. Fast-Forward) — die Inhalts-Hashes sind
über `gh`/die PR-Ansicht verifiziert, nicht geraten.

---

## 3. Wiedervorlagen (mit Datum)

| Wann | Was | Warum |
|---|---|---|
| **laufend, montags** | `Datenquelle prüfen` läuft gegen Yahoo. | Schlägt sie fehl, ist die Kursquelle das Problem, nicht der Code. |
| **25.–30.09.2026** | **Zweites Vertragstest-Fenster.** Erst jetzt gibt es eine ZWEITE Woche echter DE-Abweichungszahlen zum Vergleich mit dem ersten Fenster (25.–31.08.). | Siehe §4 Punkt 1 (DE-Toleranz) — eine einzelne Woche reicht nicht zur Kalibrierung, siehe dortige Begründung. |
| **Herbst 2026** (ab ~Nov, ≥ 4 Stichtage) | **Ranking-Verlauf.** Entscheiden, ob die Seite eine Historie zeigt. | Aktuell **2 von 4** Stichtagen vorhanden (Juli, August) — noch nichts zu zeigen. Achtung: eine Verlaufs-Anzeige darf keine Trefferquote implizieren — das Werkzeug misst keine Performance (siehe §6, Roadmap). |
| **offen, keine Frist** | **Reparatur-Agent, weitere Ausbaustufen?** PR #49 deckt genau eine von sieben real aufgetretenen Fehlerklassen ab (Datumsformat-Drift bei iShares) — bewusst schmal, siehe §4 Punkt 3. Ob und welche Fehlerklasse als Nächstes drankommt, ist **Easys Entscheid**, keine automatische Fortsetzung. | Diagnose vor PR #49 (siehe Session-Historie) hat sechs weitere Fehlerklassen benannt, von denen die meisten Domänenurteil brauchen und deshalb nicht sicher automatisierbar sind. |
| **offen, keine Frist** | **`series_roh`/`Adj Close`-Kopplung in `src/momentum/data.py` beheben — oder bewusst lassen?** Siehe §4 Punkt 4. Eine kleine, additive Entkopplung wäre möglich, wurde aber bisher nicht gebaut (nur diagnostiziert). | Kausalität zum 31.08.-Vorfall unbestätigt (siehe §4) — der Bau selbst wäre unabhängig davon vertretbar, aber ein eigener, von Easy anzustoßender Auftrag. |

**Aus der letzten Vorlage-Liste erledigt, jetzt in §10:** der 31.08.-Monats-
Stichtag selbst (samt Überschuss-Ampel-Realprobe), der erste Vergleich
zweier Monats-Ranglisten (01.09., Top-5-Wechsel real beobachtet), sowie
Hygiene-Backlog Punkt 1 (default-deny, #40).

---

## 4. Offene Punkte

**1. DE-Toleranz (`TOLERANZ = 0.010` in `kursvergleich.py`) — weiterhin
nicht neu kalibriert, jetzt aber mit echten, aber noch dünnen Messdaten.**
*(beobachten, nichts ändern)*

Das erste reale Vertragstest-Fenster (25.–31.08.2026) liegt vor. Bild
uneinheitlich: am 28.08. lief der volle Vergleich sauber durch (102 von
102 Titeln, größte Abweichung 0,00 %, Verdikt `ok` — Actions-Run
`33205016377`); am 31.08. selbst waren **0 von 102 Titeln** vergleichbar
(„entfallen", kein Bruch — siehe Punkt 2 unten). Eine einzelne Woche mit
nur einem auffälligen Tag reicht nicht, um `TOLERANZ` gegen echte
Streuung statt gegen das gesetzte Bauchgefühl zu prüfen. Nächstes Fenster:
25.–30.09.2026 (§3). **Bis dahin nichts ändern.**

**2. Der Vertragstest-Vorfall vom 31.08.2026 — untersucht, kein Bug,
zwei belegte Befunde.** *(dokumentiert, nichts zu tun)*

Der Vertragstest meldete an diesem Tag `Kursvergleich DE — nicht
durchführbar: nur 0 von 102 Titeln waren vergleichbar (0 %, nötig 80 %)`
(Actions-Run `33409297243`, Job-Log wörtlich). Das ist **kein Bruch**: das
Verdikt lautete `[ok]`, kein Push ging raus („Alle 12 Verträge halten.
Kein Push.") — `MIN_VERGLEICHSQUOTE = 0.80` in `kursvergleich.py`
behandelt einen so gut wie unvergleichbaren Tag bewusst als „nicht
durchführbar", nicht als Widerspruch zwischen den Quellen. Am selben Tag
lief der US-Vergleich vollständig durch (501 von 504 verglichen, 0 über
der Toleranz) — kein allgemeiner Quellenausfall, sondern etwas
DE-Spezifisches an genau diesem Tag.

Diagnose ergab zwei Befunde:
- **Befund A, bewiesen:** `src/momentum/data.py` (`download_prices`,
  Zeilen um 171–176) koppelt die Befüllung von `series_roh`/`close`
  (der für den DE-Kursvergleich bestimmte, unbereinigte Kurs) an die
  Gültigkeit von `Adj Close` am selben Tag — obwohl der Docstring des
  Moduls `close` ausdrücklich als „von Yahoo vollständig unabhängig"
  beschreibt. Ein Tag, an dem `Adj Close` für praktisch alle DE-Titel
  gleichzeitig fehlschlägt, würde exakt das beobachtete Bild erzeugen.
  **Code-bestätigt, nicht behoben.**
- **Befund B, unbestätigt:** dass Befund A tatsächlich die Ursache des
  31.08.-Vorfalls war. Das lässt sich nicht mehr beweisen — die
  yfinance-Antwort von damals ist nicht reproduzierbar, ein heutiger
  Abruf liefert den heutigen Stand.

Eine Entkopplung (`close` unabhängig von `adj` prüfen) wäre eine kleine,
additive Änderung, die den Score-Pfad (`adjusted`) nicht berührt — aber
noch nicht gebaut, siehe §3.

**3. Reparatur-Agent Stufe 3 — erste Ausbaustufe gebaut, keine
automatische Fortsetzung.** *(siehe §3, Easys Entscheid nötig)*

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

**5. §7.5 (Quellen, extern verifiziert) führt die Kursvergleich-Quellen
(iShares-Kurs-Spalte, SXR8/IUSA) nicht auf.** *(gemeldet, nicht in
dieser Nachziehung behoben)*

Die Rubrik deckt bisher nur Universum, Indizes, Geldmarktsätze und
Literatur ab — die beiden Kursvergleichs-Zweitquellen (Stufe 2a/2b, PRs
#26/#35, längst gebaut und scharf) fehlen dort strukturell. Das ist eine
eigene, kleine Doku-Ergänzung, absichtlich nicht Teil dieses Auftrags
(der Auftrag nannte sie nicht) — hier nur gemeldet, damit sie nicht
untergeht.

---

## 5. Hygiene-Backlog

Kleinarbeit ohne Dringlichkeit — jeweils ein eigener kleiner PR.

1. **`Node.js 20 is deprecated`-Warnung** in jedem Lauf — **jetzt fällig**
   (die ursprüngliche Rücksicht „nicht vor dem 31.08." ist mit dem
   31.08. selbst erledigt): `actions/checkout@v4` und
   `actions/setup-python@v5` auf aktuelle Fassungen heben. Betrifft
   inzwischen **sieben** Stellen in sechs Workflow-Dateien (`lauf.yml`,
   `datenquelle.yml`, `tests.yml`, `universum.yml`, `vertrag.yml` — dort
   seit PR #49 in **beiden** Jobs, `waechter.yml`) — Beleg:
   `grep -rn "actions/checkout@\|actions/setup-python@" .github/workflows/`.

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

1. **Ranking-Verlauf** (Herbst, ≥ 4 Stichtage — aktuell 2/4) — Anzeige der
   bisherigen Monats-Ranglisten. Harte Grenze: keine Renditeberechnung,
   keine Trefferquote, keine Performance-Kurve. Das Werkzeug misst keine
   Ergebnisse, es zeigt eine Rangfolge.
2. **Risikogesteuerte Varianten** (Daniel & Moskowitz 2016) — in `README`
   bereits als „dokumentiert, aber erst v1" geführt.
3. **Reparatur-Agent, weitere Fehlerklassen** — offen, Easys Entscheid
   (siehe §3/§4 Punkt 3). Die vorherige Diagnose hat sechs Kandidaten
   benannt; keiner davon ist ohne Weiteres so eng wie Datumsformat-Drift.

**Selbstwartungs-Stufenplan** (Easys Richtung vom 09.08. — „ein Tool, das
sich selbst wartet"; die Maschine arbeitet, Easy behält den Ein-Tipp-Veto):

| Stufe | Was | Stand |
|---|---|---|
| 0 | Totmannschalter (`waechter.yml`) | **gebaut** |
| 1 | Vertragstests je Fremdquelle, werktags im Fenster 25.–31. | **gebaut, jetzt einmal real durchlaufen** (25.–31.08.2026, siehe §4 Punkt 1/2) |
| 2a | Zweite Kursquelle **DE** mit Vergleichsgatter | **gebaut, scharf seit 31.08.** — realer Vorfall und Diagnose siehe §4 Punkt 2 |
| 2b | Zweite Kursquelle **US** (S&P-500-UCITS-Bestandslisten) | **gebaut, scharf seit 31.08.** (#35, MANUAL-MERGE, 14.08.). Anker = Bestands-Stichtag selbst, Toleranz 0,25 %, Zulass 3 Abweichler, Quelle SXR8 primär mit IUSA als dokumentiertem Ausweich, Split-Ausnahme mit Anti-Schlupfloch-Test, Ticker-Mapping Klassen-Titel „.“→„-“ |
| 3 | Reparatur-Agent: liest rote Läufe, öffnet einen PR, CI beweist, Easy merged | **erste Ausbaustufe gebaut** (#49, 08.09.) — schmal auf Datumsformat-Drift bei iShares begrenzt, siehe §4 Punkt 3. Weitere Fehlerklassen: offen, Easys Entscheid. |

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
| **Handelbarkeit** | Median-Tagesumsatz ≥ 5 Mio. über 3 Monate — **kein Signal**, nur Vorfilter | `config.py:46` |
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

*Kursvergleich-Zweitquellen (Stufe 2a/2b) fehlen hier noch als eigene
Zeile — siehe §4 Punkt 5, gemeldet, nicht in dieser Nachziehung ergänzt.*

**Literatur** — vollständig in `src/momentum/sources.py`, wörtlich auf der
Methodik-Seite: Jegadeesh & Titman (1993), Jegadeesh (1990), George & Hwang
(2004), Rouwenhorst (1998), Moskowitz/Ooi/Pedersen (2012), Daniel &
Moskowitz (2016), Jegadeesh & Titman (2023), Fama & French (2012), Asness
(2011), Chui/Titman/Wei (2010).

### 7.6 Die Score-Formel

`Score 0–100 = 50 × Perzentil(12-1) + 50 × Perzentil(52W-Nähe)`,
Perzentile **immer nur innerhalb eines Marktes**, Gleichstände deterministisch
(höherer Score zuerst, dann Ticker A→Z). **50/50, weil die Literatur kein
Mischverhältnis liefert** — jedes andere Verhältnis wäre eine unbelegte
Setzung. Beide Teil-Ränge stehen sichtbar auf jeder Karte.

Die Trend-Ampel ist **reine Anzeige** und rührt Score, Perzentile und
Rangfolge nie an — festgehalten in
`tests/unit/test_trend_ueberschuss.py::test_der_zins_ruehrt_score_und_rangfolge_nicht_an`.

### 7.7 Anzeige

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
    Code ändert, aber keiner explizit die Doku nachzieht. Kein Automatismus
    dagegen eingerichtet (wäre selbst ein eigener, zu klärender Auftrag) —
    hier nur benannt, damit die nächste Lücke wenigstens auffällt.

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
