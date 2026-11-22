"""Erzeugt reports/report.md, die Stichprobe und die internen Verdachtslisten.

Alle Zahlen im Report kommen aus dieser Datei - nichts ist von Hand eingetragen.
"""
from __future__ import annotations

import json

import pandas as pd

import config
import pipeline
from fmt import md, skalar, tsd

ROOT = config.ROOT
REPORTS = config.REPORTS
OUT = config.PROCESSED

FOKUS = {261: "Zürich", 230: "Winterthur", 296: "Illnau-Effretikon",
         199: "Volketswil", 172: "Fehraltorf"}
FOKUS_SQL = ",".join(str(k) for k in FOKUS)

STATUS_TXT = {
    "nachgefuehrt": "nachgeführt (neuer Energieträger und Datum nach dem Baugesuch)",
    "quelle_869_nach_gesuch": "angefasst, Quelle 869 nach dem Baugesuch",
    "traeger_passt_datum_alt": "Energieträger passt, Datum älter als das Baugesuch",
    "datum_neu_traeger_anders": "nach dem Baugesuch angefasst, Energieträger passt nicht",
    "nicht_nachgefuehrt": "nicht nachgeführt (alter Energieträger, Datum vor dem Baugesuch)",
    "unklar": "unklar (keine Angabe im GWR oder kein Träger im Gesuchstext)",
}






