"""HTML-Erzeugung fuer docs/ (GitHub Pages).

Die Methodik-Seite wird aus sources.SOURCES erzeugt -- damit KANN sie nicht
von den Belegen im Code abweichen; der 1:1-Abgleich ist strukturell und
wird zusaetzlich in tests/unit/test_sources.py festgehalten.
"""

from __future__ import annotations

import datetime as _dt
import html
import math
from dataclasses import dataclass, field

from .config import (
    LIQUIDITY_MIN_MEDIAN_TURNOVER,
    LIQUIDITY_WINDOW_MONTHS,
    REPO_SLUG,
    TOP_N,
    WORKFLOW_LAUF,
    WEIGHT_HIGH_52W,
    WEIGHT_MOMENTUM_12_1,
    Market,
)
from .sources import SCORE_COMPONENT_SOURCES, SOURCES, source

Date = _dt.date

# Die vier Ehrlichkeits-Anzeigen. Reihenfolge und Wortlaut sind Teil des
# Produkts, nicht Dekoration -- jede haengt an einem Beleg.
#
# Sie stehen seit dem 02.08.2026 auf der METHODIK-Seite, nicht mehr auf der
# Uebersicht (Produktentscheidung). Deshalb ist der Verweis auf die
# Trend-Ampel jetzt ein Sprung INNERHALB derselben Seite.
HONESTY = (
    (
        "portfolio_statistic",
        "Staerkstes Momentum nach belegter Methode",
        "Keine Einzelaktien-Prognose — die Evidenz ist Portfolio-Statistik.",
        None,
    ),
    (
        "momentum_crash",
        "Momentum kann abrupt einbrechen",
        "Die schweren Einbrueche haeuften sich nach fallenden Maerkten. "
        "Was die Trend-Ampel auf der Uebersicht je Markt bedeutet:",
        "#trend-ampel",
    ),
    (
        "decay",
        "Der Effekt ist geschrumpft",
        "US-Effekt nach 2000 im Schnitt nur noch rund 0,3 % pro Monat.",
        None,
    ),
    (
        "long_only",
        "Hier fehlt die halbe Studie",
        "Die Studien messen Gewinner MINUS Verlierer; hier steht nur die "
        "Long-Seite — Studien-Renditen sind nicht uebertragbar.",
        None,
    ),
)


@dataclass
class MarketView:
    market: Market
    ranking: dict
    price_asof: Date | None
    prices: dict[str, float]
    next_ranking_date: Date
    # Firmenname und Sektor je Ticker, rein beschreibend (siehe meta.py).
    # Mit Vorgabewert, damit jeder bestehende Aufruf unveraendert bleibt --
    # ohne die Datei sieht die Karte aus wie vorher.
    meta: dict[str, dict[str, str]] = field(default_factory=dict)


def de_date(day: Date) -> str:
    return f"{day.day:02d}.{day.month:02d}.{day.year}"


def de_daymonth(day: Date) -> str:
    return f"{day.day:02d}.{day.month:02d}."


# Deutsche Zahlentypografie, bewusst gesetzt (nicht zufaellig eingefangen):
# schmales Leerzeichen als Tausendertrennung, geschuetztes Leerzeichen vor
# Einheiten -- damit "12 345" und "42,1 %" nie ueber zwei Zeilen brechen.
THIN_SPACE = "\u2009"
NBSP = "\u00a0"


def de_num(value: float, digits: int = 2) -> str:
    text = f"{value:,.{digits}f}"
    return text.replace(",", THIN_SPACE).replace(".", ",")


def de_pct(value: float, digits: int = 1, signed: bool = True) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{de_num(value * 100, digits)}{NBSP}%"


def e(text: object) -> str:
    return html.escape(str(text), quote=True)


def last_weekday_of_month(year: int, month: int) -> Date:
    if month == 12:
        first_next = Date(year + 1, 1, 1)
    else:
        first_next = Date(year, month + 1, 1)
    day = first_next - _dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= _dt.timedelta(days=1)
    return day


# --------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------


# Textgroesse vor dem ersten Malen setzen, damit beim Laden nichts springt.
_FS_BOOTSTRAP = (
    'try{var f=localStorage.getItem("momentum-report:fs");'
    'if(f){document.documentElement.style.setProperty("--app-fs",f+"px");}}'
    "catch(e){}"
)


