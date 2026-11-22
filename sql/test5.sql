-- Test 5: Waermenutzungsanlage vorhanden, GWR sagt fossil.
--
-- Anders als eine Photovoltaikanlage (Test 4) sagt eine Erdwaermesonde direkt etwas
-- ueber die Heizung. Steht im GWR trotzdem Oel oder Gas, ist das ein Widerspruch und
-- mehr als ein Indiz.
--
-- Dreizehn Kantone veroeffentlichen ihre Anlagen, in unterschiedlicher Tiefe:
--   ZH (AWEL)  vier Layer, ohne Bohrdatum und ohne Status
--   BE (AGI)   Bewilligungsdatum (ab 1980) und Status "Ausgefuehrt"
--   SO (AFU)   Bewilligungsdatum (ab 1986), WGS84
--   LU         Bewilligungs- und Realisierungsdatum, Betriebszustand und ein
--              Kennzeichen, ob die Anlage dem Heizen dient. WGS84, Datum als TT.MM.JJJJ.
--              Dazu 7066 Luft-Wasser-Waermepumpen ohne Datum.
--   TG         Bohrdatum und Status "ausgebaut, in Nutzung"
--   GE (SITG)  Realisierungsdatum und Zustand, CSV mit LV95-Koordinaten
--   SH         ohne Datum, WGS84
--   UR (Lisag) nur "Konzession erteilt": bewilligt, nicht zwingend gebaut
--   SZ         Bewilligungsdatum (ab 1986) und Bohrtiefe, als GML
--   BL         Bohrregister: Das Jahr meint die Ausfuehrung, nicht die Bewilligung.
--   SG         Anlagenregister: fuehrt die Waermepumpe selbst, mit Anlageart,
--              baulichem Zustand und Erstellungsjahr
--   AI         Bohrkataster mit Erstelljahr und Bohrzweck
--   ZG         als einziger Kanton mit amtlicher EGID an einem Teil der Anlagen
-- BE, SO, TG, GE, SZ, BL, SG, AI und ZG gehen in die datierte Auswertung von Test 6 ein.

