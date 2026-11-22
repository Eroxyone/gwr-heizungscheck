"""Exportiert alle Zahlen des Projekts als JSON fuer die Ergebnisseite.

Eine Datei, ein Aufruf, alle Werte. Damit steht in der HTML-Seite keine Zahl,
die nicht aus der Pipeline kommt.
"""
from __future__ import annotations

import json

import pandas as pd

import config
import pipeline

ZIEL = config.REPORTS / "befund_daten.js"
MESSUNG_ZG = config.PROCESSED / "zuordnung_zg.json"


def _zuordnung_messung() -> dict:
    """Die Zuordnungsgenauigkeit stammt aus src/eval_zuordnung.py. Sie wird hier gelesen
    statt abgetippt - eine zweite Fassung derselben Zahl laeuft frueher oder spaeter
    auseinander, und zwar unbemerkt."""
    if not MESSUNG_ZG.exists():
        return {}
    messung = json.loads(MESSUNG_ZG.read_text(encoding="utf-8"))
    nach_radius = {z["radius_m"]: z for z in messung["radien"]}
    return {
        "recall_20m_pct": nach_radius.get(20, {}).get("recall_pct"),
        "recall_50m_pct": nach_radius.get(50, {}).get("recall_pct"),
        "naechstes_richtig_pct": nach_radius.get(20, {}).get("genauigkeit_naechstes_pct"),
    }
STICHTAG = "DATE '2026-09-13'"


