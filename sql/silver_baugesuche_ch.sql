-- Silver-Layer Baugesuche schweizweit (Amtsblattportal).
--
-- 13 Kantone in einem generischen XML-Format. Die einzige Angabe, die fast alle
-- mitliefern, ist die Adresse. Die Zuordnung laeuft deshalb ueber die Adresse, gegen
-- die Eingangstabelle des GWR.
--
-- Die Stichwortliste ist die des Zuercher Strangs (silver_baugesuche.sql), erweitert um
-- Franzoesisch und Italienisch. Sie ist konservativ gehalten: Jeder Fehltreffer wird
-- spaeter ein Verdachtsfall, den eine Gemeinde von Hand prueft.

CREATE OR REPLACE TABLE bronze_baugesuche_ch AS
SELECT * FROM read_json_auto('data/raw/baugesuche_ch.jsonl', format = 'newline_delimited',
                             union_by_name = true, ignore_errors = true);

-- --------------------------------------------------------- Bauherrschaft im Titel
-- Schaffhausen und Wallis stellen die Bauherrschaft in den Titel, vor den
-- Objektbeschrieb und durch ein Semikolon getrennt:
--   "Baugesuch - Muster Hans; Neubau Schleppgaube, Musterdorf"   (erfunden)
-- Der Schnitt entfernt den ersten Abschnitt, wenn er hoechstens 60 Zeichen lang ist
-- und danach mindestens 25 Zeichen uebrig bleiben. Die Laengenbedingung verhindert,
-- dass ein Titel aus zwei kurzen Abschnitten auf einen Rest zusammenschrumpft.
CREATE OR REPLACE MACRO bauherrschaft_schnitt(t) AS
    CASE WHEN regexp_matches(t, '^[^;]{1,60};')
              AND length(regexp_replace(t, '^[^;]{1,60};\s*', '')) >= 25
         THEN regexp_replace(t, '^[^;]{1,60};\s*', '')
         ELSE t END;

-- Der Publikationsvorspann steht vor dem Namen und muss deshalb zuerst weg.
CREATE OR REPLACE MACRO titel_vorspann_weg(titel) AS
    regexp_replace(COALESCE(titel, ''),
        '^(Baugesuch|Baupublikation|Gesuch für Baubewilligung|'
        || 'Kommunale Baugesuchspublikation|Bauprojekt|Domanda di costruzione|'
        || 'Demande d.autorisation de construire)\s*[-–:]\s*', '');

-- Zwei Schnitte, nicht bis zum Stillstand: Ein Titel wie "3 Doppelgaragen mit Carport
-- und Werkstatt; Sanierung Geraeteschuppen, Termen" besteht aus lauter kurzen
-- Abschnitten und verloere sonst das Bauvorhaben. Die Bauherrschaft steht im ersten
-- Abschnitt, der zweite Durchgang ist Reserve. Was danach noch wie ein Name aussieht,
-- zaehlt checks.py.
CREATE OR REPLACE MACRO titel_anonym(titel) AS
    nullif(trim(bauherrschaft_schnitt(
        bauherrschaft_schnitt(titel_vorspann_weg(titel)))), '');

-- Dasselbe fuer den Beschrieb. Bei Mandanten ohne eigenes Beschriebfeld kopiert der
-- Ingest den Titel in den Beschrieb, die Bauherrschaft wandert also mit:
--   "Muster Hans; Neubau von Einfamilienhaus ..., Beispielweg 9, Musterdorf"   (erfunden)
-- Der Schnitt greift nur, wenn der Beschrieb erkennbar aus dem Titel stammt (gleiche
-- erste zwanzig Zeichen). Ein eigener Beschrieb des Amts bleibt unangetastet, er
-- verloere sonst seinen ersten Halbsatz.
CREATE OR REPLACE MACRO beschrieb_anonym(beschrieb, titel) AS
    CASE WHEN beschrieb IS NOT NULL AND titel IS NOT NULL
              AND length(trim(beschrieb)) >= 20
              AND starts_with(titel_vorspann_weg(titel), substr(trim(beschrieb), 1, 20))
         THEN nullif(trim(bauherrschaft_schnitt(
                  bauherrschaft_schnitt(trim(beschrieb)))), '')
         ELSE beschrieb END;