-- Jeder Kanton ausser Zuerich steht zwischen "-- @optional <Datei>" und "-- @ende".
-- Fehlt die Rohdatei, laesst pipeline.py den Block aus und rechnet mit den uebrigen
-- Kantonen weiter. Anlass: Der WFS von geoportal.ch (St. Gallen, Appenzell
-- Innerrhoden) verlangte am 22.11.2026 eine Anmeldung.
CREATE OR REPLACE TABLE silver_waermenutzung AS
WITH alle AS (
    -- ---------------------------------------------------------------- Zuerich
    SELECT 'ZH' AS kanton, 'erdwaermesonde' AS anlagentyp,
           "GBS-Nummer"      AS anlage_nr,
           -- Die GBS-Nummer ("b 00-12657") traegt eine Laufnummer, die mit der Zeit
           -- steigt. Das AWEL publiziert kein Datum, die Nummer dient als Datumsersatz
           -- (gold_laufnummer_kalibrierung am Ende dieser Datei).
           TRY_CAST(regexp_extract("GBS-Nummer", '-(\d+)$', 1) AS INTEGER) AS laufnummer,
           Waermeentnahme    AS entnahme_kw,
           Sondentiefe       AS tiefe_m,
           Gesamtsondenzahl  AS anzahl,
           NULL::DATE        AS datum_bewilligung,
           NULL::VARCHAR     AS status,
           geom
    FROM st_read('data/raw/waermenutzung_zh/erdwaermesonden.json')
    UNION ALL BY NAME
    SELECT 'ZH' AS kanton, 'grundwasserfassung' AS anlagentyp,
           Grundwasserrecht AS anlage_nr, NULL::DOUBLE AS entnahme_kw,
           NULL::DATE AS datum_bewilligung, NULL::VARCHAR AS status, geom
    FROM st_read('data/raw/waermenutzung_zh/grundwasserfassung-waermenutzung.json')
    UNION ALL BY NAME
    SELECT 'ZH' AS kanton, 'quellfassung' AS anlagentyp,
           NULL::VARCHAR AS anlage_nr, NULL::DOUBLE AS entnahme_kw,
           NULL::DATE AS datum_bewilligung, NULL::VARCHAR AS status, geom
    FROM st_read('data/raw/waermenutzung_zh/quellfassung-waermenutzung.json')
    UNION ALL BY NAME
    SELECT 'ZH' AS kanton, 'erdregister' AS anlagentyp,
           NULL::VARCHAR AS anlage_nr, NULL::DOUBLE AS entnahme_kw,
           NULL::DATE AS datum_bewilligung, NULL::VARCHAR AS status, geom
    FROM st_read('data/raw/waermenutzung_zh/erdregister.json')
    -- ---------------------------------------------------------------- Bern
    -- @optional data/raw/waermenutzung_be/ERDSOND.gpkg
    UNION ALL BY NAME
    SELECT 'BE' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(objectid AS VARCHAR)     AS anlage_nr,
           NULL::DOUBLE                  AS entnahme_kw,
           laenge_tot                    AS tiefe_m,
           anzahl_tot                    AS anzahl,
           CAST(datum_bew AS DATE)       AS datum_bewilligung,
           statust_bez_de                AS status,
           geometry                      AS geom
    FROM st_read('data/raw/waermenutzung_be/ERDSOND.gpkg',
                 layer = 'geodb.erdsond_erdsondb_vw')
    -- @ende
    -- ---------------------------------------------------------------- Thurgau
    -- @optional data/raw/waermenutzung_weitere/TG_erdwaermesonden.json
    UNION ALL BY NAME
    SELECT 'TG' AS kanton, 'erdwaermesonde' AS anlagentyp,
           NULL::VARCHAR                 AS anlage_nr,
           NULL::DOUBLE                  AS entnahme_kw,
           TRY_CAST(length AS DOUBLE)    AS tiefe_m,
           NULL::DOUBLE                  AS anzahl,
           TRY_CAST(datum AS DATE)       AS datum_bewilligung,
           status_txt                    AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/TG_erdwaermesonden.json')
    -- @ende
    -- ---------------------------------------------------------------- Uri
    -- @optional data/raw/waermenutzung_weitere/UR_erdsonden.json
    UNION ALL BY NAME
    SELECT 'UR' AS kanton, 'erdwaermesonde' AS anlagentyp,
           NULL::VARCHAR AS anlage_nr, NULL::DOUBLE AS entnahme_kw,
           NULL::DATE AS datum_bewilligung,
           status AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/UR_erdsonden.json')
    -- @ende
    -- ---------------------------------------------------------------- Solothurn
    -- @optional data/raw/waermenutzung_weitere/SO_erdwaermesonden.json
    -- WGS84. Die Abgabe ist auf 5000 Objekte begrenzt, der Download blaettert deshalb
    -- mit startIndex (src/download.py).
    UNION ALL BY NAME
    SELECT 'SO' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(nummer AS VARCHAR)               AS anlage_nr,
           NULL::DOUBLE                          AS entnahme_kw,
           TRY_CAST(bohrtiefe AS DOUBLE)         AS tiefe_m,
           TRY_CAST(anlage_anzahl_bohrloecher AS DOUBLE) AS anzahl,
           TRY_CAST(anlage_datum_bewilligung AS DATE)    AS datum_bewilligung,
           waermequelle_text                     AS status,
           ST_Transform(geom, 'EPSG:4326', 'EPSG:2056', always_xy := true) AS geom
    FROM st_read('data/raw/waermenutzung_weitere/SO_erdwaermesonden.json')
    -- @ende
    -- ---------------------------------------------------------------- Luzern
    -- @optional data/raw/waermenutzung_weitere/LU_erdwaermesonden.json
    -- Als gebaut gilt, was ein Realisierungsdatum der Bohrung traegt.
    UNION ALL BY NAME
    SELECT 'LU' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(Nutzungsnummer AS VARCHAR)                       AS anlage_nr,
           NULL::DOUBLE                                          AS entnahme_kw,
           TRY_CAST("Bohrtiefe__m_" AS DOUBLE)                   AS tiefe_m,
           TRY_CAST(Anzahl_Sonden AS DOUBLE)                     AS anzahl,
           TRY_CAST(try_strptime(Bewilligung_Datum, '%d.%m.%Y') AS DATE) AS datum_bewilligung,
           CASE WHEN CAST(Realisierung_Bohrung AS VARCHAR) IS NOT NULL
                      AND trim(CAST(Realisierung_Bohrung AS VARCHAR)) <> ''
                THEN 'Bohrung realisiert' ELSE 'nur bewilligt' END AS status,
           ST_Transform(geom, 'EPSG:4326', 'EPSG:2056', always_xy := true) AS geom
    FROM st_read('data/raw/waermenutzung_weitere/LU_erdwaermesonden.json')
    -- @ende
    -- ---------------------------------------------------------------- Genf
    -- @optional data/raw/waermenutzung_weitere/GE_sonden/GOL_SONDES_GEOTH.csv
    -- CSV mit LV95-Koordinaten in den Spalten E und N. ANNEE_REALISATION ist als
    -- Zahl im Format JJJJMMTT abgelegt.
    UNION ALL BY NAME
    SELECT 'GE' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(ID_SONDAGE AS VARCHAR)                    AS anlage_nr,
           TRY_CAST(PUISSANCE_SONDE AS DOUBLE)            AS entnahme_kw,
           TRY_CAST(PROFONDEUR_EQUIPEMENT AS DOUBLE)      AS tiefe_m,
           NULL::DOUBLE                                   AS anzahl,
           TRY_CAST(try_strptime(CAST(ANNEE_REALISATION AS VARCHAR), '%Y%m%d') AS DATE)
                                                          AS datum_bewilligung,
           ETAT                                           AS status,
           ST_Point(TRY_CAST(E AS DOUBLE), TRY_CAST(N AS DOUBLE)) AS geom
    FROM read_csv('data/raw/waermenutzung_weitere/GE_sonden/GOL_SONDES_GEOTH.csv',
                  delim = ';', header = true, all_varchar = true, encoding = 'utf-8')
    WHERE TRY_CAST(E AS DOUBLE) IS NOT NULL
    -- @ende
    -- ---------------------------------------------------------------- Schaffhausen
    -- @optional data/raw/waermenutzung_weitere/SH_erdwaermesonden.json
    -- WGS84 statt LV95, deshalb die Transformation.
    UNION ALL BY NAME
    SELECT 'SH' AS kanton, 'erdwaermesonde' AS anlagentyp,
           uuid                          AS anlage_nr,
           NULL::DOUBLE                  AS entnahme_kw,
           TRY_CAST(laenge_m AS DOUBLE)  AS tiefe_m,
           TRY_CAST(anzahl AS DOUBLE)    AS anzahl,
           NULL::DATE                    AS datum_bewilligung,
           typ                           AS status,
           ST_Transform(geom, 'EPSG:4326', 'EPSG:2056', always_xy := true) AS geom
    FROM st_read('data/raw/waermenutzung_weitere/SH_erdwaermesonden.json')
    -- @ende
    -- ---------------------------------------------------------------- Schwyz
    -- @optional data/raw/waermenutzung_weitere/SZ_erdwaermesonden.gml
    -- GML statt GeoJSON. Das Datum kommt als TT.MM.JJJJ, fehlende Werte stehen als
    -- "- - -" da und werden von TRY_CAST abgefangen.
    UNION ALL BY NAME
    SELECT 'SZ' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(gml_id AS VARCHAR)                AS anlage_nr,
           NULL::DOUBLE                           AS entnahme_kw,
           TRY_CAST(tiefe AS DOUBLE)              AS tiefe_m,
           TRY_CAST(anz_erdwaermesonden AS DOUBLE) AS anzahl,
           TRY_CAST(try_strptime(CAST(bewilligungsdatum_ui AS VARCHAR), '%d.%m.%Y') AS DATE)
                                                  AS datum_bewilligung,
           NULL::VARCHAR                          AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/SZ_erdwaermesonden.gml')
    -- @ende
    -- ---------------------------------------------------------------- Basel-Landschaft
    -- @optional data/raw/waermenutzung_weitere/BL_erdsonden.gml
    -- Bohrregister: "jahr" ist das Bohrjahr, also ein Ausfuehrungs- und kein
    -- Bewilligungsdatum. Auf den 1. Januar gesetzt, die Unschaerfe betraegt bis zu
    -- einem Jahr.
    UNION ALL BY NAME
    SELECT 'BL' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(bohrung_id AS VARCHAR)            AS anlage_nr,
           NULL::DOUBLE                           AS entnahme_kw,
           TRY_CAST(sohle_tiefe AS DOUBLE)        AS tiefe_m,
           NULL::DOUBLE                           AS anzahl,
           TRY_CAST(make_date(TRY_CAST(jahr AS INTEGER), 1, 1) AS DATE)
                                                  AS datum_bewilligung,
           'Bohrung ausgefuehrt'                  AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/BL_erdsonden.gml')
    WHERE TRY_CAST(jahr AS INTEGER) BETWEEN 1900 AND year(current_date)
    -- @ende
    -- ---------------------------------------------------------------- St. Gallen
    -- @optional data/raw/waermenutzung_weitere/SG_thermischezentralen.gml
    -- Reine Kuehlanlagen sind ausgeschlossen, sie sagen nichts ueber die Heizung.
    -- "Waermeuebergabestation" ist ein Fernwaermeanschluss und zaehlt ebenfalls als
    -- Beleg gegen eine fossile Heizung.
    UNION ALL BY NAME
    SELECT 'SG' AS kanton,
           CASE WHEN q352_sg_gnobo_thermzentralen_anlageart = 'Wärmeübergabestation'
                THEN 'fernwaermeanschluss' ELSE 'waermepumpe' END      AS anlagentyp,
           CAST(q352_sg_gnobo_thermzentralen_objektnr AS VARCHAR)      AS anlage_nr,
           TRY_CAST(q352_sg_gnobo_thermzentralen_leistung AS DOUBLE)   AS entnahme_kw,
           TRY_CAST(q352_sg_gnobo_thermzentralen_erdsonlaen AS DOUBLE) AS tiefe_m,
           TRY_CAST(q352_sg_gnobo_thermzentralen_erdsonanz AS DOUBLE)  AS anzahl,
           TRY_CAST(make_date(
               TRY_CAST(q352_sg_gnobo_thermzentralen_erstellungsjahr AS INTEGER), 1, 1)
                                                                       AS DATE)
                                                                       AS datum_bewilligung,
           q352_sg_gnobo_thermzentralen_zustand_baulich                AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/SG_thermischezentralen.gml')
    WHERE COALESCE(q352_sg_gnobo_thermzentralen_anlagetyp, '') <> 'Kühlung'
      AND TRY_CAST(q352_sg_gnobo_thermzentralen_erstellungsjahr AS INTEGER)
          BETWEEN 1900 AND year(current_date)
    -- @ende
    -- ---------------------------------------------------------------- Appenzell I.Rh.
    -- @optional data/raw/waermenutzung_weitere/AI_erdwaermesonden.gml
    -- Die Eigentuemerspalte des Rohdatensatzes wird nicht uebernommen (keine
    -- Personendaten).
    UNION ALL BY NAME
    SELECT 'AI' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(f211_ai_erdwaermesonden_id_bo AS VARCHAR)               AS anlage_nr,
           NULL::DOUBLE                                                 AS entnahme_kw,
           TRY_CAST(f211_ai_erdwaermesonden_uk_bohrung AS DOUBLE)       AS tiefe_m,
           NULL::DOUBLE                                                 AS anzahl,
           TRY_CAST(make_date(
               TRY_CAST(f211_ai_erdwaermesonden_erstelljahr AS INTEGER), 1, 1) AS DATE)
                                                                        AS datum_bewilligung,
           'Bohrung ausgefuehrt'                                        AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/AI_erdwaermesonden.gml')
    WHERE f211_ai_erdwaermesonden_bohrzweck_15 = 'Erdwaermesondenanlage'
      AND TRY_CAST(f211_ai_erdwaermesonden_erstelljahr AS INTEGER)
          BETWEEN 1900 AND year(current_date)
    -- @ende
    -- ---------------------------------------------------------------- Zug
    -- @optional data/raw/waermenutzung_weitere/ZG_erdwaermenutzung.gpkg
    -- Das Bohrdatum ist der Ausfuehrungsnachweis, das Bewilligungsdatum der Rueckfall.
    -- Die obere Schranke ist noetig: Ein Datensatz traegt 2105 als Bohrdatum.
    UNION ALL BY NAME
    SELECT 'ZG' AS kanton, 'erdwaermesonde' AS anlagentyp,
           CAST(anlage_nr AS VARCHAR)                    AS anlage_nr,
           TRY_CAST(max_heizleistung AS DOUBLE)          AS entnahme_kw,
           NULL::DOUBLE                                  AS tiefe_m,
           NULL::DOUBLE                                  AS anzahl,
           CASE WHEN TRY_CAST(bohrdatum AS DATE) BETWEEN DATE '1900-01-01' AND current_date
                THEN TRY_CAST(bohrdatum AS DATE)
                WHEN TRY_CAST(bewilligungsdatum AS DATE)
                     BETWEEN DATE '1900-01-01' AND current_date
                THEN TRY_CAST(bewilligungsdatum AS DATE) END AS datum_bewilligung,
           anlagenstatus                                 AS status,
           CAST(egids AS VARCHAR)                        AS egid_amtlich,
           -- Zug liefert auch die Adresse der Anlage (Stufe 2 der Zuordnung).
           CAST(strasse AS VARCHAR)                      AS strasse,
           CAST(hausnummer AS VARCHAR)                   AS hausnummer,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/ZG_erdwaermenutzung.gpkg',
                 layer = 'zg.ews_erdwaermesondenanlagen')
    -- Reine Kuehlanlagen sagen nichts ueber die Heizung.
    WHERE COALESCE(verwendungszweck, '') NOT IN ('Gebäudekühlung',
                                                 'Gebäudekühlung + Warmwasseraufbereitung')
    -- @ende
    -- ------------------------------------------- Luzern, Luft-Wasser-Waermepumpen
    -- @optional data/raw/waermenutzung_weitere/LU_luftwasserwaermepumpen.json
    -- Luft-Wasser-Waermepumpen stehen in keinem Sondenkataster, weil sie nicht bohren.
    -- Laut Kanton koennen die Anlagen erstellt oder in Planung sein. Ihr Status zaehlt
    -- bei ist_gebaut mit, aber nicht als Anlagenbeleg (belegt_anlage) und nicht in
    -- Test 6.
    UNION ALL BY NAME
    SELECT 'LU' AS kanton, 'luft_wasser_wp' AS anlagentyp,
           CAST(OBJECTID AS VARCHAR)  AS anlage_nr,
           NULL::DOUBLE               AS entnahme_kw,
           NULL::DOUBLE               AS tiefe_m,
           NULL::DOUBLE               AS anzahl,
           NULL::DATE                 AS datum_bewilligung,
           'bewilligt oder geplant'   AS status,
           ST_Transform(geom, 'EPSG:4326', 'EPSG:2056', always_xy := true) AS geom
    FROM st_read('data/raw/waermenutzung_weitere/LU_luftwasserwaermepumpen.json')
    -- @ende
    -- ---------------------------------------------------------------- Uri, Grundwasser
    -- @optional data/raw/waermenutzung_weitere/UR_grundwasserwaermepumpen.json
    UNION ALL BY NAME
    SELECT 'UR' AS kanton, 'grundwasserwaermepumpe' AS anlagentyp,
           CAST(id AS VARCHAR)  AS anlage_nr,
           NULL::DOUBLE         AS entnahme_kw,
           NULL::DOUBLE         AS tiefe_m,
           NULL::DOUBLE         AS anzahl,
           NULL::DATE           AS datum_bewilligung,
           status               AS status,
           geom
    FROM st_read('data/raw/waermenutzung_weitere/UR_grundwasserwaermepumpen.json')
    -- @ende
)
SELECT row_number() OVER ()  AS anlage_id,
       kanton, anlagentyp, anlage_nr, entnahme_kw, tiefe_m, anzahl,
       datum_bewilligung, status, egid_amtlich, strasse, hausnummer, laufnummer,
       -- Wo ein Status gefuehrt wird, zaehlt nur, was gebaut wurde. Zuerich fuehrt
       -- keinen, dort gelten alle veroeffentlichten Anlagen als bestehend. Uri meldet
       -- nur "Konzession erteilt": hier noch enthalten, in Test 6 ausgeschlossen.
       (status IS NULL
        OR status IN ('Ausgeführt', 'In Ausführung',
                      'ausgebaut, in Nutzung', 'ausgebaut, Messungen möglich',
                      'Konzession erteilt', 'bewilligt oder geplant',
                      -- Solothurn fuehrt keinen Status, sondern die Waermequelle
                      'WP mit Erdwärmesonde', 'WP mit Erdkollektor',
                      'WP mit Grundwasser, Eisspeicher oder Andere',
                      -- Genf: alles ausser zugeschuetteten Bohrungen
                      'Inconnu', 'Exploitable', 'Exploité / En activité', 'Défectueux',
                      -- Luzern, Basel-Landschaft und Appenzell: nachweislich gebohrt
                      'Bohrung realisiert', 'Bohrung ausgefuehrt',
                      -- St. Gallen: nur was steht, nicht was geplant ist
                      'bestehend, vorhanden',
                      -- Zug: "nicht erstellt" ist ausgeschlossen, "unbekannt" nicht
                      -- (dort liegt meist ein Bohrdatum vor).
                      'in Betrieb', 'ausser Betrieb', 'unbekannt')
        OR status IN ('Erdsonde', 'Erdsondenfeld', 'Erdkollektoren', 'Erdkörbe', 'GRD'))
                                                                      AS ist_gebaut,
       -- Gebaut ist nicht dasselbe wie in Betrieb. Genf fuehrt fuer fast alle
       -- Bohrungen den Status "Inconnu" (2'800) oder "Exploitable" (720): eine
       -- Einstufung der Ressource, keine Aussage ueber eine laufende Waermepumpe.
       -- Deshalb ein zweites, engeres Merkmal: Belegt der Status, dass am Gebaeude
       -- eine Waermepumpe laeuft oder entsteht? Bewilligung, Konzession und
       -- Ressourceneinstufung tun das nicht (reports/belegwirkung.md).
       (status IS NULL
        OR status IN ('Ausgeführt', 'In Ausführung',
                      'ausgebaut, in Nutzung', 'ausgebaut, Messungen möglich',
                      'WP mit Erdwärmesonde', 'WP mit Erdkollektor',
                      'WP mit Grundwasser, Eisspeicher oder Andere',
                      'Exploité / En activité',
                      'Bohrung realisiert', 'Bohrung ausgefuehrt',
                      'bestehend, vorhanden',
                      'in Betrieb', 'unbekannt')
        OR status IN ('Erdsonde', 'Erdsondenfeld', 'Erdkollektoren', 'Erdkörbe', 'GRD'))
                                                                      AS belegt_anlage,
       ST_X(ST_Centroid(geom)) AS e_lv95,
       ST_Y(ST_Centroid(geom)) AS n_lv95
FROM alle
WHERE geom IS NOT NULL;

-- ---------------------------------------------------------- Zuordnung als Kaskade
-- Der Radius von 20 m stammt aus einer Sensitivitaetsrechnung (ZH):
--   10 m  26448 Anlagen mit Gebaeude (67 %), 1,3 Gebaeude je Anlage, 13,7 % Widerspruch
--   20 m  37389 Anlagen mit Gebaeude (95 %), 2,4 Gebaeude je Anlage, 19,1 % Widerspruch
--   50 m  39284 Anlagen mit Gebaeude (99 %), 11,3 Gebaeude je Anlage, 25,6 % Widerspruch
-- Gemessen an Zugs amtlichen EGID trifft der 20-m-Umkreis das richtige Gebaeude in
-- 73,8 % der Faelle, bei im Schnitt 1,87 Gebaeuden je Anlage (reports/zuordnung_zg.md).
--
-- Die Kaskade nimmt deshalb zuerst, was der Kanton mitliefert:
--   1. amtliche EGID   der Kanton hat das Gebaeude selbst benannt
--   2. Adresse         gegen die GWR-Eingangstabelle
--   3. Umkreis         alle Gebaeude innerhalb von 20 m
-- Greift eine Stufe, entfallen die folgenden fuer diese Anlage.
--
-- Der naechste Pipeline-Schritt (zuordnung_anlagen.sql) ersetzt match_waermenutzung
-- und v_test5 durch eine Fassung mit einer Entscheidung je Anlage. Die Fassung hier
-- bleibt stehen, weil die Laufnummer-Kalibrierung am Ende der Datei auf ihr rechnet.
CREATE OR REPLACE TABLE match_waermenutzung AS
WITH geb AS (
    SELECT egid, kanton, bfs_nr, gemeinde, e_lv95, n_lv95, energie_klasse, ist_fossil,
           quelle_code, quelle_txt, quelle_datum, gkat, baujahr, ist_wohngebaeude
    FROM silver_gebaeude_ch
    WHERE kanton IN ('ZH', 'BE', 'SO', 'LU', 'TG', 'GE', 'SH', 'UR', 'SZ', 'BL',
                     'SG', 'AI', 'ZG')
),
-- Stufe 1: Der Kanton nennt die EGID selbst. Mehrere EGID je Anlage sind erlaubt -
-- eine Erdsondenanlage kann ein Doppelhaus versorgen.
ueber_egid AS (
    SELECT a.anlage_id, TRY_CAST(TRIM(x) AS BIGINT) AS egid, 'amtlich' AS weg,
           0.0 AS dist_m
    FROM silver_waermenutzung a,
         UNNEST(str_split(a.egid_amtlich, ',')) AS t(x)
    WHERE a.egid_amtlich IS NOT NULL AND TRIM(x) <> ''
),
-- Stufe 2: nur fuer Anlagen, die Stufe 1 nicht erreicht haben
ueber_adresse AS (
    SELECT a.anlage_id, ad.egid, 'adresse' AS weg, 0.0 AS dist_m
    FROM silver_waermenutzung a
    JOIN silver_adresse_ch ad
      ON ad.kanton = a.kanton
     AND ad.strasse_k = strasse_norm(a.strasse)
     AND ad.hausnr_k  = hausnr_norm(a.hausnummer)
    WHERE a.strasse IS NOT NULL AND a.hausnummer IS NOT NULL
      AND strasse_norm(a.strasse) <> '' AND hausnr_norm(a.hausnummer) <> ''
      AND a.anlage_id NOT IN (SELECT anlage_id FROM ueber_egid)
),
-- Stufe 3: Umkreis, fuer alles Uebrige
ueber_umkreis AS (
    SELECT a.anlage_id, g.egid, 'umkreis' AS weg,
           round(sqrt(pow(a.e_lv95 - g.e_lv95, 2)
                      + pow(a.n_lv95 - g.n_lv95, 2)), 1) AS dist_m
    FROM silver_waermenutzung a
    JOIN geb g
      ON g.kanton = a.kanton
     AND g.e_lv95 BETWEEN a.e_lv95 - 20 AND a.e_lv95 + 20
     AND g.n_lv95 BETWEEN a.n_lv95 - 20 AND a.n_lv95 + 20
    WHERE a.e_lv95 IS NOT NULL AND g.e_lv95 IS NOT NULL
      AND sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) <= 20
      AND a.anlage_id NOT IN (SELECT anlage_id FROM ueber_egid)
      AND a.anlage_id NOT IN (SELECT anlage_id FROM ueber_adresse)
),
zusammen AS (
    SELECT * FROM ueber_egid
    UNION ALL SELECT * FROM ueber_adresse
    UNION ALL SELECT * FROM ueber_umkreis
)
SELECT z.anlage_id, a.kanton, a.anlagentyp, a.entnahme_kw,
       a.datum_bewilligung, a.status, a.ist_gebaut, a.belegt_anlage,
       z.weg, z.dist_m,
       g.egid, g.bfs_nr, g.gemeinde, g.energie_klasse, g.ist_fossil, g.ist_wohngebaeude,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.gkat, g.baujahr
