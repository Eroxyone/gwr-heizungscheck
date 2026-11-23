"""Silver- und Gold-Layer des schweizweiten Strangs gegen das erfundene Register.

Jede erwartete Zahl laesst sich in tests/conftest.py von Hand nachzaehlen.
"""
from __future__ import annotations

import datetime as dt
import shutil

import pipeline
from conftest import (
    FERNWAERME,
    GAS_BEWILLIGT,
    KODES,
    OEL_VZ,
    SONDE,
    STAND_ALT,
    STAND_NEU,
    _gebaeude,
    baue_register,
    datenverzeichnis,
    schreibe_adressen,
    schreibe_gebaeude,
    schreibe_kodes,
)


def zeile(con, sql: str) -> dict:
    cur = con.execute(sql)
    spalten = [d[0] for d in cur.description]
    werte = cur.fetchall()
    assert len(werte) == 1, f"genau eine Zeile erwartet, {len(werte)} erhalten"
    return dict(zip(spalten, werte[0], strict=True))


# --------------------------------------------------------------------------- Silver

def test_silver_fuehrt_nur_bestehende_gebaeude_des_juengsten_stands(register):
    r = zeile(register, """
        SELECT count(*) AS n, count(DISTINCT egid) AS eindeutig, min(stand) AS von, max(stand) AS bis,
               count(*) FILTER (WHERE egid = 900000012) AS abgebrochen,
               count(*) FILTER (WHERE egid = 900000014) AS nur_im_alten_stand
        FROM silver_gebaeude_ch""")
    assert r["n"] == r["eindeutig"] == 18          # AI 12 (ohne das abgebrochene), ZG 6
    assert r["von"] == r["bis"] == dt.date.fromisoformat(STAND_NEU)
    assert r["abgebrochen"] == 0
    assert r["nur_im_alten_stand"] == 0


def test_silver_klassifiziert_energietraeger_und_quelle(register):
    klassen = dict(register.execute("""
        SELECT energie_klasse, count(*) FROM silver_gebaeude_ch
        WHERE kanton = 'AI' AND ist_wohngebaeude GROUP BY 1""").fetchall())
    assert klassen == {"oel": 2, "gas": 2, "waermepumpe": 6, "unbestimmt": 1}

    r = zeile(register, """
        SELECT energietraeger_txt, quelle_txt, ist_fossil, quelle_vz2000, hat_angabe, alter_jahre
        FROM silver_gebaeude_ch WHERE egid = 900000001""")
    assert r == {"energietraeger_txt": "Heizöl", "quelle_txt": "Gemäss Volkszählung 2000",
                 "ist_fossil": True, "quelle_vz2000": True, "hat_angabe": True, "alter_jahre": 25}

    # "Unbestimmt" ist ein Eintrag, aber keine Angabe
    assert register.execute(
        "SELECT hat_angabe FROM silver_gebaeude_ch WHERE egid = 900000010").fetchone()[0] is False


def test_adressen_werden_auf_dieselbe_schreibweise_gebracht(register):
    schluessel = register.execute("""
        SELECT egid, strasse_k, hausnr_k FROM silver_adresse_ch
        WHERE ist_offiziell ORDER BY egid""").fetchall()
    assert schluessel == [
        (900000001, "bahnhofstrasse", "4a"),       # "Bahnhofstr." / "4a"
        (900000002, "bahnhofstrasse", "4a"),       # "Bahnhofstrasse" / "4 A"
        (900000003, "dorfgasse", "7"),             # fuehrende Nullen fallen weg
    ]


# --------------------------------------------------------------------------- Gold

def test_gold_gemeinde_zaehlt_nur_wohngebaeude(register):
    r = zeile(register, """
        SELECT wohngebaeude, fossil, aus_vz2000, waermepumpe, mit_angabe, kandidaten
        FROM gold_gemeinde WHERE bfs_nr = 9001""")
    assert r == {"wohngebaeude": 11, "fossil": 4, "aus_vz2000": 2, "waermepumpe": 6,
                 "mit_angabe": 10, "kandidaten": 2}