-- --------------------------------------------------------------------- Klassifikation
CREATE OR REPLACE TABLE silver_baugesuche_ch AS
WITH b AS (
    SELECT
        id                                        AS bg_id,
        rubrik,
        kanton,
        TRY_CAST(datum AS DATE)                   AS pub_datum,
        TRY_CAST(COALESCE(bfs_nr, bfs_behoerde) AS INTEGER) AS bfs_nr_roh,
        titel,
        -- Publikations-URL, publizierendes Amt und Parzelle sind die Referenzen, unter
        -- denen eine Bauverwaltung das Gesuch wiederfindet.
        ref                                      AS publikation_url,
        amt                                      AS publizierendes_amt,
        versicherungs_nr,
        beschrieb,
        strasse, hausnummer, plz, ort,
        parzelle, koordinate, adresse_herkunft,
        COALESCE(heizungsbezug, FALSE)            AS titel_oder_text_heizung,
        -- Titel UND Beschrieb durchsuchen: Bei den "titel"-Mandanten steht der
        -- Beschrieb im Titel, bei den "voll"-Mandanten steht im Titel die Adresse.
        lower(strip_accents(COALESCE(titel, '') || ' ' || COALESCE(beschrieb, ''))) AS t
    FROM bronze_baugesuche_ch
    WHERE beschrieb IS NOT NULL OR titel IS NOT NULL
),
flags AS (
    SELECT b.*,
        regexp_matches(t, 'warmepumpe|waermepumpe|warmepumpen|luft[ /-]{0,3}wasser|erdsonde|erdwarmesonde|erdwarme|erdregister|geothermie|sole[ /-]{0,3}wasser|wasser[ /-]{0,3}wasser.{0,15}pumpe|pompe a chaleur|sonde geothermique|pompa di calore|termopompa|sonda geotermica') AS kw_wp,
        regexp_matches(t, 'fernwarme|warmeverbund|warmenetz|anergienetz|energieverbund|fernheiz|chauffage a distance|reseau de chaleur|teleriscaldamento')        AS kw_fw,
        regexp_matches(t, 'pellet|holzschnitzel|stuckholz|holzheizung|holzfeuerung|schnitzelheizung|holzkessel|chauffage au bois|caldaia a legna')                AS kw_holz,
        regexp_matches(t, 'solarthermie|sonnenkollektor|thermische solar|thermischen solar|solaire thermique|solare termico')                                     AS kw_solarth,
        regexp_matches(t, 'gasheizung|gasfeuerung|erdgas|gastherme|gaskessel|gasbrenner|chauffage a gaz|caldaia a gas')                                           AS kw_gas,
        regexp_matches(t, 'olheizung|olfeuerung|oltank|olkessel|olbrenner|heizol|oelheizung|mazout|chaudiere a mazout|caldaia a gasolio|gasolio')                  AS kw_oel,
        regexp_matches(t, 'elektroheizung|elektro-heizung|elektrospeicherheizung|widerstandsheizung|chauffage electrique')                                        AS kw_elektro,
        regexp_matches(t, 'heizungsersatz|heizungssanierung|heizungserneuerung|heizungsanlage|heizzentrale|energiezentrale|warmeerzeug|heizung.{0,12}ersetz|ersatz.{0,12}heizung|neue heizung|heizungsumbau|heizungsinstallation|remplacement.{0,15}chauffage|installation.{0,15}chauffage|sostituzione.{0,15}riscaldamento|impianto di riscaldamento') AS kw_generisch,
        regexp_matches(t, 'leitung|trasse|erschliessung|leitungsbau|rohrleitung|conduite')                  AS kw_leitung,
        regexp_matches(t, 'heizungsraum|heizraum|heizungskeller|local technique')                           AS kw_heizraum,
        regexp_matches(t, 'warmepumpenboiler|wp-boiler|warmwasser.{0,10}warmepumpe|chauffe-eau')            AS kw_wwwp,
        regexp_matches(t, 'neubau|ersatzneubau|abbruch|construction nouvelle|nuova costruzione')            AS kw_neubau,
        regexp_matches(t, 'ersatz|ersetz|sanierung|erneuerung|umbau|umstell|austausch|umrust|statt|remplacement|renovation|sostituzione|risanamento') AS kw_ersatz
    FROM b
)
SELECT
    bg_id, rubrik, kanton, pub_datum, bfs_nr_roh, titel, beschrieb,
    publikation_url, publizierendes_amt, versicherungs_nr,
    -- Anonymisierung von Titel und Beschrieb, Regeln in den Makros oben. Die Regel ist
    -- grob: Wo der erste Abschnitt kein Name ist, geht ein Stueck Beschreibung verloren.
    titel_anonym(titel)                                           AS titel_anonym,
    beschrieb_anonym(beschrieb, titel)                            AS beschrieb_anonym,
    strasse, hausnummer, plz, ort, parzelle, koordinate, adresse_herkunft,
    strasse_norm(strasse) AS strasse_k,
    hausnr_norm(hausnummer) AS hausnr_k,
    -- Entdopplung wie im Zuercher Strang: Ein Vorhaben wird oft mehrfach publiziert.
    -- Gezaehlt werden Vorhaben, nicht Publikationen.
    md5(COALESCE(beschrieb, titel, '') || '|' || COALESCE(kanton, '') || '|'
        || COALESCE(strasse, '') || '|' || COALESCE(hausnummer, ''))  AS vorhaben_id,
    row_number() OVER (
        PARTITION BY COALESCE(beschrieb, titel, ''), COALESCE(kanton, ''),
                     COALESCE(strasse, ''), COALESCE(hausnummer, '')
        ORDER BY pub_datum, bg_id) = 1                                AS ist_erstpublikation,
    kw_wp, kw_fw, kw_holz, kw_solarth, kw_gas, kw_oel, kw_elektro, kw_generisch,
    kw_leitung, kw_neubau, kw_ersatz,
    (kw_fw AND kw_leitung AND NOT kw_wp AND NOT kw_generisch)          AS ist_netzprojekt,
    (kw_heizraum AND NOT (kw_wp OR kw_fw OR kw_holz OR kw_gas OR kw_oel OR kw_generisch))
                                                                       AS ist_raumumnutzung,
    kw_wwwp                                                            AS ist_ww_waermepumpe,
    (kw_wp OR kw_fw OR kw_holz OR kw_solarth OR kw_gas OR kw_oel OR kw_elektro OR kw_generisch)
      AND NOT (kw_fw AND kw_leitung AND NOT kw_wp AND NOT kw_generisch)
      AND NOT (kw_heizraum AND NOT (kw_wp OR kw_fw OR kw_holz OR kw_gas OR kw_oel OR kw_generisch))
                                                                       AS ist_heizungsereignis,
    CASE
        WHEN kw_wp                          THEN 'waermepumpe'
        WHEN kw_fw AND NOT kw_leitung       THEN 'fernwaerme'
        WHEN kw_holz                        THEN 'holz'
        WHEN kw_solarth                     THEN 'solarthermie'
        WHEN kw_generisch                   THEN 'unklar'
        WHEN kw_gas OR kw_oel OR kw_elektro THEN 'unklar'
        ELSE NULL
    END                                                                AS neuer_traeger,
    CASE
        WHEN kw_oel AND kw_gas THEN 'oel_und_gas'
        WHEN kw_oel            THEN 'oel'
        WHEN kw_gas            THEN 'gas'
        WHEN kw_elektro        THEN 'elektro'
        ELSE NULL
    END                                                                AS alter_traeger_genannt