FROM zusammen z
JOIN silver_waermenutzung a USING (anlage_id)
JOIN geb g ON g.egid = z.egid;

-- Sicht je Anlage: Traegt eines der zugeordneten Gebaeude eine Waermepumpe? Der Anteil
-- ohne ist ein Mass fuer die Fehlerquote des Registers, an einer unabhaengigen Quelle.
CREATE OR REPLACE VIEW v_test5_anlage AS
SELECT anlage_id, kanton, anlagentyp, any_value(ist_gebaut) AS ist_gebaut,
       any_value(belegt_anlage)                          AS belegt_anlage,
       any_value(datum_bewilligung)                      AS datum_bewilligung,
       any_value(status)                                 AS status,
       count(*)                                          AS gebaeude_im_umkreis,
       min(dist_m)                                       AS naechstes_gebaeude_m,
       sum((energie_klasse = 'waermepumpe')::INT)        AS mit_waermepumpe,
       sum(ist_fossil::INT)                              AS fossil,
       max(quelle_datum)                                 AS juengstes_quelldatum,
       any_value(bfs_nr)                                 AS bfs_nr,
       any_value(gemeinde)                               AS gemeinde
FROM match_waermenutzung
GROUP BY anlage_id, kanton, anlagentyp;

-- --------------------------------------------------------- Lagequalitaet je Kanton
-- Nicht jede Koordinate meint dasselbe. Entfernung der Anlage zum naechstgelegenen
-- Gebaeude (Stichprobe 3000 je Kanton, Suchradius 300 m):
--   ZH  Median  8,0 m   95,3 % unter 20 m
--   BE  Median  8,8 m   95,0 %
--   SG  Median  9,3 m   93,3 %
--   LU  Median 24,2 m   42,5 %
-- In Luzern meint die Koordinate offenbar die Parzelle: kein systematischer Versatz
-- (Median -2,7/-4,7 m), aber grosse Streuung (mittlere Distanz 40,2 m). Im Umkreis von
-- 0 bis 5 m tragen dort 18,2 % der Gebaeude eine Waermepumpe, bei einer kantonalen
-- Hintergrundrate von 21,8 % (St. Gallen: 84,4 % gegen 30,4 %). Die Zuordnung traegt
-- in Luzern also keine Information. Der Kanton bleibt in silver_waermenutzung, faellt
-- aber aus den auswertenden Sichten. checks.py sucht weitere Kantone mit diesem Muster.
CREATE OR REPLACE VIEW v_lage_ungenau AS
SELECT unnest(['LU']) AS kanton;