def _head(title: str, description: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d1117">
<meta name="description" content="{e(description)}">
<title>{e(title)}</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon.svg">
<link rel="stylesheet" href="style.css">
<script>{_FS_BOOTSTRAP}</script>
</head>
<body data-repo="{e(REPO_SLUG)}" data-workflow="{e(WORKFLOW_LAUF)}">"""


def _header(subline: str, *, zurueck: bool = False) -> str:
    """Seitenkopf. `zurueck` setzt den Rueckweg fuer Unterseiten.

    WARUM DER RUECKWEG SEIN MUSS: Als installierte PWA laeuft die Seite im
    Standalone-Modus — ohne Adresszeile und ohne Zurueck-Taste des Browsers.
    Eine Unterseite ohne sichtbaren Rueckweg ist dort eine Sackgasse: man
    kaeme nur ueber das Schliessen und Neustarten der App wieder heraus.
    Der Kopf ist ohnehin sticky, der Weg zurueck also immer in Reichweite.
    """
    zurueck_html = (
        """  <a class="back" href="./index.html">
    <span class="back-arrow" aria-hidden="true">←</span>Zurück zur Übersicht
  </a>
"""
        if zurueck
        else ""
    )
    return f"""<header class="hdr{" hdr--sub" if zurueck else ""}">
{zurueck_html}  <div class="hdr-row">
    <div class="hdr-main">
      <h1>Momentum-Report</h1>
      <p class="stand">{subline}</p>
    </div>
    <button class="menu-btn" id="menu-btn" aria-label="Menü öffnen" aria-expanded="false">☰</button>
  </div>
</header>
<div class="overlay" id="overlay" hidden>
  <div class="overlay-backdrop" data-close></div>
  <nav class="sheet" aria-label="Menü">
    <a class="sheet-item" href="methodik.html">
      <span class="sheet-icon" aria-hidden="true">▤</span>
      <span><span class="sheet-title">Methodik</span><span class="sheet-sub">Jede Zutat mit Quelle</span></span>
    </a>
    <a class="sheet-item" href="konfluenz.html">
      <span class="sheet-icon" aria-hidden="true">∩</span>
      <span><span class="sheet-title">Konfluenz</span><span class="sheet-sub">Wo Momentum und Elliott sich treffen</span></span>
    </a>
    <button type="button" class="sheet-item sheet-item--btn" id="reload-btn">
      <span class="sheet-icon" aria-hidden="true">⟳</span>
      <span><span class="sheet-title">Neu laden</span><span class="sheet-sub">Daten frisch holen, ohne die Seite neu zu öffnen</span></span>
    </button>
    <button type="button" class="sheet-item sheet-item--btn" id="recalc-btn">
      <span class="sheet-icon" aria-hidden="true">Σ</span>
      <span><span class="sheet-title">Neu berechnen</span><span class="sheet-sub">Stößt den Momentum-Lauf bei GitHub an</span></span>
    </button>
    <button type="button" class="sheet-item sheet-item--btn" id="lock-btn" disabled>
      <span class="sheet-icon" aria-hidden="true">⌧</span>
      <span><span class="sheet-title">Sperren</span><span class="sheet-sub" id="lock-sub">Kein Token gespeichert</span></span>
    </button>
    <div class="sheet-item sheet-item--static">
      <span class="sheet-icon" aria-hidden="true">A</span>
      <span class="sheet-grow"><span class="sheet-title">Textgröße</span>
        <span class="fs-row" role="group" aria-label="Textgröße">
          <button type="button" class="fs-btn" data-fs="15">Klein</button>
          <button type="button" class="fs-btn" data-fs="16">Normal</button>
          <button type="button" class="fs-btn" data-fs="18">Groß</button>
          <button type="button" class="fs-btn" data-fs="20">Sehr groß</button>
        </span>
      </span>
    </div>
    <button type="button" class="sheet-close" data-close>Schließen</button>
  </nav>
</div>
{_TOKEN_DIALOG}
{_RUNBAR}"""


# --------------------------------------------------------------------------
# Fernsteuerung: Token-Dialog und Lauf-Banner
#
# Beide stehen auf JEDER Seite, weil das Menue auf jeder Seite steht. Ohne
# gespeicherten Token passiert nichts Stilles: der Knopf oeffnet diesen
# Dialog, mehr nicht.
# --------------------------------------------------------------------------

_TOKEN_DIALOG = """<div class="overlay" id="tok-overlay" hidden>
  <div class="overlay-backdrop" data-tok-close></div>
  <div class="sheet tok-dlg" role="dialog" aria-modal="true" aria-labelledby="tok-title">
    <h2 class="tok-title" id="tok-title">Zugriffs-Token nötig</h2>
    <p class="tok-text">Die Neuberechnung startet den Lauf bei GitHub. Dafür braucht
      diese Seite einen <strong>Fine-grained Personal Access Token</strong>, der nur
      für dieses eine Repository gilt.</p>
    <ol class="tok-steps">
      <li>Auf GitHub: <strong>Settings → Developer settings → Personal access tokens
        → Fine-grained tokens → Generate new token</strong>.
        <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener noreferrer">Direkt dorthin →</a></li>
      <li><em>Repository access</em>: <strong>Only select repositories</strong> →
        <code>Momentum-Report</code>. Kein anderes.</li>
      <li><em>Repository permissions</em>: <strong>Actions</strong> auf
        <em>Read and write</em>, <strong>Contents</strong> auf <em>Read and write</em>.
        Alles andere auf <em>No access</em> lassen.</li>
      <li>Token erzeugen, kopieren, hier einsetzen.</li>
    </ol>
    <label class="tok-label" for="tok-input">Token</label>
    <input class="tok-input" id="tok-input" type="password" autocomplete="off"
           autocapitalize="off" spellcheck="false" placeholder="github_pat_…">
    <p class="tok-note">Der Token bleibt <strong>auf diesem Gerät</strong> (IndexedDB),
      28 Tage lang, danach wird erneut gefragt. Er geht ausschließlich an
      <code>api.github.com</code>, steht in keiner Adresszeile und in keinem
      Protokoll. Über <em>Sperren</em> im Menü ist er sofort wieder weg.</p>
    <p class="tok-error" id="tok-error" role="alert" hidden></p>
    <div class="tok-row">
      <button type="button" class="tok-btn tok-btn--main" id="tok-save">Speichern und starten</button>
      <button type="button" class="tok-btn" data-tok-close>Abbrechen</button>
    </div>
  </div>
</div>"""

_RUNBAR = """<div class="runbar" id="runbar" hidden role="status" aria-live="polite">
  <span class="runbar-dot" id="runbar-dot" aria-hidden="true"></span>
  <span class="runbar-text" id="runbar-text"></span>
  <a class="runbar-link" id="runbar-link" target="_blank" rel="noopener noreferrer" hidden>Protokoll →</a>
  <button type="button" class="runbar-close" id="runbar-close" aria-label="Meldung schließen">✕</button>
</div>"""


# --------------------------------------------------------------------------
# Kopf-Banner — REIN DEKORATIV.
#
# Von Easy freigegebenes SVG, unveraendert uebernommen (nur eingerueckt).
# Inline und ohne jeden Nachladevorgang: kein Bild, kein Fetch, keine
# Schriftdatei. aria-hidden, weil es nichts aussagt, was nicht daneben in
# Worten steht -- der Bildschirmleser ueberspringt es.
#
# Die ids tragen alle das Praefix "mmb-". Im ganzen Projekt gibt es sonst
# nur zwei SVG-defs, "bar" und "barm", und die stehen in eigenen Dateien
# (docs/icon.svg, docs/icon-maskable.svg), also ohnehin in einem anderen
# Dokument. Eine Kollision ist damit doppelt ausgeschlossen -- auch wenn
# spaeter Sparklines inline dazukommen, ist das Praefix frei.
#
# Breite/Hoehe stehen bewusst NICHT im SVG: die Skalierung macht das
# viewBox-Verhaeltnis zusammen mit `.banner > svg` in style.css.
_BANNER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1170 190" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="mmb-bg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#0d1524"/>
        <stop offset="1" stop-color="#0a0f1a"/>
      </linearGradient>
      <linearGradient id="mmb-curve" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#fb923c"/>
        <stop offset="0.5" stop-color="#38bdf8"/>
        <stop offset="1" stop-color="#4ade80"/>
      </linearGradient>
      <linearGradient id="mmb-fill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#22c55e" stop-opacity="0.26"/>
        <stop offset="1" stop-color="#22c55e" stop-opacity="0"/>
      </linearGradient>
      <filter id="mmb-glow" x="-20%" y="-60%" width="140%" height="220%">
        <feGaussianBlur stdDeviation="5" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
      <radialGradient id="mmb-burst" cx="0.5" cy="0.5" r="0.5">
        <stop offset="0" stop-color="#a7f3d0" stop-opacity="0.9"/>
        <stop offset="0.4" stop-color="#4ade80" stop-opacity="0.35"/>
        <stop offset="1" stop-color="#4ade80" stop-opacity="0"/>
      </radialGradient>
      <linearGradient id="mmb-fadeL" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#0a0f1a"/>
        <stop offset="1" stop-color="#0a0f1a" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="mmb-fadeR" x1="1" y1="0" x2="0" y2="0">
        <stop offset="0" stop-color="#0a0f1a"/>
        <stop offset="1" stop-color="#0a0f1a" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <rect width="1170" height="190" rx="16" fill="url(#mmb-bg)"/>
    <g stroke="#1e2a3f" stroke-width="1" opacity="0.55">
      <line x1="0" y1="48" x2="1170" y2="48"/>
      <line x1="0" y1="95" x2="1170" y2="95"/>
      <line x1="0" y1="143" x2="1170" y2="143"/>
      <line x1="66" y1="0" x2="66" y2="190"/><line x1="153" y1="0" x2="153" y2="190"/>
      <line x1="240" y1="0" x2="240" y2="190"/><line x1="327" y1="0" x2="327" y2="190"/>
      <line x1="414" y1="0" x2="414" y2="190"/><line x1="501" y1="0" x2="501" y2="190"/>
      <line x1="588" y1="0" x2="588" y2="190"/><line x1="675" y1="0" x2="675" y2="190"/>
      <line x1="762" y1="0" x2="762" y2="190"/><line x1="849" y1="0" x2="849" y2="190"/>
      <line x1="936" y1="0" x2="936" y2="190"/><line x1="1023" y1="0" x2="1023" y2="190"/>
    </g>
    <g>
      <rect x="1023" y="0" width="87" height="190" fill="#38bdf8" opacity="0.05"/>
      <line x1="1023" y1="0" x2="1023" y2="190" stroke="#38bdf8" stroke-width="1.5" stroke-dasharray="4 5" opacity="0.5"/>
      <text x="1066" y="176" font-family="Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#7dd3fc" text-anchor="middle" opacity="0.9">Skip</text>
    </g>
    <line x1="0" y1="58" x2="1170" y2="58" stroke="#60a5fa" stroke-width="1.5" stroke-dasharray="8 7" opacity="0.55"/>
    <text x="74" y="50" font-family="Helvetica, Arial, sans-serif" font-size="15" font-weight="700" fill="#7dd3fc" opacity="0.85">52W-Hoch</text>
    <path d="M60,170 C320,162 620,140 830,96 C920,76 985,52 1030,32"
          fill="none" stroke="#fb923c" stroke-width="2.5" opacity="0.14"
          transform="translate(-26,14)" stroke-linecap="round"/>
    <path d="M60,170 C320,162 620,140 830,96 C920,76 985,52 1030,32"
          fill="none" stroke="#fb923c" stroke-width="2" opacity="0.07"
          transform="translate(-52,28)" stroke-linecap="round"/>
    <path d="M60,170 C320,162 620,140 830,96 C920,76 985,52 1030,32 L1030,190 L60,190 Z"
          fill="url(#mmb-fill)"/>
    <path d="M60,170 C320,162 620,140 830,96 C920,76 985,52 1030,32"
          fill="none" stroke="url(#mmb-curve)" stroke-width="4.5"
          stroke-linecap="round" filter="url(#mmb-glow)"/>
    <circle cx="967" cy="58" r="26" fill="url(#mmb-burst)"/>
    <circle cx="967" cy="58" r="6" fill="#0a0f1a" stroke="#4ade80" stroke-width="2.5"/>
    <path d="M1030,32 L1013,33 M1030,32 L1021,47" stroke="#4ade80" stroke-width="4.5"
          stroke-linecap="round" filter="url(#mmb-glow)"/>
    <path d="M1030,32 C1060,20 1090,14 1118,12" fill="none" stroke="#4ade80"
          stroke-width="3.5" stroke-dasharray="6 7" stroke-linecap="round" opacity="0.45"/>
    <text x="78" y="126" font-family="Helvetica, Arial, sans-serif" font-size="47"
          font-weight="800" font-style="italic" letter-spacing="1.5"
          fill="url(#mmb-curve)" filter="url(#mmb-glow)">Momentum</text>
    <rect x="0" y="0" width="46" height="190" fill="url(#mmb-fadeL)"/>
    <rect x="1124" y="0" width="46" height="190" fill="url(#mmb-fadeR)"/>
  </svg>"""


def _banner() -> str:
    """Das Banner in seinem Traeger.

    Der Traeger-<div> existiert, damit das SVG selbst unangetastet bleibt:
    die Layout-Regeln haengen an `.banner`, nicht am SVG-Element.
    """
    return f'<div class="banner">\n  {_BANNER_SVG}\n</div>'


def _honesty_block() -> str:
    items = []
    for key, title, text, link in HONESTY:
        src = source(key)
        link_html = (
            f' <a class="disc-link" href="{link}">Trend-Ampel erklärt →</a>'
            if link
            else ""
        )
        items.append(
            f"""    <li class="disc-item">
      <span class="disc-title">{e(title)}</span>
      <span class="disc-text">{e(text)}{link_html}</span>
      <span class="disc-src">{e(src.short)}</span>
    </li>"""
        )
    return (
        '<section class="disc-box" id="ehrlich-gesagt" '
        'aria-label="Was dieses Werkzeug nicht kann">\n'
        '  <ul class="disc-list">\n' + "\n".join(items) + "\n  </ul>\n</section>"
    )


# --------------------------------------------------------------------------
# TREND-TACHO — reine Anzeige der vorhandenen Felder.
#
# Gelesen werden ausschliesslich `rendite_12m` und `warnung` aus dem
# eingefrorenen Ranking. Hier wird NICHTS gerechnet, was nicht schon im
# Report steht -- der Tacho ist ein Bild derselben Zahl, die daneben in
# Worten steht, kein zweites Kriterium.
#
# Geometrie nach Easys Vorlage: viewBox 0 0 120 72, Halbbogen aus zwei
# Segmenten um den Drehpunkt (60, 64) mit Radius 48.
# --------------------------------------------------------------------------

TACHO_MITTE_X = 60.0
TACHO_MITTE_Y = 64.0
TACHO_NADEL_LAENGE = 46.0

# Skalenende: -25 % links, +25 % rechts. 0 % liegt exakt oben -- und damit
# genau auf dem Umschlagpunkt zwischen rotem und gruenem Segment. Das ist
# kein Zufall, sondern die Aussage: das Trendkriterium fragt nur, ob der
# Index ueber zwoelf Monate im Minus steht.
TACHO_SKALA = 0.25


def tacho_winkel(rendite: float) -> float:
    """Grad auf dem Halbbogen: 180 bei -25 %, 90 bei 0 %, 0 bei +25 %.

    Werte ausserhalb der Skala werden an die Enden GEKLEMMT -- die Nadel
    verlaesst den Bogen nie. Ein Anschlag ist ehrlicher als eine Nadel, die
    ins Nichts zeigt; die genaue Zahl steht ohnehin als Text daneben.
    """
    anteil = max(-1.0, min(1.0, rendite / TACHO_SKALA))
    return 90.0 - anteil * 90.0


def tacho_nadel(rendite: float, laenge: float = TACHO_NADEL_LAENGE) -> tuple[float, float]:
    """Endpunkt der Nadel im viewBox-Koordinatensystem.

    x = 60 + L·cos(θ), y = 64 − L·sin(θ) — y zeigt im SVG nach unten,
    deshalb das Minus. Auf zwei Nachkommastellen gerundet, damit bei
    gleicher Eingabe Zeichen fuer Zeichen dasselbe SVG entsteht.
    """
    bogen = math.radians(tacho_winkel(rendite))
    x = TACHO_MITTE_X + laenge * math.cos(bogen)
    y = TACHO_MITTE_Y - laenge * math.sin(bogen)
    return round(x, 2), round(y, 2)


def _trend_tacho(
    markt_key: str,
    index_name: str,
    rendite: float,
    warnung: bool,
    *,
    mit_zins: bool = False,
) -> str:
    """Der Tacho als eigenstaendiges SVG — inline, ohne Nachladen.

    Die id am Wurzelelement traegt den Markt (tta-us / tta-de). INNEN gibt
    es bewusst keine einzige id: was nichts referenziert, kann auch nicht
    kollidieren, wenn dieselbe Grafik zweimal auf der Seite steht.

    `mit_zins` steuert NUR den Vorlesetext. Er muss zur danebenstehenden
    Satz-Box passen: sagt die Box "ohne Zins-Abzug", darf die Grafik nicht
    "unter Geldmarkt" vorlesen -- sonst behaupten Bild und Text
    Verschiedenes.
    """
    nadel_x, nadel_y = tacho_nadel(rendite)
    zahl = de_pct(rendite)
    if warnung:
        lage = (
            "Warnung: Markt unter dem Geldmarkt"
            if mit_zins
            else "Warnung: Markt im 12-Monats-Minus"
        )
    else:
        lage = "kein Alarm"
    return f"""    <svg class="tta{" tta--warn" if warnung else ""}" id="tta-{e(markt_key)}"
         viewBox="0 0 120 72" role="img"
         aria-label="Trend-Kriterium {e(index_name)}: {zahl}, {lage}">
      <path d="M12,64 A48,48 0 0 1 60,16" fill="none" stroke="#ef4444"
            stroke-width="9" stroke-linecap="round"
            opacity="{"0.9" if warnung else "0.55"}"/>
      <path d="M60,16 A48,48 0 0 1 108,64" fill="none" stroke="#4ade80"
            stroke-width="9" stroke-linecap="round"
            opacity="{"0.45" if warnung else "0.85"}"/>
      <line class="tta-nadel" x1="60" y1="64" x2="{nadel_x}" y2="{nadel_y}"
            stroke="#e7ecf4" stroke-width="3.5" stroke-linecap="round"/>
      <circle cx="60" cy="64" r="5" fill="#e7ecf4"/>
      <text class="tta-zahl" x="60" y="60" text-anchor="middle"
            fill="{"#f87171" if warnung else "#4ade80"}">{zahl}</text>
    </svg>"""


# Zwei verschiedene Gruende, warum kein Zins abgezogen wurde -- und zwei
# verschiedene Saetze dafuer. Sie zusammenzuwerfen waere bequem und falsch:
# ein Ranking, das vor der Umstellung eingefroren wurde, hat KEINE
# unerreichbare Quelle gesehen; es hat nie eine gesucht. Beide Texte stehen
# je genau einmal hier.
ZINS_FEHLT_HINWEIS = "ohne Zins-Abzug — Zinsquelle nicht erreichbar"
ZINS_ALT_HINWEIS = "ohne Zins-Abzug — dieses Ranking entstand vor der Umstellung"


def zins_hinweis(ampel: dict) -> str | None:
    """Der passende Hinweis, oder None wenn der Abzug wirklich drinsteckt."""
    if ampel.get("riskfree_12m") is not None:
        return None
    return ZINS_FEHLT_HINWEIS if "riskfree_quelle" in ampel else ZINS_ALT_HINWEIS


def ampel_wert(ampel: dict) -> tuple[float, bool]:
    """Angezeigte Zahl und ob der Zins-Abzug wirklich drinsteckt.

    Aeltere, bereits eingefrorene Rankings kennen die neuen Felder nicht --
    sie tragen ausschliesslich die Preisrendite. Dann wird genau die
    gezeigt, samt sichtbarem Hinweis. Eine alte Zahl stillschweigend als
    Ueberschussrendite auszugeben, waere die Art Beschoenigung, die dieses
    Werkzeug nirgends duldet.
    """
    mit_zins = ampel.get("riskfree_12m") is not None
    wert = ampel["ueberschuss_12m"] if mit_zins else ampel["rendite_12m"]
    return float(wert), mit_zins


def _trend_banner(view: MarketView) -> str:
    ampel = view.ranking["trend_ampel"]
    wert, mit_zins = ampel_wert(ampel)
    src = source("momentum_crash")
    tacho = _trend_tacho(
        view.market.key, ampel["index_name"], wert, ampel["warnung"], mit_zins=mit_zins
    )
    ueber = " über Geldmarkt" if mit_zins else ""
    text = zins_hinweis(ampel)
    hinweis = "" if text is None else f'\n    <span class="ampel-hinweis">{e(text)}</span>'
    if ampel["warnung"]:
        lage = (
            "Markt unter dem Geldmarkt" if mit_zins else "Markt im 12-Monats-Minus"
        )
        return f"""  <div class="ampel ampel--warn" role="status">
{tacho}
    <span class="ampel-body"><strong>Momentum-Gefahrenlage:</strong> {lage}
    ({e(ampel["index_name"])} {de_pct(wert)}{ueber}) — in solchen Phasen häufen sich historisch die
    Momentum-Einbrüche. <a href="methodik.html#trend-ampel">Was das heißt →</a>
    <span class="ampel-src">{e(src.short)}</span>{hinweis}</span>
  </div>"""
    return f"""  <div class="ampel ampel--ok" role="status">
{tacho}
    <span class="ampel-body">{e(ampel["index_name"])} auf 12 Monate {de_pct(wert)}{ueber} — das
    Trendkriterium schlägt derzeit nicht an.
    <a href="methodik.html#trend-ampel">Erklärung →</a>{hinweis}</span>
  </div>"""


CHART_BASIS = "https://stockanalysis.com"


def chart_url(ticker: str) -> str:
    """Adresse der Chart-Seite bei stockanalysis.com.

    BEST-GUESS-MUSTER, ausdruecklich benannt: Es findet keine Pruefung
    statt, ob die Seite existiert. Trifft das Muster daneben, landet man
    dort auf einer Suchseite -- unschoen, aber harmlos. Eine Pruefung waere
    ein Netzabruf je Titel bei jedem Seitenaufbau, und das waere der
    schlechtere Handel.

    Deutsche Titel tragen bei uns das Yahoo-Suffix ".DE"; stockanalysis
    fuehrt sie unter der Xetra-Kennung ohne Suffix (etr/SAP). Genau diese
    Endung wird abgeschnitten -- weitere Boersen kommen hier nicht vor,
    weil das Universum nur Xetra-Titel enthaelt.
    """
    if ticker.endswith(".DE"):
        return f"{CHART_BASIS}/quote/etr/{ticker[:-3]}"
    return f"{CHART_BASIS}/stocks/{ticker}/"


def _card(row: dict, view: MarketView) -> str:
    market = view.market
    price = view.prices.get(row["ticker"])
    price_text = (
        f"{market.currency_symbol}{NBSP}{de_num(price, 2)}"
        if price is not None
        else "—"
    )
    mom = row["momentum_12_1"]
    mom_class = "pos" if mom > 0 else ("neg" if mom < 0 else "")
    # Die beiden Teil-Raenge. Sie stehen hier, damit die Mischung SICHTBAR
    # ist: bei Gleichgewichtung kann ein Titel vorn liegen, weil er in einer
    # Zutat sehr stark und in der anderen nur mittelmaessig ist. Das gehoert
    # auf die Karte, nicht in eine Fussnote.
    bewertet = view.ranking["abdeckung"]["bewertet"]
    # Beschreibung aus der Meta-Datei. Fehlt sie oder der Eintrag, steht
    # ein Gedankenstrich -- der Lauf scheitert daran NIE (siehe meta.py).
    beschreibung = view.meta.get(row["ticker"], {})
    firma = beschreibung.get("name") or row["name"] or "—"
    sektor = beschreibung.get("sektor") or "—"
    # Der Stichtag-Kurs ist die Zahl, auf der Score und 52W-Naehe wirklich
    # beruhen -- eingefroren am Monats-Stichtag, unveraenderlich seit dem
    # Bau des Rankings. Er steht bereits in jeder Zeile (row["kurs_stichtag"],
    # siehe ranking.py); hier wird nichts Neues berechnet, nur zusaetzlich
    # gezeigt. Bewusst als eigener Ehrlichkeits-Satz (--disc, wie card-ft
    # oben) und NICHT im "Kurs (...)"-Kaestchen: der Live-Puls dort zeigt
    # den JETZIGEN Kurs, und beide in derselben Farbe/Zeile zu vermengen
    # wuerde genau die Verwechslung nahelegen, die dieser Zusatz vermeiden
    # soll.
    stichtag = Date.fromisoformat(view.ranking["stichtag"])
    stichtag_kurs_text = f"{market.currency_symbol}{NBSP}{de_num(row['kurs_stichtag'], 2)}"
    return f"""      <article class="card">
        <div class="card-hd">
          <div class="card-id">
            <span class="rank">{row["rang"]}</span>
            <span class="id-text">
              <span class="ticker-zeile">
                <span class="ticker">{e(row["ticker"])}</span>
                <a class="chart-badge" href="{e(chart_url(row["ticker"]))}"
                   target="_blank" rel="noopener noreferrer"
                   aria-label="Chart für {e(row["ticker"])} bei stockanalysis.com (neuer Tab)"
                   >CHART<span class="chart-icon" aria-hidden="true">↗</span></a>
              </span>
              <span class="cname">{e(firma)}</span>
              <span class="csektor">{e(sektor)}</span>
            </span>
          </div>
          <div class="card-score">
            <span class="score-val">{de_num(row["score"], 1)}</span>
            <span class="score-lbl">Score</span>
          </div>
        </div>
        <div class="metrics">
          <div class="metric-box">
            <span class="m-val {mom_class}">{de_pct(mom)}</span>
            <span class="m-lbl">12-1-Momentum</span>
          </div>
          <div class="metric-box">
            <span class="m-val">{de_pct(row["high_52w"], 1, signed=False)}</span>
            <span class="m-lbl">52W-Hoch-Nähe</span>
          </div>
          <div class="metric-box">
            <span class="m-val" data-quote="{e(row["ticker"])}">{price_text}</span>
            <span class="m-chg" data-quote-change="{e(row["ticker"])}"></span>
            <span class="m-lbl">Kurs ({e(market.currency)})</span>
            <span class="live live--karte" data-live-markt="{e(market.key)}"
                  data-live-ticker="{e(row["ticker"])}"
               ><span class="live-dot" aria-hidden="true"></span
               ><span class="live-txt">Live · —</span></span>
          </div>
        </div>
        <div class="metrics metrics--rang">
          <div class="metric-box">
            <span class="m-val">{row["rank_12_1"]}.{NBSP}von{NBSP}{bewertet}</span>
            <span class="m-lbl">Rang 12-1-Momentum</span>
          </div>
          <div class="metric-box">
            <span class="m-val">{row["rank_52w"]}.{NBSP}von{NBSP}{bewertet}</span>
            <span class="m-lbl">Rang 52W-Hoch-Nähe</span>
          </div>
        </div>
        <p class="card-ft">Rang aus belegter Rechenvorschrift — keine Prognose für diese Aktie.</p>
        <p class="card-ft card-ft--stichtag">Kurs vom {de_daymonth(stichtag)}, <strong>eingefroren</strong>
           — Basis für dieses Ranking: {stichtag_kurs_text}.</p>
      </article>"""


def _market_section(view: MarketView) -> str:
    market = view.market
    ranking = view.ranking
    rows = ranking["rangliste"][:TOP_N]
    cov = ranking["abdeckung"]
    stichtag = Date.fromisoformat(ranking["stichtag"])
    price_line = (
        f"Kurse vom {de_date(view.price_asof)}"
        if view.price_asof
        else "Kurse: keine aktuelleren als zum Stichtag"
    )
    return f"""<section class="market">
  <h2><span class="flag" aria-hidden="true">{market.flag}</span>{e(market.name)}</h2>
  <p class="market-meta">Ranking vom {de_date(stichtag)} · {price_line} ·
     {cov["bewertet"]} von {cov["universum"]} Titeln bewertet</p>
{_trend_banner(view)}
  <div class="cards">
{chr(10).join(_card(row, view) for row in rows)}
  </div>
  <p class="cov">
    Handelbarkeits-Filter, kein Signal: {cov["ohne_handelbarkeit"]} Titel unter
    {de_num(LIQUIDITY_MIN_MEDIAN_TURNOVER / 1_000_000, 0)}{NBSP}Mio.{NBSP}{e(market.currency)}
    Median-Tagesumsatz ({LIQUIDITY_WINDOW_MONTHS} Monate) — aussortiert, bevor
    irgendetwas gerechnet wurde. {len(cov["ohne_ausreichende_historie"])} Titel ohne
    ausreichende Historie. Universum: {e(ranking["universum"]["bezeichnung"])},
    Stand {e(ranking["universum"]["stand"])}.
  </p>
</section>"""


def _foot(extra: str = "") -> str:
    return f"""{extra}
<footer class="foot">
  <p>Momentum-Report — Anwendungs-Werkzeug auf belegter Wissenschaft.
     Keine Anlageberatung, keine Kauf- oder Verkaufsempfehlung.</p>
  <p class="foot-dim">Kurse: Yahoo Finance, dividenden- und splitbereinigt.
     Ohne Gewähr auf Richtigkeit oder Vollständigkeit.</p>
</footer>
<script src="app.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Seiten
# --------------------------------------------------------------------------


def render_index(views: list[MarketView], run_date: Date) -> str:
    ranked = [v for v in views if v.ranking]
    if ranked:
        stichtag = max(Date.fromisoformat(v.ranking["stichtag"]) for v in ranked)
        nxt = min(v.next_ranking_date for v in ranked)
        price_days = [v.price_asof for v in ranked if v.price_asof]
        price_txt = de_date(max(price_days)) if price_days else "—"
        subline = (
            f"Ranking vom {de_daymonth(stichtag)} · nächstes am "
            f"{de_daymonth(nxt)} · Kurse vom {price_txt}"
        )
    else:
        subline = f"Noch kein Ranking gebildet · Stand {de_date(run_date)}"

    body = [
        _head(
            "Momentum-Report",
            "Staerkstes Momentum in USA und Deutschland nach belegter Methode.",
        ),
        _header(subline),
        "<main>",
        # Das Banner steht als ERSTES im Inhalt, direkt unter der Ueberschrift
        # -- Easys ausdrueckliche Platzierung.
        #
        # Bewusst NICHT in den <header>: der ist sticky. Dort wuerde das Band
        # beim Scrollen kleben und dauerhaft Bildschirmplatz kosten. Als
        # erstes Element in <main> scrollt es weg wie jeder andere Inhalt und
        # nimmt zugleich Innenabstand und Maximalbreite des Inhalts mit.
        #
        # Die vier Ehrlichkeits-Anzeigen standen frueher hier. Sie stehen
        # jetzt auf der Methodik-Seite unter „Ehrlich gesagt" -- ebenfalls
        # Produktentscheidung. Der Haftungshinweis im Fuss bleibt, wo er ist.
        _banner(),
    ]
    for view in views:
        if view.ranking:
            body.append(_market_section(view))
        else:
            body.append(
                f'<section class="market"><h2><span class="flag" aria-hidden="true">'
                f"{view.market.flag}</span>{e(view.market.name)}</h2>"
                f'<div class="ampel ampel--warn"><span class="ampel-body">Kein Ranking '
                f"vorhanden. Es wird bewusst keines gezeigt, solange die Datengrundlage "
                f"nicht vollständig ist.</span></div></section>"
            )
    body.append("</main>")
    body.append(_foot())
    return "\n".join(body)


def _method_card(title: str, keys: tuple[str, ...], body_html: str, anchor: str = "") -> str:
    footnotes = "".join(
        f'<li>{e(SOURCES[k].authors)} ({SOURCES[k].year}): '
        f"„{e(SOURCES[k].title)}“, <em>{e(SOURCES[k].journal)}</em>. "
        f"{e(SOURCES[k].claim)}</li>"
        for k in keys
    )
    anchor_attr = f' id="{anchor}"' if anchor else ""
    return f"""<article class="card mcard"{anchor_attr}>
  <h3>{e(title)}</h3>
  {body_html}
  <ul class="src-list">{footnotes}</ul>
</article>"""


# --------------------------------------------------------------------------
# KONFLUENZ-SEITE
#
# Zwei Werkzeuge, zwei Blickwinkel — mehr behauptet diese Seite nie. Es gibt
# hier KEINEN gemeinsamen Score, KEINE verrechnete Wahrscheinlichkeit und
# KEINE Rangfolge der Treffer. Ein Mischwert waere eine Zahl, die niemand
# belegt hat, und genau das duldet dieses Projekt nirgends.
#
# Die Seite ist ein leeres Geruest; gefuellt wird sie im Browser aus zwei
# JSON-Dateien (siehe app.js). So bleibt sie unabhaengig davon, wann das
# jeweils andere Werkzeug zuletzt gelaufen ist.
# --------------------------------------------------------------------------

# Der feste Satz. Er steht auf der Seite und in einem Test -- damit er nicht
# im Laufe der Zeit weichgespuelt wird.
KONFLUENZ_SATZ = (
    "Hier wird nichts verrechnet. Beide Werkzeuge messen Verschiedenes und "
    "stehen unabhängig nebeneinander: Momentum misst vergangene relative "
    "Stärke, Elliott beschreibt Kursmuster. Eine Überschneidung ist ein "
    "Zufall zweier Verfahren, kein doppelter Beleg und keine höhere "
    "Trefferwahrscheinlichkeit."
)

KONFLUENZ_LEER = (
    "Keine Überschneidung — das ist der Regelfall. Beide Werkzeuge messen "
    "Verschiedenes; ein gemeinsamer Treffer ist selten."
)


def render_konfluenz() -> str:
    body = [
        _head(
            "Konfluenz — Momentum-Report",
            "Wo Momentum-Top-5 und Elliott-Long-Kandidaten sich treffen.",
        ),
        _header("Zwei Blickwinkel nebeneinander", zurueck=True),
        "<main>",
        f"""<p class="lead">Diese Seite stellt zwei getrennte Werkzeuge
nebeneinander: die eingefrorenen <strong>Top-5 dieses Momentum-Reports</strong>
und die <strong>Long-Kandidaten des Elliott-Reports</strong>. Steht ein Titel
in beiden, wird er hervorgehoben.</p>
<p class="konf-regel">{e(KONFLUENZ_SATZ)}</p>""",
        # Der Stand BEIDER Quellen. Die Werkzeuge laufen zu verschiedenen
        # Zeiten -- wer das nicht sieht, vergleicht womoeglich Aepfel mit
        # Birnen von gestern.
        """<div class="konf-stand" id="konf-stand">
  <span class="konf-quelle"><span class="konf-quelle-name">Momentum</span>
    <span class="konf-quelle-stand" id="stand-momentum">wird geladen …</span></span>
  <span class="konf-quelle"><span class="konf-quelle-name">Elliott</span>
    <span class="konf-quelle-stand" id="stand-elliott">wird geladen …</span></span>
</div>""",
        '<div class="konf-hinweis" id="konf-hinweis" role="status" hidden></div>',
        '<div id="konf-inhalt"></div>',
        "</main>",
    ]
    return "\n".join(body) + _foot()


def render_methodik() -> str:
    body = [
        _head("Methodik — Momentum-Report", "Jede Zutat mit Primaerquelle."),
        _header("Wie gerechnet wird — und was bewusst fehlt", zurueck=True),
        "<main>",
        """<p class="lead">Dieses Werkzeug erfindet nichts. Es rechnet eine
Vorschrift nach, die in wissenschaftlichen Aufsätzen veröffentlicht und
geprüft wurde. Unten steht jede einzelne Zutat: was gerechnet wird, in
einfacher Sprache, und woher sie stammt. Was hier keine Quelle hat, steht
nicht im Score.</p>""",
        # Zuerst die Grenzen, dann die Rechnung: Wer wissen will, wie das
        # Werkzeug rechnet, soll vorher wissen, was es NICHT behauptet.
        "<h2>Ehrlich gesagt</h2>",
        """<p class="lead">Vier Dinge, die man wissen muss, bevor man eine
Zahl auf der Übersicht ernst nimmt. Jede hat eine Quelle.</p>""",
        _honesty_block(),
        "<h2>Die zwei Zutaten des Scores</h2>",
        _method_card(
            f"1. 12-1-Momentum (Gewicht {int(WEIGHT_MOMENTUM_12_1 * 100)} %)",
            SCORE_COMPONENT_SOURCES["momentum_12_1"],
            """<p>Wir schauen, wie stark eine Aktie in einem Fenster von rund einem
Jahr gestiegen ist — und lassen dabei den <strong>jüngsten Monat bewusst
weg</strong>.</p>
<p class="formula">Kurs am letzten Handelstag des <em>vorletzten</em> Monats
÷ Kurs am letzten Handelstag des Monats vor zwölf Monaten − 1</p>
<p>Beispiel für den Stichtag 31.07.: gerechnet wird vom 31.07. des Vorjahres
bis zum 30.06. — der Juli fällt heraus. Dieser übersprungene Monat ist kein
Versehen und keine Einstellung: einzelne Monate neigen zur Gegenbewegung,
deshalb gehört das Auslassen zur belegten Rezeptur.</p>
<p>Gerechnet wird mit <strong>bereinigten Kursen</strong> — Dividenden und
Aktiensplits sind eingerechnet, weil die Studien Gesamtrenditen messen.</p>""",
        ),
        _method_card(
            f"2. Nähe zum 52-Wochen-Hoch (Gewicht {int(WEIGHT_HIGH_52W * 100)} %)",
            SCORE_COMPONENT_SOURCES["high_52w"],
            """<p>Wie nah notiert die Aktie heute an ihrem höchsten Stand des
letzten Jahres?</p>
<p class="formula">Kurs am Stichtag ÷ höchster Tages-Schlusskurs der letzten
52 Wochen</p>
<p>Das Ergebnis liegt zwischen 0 und 1; 100 % heißt: die Aktie steht genau
auf ihrem Jahreshoch. Das Hoch wird aus <strong>Tages-Schlusskursen</strong>
gebildet, nicht aus Intraday-Hochs — das ist die übliche Konvention beim
Nachbilden dieser Arbeit.</p>""",
        ),
        _method_card(
            "So entsteht der Score von 0 bis 100",
            ("within_market",),
            f"""<p>Beide Zutaten werden je Markt in eine Rangreihe gebracht. Der
schwächste Titel bekommt 0, der stärkste 1, alle anderen liegen gleichmäßig
dazwischen (Perzentil-Rang).</p>
<p class="formula">Score = {int(WEIGHT_MOMENTUM_12_1 * 100)} × Perzentil(12-1-Momentum)
+ {int(WEIGHT_HIGH_52W * 100)} × Perzentil(52-Wochen-Hoch-Nähe)</p>
<p><strong>Beide Zutaten zählen gleich viel.</strong> Das ist eine bewusste
Entscheidung, und sie hat einen Grund: Die Forschung liefert
<em>kein</em> Mischverhältnis für diese beiden Größen. Sie untersucht sie als
zwei getrennte Verfahren und vergleicht sie miteinander — in der Arbeit von
George &amp; Hwang war für den US-Markt sogar die Nähe zum 52-Wochen-Hoch die
stärkere der beiden. Wo Arbeiten mehrere solcher Größen zusammenfassen,
gewichten sie üblicherweise gleich.</p>
<p>Jedes andere Verhältnis wäre also eine Zahl, die niemand belegt hat. Wenn
man nicht weiß, welche Zutat wie viel wiegen sollte, ist Gleichgewichtung die
ehrliche Wahl — sie behauptet nichts.</p>
<p>Damit man sieht, woher der Score kommt, zeigt jede Karte
<strong>zusätzlich beide Teil-Ränge</strong> („3. von 470"). So erkennt man
sofort, ob ein Titel in beiden Zutaten stark ist oder nur in einer.</p>
<p>Wichtig: Die Ränge werden <strong>immer nur innerhalb eines Marktes</strong>
gebildet — US-Titel gegen US-Titel, deutsche gegen deutsche. Nie gemischt.
Bei exakt gleichem Wert entscheidet die alphabetische Reihenfolge des Tickers;
dadurch ist die Rangliste bei jedem Lauf identisch reproduzierbar. Bei
Gleichgewichtung kommt das häufiger vor als vorher — zwei Titel mit
spiegelbildlichen Teil-Rängen landen exakt gleichauf. Auch dann entscheidet
allein das Alphabet, nie der Zufall.</p>""",
        ),
        _method_card(
            "Warum nur fünf Titel — und was das kostet",
            ("portfolio_statistic", "long_only"),
            """<p>Die Untersuchungen teilen den Markt in zehn gleich große
Gruppen und messen die stärkste davon. Bei rund 105 Titeln wären das etwa
zehn bis elf Aktien.</p>
<p>Hier stehen <strong>fünf</strong> — also nur die halbe Gruppe. Diese
Auswahl ist enger als das, was gemessen wurde: Je weniger Titel, desto
stärker schlägt das Schicksal eines einzelnen Unternehmens durch. Dieses
zusätzliche Risiko ist in den Durchschnittszahlen der Aufsätze
<strong>nicht</strong> enthalten.</p>
<p>Fünf Titel sind eine Entscheidung für Lesbarkeit auf dem Telefon, keine
Aussage der Wissenschaft. Wer sich an der Studienlage orientieren will,
sollte das im Kopf behalten.</p>""",
        ),
        "<h2>Der monatliche Stichtag</h2>",
        _method_card(
            "Einmal im Monat — und dann eingefroren",
            ("momentum_12_1",),
            """<p>Die Rangliste entsteht <strong>einmal pro Monat</strong>, am letzten
Handelstag. Bis zum nächsten Stichtag ändern sich Score, Rang und Top-5
<strong>nicht mehr</strong>. Werktags werden nur die angezeigten Kurse
aktualisiert.</p>
<p>Grund: Die Evidenz in den Aufsätzen ist monatlich gemessen. Eine
Rangliste, die sich täglich dreht, wäre eine andere — ungeprüfte — Methode.
Deshalb kann ein Lauf mitten im Monat die Rangfolge technisch gar nicht
verändern.</p>
<p>Fällt der letzte Werktag auf einen Feiertag, ist der Stichtag der letzte
Tag mit Handel; das angezeigte Datum sagt immer, welcher Tag es wirklich
war.</p>""",
        ),
        "<h2>Die Trend-Ampel</h2>",
        _method_card(
            "Warnanzeige je Markt",
            ("trend_filter", "momentum_crash"),
            """<p>Bringt der Marktindex über die letzten zwölf Monate
<strong>weniger als der Geldmarkt</strong>, erscheint eine deutliche
Warnung. In genau solchen Phasen häuften sich historisch die schweren
Momentum-Einbrüche.</p>
<p><strong>Warum der Zins abgezogen wird:</strong> Die zugrunde liegende
Arbeit misst nicht den Kursgewinn, sondern das, was <em>über</em> dem
Geldmarkt übrig blieb. Ein Markt, der zwölf Monate lang 2&nbsp;% zulegt,
während Tagesgeld 3&nbsp;% brachte, hat nichts verdient — vorher galt er
hier als unauffällig, jetzt schlägt das Kriterium an. Das ist die einzige
Änderung: gerechnet wird <em>Indexrendite minus Geldmarktsatz</em>.</p>
<p><strong>Die Mittelung ist eine Näherung</strong>, und das soll so
dastehen: Aus der täglichen, aufs Jahr gerechneten Rate wird der
Durchschnitt über die zwölf Monate gebildet und einmal abgezogen. Das ist
nicht dasselbe wie die exakt aufgezinste Geldmarkt-Rendite desselben
Zeitraums; der Unterschied liegt im Bereich von Zehntel-Prozentpunkten.
Quellen: für den Dollar der 13-Wochen-Satz auf US-Staatsanleihen (^IRX),
für den Euro der €STR aus dem Datenportal der Europäischen Zentralbank.
Ist eine dieser Quellen nicht erreichbar, rechnet das Kriterium wie
zuvor ohne Abzug — und die Anzeige sagt genau das dazu.</p>
<p>Beide Indizes rechnen Dividenden ein (Performance-Indizes): der DAX von
Haus aus, für die USA wird der S&amp;P&nbsp;500 Total Return herangezogen.
Ein Kursindex gegen einen Performance-Index zu stellen, wäre ein Vergleich
zweier verschiedener Dinge.</p>
<p>Die Ampel ist <strong>reine Anzeige</strong>. Sie greift nicht in die
Rangliste ein, filtert nichts heraus und verändert keinen Score.</p>""",
            anchor="trend-ampel",
        ),
        "<h2>Das Universum und der Handelbarkeits-Filter</h2>",
        _method_card(
            "Wer überhaupt in die Wertung kommt",
            ("within_market",),
            f"""<p>USA: die Mitglieder des S&amp;P 500. Deutschland: der HDAX
(rund 100 Titel aus DAX, MDAX und TecDAX). Beide Listen liegen als feste
Dateien im Projekt, mit Herkunft und Stand-Datum — sie werden nur durch
einen bewusst angestoßenen Vorgang geändert, nie automatisch im Hintergrund.</p>
<p>Einziger Vorfilter: <strong>Handelbarkeit</strong>. Ein Titel muss in den
letzten {LIQUIDITY_WINDOW_MONTHS} Monaten einen Median-Tagesumsatz von
mindestens {int(LIQUIDITY_MIN_MEDIAN_TURNOVER / 1_000_000)} Mio. in
Heimatwährung erreicht haben. Das ist <strong>kein Signal</strong> und keine
Qualitätsaussage — es sorgt nur dafür, dass die Liste keine Titel zeigt, die
praktisch kaum handelbar sind.</p>""",
        ),
        "<h2>Was dieses Werkzeug bewusst NICHT tut</h2>",
        # „Keine Verlierer-Seite" und „der Effekt ist geschrumpft" standen
        # hier frueher als eigene Punkte. Beides sagt oben schon „Ehrlich
        # gesagt" — mit denselben Belegen. Doppelt gesagt wirkt nicht
        # doppelt, sondern beliebig, deshalb steht es nur noch dort.
        _method_card(
            "Klare Grenzen",
            ("portfolio_statistic",),
            """<ul class="nolist">
<li>Keine Rückrechnung (Backtest), keine Trefferquote, keine Erfolgsbilanz —
das wäre eine eigene Wissenschaft und würde hier nur Sicherheit vortäuschen.</li>
<li>Keine Kursziele, keine Kauf- oder Verkaufssignale, keine Ausstiegsregeln.</li>
<li>Keine Zutat ohne Quelle. Nichts wird „weil es plausibel klingt“ ergänzt.</li>
<li>Keine risikogesteuerten Varianten in dieser Fassung — dokumentiert, aber
nicht gebaut.</li>
<li>Die beiden härtesten Einschränkungen — nur die Gewinner-Seite, und ein
seit 2000 geschrumpfter Effekt — stehen oben unter
<a href="#ehrlich-gesagt">Ehrlich gesagt</a>.</li>
</ul>""",
        ),
        "<h2>Warum Japan, Taiwan und Südkorea fehlen</h2>",
        _method_card(
            "Eine dokumentierte Ausnahme",
            ("asia_exception", "asia_culture", "asia_international"),
            """<p>Momentum ist in sehr vielen Märkten gefunden worden — aber in
Ostasien nicht verlässlich. In Japan ließ sich der Effekt nicht belastbar
nachweisen, und in internationalen Vergleichen war er in ostasiatischen
Märkten am schwächsten.</p>
<p>Ein Werkzeug, das sich auf Belege stützt, darf dort nicht so tun, als
gälte dieselbe Regel. Deshalb: keine Abdeckung von Japan, Taiwan und
Südkorea — lieber eine Lücke als eine unbelegte Aussage.</p>""",
        ),
        "<h2>Datenherkunft</h2>",
        _method_card(
            "Kurse",
            ("total_return",),
            """<p>Tages-Schlusskurse von Yahoo Finance, dividenden- und
splitbereinigt. Zeilen ohne belastbare Zahl werden verworfen und gezählt;
die Zahl steht im Lauf-Protokoll. Liefert die Quelle zu wenige Titel, wird
bewusst <strong>kein</strong> Ranking gebildet, statt eines auf Lückenbasis.</p>""",
        ),
        "</main>",
    ]
    return "\n".join(body) + _foot()