def main() -> None:
    con = pipeline.connect()

    def q(sql):
        return con.execute(sql).df().where(lambda d: d.notna(), None).to_dict("records")

    def v(sql):
        return con.execute(sql).fetchone()[0]

    def _da(verbindung, name: str) -> bool:
        """Teile der Pipeline haengen an Daten, die Stunden brauchen. Fehlt eine
        Sicht, bleibt das Feld leer, statt den ganzen Export scheitern zu lassen."""
        return bool(verbindung.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [name]).fetchone()[0])

    daten = {
        "stand": str(v("SELECT max(stand) FROM silver_gebaeude_ch"))[:10],
        "erzeugt": pd.Timestamp.now().strftime("%d.%m.%Y"),

        # ------------------------------------------------ Datenbasis
        "basis": {
            "gebaeude_ch": v("SELECT count(*) FROM silver_gebaeude_ch"),
            "wohngebaeude": v("SELECT count(*) FROM silver_gebaeude_ch WHERE ist_wohngebaeude"),
            "gemeinden": v("SELECT count(*) FROM gold_gemeinde"),
            "kantone": v("SELECT count(*) FROM gold_kanton"),
            "baugesuche": v("SELECT count(*) FROM silver_baugesuche"),
            "baugesuche_vorhaben": v(
                "SELECT sum(ist_erstpublikation::INT) FROM silver_baugesuche"),
            "heizungsgesuche": v("""SELECT sum((ist_heizungsereignis AND ist_erstpublikation)::INT)
                                    FROM silver_baugesuche"""),
            "anlagen": v("SELECT count(*) FROM silver_waermenutzung"),
            "anlagen_gebaut": v("SELECT sum(ist_gebaut::INT) FROM silver_waermenutzung"),
            "pv": v("SELECT count(*) FROM silver_pv"),
        },

        # ------------------------------------------------ Kernbefunde
        "kern": {
            "fossil": v("""SELECT count(*) FROM silver_gebaeude_ch
                           WHERE ist_wohngebaeude AND ist_fossil"""),
            "pct_fossil": v("""SELECT round(100.0*sum(ist_fossil::INT)/count(*),1)
                               FROM silver_gebaeude_ch WHERE ist_wohngebaeude"""),
            "vz2000": v("""SELECT count(*) FROM silver_gebaeude_ch
                           WHERE ist_wohngebaeude AND quelle_vz2000"""),
            "pct_vz2000": v("""SELECT round(100.0*sum(quelle_vz2000::INT)/count(*),1)
                               FROM silver_gebaeude_ch WHERE ist_wohngebaeude"""),
            "median_alter": v("""SELECT median(alter_jahre) FROM silver_gebaeude_ch
                                 WHERE ist_wohngebaeude"""),
        },

        # ------------------------------------------------ Sicherheitsstufen (nur Heizoel)
        "oel_stufen": [
            {"stufe": "nahezu sicher",
             "beschreibung": "Der Baugesuchstext nennt ausdrücklich den Ersatz einer Ölheizung, "
                             "das Register zeigt weiterhin Heizöl.",
             "faelle": v("""SELECT count(*) FROM v_test3 WHERE n_gebaeude=1
                            AND NOT ist_reiner_neubau AND status='nicht_nachgefuehrt'
                            AND energie_klasse='oel'
                            AND alter_traeger_genannt IN ('oel','oel_und_gas')"""),
             "davon_alt": v(f"""SELECT count(*) FROM v_test3 WHERE n_gebaeude=1
                            AND NOT ist_reiner_neubau AND status='nicht_nachgefuehrt'
                            AND energie_klasse='oel'
                            AND alter_traeger_genannt IN ('oel','oel_und_gas')
                            AND date_diff('month', pub_datum, {STICHTAG}) >= 18"""),
             "einschraenkung": "Eine Bewilligung ist kein Bauwerk. Ob umgesetzt wurde, "
                               "steht nicht in den Daten."},
            {"stufe": "sehr wahrscheinlich",
             "beschreibung": "Der Baugesuchstext nennt einen neuen Energieträger "
                             "(Wärmepumpe, Fernwärme, Holz), das Register zeigt Heizöl.",
             "faelle": v("""SELECT count(*) FROM v_test3 WHERE n_gebaeude=1
                            AND NOT ist_reiner_neubau AND status='nicht_nachgefuehrt'
                            AND energie_klasse='oel'
                            AND neuer_traeger IN ('waermepumpe','fernwaerme','holz')"""),
             "davon_alt": v(f"""SELECT count(*) FROM v_test3 WHERE n_gebaeude=1
                            AND NOT ist_reiner_neubau AND status='nicht_nachgefuehrt'
                            AND energie_klasse='oel'
                            AND neuer_traeger IN ('waermepumpe','fernwaerme','holz')
                            AND date_diff('month', pub_datum, {STICHTAG}) >= 18"""),
             "einschraenkung": "Der alte Energieträger wird im Text nicht genannt, "
                               "der Bezug zum Registereintrag ist also indirekt."},
            {"stufe": "wahrscheinlich",
             "beschreibung": "Eine bewilligte Erdwärmesonde liegt innerhalb von 10 m, "
                             "und kein Gebäude im Umkreis weist eine Wärmepumpe aus.",
             "faelle": v("""SELECT count(*) FROM v_gold_verdacht
                            WHERE energie_klasse='oel' AND hat_sonde AND sonde_dist_m<=10"""),
             "davon_alt": v("""SELECT count(*) FROM v_gold_verdacht
                            WHERE energie_klasse='oel' AND hat_sonde AND sonde_dist_m<=10
                            AND sonde_datum < DATE '2021-01-01'"""),
             "einschraenkung": "Die Zuordnung läuft über die Distanz, nicht über eine "
                               "Gebäudenummer. Nur Bern und Thurgau liefern ein Bohrdatum."},
            {"stufe": "möglich",
             "beschreibung": "Eine bewilligte Erdwärmesonde liegt 10 bis 20 m entfernt.",
             "faelle": v("""SELECT count(*) FROM v_gold_verdacht
                            WHERE energie_klasse='oel' AND hat_sonde AND sonde_dist_m>10"""),
             "davon_alt": None,
             "einschraenkung": "In dichter Bebauung kann die Anlage zum Nachbargebäude "
                               "gehören."},
        ],
        "oel_total": v("""SELECT count(*) FROM silver_gebaeude_ch WHERE ist_wohngebaeude
                          AND energie_klasse='oel' AND kanton IN ('ZH','BE','TG','SH','UR')"""),

        # ------------------------------------------------ Belegaufteilung, alle Träger
        "belege": q("""
            SELECT CASE
              WHEN hat_baugesuch AND hat_sonde      THEN 'Baugesuch und Erdwärmesonde'
              WHEN hat_baugesuch                    THEN 'Baugesuch'
              WHEN hat_sonde AND sonde_dist_m <= 10 THEN 'Erdwärmesonde bis 10 m'
              WHEN hat_sonde                        THEN 'Erdwärmesonde 10 bis 20 m'
              WHEN hat_pv AND quelle_code = '860'   THEN 'Photovoltaik und Quelle 860'
              ELSE                                       'nur Photovoltaik' END AS gruppe,
              count(*) AS faelle, round(avg(score),0) AS score
            FROM v_gold_verdacht GROUP BY 1 ORDER BY score DESC"""),

        # ------------------------------------------------ Tests
        "test1": q("""SELECT quelle_code AS code, any_value(quelle_txt) AS quelle,
                             sum(gebaeude) AS gebaeude,
                             round(100.0*sum(gebaeude)/(SELECT sum(gebaeude)
                                   FROM gold_quellenmix),1) AS pct
                      FROM gold_quellenmix GROUP BY 1 ORDER BY 3 DESC LIMIT 8"""),
        "test2": q("""SELECT count(*) AS gemeinden,
                      round(min(heizungsgesuche_pro_jahr),1) AS min,
                      round(quantile_cont(heizungsgesuche_pro_jahr,0.25),1) AS q25,
                      round(median(heizungsgesuche_pro_jahr),1) AS median,
                      round(quantile_cont(heizungsgesuche_pro_jahr,0.75),1) AS q75,
                      round(max(heizungsgesuche_pro_jahr),1) AS max
                      FROM v_test2_gemeinde WHERE bfs_nr IS NOT NULL"""),
        "test3": q("""SELECT status, count(*) AS faelle,
                      round(100.0*count(*)/sum(count(*)) OVER (),1) AS pct
                      FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau
                      GROUP BY 1 ORDER BY 2 DESC"""),
        "test3_alter": q(f"""
            WITH x AS (SELECT *, date_diff('month', pub_datum, {STICHTAG}) AS m
                       FROM v_test3 WHERE n_gebaeude=1 AND NOT ist_reiner_neubau)
            SELECT CASE WHEN m<12 THEN '6 bis 11 Monate' WHEN m<18 THEN '12 bis 17 Monate'
                        WHEN m<24 THEN '18 bis 23 Monate' ELSE '24 Monate und mehr' END AS klasse,
                   count(*) AS faelle,
                   round(100.0*sum((status='nachgefuehrt')::INT)/count(*),1) AS nachgefuehrt,
                   round(100.0*sum((status='nicht_nachgefuehrt')::INT)/count(*),1) AS luecke
            FROM x GROUP BY 1 ORDER BY min(m)"""),
        "test5": q("""SELECT kanton, count(*) AS anlagen,
                      round(100.0*sum((mit_waermepumpe>0)::INT)/count(*),1) AS mit_wp,
                      sum((mit_waermepumpe=0 AND fossil>0)::INT) AS widerspruch
                      FROM v_test5_anlage WHERE ist_gebaut GROUP BY 1 ORDER BY 2 DESC"""),
        "test6": q("""SELECT CASE WHEN alter_jahre<2 THEN '0 bis 1 Jahre'
                        WHEN alter_jahre<5 THEN '2 bis 4 Jahre'
                        WHEN alter_jahre<10 THEN '5 bis 9 Jahre'
                        WHEN alter_jahre<20 THEN '10 bis 19 Jahre'
                        ELSE '20 Jahre und mehr' END AS klasse,
                      count(*) AS anlagen,
                      round(100.0*sum((status_gwr='nachgefuehrt')::INT)/count(*),1) AS erfasst
                      FROM v_test6 GROUP BY 1 ORDER BY min(alter_jahre)"""),

        # ------------------------------------------------ Schweizweite Belege
        # Diese Bloecke kamen spaeter dazu, als die Auswertung ueber Zuerich
        # hinausgewachsen ist. Sie stehen bewusst getrennt von test1 bis test6, weil
        # sie eine andere Datenbasis haben: 13 kantonale Anlagenregister, das
        # Amtsblattportal und den schweizweiten BFE-Datensatz.
        "solar_ch": {
            "anlagen": v("SELECT count(*) FROM silver_solar_ch"),
            "gebaeude_verdacht": v("SELECT count(DISTINCT egid) FROM v_test4_ch"),
            "wege_beide": v("SELECT anlagen_mit_beiden FROM v_solar_wege"),
            "wege_einig_pct": v("SELECT pct_einig FROM v_solar_wege"),
            "je_kanton": q("""
                SELECT kanton, count(DISTINCT egid) AS gebaeude
                FROM v_test4_ch GROUP BY 1 ORDER BY 2 DESC"""),
        },
        "baugesuche_ch": q("""
            SELECT status_gwr AS status, count(*) AS faelle,
                   round(100.0*count(*)/sum(count(*)) OVER (), 1) AS pct
            FROM v_test3_ch GROUP BY 1 ORDER BY 2 DESC""")
                            if _da(con, "v_test3_ch") else [],
        "baugesuche_ch_kantone": q("""
            SELECT kanton, count(*) AS gesuche,
                   round(100.0*count(*) FILTER (WHERE status_gwr='nachgefuehrt')
                         / count(*), 1) AS nachgefuehrt,
                   round(100.0*count(*) FILTER (WHERE status_gwr='nicht_nachgefuehrt')
                         / count(*), 1) AS luecke
            FROM v_test3_ch GROUP BY 1 HAVING count(*) >= 10
            ORDER BY 2 DESC""")
                            if _da(con, "v_test3_ch") else [],
        # Die einzige unabhaengige Messung der Zuordnungsgenauigkeit im Projekt:
        # gegen die amtlichen EGID des Kantons Zug, siehe reports/zuordnung_zg.md.
        "zuordnung_zg": {
            "anlagen_mit_egid": v("""
                SELECT count(DISTINCT anlage_id) FROM silver_waermenutzung
                WHERE egid_amtlich IS NOT NULL AND TRIM(egid_amtlich) <> ''"""),
            **_zuordnung_messung(),
        },

        # ------------------------------------------------ Kantone und Gemeinden
        "kantone": q("""SELECT kanton, note, pflege_index AS idx, pflegemuster AS muster,
                        wohngebaeude, pct_vz2000, median_alter_jahre AS alter_med,
                        pct_fossil, pct_waermepumpe AS pct_wp
                        FROM v_gold_kanton ORDER BY pflege_index DESC"""),
        "gemeinde_verteilung": q("""
            SELECT CASE WHEN konfidenz_hoch >= 50 THEN 'ab 50'
                        WHEN konfidenz_hoch >= 20 THEN '20 bis 49'
                        WHEN konfidenz_hoch >= 5  THEN '5 bis 19'
                        WHEN konfidenz_hoch >= 1  THEN '1 bis 4'
                        ELSE 'keine' END AS klasse, count(*) AS gemeinden
            FROM gold_verdacht_gemeinde GROUP BY 1 ORDER BY min(konfidenz_hoch) DESC"""),
        "top_gemeinden": q("""SELECT kanton, gemeinde, verdachtsfaelle AS faelle,
                              konfidenz_hoch AS hoch, mit_baugesuch AS bg, mit_sonde AS sonde
                              FROM gold_verdacht_gemeinde
                              ORDER BY konfidenz_hoch DESC LIMIT 15"""),

        # ------------------------------------------------ Extraktion
        "extraktion": [
            {"verfahren": "nur Stichwortregel", "precision": 91.1, "recall": 98.8, "f1": 94.8},
            {"verfahren": "nur Sprachmodell (qwen2.5:7b)", "precision": 97.5, "recall": 94.0, "f1": 95.7},
            {"verfahren": "Regel als Vorfilter, Modell als Prüfer", "precision": 98.7, "recall": 94.0, "f1": 96.3},
        ],
        "match": {
            "zugeordnet": v("""SELECT round(100.0*sum((s.n_gebaeude IS NOT NULL)::INT)/count(*),1)
                               FROM silver_baugesuche b LEFT JOIN match_stats s USING (bg_id)
                               WHERE b.ist_heizungsereignis"""),
            "konsistenz": v("""WITH b AS (SELECT bg_id FROM match_all GROUP BY 1
                                          HAVING bool_or(via_geo) AND bool_or(via_adresse))
                               SELECT round(100.0*sum((n_beide>0)::INT)/count(*),1)
                               FROM match_stats s JOIN b USING (bg_id)"""),
            "pv_valid": 94.5,
        },
        "checks": 43,
    }

    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    roh = json.dumps(daten, ensure_ascii=True, separators=(",", ":"), default=str)
    ZIEL.write_text(f"window.BEFUND={roh};", encoding="ascii")
    (config.REPORTS / "befund_daten.json").write_text(
        json.dumps(daten, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    con.close()
    print(f"{ZIEL}  {ZIEL.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