def test_kandidat_ist_nur_wer_fossil_und_ungeprueft_ist(register):
    # Musterhausen: drei Oelheizungen aus der Volkszaehlung, drei Fernwaermeanschluesse von 2024.
    # Der Gaskessel mit Baubewilligung von 2020 in Testwil ist fossil, aber kein Kandidat.
    r = zeile(register, """
        SELECT fossil, kandidaten, pct_vz2000, pct_aktuell_15j, pflege_index
        FROM gold_gemeinde WHERE bfs_nr = 9002""")
    assert r["fossil"] == r["kandidaten"] == 3
    assert float(r["pct_vz2000"]) == 50.0
    assert float(r["pct_aktuell_15j"]) == 50.0
    # Mittel aus Vollstaendigkeit (100), Aktualitaet (50) und Herkunft (50)
    assert float(r["pflege_index"]) == 66.7


def test_gemeindesummen_ergeben_die_kantonssummen(register):
    abweichungen = register.execute("""
        WITH g AS (
            SELECT kanton, sum(wohngebaeude) AS wohngebaeude, sum(fossil) AS fossil,
                   sum(aus_vz2000) AS aus_vz2000, sum(kandidaten) AS kandidaten
            FROM gold_gemeinde GROUP BY 1)
        SELECT count(*) FROM gold_kanton k JOIN g USING (kanton)
        WHERE k.wohngebaeude <> g.wohngebaeude OR k.fossil <> g.fossil
           OR k.aus_vz2000 <> g.aus_vz2000 OR k.kandidaten <> g.kandidaten""").fetchone()[0]
    assert abweichungen == 0
    assert register.execute("SELECT count(*) FROM gold_kanton").fetchone()[0] == 2


KENNZAHLEN = [
    "wohngebaeude", "mit_angabe", "aktuell_5j", "aktuell_15j", "aus_vz2000", "fossil", "waermepumpe",
    "kandidaten", "median_alter_jahre", "aktualisiert_12m",
    "pct_vollstaendig", "pct_aktuell_5j", "pct_aktuell_15j", "pct_vz2000", "pct_ohne_vz2000",
    "pct_fossil", "pct_waermepumpe", "pct_kandidaten", "pct_bewegung_12m", "pflege_index",
]


def spalten(con, tabelle: str) -> list[str]:
    return [s[0] for s in con.execute(f"DESCRIBE {tabelle}").fetchall()]


def test_gold_gemeinde_fuehrt_jede_kennzahl(register):
    # Testwil am 12.01.2026, elf Wohngebaeude (Endziffern der EGID):
    #   01, 02      Heizoel, Volkszaehlung, 29.11.2001       25 Jahre alt
    #   03, 04      Erdwaermesonde, Kanton, 08.01.2026        0 Jahre
    #   05          Gas, Baubewilligung, 09.01.2026           0 Jahre
    #   06          Gas, Baubewilligung, 01.05.2020           6 Jahre
    #   07, 08, 09  Erdwaermesonde, Baubewilligung, 2023      3 Jahre
    #   10          unbestimmt, andere Quelle, 01.01.2012    14 Jahre
    #   13          Luft, Baubewilligung, 01.12.2025          1 Jahr
    r = zeile(register, "SELECT * EXCLUDE (kanton, gemeinde, stand) FROM gold_gemeinde WHERE bfs_nr = 9001")
    assert {k: float(w) if k.startswith("pct_") or k == "pflege_index" else w for k, w in r.items()} == {
        "bfs_nr": 9001,
        "wohngebaeude": 11,
        "mit_angabe": 10,               # alle ausser 10
        "aktuell_5j": 7,                # ab 12.01.2021: 03, 04, 05, 07, 08, 09, 13
        "aktuell_15j": 9,               # ab 12.01.2011: dazu 06 und 10
        "aus_vz2000": 2,
        "fossil": 4,                    # 01, 02, 05, 06
        "waermepumpe": 6,               # 03, 04, 07, 08, 09, 13
        "fernwaerme": 0,
        "holz": 0,
        "kandidaten": 2,                # 01, 02
        "median_alter_jahre": 3.0,      # 0, 0, 0, 1, 3, [3], 3, 6, 14, 25, 25
        "anzahl_quellen": 4,            # 859, 860, 864, 869
        "aktualisiert_12m": 4,          # ab 12.01.2025: 03, 04, 05, 13
        "pct_vollstaendig": 90.9,       # 10 von 11
        "pct_aktuell_5j": 63.6,         # 7 von 11
        "pct_aktuell_15j": 81.8,        # 9 von 11
        "pct_vz2000": 18.2,             # 2 von 11
        "pct_ohne_vz2000": 81.8,
        "pct_fossil": 36.4,             # 4 von 11
        "pct_waermepumpe": 54.5,        # 6 von 11
        "pct_kandidaten": 18.2,
        "pct_bewegung_12m": 36.4,
        "pflege_index": 84.8,           # (90,91 + 81,82 + 81,82) / 3
    }


