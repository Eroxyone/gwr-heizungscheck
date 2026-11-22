"""Kleine, reine Funktionen: Formatierung der Berichte, Anonymisierung, Pruefwerkzeug."""
from __future__ import annotations

import re

import duckdb
import pandas as pd

import config
import fmt
import pipeline
from checks import Pruefer
from ingest_baugesuche import _anonymisieren, _koordinate_aus_text

# --------------------------------------------------------------------------- fmt

def test_dezimalkomma_nur_in_zahlen():
    assert fmt.de("Anteil 12.5 % bei 3.25 Punkten") == "Anteil 12,5 % bei 3,25 Punkten"


def test_datum_modellname_und_url_bleiben_unangetastet():
    assert fmt.de("Stand 14.09.2026") == "Stand 14.09.2026"
    assert fmt.de("Modell `qwen2.5:7b` erreicht 98.7 %") == "Modell `qwen2.5:7b` erreicht 98,7 %"
    assert fmt.de("https://example.org/v1.2/daten") == "https://example.org/v1.2/daten"
    assert fmt.de("siehe Abschnitt 3.2") == "siehe Abschnitt 3.2"


def test_tausendertrennung_mit_apostroph():
    assert fmt.tsd(3170000) == "3'170'000"
    assert fmt.tsd(999) == "999"


def test_tabelle_setzt_ganzzahlen_ohne_nachkommastelle_und_prozente_mit():
    tabelle = fmt.md(pd.DataFrame({"Kanton": ["ZH"], "Fälle": [2143.0], "% belegt": [6.0]}))
    kopf, _, werte = tabelle.splitlines()
    assert [z.strip() for z in kopf.strip("|").split("|")] == ["Kanton", "Fälle", "% belegt"]
    assert [z.strip() for z in werte.strip("|").split("|")] == ["ZH", "2143", "6,0"]


# --------------------------------------------------------------------------- Anonymisierung

def test_vorspann_mit_personen_faellt_weg():
    # Namen und Adressen erfunden; der Aufbau entspricht einer Schwyzer Publikation.
    text = ("Zone: W2. Planverfasser: Muster Architektur AG, Beispielweg 1, 6430 Schwyz. "
            "Grundeigentümer: Hans Muster, Beispielweg 3, 6430 Schwyz. "
            "Bauobjekt: Ersatz Ölheizung durch Erdsonden-Wärmepumpe")
    assert _anonymisieren(text) == "Ersatz Ölheizung durch Erdsonden-Wärmepumpe"


def test_namensfeld_im_fliesstext_wird_ersetzt():
    bereinigt = _anonymisieren("Einbau Wärmepumpe. Bauherrschaft: Hans Muster, Beispielweg 3. Parzelle 123")
    assert "Hans Muster" not in bereinigt
    assert "Bauherrschaft: [entfernt]" in bereinigt
    assert bereinigt.startswith("Einbau Wärmepumpe.")


def test_namensfeld_endet_nicht_am_semikolon():
    # Schwyz schreibt "Grundeigentuemer: Firma; Herr + Frau Vorname Name, Strasse, Ort." Die
    # erste Fassung schnitt am Semikolon: Die Firma verschwand, die Privatpersonen blieben
    # mitsamt Wohnadresse stehen (108 Publikationen). Namen und Adresse hier erfunden.
    text = ("Umbau Wohnhaus. Grundeigentümer: Muster GmbH; Herr + Frau Hans Muster, Beispielweg 5, "
            "8849 Alpthal. Einbau einer Luft-Wasser-Wärmepumpe")
    assert _anonymisieren(text) == (
        "Umbau Wohnhaus. Grundeigentümer: [entfernt]. Einbau einer Luft-Wasser-Wärmepumpe")


def test_leerer_text_bleibt_leer():
    assert _anonymisieren(None) is None
    assert _anonymisieren("") is None


def test_lv95_koordinate_aus_freitext():
    assert _koordinate_aus_text("Koordinaten 2 700 535/1 221 177") == "2700535/1221177"
    assert _koordinate_aus_text("Koordinaten 2'700'535, 1'221'177") == "2700535/1221177"
    assert _koordinate_aus_text("Parzelle 2700") is None


# --------------------------------------------------------------------------- Pruefwerkzeug

def test_pruefer_haelt_bestandene_und_gefallene_behauptungen_fest():
    con = duckdb.connect()
    con.execute("CREATE TABLE t AS SELECT * FROM range(5) r(i)")
    p = Pruefer(con)
    p.gleich("fuenf Zeilen", "SELECT count(*) FROM t", 5)
    p.null("keine negativen Werte", "SELECT * FROM t WHERE i < 0")
    p.null("keine Werte ueber drei", "SELECT * FROM t WHERE i > 3")
    p.hoechstens("bekannte Ausreisser", "SELECT * FROM t WHERE i > 3", 1)
    p.zwischen("Mittelwert", "SELECT avg(i) FROM t", 1.5, 2.5)
    p.zwischen("leeres Ergebnis faellt", "SELECT avg(i) FROM t WHERE i > 10", 0, 1)
    assert [e.bestanden for e in p.ergebnisse] == [True, True, False, True, True, False]
    assert p.hat("t") and not p.hat("gibt_es_nicht")


