# Momentum-Report

Anwendungs-Werkzeug auf belegter Wissenschaft. Es zeigt je Markt (USA,
Deutschland) die fünf Titel mit dem stärksten Momentum nach einer
veröffentlichten, nachgerechneten Methode — und sagt gleichzeitig deutlich,
was es damit **nicht** behauptet.

**Tragendes Prinzip: Literaturtreue ersetzt Validierung.** Jede Zutat des
Scores hat eine Primärquelle — im Code-Kommentar *und* auf der
Methodik-Seite. Die Tests beweisen „rechnet exakt die dokumentierte Formel",
niemals „trifft es".

Seite: `https://easywebb911.github.io/Momentum-Report/` (nach Aktivierung
von GitHub Pages, siehe unten)

## Was gerechnet wird

| Zutat | Gewicht | Quelle |
|---|---|---|
| 12-1-Momentum (jüngster Monat übersprungen) | 50 % | Jegadeesh & Titman (1993), *The Journal of Finance*; Jegadeesh (1990) |
| Nähe zum 52-Wochen-Hoch | 50 % | George & Hwang (2004), *The Journal of Finance* |

Score `0–100 = 50 × Perzentil(12-1) + 50 × Perzentil(52W-Nähe)`,
Perzentile **immer nur innerhalb eines Marktes** (Rouwenhorst 1998),
Gleichstände deterministisch alphabetisch gebrochen.

**Warum gleichgewichtet.** Die Literatur liefert *kein* Mischverhältnis für
diese beiden Zutaten — sie untersucht sie als getrennte Strategien und
vergleicht sie; bei George & Hwang war für den US-Markt sogar die
52-Wochen-Nähe die stärkere. Wo Arbeiten mehrere solcher Größen
zusammenfassen, gewichten sie üblicherweise gleich. Jedes andere Verhältnis
wäre eine unbelegte Setzung. Damit die Mischung sichtbar bleibt, führt jeder
Titel **zusätzlich beide Teil-Ränge** (`rank_12_1`, `rank_52w`) — auf der
Karte als „3. von 470".

Dazu je Markt eine **Trend-Ampel** (Moskowitz/Ooi/Pedersen 2012): steht der
Index über zwölf Monate im Minus, erscheint eine Warnung (Daniel &
Moskowitz 2016). Reine Anzeige — sie greift nie ins Ranking ein.

## Der monatliche Stichtag

Das Ranking entsteht **einmal pro Monat**, zum letzten Handelstag; erstmals
rückwirkend zum 31.07.2026. Danach ist es eingefroren: werktägliche Läufe
aktualisieren **nur** die angezeigten Kurse.

Das ist nicht bloß Konvention, sondern technisch verriegelt:

* Eine geschriebene Ranking-Datei wird nie überschrieben
  (`ranking.write_ranking`).
* An einem gewöhnlichen Tag lädt der Lauf nur die Kurse der fünf
  eingefrorenen Titel — die Daten für ein neues Ranking werden gar nicht
  erst beschafft.

Fällt der letzte Werktag auf einen Feiertag, holt der erste Lauf des
Folgemonats das Ranking mit dem korrekten Stichtag nach — mit demselben
Ergebnis, als wäre es am Stichtag selbst entstanden.

**Ein geschriebenes Ranking korrigieren** geht bewusst nur auf einem Weg:
die betreffende Datei unter `data/rankings/` von Hand aus dem Repo löschen.
Es gibt keinen Schalter und keine Neuberechnung — sonst wäre die
Einfrierung keine. Nach dem Löschen bildet der nächste Lauf den Monat mit
korrektem Stichtag neu.

## Woher das Universum kommt

| Markt | Quelle | Schutz gegen Veraltung |
|---|---|---|
| USA | Wikipedia *List of S&P 500 companies* | laufend gepflegter Artikel |
| Deutschland | tägliche Holdings-CSVs der iShares-ETFs EXS1 / EXS3 / EXS2 | **Veraltungs-Gatter**: Bestands-Stichtag älter als 10 Handelstage → Abbruch |

Der deutsche Weg lief anfangs ebenfalls über Wikipedia und ist daran
gescheitert: die englischen Artikel zu den DE-Indizes waren jahrealt
(TecDAX zuletzt eine bloße Namensliste ohne Symbole). Das Tückische daran
ist nicht der Parse-Fehler, sondern die **fehlende Neuaufnahme** — ein
Ticker, den es in der Liste nicht gibt, kann in keiner Kursprüfung
durchfallen. Nur ein Stichtag deckt so etwas auf, und genau den führen die
ETF-Bestandslisten mit.

