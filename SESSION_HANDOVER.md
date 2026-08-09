# Session-Handover — Momentum-Report

**Stand: 09.08.2026** (Sonntag), nach dem Kosmetik-Durchgang. Repo
`easywebb911/Momentum-Report`, Branch `main` — den aktuellen Stand nennt
`git log -1`, er steht hier bewusst nicht als Zahl.

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

---

## 1. Betriebszustand (09.08.2026)

| Sache | Zustand | Beleg |
|---|---|---|
| GitHub Pages | **aktiv** seit 02.08., deployt bei jedem Push auf `main` | Workflow `pages-build-deployment` (`dynamic/pages/pages-build-deployment`), angelegt 02.08.2026 16:11 — Zähler und letzter Lauf in Actions |
| Momentum-Lauf | läuft werktäglich, **bisher kein Fehlschlag** | Actions-Liste `lauf.yml`; der jeweils letzte Lauf steht als Commit „Lauf N" im `git log` |
| Ranking | eingefroren zum **31.07.2026**, beide Märkte | `data/rankings/us_2026-07.json`, `de_2026-07.json` |
| US-Top-5 | VLO, DVA, MRK, VTRS, ROST — aus 500 bewerteten von 503 | `us_2026-07.json` → `top`, `abdeckung` |
| DE-Top-5 | DHL.DE, DWS.DE, ALV.DE, TKA.DE, SIE.DE — aus 85 bewerteten von 102 | `de_2026-07.json` |
| Universen | **beide VERIFIED**, Stand 03.08.2026 | `universe/universe_us.txt`, `universe_de.txt` (Kopfzeile `# STATUS: VERIFIED`) |
| Beschreibende Angaben | vorhanden (Name + Sektor je Ticker) | `universe/ticker_meta_us.json`, `ticker_meta_de.json`, seit `c97e3f4` |
| Konfluenz-Export | `docs/data/top5.json` vorhanden, seit `e695b54` (Lauf 9) unverändert — korrekt, das Ranking ist eingefroren | Datei + `git log -- docs/data/top5.json` |
| Trend-Ampel auf der Seite | zeigt für **beide** Märkte die Preisrendite mit dem Hinweis *„ohne Zins-Abzug — dieses Ranking entstand vor der Umstellung"* | `docs/index.html`; erwartetes Verhalten, siehe §4 |
| ntfy-Push | **verdrahtet und angekommen** — Probe am 08.08. auf dem Handy bestätigt | Lauf 19 (`workflow_dispatch`, `success`, Job 93120989543) |
| Kurse | Stand je Markt in `kurse_vom` | `data/status.json` |
| Tests | vollständig grün | `pytest` (Zähler bewusst nicht abgeschrieben — er wächst mit jedem PR) |
| Offene PRs | **keine** | GitHub-PR-Liste, Status `open` = leer |

**Cron-Fahrplan** (`.github/workflows/`):

| Workflow | Auslöser | Datei |
|---|---|---|
| Momentum-Lauf | `45 21 * * 1-5` (werktags 21:45 UTC) + manuell | `lauf.yml` |
| Datenquelle prüfen | `15 6 * * 1` (montags 06:15 UTC) + manuell | `datenquelle.yml` |
| Vertragstest | `0 8 25-31 * *` + Wochentag-Riegel im Job (Cron kann Tag-des-Monats und Wochentag nur mit ODER) + manuell | `vertrag.yml` — schweigt im Normalfall, ein Push mit allen Brüchen |
| Wächter (Totmannschalter) | `30 7 * * 1` (montags 07:30 UTC) + manuell | `waechter.yml` — schweigt im Normalfall, Alarm-Push + roter Lauf ab > 4 Tagen Stille |
| Universum aktualisieren | **nur manuell** | `universum.yml` |
| Tests | jeder Push und jeder PR | `tests.yml` |

Am Wochenende läuft nichts. Ist der letzte Lauf von Freitag, ist das
kein Ausfall, sondern der Fahrplan.

---

## 2. Gemergte Arbeit (#1–#21)

