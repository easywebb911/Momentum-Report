"""Der Wiedervorlagen-Wächter (wiedervorlagen_waechter.py) — geprueft
ohne echte Datei (`ermittle_eintraege`/`melder` ersetzen Datei-Zugriff
und ntfy).

Kernaussagen: §3 wird ausschliesslich ueber den `faellig`-Kommentar
ausgewertet, nie ueber den sichtbaren Freitext. "offen"-Zeilen werden
NIE gemeldet. Eine faellige Zeile loest am Faelligkeitstag und am Tag
1/8/15/... danach eine Meldung aus, sonst Stille. Fehlt der Kommentar
oder ist er unlesbar: fail-soft, Exit 1, kein Absturz. Und: MELDEN, NIE
HANDELN -- dieses Modul schreibt nirgends.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pytest
import yaml

from momentum.wiedervorlagen_waechter import (
    ERINNERUNG_TAGE,
    Eintrag,
    FormatFehler,
    faellige_bloecke,
    kurztitel,
    lies_eintraege,
    main,
    meldetext,
    parse_eintraege,
    status_am_tag,
)

Date = _dt.date


def zeile(wann_kommentar: str, was: str = "**Titel.** Text.") -> str:
    return f"| **Platzhalter** <!-- faellig: {wann_kommentar} --> | {was} | Warum-Spalte |"


def tabelle(*zeilen: str) -> str:
    kopf = "## 3. Wiedervorlagen (mit Datum)\n\n| Wann | Was | Warum |\n|---|---|---|\n"
    return kopf + "\n".join(zeilen) + "\n\n---\n"


# --------------------------------------------------------------- parse_eintraege


def test_parse_eintraege_liest_datum_und_offen():
    text = tabelle(zeile("2026-10-30"), zeile("offen"))
    eintraege = parse_eintraege(text)
    assert len(eintraege) == 2
    assert eintraege[0].faellig == Date(2026, 10, 30)
    assert eintraege[1].faellig is None


def test_parse_eintraege_entfernt_den_kommentar_aus_dem_sichtbaren_text():
    text = tabelle(zeile("2026-10-30"))
    [eintrag] = parse_eintraege(text)
    assert eintrag.wann_sichtbar == "**Platzhalter**"
    assert "<!--" not in eintrag.wann_sichtbar


def test_parse_eintraege_ueberspringt_kopf_und_trennzeile():
    text = tabelle(zeile("offen"))
    eintraege = parse_eintraege(text)
    assert len(eintraege) == 1


def test_parse_eintraege_abschnitt_fehlt_wirft_formatfehler():
    with pytest.raises(FormatFehler):
        parse_eintraege("# Irgendein anderes Dokument\n\nkein §3 hier.")


def test_parse_eintraege_fehlender_kommentar_wirft_formatfehler():
    text = "## 3. Wiedervorlagen (mit Datum)\n\n| Wann | Was | Warum |\n|---|---|---|\n| **30.10.2026** | Text | Warum |\n\n---\n"
    with pytest.raises(FormatFehler, match="kein 'faellig'-Kommentar"):
        parse_eintraege(text)


def test_parse_eintraege_ungueltiges_datum_wirft_formatfehler():
    text = tabelle(zeile("30. Oktober 2026"))
    with pytest.raises(FormatFehler):
        parse_eintraege(text)


def test_parse_eintraege_leerer_abschnitt_ergibt_leere_liste():
    text = tabelle()
    assert parse_eintraege(text) == []


# -------------------------------------------------------------------- lies_eintraege


def test_lies_eintraege_datei_fehlt(tmp_path):
    eintraege, grund = lies_eintraege(pfad=tmp_path / "nicht_da.md")
    assert eintraege is None
    assert grund is not None and "nicht lesbar" in grund


def test_lies_eintraege_kaputtes_format_wird_gemeldet_nicht_geworfen(tmp_path):
    pfad = tmp_path / "SESSION_HANDOVER.md"
    pfad.write_text(
        "## 3. Wiedervorlagen (mit Datum)\n\n| Wann | Was | Warum |\n|---|---|---|\n"
        "| **30.10.2026** | Text ohne Kommentar | Warum |\n\n---\n",
        encoding="utf-8",
    )
    eintraege, grund = lies_eintraege(pfad=pfad)
    assert eintraege is None
    assert grund is not None and "faellig" in grund


def test_lies_eintraege_funktioniert_mit_echter_datei():
    eintraege, grund = lies_eintraege()
    assert grund is None
    assert len(eintraege) >= 1


# --------------------------- Teil C: Format-Test gegen die echte §3-Tabelle


def test_jede_zeile_in_paragraph_3_hat_einen_gueltigen_faellig_kommentar():
    """Wird ROT, sobald irgendeine Zeile in §3 von SESSION_HANDOVER.md
    keinen `faellig`-Kommentar traegt oder sein Wert weder 'offen' noch
    ein gueltiges JJJJ-MM-TT-Datum ist -- die eigentliche Pruefung steckt
    in parse_eintraege()/_faellig_parsen(), hier nur gegen die ECHTE
    Datei ausgefuehrt, nicht gegen eine Attrappe."""
    text = Path("SESSION_HANDOVER.md").read_text(encoding="utf-8")
    try:
        eintraege = parse_eintraege(text)
    except FormatFehler as exc:
        pytest.fail(f"§3 enthaelt eine Zeile ohne gueltigen faellig-Kommentar: {exc}")
    assert len(eintraege) >= 1, "§3 scheint leer zu sein -- Muster passt nicht mehr"


# -------------------------------------------------------------------- status_am_tag


def test_status_am_tag_heute_faellig():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 10, 30)) == ("heute_faellig", 0)


def test_status_am_tag_noch_nicht_faellig_ist_still():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 10, 29)) is None


def test_status_am_tag_ueberfaellig_tag_1_meldet():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 10, 31)) == ("ueberfaellig", 1)


def test_status_am_tag_ueberfaellig_tag_2_bleibt_still():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 11, 1)) is None


def test_status_am_tag_ueberfaellig_tag_7_bleibt_still():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 11, 6)) is None


def test_status_am_tag_ueberfaellig_tag_8_meldet_erneut():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 11, 7)) == ("ueberfaellig", 8)


def test_status_am_tag_ueberfaellig_tag_15_meldet_erneut():
    assert status_am_tag(Date(2026, 10, 30), Date(2026, 11, 14)) == ("ueberfaellig", 15)
    assert (15 - 1) % ERINNERUNG_TAGE == 0


# -------------------------------------------------------------------- kurztitel


def test_kurztitel_nimmt_das_erste_fette_wort():
    assert kurztitel("**Drittes Vertragstest-Fenster.** Rest hier.") == "Drittes Vertragstest-Fenster."


def test_kurztitel_faellt_auf_den_ganzen_text_zurueck_ohne_fettung():
    assert kurztitel("Nur normaler Text ohne Sternchen") == "Nur normaler Text ohne Sternchen"


def test_kurztitel_kuerzt_sehr_lange_titel():
    lang = "**" + ("x" * 200) + "**"
    gekuerzt = kurztitel(lang, max_laenge=20)
    assert len(gekuerzt) == 20
    assert gekuerzt.endswith("…")


# -------------------------------------------------------------------- faellige_bloecke


def test_faellige_bloecke_offen_wird_nie_gemeldet():
    eintraege = [Eintrag("offen, keine Frist", "**Text.**", None)]
    assert faellige_bloecke(eintraege, Date(2026, 10, 30)) == []


def test_faellige_bloecke_nichts_faellig_ist_leer():
    eintraege = [Eintrag("30.10.2026", "**Text.**", Date(2026, 10, 30))]
    assert faellige_bloecke(eintraege, Date(2026, 10, 20)) == []


def test_faellige_bloecke_heute_faellig_enthaelt_die_zeile():
    eintraege = [Eintrag("30.10.2026", "**Mein Titel.** Rest.", Date(2026, 10, 30))]
    [(name, text)] = faellige_bloecke(eintraege, Date(2026, 10, 30))
    assert name == "Mein Titel."
    assert "📅 Heute fällig" in text
    assert "Mein Titel." in text


def test_faellige_bloecke_mehrere_zeilen_am_selben_tag():
    eintraege = [
        Eintrag("30.10.2026", "**Erste.** x", Date(2026, 10, 30)),
        Eintrag("30.10.2026", "**Zweite.** y", Date(2026, 10, 30)),
        Eintrag("offen", "**Dritte.** z", None),
    ]
    bloecke = faellige_bloecke(eintraege, Date(2026, 10, 30))
    assert {n for n, _ in bloecke} == {"Erste.", "Zweite."}


# ------------------------------------------------------------------------ main()


def test_main_still_und_gruen_wenn_nichts_faellig():
    eintraege = [Eintrag("30.10.2026", "**Text.**", Date(2026, 10, 30))]
    gerufen = []
    code = main(
        ["--heute", "2026-10-20"],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_eintraege=lambda: (eintraege, None),
    )
    assert code == 0
    assert gerufen == []


def test_main_pusht_am_faelligkeitstag():
    eintraege = [Eintrag("30.10.2026", "**Mein Titel.** Rest.", Date(2026, 10, 30))]
    gerufen = []
    code = main(
        ["--heute", "2026-10-30"],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_eintraege=lambda: (eintraege, None),
    )
    assert code == 0, "der Push IST das Signal -- kein roter Lauf noetig"
    assert len(gerufen) == 1
    assert "Mein Titel." in gerufen[0]


def test_main_offen_wird_nie_gemeldet_auch_nicht_zufaellig():
    eintraege = [Eintrag("offen, keine Frist", "**Niemals.**", None)]
    gerufen = []
    for tag in ("2026-01-01", "2026-06-15", "2026-12-31"):
        code = main(
            ["--heute", tag],
            melder=lambda text: gerufen.append(text) or True,
            ermittle_eintraege=lambda: (eintraege, None),
        )
        assert code == 0
    assert gerufen == []


def test_main_erinnerung_hoechstens_einmal_pro_woche_ueber_drei_wochen():
    eintraege = [Eintrag("30.10.2026", "**Mein Titel.**", Date(2026, 10, 30))]
    ergebnisse = {}
    for versatz in range(0, 16):
        tag = (Date(2026, 10, 30) + _dt.timedelta(days=versatz)).isoformat()
        gerufen = []
        main(
            ["--heute", tag],
            melder=lambda text: gerufen.append(text) or True,
            ermittle_eintraege=lambda: (eintraege, None),
        )
        ergebnisse[versatz] = bool(gerufen)

    assert ergebnisse[0] is True  # heute faellig
    assert ergebnisse[1] is True  # Tag 1 ueberfaellig
    for versatz in range(2, 8):
        assert ergebnisse[versatz] is False, f"Tag {versatz} haette still bleiben muessen"
    assert ergebnisse[8] is True  # Erinnerung
    for versatz in range(9, 15):
        assert ergebnisse[versatz] is False, f"Tag {versatz} haette still bleiben muessen"
    assert ergebnisse[15] is True  # zweite Erinnerung


def test_main_technischer_fehlschlag_ist_rot_und_wird_trotzdem_gemeldet():
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_eintraege=lambda: (None, "Zeile 3: kein 'faellig'-Kommentar."),
    )
    assert code == 1
    assert len(gerufen) == 1
    assert "nicht lesen" in gerufen[0]


def test_main_fail_soft_bei_kaputtem_format_stuerzt_nicht_ab(tmp_path):
    pfad = tmp_path / "SESSION_HANDOVER.md"
    pfad.write_text(
        "## 3. Wiedervorlagen (mit Datum)\n\n| Wann | Was | Warum |\n|---|---|---|\n"
        "| **kaputt** | ohne Kommentar | Warum |\n\n---\n",
        encoding="utf-8",
    )
    gerufen = []
    code = main(
        [],
        melder=lambda text: gerufen.append(text) or True,
        ermittle_eintraege=lambda: lies_eintraege(pfad=pfad),
    )
    assert code == 1
    assert len(gerufen) == 1


def test_main_ein_gescheiterter_push_aendert_den_exit_code_nie():
    eintraege = [Eintrag("30.10.2026", "**Text.**", Date(2026, 10, 30))]

    def wirft(_text):
        raise OSError("keine Verbindung")

    code = main(
        ["--heute", "2026-10-30"],
        melder=wirft,
        ermittle_eintraege=lambda: (eintraege, None),
    )
    assert code == 0


# ----------------------------------------------- Ziel-Mechanik (Exzellenz 1)


def test_am_30_10_2026_kaeme_heute_faellig_fuer_die_stichtag_zeilen():
    """Belegt per festem Datum, wie im Auftrag gefordert: am 30.10.2026
    waeren die drei 30.10.-Zeilen (Split-Waechter, Sektor-Hinweis,
    Stichtag-Schutz-Fix) alle 'Heute faellig'."""
    eintraege = [
        Eintrag("30.10.2026", "**Split-Test.**", Date(2026, 10, 30)),
        Eintrag("30.10.2026", "**Sektor-Test.**", Date(2026, 10, 30)),
        Eintrag("30.10.2026", "**Stichtag-Test.**", Date(2026, 10, 30)),
        Eintrag("25.–31.10.2026", "**Vertragstest-Fenster.**", Date(2026, 10, 25)),
    ]
    bloecke = faellige_bloecke(eintraege, Date(2026, 10, 30))
    namen = {n for n, _ in bloecke}
    assert namen == {"Split-Test.", "Sektor-Test.", "Stichtag-Test."}
    assert all("📅 Heute fällig" in text for _, text in bloecke)


# ----------------------------------------- Determinismus (Exzellenz 7)


def test_meldetext_ist_deterministisch():
    eintrag = Eintrag("30.10.2026", "**Text.**", Date(2026, 10, 30))
    a = meldetext(eintrag, *status_am_tag(eintrag.faellig, Date(2026, 10, 30)))
    b = meldetext(eintrag, *status_am_tag(eintrag.faellig, Date(2026, 10, 30)))
    assert a == b


# -------------------------------------------------------- Melden, nie Handeln


def test_der_waechter_code_kann_nirgends_schreiben():
    """Statischer Nie-Handeln-Test, analog zu jedem anderen Waechter
    dieses Projekts."""
    quelltext = Path("src/momentum/wiedervorlagen_waechter.py").read_text(encoding="utf-8")
    _, _, code = quelltext.partition('"""\n\nfrom __future__')
    assert code, "Modul-Docstring nicht gefunden -- Test greift ins Leere"
    verboten = [
        "write_text", "write_bytes", "open(",
        "\"w\")", "'w')", "\"wb\"", "'wb'", "\"a\")", "'a')",
        "git commit", "git push", "git add", "gh pr",
    ]
    for muster in verboten:
        assert muster not in code, f"verbotenes Muster im Code gefunden: {muster!r}"