Gegen eine **vertauschte URL** prüft der Bootstrap die Zahl der
Aktien-Zeilen gegen den erwarteten Bereich des Index: DAX 38–42, MDAX
48–52, TecDAX 28–32. Diese Bereiche überlappen nicht — landet die
MDAX-Datei unter der DAX-Adresse, kommen 50 Zeilen an, wo 38–42 erwartet
werden, und der Lauf bricht ab, statt still ein falsches Universum zu
bauen. (Der Fondsname taugte dafür nicht: die echten deutschen
Bestandslisten führen gar keinen, ihr ganzer Vorspann ist eine Zeile mit
dem Stichtag.)

## Das Universum ist default-deny

Gerechnet wird **nur** mit einer Universums-Datei, die ausdrücklich
`# STATUS: VERIFIED` trägt. Diese Zeile schreibt allein
`tools/build_universe.py`, und zwar erst, nachdem **jeder einzelne Ticker**
gegen echte Kursdaten geprüft wurde.

Abgelehnt wird alles andere: der ausgelieferte Platzhalter, eine Datei ohne
Statuszeile, mit fremdem Status oder halb geschrieben. Der Riegel greift
**vor** dem Datenabruf — bei einem ungeprüften Universum wird nicht ein
einziger Kurs angefragt, es kann also gar kein Ranking entstehen, das
einfrieren könnte.

Folge, die man kennen muss: Wird ein Universum später wieder auf
`PLACEHOLDER` gesetzt, obwohl schon ein echtes Ranking existiert, verweigert
auch der gewöhnliche Anzeige-Lauf den Dienst — die Kurse werden dann nicht
mehr aktualisiert und die Seite friert auf dem letzten guten Stand ein. Das
ist gewollt. Wer nur die Läufe stoppen will, schaltet stattdessen den
Workflow ab.

## Was dieses Werkzeug bewusst NICHT tut

Keine Sammlung, keine Registry, kein Backtesting, keine Trefferquoten,
keine Kursziele, keine Invalidierungen, kein Long-Short, kein Intraday,
keine Zutat ohne Quelle, keine risikogesteuerten Varianten (dokumentiert,
aber erst v1), keine Watchlist, keine KI-Kommentare, keine Neuberechnung
des Rankings auf Knopfdruck.

## Aufbau

```
src/momentum/
  sources.py     Quellenverzeichnis — die EINE Wahrheit für Belege
  config.py      alle Stellschrauben als benannte Konstanten
  scoring.py     die Rechenkerne (reine Funktionen, kein Netz)
  ranking.py     Stichtags-Mechanik, Handelbarkeits-Filter, Einfrieren
  data.py        einzige Stelle mit Netzzugriff (yfinance)
  render.py      HTML für docs/ — Methodik-Seite wird aus sources.py erzeugt
  notify.py      ntfy-Push
  run.py         Einstiegspunkt des Laufs
universe/        committete statische Listen, Status VERIFIED + Herkunft
data/rankings/   die eingefrorenen Monats-Rankings (JSON, ohne Zeitstempel)
docs/            die veröffentlichte Seite (GitHub Pages)
tools/           Bootstrap für die Universums-Listen
tests/unit       ohne Netz, mit von Hand nachgerechneten Sollwerten
tests/design     Layout-Messung im echten Browser bei 390 px
tests/network    Nachweise gegen die echte Kursquelle (wöchentlich)
```

## Läufe

| Workflow | Auslöser | Zweck |
|---|---|---|
| `Momentum-Lauf` | werktags 21:45 UTC + manuell | Kurse aktualisieren, am Stichtag das Monats-Ranking bilden |
| `Universum aktualisieren` | **nur manuell** | Universums-Listen neu ziehen und prüfen |
| `Tests` | jeder Push / PR | Wert-, Mutations-, Determinismus- und Layout-Tests |
| `Datenquelle prüfen` | montags + manuell | Netz-Nachweise gegen Yahoo |

## Die Seite bedienen

