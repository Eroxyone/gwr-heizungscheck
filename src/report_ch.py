"""Erzeugt reports/kantonsvergleich.md aus dem Gold-Layer.

Alle Zahlen kommen aus der Pipeline, nichts ist von Hand eingetragen.
"""
from __future__ import annotations

import config
import pipeline
from fmt import de, md, tsd

ZIEL = config.REPORTS / "kantonsvergleich.md"


def main() -> None:
    con = pipeline.run("ch")

    def q(sql):
        return con.execute(sql).df()

    def v1(sql):
        return con.execute(sql).fetchone()[0]

    # Der Kantonsvergleich stellt den Registerkennzahlen die Belege gegenueber. Die kommen
    # aus den Anlagenregistern und den Solaranlagen, also aus dem vollen Lauf.
    if not pipeline.hat(con, "silver_waermenutzung", "v_test4_ch", "v_solar_wege"):
        con.close()
        raise SystemExit(
            "Der Kantonsvergleich braucht die Belegdaten, die der schweizweite Strang allein "
            "nicht laedt.\nZuerst:  python src/download.py && python src/build_db.py && "
            "python src/pipeline.py alle")

    # Test 3 aus dem Zuercher Strang - nur, wenn er gerechnet ist. Die Zahlen standen
    # hier einmal fest im Text (541 Faelle, 39 Prozent) und stammten aus einem aelteren
    # Lauf; report.md nannte fuer denselben Sachverhalt 458 und 40,6 Prozent.
    hat_test3 = bool(v1("""SELECT count(*) FROM information_schema.tables
                           WHERE table_name = 'v_test3'"""))
    if hat_test3:
        t3 = q("""
            SELECT count(*) AS n,
                   round(100.0 * avg((status = 'nicht_nachgefuehrt')::INT)) AS luecke,
                   round(100.0 * avg((status = 'nicht_nachgefuehrt')::INT)
                         FILTER (WHERE alter_monate >= 18))                 AS luecke18
            FROM (SELECT status,
                         date_diff('month', pub_datum,
                                   (SELECT max(pub_datum) FROM silver_baugesuche))
                           AS alter_monate
                  FROM v_test3
                  WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau)""").iloc[0]
        t3_n, t3_luecke, t3_luecke18 = (tsd(int(t3.n)), str(int(t3.luecke)),
                                        str(int(t3.luecke18)))
    else:
        t3_n = t3_luecke = t3_luecke18 = "-"

    ch = q("""
        SELECT count(*) AS wohngebaeude, sum(hat_angabe::INT) AS mit_angabe,
               sum(ist_fossil::INT) AS fossil, sum(quelle_vz2000::INT) AS vz2000,
               sum((energie_klasse='waermepumpe')::INT) AS waermepumpe,
               sum((ist_fossil AND (quelle_vz2000 OR quelle_datum IS NULL
                    OR quelle_datum < stand - INTERVAL 15 YEAR))::INT) AS kandidaten,
               median(alter_jahre) AS median_alter, max(stand) AS stand
        FROM v_gold_basis
    """).iloc[0]

    rang = q("""
        SELECT kanton AS KT, note AS Note, pflege_index AS "Index", pflegemuster AS Pflegemuster,
               wohngebaeude AS "Wohngebäude", pct_vollstaendig AS "% vollständig",
               pct_aktuell_15j AS "% aktuell", pct_vz2000 AS "% VZ 2000",
               median_alter_jahre AS "Alter (J.)", pct_fossil AS "% fossil",
               pct_waermepumpe AS "% WP", pct_kandidaten AS "% Verdacht"
        FROM v_gold_kanton ORDER BY pflege_index DESC
    """)
    muster = q("""
        SELECT pflegemuster AS Pflegemuster, count(*) AS Kantone,
               string_agg(kanton, ' ' ORDER BY pflege_index DESC) AS "welche"
        FROM v_gold_kanton GROUP BY 1 ORDER BY 2 DESC
    """)
    gem_noten = q("""
        SELECT note AS Note, count(*) AS Gemeinden,
               round(100.0*count(*)/sum(count(*)) OVER (),1) AS "% der Gemeinden",
               sum(wohngebaeude) AS "Wohngebäude"
        FROM v_gold_gemeinde GROUP BY 1 ORDER BY 1
    """)
    gem_muster = q("""
        SELECT pflegemuster AS Pflegemuster, count(*) AS Gemeinden,
               sum(wohngebaeude) AS "Wohngebäude", sum(kandidaten) AS "Verdachtsfälle"
        FROM v_gold_gemeinde GROUP BY 1 ORDER BY 2 DESC
    """)
    schlecht = q("""
        SELECT kanton AS KT, gemeinde AS Gemeinde, wohngebaeude AS "Wohngebäude",
               pflege_index AS "Index", pct_vz2000 AS "% VZ 2000",
               median_alter_jahre AS "Alter (J.)", kandidaten AS "Verdachtsfälle"
        FROM v_gold_gemeinde WHERE wohngebaeude >= 500 ORDER BY pflege_index LIMIT 15
    """)
    gut = q("""
        SELECT kanton AS KT, gemeinde AS Gemeinde, wohngebaeude AS "Wohngebäude",
               pflege_index AS "Index", pflegemuster AS Pflegemuster,
               aktive_tage_24m AS "aktive Tage 24 Mt."
        FROM v_gold_gemeinde WHERE wohngebaeude >= 500 AND pflegemuster = 'laufend'
        ORDER BY pflege_index DESC LIMIT 12
    """)
    absolut = q("""
        SELECT kanton AS KT, gemeinde AS Gemeinde, wohngebaeude AS "Wohngebäude",
               kandidaten AS "Verdachtsfälle", pct_kandidaten AS "% Verdacht",
               pflege_index AS "Index"
        FROM v_gold_gemeinde ORDER BY kandidaten DESC LIMIT 15
    """)
    bulk = q("""
        SELECT kanton AS KT, pct_groesstes_datum AS "% am selben Tag",
               verschiedene_daten AS "verschiedene Daten", aktive_tage_24m AS "aktive Tage 24 Mt."
        FROM v_gold_kanton WHERE pflegemuster = 'Sammelimport' ORDER BY 2 DESC
    """)
    quellen_ch = q("""
        SELECT quelle_code AS Code, any_value(quelle_txt) AS Informationsquelle,
               sum(gebaeude) AS "Gebäude",
               round(100.0*sum(gebaeude)/(SELECT sum(gebaeude) FROM gold_quellenmix),1) AS "%"
        FROM gold_quellenmix GROUP BY 1 ORDER BY 3 DESC
    """)

    # Belege je Kanton: Was gibt es ausser dem GWR selbst, um es zu pruefen?
    # v_test5 entsteht im ZH-Strang. Laeuft nur der schweizweite Strang auf einer frischen
    # Datenbank, gibt es die Sicht nicht - dann bleibt die Spalte leer statt zu scheitern.
    hat_test5 = bool(v1("""SELECT count(*) FROM information_schema.tables
                           WHERE table_name = 'v_test5'"""))
    belege = q("""
        WITH anl AS (
            SELECT kanton, count(*) AS anlagen, count(datum_bewilligung) AS datiert
            FROM silver_waermenutzung GROUP BY 1
        ),
        wid AS (
            SELECT * FROM (VALUES (NULL::VARCHAR, 0)) AS t(kanton, widerspruch)
            WHERE FALSE
            UNION ALL SELECT kanton, count(*) FROM {test5} GROUP BY 1
        ),
        pv AS (
            SELECT kanton, count(DISTINCT egid) AS pv_verdacht FROM v_test4_ch GROUP BY 1
        )
        SELECT k.kanton AS KT,
               COALESCE(a.anlagen, 0)     AS "Anlagen",
               COALESCE(a.datiert, 0)     AS "davon datiert",
               COALESCE(w.widerspruch, 0) AS "Widerspruch Anlage",
               COALESCE(p.pv_verdacht, 0) AS "Verdacht Solar"
        FROM v_gold_kanton k
        LEFT JOIN anl a ON a.kanton = k.kanton
        LEFT JOIN wid w ON w.kanton = k.kanton
        LEFT JOIN pv  p ON p.kanton = k.kanton
        ORDER BY 2 DESC, 5 DESC, 1
    """.replace("{test5}", "v_test5" if hat_test5
                 else "(SELECT NULL::VARCHAR AS kanton WHERE FALSE)"))
    solar = q("SELECT * FROM v_solar_wege").iloc[0]

    werte = dict(
        belege=md(belege),
        solar_beide=tsd(int(solar.anlagen_mit_beiden)),
        solar_pct=de(str(solar.pct_einig)),
        stand=str(ch.stand)[:10], wohngeb=tsd(ch.wohngebaeude), fossil=tsd(ch.fossil),
        pct_fossil=de(f"{100*ch.fossil/ch.wohngebaeude:.1f}"),
        vz2000=tsd(ch.vz2000), pct_vz2000=de(f"{100*ch.vz2000/ch.wohngebaeude:.1f}"),
        kandidaten=tsd(ch.kandidaten),
        pct_kandidaten=de(f"{100*ch.kandidaten/ch.wohngebaeude:.1f}"),
        median_alter=de(str(ch.median_alter)),
        wp=tsd(ch.waermepumpe), pct_wp=de(f"{100*ch.waermepumpe/ch.wohngebaeude:.1f}"),
        gemeinden=tsd(v1("SELECT count(*) FROM gold_gemeinde")),
        rang=md(rang), muster=md(muster), gem_noten=md(gem_noten), gem_muster=md(gem_muster),
        schlecht=md(schlecht), gut=md(gut), absolut=md(absolut), bulk=md(bulk),
        quellen_ch=md(quellen_ch),
        best_kt=rang.iloc[0]["KT"], best_idx=de(str(rang.iloc[0]["Index"])),
        schlecht_kt=rang.iloc[-1]["KT"], schlecht_idx=de(str(rang.iloc[-1]["Index"])),
        n_rueckstand=v1("SELECT count(*) FROM v_gold_kanton WHERE pflegemuster='Rueckstand'"),
        n_gem_rueckstand=tsd(v1("SELECT count(*) FROM v_gold_gemeinde WHERE pflegemuster='Rueckstand'")),
        n_gem_de=tsd(v1("SELECT count(*) FROM v_gold_gemeinde WHERE note IN ('D','E')")),
        pct_gem_de=de(str(v1("""SELECT round(100.0*count(*) FILTER (WHERE note IN ('D','E'))
                                / count(*), 1) FROM v_gold_gemeinde"""))),
        t3_n=t3_n, t3_luecke=t3_luecke, t3_luecke18=t3_luecke18,
        zukunft=v1("SELECT count(*) FROM silver_gebaeude_ch WHERE quelle_datum > stand"),
        ohne_datum=tsd(v1("SELECT count(*) FROM silver_gebaeude_ch WHERE quelle_datum IS NULL")),
    )

    vorlage = (config.ROOT / "src" / "report_ch_template.md").read_text(encoding="utf-8")
    ZIEL.write_text(vorlage.format(**werte), encoding="utf-8")
    con.close()
    print(f"geschrieben: {ZIEL}")


if __name__ == "__main__":
    main()