FROM flags;

-- ------------------------------------------------------------------------- Zuordnung
-- Zwei Wege, getrennt gefuehrt:
--   adresse      Strasse + Hausnummer + PLZ gegen die GWR-Eingangstabelle. Der Normalfall.
--   koordinate   Nur Schwyz, Wallis und Bern liefern eine. Dann gilt derselbe 20-m-Umkreis
--                wie bei den Waermenutzungsanlagen, mit derselben Schwaeche.
-- Der Weg bleibt in der Spalte weg sichtbar: Eine Adresszuordnung trifft ein Gebaeude,
-- eine Koordinatenzuordnung eine Nachbarschaft.
CREATE OR REPLACE TABLE match_baugesuche_ch AS
WITH heizung AS (
    SELECT * FROM silver_baugesuche_ch
    WHERE ist_heizungsereignis AND ist_erstpublikation
),
ueber_adresse AS (
    -- Die Eingangstabelle fuehrt auch Adressen abgebrochener, projektierter und im Bau
    -- befindlicher Gebaeude, silver_gebaeude_ch nur bestehende. Deshalb das EXISTS.
    SELECT h.bg_id, a.egid, 'adresse' AS weg, 0.0 AS dist_m
    FROM heizung h
    JOIN silver_adresse_ch a
      ON a.kanton = h.kanton
     AND a.strasse_k = h.strasse_k
     AND a.hausnr_k  = h.hausnr_k
     AND (h.plz IS NULL OR a.plz = h.plz)
    WHERE h.strasse_k <> '' AND h.hausnr_k <> ''
      AND EXISTS (SELECT 1 FROM silver_gebaeude_ch g WHERE g.egid = a.egid)
),
mit_koord AS (
    SELECT bg_id, kanton,
           TRY_CAST(split_part(koordinate, '/', 1) AS DOUBLE) AS e_lv95,
           TRY_CAST(split_part(koordinate, '/', 2) AS DOUBLE) AS n_lv95
    FROM heizung
    WHERE koordinate IS NOT NULL AND koordinate LIKE '%/%'
),
ueber_koordinate AS (
    SELECT k.bg_id, g.egid, 'koordinate' AS weg,
           round(sqrt(pow(k.e_lv95 - g.e_lv95, 2) + pow(k.n_lv95 - g.n_lv95, 2)), 1) AS dist_m
    FROM mit_koord k
    JOIN silver_gebaeude_ch g
      ON g.kanton = k.kanton
     AND g.e_lv95 BETWEEN k.e_lv95 - 20 AND k.e_lv95 + 20
     AND g.n_lv95 BETWEEN k.n_lv95 - 20 AND k.n_lv95 + 20
     AND sqrt(pow(k.e_lv95 - g.e_lv95, 2) + pow(k.n_lv95 - g.n_lv95, 2)) <= 20
    WHERE k.e_lv95 BETWEEN 2480000 AND 2840000
      AND k.n_lv95 BETWEEN 1070000 AND 1300000
),
zusammen AS (
    SELECT * FROM ueber_adresse
    UNION ALL
    SELECT * FROM ueber_koordinate
)
SELECT z.bg_id, z.egid, z.weg, z.dist_m,
       h.kanton, h.pub_datum, h.vorhaben_id, h.neuer_traeger, h.alter_traeger_genannt,
       h.ist_ww_waermepumpe, h.kw_wp, h.kw_fw, h.beschrieb, h.titel,
       h.titel_anonym, h.beschrieb_anonym,
       h.publikation_url, h.publizierendes_amt, h.parzelle, h.versicherungs_nr,
       g.bfs_nr, g.gemeinde, g.energie_klasse, g.ist_fossil, g.ist_wohngebaeude,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.gkat, g.baujahr
