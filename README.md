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
| 12-1-Momentum (jüngster Monat übersprungen) | 70 % | Jegadeesh & Titman (1993), *The Journal of Finance*; Jegadeesh (1990) |
| Nähe zum 52-Wochen-Hoch | 30 % | George & Hwang (2004), *The Journal of Finance* |

Score `0–100 = 70 × Perzentil(12-1) + 30 × Perzentil(52W-Nähe)`,
Perzentile **immer nur innerhalb eines Marktes** (Rouwenhorst 1998),
Gleichstände deterministisch alphabetisch gebrochen.

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
Folgemonats das Ranking mit dem korrekten Stichtag nach.

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
universe/        committete statische Listen mit Herkunft + Stand-Datum
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
