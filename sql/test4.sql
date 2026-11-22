-- Test 4: Gebaeude mit registrierter Solaranlage, aber fossilem Heizungseintrag aus der Volkszaehlung 2000.
-- Die vollstaendige BFE-Datei hat keine EGID-Spalte -> raeumlicher Abgleich ueber die Anlagenkoordinate.

CREATE OR REPLACE TABLE silver_pv AS
SELECT
    xtf_id                                   AS pv_id,
    Address                                  AS adresse,
    PostCode                                 AS plz,
    Municipality                             AS gemeinde_txt,
    TRY_CAST(BeginningOfOperation AS DATE)   AS inbetriebnahme,
    TRY_CAST(TotalPower AS DOUBLE)           AS leistung_kw,
    PlantCategory                            AS anlagenkategorie,
    TRY_CAST(_x AS DOUBLE)                   AS e_lv95,
    TRY_CAST(_y AS DOUBLE)                   AS n_lv95
FROM bronze_epa
WHERE Canton = 'ZH'
  AND SubCategory = 'subcat_2'          -- Photovoltaik
  AND TRY_CAST(_x AS DOUBLE) IS NOT NULL;

-- naechstes GWR-Gebaeude innerhalb von 25 m
CREATE OR REPLACE TABLE match_pv AS
WITH geb AS (
    SELECT egid, bfs_nr, e_lv95, n_lv95 FROM silver_gebaeude
    WHERE e_lv95 IS NOT NULL AND n_lv95 IS NOT NULL
),
paare AS (
    SELECT p.pv_id, g.egid,
           sqrt(pow(p.e_lv95 - g.e_lv95, 2) + pow(p.n_lv95 - g.n_lv95, 2)) AS dist_m,
           row_number() OVER (PARTITION BY p.pv_id
               ORDER BY pow(p.e_lv95 - g.e_lv95, 2) + pow(p.n_lv95 - g.n_lv95, 2)) AS rang
    FROM silver_pv p
    JOIN geb g
      ON g.e_lv95 BETWEEN p.e_lv95 - 25 AND p.e_lv95 + 25
     AND g.n_lv95 BETWEEN p.n_lv95 - 25 AND p.n_lv95 + 25
)
SELECT pv_id, egid, round(dist_m, 1) AS dist_m FROM paare WHERE rang = 1 AND dist_m <= 25;

CREATE OR REPLACE VIEW v_test4 AS
SELECT g.bfs_nr, g.gemeinde, g.egid, g.energietraeger_txt, g.energie_klasse,
       g.quelle_txt, g.quelle_datum, g.baujahr,
       p.inbetriebnahme, p.leistung_kw, m.dist_m
FROM match_pv m
JOIN silver_pv p        USING (pv_id)
JOIN silver_gebaeude g  ON g.egid = m.egid
WHERE g.gkat IN ('1020', '1030', '1040')
  AND g.ist_fossil
  AND g.quelle_code = '860';
