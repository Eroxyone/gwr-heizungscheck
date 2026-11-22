"""Exportiert die Gold-Kennzahlen als kompaktes JSON fuer das Dashboard.

Spaltenorientiert und mit Kurznamen, damit die Datei klein bleibt und ohne
Nachladen in eine einzelne HTML-Seite passt.
"""
from __future__ import annotations

import json

import pandas as pd

import config
import pipeline

ZIEL = config.REPORTS / "dashboard_data.json"

KANTON_FELDER = [
    "kanton", "note", "pflege_index", "pflegemuster", "gemeinden", "wohngebaeude",
    "pct_vollstaendig", "pct_aktuell_15j", "pct_vz2000", "median_alter_jahre",
    "pct_fossil", "pct_waermepumpe", "pct_kandidaten", "kandidaten",
    "pct_groesstes_datum", "aktive_tage_24m", "pct_bewegung_12m", "stand",
]
GEMEINDE_FELDER = [
    "kanton", "bfs_nr", "gemeinde", "note", "pflege_index", "pflegemuster",
    "wohngebaeude", "pct_vz2000", "median_alter_jahre", "pct_fossil",
    "pct_waermepumpe", "pct_kandidaten", "kandidaten", "pct_aktuell_15j",
]


# Belege je Kanton. Die Felder kommen aus verschiedenen Tests, deshalb einzeln
# zusammengesetzt statt aus einer Sicht - und jede Quelle einzeln abgesichert, weil
# Teile der Pipeline an Daten haengen, die Stunden brauchen.
BELEG_FELDER = ["kanton", "anlagen", "anlagen_datiert", "widerspruch_anlage",
                "verdacht_solar", "baugesuche_heizung", "stufe"]


def _optional(con, sql: str, tabelle: str) -> dict:
    """Liefert {kanton: wert} oder ein leeres Mapping, wenn die Tabelle fehlt."""
    da = con.execute("""SELECT count(*) FROM information_schema.tables
                        WHERE table_name = ?""", [tabelle]).fetchone()[0]
    return dict(con.execute(sql).fetchall()) if da else {}


def _belege(con) -> list[list]:
    anlagen = _optional(con, """SELECT kanton, count(*) FROM silver_waermenutzung
                                GROUP BY 1""", "silver_waermenutzung")
    datiert = _optional(con, """SELECT kanton, count(datum_bewilligung)
                                FROM silver_waermenutzung GROUP BY 1""",
                        "silver_waermenutzung")
    wid = _optional(con, "SELECT kanton, count(*) FROM v_test5 GROUP BY 1", "v_test5")
    pv = _optional(con, """SELECT kanton, count(DISTINCT egid) FROM v_test4_ch
                           GROUP BY 1""", "match_solar_ch")
    bg = _optional(con, """SELECT kanton, count(*) FROM silver_baugesuche_ch
                           WHERE ist_heizungsereignis AND ist_erstpublikation
                           GROUP BY 1""", "silver_baugesuche_ch")
    zeilen = []
    for kt in config.KANTONE:
        a, d, b = anlagen.get(kt, 0), datiert.get(kt, 0), bg.get(kt, 0)
        stufe = 3 if (b and d) else 2 if (d or b) else 1 if a else 0
        zeilen.append([kt, a, d, wid.get(kt, 0), pv.get(kt, 0), b, stufe])
    return zeilen


def _records(df: pd.DataFrame) -> list[list]:
    """Spaltenorientierte Ausgabe: Werteliste je Zeile, Spaltennamen separat."""
    return df.where(pd.notna(df), None).values.tolist()


def main() -> None:
    con = pipeline.connect()

    kantone = con.execute(f"""
        SELECT {", ".join(KANTON_FELDER)} FROM v_gold_kanton ORDER BY pflege_index DESC
    """).df()
    gemeinden = con.execute(f"""
        SELECT {", ".join(GEMEINDE_FELDER)} FROM v_gold_gemeinde ORDER BY pflege_index DESC
    """).df()
    quellen = con.execute("""
        SELECT kanton, quelle_code, quelle_txt, gebaeude, pct
        FROM gold_quellenmix WHERE pct >= 1 ORDER BY kanton, pct DESC
    """).df()
    alter = con.execute("""
        SELECT kanton, altersklasse, gebaeude, pct FROM gold_altersprofil ORDER BY kanton, altersklasse
    """).df()
    schweiz = con.execute("""
        SELECT count(*)                                                   AS wohngebaeude,
               sum(hat_angabe::INT)                                       AS mit_angabe,
               sum(ist_fossil::INT)                                       AS fossil,
               sum((energie_klasse='waermepumpe')::INT)                   AS waermepumpe,
               sum(quelle_vz2000::INT)                                    AS aus_vz2000,
               sum((ist_fossil AND (quelle_vz2000 OR quelle_datum IS NULL
                    OR quelle_datum < stand - INTERVAL 15 YEAR))::INT)    AS kandidaten,
               median(alter_jahre)                                        AS median_alter_jahre,
               max(stand)                                                 AS stand
        FROM v_gold_basis
    """).df()

    for spalte in ("stand",):
        if spalte in kantone:
            kantone[spalte] = kantone[spalte].astype(str)
    schweiz["stand"] = schweiz["stand"].astype(str)

    daten = {
        "erzeugt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "schweiz": schweiz.iloc[0].to_dict(),
        "kantonNamen": config.KANTONE,
        "grossregion": config.GROSSREGION,
        "kantonFelder": KANTON_FELDER,
        "kantone": _records(kantone),
        "gemeindeFelder": GEMEINDE_FELDER,
        "gemeinden": _records(gemeinden),
        "quellen": _records(quellen),
        "alter": _records(alter),
        "belegFelder": BELEG_FELDER,
        "belege": _belege(con),
    }

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    # Als JS-Datei, damit das Dashboard sie ohne fetch laden kann. ensure_ascii, damit
    # Umlaute unabhaengig davon ankommen, welches Encoding der Server mitschickt.
    ascii_json = json.dumps(daten, ensure_ascii=True, separators=(",", ":"))
    (ZIEL.parent / "dashboard_daten.js").write_text(
        f"window.GWR_DATEN={ascii_json};", encoding="ascii")
    con.close()
    print(f"{ZIEL}  {ZIEL.stat().st_size / 1024:.0f} KB")
    print(f"  {len(kantone)} Kantone, {len(gemeinden)} Gemeinden, "
          f"{len(quellen)} Quellenzeilen, {len(alter)} Alterszeilen, "
          f"{len(daten['belege'])} Belegzeilen")


if __name__ == "__main__":
    main()