def test_kanton_mit_einer_gemeinde_traegt_deren_kennzahlen(register):
    # Beide Kantone des Registers bestehen aus einer Gemeinde. Jede Kennzahl, die auf
    # beiden Ebenen gefuehrt wird, muss dort uebereinstimmen.
    assert spalten(register, "gold_kanton") == ["kanton", "stand", "gemeinden", *KENNZAHLEN]
    gemeinsam = ", ".join(["kanton", "stand", *KENNZAHLEN])
    kantone = register.execute(f"SELECT {gemeinsam} FROM gold_kanton ORDER BY kanton").fetchall()
    gemeinden = register.execute(f"SELECT {gemeinsam} FROM gold_gemeinde ORDER BY kanton").fetchall()
    assert kantone == gemeinden
    assert [k[0] for k in kantone] == ["AI", "ZG"]
    assert register.execute("SELECT DISTINCT gemeinden FROM gold_kanton").fetchall() == [(1,)]


def test_kanton_fasst_seine_gemeinden_zusammen(tmp_path, monkeypatch):
    """Ein Kanton mit zwei Gemeinden: Der Kanton rechnet ueber alle Gebaeude, nicht ueber
    die Kennzahlen der Gemeinden. Am Median zeigt sich der Unterschied.

        Oberdorf   zweimal Heizoel aus der Volkszaehlung (25 Jahre), eine Sonde von 2023 (3)
        Unterdorf  Fernwaerme von 2024 (2 Jahre), Gas mit Baubewilligung von 2020 (6)
    """
    ober = lambda egid, heizung: _gebaeude(egid, "GL", 9003, "Oberdorf", heizung)       # noqa: E731
    unter = lambda egid, heizung: _gebaeude(egid, "GL", 9004, "Unterdorf", heizung)     # noqa: E731
    schreibe_gebaeude(tmp_path, STAND_NEU, "GL", [
        ober(900000201, OEL_VZ), ober(900000202, OEL_VZ), ober(900000203, SONDE),
        unter(900000204, FERNWAERME), unter(900000205, GAS_BEWILLIGT)])
    schreibe_adressen(tmp_path, STAND_NEU, "GL", [{"EGID": "900000201", "STRNAME": "Dorfplatz", "DEINR": "1"}])
    schreibe_kodes(tmp_path, KODES)
    datenverzeichnis(monkeypatch, tmp_path)

    con = pipeline.run("ch")
    try:
        assert spalten(con, "gold_gemeinde") == [
            "kanton", "bfs_nr", "gemeinde", "stand", *KENNZAHLEN[:7], "fernwaerme", "holz", "kandidaten",
            "median_alter_jahre", "anzahl_quellen", *KENNZAHLEN[9:]]
        gemeinden = con.execute("""
            SELECT gemeinde, wohngebaeude, fossil, fernwaerme, kandidaten, median_alter_jahre,
                   anzahl_quellen, pflege_index::DOUBLE
            FROM gold_gemeinde ORDER BY bfs_nr""").fetchall()
        assert gemeinden == [
            # Vollstaendigkeit 100, Aktualitaet 33,3 (die Sonde), Herkunft 33,3
            ("Oberdorf", 3, 2, 0, 2, 25.0, 2, 55.6),
            # 100, 100, 100
            ("Unterdorf", 2, 1, 1, 0, 4.0, 2, 100.0),
        ]
        r = zeile(con, "SELECT * EXCLUDE (kanton, stand) FROM gold_kanton")
        assert {k: float(w) if k.startswith("pct_") or k == "pflege_index" else w for k, w in r.items()} == {
            "gemeinden": 2,
            "wohngebaeude": 5,
            "mit_angabe": 5,
            "aktuell_5j": 2,                # Sonde 2023, Fernwaerme 2024
            "aktuell_15j": 3,               # dazu Gas 2020
            "aus_vz2000": 2,
            "fossil": 3,
            "waermepumpe": 1,
            "kandidaten": 2,
            "median_alter_jahre": 6.0,      # 2, 3, [6], 25, 25 - nicht das Mittel aus 25 und 4
            "aktualisiert_12m": 0,
            "pct_vollstaendig": 100.0,
            "pct_aktuell_5j": 40.0,
            "pct_aktuell_15j": 60.0,
            "pct_vz2000": 40.0,
            "pct_ohne_vz2000": 60.0,
            "pct_fossil": 60.0,
            "pct_waermepumpe": 20.0,
            "pct_kandidaten": 40.0,
            "pct_bewegung_12m": 0.0,
            "pflege_index": 73.3,           # (100 + 60 + 60) / 3
        }
    finally:
        con.close()


