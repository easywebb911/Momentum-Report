"""Quellenverzeichnis — die EINE Wahrheit fuer Belege im Tool.

Tragendes Prinzip des Projekts: LITERATURTREUE ERSETZT VALIDIERUNG.
Jede Score-Zutat und jede Anzeige-Aussage haengt an genau einem Eintrag
hier. Der Code kommentiert mit dem Schluessel, die Methodik-Seite wird aus
demselben Dict erzeugt -- damit ist der 1:1-Abgleich strukturell garantiert
und nicht nur per Konvention (siehe tests/unit/test_sources.py).

Neue Score-Zutat ohne Eintrag hier ist nicht vorgesehen: config.py prueft
beim Import, dass jede gewichtete Komponente einen Beleg hat.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """Ein Primaerbeleg.

    key      -- stabiler Schluessel, im Code als Kommentar-Referenz benutzt
    authors  -- Autorennennung wie zitiert
    year     -- Erscheinungsjahr
    journal  -- Journal / Publikationsort
    title    -- Titel der Arbeit
    claim    -- Was GENAU dieses Tool aus der Arbeit uebernimmt (einfache
                Sprache, erscheint woertlich auf der Methodik-Seite)
    """

    key: str
    authors: str
    year: int
    journal: str
    title: str
    claim: str

    @property
    def short(self) -> str:
        return f"{self.authors} ({self.year}), {self.journal}"


_ALL = [
    Source(
        key="momentum_12_1",
        authors="Jegadeesh & Titman",
        year=1993,
        journal="The Journal of Finance",
        title=(
            "Returns to Buying Winners and Selling Losers: Implications for "
            "Stock Market Efficiency"
        ),
        claim=(
            "Aktien, die in den vergangenen rund zwoelf Monaten am staerksten "
            "gestiegen sind, liefen im Durchschnitt der Folgemonate weiter "
            "besser als die schwaechsten. Gemessen wird die Rendite vom Ende "
            "des Monats vor zwoelf Monaten bis zum Ende des VORLETZTEN Monats."
        ),
    ),
    Source(
        key="skip_month",
        authors="Jegadeesh",
        year=1990,
        journal="The Journal of Finance",
        title="Evidence of Predictable Behavior of Security Returns",
        claim=(
            "Auf Sicht eines einzelnen Monats kehren sich Kursbewegungen im "
            "Mittel um. Deshalb laesst die Standard-Rezeptur den juengsten "
            "Monat bewusst aus dem Messfenster heraus -- dieser "
            "uebersprungene Monat ist Teil der belegten Methode, keine Option."
        ),
    ),
    Source(
        key="high_52w",
        authors="George & Hwang",
        year=2004,
        journal="The Journal of Finance",
        title="The 52-Week High and Momentum Investing",
        claim=(
            "Wie nah eine Aktie an ihrem hoechsten Kurs der letzten 52 Wochen "
            "notiert, trug in der Untersuchung eigene Erklaerungskraft fuer "
            "die kuenftige Entwicklung -- zusaetzlich zur reinen "
            "Zwoelf-Monats-Rendite."
        ),
    ),
    Source(
        key="within_market",
        authors="Rouwenhorst",
        year=1998,
        journal="The Journal of Finance",
        title="International Momentum Strategies",
        claim=(
            "Der Effekt wurde je Markt gegen die Titel DESSELBEN Marktes "
            "gemessen. Deshalb werden Perzentil-Raenge hier ausschliesslich "
            "innerhalb eines Marktes gebildet und nie ueber Maerkte gemischt."
        ),
    ),
    Source(
        key="trend_filter",
        authors="Moskowitz, Ooi & Pedersen",
        year=2012,
        journal="Journal of Financial Economics",
        title="Time Series Momentum",
        claim=(
            "Die Vorzeichen-Richtung eines Marktes ueber die vergangenen "
            "zwoelf Monate trug Information ueber die naechste Phase -- "
            "gemessen an der Rendite UEBER dem Geldmarktsatz, nicht am "
            "reinen Kursgewinn. Daraus speist sich hier ausschliesslich eine "
            "Warnanzeige je Markt."
        ),
    ),
    Source(
        key="momentum_crash",
        authors="Daniel & Moskowitz",
        year=2016,
        journal="Journal of Financial Economics",
        title="Momentum Crashes",
        claim=(
            "Die schweren Einbrueche von Momentum-Strategien (Gewinner minus "
            "Verlierer) haeuften sich in Phasen, in denen der Gesamtmarkt "
            "zuvor gefallen war und die Schwankung hoch lag. Sie gingen "
            "ueberwiegend auf die Verlierer-Seite zurueck: Die schwaechsten "
            "Aktien erholten sich dann ploetzlich stark. Fuer die Gewinner "
            "allein ist ein solcher Crash damit nicht belegt."
        ),
    ),
    Source(
        key="momentum_states_intl",
        authors="Goyal, Jegadeesh & Subrahmanyam",
        year=2025,
        journal="Review of Finance 29(1), 2025",
        title="Empirical determinants of momentum: a perspective using international data",
        claim=(
            "Mit internationalen Daten: Momentum war nach steigenden Märkten "
            "und in ruhigen Märkten stärker als nach fallenden bzw. in "
            "unruhigen. Der Unterschied ging fast ganz auf die Verlierer "
            "zurück; bei den Gewinnern war er klein, nicht deutlich oder "
            "sogar umgekehrt."
        ),
    ),
    Source(
        key="decay",
        authors="Jegadeesh & Titman",
        year=2023,
        journal="Financial Analysts Journal",
        title="Momentum: Evidence and Insights 30 Years Later",
        claim=(
            "Im US-Markt fiel der gemessene Effekt nach dem Jahr 2000 im "
            "Mittel auf rund 0,3 % pro Monat -- deutlich weniger als im "
            "urspruenglich untersuchten Zeitraum."
        ),
    ),
    Source(
        key="long_only",
        authors="Jegadeesh & Titman",
        year=1993,
        journal="The Journal of Finance",
        title=(
            "Returns to Buying Winners and Selling Losers: Implications for "
            "Stock Market Efficiency"
        ),
        claim=(
            "Die gemessene Rendite ist die Differenz Gewinner MINUS Verlierer. "
            "Dieses Tool zeigt nur die Gewinner-Seite; die Studienrenditen "
            "sind deshalb nicht auf das hier Gezeigte uebertragbar."
        ),
    ),
    Source(
        key="portfolio_statistic",
        authors="Fama & French",
        year=2012,
        journal="Journal of Financial Economics",
        title="Size, Value, and Momentum in International Stock Returns",
        claim=(
            "Alle Belege sind Durchschnitte ueber breite Portfolios und lange "
            "Zeitraeume. Ueber eine einzelne Aktie sagt der Befund nichts."
        ),
    ),
    Source(
        key="asia_exception",
        authors="Asness",
        year=2011,
        journal="The Journal of Portfolio Management",
        title="Momentum in Japan: The Exception That Proves the Rule",
        claim=(
            "In Japan liess sich der Momentum-Effekt nicht verlaesslich "
            "nachweisen -- eine dokumentierte Ausnahme."
        ),
    ),
    Source(
        key="asia_culture",
        authors="Chui, Titman & Wei",
        year=2010,
        journal="The Journal of Finance",
        title="Individualism and Momentum around the World",
        claim=(
            "Die Staerke des Effekts hing systematisch von der Kultur des "
            "Marktes ab; in ostasiatischen Maerkten war er am schwaechsten."
        ),
    ),
    Source(
        key="asia_international",
        authors="Fama & French",
        year=2012,
        journal="Journal of Financial Economics",
        title="Size, Value, and Momentum in International Stock Returns",
        claim=(
            "In der internationalen Auswertung war Japan der Markt ohne "
            "belastbaren Momentum-Befund. Deshalb deckt dieses Tool Japan, "
            "Taiwan und Suedkorea bewusst NICHT ab."
        ),
    ),
    Source(
        key="total_return",
        authors="Jegadeesh & Titman",
        year=1993,
        journal="The Journal of Finance",
        title=(
            "Returns to Buying Winners and Selling Losers: Implications for "
            "Stock Market Efficiency"
        ),
        claim=(
            "Gemessen wurden Gesamtrenditen inklusive Dividenden. Deshalb "
            "rechnet dieses Tool ausschliesslich mit dividenden- und "
            "split-bereinigten Kursen."
        ),
    ),
]

# --- Begruendung der Gewichtung je Markt (Entscheidung Easy, 01.11.2026) ---
# Diese fuenf Eintraege tragen KEINE Score-Zutat (deshalb nicht in
# SCORE_COMPONENT_SOURCES), sondern die Begruendung, WIE die beiden Zutaten
# je Markt gewichtet werden (config.Market.gewichts_fahrplan). Wo eine Arbeit
# nicht begutachtet ist, steht das im Feld `journal` -- es erscheint so auf
# der Methodik-Seite. Pruefstand der Angaben: SESSION_HANDOVER.md §4 Punkt 8.
_ALL += [
    Source(
        key="weights_hxz",
        authors="Hou, Xue & Zhang",
        year=2020,
        journal="The Review of Financial Studies 33(5), S. 2019–2133",
        title="Replicating Anomalies",
        claim=(
            "Nachgerechnet so, dass große Firmen das Ergebnis bestimmen "
            "(NYSE-Grenzen, wertgewichtet), ein Monat Haltedauer: Nähe zum "
            "52-Wochen-Hoch 0,13 % pro Monat (t-Wert 0,38, nicht von null "
            "unterscheidbar), Momentum über elf Monate (dort \"R11\") "
            "1,16 % pro Monat (t-Wert 3,99)."
        ),
    ),
    Source(
        key="weights_barroso_wang",
        authors="Barroso & Wang",
        year=2021,
        journal="Arbeitspapier, EFMA-Jahrestagung 2021 Leeds (nicht begutachtet)",
        title=(
            "What explains price momentum and 52-week high momentum when "
            "they really work?"
        ),
        claim=(
            "Hauptstichprobe 07/1972–12/2019: Außer bei kleinen Werten ist das "
            "Kurs-Momentum der stärkere Effekt; im Durchschnitt schließt es "
            "den 52-Wochen-Hoch-Effekt vollständig mit ein."
        ),
    ),
    Source(
        key="weights_imc",
        authors="The Informed Momentum Company (IMC)",
        year=2026,
        journal="Studie eines Vermögensverwalters (nicht begutachtet, Eigeninteresse möglich)",
        title="Buy High, Sell Higher — Evaluating the 52-week high as a momentum signal",
        claim=(
            "Große US-Werte, sechs Monate Haltedauer: über 06/1988–12/2025 "
            "war die Mischung aus beiden Zutaten leicht besser als reines "
            "Momentum (IR 0,24 gegen 0,20), im Teilzeitraum 06/2006–12/2025 "
            "umgekehrt (0,07 gegen 0,11). Ob die Unterschiede Zufall sein "
            "können, wurde nicht geprüft."
        ),
    ),
    Source(
        key="weights_burghof_prothmann",
        authors="Burghof & Prothmann",
        year=2009,
        journal="The International Journal of Business and Finance Research 3(2), S. 47–69",
        title="Can Stock Price Momentum Be Explained by Anchoring?",
        claim=(
            "Alle in Deutschland gehandelten Aktien, 1980–2008: Die Nähe zum "
            "52-Wochen-Hoch sagte die künftige Entwicklung besser voraus als "
            "das Momentum."
        ),
    ),
    Source(
        key="weights_franz_regele",
        authors="Franz & Regele",
        year=2016,
        journal="Financial Markets and Portfolio Management 30(2), S. 161–204",
        title="Beating the DAX, MDAX, and SDAX: investment strategies in Germany",
        claim=(
            "1988–2015: Eine Momentum-Prämie zeigte sich nur im SDAX, nicht "
            "in DAX und MDAX."
        ),
    ),
]

# Reihenfolge, in der die Gewichtungs-Belege auf der Methodik-Seite stehen.
WEIGHTING_SOURCES: tuple[str, ...] = (
    "weights_hxz",
    "weights_barroso_wang",
    "weights_imc",
    "weights_burghof_prothmann",
    "weights_franz_regele",
)

SOURCES: dict[str, Source] = {s.key: s for s in _ALL}

# Belege, die JEDE gewichtete Score-Komponente tragen muss.
SCORE_COMPONENT_SOURCES: dict[str, tuple[str, ...]] = {
    "momentum_12_1": ("momentum_12_1", "skip_month", "total_return"),
    "high_52w": ("high_52w", "total_return"),
}


def source(key: str) -> Source:
    """Beleg holen; unbekannter Schluessel ist ein Programmierfehler."""
    try:
        return SOURCES[key]
    except KeyError as exc:  # pragma: no cover - Schutz gegen Tippfehler
        raise KeyError(
            f"Unbelegter Quellen-Schluessel {key!r}. Jede Aussage im Tool "
            f"braucht einen Eintrag in sources.py."
        ) from exc
