-- Ersetzt match_waermenutzung und v_test5 aus test5.sql (dort die erste Fassung).
-- Eine Entscheidung je Anlage; keine Zwangszuordnung bei Mehrdeutigkeit.
-- Schwellen sind konservative Annahmen, keine gelernten Wahrscheinlichkeiten.
-- Amtliche Mehrfach-EGID bleiben als Versorgungsgruppe zur manuellen Pruefung offen.
CREATE OR REPLACE TABLE anlage_kandidaten AS
WITH amt AS (
    SELECT DISTINCT a.anlage_id, TRY_CAST(trim(x) AS BIGINT) AS egid
    FROM silver_waermenutzung a,
         UNNEST(str_split(a.egid_amtlich, ',')) t(x)
    WHERE trim(x) <> ''
), adr AS (
    SELECT DISTINCT a.anlage_id, ad.egid
    FROM silver_waermenutzung a JOIN silver_adresse_ch ad
      ON ad.kanton = a.kanton AND ad.strasse_k = strasse_norm(a.strasse)
     AND ad.hausnr_k = hausnr_norm(a.hausnummer)
    WHERE strasse_norm(a.strasse) <> '' AND hausnr_norm(a.hausnummer) <> ''
), raum AS (
    SELECT a.anlage_id, g.egid
    FROM silver_waermenutzung a JOIN silver_gebaeude_ch g
      ON g.kanton = a.kanton
     AND g.e_lv95 BETWEEN a.e_lv95 - 20 AND a.e_lv95 + 20
     AND g.n_lv95 BETWEEN a.n_lv95 - 20 AND a.n_lv95 + 20
    WHERE sqrt(pow(a.e_lv95-g.e_lv95,2)+pow(a.n_lv95-g.n_lv95,2)) <= 20
), alle AS (
    SELECT *, 'amtlich' AS weg FROM amt
    UNION ALL SELECT *, 'adresse' FROM adr
    UNION ALL SELECT *, 'umkreis' FROM raum
)
SELECT z.*, g.egid IS NOT NULL AND g.kanton=a.kanton AS gueltig,
       sqrt(pow(a.e_lv95-g.e_lv95,2)+pow(a.n_lv95-g.n_lv95,2)) AS dist_m
FROM alle z JOIN silver_waermenutzung a USING(anlage_id)
LEFT JOIN silver_gebaeude_ch g ON g.egid=z.egid;

CREATE OR REPLACE TABLE anlage_entscheidung AS
WITH statistik AS (
    SELECT a.anlage_id,
        count(*) FILTER(WHERE k.weg='amtlich') AS n_amt,
        count(*) FILTER(WHERE k.weg='amtlich' AND k.gueltig) AS n_amt_gueltig,
        count(*) FILTER(WHERE k.weg='adresse' AND k.gueltig) AS n_adr,
        count(*) FILTER(WHERE k.weg='umkreis' AND k.gueltig) AS n_raum,
        min(k.egid) FILTER(WHERE k.weg='amtlich' AND k.gueltig) AS egid_amt,
        min(k.egid) FILTER(WHERE k.weg='adresse' AND k.gueltig) AS egid_adr,
        min(k.egid) FILTER(WHERE k.weg='umkreis' AND k.gueltig) AS egid_raum,
        min(k.dist_m) FILTER(WHERE k.weg='adresse' AND k.gueltig) AS adr_dist
    FROM silver_waermenutzung a LEFT JOIN anlage_kandidaten k USING(anlage_id)
    GROUP BY a.anlage_id
), entscheid AS (
    SELECT *, CASE
        WHEN n_amt>0 AND n_amt<>n_amt_gueltig THEN 'offen_amtlich_ungueltig'
        WHEN n_amt>1 THEN 'offen_versorgungsgruppe'
        WHEN n_amt=1 AND n_adr=1 AND egid_amt<>egid_adr THEN 'offen_quellenkonflikt'
        WHEN n_amt=1 THEN 'amtlich'
        WHEN n_adr>1 THEN 'offen_adresse_mehrdeutig'
        WHEN n_adr=1 AND coalesce(adr_dist>200,TRUE) THEN 'offen_adresse_lage'
        WHEN n_adr=1 THEN 'adresse'
        WHEN n_raum=1 THEN 'umkreis_eindeutig'
        WHEN n_raum>1 THEN 'offen_umkreis_mehrdeutig'
        ELSE 'offen_kein_kandidat' END AS entscheidung
    FROM statistik
)
SELECT e.*, CASE entscheidung WHEN 'amtlich' THEN egid_amt
    WHEN 'adresse' THEN egid_adr WHEN 'umkreis_eindeutig' THEN egid_raum END AS egid