# --------------------------------------------------------------------------- Zeitreihe

def test_zeitreihe_findet_genau_die_eingebauten_aenderungen(register):
    r = zeile(register, f"""
        SELECT gebaeude_verglichen, zugaenge, abgaenge, traeger_geaendert, quelle_geaendert,
               datum_geaendert, datum_geaendert_wohnen
        FROM v_gold_veraenderung
        WHERE kanton = 'AI' AND stand_alt = DATE '{STAND_ALT}' AND stand_neu = DATE '{STAND_NEU}'""")
    assert r == {
        "gebaeude_verglichen": 12,
        # Ein Zugang darf nicht in einer NULL-Gruppe verschwinden: Genau das tat die erste
        # Fassung der View, weil Kanton und Stand nur von der linken Seite des FULL JOIN kamen.
        "zugaenge": 1,
        "abgaenge": 1,
        "traeger_geaendert": 2,        # zwei Oelheizungen wurden zu Erdwaermesonden
        "quelle_geaendert": 2,
        "datum_geaendert": 3,          # dieselben zwei, dazu ein Gaskessel mit neuem Datum
        "datum_geaendert_wohnen": 3,
    }


def test_zeitreihe_meldet_fuer_einen_ruhigen_kanton_keine_bewegung(register):
    r = zeile(register, """
        SELECT gebaeude_verglichen, zugaenge, abgaenge, traeger_geaendert, datum_geaendert, pct_bewegt
        FROM v_gold_veraenderung WHERE kanton = 'ZG'""")
    assert r["gebaeude_verglichen"] == 6
    assert (r["zugaenge"], r["abgaenge"], r["traeger_geaendert"], r["datum_geaendert"]) == (0, 0, 0, 0)
    assert float(r["pct_bewegt"]) == 0.0


def test_ohne_vorgaenger_gibt_es_keinen_vergleich(register):
    # Der aelteste Stand hat keinen Vorgaenger und darf keine Zeile erzeugen.
    assert register.execute(
        "SELECT count(*) FROM v_gold_veraenderung WHERE stand_alt IS NULL").fetchone()[0] == 0


# --------------------------------------------------------------------------- Einstieg

def test_ein_einzelner_kanton_und_ein_einzelner_stand_reichen(tmp_path, monkeypatch):
    """Wer das Projekt ausprobiert, laedt zuerst einen Kanton: `python src/ingest.py AI`.

    Dann liegt genau eine Snapshot-Datei vor. In dieser Lage brach der Adress-Schritt mit
    einem internen DuckDB-Fehler ab, und die Zeitreihe hat noch nichts zu vergleichen.
    """
    baue_register(tmp_path)
    shutil.rmtree(tmp_path / "snapshots" / "gwr" / f"snapshot_date={STAND_ALT}")
    shutil.rmtree(tmp_path / "snapshots" / "gwr" / f"snapshot_date={STAND_NEU}" / "kanton=ZG")
    datenverzeichnis(monkeypatch, tmp_path)

    con = pipeline.run("ch")
    try:
        assert con.execute("SELECT count(*) FROM silver_gebaeude_ch").fetchone()[0] == 12
        assert con.execute("SELECT count(*) FROM silver_adresse_ch").fetchone()[0] == 4
        assert con.execute("SELECT count(*) FROM gold_kanton").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM v_gold_veraenderung").fetchone()[0] == 0
    finally:
        con.close()
