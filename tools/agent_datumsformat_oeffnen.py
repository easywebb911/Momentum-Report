"""Reparatur-Agent, Stufe 3 -- der EINZIGE Ort, an dem tatsaechlich Git-
und `gh`-Befehle ausgefuehrt werden (Branch, Commit, Push, PR-Erstellung).

Bewusst getrennt von `tools/agent_datumsformat.py`: dort lebt die reine,
ohne Netz testbare Ableitung (Roh-Zeile -> Muster -> Vorschlag); hier NUR
die duenne Orchestrierung der bereits fertigen Vorschlaege aus dessen
`--ausgabe`-Datei. Diese Trennung ist der Grund, warum die Kernlogik ohne
echtes Repository und ohne `gh` getestet werden kann (siehe
tests/unit/test_agent_datumsformat_oeffnen.py) -- nur die duenne Huelle
hier bleibt ungetestet, nicht die Entscheidungen selbst.

HARTE GRENZE: dieses Skript OEFFNET PRs (`gh pr create --draft`) und
MERGT NIE -- kein `gh pr merge`-Aufruf existiert hier, an keiner Stelle.

BREMSE gegen PR-Flut: vor jedem Oeffnen wird per `gh pr list` geprueft, ob
zu genau diesem Titel (Marker "Agent: iShares-Datumsformat <Quelle>")
schon ein offener PR existiert. Wenn ja: nur geloggt, nicht erneut
geoeffnet -- ein offener PR je Bestandsquelle ist die Obergrenze.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

ISHARES_PY_PFAD = Path("src/momentum/ishares.py")


def bereits_offener_pr(titel: str, *, laeufer=subprocess.run) -> bool:
    """True, wenn `gh pr list` bereits einen offenen PR mit diesem exakten
    Titel findet -- die Bremse gegen wiederholtes Oeffnen."""
    ergebnis = laeufer(
        ["gh", "pr", "list", "--state", "open", "--search", f'in:title "{titel}"',
         "--json", "number"],
        capture_output=True, text=True, check=True,
    )
    return len(json.loads(ergebnis.stdout)) > 0


def oeffne_pr(vorschlag: dict, index: int, *, laeufer=subprocess.run) -> None:
    """Branch, Commit, Push, PR -- fuer GENAU EINEN Vorschlag. Jeder
    Git-/gh-Schritt einzeln und pruefbar (`check=True`: ein Fehlschlag
    irgendwo bricht laut ab, statt einen halbfertigen Zustand zu
    hinterlassen -- kein PR ist besser als ein PR mit falschem Titel)."""
    zeitstempel = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    zweig = f"agent/datumsformat-{zeitstempel}-{index}"

    laeufer(["git", "checkout", "-b", zweig], check=True)
    ISHARES_PY_PFAD.write_text(vorschlag["neuer_quelltext"], encoding="utf-8")
    laeufer(["git", "config", "user.name", "momentum-agent"], check=True)
    laeufer(["git", "config", "user.email", "actions@github.com"], check=True)
    laeufer(["git", "add", str(ISHARES_PY_PFAD)], check=True)
    commit_text = f"{vorschlag['titel']}\n\n{vorschlag['pr_text']}"
    laeufer(["git", "commit", "-m", commit_text], check=True)
    laeufer(["git", "push", "-u", "origin", zweig], check=True)
    laeufer(
        ["gh", "pr", "create", "--draft", "--title", vorschlag["titel"],
         "--body", vorschlag["pr_text"], "--head", zweig],
        check=True,
    )
    laeufer(["git", "checkout", "-"], check=True)


def main(argv: list[str] | None = None, *, laeufer=subprocess.run) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("Aufruf: agent_datumsformat_oeffnen.py <vorschlaege.json>", file=sys.stderr)
        return 2
    daten = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    vorschlaege = daten["vorschlaege"]
    print(f"{len(vorschlaege)} Vorschlag/Vorschlaege abgeleitet.")
    for i, vorschlag in enumerate(vorschlaege):
        if bereits_offener_pr(vorschlag["titel"], laeufer=laeufer):
            print(f"Bereits ein offener PR fuer '{vorschlag['titel']}' -- kein zweiter.")
            continue
        oeffne_pr(vorschlag, i, laeufer=laeufer)
        print(f"PR geoeffnet: {vorschlag['titel']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - Einstiegspunkt
    raise SystemExit(main())