FROM entscheid e;

-- Diagnostik bleibt auf unselektierten Nachbarn und kann weiterhin ohne amtliche
-- EGID gegen die Zuger Referenz gemessen werden (kein Selbsttest des EGID-Joins).
CREATE OR REPLACE TABLE match_waermenutzung AS
SELECT a.anlage_id, a.kanton, a.anlagentyp, a.entnahme_kw,
       a.datum_bewilligung,a.status,a.ist_gebaut,a.belegt_anlage,'umkreis' AS weg,k.dist_m,
       g.egid,g.bfs_nr,g.gemeinde,g.energie_klasse,g.ist_fossil,g.ist_wohngebaeude,
       g.quelle_code,g.quelle_txt,g.quelle_datum,g.gkat,g.baujahr
FROM anlage_kandidaten k JOIN silver_waermenutzung a USING(anlage_id)
JOIN silver_gebaeude_ch g ON g.egid=k.egid
WHERE k.weg='umkreis' AND k.gueltig;

-- Listensignal: eindeutig zugeordnet, echter Abstand, keine aufgegebenen oder geplanten
-- Anlagen. Anlagen ohne Statusfeld (etwa Zuerich) bleiben drin, obwohl ein fehlender
-- Status die Ausfuehrung nicht belegt.
CREATE OR REPLACE VIEW v_test5 AS
SELECT g.egid,g.kanton,g.bfs_nr,g.gemeinde,g.baujahr,g.gkat,g.energie_klasse,
       g.quelle_code,g.quelle_txt,g.quelle_datum,a.anlagentyp,
       sqrt(pow(a.e_lv95-g.e_lv95,2)+pow(a.n_lv95-g.n_lv95,2)) AS dist_m,
       a.entnahme_kw,a.datum_bewilligung,a.status,
       -- Nur beim Weg ueber den Umkreis ist diese Zahl gemessen, und dann ist sie
       -- eins. Bei amtlicher EGID oder Adresse wurde nie gezaehlt, wie viele Gebaeude
       -- in der Naehe stehen, deshalb NULL.
       CASE WHEN e.entscheidung='umkreis_eindeutig' THEN 1::BIGINT END
                                                  AS gebaeude_im_umkreis,
       a.anlage_id,a.anlage_nr,
       -- Zuerich: Laufnummer der GBS-Nummer, kalibrierter Datumsersatz (test5.sql)
       a.laufnummer AS sonde_laufnummer,
       e.entscheidung AS zuordnungsweg
FROM anlage_entscheidung e JOIN silver_waermenutzung a USING(anlage_id)
JOIN silver_gebaeude_ch g ON g.egid=e.egid
WHERE g.ist_fossil AND g.ist_wohngebaeude AND a.ist_gebaut
  -- Statusfilter ist belegt_anlage aus silver_waermenutzung (test5.sql), damit er nur
  -- an einer Stelle definiert ist.
  AND a.belegt_anlage
  AND (a.kanton NOT IN (SELECT kanton FROM v_lage_ungenau)
       OR e.entscheidung IN ('amtlich','adresse'))
QUALIFY row_number() OVER(PARTITION BY g.egid ORDER BY
    CASE e.entscheidung WHEN 'amtlich' THEN 1 WHEN 'adresse' THEN 2 ELSE 3 END,
    dist_m NULLS LAST,a.kanton,a.anlage_nr,a.anlage_id)=1;