Alle Merge-Commits liegen auf `main`. Die Merge-Klasse steht ab #14 im
PR-Titel; davor wurde sie je Auftrag im Chat vereinbart und ist im Repo
nicht dokumentiert (bei #1–#3 deshalb „—").

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

#19–#21 fielen in die Nacht zum 09.08. (MESZ); in UTC tragen sie noch den
08.08. — deshalb die Uhrzeiten in den Belegen.

---

## 3. Wiedervorlagen (mit Datum)

| Wann | Was | Warum |
|---|---|---|
| **31.08.2026** (Mo) | **Monats-Stichtag.** Der erste Lauf danach bildet das August-Ranking. | Erster Stichtag *nach* #16 — hier greift die Überschuss-Ampel zum ersten Mal mit echten Zahlen. Danach prüfen: Tragen beide Märkte `riskfree_12m ≠ null`? Steht auf der Seite „über Geldmarkt" statt des Umstellungs-Hinweises? Kam der Ranking-Push an? Der Probe-Push vom 08.08. belegt Thema und Sendeweg — `push_new_ranking` baut aber eine andere Nachricht und ist bisher nur durch Unit-Tests gedeckt. |
| **01.09.2026** | Erster Vergleich zweier Monats-Ranglisten (Juli → August). | Ab hier lässt sich zum ersten Mal sehen, wie stark die Top-5 wechseln. |
| **Anfang September 2026** | **Monatsende auswerten → Hygiene-Block → Stufe 3.** In dieser Reihenfolge: erst das erste scharfe Monatsende (31.08.) auswerten, dann den Hygiene-Backlog (§5: default-deny, Node-20), dann den Reparatur-Agenten bauen. | Easys Termin-Entscheid vom 09.08. Die Auswertung liefert die Bau-Grundlage für Stufe 3 — bis dahin wüsste ein Reparatur-Agent gar nicht, welche Sorten Rot es überhaupt gibt. Begründung im Stufenplan (§6). |
| **Herbst 2026** (ab ~Nov, ≥ 4 Stichtage) | **Ranking-Verlauf.** Entscheiden, ob die Seite eine Historie zeigt. | Vorher gibt es nichts zu zeigen. Achtung: eine Verlaufs-Anzeige darf keine Trefferquote implizieren — das Werkzeug misst keine Performance (siehe §6, Roadmap). |
| **laufend, montags** | `Datenquelle prüfen` läuft gegen Yahoo. | Schlägt sie fehl, ist die Kursquelle das Problem, nicht der Code. |

---

## 4. Offene Punkte

**1. Der Umstellungs-Hinweis steht bis zum 31.08. auf der Seite.** *(erwartet, kein Fehler)*

Die Juli-Rankings sind eingefroren und tragen die Felder `riskfree_12m` /
`ueberschuss_12m` nicht — sie entstanden vor #16. Die Anzeige sagt das
wörtlich: *„ohne Zins-Abzug — dieses Ranking entstand vor der Umstellung"*.
Der ehrliche Zwischenzustand verschwindet mit dem August-Ranking von selbst.
**Nichts tun.** Insbesondere nicht die Juli-Dateien löschen, um „schöne"
Zahlen zu erzwingen.

**2. `^SP500TR`-Historientiefe im Ernstfall.** *(beobachten)*

Extern verifiziert waren 251 Tageskurse über das Jahr — genug. Reicht die
Reihe an einem künftigen Stichtag nicht, greift der laute Abbruch
(`Keine Indexdaten … ohne Handelskalender kein Stichtag`), kein stiller
Rückfall. Träte das ein, wäre die Frage: Kursindex als Notnagel (nein) oder
Stichtag verschieben (ja).

**3. Stufe 3 (Reparatur-Agent) hat jetzt einen Termin.** *(nichts tun bis September)*

Easy hat am 09.08. entschieden: **Anfang September**, nach Auswertung des ersten scharfen Monatsendes. Die datierte Wiedervorlage steht in §3, die Begründung und die unveränderte harte Grenze im Stufenplan (§6). Hier steht sie nur, damit sie auch von den offenen Punkten aus auffindbar ist — es gibt bis dahin nichts zu tun.

---

## 5. Hygiene-Backlog

Kleinarbeit ohne Dringlichkeit — jeweils ein eigener kleiner PR.

1. **Testkontext auf default-deny umstellen — bewusst erst NACH dem
   31.08.**, weil er die Testinfrastruktur anfasst und die vor dem ersten
   scharfen Stichtag unbewegt bleiben soll. Heute blockieren die
   Browser-Tests *namentlich* zwei Hosts (`quote-proxy.easywebb.workers.dev`,
   `easywebb911.github.io/Elliott-Report`); die EZB-Verbindung sperrt eine
   autouse-Fixture in `tests/conftest.py`. Das ist default-allow: ein
   künftiger externer Host wäre stillschweigend erlaubt. Richtig wäre
   `kontext.route("**/*", …)` mit einer Ausnahme für `127.0.0.1` — also
   alles gesperrt, was nicht der Testserver ist. Belegstelle: die beiden
   `kontext.route(...)`-Aufrufe in `tests/design/conftest.py`.
2. **`Node.js 20 is deprecated`-Warnung** in jedem Lauf: `actions/checkout@v4`
   und `actions/setup-python@v5` auf aktuelle Fassungen heben.

Erledigt und deshalb nicht mehr aufgeführt: die Kosmetik-Punkte (tote
CSS-Regel, tote Symbole, verwaiste Fixture, doppeltes Literal, zu breite
`window.MR`-Ausfuhr, liegengebliebene Branches, `.gitignore`) sowie die
Doku-Drift durch abgeschriebene Zähler. Die README-Modulliste ist kein
Backlog-Punkt mehr, sondern eine Daueraufgabe — sie steht in den Lessons.

---

## 6. Roadmap

Ausdrücklich **keine** Zusage, nur die Liste der Dinge, die als Nächstes
sinnvoll wären — in dieser Reihenfolge:

1. **Nach dem 31.08.:** Die Überschuss-Ampel im echten Betrieb ansehen. Sind
   die Geldmarktsätze plausibel (US ~3,7 %, EUR ~2,2 %)? Sagt die Box, was
   sie soll?
2. **Ranking-Verlauf** (Herbst, ≥ 4 Stichtage) — Anzeige der bisherigen
   Monats-Ranglisten. Harte Grenze: keine Renditeberechnung, keine
   Trefferquote, keine Performance-Kurve. Das Werkzeug misst keine
   Ergebnisse, es zeigt eine Rangfolge.
3. **Risikogesteuerte Varianten** (Daniel & Moskowitz 2016) — in `README`
   bereits als „dokumentiert, aber erst v1" geführt.

**Selbstwartungs-Stufenplan** (Easys Richtung vom 09.08. — „ein Tool, das
sich selbst wartet"; die Maschine arbeitet, Easy behält den Ein-Tipp-Veto):

| Stufe | Was | Stand |
|---|---|---|
| 0 | Totmannschalter (`waechter.yml`) | **gebaut** |
| 1 | Vertragstests je Fremdquelle, werktags im Fenster 25.–31. | **gebaut** |
| 2a | Zweite Kursquelle **DE** mit Vergleichsgatter (kein stiller Fallback; Muster: `riskfree_quelle`) | **gebaut** — erstmals scharf am 31.08. |
| 2b | Zweite Kursquelle **US** (S&P-500-UCITS-Bestandslisten) | in Kalibrierung — Anker und Toleranz werden gemessen, nicht gesetzt |
| 3 | Reparatur-Agent: liest rote Läufe, öffnet einen PR, CI beweist, Easy merged | offen — **entschieden 09.08.: Anfang September**, nach Auswertung des ersten scharfen Monatsendes (31.08.) |

*Warum der September und nicht früher:* Bis dahin ist das Fundament 0–2 komplett (2b in Kalibrierung), das erste scharfe Monatsende liefert die echten Rot-Sorten als Bau-Grundlage statt ausgedachter, und der Termin fällt in denselben September-Block wie default-deny und Node-20.

Die harte Grenze der Stufe 3 gilt **unverändert weiter**: Der Agent öffnet PRs, die CI beweist, **Easy merged**. Kein Auto-Merge agentengeschriebener Fixes — der Termin ändert daran nichts.

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

Ausnahme: alles, was ein **Ranking** verfälschen könnte, bricht laut ab.
Anzeige darf weich ausfallen, Rechnung nicht.

### 7.4 Merge-Klassen

| Klasse | Wer merged | Wann |
|---|---|---|
| **MANUAL-MERGE** | Easy | Score-/Warnlogik, Universums-Logik, Token-Mechanik, neue externe Datenquelle, additive Schema-Felder |
| **SELF-MERGE bei grünem CI** | Claude, nach zwei grünen `tests`-Läufen und ohne offene Kommentare | rein dekoratives Frontend, Bug-Fixes ohne Logikänderung, Doku |

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
  Code und auf der Methodik-Seite.

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
- **Farben sind Semantik:** `--grn` nur positiv, `--red` nur negativ,
  `--ora` nur Warnlage, `--disc` **ausschließlich** Ehrlichkeits-Aussagen
  (erlaubt an `.disc-title`, `.card-ft`, `.konf-regel` — die Liste wächst nur
  um Stellen, die wirklich eine Einschränkung aussprechen).
- **Konfluenz-Seite:** zwei Werkzeuge nebeneinander. **Kein gemeinsamer
  Score, keine Wahrscheinlichkeit, keine Rangfolge der Treffer.** Treffer
  stehen alphabetisch — jede andere Reihenfolge wäre eine Aussage darüber,
  welcher der bessere ist.
- **Alles rendert aus `render.py`.** Sichtbar wird eine Änderung erst, wenn
  der nächste `Momentum-Lauf` `docs/index.html` neu erzeugt.
  `docs/index.html` wird **niemals** von Hand gelöscht und neu gebaut — dort
  steht die echte, ausgelieferte Rangliste.

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
3. **Fehlende Neuaufnahme ist tückischer als ein Parse-Fehler.** Ein Ticker,
   den die Liste nicht enthält, kann in keiner Kursprüfung durchfallen. Nur
   ein Stichtag deckt so etwas auf — deshalb die ETF-Listen mit Stichtag
   statt Wikipedia.
4. **`^…$` ist in Python nicht `\A…\Z`.** `^[-_A-Za-z0-9]{1,64}$` hätte
   `"thema\n"` durchgelassen — genau den Fehler, der den ntfy-Push mit
   HTTP 400 killte. In `notify.py` steht deshalb `\A…\Z`.
5. **Tests, die nach draußen telefonieren, sind keine Tests.** Zweimal rot
   auf CI, weil die Browser-Tests lokal (Egress-Sperre) grün waren und auf
   dem Runner den echten Dienst erreichten. Externe Hosts werden im
   Testkontext gesperrt — siehe Hygiene-Backlog Punkt 1.
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
| ntfy-Versand nachgewiesen | Probe-Push, Lauf 19 am 08.08. | Lauf 19 `success`; Easy hat den Empfang auf dem Gerät bestätigt. Die Probe geht durch **denselben** `push()` wie jeder echte Push (`notify.push_test`) — sie belegt damit Thema, Sendeweg und Fehlerbehandlung, nicht nur einen Sonderpfad. Damit ist der `HTTP 400 topic invalid` aus Lauf 2 (02.08., vor der Härtung aus #9) abgehakt. |
| Score auf 50/50 vor dem ersten Lauf | #8, gemergt 20:39 UTC, Ranking entstand 20:47 UTC | `f10dad9` vs. `07cbedd` |
| **Zins-Pfad live bewiesen** (war S1 der Pflege-Inventur) | Wegwerf-Probe #19, [Lauf 1 am 08.08. 23:15 UTC](https://github.com/easywebb911/Momentum-Report/actions/runs/31283577911) | Beide Proben grün. US: Rendite +19,56 %, Geldmarkt **+3,71 %** (`^IRX`), Überschuss +15,86 %. DE: +6,50 %, **+1,96 %** (€STR über die EZB), +4,54 %. **Kein fail-soft** — die EZB antwortet aus dem Runner heraus. |
| **Korrekturweg + Determinismus live bewiesen** | dieselbe Probe, Teil B | `de_2026-07.json` gelöscht und neu gebaut: Rangliste, Top-5, Abdeckung, Methode, Stichtag **bitgleich**; `rendite_12m` +6,4980 % alt wie neu; Wiederherstellung bitgleich, `git status` leer. |
| Wegwerf-Probe wieder entfernt | #20 | `42f5653` — Workflow, Skript und Test raus; der Lauf bleibt als Protokoll in Actions |
| Test-Werkzeuge gepinnt, beide erzeugten Seiten in der CI-Frischeprüfung, Zeit-Deckel in allen vier Workflows | #21 (S2/S3/S4 der Inventur) | `645401e`, `requirements-dev.txt`, `tests/unit/test_workflow_hygiene.py` |
| Kosmetik: tote CSS-Regel, tote Symbole, verwaiste Fixture, doppeltes Literal, zu breite `window.MR`-Ausfuhr, alte Branches, `.gitignore` | dieser PR | siehe PR-Text; Suite grün als Nachweis der Verhaltens-Neutralität |
