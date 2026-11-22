"""Silver- und Gold-Layer des schweizweiten Strangs gegen das erfundene Register.

Jede erwartete Zahl laesst sich in tests/conftest.py von Hand nachzaehlen.
"""
from __future__ import annotations

import datetime as dt
import shutil

import config
import pipeline
from conftest import STAND_ALT, STAND_NEU, baue_register


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
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "RAW", tmp_path / "raw")
    monkeypatch.setattr(config, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(config, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(config, "DB", tmp_path / "processed" / "gwr.duckdb")

    con = pipeline.run("ch")
    try:
        assert con.execute("SELECT count(*) FROM silver_gebaeude_ch").fetchone()[0] == 12
        assert con.execute("SELECT count(*) FROM silver_adresse_ch").fetchone()[0] == 4
        assert con.execute("SELECT count(*) FROM gold_kanton").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM v_gold_veraenderung").fetchone()[0] == 0
    finally:
        con.close()