FROM zusammen z
JOIN heizung h USING (bg_id)
JOIN silver_gebaeude_ch g USING (egid);

-- ----------------------------------------------------------------------------- Test 3
-- Dieselbe Frage wie im Zuercher Strang: Zeigt das GWR nach einem Heizungsbaugesuch den
-- neuen Energietraeger?
-- Entschieden wird je Baugesuch, nicht je Paar aus Gesuch und Gebaeude. Der
-- Koordinatenweg haengt mehrere Gebaeude an ein Gesuch. Dasselbe Vorhaben wuerde sonst
-- mehrfach gezaehlt und koennte zugleich als nachgefuehrt und nicht nachgefuehrt gelten.
-- Zeigt irgendein Gebaeude im Umkreis den neuen Energietraeger, gilt das Gesuch als
-- nachgefuehrt. Das unterschaetzt den Rueckstand eher.
CREATE OR REPLACE VIEW v_test3_ch AS
WITH paare AS (
    SELECT m.*,
           CASE
               WHEN m.neuer_traeger = 'waermepumpe' AND m.energie_klasse = 'waermepumpe'
                    THEN 'nachgefuehrt'
               WHEN m.neuer_traeger = 'fernwaerme'  AND m.energie_klasse = 'fernwaerme'
                    THEN 'nachgefuehrt'
               WHEN m.neuer_traeger = 'holz'        AND m.energie_klasse = 'holz'
                    THEN 'nachgefuehrt'
               WHEN m.quelle_code = '869' AND m.quelle_datum >= m.pub_datum
                    THEN 'nachgefuehrt'
               WHEN m.neuer_traeger IN ('waermepumpe', 'fernwaerme', 'holz') AND m.ist_fossil
                    THEN 'nicht_nachgefuehrt'
               ELSE 'unklar'
           END AS status_paar
    FROM match_baugesuche_ch m
    -- Sechs Monate, damit die Gemeinde Zeit zum Nachfuehren hatte. Dieselbe Schwelle wie
    -- im Zuercher Strang, damit die Zahlen vergleichbar sind.
    WHERE date_diff('month', m.pub_datum,
                    (SELECT max(stand) FROM silver_gebaeude_ch)) >= 6
      AND m.egid IS NOT NULL
)
SELECT bg_id,
       any_value(kanton)        AS kanton,
       any_value(bfs_nr)        AS bfs_nr,
       any_value(gemeinde)      AS gemeinde,
       any_value(vorhaben_id)   AS vorhaben_id,
       any_value(pub_datum)     AS pub_datum,
       any_value(neuer_traeger) AS neuer_traeger,
       count(DISTINCT egid)     AS gebaeude_im_treffer,
       -- Adresse schlaegt Koordinate, weil sie ein einzelnes Gebaeude meint.
       min(CASE weg WHEN 'adresse' THEN 'adresse' ELSE 'koordinate' END) AS weg,
       date_diff('month', any_value(pub_datum),
                 (SELECT max(stand) FROM silver_gebaeude_ch))            AS alter_monate,
       CASE
           WHEN bool_or(status_paar = 'nachgefuehrt')       THEN 'nachgefuehrt'
           WHEN bool_or(status_paar = 'nicht_nachgefuehrt') THEN 'nicht_nachgefuehrt'
           ELSE 'unklar'
       END                                                               AS status_gwr
