"""Bronze-Layer in DuckDB laden.

Liest die Rohdateien aus data/raw und legt sie als Tabellen in data/processed/gwr.duckdb ab.
Idempotent: Tabellen werden neu erstellt.
"""
from __future__ import annotations

import duckdb

import config
import pipeline

RAW = config.RAW
DB = config.DB


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    pipeline.lade_spatial(con)

    gwr = RAW / "gwr_zh"
    print("-> bronze_gwr_gebaeude")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_gwr_gebaeude AS
        SELECT * FROM read_csv('{(gwr / "gebaeude_batiment_edificio.csv").as_posix()}',
            delim='\t', header=true, all_varchar=true, encoding='utf-8');
        """
    )
    print("-> bronze_gwr_eingang")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_gwr_eingang AS
        SELECT * FROM read_csv('{(gwr / "eingang_entree_entrata.csv").as_posix()}',
            delim='\t', header=true, all_varchar=true, encoding='utf-8');
        """
    )
    print("-> bronze_gwr_kodes")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_gwr_kodes AS
        SELECT * FROM read_csv('{(gwr / "kodes_codes_codici.csv").as_posix()}',
            delim='\t', header=true, all_varchar=true, encoding='utf-8');
        """
    )
    print("-> bronze_baugesuche")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_baugesuche AS
        SELECT * FROM read_csv('{(RAW / "baugesuche_zh.csv").as_posix()}',
            header=true, all_varchar=true, encoding='utf-8');
        """
    )
    print("-> bronze_baugesuche_geo")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_baugesuche_geo AS
        SELECT * FROM st_read('{(RAW / "baugesuche_zh_geo.gpkg").as_posix()}');
        """
    )
    print("-> bronze_epa")
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bronze_epa AS
        SELECT * FROM read_csv('{(RAW / "epa" / "ElectricityProductionPlant.csv").as_posix()}',
            header=true, all_varchar=true, encoding='utf-8');
        """
    )

    for t, in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY 1"
    ).fetchall():
        n = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        print(f"   {t:28s} {n:>10,} Zeilen")
    con.close()
    print(f"\nDB: {DB}")


if __name__ == "__main__":
    main()
