"""WEGWERF-PROBE: Gibt es fuer den US-Markt eine zweite Kursquelle?

Nach dem Befund wieder loeschen (zusammen mit
.github/workflows/probe_us_quelle.yml).

DIE FRAGE
Der DE-Kursvergleich lebt davon, dass die iShares-Bestandslisten eine
Spalte "Kurs" fuehren. Fuer die USA gibt es diese zweite Meinung bisher
nicht. Zwei Kandidaten stehen zur Debatte:

  (a) die US-Bestandsliste des iShares Core S&P 500 (IVV) ueber den
      amerikanischen Endpunkt (1467271812596.ajax). Beobachtet wurde
      bisher, dass amerikanische iShares-Seiten statt der Datei eine
      Zustimmungs-Seite ausliefern -- ob das auch fuer die Runner-Adressen
      gilt, ist genau die offene Frage.

  (b) ein in Europa aufgelegter S&P-500-ETF von iShares, dessen Datei
      ueber den BEWAEHRTEN deutschen Endpunkt-Typ kommt
      (1478358465952.ajax auf de/privatanleger) -- also derselbe Weg, der
      fuer DAX, MDAX und TecDAX seit Monaten zuverlaessig laeuft.

DIESE PROBE ENTSCHEIDET NICHTS. Sie berichtet nur, was ankam: HTTP-Code,
Inhaltstyp, Groesse, die ersten Zeilen, und -- falls es eine CSV ist --
ob der ECHTE Parser sie lesen kann und ob eine Kurs-Spalte drin steckt.
Ob daraus ein Gatter wird, entscheidet Easy (Stufe 2b).

WICHTIG: Die Produkt-IDs unter (b) sind RECHERCHE, nicht verifiziert --
genau deshalb wird hier ja gemessen. Eine URL, die nicht zieht, ist ein
gueltiges Ergebnis und kein Fehler; die Probe endet immer gruen.
"""

from __future__ import annotations

import datetime as _dt
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from momentum.ishares import (  # noqa: E402
    KURS_SPALTEN,
    USER_AGENT,
    QuelleUnbrauchbar,
    _kopfzeile_finden,
    parse_ishares_holdings,
)

# (Bezeichnung, URL). Die erste ist die vom Auftrag genannte US-Datei, die
# uebrigen sind europaeische S&P-500-ETFs von iShares ueber den bewaehrten
# deutschen Endpunkt-Typ.
KANDIDATEN: tuple[tuple[str, str], ...] = (
    (
        "IVV — iShares Core S&P 500 (US-Endpunkt)",
        "https://www.ishares.com/us/products/239726/"
        "ishares-core-sp-500-etf/1467271812596.ajax"
        "?fileType=csv&fileName=IVV_holdings&dataType=fund",
    ),
    (
        "SXR8 / CSPX — iShares Core S&P 500 UCITS (DE-Endpunkt, Produkt 253743)",
        "https://www.ishares.com/de/privatanleger/de/produkte/253743/"
        "ishares-sp-500-b-ucits-etf-acc-fund/1478358465952.ajax"
        "?fileType=csv&fileName=SXR8_holdings&dataType=fund",
    ),
    (
        "IUSA — iShares S&P 500 UCITS (DE-Endpunkt, Produkt 251900)",
        "https://www.ishares.com/de/privatanleger/de/produkte/251900/"
        "ishares-sp-500-ucits-etf-inc-fund/1478358465952.ajax"
        "?fileType=csv&fileName=IUSA_holdings&dataType=fund",
    ),
)

# So viele Zeilen erwartet eine S&P-500-Bestandsliste. Nur zur Einordnung
# in der Ausgabe -- die Probe bricht an nichts ab.
ERWARTETE_ZEILEN = (495, 510)


def log(text: str = "") -> None:
    print(text, flush=True)


