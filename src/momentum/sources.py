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
            "Die schweren Einbrueche von Momentum-Strategien haeuften sich in "
            "Phasen, in denen der Gesamtmarkt zuvor gefallen war und die "
            "Schwankung hoch lag. Genau davor warnt die Trend-Ampel."
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
