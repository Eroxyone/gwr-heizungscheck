-- Silver-Layer Schweiz: Gebaeude aus den Snapshots, typisiert und klassifiziert.
-- Quelle sind die Parquet-Snapshots unter data/snapshots/gwr/. Dadurch laeuft dieselbe
-- Logik ueber alle Kantone und ueber alle Staende.

-- Alle Snapshots, hive-partitioniert nach snapshot_date und kanton
CREATE OR REPLACE VIEW bronze_gwr_snapshots AS
SELECT * FROM read_parquet('data/snapshots/gwr/**/*.parquet', hive_partitioning = true);

-- Der jeweils neueste Stand je Kanton. Kantone werden nicht am selben Tag exportiert,
-- deshalb pro Kanton das Maximum, nicht global.
CREATE OR REPLACE VIEW bronze_gwr_aktuell AS
WITH neueste AS (
    SELECT kanton, max(snapshot_date) AS snapshot_date
    FROM bronze_gwr_snapshots GROUP BY 1
)
SELECT s.* FROM bronze_gwr_snapshots s JOIN neueste n USING (kanton, snapshot_date);

CREATE OR REPLACE TABLE silver_gebaeude_ch AS
WITH g AS (
    SELECT
        CAST(EGID AS BIGINT)                       AS egid,
        kanton,
        CAST(GGDENR AS INTEGER)                    AS bfs_nr,
        GGDENAME                                   AS gemeinde,
        TRY_CAST(GKODE AS DOUBLE)                  AS e_lv95,
        TRY_CAST(GKODN AS DOUBLE)                  AS n_lv95,
        TRY_CAST(GBAUJ AS INTEGER)                 AS baujahr,
        TRY_CAST(GAREA AS INTEGER)                 AS flaeche_m2,
        TRY_CAST(GANZWHG AS INTEGER)               AS anzahl_wohnungen,
        GKAT                                       AS gkat,
        GKLAS                                      AS gklas,
        GWAERZH1                                   AS waermeerzeuger_code,
        GENH1                                      AS energietraeger_code,
        GWAERSCEH1                                 AS quelle_code,
        TRY_CAST(GWAERDATH1 AS DATE)               AS quelle_datum,
        GENW1                                      AS ww_energietraeger_code,
        GWAERSCEW1                                 AS ww_quelle_code,
        TRY_CAST(GWAERDATW1 AS DATE)               AS ww_quelle_datum,
        TRY_CAST(snapshot_date AS DATE)            AS stand
    FROM bronze_gwr_aktuell
    WHERE GSTAT = '1004'          -- nur bestehende Gebaeude
)
SELECT
    g.*,
    ke.CODTXTLD AS energietraeger_txt,
    ks.CODTXTLD AS quelle_txt,
    kk.CODTXTLD AS gebaeudekategorie_txt,
    CASE g.energietraeger_code
        WHEN '7500' THEN 'keine'
        WHEN '7501' THEN 'waermepumpe' WHEN '7510' THEN 'waermepumpe'
        WHEN '7511' THEN 'waermepumpe' WHEN '7512' THEN 'waermepumpe'
        WHEN '7513' THEN 'waermepumpe'
        WHEN '7520' THEN 'gas'         WHEN '7530' THEN 'oel'
        WHEN '7540' THEN 'holz'        WHEN '7541' THEN 'holz'
        WHEN '7542' THEN 'holz'        WHEN '7543' THEN 'holz'
        WHEN '7550' THEN 'abwaerme'    WHEN '7560' THEN 'elektro'
        WHEN '7570' THEN 'solarthermie'
        WHEN '7580' THEN 'fernwaerme'  WHEN '7581' THEN 'fernwaerme'
        WHEN '7582' THEN 'fernwaerme'
        WHEN '7598' THEN 'unbestimmt'  WHEN '7599' THEN 'andere'
        ELSE 'ohne_angabe'
    END                                                            AS energie_klasse,
    g.energietraeger_code IN ('7520', '7530')                      AS ist_fossil,
    g.gkat IN ('1020', '1030', '1040')                             AS ist_wohngebaeude,
    -- eine Angabe gilt als brauchbar, wenn ein konkreter Traeger genannt ist
    (g.energietraeger_code IS NOT NULL
       AND g.energietraeger_code NOT IN ('7598', '7599'))          AS hat_angabe,
    g.quelle_code = '860'                                          AS quelle_vz2000,
    date_diff('year', g.quelle_datum, g.stand)                     AS alter_jahre
FROM g
LEFT JOIN bronze_gwr_kodes ke ON ke.CMERKM = 'GENH1'      AND ke.CECODID = g.energietraeger_code
LEFT JOIN bronze_gwr_kodes ks ON ks.CMERKM = 'GWAERSCEH1' AND ks.CECODID = g.quelle_code
LEFT JOIN bronze_gwr_kodes kk ON kk.CMERKM = 'GKAT'       AND kk.CECODID = g.gkat;

CREATE INDEX IF NOT EXISTS idx_geb_ch_gemeinde ON silver_gebaeude_ch (bfs_nr);
CREATE INDEX IF NOT EXISTS idx_geb_ch_kanton   ON silver_gebaeude_ch (kanton);