def hole(url: str) -> tuple[int, str, bytes, str]:
    """(HTTP-Code, Inhaltstyp, Rohdaten, Fehlertext)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as antwort:
            return (
                getattr(antwort, "status", 0),
                antwort.headers.get("Content-Type", "—"),
                antwort.read(),
                "",
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "—") if exc.headers else "—", b"", ""
    except Exception as exc:  # noqa: BLE001 - jede Sperre ist selbst der Befund
        return 0, "—", b"", f"{type(exc).__name__}: {exc}"


def beurteile(rohdaten: bytes) -> list[str]:
    """Was steckt drin? Nur berichten, nichts entscheiden."""
    if not rohdaten:
        return ["  Inhalt: leer"]
    text = rohdaten.decode("utf-8-sig", "replace")
    zeilen = [f"  Groesse: {len(rohdaten)} Bytes"]
    kopf = text[:400].replace("\n", " | ").strip()
    zeilen.append(f"  Anfang:  {kopf[:300]}")

    if "<html" in text[:2000].lower():
        zeilen.append("  ==> HTML statt CSV — vermutlich die Zustimmungs-Seite.")
        return zeilen

    try:
        _, trenner, spalten = _kopfzeile_finden(text.splitlines())
    except QuelleUnbrauchbar as exc:
        zeilen.append(f"  ==> keine erkennbare Kopfzeile: {exc}")
        return zeilen
    zeilen.append(f"  Trenner: {trenner!r}")
    zeilen.append(f"  Spalten: {', '.join(spalten)}")
    kurs_spalte = [s for s in spalten if s in KURS_SPALTEN]
    zeilen.append(
        f"  ==> Kurs-Spalte: {'JA — ' + kurs_spalte[0] if kurs_spalte else 'NEIN'}"
    )

    # Mit dem ECHTEN Parser gegenlesen. Das Anzahl-Gatter wird ausgesetzt
    # (ein S&P 500 passt in keinen der drei DE-Bereiche), das
    # Veraltungs-Gatter bleibt scharf -- es ist Teil der Frage.
    #
    # Zwei Eigenheiten der Ausgabe, die hier nichts bedeuten: Fehlermeldungen
    # sprechen von "DAX-Bestandsliste" (der Parser bekommt diesen Namen als
    # Platzhalter), und Ticker erscheinen mit ".DE"-Endung, weil die
    # DE-Uebersetzung stumpf angehaengt wird. Beides ist fuer die Frage
    # "gibt es hier ueberhaupt eine Kurs-Spalte" ohne Belang.
    try:
        befund = parse_ishares_holdings(
            text, "DAX", heute=_dt.date.today(), erwartete_anzahl=(1, 100000)
        )
    except QuelleUnbrauchbar as exc:
        zeilen.append(f"  ==> Parser: {exc}")
        return zeilen
    mit_kurs = [k for k in befund.kandidaten if k.kurs is not None]
    unten, oben = ERWARTETE_ZEILEN
    zeilen.append(
        f"  ==> Parser: Stichtag {befund.bestand_stand}, "
        f"{befund.aktien_zeilen} Aktien-Zeilen (S&P 500 waere {unten}–{oben}), "
        f"{len(befund.kandidaten)} Ticker, {len(mit_kurs)} mit Kurs, "
        f"Zahlenschreibweise {befund.kurs_konvention or 'nicht eindeutig'}"
    )
    if mit_kurs:
        probe = mit_kurs[:3]
        zeilen.append(
            "  ==> Beispiele: "
            + "; ".join(
                f"{k.ticker} {k.kurs} {k.waehrung or '—'}" for k in probe
            )
        )
    return zeilen


def main() -> int:
    log(f"Probe US-Quelle, {_dt.date.today().isoformat()}")
    log("Sie schreibt nichts und entscheidet nichts — sie berichtet.")
    log()
    for name, url in KANDIDATEN:
        log(f"### {name}")
        log(f"  URL: {url}")
        code, typ, rohdaten, fehler = hole(url)
        if fehler:
            log(f"  ==> nicht erreichbar: {fehler}")
            log()
            continue
        log(f"  HTTP {code}, Content-Type {typ}")
        for zeile in beurteile(rohdaten):
            log(zeile)
        log()
    log("Ende der Probe. Kein Ergebnis dieser Probe wirkt auf irgendeinen Lauf.")
    # Immer gruen: eine URL, die nicht zieht, IST das Ergebnis.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
