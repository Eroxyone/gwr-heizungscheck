"""Fuehrt die SQL-Schritte in der richtigen Reihenfolge aus.

Zwei Straenge:
  CH  - schweizweit, Basis sind die Parquet-Snapshots. Braucht nur den Ingest.
  ZH  - Zuerich im Detail, zusaetzlich Baugesuche und Solaranlagen. Braucht build_db.py.

    python src/pipeline.py          # beides, ZH nur wenn die Bronze-Tabellen da sind
    python src/pipeline.py ch       # nur den schweizweiten Strang
    python src/pipeline.py zh       # nur den Zuercher Strang
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import duckdb

import config

SCHRITTE_CH = ["silver_ch.sql", "silver_adressen.sql", "gold.sql",
               "test4_ch.sql"]
# Braucht zusaetzlich den Amtsblatt-Abzug und die Adress-Snapshots. Fehlt eines von
# beiden, wird der Schritt uebersprungen statt die ganze Pipeline abzubrechen - der
# Abzug laeuft Stunden, und der Rest der Auswertung haengt nicht daran.
SCHRITTE_CH_BAUGESUCHE = ["silver_baugesuche_ch.sql"]
SCHRITTE_ZH = [
    "silver.sql", "silver_baugesuche.sql", "silver_llm.sql", "match.sql",
    "test1.sql", "test2.sql", "test3.sql", "test4.sql", "test5.sql",
    "zuordnung_anlagen.sql",
    # Der Genfer Feuerungskataster muss vor dem Verdachts-Layer stehen: Ein aktiver
    # Oel- oder Gaskessel am selben Gebaeude ist ein Gegenbeleg und nimmt den Fall
    # aus der Liste, statt ihn nachtraeglich zu kommentieren.
    "gegenbeleg_ge.sql", "groundtruth_ge.sql", "gegenbeleg_zg.sql",
    # Die Labelsaetze muessen vor dem Verdachts-Layer stehen: Sie liefern die Messung,
    # aus der dessen Gewichte stammen. Danach laesst sich die Rangfolge gegen sie
    # pruefen - aber nur ueber v_gold_score, nie ueber v_gold_verdacht.
    "groundtruth_zg.sql",
    "gold_verdacht.sql",
    "precision_ge.sql",
    # Muss nach gold_verdacht.sql stehen: misst dessen Belege gegen beide Labelsaetze.
    "belegwirkung.sql",
]


def connect(schreibend: bool = True) -> duckdb.DuckDBPyConnection:
    """Verbindung zur Datenbank.

    DuckDB erlaubt nur einen schreibenden Prozess. Wer bloss auswertet oder exportiert,
    soll deshalb lesend oeffnen - sonst blockieren sich ein laufender Pipelinelauf und
    ein Berichtslauf gegenseitig, und zwar mit einer Fehlermeldung, die nach einem
    kaputten Projekt aussieht statt nach zwei gleichzeitigen Zugriffen.
    """
    config.DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DB), read_only=not schreibend)
    con.execute("INSTALL spatial; LOAD spatial; SET enable_progress_bar=false;")
    return con


def datenpfade(sql: str) -> str:
    """Loest die relativen Datenpfade ('data/...') gegen das Datenverzeichnis auf."""
    return sql.replace("'data/", f"'{config.DATA.as_posix()}/")


def hat(con: duckdb.DuckDBPyConnection, *tabellen: str) -> bool:
    """Gibt es alle diese Tabellen oder Sichten? Der Zuercher Strang und die Belegdaten
    sind optional; wer nur den schweizweiten Strang rechnet, hat sie nicht."""
    da = {t for (t,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()}
    return set(tabellen) <= da


_OPTIONAL = re.compile(r"^[ \t]*-- @optional (data/\S+)\n(.*?)^[ \t]*-- @ende\n", re.S | re.M)
_ROHDATEI = re.compile(r"'(data/raw/[^'*]+)'")


def ohne_fehlende_quellen(sql: str) -> tuple[str, list[str]]:
    """Laesst die als entbehrlich markierten Bloecke aus, deren Rohdatei fehlt.

    Ein Block steht zwischen "-- @optional data/raw/..." und "-- @ende". Gibt das
    bereinigte SQL und die Namen der fehlenden Dateien zurueck.
    """
    fehlend: list[str] = []

    def ersetze(m: re.Match) -> str:
        if (config.DATA / m.group(1).removeprefix("data/")).exists():
            return m.group(0)
        fehlend.append(Path(m.group(1)).name)
        return ""

    return _OPTIONAL.sub(ersetze, sql), fehlend


def fehlende_rohdateien(sql: str) -> list[str]:
    """Rohdateien, die das SQL liest, die aber nicht vorliegen."""
    return sorted({pfad for pfad in _ROHDATEI.findall(sql)
                   if not (config.DATA / pfad.removeprefix("data/")).exists()})


def _sql(datei: str) -> str:
    """Liest eine SQL-Datei, laesst entbehrliche Bloecke ohne Rohdatei aus und loest die
    relativen Datenpfade gegen das Datenverzeichnis auf."""
    text, fehlend = ohne_fehlende_quellen((config.SQL / datei).read_text(encoding="utf-8"))
    if fehlend:
        print(f"\n   ({datei}: ohne {', '.join(fehlend)} - Rohdatei fehlt)")
    if (pflicht := fehlende_rohdateien(text)):
        raise FileNotFoundError(
            f"{datei} braucht Rohdateien, die nicht vorliegen: {', '.join(pflicht)}\n"
            "Zuerst:  python src/download.py")
    return datenpfade(text)


def _llm_datei_sicherstellen() -> None:
    """silver_llm.sql liest ein JSONL, das erst nach einem Extraktionslauf existiert.
    Fehlt es, legen wir eine leere Datei an - die Kaskade faellt dann auf die reine
    Stichwortregel zurueck, statt die ganze Pipeline scheitern zu lassen."""
    ziel = config.PROCESSED / "llm_extraktion.jsonl"
    if not ziel.exists():
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text('{"text": null, "llm": {}}\n', encoding="utf-8")


def _bronze_zh_vorhanden(con: duckdb.DuckDBPyConnection) -> bool:
    noetig = {"bronze_gwr_gebaeude", "bronze_gwr_eingang", "bronze_baugesuche",
              "bronze_baugesuche_geo", "bronze_epa"}
    da = {t for (t,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()}
    return noetig <= da


def _kodes_sicherstellen(con: duckdb.DuckDBPyConnection) -> None:
    """Die Codeliste liegt nach dem Ingest unter data/raw/. Ohne sie laeuft der Silver-Layer nicht."""
    vorhanden = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name='bronze_gwr_kodes'"
    ).fetchone()[0]
    if vorhanden:
        return
    for kandidat in (config.RAW / "kodes_codes_codici.csv",
                     config.RAW / "gwr_zh" / "kodes_codes_codici.csv"):
        if kandidat.exists():
            con.execute(
                f"""CREATE OR REPLACE TABLE bronze_gwr_kodes AS
                    SELECT * FROM read_csv('{kandidat.as_posix()}', delim='\t',
                        header=true, all_varchar=true, encoding='utf-8')"""
            )
            return
    raise FileNotFoundError("kodes_codes_codici.csv fehlt - zuerst python src/ingest.py laufen lassen")


def _solar_ch_bereit() -> str | None:
    """Test 4 schweizweit braucht beide BFE-Abzuege: den vollstaendigen mit Koordinaten
    und den kleineren mit EGID-Spalte."""
    fehlt = [p.name for p in (
        config.RAW / "epa" / "ElectricityProductionPlant.csv",
        config.RAW / "epa_egid" / "ElectricityProductionPlant.csv") if not p.exists()]
    return f"BFE-Anlagendaten fehlen ({', '.join(fehlt)})" if fehlt else None


def _baugesuche_ch_bereit() -> str | None:
    """Gibt den Grund zurueck, warum der schweizweite Baugesuch-Schritt nicht laufen kann,
    oder None, wenn alles da ist."""
    if not (config.RAW / "baugesuche_ch.jsonl").exists():
        return "data/raw/baugesuche_ch.jsonl fehlt (python src/ingest_baugesuche.py)"
    if not any((config.SNAPSHOTS / "gwr_adresse").glob("**/*.parquet")):
        return "Adress-Snapshots fehlen (python src/ingest.py)"
    return None


def run(strang: str = "alle", con: duckdb.DuckDBPyConnection | None = None):
    if strang not in ("alle", "ch", "zh"):
        raise ValueError(f"Unbekannter Strang '{strang}': erlaubt sind alle, ch, zh")
    con = con or connect()
    _kodes_sicherstellen(con)
    _llm_datei_sicherstellen()

    schritte: list[str] = []
    if strang in ("alle", "ch"):
        schritte += SCHRITTE_CH
        if (grund := _solar_ch_bereit()):
            print(f"   (Test 4 CH uebersprungen: {grund})")
            schritte = [x for x in schritte if x != "test4_ch.sql"]
        if (grund := _baugesuche_ch_bereit()):
            print(f"   (Baugesuche CH uebersprungen: {grund})")
        else:
            schritte += SCHRITTE_CH_BAUGESUCHE
    if strang in ("alle", "zh"):
        if _bronze_zh_vorhanden(con):
            schritte += SCHRITTE_ZH
        elif strang == "zh":
            raise RuntimeError("Bronze-Tabellen fuer ZH fehlen - zuerst python src/build_db.py")
        else:
            print("   (ZH-Strang uebersprungen, Bronze-Tabellen fehlen)")

    for schritt in schritte:
        start = time.time()
        print(f"-> {schritt}", end="", flush=True)
        con.execute(_sql(schritt))
        print(f"  {time.time() - start:5.1f}s")
    return con


if __name__ == "__main__":
    strang = sys.argv[1].lower() if len(sys.argv) > 1 else "alle"
    if strang not in ("alle", "ch", "zh"):
        raise SystemExit(f"Unbekannter Strang '{strang}'. Aufruf: python src/pipeline.py [alle|ch|zh]")
    verbindung = run(strang)
    zeilen = verbindung.execute("""
        SELECT 'Gebaeude CH' AS was, count(*) AS n FROM silver_gebaeude_ch
        UNION ALL SELECT 'davon Wohngebaeude', count(*) FROM silver_gebaeude_ch WHERE ist_wohngebaeude
        UNION ALL SELECT 'Gemeinden', count(*) FROM gold_gemeinde
        UNION ALL SELECT 'Kantone', count(*) FROM gold_kanton
    """).fetchall()
    for was, n in zeilen:
        print(f"   {was:22s} {n:>10,}".replace(",", "'"))
    verbindung.close()
    print("fertig")