FROM paare
GROUP BY bg_id;


-- --------------------------------------------------------- Gebaeudegenau fuer Gold
-- v_test3_ch entscheidet je Baugesuch, der Verdachts-Layer braucht Zeilen je Gebaeude.
-- Uebernommen werden nur Gesuche, die genau ein Gebaeude getroffen haben. Bei mehreren
-- Treffern ist unklar, welches gemeint war. Dieselbe Regel gilt im Zuercher Strang
-- (n_gebaeude = 1).
CREATE OR REPLACE VIEW v_test3_ch_gebaeude AS
SELECT m.egid, t.bg_id, t.kanton, t.pub_datum, t.neuer_traeger, t.weg,
       m.publikation_url, m.publizierendes_amt,
       COALESCE(m.parzelle, m.versicherungs_nr) AS parzelle,
       -- Nie der rohe Titel: Er traegt in Schaffhausen und im Wallis die
       -- Bauherrschaft im Klartext.
       COALESCE(m.beschrieb_anonym, m.titel_anonym) AS beschrieb,
       -- Der Zuercher Strang fuehrt hier ein LLM-Urteil. Fuer die uebrigen Kantone
       -- gibt es keines, der Beleg gilt als reiner Regeltreffer.
       FALSE           AS llm_geprueft,
       NULL::VARCHAR   AS llm_begruendung
FROM v_test3_ch t
JOIN match_baugesuche_ch m USING (bg_id)
WHERE t.status_gwr = 'nicht_nachgefuehrt'
  AND t.gebaeude_im_treffer = 1;