# --------------------------------------------------------------------------- Aufbau

def test_jeder_pipeline_schritt_hat_eine_sql_datei_und_umgekehrt():
    schritte = set(pipeline.SCHRITTE_CH + pipeline.SCHRITTE_CH_BAUGESUCHE + pipeline.SCHRITTE_ZH)
    dateien = {p.name for p in config.SQL.glob("*.sql")}
    assert schritte == dateien


def test_datenpfade_in_sql_zeigen_ins_datenverzeichnis(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA", tmp_path)
    sql = pipeline._sql("silver_ch.sql")
    assert f"'{tmp_path.as_posix()}/snapshots/gwr/**/*.parquet'" in sql
    assert "'data/" not in sql


# --------------------------------------------------------------------------- entbehrliche Quellen

BEISPIEL = """CREATE TABLE t AS
WITH alle AS (
    SELECT 1 AS x FROM st_read('data/raw/pflicht.json')
    -- ------------------------------------------------------- Kanton A
    -- @optional data/raw/a.json
    UNION ALL BY NAME
    SELECT 2 AS x FROM st_read('data/raw/a.json')
    -- @ende
    -- ------------------------------------------------------- Kanton B
    -- @optional data/raw/b.json
    UNION ALL BY NAME
    SELECT 3 AS x FROM st_read('data/raw/b.json')
    -- @ende
)
SELECT * FROM alle;
"""


def test_block_ohne_rohdatei_wird_ausgelassen(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA", tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "a.json").write_text("{}", encoding="utf-8")

    sql, fehlend = pipeline.ohne_fehlende_quellen(BEISPIEL)
    assert fehlend == ["b.json"]
    assert "a.json" in sql and "b.json" not in sql
    assert sql.count("UNION ALL BY NAME") == 1
    # Was nicht als entbehrlich markiert ist, wird gemeldet statt verschwiegen
    assert pipeline.fehlende_rohdateien(sql) == ["data/raw/pflicht.json"]


def test_vollstaendige_daten_lassen_das_sql_unveraendert(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA", tmp_path)
    (tmp_path / "raw").mkdir()
    for name in ("pflicht.json", "a.json", "b.json"):
        (tmp_path / "raw" / name).write_text("{}", encoding="utf-8")
    assert pipeline.ohne_fehlende_quellen(BEISPIEL) == (BEISPIEL, [])
    assert pipeline.fehlende_rohdateien(BEISPIEL) == []


def test_anlagenregister_sind_einzeln_entbehrlich(monkeypatch, tmp_path):
    # Ohne jede Rohdatei bleibt vom Anlagen-Schritt genau der Zuercher Kern uebrig:
    # vier Layer des AWEL, alle uebrigen Kantone fallen sauber heraus.
    monkeypatch.setattr(config, "DATA", tmp_path)
    roh = (config.SQL / "test5.sql").read_text(encoding="utf-8")
    assert roh.count("-- @optional data/raw/") == roh.count("    -- @ende\n") == 14

    sql, fehlend = pipeline.ohne_fehlende_quellen(roh)
    assert len(fehlend) == 14
    assert "@optional" not in sql.split("WITH alle AS (", 1)[1]
    assert pipeline.fehlende_rohdateien(sql) == [
        "data/raw/waermenutzung_zh/erdregister.json",
        "data/raw/waermenutzung_zh/erdwaermesonden.json",
        "data/raw/waermenutzung_zh/grundwasserfassung-waermenutzung.json",
        "data/raw/waermenutzung_zh/quellfassung-waermenutzung.json",
    ]


def test_auffangsicht_fuer_fehlende_amtsblatt_baugesuche_traegt_alle_spalten():
    # Der Abzug aus dem Amtsblattportal ist optional und dauert Stunden. Fehlt er, legt
    # gold_verdacht.sql eine leere Auffangsicht an. Sie muss jede Spalte fuehren, die der
    # Verdachts-Layer daraus liest - sonst scheitert der Schritt genau bei denen, die das
    # Projekt zum ersten Mal rechnen.
    sql = (config.SQL / "gold_verdacht.sql").read_text(encoding="utf-8")
    sicht = re.search(r"CREATE VIEW IF NOT EXISTS v_test3_ch_gebaeude AS.*?;", sql, re.S).group(0)
    abfrage = re.search(r"UNION ALL\s+(SELECT egid, pub_datum.*?FROM v_test3_ch_gebaeude)", sql, re.S).group(1)

    con = duckdb.connect()
    con.execute(sicht)
    assert con.execute(abfrage).fetchall() == []

    echte_sicht = (config.SQL / "silver_baugesuche_ch.sql").read_text(encoding="utf-8")
    echte_spalten = re.search(
        r"CREATE OR REPLACE VIEW v_test3_ch_gebaeude AS\s+SELECT(.*?)\nFROM v_test3_ch t", echte_sicht, re.S).group(1)
    for spalte in (s[0] for s in con.execute("DESCRIBE v_test3_ch_gebaeude").fetchall()):
        assert re.search(rf"\b{spalte}\b", echte_spalten), f"{spalte} fehlt in der echten Sicht"