-- Widerspruchsfaelle: fossil beheiztes Wohngebaeude an einer Waermenutzungsanlage, ohne
-- dass eines der zugeordneten Gebaeude eine Waermepumpe eingetragen hat. Anlagenkennung
-- und Zuordnungsweg laufen mit, damit die Gemeinde den Beleg wiederfindet.
CREATE OR REPLACE VIEW v_test5 AS
SELECT m.egid, m.kanton, m.bfs_nr, m.gemeinde, m.baujahr, m.gkat,
       m.energie_klasse, m.quelle_code, m.quelle_txt, m.quelle_datum,
       m.anlagentyp, m.dist_m, m.entnahme_kw, m.datum_bewilligung, m.status,
       m.anlage_id, m.weg AS zuordnungsweg,
       w.anlage_nr, w.laufnummer AS sonde_laufnummer,
       a.gebaeude_im_umkreis
FROM match_waermenutzung m
JOIN silver_waermenutzung w USING (anlage_id)
JOIN v_test5_anlage a USING (anlage_id)
WHERE m.ist_fossil
  AND m.ist_wohngebaeude
  AND m.ist_gebaut
  -- Nur Anlagen, deren Status eine laufende oder entstehende Waermepumpe belegt.
  AND m.belegt_anlage
  AND a.mit_waermepumpe = 0
  AND m.kanton NOT IN (SELECT kanton FROM v_lage_ungenau)
