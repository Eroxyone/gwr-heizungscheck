-- Zuordnung Waermenutzungsanlage -> Gebaeude: eine Entscheidung je Anlage.
--
-- Ersetzt match_waermenutzung und v_test5 aus test5.sql. Dort wird jedes Gebaeude
-- zugeordnet, das ein Weg findet, im Umkreis also alle innerhalb von 20 m. Hier wird
-- eine Anlage nur zugeordnet, wenn genau ein Gebaeude in Frage kommt, sonst bleibt sie
-- offen. Die Schwellen (20 m Umkreis, 200 m zwischen Adresse und Anlage) sind
-- vorsichtige Annahmen, keine gelernten Wahrscheinlichkeiten.
--
-- Drei Wege, in dieser Rangfolge:
--   amtlich   der Kanton nennt die EGID selbst
--   adresse   Strasse und Hausnummer der Anlage gegen die GWR-Eingangstabelle
--   umkreis   Gebaeude innerhalb von 20 m um die Anlage

-- --------------------------------------------------------------------------- Kandidaten
-- Alle Gebaeude, die ueber einen der drei Wege in Frage kommen. gueltig ist ein
-- Kandidat, wenn das Gebaeude im Register besteht und im Kanton der Anlage liegt.
CREATE OR REPLACE TABLE anlage_kandidaten AS
WITH ueber_egid AS (
    SELECT DISTINCT a.anlage_id, TRY_CAST(trim(x) AS BIGINT) AS egid
    FROM silver_waermenutzung a,
         UNNEST(str_split(a.egid_amtlich, ',')) AS t(x)
    WHERE trim(x) <> ''
),
ueber_adresse AS (
    SELECT DISTINCT a.anlage_id, ad.egid
    FROM silver_waermenutzung a
    JOIN silver_adresse_ch ad
      ON ad.kanton = a.kanton
     AND ad.strasse_k = strasse_norm(a.strasse)
     AND ad.hausnr_k  = hausnr_norm(a.hausnummer)
    WHERE strasse_norm(a.strasse) <> '' AND hausnr_norm(a.hausnummer) <> ''
),
ueber_umkreis AS (
    SELECT a.anlage_id, g.egid
    FROM silver_waermenutzung a
    JOIN silver_gebaeude_ch g
      ON g.kanton = a.kanton
     AND g.e_lv95 BETWEEN a.e_lv95 - 20 AND a.e_lv95 + 20
     AND g.n_lv95 BETWEEN a.n_lv95 - 20 AND a.n_lv95 + 20
    WHERE sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) <= 20
),
zusammen AS (
    SELECT *, 'amtlich' AS weg FROM ueber_egid
    UNION ALL
    SELECT *, 'adresse' FROM ueber_adresse
    UNION ALL
    SELECT *, 'umkreis' FROM ueber_umkreis
)
SELECT z.*,
       (g.egid IS NOT NULL AND g.kanton = a.kanton)                         AS gueltig,
       sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2))      AS dist_m
FROM zusammen z
JOIN silver_waermenutzung a USING (anlage_id)
LEFT JOIN silver_gebaeude_ch g ON g.egid = z.egid;

-- --------------------------------------------------------------------------- Entscheidung
-- Die erste zutreffende Zeile gilt. Greift ein hoeherer Weg, ohne eindeutig zu sein,
-- bleibt die Anlage offen und faellt nicht auf den naechsten Weg zurueck.
--   offen_amtlich_ungueltig    eine amtliche EGID fehlt im Register oder liegt in einem
--                              anderen Kanton
--   offen_versorgungsgruppe    mehrere amtliche EGID: Die Anlage versorgt mehrere
--                              Gebaeude und bleibt zur Pruefung von Hand offen
--   offen_quellenkonflikt      amtliche EGID und Adresse nennen verschiedene Gebaeude
--   amtlich                    genau eine amtliche EGID
--   offen_adresse_mehrdeutig   die Adresse trifft mehrere Gebaeude
--   offen_adresse_lage         die Adresse trifft ein Gebaeude, das mehr als 200 m von
--                              der Anlage entfernt liegt oder keine Koordinate traegt
--   adresse                    die Adresse trifft genau ein Gebaeude in der Naehe
--   umkreis_eindeutig          genau ein Gebaeude im Umkreis
--   offen_umkreis_mehrdeutig   mehrere Gebaeude im Umkreis
--   offen_kein_kandidat        kein Gebaeude im Umkreis
CREATE OR REPLACE TABLE anlage_entscheidung AS
WITH statistik AS (
    SELECT a.anlage_id,
           count(*)      FILTER (WHERE k.weg = 'amtlich')                AS n_amt,
           count(*)      FILTER (WHERE k.weg = 'amtlich' AND k.gueltig)  AS n_amt_gueltig,
           count(*)      FILTER (WHERE k.weg = 'adresse' AND k.gueltig)  AS n_adr,
           count(*)      FILTER (WHERE k.weg = 'umkreis' AND k.gueltig)  AS n_raum,
           min(k.egid)   FILTER (WHERE k.weg = 'amtlich' AND k.gueltig)  AS egid_amt,
           min(k.egid)   FILTER (WHERE k.weg = 'adresse' AND k.gueltig)  AS egid_adr,
           min(k.egid)   FILTER (WHERE k.weg = 'umkreis' AND k.gueltig)  AS egid_raum,
           min(k.dist_m) FILTER (WHERE k.weg = 'adresse' AND k.gueltig)  AS adr_dist
    FROM silver_waermenutzung a
    LEFT JOIN anlage_kandidaten k USING (anlage_id)
    GROUP BY a.anlage_id
),
entscheid AS (
    SELECT *,
        CASE
            WHEN n_amt > 0 AND n_amt <> n_amt_gueltig              THEN 'offen_amtlich_ungueltig'
            WHEN n_amt > 1                                         THEN 'offen_versorgungsgruppe'
            WHEN n_amt = 1 AND n_adr = 1 AND egid_amt <> egid_adr  THEN 'offen_quellenkonflikt'
            WHEN n_amt = 1                                         THEN 'amtlich'
            WHEN n_adr > 1                                         THEN 'offen_adresse_mehrdeutig'
            WHEN n_adr = 1 AND COALESCE(adr_dist > 200, TRUE)      THEN 'offen_adresse_lage'
            WHEN n_adr = 1                                         THEN 'adresse'
            WHEN n_raum = 1                                        THEN 'umkreis_eindeutig'
            WHEN n_raum > 1                                        THEN 'offen_umkreis_mehrdeutig'
            ELSE                                                        'offen_kein_kandidat'
        END AS entscheidung
    FROM statistik
)
SELECT e.*,
       CASE entscheidung
           WHEN 'amtlich'           THEN egid_amt
           WHEN 'adresse'           THEN egid_adr
           WHEN 'umkreis_eindeutig' THEN egid_raum
       END AS egid
