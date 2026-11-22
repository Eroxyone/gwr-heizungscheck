-- Silver-Layer: typisiert, klassifiziert, ohne fachliche Auswertung.
-- Codes stammen 1:1 aus kodes_codes_codici.csv (GWR-Merkmalskatalog), nichts geraten.

CREATE OR REPLACE TABLE silver_gebaeude AS
WITH g AS (
    SELECT
        CAST(EGID AS BIGINT)                                   AS egid,
        CAST(GGDENR AS INTEGER)                                AS bfs_nr,
        GGDENAME                                               AS gemeinde,
        TRY_CAST(GKODE AS DOUBLE)                              AS e_lv95,
        TRY_CAST(GKODN AS DOUBLE)                              AS n_lv95,
        TRY_CAST(GBAUJ AS INTEGER)                             AS baujahr,
        GKAT                                                   AS gkat,
        GSTAT                                                  AS gstat,
        LPARZ                                                  AS parzelle,
        EGRID                                                  AS egrid,
        GWAERZH1                                               AS waermeerzeuger_code,
        GENH1                                                  AS energietraeger_code,
        GWAERSCEH1                                             AS quelle_code,
        TRY_CAST(GWAERDATH1 AS DATE)                           AS quelle_datum,
        GWAERZW1                                               AS ww_erzeuger_code,
        GENW1                                                  AS ww_energietraeger_code,
        GWAERSCEW1                                             AS ww_quelle_code,
        TRY_CAST(GWAERDATW1 AS DATE)                           AS ww_quelle_datum
    FROM bronze_gwr_gebaeude
    WHERE GSTAT = '1004'          -- nur bestehende Gebaeude
)
SELECT
    g.*,
    kz.CODTXTLD AS waermeerzeuger_txt,
    ke.CODTXTLD AS energietraeger_txt,
    ks.CODTXTLD AS quelle_txt,
    kk.CODTXTLD AS gebaeudekategorie_txt,
    CASE g.energietraeger_code
        WHEN '7500' THEN 'keine'
        WHEN '7501' THEN 'waermepumpe'
        WHEN '7510' THEN 'waermepumpe'
        WHEN '7511' THEN 'waermepumpe'
        WHEN '7512' THEN 'waermepumpe'
        WHEN '7513' THEN 'waermepumpe'
        WHEN '7520' THEN 'gas'
        WHEN '7530' THEN 'oel'
        WHEN '7540' THEN 'holz'
        WHEN '7541' THEN 'holz'
        WHEN '7542' THEN 'holz'
        WHEN '7543' THEN 'holz'
        WHEN '7550' THEN 'abwaerme'
        WHEN '7560' THEN 'elektro'
        WHEN '7570' THEN 'solarthermie'
        WHEN '7580' THEN 'fernwaerme'
        WHEN '7581' THEN 'fernwaerme'
        WHEN '7582' THEN 'fernwaerme'
        WHEN '7598' THEN 'unbestimmt'
        WHEN '7599' THEN 'andere'
        ELSE 'ohne_angabe'
    END AS energie_klasse,
    g.energietraeger_code IN ('7520', '7530')                  AS ist_fossil,
    g.quelle_code = '860'                                      AS quelle_vz2000,
    g.quelle_code = '869'                                      AS quelle_baubewilligung
FROM g
LEFT JOIN bronze_gwr_kodes kz ON kz.CMERKM = 'GWAERZH1'   AND kz.CECODID = g.waermeerzeuger_code
LEFT JOIN bronze_gwr_kodes ke ON ke.CMERKM = 'GENH1'      AND ke.CECODID = g.energietraeger_code
LEFT JOIN bronze_gwr_kodes ks ON ks.CMERKM = 'GWAERSCEH1' AND ks.CECODID = g.quelle_code
LEFT JOIN bronze_gwr_kodes kk ON kk.CMERKM = 'GKAT'       AND kk.CECODID = g.gkat;

-- Adressen je EGID, normalisiert fuer den Textabgleich mit Baugesuchen
CREATE OR REPLACE TABLE silver_adressen AS
SELECT
    CAST(EGID AS BIGINT)            AS egid,
    STRNAME                         AS strasse,
    DEINR                           AS hausnummer,
    DPLZ4                           AS plz,
    DPLZNAME                        AS ort,
    TRY_CAST(DKODE AS DOUBLE)       AS e_lv95,
    TRY_CAST(DKODN AS DOUBLE)       AS n_lv95,
    -- Normalisierung: klein, Umlaute und Akzente ersetzt, nur a-z und 0-9
    regexp_replace(
      replace(replace(replace(replace(replace(replace(lower(COALESCE(STRNAME, '')),
        'ä','a'),'ö','o'),'ü','u'),'é','e'),'è','e'),'ß','ss'),
      '[^a-z0-9]', '', 'g')         AS strasse_norm,
    lower(regexp_replace(COALESCE(DEINR, ''), '[^0-9a-zA-Z]', '', 'g')) AS hnr_norm
FROM bronze_gwr_eingang
WHERE STRNAME IS NOT NULL;
