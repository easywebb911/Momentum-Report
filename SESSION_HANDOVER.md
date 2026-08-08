# Session-Handover — Momentum-Report

**Stand: 08.08.2026** (Samstag). Repo `easywebb911/Momentum-Report`, Branch `main` bei `42b04a4`.

Dieses Dokument ist der Übergabepunkt zwischen zwei Arbeits-Sitzungen. Es
beantwortet drei Fragen: *Was läuft gerade?*, *Was ist offen?*, *Was darf
man nicht kaputtmachen?*

**Belegregel für dieses Dokument:** Jede Aussage hier ist am Repo
nachprüfbar — durch einen Commit-Hash, eine Datei oder ein Lauf-Protokoll.
Der Beleg steht jeweils dabei. Was sich nicht belegen lässt, steht als
*ungeprüft* markiert und nicht als Tatsache.

---

## 1. Betriebszustand (08.08.2026)

| Sache | Zustand | Beleg |
|---|---|---|
| GitHub Pages | **aktiv** seit 02.08., 36 Deployments, letztes 07.08. erfolgreich | Workflow `pages-build-deployment` (`dynamic/pages/pages-build-deployment`), angelegt 02.08.2026 16:11 |
| Momentum-Lauf | **18 Läufe, alle erfolgreich**, letzter am 07.08. 22:17 UTC | `git log` → `42b04a4 Lauf 18`; Actions-Liste `lauf.yml` |
| Ranking | eingefroren zum **31.07.2026**, beide Märkte | `data/rankings/us_2026-07.json`, `de_2026-07.json` |
| US-Top-5 | VLO, DVA, MRK, VTRS, ROST — aus 500 bewerteten von 503 | `us_2026-07.json` → `top`, `abdeckung` |
| DE-Top-5 | DHL.DE, DWS.DE, ALV.DE, TKA.DE, SIE.DE — aus 85 bewerteten von 102 | `de_2026-07.json` |
| Universen | **beide VERIFIED**, Stand 03.08.2026 | `universe/universe_us.txt`, `universe_de.txt` (Kopfzeile `# STATUS: VERIFIED`) |
| Beschreibende Angaben | vorhanden (Name + Sektor je Ticker) | `universe/ticker_meta_us.json`, `ticker_meta_de.json`, seit `c97e3f4` |
| Konfluenz-Export | `docs/data/top5.json` vorhanden, seit `e695b54` (Lauf 9) unverändert — korrekt, das Ranking ist eingefroren | Datei + `git log -- docs/data/top5.json` |
| Trend-Ampel auf der Seite | zeigt für **beide** Märkte die Preisrendite mit dem Hinweis *„ohne Zins-Abzug — dieses Ranking entstand vor der Umstellung"* | `docs/index.html`; erwartetes Verhalten, siehe §4 |
| Kurse | US vom 07.08., DE vom 06.08. | `data/status.json` |
| Tests | 385 Unit + 120 Design, alle grün | `pytest tests/unit`, `pytest tests/design` (08.08.) |
| Offene PRs | **keine**, 16 von 16 gemergt | GitHub-PR-Liste, Status `open` = leer |

**Cron-Fahrplan** (`.github/workflows/`):

| Workflow | Auslöser | Datei |
|---|---|---|
| Momentum-Lauf | `45 21 * * 1-5` (werktags 21:45 UTC) + manuell | `lauf.yml` |
| Datenquelle prüfen | `15 6 * * 1` (montags 06:15 UTC) + manuell | `datenquelle.yml` |
| Universum aktualisieren | **nur manuell** | `universum.yml` |
| Tests | jeder Push und jeder PR | `tests.yml` |

Am Wochenende läuft nichts — deshalb ist der letzte Lauf vom Freitag, den
07.08., und nicht von heute. Das ist kein Ausfall.

---

## 2. Gemergte Arbeit (#1–#16)

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

---

## 3. Wiedervorlagen (mit Datum)

| Wann | Was | Warum |
|---|---|---|
| **31.08.2026** (Mo) | **Monats-Stichtag.** Der erste Lauf danach bildet das August-Ranking. | Erster Stichtag *nach* #16 — hier greift die Überschuss-Ampel zum ersten Mal mit echten Zahlen. Danach prüfen: Tragen beide Märkte `riskfree_12m ≠ null`? Steht auf der Seite „über Geldmarkt" statt des Umstellungs-Hinweises? Kam der ntfy-Push an (siehe §4)? |
| **01.09.2026** | Erster Vergleich zweier Monats-Ranglisten (Juli → August). | Ab hier lässt sich zum ersten Mal sehen, wie stark die Top-5 wechseln. |
| **Herbst 2026** (ab ~Nov, ≥ 4 Stichtage) | **Ranking-Verlauf.** Entscheiden, ob die Seite eine Historie zeigt. | Vorher gibt es nichts zu zeigen. Achtung: eine Verlaufs-Anzeige darf keine Trefferquote implizieren — das Werkzeug misst keine Performance (siehe §6, Roadmap). |
| **laufend, montags** | `Datenquelle prüfen` läuft gegen Yahoo. | Schlägt sie fehl, ist die Kursquelle das Problem, nicht der Code. |

---

## 4. Offene Punkte

**1. ntfy-Push ist nie nachweislich angekommen.** *(offen, mit Belegen)*