Das ☰-Menü steht auf **jeder** Seite; jede Unterseite trägt oben zusätzlich
einen **← Zurück**-Link. Der ist kein Schmuck: als installierte PWA läuft
das Werkzeug im Standalone-Modus, ohne Adresszeile und ohne Zurück-Taste
des Browsers — ohne diesen Link wäre die Methodik-Seite eine Sackgasse.

| Menüpunkt | Was passiert |
|---|---|
| **Neu laden** | holt dieselbe Seite frisch (Cache-Brecher am Zeitstempel) und tauscht den Inhalt aus — ohne die Seite neu zu öffnen |
| **Neu berechnen** | stößt den `Momentum-Lauf` per `workflow_dispatch` auf `main` an und verfolgt ihn bis zum Ende |
| **Sperren** | verwirft den gespeicherten Zugriffs-Token sofort |

**Neu berechnen** braucht einen **Fine-grained Personal Access Token** —
nur für dieses Repository, mit *Actions: Read and write* und *Contents:
Read and write*. Ohne gespeicherten Token passiert **nichts Stilles**: der
Knopf öffnet den Dialog, der erklärt, wo der Token entsteht.

Zum Token, unbeschönigt:

* Er liegt **auf dem Gerät** (IndexedDB), 28 Tage, danach wird erneut
  gefragt. Er steht in keiner Adresszeile, in keiner Protokollausgabe und
  nirgends im Repository; er geht ausschließlich als
  `Authorization`-Kopfzeile an `api.github.com`.
* Wer das entsperrte Gerät in die Hand bekommt, kann ihn benutzen. Das ist
  die Grenze des Verfahrens — deshalb der Punkt *Sperren*, und deshalb ein
  Token, der nur dieses eine Repository erreicht.

Während der Lauf läuft, zeigt ein Banner unten die Sekunden. Es zählt
**nicht** ewig: Schlägt der Lauf fehl, wird das Banner rot und verweist auf
das Actions-Protokoll; nach 10 Minuten ohne Ergebnis sagt es genau das.
Läuft der Lauf durch, werden die Daten geholt und die Seite aktualisiert.

## Einrichtung (einmalig, in der GitHub-Oberfläche)

1. **GitHub Pages aktivieren** — Settings → Pages → Source:
   *Deploy from a branch* → Branch `main`, Ordner `/docs`.
2. **Push-Secret setzen** — Settings → Secrets and variables → Actions →
   *New repository secret*, Name `NTFY_TOPIC`, Wert: der ntfy-Themenname.
   Fehlt das Secret, läuft die Analyse vollständig weiter; das Fehlen steht
   dann als deutliche Zeile im Lauf-Protokoll und als Warnung am Lauf —
   nie als stiller Rückfall.
3. **Universum befüllen** — Actions → *Universum aktualisieren* → Run
   workflow. Bis dahin verweigert das Werkzeug bewusst jedes Ranking.
   Quellen: für die USA der englischsprachige Wikipedia-Artikel
   *List of S&P 500 companies*; für Deutschland die **täglichen
   Bestandslisten** der physisch replizierenden iShares-ETFs EXS1 (DAX),
   EXS3 (MDAX) und EXS2 (TecDAX) — was so ein Fonds hält, ist praktisch
   der Index. Zieht ein CSV-Link nicht mehr, lässt er sich dem Workflow
   als Eingabefeld mitgeben, ohne den Code zu ändern.
4. **Ersten Lauf starten** — Actions → *Momentum-Lauf* → Run workflow.
   Er bildet rückwirkend das Ranking zum letzten Handelstag Juli 2026.

## Lokal

```bash
pip install -r requirements.txt pytest
PYTHONPATH=src python -m pytest                            # ohne Netz
PYTHONPATH=src python -m pytest tests/design               # Layout im Browser
PYTHONPATH=src python -m pytest -m network tests/network   # braucht Netz
PYTHONPATH=src python -m momentum.build_pages              # Methodik-Seite neu erzeugen
```

## Keine Anlageberatung

Dieses Werkzeug gibt keine Kauf- oder Verkaufsempfehlung ab. Die
zugrundeliegende Evidenz ist Portfolio-Statistik über lange Zeiträume und
sagt über eine einzelne Aktie nichts. Der gemessene Effekt ist im US-Markt
nach 2000 deutlich geschrumpft, und die Studien messen Gewinner *minus*
Verlierer — hier steht nur die Gewinner-Seite.