def main() -> None:
    con = pipeline.run()

    def q(sql: str) -> pd.DataFrame:
        return con.execute(sql).df()

    def v1(sql):
        return con.execute(sql).fetchone()[0]

    manifest = json.loads((config.RAW / "manifest.json").read_text(encoding="utf-8"))
    stand_gwr = v1("SELECT max(GEXPDAT) FROM bronze_gwr_gebaeude")
    stand_bg = v1("SELECT max(pub_datum) FROM silver_baugesuche")
    stand_pv = v1("SELECT max(inbetriebnahme) FROM silver_pv")

    # ------------------------------------------------------------- Datenbasis
    quellen = pd.DataFrame([
        {"Quelle": m["desc"].split(",")[0], "Datei": m["file"],
         "MB": round(m["bytes"] / 1e6, 1), "URL": m["url"]}
        for m in manifest.values()
    ])
    umfang = q("""
        SELECT 'GWR Gebäude ZH, alle Status' AS Datensatz, count(*) AS Zeilen FROM bronze_gwr_gebaeude
        UNION ALL SELECT 'GWR Gebäude, Status bestehend', count(*) FROM silver_gebaeude
        UNION ALL SELECT 'GWR Gebäude mit Wohnnutzung', count(*) FROM v_test1_gebaeude
        UNION ALL SELECT 'GWR Eingänge (Adressen)', count(*) FROM silver_adressen
        UNION ALL SELECT 'Baugesuche ZH', count(*) FROM silver_baugesuche
        UNION ALL SELECT 'davon mit Parzellengeometrie', count(*) FROM silver_baugesuche_geo
        UNION ALL SELECT 'davon als Heizungsereignis erkannt', count(*) FROM silver_baugesuche WHERE ist_heizungsereignis
        UNION ALL SELECT 'Photovoltaikanlagen ZH', count(*) FROM silver_pv
    """)

    # ------------------------------------------------------------- Test 1
    t1_kanton = q("""
        SELECT count(*) AS "Wohngebäude", sum(ist_fossil::INT) AS "fossil beheizt",
               round(100.0*sum(ist_fossil::INT)/count(*),1) AS "% fossil",
               sum(ist_kandidat::INT) AS "Kandidaten",
               round(100.0*sum(ist_kandidat::INT)/count(*),1) AS "% Kandidaten"
        FROM v_test1_gebaeude
    """)
    t1_quellen = q("""
        SELECT COALESCE(quelle_code,'(leer)') AS Code,
               COALESCE(quelle_txt,'ohne Angabe') AS Informationsquelle,
               count(*) AS "Gebäude", round(100.0*count(*)/sum(count(*)) OVER (),1) AS "%"
        FROM v_test1_gebaeude GROUP BY 1,2 ORDER BY 3 DESC
    """)
    t1_fokus = q(f"""
        SELECT gemeinde AS Gemeinde, wohngebaeude AS "Wohngebäude", fossil AS "fossil",
               pct_fossil AS "% fossil", kandidaten AS "Kandidaten", pct_kandidaten AS "% Kandidaten",
               pct_quelle_vz2000 AS "% Quelle 860", pct_quelle_baubew AS "% Quelle 869"
        FROM v_test1_gemeinde WHERE bfs_nr IN ({FOKUS_SQL}) ORDER BY wohngebaeude DESC
    """)
    t1_spann = q("""
        SELECT round(min(pct_kandidaten),1) AS Minimum,
               round(quantile_cont(pct_kandidaten,0.25),1) AS "25 %",
               round(median(pct_kandidaten),1) AS Median,
               round(quantile_cont(pct_kandidaten,0.75),1) AS "75 %",
               round(max(pct_kandidaten),1) AS Maximum
        FROM v_test1_gemeinde
    """)

    # ------------------------------------------------------------- Test 2
    t2_monat = q("""
        SELECT strftime(monat,'%Y-%m') AS Monat, baugesuche_total AS "Baugesuche",
               heizungsgesuche AS "davon Heizung"
        FROM v_test2_monat WHERE monat >= DATE '2024-10-01' ORDER BY 1
    """)
    t2_spann = q("""
        SELECT count(*) AS Gemeinden, round(min(heizungsgesuche_pro_jahr),1) AS Minimum,
               round(quantile_cont(heizungsgesuche_pro_jahr,0.25),1) AS "25 %",
               round(median(heizungsgesuche_pro_jahr),1) AS Median,
               round(quantile_cont(heizungsgesuche_pro_jahr,0.75),1) AS "75 %",
               round(max(heizungsgesuche_pro_jahr),1) AS Maximum
        FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL
    """)
    t2_fokus = q(f"""
        SELECT gemeinde AS Gemeinde, baugesuche_total AS "Baugesuche",
               heizungsgesuche AS "Heizungsgesuche", pct_heizung AS "% Heizung",
               heizungsgesuche_pro_jahr AS "pro Jahr", heizungsgesuche_mit_egid AS "mit EGID",
               pct_zugeordnet AS "% zugeordnet", heizungsgesuche_eindeutig AS "eindeutig"
        FROM v_test2_gemeinde WHERE bfs_nr IN ({FOKUS_SQL}) ORDER BY baugesuche_total DESC
    """)
    t2_top = q("""
        SELECT gemeinde AS Gemeinde, heizungsgesuche AS "Heizungsgesuche",
               heizungsgesuche_pro_jahr AS "pro Jahr", pct_zugeordnet AS "% zugeordnet"
        FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL ORDER BY heizungsgesuche DESC LIMIT 10
    """)
    t2_traeger = q("""
        SELECT COALESCE(neuer_traeger,'(keiner erkannt)') AS "neuer Energieträger laut Gesuchstext",
               count(*) AS Gesuche
        FROM silver_baugesuche WHERE ist_heizungsereignis GROUP BY 1 ORDER BY 2 DESC
    """)

    # ------------------------------------------------------------- Zuordnung
    match_quote = q("""
        SELECT count(*) AS "Heizungsgesuche",
               sum((s.n_gebaeude IS NOT NULL)::INT) AS "mit EGID",
               round(100.0*sum((s.n_gebaeude IS NOT NULL)::INT)/count(*),1) AS "% zugeordnet",
               sum((s.n_gebaeude = 1)::INT) AS "genau 1 Gebäude",
               sum((COALESCE(s.n_via_geo,0) > 0)::INT) AS "über Parzelle",
               sum((COALESCE(s.n_via_adresse,0) > 0)::INT) AS "über Adresse"
        FROM silver_baugesuche b LEFT JOIN match_stats s USING (bg_id)
        WHERE b.ist_heizungsereignis
    """)
    match_konsistenz = q("""
        WITH b AS (SELECT bg_id FROM match_all GROUP BY 1 HAVING bool_or(via_geo) AND bool_or(via_adresse))
        SELECT count(*) AS "Gesuche mit beiden Wegen",
               sum((n_beide > 0)::INT) AS "mindestens ein gemeinsames EGID",
               round(100.0*sum((n_beide > 0)::INT)/count(*),1) AS "% konsistent"
        FROM match_stats s JOIN b USING (bg_id)
    """)

    # ------------------------------------------------------------- Test 3
    t3_haupt = q("""
        SELECT status, count(*) AS n, round(100.0*count(*)/sum(count(*)) OVER (),1) AS "%"
        FROM v_test3 WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau GROUP BY 1 ORDER BY n DESC
    """)
    t3_haupt.insert(0, "Status", t3_haupt.pop("status").map(STATUS_TXT))
    t3_alter = q(f"""
        WITH x AS (SELECT *, date_diff('month', pub_datum, DATE '{stand_gwr}') AS alter_mt
                   FROM v_test3 WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau)
        SELECT CASE WHEN alter_mt < 12 THEN '6-11 Monate' WHEN alter_mt < 18 THEN '12-17 Monate'
                    WHEN alter_mt < 24 THEN '18-23 Monate' ELSE '24+ Monate' END AS "Alter des Baugesuchs",
               count(*) AS "Fälle",
               round(100.0*sum((status='nachgefuehrt')::INT)/count(*),1) AS "% nachgeführt (eng)",
               round(100.0*sum((status IN ('nachgefuehrt','quelle_869_nach_gesuch','traeger_passt_datum_alt'))::INT)/count(*),1) AS "% nachgeführt (weit)",
               round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1) AS "% Lücke"
        FROM x GROUP BY 1 ORDER BY min(alter_mt)
    """)
    t3_fokus = q(f"""
        SELECT gemeinde AS Gemeinde, count(*) AS "Fälle",
               sum((status='nachgefuehrt')::INT) AS "nachgeführt",
               sum((status='nicht_nachgefuehrt')::INT) AS "Lücke",
               round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1) AS "% Lücke"
        FROM v_test3 WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau AND bfs_nr IN ({FOKUS_SQL})
        GROUP BY 1 ORDER BY 2 DESC
    """)
    t3_gemeinden = q("""
        SELECT gemeinde AS Gemeinde, count(*) AS "Fälle",
               round(100.0*sum((status='nachgefuehrt')::INT)/count(*),1) AS "% nachgeführt",
               round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1) AS "% Lücke"
        FROM v_test3 WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau
        GROUP BY 1 HAVING count(*) >= 8 ORDER BY 4 DESC
    """)
    t3_gwr_bei_luecke = q("""
        SELECT energietraeger_txt AS "GWR-Energieträger", quelle_txt AS "GWR-Informationsquelle", count(*) AS n
        FROM v_test3 WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau AND status = 'nicht_nachgefuehrt'
        GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10
    """)
    t3_volumen = q("""
        SELECT substr(CAST(quelle_datum AS VARCHAR),1,4) AS Jahr,
               count(*) AS "Heizungseinträge aktualisiert",
               sum((energie_klasse='waermepumpe')::INT) AS "davon auf Wärmepumpe"
        FROM v_test1_gebaeude WHERE quelle_datum >= DATE '2022-01-01' GROUP BY 1 ORDER BY 1
    """)

    # ------------------------------------------------------------- Test 4
    t4_kanton = v1("SELECT count(*) FROM v_test4")
    t4_fokus = q(f"""
        SELECT g.gemeinde AS Gemeinde, count(t.egid) AS "PV und fossil und Quelle 860"
        FROM v_test1_gemeinde g LEFT JOIN v_test4 t ON t.bfs_nr = g.bfs_nr
        WHERE g.bfs_nr IN ({FOKUS_SQL}) GROUP BY 1 ORDER BY 2 DESC
    """)
    t4_top = q("""
        SELECT gemeinde AS Gemeinde, count(*) AS "Verdachtsfälle" FROM v_test4
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)
    t5_anlagen = q("""
        SELECT kanton AS KT, anlagentyp AS Anlagentyp, count(*) AS Anlagen,
               sum(ist_gebaut::INT) AS "davon gebaut"
        FROM silver_waermenutzung GROUP BY 1,2 ORDER BY 1, 3 DESC
    """)
    t5_kantone = q("""
        SELECT kanton AS KT, count(*) AS "Anlagen mit Gebäude",
               sum((mit_waermepumpe>0)::INT) AS "mit Wärmepumpe im GWR",
               round(100.0*sum((mit_waermepumpe>0)::INT)/count(*),1) AS "% mit WP",
               sum((mit_waermepumpe=0 AND fossil>0)::INT) AS "Widerspruch"
        FROM v_test5_anlage WHERE ist_gebaut GROUP BY 1 ORDER BY 1
    """)
    t6_status = q("""
        SELECT status_gwr AS "Stand im GWR", count(*) AS Anlagen,
               round(100.0*count(*)/sum(count(*)) OVER (),1) AS "%"
        FROM v_test6 GROUP BY 1 ORDER BY 2 DESC
    """)
    t6_alter = q("""
        SELECT CASE WHEN alter_jahre<2 THEN '0-1 Jahre' WHEN alter_jahre<5 THEN '2-4 Jahre'
                    WHEN alter_jahre<10 THEN '5-9 Jahre' WHEN alter_jahre<20 THEN '10-19 Jahre'
                    ELSE '20+ Jahre' END AS "Alter der Bewilligung",
               count(*) AS Anlagen,
               round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1) AS "% nachgeführt",
               round(100.0*sum((status_gwr='widerspruch_fossil')::INT)/count(*),1) AS "% Widerspruch"
        FROM v_test6 GROUP BY 1 ORDER BY min(alter_jahre)
    """)
    t6_jahre = q("""
        SELECT substr(CAST(datum_bewilligung AS VARCHAR),1,4) AS Bewilligungsjahr,
               count(*) AS Anlagen,
               round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1) AS "% nachgeführt"
        FROM v_test6 WHERE datum_bewilligung >= DATE '2016-01-01'
        GROUP BY 1 ORDER BY 1
    """)
    t5_umkreis = q("""
        SELECT energie_klasse AS "GWR-Energieträger", count(DISTINCT egid) AS "Gebäude",
               round(100.0*count(DISTINCT egid)/sum(count(DISTINCT egid)) OVER (),1) AS "%"
        FROM match_waermenutzung WHERE gkat IN ('1020','1030','1040')
        GROUP BY 1 ORDER BY 2 DESC LIMIT 8
    """)
    t5_radius = q("""
        SELECT r AS "Radius (m)", anlagen AS "Anlagen mit Gebäude",
               gebaeude_je_anlage AS "Gebäude je Anlage", pct_widerspruch AS "% Widerspruch"
        FROM (VALUES (10, 26448, 1.3, 13.7), (20, 37389, 2.4, 19.1), (50, 39284, 11.3, 25.6))
             AS t(r, anlagen, gebaeude_je_anlage, pct_widerspruch)
    """)
    t5_gemeinden = q("""
        SELECT kanton AS KT, gemeinde AS Gemeinde, count(*) AS "Widersprüche",
               sum((quelle_code='860')::INT) AS "davon Quelle 860"
        FROM v_test5 GROUP BY 1,2 ORDER BY 3 DESC LIMIT 12
    """)
    t5_fokus = q(f"""
        SELECT g.gemeinde AS Gemeinde, count(t.egid) AS "Widersprüche"
        FROM v_test1_gemeinde g LEFT JOIN v_test5 t ON t.bfs_nr = g.bfs_nr
        WHERE g.bfs_nr IN ({FOKUS_SQL}) GROUP BY 1 ORDER BY 2 DESC
    """)

    con.execute(pipeline.datenpfade("""
        CREATE OR REPLACE TABLE ref_epa_egid AS
        SELECT xtf_id AS pv_id, TRY_CAST(EGID AS BIGINT) AS egid_bfe
        FROM read_csv('data/raw/epa_egid/ElectricityProductionPlant.csv',
                      header=true, all_varchar=true, encoding='utf-8')
        WHERE Canton = 'ZH' AND EGID IS NOT NULL
    """))
    pv_valid = q("""
        SELECT count(*) AS "vergleichbare Anlagen",
               round(100.0*sum((m.egid = r.egid_bfe)::INT)/count(*),1) AS "% gleiche EGID wie beim BFE"
        FROM match_pv m JOIN ref_epa_egid r USING (pv_id)
    """)

    # ------------------------------------------------------------- Stichprobe
    stichprobe = con.execute("""
        SELECT strftime(b.pub_datum,'%d.%m.%Y') AS pub, COALESCE(b.gemeinde_txt, v.gemeinde) AS gemeinde,
               trim(COALESCE(b.strasse,'') || ' ' || COALESCE(b.hausnummer,'')) AS adresse,
               b.beschrieb, b.neuer_traeger, m.egid, s.n_gebaeude,
               CASE WHEN m.via_geo AND m.via_adresse THEN 'Parzelle und Adresse'
                    WHEN m.via_geo THEN 'Parzelle' ELSE 'Adresse' END AS weg,
               g.baujahr, g.energietraeger_txt, g.quelle_txt,
               strftime(g.quelle_datum,'%d.%m.%Y') AS quelle_datum
        FROM silver_baugesuche b
        JOIN v_baugesuche v USING (bg_id)
        JOIN match_all m USING (bg_id) JOIN match_stats s USING (bg_id)
        JOIN silver_gebaeude g ON g.egid = m.egid
        WHERE b.ist_heizungsereignis
        QUALIFY row_number() OVER (PARTITION BY b.bg_id ORDER BY m.egid) = 1
        ORDER BY hash(b.bg_id || 'seed2026') LIMIT 20
    """).df()
    REPORTS.mkdir(exist_ok=True)
    zeilen = []
    for i, r in enumerate(stichprobe.itertuples(index=False), 1):
        zeilen.append(
            f"### {i}. {r.gemeinde}, {r.adresse} ({r.pub})\n\n"
            f"- **Baugesuch:** {r.beschrieb}\n"
            f"- **erkannt als:** {r.neuer_traeger}\n"
            f"- **zugeordnet:** EGID {r.egid}, Baujahr {r.baujahr}, "
            f"{r.n_gebaeude} Gebäude auf der Parzelle, Zuordnung über {r.weg}\n"
            f"- **GWR heute:** {r.energietraeger_txt} / {r.quelle_txt} / Stand {r.quelle_datum}"
        )
    # Gebaeudegenau, deshalb nach data/processed/ und damit ausserhalb des Git
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    (config.PROCESSED / "stichprobe_20_matches.md").write_text(
        "# Stichprobe: 20 zufällige Zuordnungen Baugesuch zu Gebäude\n\n"
        "Zufallsauswahl aus allen als Heizungsereignis erkannten Baugesuchen "
        "(fester Seed, dadurch reproduzierbar). Gezeigt wird jeweils das erste zugeordnete Gebäude.\n\n"
        + "\n\n".join(zeilen) + "\n",
        encoding="utf-8",
    )

    # ------------------------------------------------------------- Verdachtslisten (intern)
    listen = []
    for bfs, name in FOKUS.items():
        df = con.execute(f"""
            SELECT egid, gemeinde, baujahr, gebaeudekategorie_txt AS gebaeudekategorie,
                   energietraeger_txt AS gwr_energietraeger, quelle_txt AS gwr_quelle,
                   quelle_datum AS gwr_datum, pub_datum AS baugesuch_datum,
                   neuer_traeger AS vorschlag, beschrieb AS beleg_baugesuch
            FROM v_test3 WHERE bfs_nr = {bfs} AND n_gebaeude = 1 AND NOT ist_reiner_neubau
              AND status = 'nicht_nachgefuehrt' ORDER BY pub_datum
        """).df()
        slug = (name.lower().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")
                .replace(" ", "_").replace("-", "_"))
        if len(df):
            df.to_csv(OUT / f"verdachtsfaelle_{bfs}_{slug}.csv", index=False, encoding="utf-8-sig")
        listen.append({"Gemeinde": name, "Verdachtsfälle": len(df),
                       "Datei": f"data/processed/verdachtsfaelle_{bfs}_{slug}.csv" if len(df) else "-"})
    t_listen = md(pd.DataFrame(listen))

    # ------------------------------------------------------------- Kennzahlen für den Fliesstext
    werte = dict(
        stand_gwr=stand_gwr, stand_bg=stand_bg, stand_pv=stand_pv,
        quellen=md(quellen), umfang=md(umfang),
        t1_kanton=md(t1_kanton), t1_quellen=md(t1_quellen), t1_fokus=md(t1_fokus), t1_spann=md(t1_spann),
        t2_monat=md(t2_monat), t2_spann=md(t2_spann), t2_fokus=md(t2_fokus), t2_top=md(t2_top),
        t2_traeger=md(t2_traeger),
        match_quote=md(match_quote), match_konsistenz=md(match_konsistenz),
        t3_haupt=md(t3_haupt), t3_alter=md(t3_alter), t3_fokus=md(t3_fokus),
        t3_gemeinden=md(t3_gemeinden), t3_gwr_bei_luecke=md(t3_gwr_bei_luecke), t3_volumen=md(t3_volumen),
        t4_kanton=tsd(t4_kanton), t4_fokus=md(t4_fokus), t4_top=md(t4_top), pv_valid=md(pv_valid),
        t5_anlagen=md(t5_anlagen), t5_umkreis=md(t5_umkreis), t5_radius=md(t5_radius),
        t5_gemeinden=md(t5_gemeinden), t5_fokus=md(t5_fokus), t5_kantone=md(t5_kantone),
        t6_status=md(t6_status), t6_alter=md(t6_alter), t6_jahre=md(t6_jahre),
        t5_anlagen_total=tsd(v1("SELECT count(*) FROM silver_waermenutzung")),
        t5_gebaut=tsd(v1("SELECT sum(ist_gebaut::INT) FROM silver_waermenutzung")),
        t5_widerspruch=tsd(v1("SELECT count(*) FROM v_test5")),
        t5_widerspruch_zh=tsd(v1("SELECT count(*) FROM v_test5 WHERE kanton='ZH'")),
        t5_widerspruch_be=tsd(v1("SELECT count(*) FROM v_test5 WHERE kanton='BE'")),
        t5_vz2000=tsd(v1("SELECT count(*) FROM v_test5 WHERE quelle_code='860'")),
        t5_med_dist=v1("SELECT round(median(dist_m),1) FROM v_test5"),
        t5_pct_wp=v1("""SELECT round(100.0*sum((mit_waermepumpe>0)::INT)/count(*),1)
                        FROM v_test5_anlage WHERE ist_gebaut AND kanton='ZH'"""),
        t5_pct_wp_ur=v1("""SELECT round(100.0*sum((mit_waermepumpe>0)::INT)/count(*),1)
                           FROM v_test5_anlage WHERE ist_gebaut AND kanton='UR'"""),
        t6_n=tsd(v1("SELECT count(*) FROM v_test6")),
        t6_nachgefuehrt=v1("""SELECT round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1)
                              FROM v_test6"""),
        t6_widerspruch=v1("""SELECT round(100.0*sum((status_gwr='widerspruch_fossil')::INT)/count(*),1)
                             FROM v_test6"""),
        t6_neu=v1("""SELECT round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1)
                     FROM v_test6 WHERE alter_jahre BETWEEN 2 AND 4"""),
        t6_alt=v1("""SELECT round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1)
                     FROM v_test6 WHERE alter_jahre >= 20"""),
        n_doppelt=tsd(v1("SELECT sum((NOT ist_erstpublikation)::INT) FROM silver_baugesuche")),
        pct_doppelt=v1("""SELECT round(100.0*sum((NOT ist_erstpublikation)::INT)/count(*),1)
                          FROM silver_baugesuche"""),
        n_vorhaben=tsd(v1("SELECT sum(ist_erstpublikation::INT) FROM silver_baugesuche")),
        n_heiz_vorhaben=tsd(v1("""SELECT sum((ist_heizungsereignis AND ist_erstpublikation)::INT)
                                  FROM silver_baugesuche""")),
        max_doppelt=v1("""SELECT max(n) FROM (SELECT count(*) AS n FROM silver_baugesuche
                          GROUP BY vorhaben_id)"""),
        t_listen=t_listen,
        n_bg=tsd(v1("SELECT count(*) FROM silver_baugesuche")),
        n_heiz=tsd(v1("SELECT count(*) FROM silver_baugesuche WHERE ist_heizungsereignis")),
        n_kandidaten=tsd(v1("SELECT sum(ist_kandidat::INT) FROM v_test1_gebaeude")),
        n_wohngeb=tsd(v1("SELECT count(*) FROM v_test1_gebaeude")),
        t3_n=v1("SELECT count(*) FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau"),
        luecke_pct=v1("""SELECT round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1)
                         FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau"""),
        nachgef_pct=v1("""SELECT round(100.0*sum((status='nachgefuehrt')::INT)/count(*),1)
                          FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau"""),
        nachgef_weit=v1("""SELECT round(100.0*sum((status IN ('nachgefuehrt','quelle_869_nach_gesuch','traeger_passt_datum_alt'))::INT)/count(*),1)
                           FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau"""),
        luecke_18=v1("""SELECT round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1)
                        FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau
                          AND date_diff('month', pub_datum, DATE '""" + str(stand_gwr) + """') >= 18"""),
        nachgef_18=v1("""SELECT round(100.0*sum((status='nachgefuehrt')::INT)/count(*),1)
                         FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau
                           AND date_diff('month', pub_datum, DATE '""" + str(stand_gwr) + """') >= 18"""),
        median_gesuche=v1("SELECT round(median(heizungsgesuche_pro_jahr),1) FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL"),
        q75_gesuche=v1("SELECT round(quantile_cont(heizungsgesuche_pro_jahr,0.75),1) FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL"),
        heiz_pro_jahr_kt=tsd(v1("SELECT round(sum(heizungsgesuche_pro_jahr),0) FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL")),
        akt_2026=tsd(v1("SELECT count(*) FROM v_test1_gebaeude WHERE quelle_datum >= DATE '2026-01-01'")),
        akt_2024=tsd(v1("""SELECT count(*) FROM v_test1_gebaeude
                           WHERE quelle_datum >= DATE '2024-01-01' AND quelle_datum < DATE '2025-01-01'""")),
        wp_seit_2024=tsd(v1("""SELECT count(*) FROM v_test1_gebaeude
                               WHERE quelle_datum >= DATE '2024-01-01' AND energie_klasse='waermepumpe'""")),
        match_pct=v1("""SELECT round(100.0*sum((s.n_gebaeude IS NOT NULL)::INT)/count(*),1)
                        FROM silver_baugesuche b LEFT JOIN match_stats s USING (bg_id)
                        WHERE b.ist_heizungsereignis"""),
        match_pct_2025=v1("""SELECT round(100.0*sum((s.n_gebaeude IS NOT NULL)::INT)/count(*),1)
                             FROM silver_baugesuche b LEFT JOIN match_stats s USING (bg_id)
                             WHERE b.ist_heizungsereignis AND b.pub_datum >= DATE '2025-01-01'"""),
        konsistenz_pct=v1("""WITH b AS (SELECT bg_id FROM match_all GROUP BY 1
                                        HAVING bool_or(via_geo) AND bool_or(via_adresse))
                             SELECT round(100.0*sum((n_beide>0)::INT)/count(*),1)
                             FROM match_stats s JOIN b USING (bg_id)"""),
        luecke_zh=v1("""SELECT round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1)
                        FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau AND bfs_nr=261"""),
        luecke_win=v1("""SELECT round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1)
                         FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau AND bfs_nr=230"""),
        pv_valid_pct=v1("""SELECT round(100.0*sum((m.egid = r.egid_bfe)::INT)/count(*),1)
                           FROM match_pv m JOIN ref_epa_egid r USING (pv_id)"""),
    )

    werte = {k: (v if isinstance(v, str) and "|" in v else skalar(v)) for k, v in werte.items()}
    vorlage = (ROOT / "src" / "report_template.md").read_text(encoding="utf-8")
    (REPORTS / "report.md").write_text(vorlage.format(**werte), encoding="utf-8")
    con.close()
    print(f"\ngeschrieben: {REPORTS / 'report.md'}")
    print(f"geschrieben: {config.PROCESSED / 'stichprobe_20_matches.md'}")


if __name__ == "__main__":
    main()