QUALIFY row_number() OVER (PARTITION BY m.egid ORDER BY m.dist_m) = 1;

-- --------------------------------------------------------------------------- Test 6
-- BE, SO, TG, GE, SZ, BL, SG, AI und ZG: Anlage mit Datum und Ausfuehrungsnachweis.
-- Luzern waere ebenfalls datiert, faellt aber ueber v_lage_ungenau heraus.
-- Dieselbe Frage wie in Test 3 mit den Baugesuchen. Hier steht fest, dass gebaut wurde.
CREATE OR REPLACE VIEW v_test6 AS
WITH anlagen AS (
    SELECT a.anlage_id, a.kanton, a.datum_bewilligung, a.bfs_nr, a.gemeinde,
           a.mit_waermepumpe, a.fossil, a.gebaeude_im_umkreis
    FROM v_test5_anlage a
    WHERE a.kanton IN ('BE', 'SO', 'LU', 'TG', 'GE', 'SZ', 'BL', 'SG', 'AI', 'ZG')
      AND a.ist_gebaut
      AND COALESCE(a.status, '') NOT IN ('Konzession erteilt', 'bewilligt oder geplant')
      AND a.datum_bewilligung IS NOT NULL
      AND a.gebaeude_im_umkreis > 0
      AND a.kanton NOT IN (SELECT kanton FROM v_lage_ungenau)
)
SELECT an.anlage_id, an.kanton, an.datum_bewilligung, an.bfs_nr, an.gemeinde,
       an.gebaeude_im_umkreis, an.mit_waermepumpe, an.fossil,
       date_diff('year', an.datum_bewilligung,
                 (SELECT max(stand) FROM silver_gebaeude_ch)) AS alter_jahre,
       CASE
           WHEN an.mit_waermepumpe > 0 THEN 'nachgefuehrt'
           WHEN an.fossil > 0          THEN 'widerspruch_fossil'
           ELSE                             'unklar'
       END AS status_gwr