FROM entscheid e;

-- --------------------------------------------------------------------------- Diagnostik
-- Alle Nachbarn im Umkreis, ohne Auswahl und ohne Blick auf EGID oder Adresse. Auf
-- dieser Tabelle laesst sich der Umkreis gegen die Zuger Referenz messen, ohne dass die
-- amtliche EGID ihr eigenes Ergebnis bestaetigt.
CREATE OR REPLACE TABLE match_waermenutzung AS
SELECT a.anlage_id, a.kanton, a.anlagentyp, a.entnahme_kw,
       a.datum_bewilligung, a.status, a.ist_gebaut, a.belegt_anlage,
       'umkreis' AS weg, k.dist_m,
       g.egid, g.bfs_nr, g.gemeinde, g.energie_klasse, g.ist_fossil, g.ist_wohngebaeude,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.gkat, g.baujahr
FROM anlage_kandidaten k
JOIN silver_waermenutzung a USING (anlage_id)
JOIN silver_gebaeude_ch g ON g.egid = k.egid
WHERE k.weg = 'umkreis' AND k.gueltig;

-- --------------------------------------------------------------------------- Listensignal
-- Fossil beheiztes Wohngebaeude mit einer zugeordneten, gebauten Anlage. Je Gebaeude
-- eine Zeile: amtlich vor Adresse vor Umkreis, danach die naechstgelegene Anlage.
-- dist_m ist auf jedem Weg der Abstand zwischen Anlage und Gebaeude.
-- Anlagen ohne Statusfeld (etwa Zuerich) bleiben drin, obwohl ein fehlender Status die
-- Ausfuehrung nicht belegt.
CREATE OR REPLACE VIEW v_test5 AS
SELECT g.egid, g.kanton, g.bfs_nr, g.gemeinde, g.baujahr, g.gkat, g.energie_klasse,
       g.quelle_code, g.quelle_txt, g.quelle_datum, a.anlagentyp,
       sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) AS dist_m,
       a.entnahme_kw, a.datum_bewilligung, a.status,
       -- Nur beim Weg ueber den Umkreis ist diese Zahl gemessen, und dann ist sie
       -- eins. Bei amtlicher EGID oder Adresse wurde nie gezaehlt, wie viele Gebaeude
       -- in der Naehe stehen, deshalb NULL.
       CASE WHEN e.entscheidung = 'umkreis_eindeutig' THEN 1::BIGINT END
                                                                       AS gebaeude_im_umkreis,
       a.anlage_id, a.anlage_nr,
       -- Zuerich: Laufnummer der GBS-Nummer, kalibrierter Datumsersatz (test5.sql)
       a.laufnummer                                                    AS sonde_laufnummer,
       e.entscheidung                                                  AS zuordnungsweg
FROM anlage_entscheidung e
JOIN silver_waermenutzung a USING (anlage_id)
JOIN silver_gebaeude_ch g ON g.egid = e.egid
WHERE g.ist_fossil
  AND g.ist_wohngebaeude
  AND a.ist_gebaut
  -- Der Statusfilter ist belegt_anlage aus silver_waermenutzung (test5.sql), damit er
  -- nur an einer Stelle definiert ist.
  AND a.belegt_anlage
  -- Wo die Koordinate nicht das Gebaeude meint (v_lage_ungenau), zaehlen nur die Wege,
  -- die ohne sie auskommen.
  AND (a.kanton NOT IN (SELECT kanton FROM v_lage_ungenau)
       OR e.entscheidung IN ('amtlich', 'adresse'))
QUALIFY row_number() OVER (
    PARTITION BY g.egid
    ORDER BY CASE e.entscheidung WHEN 'amtlich' THEN 1 WHEN 'adresse' THEN 2 ELSE 3 END,
             dist_m NULLS LAST, a.kanton, a.anlage_nr, a.anlage_id) = 1;
