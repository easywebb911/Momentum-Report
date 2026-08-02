"""HTML-Erzeugung fuer docs/ (GitHub Pages).

Die Methodik-Seite wird aus sources.SOURCES erzeugt -- damit KANN sie nicht
von den Belegen im Code abweichen; der 1:1-Abgleich ist strukturell und
wird zusaetzlich in tests/unit/test_sources.py festgehalten.
"""

from __future__ import annotations

import datetime as _dt
import html
from dataclasses import dataclass

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
        "Was die Trend-Ampel oben je Markt bedeutet:",
        "methodik.html#trend-ampel",
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
        '<section class="disc-box" aria-label="Was dieses Werkzeug nicht kann">\n'
        '  <ul class="disc-list">\n' + "\n".join(items) + "\n  </ul>\n</section>"
    )


def _trend_banner(view: MarketView) -> str:
    ampel = view.ranking["trend_ampel"]
    ret = ampel["rendite_12m"]
    src = source("momentum_crash")
    if ampel["warnung"]:
        return f"""  <div class="ampel ampel--warn" role="status">
    <span class="ampel-dot" aria-hidden="true"></span>
    <span class="ampel-body"><strong>Momentum-Gefahrenlage:</strong> Markt im 12-Monats-Minus
    ({e(ampel["index_name"])} {de_pct(ret)}) — in solchen Phasen häufen sich historisch die
    Momentum-Einbrüche. <a href="methodik.html#trend-ampel">Was das heißt →</a>
    <span class="ampel-src">{e(src.short)}</span></span>
  </div>"""
    return f"""  <div class="ampel ampel--ok" role="status">
    <span class="ampel-body">{e(ampel["index_name"])} auf 12 Monate {de_pct(ret)} — das
    Trendkriterium schlägt derzeit nicht an.
    <a href="methodik.html#trend-ampel">Erklärung →</a></span>
  </div>"""


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
    return f"""      <article class="card">
        <div class="card-hd">
          <div class="card-id">
            <span class="rank">{row["rang"]}</span>
            <span class="id-text">
              <span class="ticker">{e(row["ticker"])}</span>
              <span class="cname">{e(row["name"])}</span>
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
            <span class="m-val">{price_text}</span>
            <span class="m-lbl">Kurs ({e(market.currency)})</span>
          </div>
        </div>
        <p class="card-ft">Rang aus belegter Rechenvorschrift — keine Prognose für diese Aktie.</p>
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
        # Reihenfolge mit Absicht: erst die Ehrlichkeits-Anzeigen, dann die
        # Dekoration, dann der Inhalt. Warnendes steht zuoberst -- ein
        # Schmuckband darf die vier Hinweise nicht nach unten druecken.
        _honesty_block(),
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
        "<h2>Die zwei Zutaten des Scores</h2>",
        _method_card(
            "1. 12-1-Momentum (Gewicht 70 %)",
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
            "2. Nähe zum 52-Wochen-Hoch (Gewicht 30 %)",
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
<p>Wichtig: Die Ränge werden <strong>immer nur innerhalb eines Marktes</strong>
gebildet — US-Titel gegen US-Titel, deutsche gegen deutsche. Nie gemischt.
Bei exakt gleichem Wert entscheidet die alphabetische Reihenfolge des Tickers;
dadurch ist die Rangliste bei jedem Lauf identisch reproduzierbar.</p>""",
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
            """<p>Steht der Marktindex über die letzten zwölf Monate im Minus,
erscheint eine deutliche Warnung. In genau solchen Phasen häuften sich
historisch die schweren Momentum-Einbrüche.</p>
<p>Die Ampel ist <strong>reine Anzeige</strong>. Sie greift nicht in die
Rangliste ein, filtert nichts heraus und verändert keinen Score. Gemessen
wird der S&amp;P 500 für die USA und der DAX für Deutschland.</p>""",
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
        _method_card(
            "Klare Grenzen",
            ("long_only", "decay", "portfolio_statistic"),
            """<ul class="nolist">
<li>Keine Rückrechnung (Backtest), keine Trefferquote, keine Erfolgsbilanz —
das wäre eine eigene Wissenschaft und würde hier nur Sicherheit vortäuschen.</li>
<li>Keine Kursziele, keine Kauf- oder Verkaufssignale, keine Ausstiegsregeln.</li>
<li>Keine Verlierer-Seite: Die Studien messen Gewinner <em>minus</em> Verlierer.
Hier steht nur die Gewinner-Seite — die Studienrenditen gelten für das
Gezeigte also nicht.</li>
<li>Keine Zutat ohne Quelle. Nichts wird „weil es plausibel klingt“ ergänzt.</li>
<li>Keine risikogesteuerten Varianten in dieser Fassung — dokumentiert, aber
nicht gebaut.</li>
<li>Der Effekt ist im US-Markt nach 2000 deutlich geschrumpft. Das steht auf
der Startseite, weil es dorthin gehört.</li>
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