- Das Secret ist gesetzt: im Lauf-Protokoll steht `NTFY_TOPIC: ***` — GitHub
  maskiert nur belegte Secrets.
- Der Code ist gehärtet (#9): Topic wird `strip`-t und gegen
  `\A[-_A-Za-z0-9]{1,64}\Z` geprüft, bevor gesendet wird; der Antwort-Body
  landet redigiert im Protokoll.
- Die Verdrahtungsprobe existiert (#13): `Momentum-Lauf` → `testpush`.
- **Aber:** Ein echter Ranking-Push ging genau einmal raus — in Lauf 2 am
  02.08., beim ersten Einfrieren (`git log --diff-filter=A -- data/rankings/`
  → nur `07cbedd`, Lauf 2). Das war **vor** der Härtung aus #9, und dieser
  Push scheiterte laut externem Befund mit `HTTP 400 topic invalid`.
  Seither wurde kein neues Ranking gebildet, also auch kein Push versendet.
  Im geprüften Lauf 13 (04.08.) steht keine Push-Zeile im Protokoll — die
  Probe war dort nicht eingeschaltet.
- **Nächster Schritt:** einmal `Momentum-Lauf` mit `testpush = true` starten
  und im Protokoll nachsehen. Sonst fällt es erst am 31.08. auf, wenn die
  einzige Benachrichtigung des Monats ausbleibt.

**2. Der Umstellungs-Hinweis steht bis zum 31.08. auf der Seite.** *(erwartet, kein Fehler)*

Die Juli-Rankings sind eingefroren und tragen die Felder `riskfree_12m` /
`ueberschuss_12m` nicht — sie entstanden vor #16. Die Anzeige sagt das
wörtlich: *„ohne Zins-Abzug — dieses Ranking entstand vor der Umstellung"*.
Der ehrliche Zwischenzustand verschwindet mit dem August-Ranking von selbst.
**Nichts tun.** Insbesondere nicht die Juli-Dateien löschen, um „schöne"
Zahlen zu erzwingen.

**3. `^SP500TR`-Historientiefe im Ernstfall.** *(beobachten)*

Extern verifiziert waren 251 Tageskurse über das Jahr — genug. Reicht die
Reihe an einem künftigen Stichtag nicht, greift der laute Abbruch
(`Keine Indexdaten … ohne Handelskalender kein Stichtag`), kein stiller
Rückfall. Träte das ein, wäre die Frage: Kursindex als Notnagel (nein) oder
Stichtag verschieben (ja).

---

## 5. Hygiene-Backlog

Kleinarbeit ohne Dringlichkeit — jeweils ein eigener kleiner PR.

1. **Testkontext auf default-deny umstellen.** Heute blockieren die
   Browser-Tests *namentlich* zwei Hosts (`quote-proxy.easywebb.workers.dev`,
   `easywebb911.github.io/Elliott-Report`) und die EZB-Verbindung über eine
   autouse-Fixture (`tests/conftest.py:85`). Das ist default-allow: ein
   künftiger externer Host wäre stillschweigend erlaubt. Richtig wäre
   `kontext.route("**/*", …)` mit einer Ausnahme für `127.0.0.1` — also
   alles gesperrt, was nicht der Testserver ist. Belegstellen:
   `tests/design/conftest.py:270` und `:275`.
2. **`Node.js 20 is deprecated`-Warnung** in jedem Lauf: `actions/checkout@v4`
   und `actions/setup-python@v5` auf aktuelle Fassungen heben.
3. **README-Aufbau-Liste** vollständig halten — sie zählt Module auf und
   veraltet bei jedem neuen Modul (zuletzt bei `riskfree.py` passiert).

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
| GitHub Pages aktivieren | Easy, 02.08. | Workflow `pages-build-deployment` seit 02.08. 16:11, 36 erfolgreiche Deployments |
| Universum befüllen (beide Märkte) | `Universum aktualisieren`, Lauf 7 | `c97e3f4`, beide Dateien `# STATUS: VERIFIED`, Stand 03.08. |
| Erstes Ranking bilden | `Momentum-Lauf` Lauf 2, 02.08. | `07cbedd`, `data/rankings/*_2026-07.json` |
| `ticker_meta_*.json` erzeugen (Sektor + Name auf den Karten) | Lauf 7 | `universe/ticker_meta_us.json`, `ticker_meta_de.json` |
| `docs/data/top5.json` auf die Seite bringen | Lauf 9 | `e695b54` |
| Tacho, Chart-Verweise, Sektorzeilen, Live-Anker live | Läufe ab 03.08. | `docs/index.html`: 6 × `tta-`, 20 × `stockanalysis.com`, 20 × `data-quote` |
| Konfluenz-Seite ausgeliefert | #14/#15 | `docs/konfluenz.html`, ☰-Eintrag in `docs/index.html` |
| `NTFY_TOPIC` gesetzt | Easy | `NTFY_TOPIC: ***` im Lauf-Protokoll (nur belegte Secrets werden maskiert) — **aber** siehe §4.1: der Versand selbst ist unbelegt |
| Score auf 50/50 vor dem ersten Lauf | #8, gemergt 20:39 UTC, Ranking entstand 20:47 UTC | `f10dad9` vs. `07cbedd` |