FROM anlagen an;


-- ------------------------------------------------- Zuerich: Laufnummer als Datumsersatz
-- Das AWEL veroeffentlicht zu seinen 38'553 Erdwaermesonden kein Datum. Ob der Beleg
-- juenger ist als der Registereintrag, laesst sich dort nicht direkt pruefen. Die
-- GBS-Nummer traegt aber eine Laufnummer, die mit der Zeit steigt. Gemessen an
-- Zuercher Neubauten mit Waermepumpe, denen genau eine Sonde im 20-m-Umkreis zugeordnet
-- ist (Median der Laufnummer je Baujahr): 2005 rund 10'200, 2010 rund 10'560, 2015 rund
-- 10'920, 2020 rund 11'340, 2024 rund 11'920, 2026 rund 12'190.
--
-- Zwei Serien: Nummern unter 10'000 ("b 00-1234") gehoeren zu Baujahren bis 2001,
-- Nummern ab 10'000 zu Baujahren ab 2002. Ein Volkszaehlungseintrag vom 29.11.2001 ist
-- damit aelter als jede Sonde der neuen Serie.
--
-- Die Schwelle je Jahr des Registereintrags:
--   bis 2002       10'100: der Serienwechsel, mit Abstand zu den ersten Nummern
--                  (25 % der Sonden an Neubauten 2002 tragen Nummern bis 10'082)
--   2003 bis 2008  die Schwelle des ersten kalibrierten Jahres. In diesen Jahren sind
--                  die Neubau-Perzentile durch spaeter nachgeruestete Sonden verzerrt
--                  (90. Perzentil 2005: 12'554, 2009: 10'934)
--   ab 2009        das 90. Perzentil der Laufnummern an Neubauten dieses Baujahrs,
--                  monoton steigend gemacht, nur Jahre mit mindestens 50 Neubauten
--
-- Liegt die Laufnummer ueber der Schwelle des Eintragsjahrs, wurde die Sonde nach 90 %
-- der Sonden dieses Jahrs nummeriert, also wahrscheinlich nach dem Eintrag. Das ist
-- ein Ersatz und keine amtliche Datierung, die Stufe heisst deshalb "reihenfolge
-- plausibel". Gemessen ist sie nicht, weil der Labelkanton Zug echte Daten publiziert.
CREATE OR REPLACE TABLE gold_laufnummer_kalibrierung AS
WITH eindeutig AS (
    SELECT m.egid, w.laufnummer
    FROM match_waermenutzung m
    JOIN silver_waermenutzung w USING (anlage_id)
    WHERE w.kanton = 'ZH' AND w.anlagentyp = 'erdwaermesonde'
      AND w.laufnummer IS NOT NULL
    QUALIFY count(*) OVER (PARTITION BY m.anlage_id) = 1
),
je_baujahr AS (
    SELECT g.baujahr AS jahr, count(*) AS neubauten,
           quantile_cont(e.laufnummer, 0.9) AS p90
    FROM eindeutig e
    JOIN silver_gebaeude_ch g USING (egid)
    WHERE g.kanton = 'ZH' AND g.energie_klasse = 'waermepumpe'
      AND g.baujahr >= 2009
    GROUP BY 1
    HAVING count(*) >= 50
),
monoton AS (
    SELECT jahr, neubauten, p90,
           max(p90) OVER (ORDER BY jahr ROWS UNBOUNDED PRECEDING) AS schwelle
    FROM je_baujahr
),
erstes AS (SELECT min(jahr) AS jahr FROM monoton),
jahre AS (SELECT unnest(range(1990, 2041)) AS jahr)
SELECT 'ZH' AS kanton, j.jahr,
       CASE WHEN j.jahr <= 2002 THEN 10100
            WHEN j.jahr < (SELECT jahr FROM erstes)
                 THEN (SELECT schwelle FROM monoton ORDER BY jahr LIMIT 1)
            ELSE m.schwelle END                                   AS schwelle,
       m.neubauten, m.p90,
       CASE WHEN j.jahr <= 2002
                 THEN 'Serienwechsel: Nummern ab 10000 erst ab 2002 vergeben'
            WHEN j.jahr < (SELECT jahr FROM erstes)
                 THEN 'Schwelle des ersten kalibrierten Jahres'
            WHEN m.jahr IS NOT NULL
                 THEN '90. Perzentil der Neubauten dieses Baujahrs, monoton'
            ELSE 'nicht kalibriert' END                            AS grundlage
FROM jahre j
LEFT JOIN monoton m USING (jahr)
ORDER BY j.jahr;