def test_der_workflow_kann_nur_lesen():
    daten = yaml.safe_load(
        Path(".github/workflows/wiedervorlagen_waechter.yml").read_text(encoding="utf-8")
    )
    assert daten["permissions"] == {"contents": "read"}
    assert "write" not in yaml.dump(daten["permissions"])
    ausloeser = daten[True] if True in daten else daten["on"]
    zeitplaene = ausloeser["schedule"]
    assert len(zeitplaene) == 1
    minute, stunde = zeitplaene[0]["cron"].split()[:2]
    assert minute not in ("0", "30"), "Zeitpunkt darf nicht zur vollen/halben Stunde liegen"
    assert "workflow_dispatch" in ausloeser
    text = Path(".github/workflows/wiedervorlagen_waechter.yml").read_text(encoding="utf-8")
    assert "secrets.NTFY_TOPIC" in text
    assert "${{ inputs." not in text


def test_der_workflow_laeuft_morgens_in_berlin_in_beiden_zeitzonen():
    daten = yaml.safe_load(
        Path(".github/workflows/wiedervorlagen_waechter.yml").read_text(encoding="utf-8")
    )
    ausloeser = daten[True] if True in daten else daten["on"]
    minute, stunde = ausloeser["schedule"][0]["cron"].split()[:2]
    utc_uhrzeit = _dt.time(int(stunde), int(minute))
    # MEZ (Winter) = UTC+1, MESZ (Sommer) = UTC+2 -- beide Lokalzeiten
    # muessen im Berliner Morgen (06:00-11:00) liegen.
    mez = (_dt.datetime.combine(_dt.date.today(), utc_uhrzeit) + _dt.timedelta(hours=1)).time()
    mesz = (_dt.datetime.combine(_dt.date.today(), utc_uhrzeit) + _dt.timedelta(hours=2)).time()
    for lokal in (mez, mesz):
        assert _dt.time(6, 0) <= lokal <= _dt.time(11, 0), lokal
