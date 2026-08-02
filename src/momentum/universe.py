"""Universums-Listen lesen -- committete, statische Dateien.

Bewusste Entscheidung: das Universum wird NICHT bei jedem Lauf frisch aus
dem Netz gezogen. Es steht als Datei im Repo, mit Herkunft und Stand-Datum
im Kopf, und wird nur durch einen bewusst angestossenen Vorgang
(.github/workflows/universe-bootstrap.yml) veraendert. So kann sich das
Universum nie unbemerkt unter einem laufenden Ranking wegdrehen.

Dateiformat (UTF-8):

    # Universum: <Bezeichnung>
    # Herkunft: <Quelle, woertlich>
    # Stand: JJJJ-MM-TT
    # STATUS: PLACEHOLDER      <- optional; solange gesetzt: harter Abbruch
    TICKER<TAB>Firmenname
    ...
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_MARKER = "PLACEHOLDER"


class UniverseNotReady(Exception):
    """Universum ist Platzhalter oder unbrauchbar -- lauter Abbruch.

    Niemals ein stiller Rueckfall auf eine Teilliste: lieber gar kein
    Ranking als ein Ranking auf einem erfundenen Universum.
    """


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    name: str


@dataclass(frozen=True)
class Universe:
    label: str
    origin: str
    as_of: str
    entries: tuple[UniverseEntry, ...]

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(e.ticker for e in self.entries)

    def name_of(self, ticker: str) -> str:
        for entry in self.entries:
            if entry.ticker == ticker:
                return entry.name
        return ticker


def _parse_header(lines: list[str]) -> dict[str, str]:
    header: dict[str, str] = {}
    for raw in lines:
        if not raw.startswith("#"):
            break
        body = raw.lstrip("#").strip()
        if ":" in body:
            key, _, value = body.partition(":")
            header[key.strip().lower()] = value.strip()
    return header


def load_universe(path: str | Path) -> Universe:
    """Universum laden und alle Kopfangaben erzwingen."""
    p = Path(path)
    if not p.exists():
        raise UniverseNotReady(f"Universums-Datei fehlt: {p}")
    lines = p.read_text(encoding="utf-8").splitlines()
    header = _parse_header(lines)

    if header.get("status", "").upper().startswith(PLACEHOLDER_MARKER):
        raise UniverseNotReady(
            f"{p} ist noch ein PLATZHALTER. Das Universum muss einmal ueber "
            f"den Workflow 'Universum aktualisieren' (workflow_dispatch) "
            f"befuellt werden. Bis dahin wird bewusst KEIN Ranking gebildet."
        )

    missing = [k for k in ("universum", "herkunft", "stand") if k not in header]
    if missing:
        raise UniverseNotReady(
            f"{p}: Kopfangaben fehlen ({', '.join(missing)}). Herkunft und "
            f"Stand-Datum sind Pflicht -- ein Universum ohne Herkunft ist "
            f"fuer dieses Tool wertlos."
        )
    try:
        _dt.date.fromisoformat(header["stand"])
    except ValueError as exc:
        raise UniverseNotReady(f"{p}: 'Stand' ist kein Datum JJJJ-MM-TT") from exc

    entries: list[UniverseEntry] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        ticker, _, name = line.partition("\t")
        ticker = ticker.strip()
        name = name.strip() or ticker
        if not ticker:
            continue
        if ticker in seen:
            raise UniverseNotReady(f"{p}: Ticker {ticker} doppelt gelistet")
        seen.add(ticker)
        entries.append(UniverseEntry(ticker=ticker, name=name))

    if not entries:
        raise UniverseNotReady(f"{p}: keine Ticker enthalten")

    return Universe(
        label=header["universum"],
        origin=header["herkunft"],
        as_of=header["stand"],
        entries=tuple(entries),
    )
