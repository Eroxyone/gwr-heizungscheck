-- Gold-Layer: ein Verdachtsscore je Gebaeude, aus allen verfuegbaren Belegen
-- (Baugesuch, Waermenutzungsanlage, Photovoltaik, Widerspruch im Registereintrag).
--
-- Der Score ordnet nach Beleglage, er schaetzt keine Wahrscheinlichkeit. Die Gewichte
-- sind an den Labels aus Genf und Zug kalibriert (reports/groundtruth.md,
-- reports/belegwirkung.md), soweit die Belegart dort vorkommt. Das Baugesuch und der
-- Erzeuger-Widerspruch kommen dort nicht vor, ihre Punkte sind gesetzt.

-- --------------------------------------------------------------------------- Belege
-- Leere Auffangsicht, falls kein Gegenbeleg geladen ist. IF NOT EXISTS laesst die
-- echte Sicht aus gegenbeleg_zg.sql stehen.
CREATE VIEW IF NOT EXISTS v_gegenbeleg AS
SELECT NULL::BIGINT AS egid, NULL::VARCHAR AS gegenbeleg_quelle,
       FALSE AS fossil_aktiv, FALSE AS fossil_stillgelegt
WHERE FALSE;

-- Dasselbe fuer den schweizweiten Baugesuch-Abzug: Fehlt er, laeuft der Zuercher Strang
-- allein. Die Spalten muessen denen der echten Sicht in silver_baugesuche_ch.sql
-- entsprechen (geprueft in tests/test_hilfen.py).
CREATE VIEW IF NOT EXISTS v_test3_ch_gebaeude AS
SELECT NULL::BIGINT AS egid, NULL::VARCHAR AS bg_id, NULL::VARCHAR AS kanton,
       NULL::DATE AS pub_datum, NULL::VARCHAR AS neuer_traeger, NULL::VARCHAR AS weg,
       NULL::VARCHAR AS publikation_url, NULL::VARCHAR AS publizierendes_amt,
       NULL::VARCHAR AS parzelle,
       NULL::VARCHAR AS beschrieb, FALSE AS llm_geprueft,
       NULL::VARCHAR AS llm_begruendung
WHERE FALSE;

CREATE OR REPLACE TABLE gold_belege AS
WITH
-- Beleg 1: Heizungs-Baugesuch zugeordnet, im GWR nicht nachgefuehrt. Nennt den neuen
-- Energietraeger und ist datiert. Zwei Straenge: Zuerich aus dem OGD-Datensatz
-- (Parzellenpolygone, LLM-Pruefung), die uebrigen Kantone aus dem Amtsblattportal
-- ueber Adresse oder Koordinate (ohne Parzellengeometrie, ohne LLM-Pruefung).
baugesuch AS (
    SELECT egid,
           count(*) OVER (PARTITION BY egid)           AS n_baugesuche,
           pub_datum                                  AS bg_datum,
           neuer_traeger                              AS bg_neuer_traeger,
           beschrieb                                  AS bg_beschrieb,
           TRUE                                       AS bg_nicht_nachgefuehrt,
           llm_geprueft                                AS bg_llm_geprueft,
           llm_begruendung                             AS bg_llm_begruendung,
           bg_id, bg_quelle, bg_referenz, bg_parzelle, bg_url, bg_weg
    FROM (
        SELECT egid, pub_datum, neuer_traeger, beschrieb,
               llm_geprueft, llm_begruendung, CAST(bg_id AS VARCHAR) AS bg_id,
               'ZH OGD Baugesuche' AS bg_quelle,
               -- Referenz fuers Bauamt ist die Publikationsnummer, die UUID ist intern.
               publikationsnr                   AS bg_referenz,
               CAST(kataster_nr AS VARCHAR)     AS bg_parzelle,
               -- Die ref-URL im Rohabzug zeigt auf die API. Die oeffentliche
               -- Detailseite wird deshalb aus der Kennung gebaut.
               'https://www.amtsblattportal.ch/#!/search/publications/detail/'
                   || CAST(bg_id AS VARCHAR)    AS bg_url,
               CASE WHEN via_geo AND via_adresse THEN 'parzelle_und_adresse'
                    WHEN via_geo THEN 'parzelle' ELSE 'adresse' END AS bg_weg
        FROM v_test3
        WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau AND status='nicht_nachgefuehrt'
        UNION ALL
        SELECT egid, pub_datum, neuer_traeger, beschrieb,
               llm_geprueft, llm_begruendung, CAST(bg_id AS VARCHAR),
               'Amtsblattportal',
               publizierendes_amt, CAST(parzelle AS VARCHAR),
               'https://www.amtsblattportal.ch/#!/search/publications/detail/'
                   || CAST(bg_id AS VARCHAR), weg
        FROM v_test3_ch_gebaeude
    )
    QUALIFY row_number() OVER (PARTITION BY egid ORDER BY pub_datum DESC,
        bg_quelle, bg_id)=1
),
-- Beleg 2: Waermenutzungsanlage am Gebaeude, aber keine Waermepumpe im GWR (v_test5).
-- Sagt direkt etwas ueber die Heizung, ist aber nicht in jedem Kanton datiert.
sonde AS (
    SELECT egid,
           anlagentyp                                 AS sonde_typ,
           dist_m                                     AS sonde_dist_m,
           datum_bewilligung                           AS sonde_datum,
           anlage_id AS sonde_id, anlage_nr AS sonde_nr,
           zuordnungsweg AS sonde_weg, status AS sonde_status,
           sonde_laufnummer
    FROM v_test5
),
-- Beleg 3: Photovoltaikanlage (BFE, alle 26 Kantone). Sagt nichts ueber die Heizung,
-- zeigt nur, dass am Gebaeude in den letzten Jahren etwas gemacht wurde.
pv AS (
    SELECT egid, max(inbetriebnahme) AS pv_datum
    FROM v_solar_gebaeude
    GROUP BY egid
),
-- Beleg 4: Das Register widerspricht sich selbst. Braucht keine externe Quelle und gilt
-- deshalb in allen 26 Kantonen.
--   erzeuger     Waermeerzeuger "Waermepumpe" mit Energietraeger "Heizoel": technisch
--                unmoeglich, also ein Erfassungsfehler. Als einzige Art mit Punkten.
--   fernwaerme, erdwaerme, luft
--                Warmwasser ueber einen anderen Traeger als die fossile Heizung.
widerspruch AS (
    SELECT egid,
        CASE
            WHEN waermeerzeuger_code IN ('7410', '7411')
                 AND energietraeger_code = '7530'                            THEN 'erzeuger'
            WHEN ww_energietraeger_code IN ('7580', '7581', '7582')          THEN 'fernwaerme'
            WHEN ww_energietraeger_code IN ('7510', '7511', '7512', '7513')  THEN 'erdwaerme'
            WHEN ww_energietraeger_code = '7501'                             THEN 'luft'
        END                                                                  AS ws_art,
        ww_quelle_datum                                                      AS ws_datum
    FROM silver_gebaeude_ch
    WHERE ist_wohngebaeude AND ist_fossil
      AND (ww_energietraeger_code IN ('7501', '7510', '7511', '7512', '7513',
                                      '7580', '7581', '7582')
           OR (waermeerzeuger_code IN ('7410', '7411') AND energietraeger_code = '7530'))
)
SELECT
    g.egid, g.kanton, g.bfs_nr, g.gemeinde, g.baujahr,
    -- Koordinate fuer die Pruefliste: Ein Bauamt sucht im GIS, nicht ueber die EGID.
    g.e_lv95, g.n_lv95,
    g.gebaeudekategorie_txt, g.energie_klasse, g.energietraeger_txt,
    g.quelle_code, g.quelle_txt, g.quelle_datum, g.alter_jahre,
    -- Registerstand je Zeile: Das Alter eines Belegs wird am Tag des Abzugs gemessen.
    g.stand,
    -- Belege
    COALESCE(b.bg_nicht_nachgefuehrt, FALSE)           AS hat_baugesuch,
    b.bg_datum, b.bg_neuer_traeger, b.bg_beschrieb, b.n_baugesuche,
    COALESCE(b.bg_llm_geprueft, FALSE)                 AS bg_llm_geprueft,
    b.bg_llm_begruendung,
    b.bg_id, b.bg_quelle, b.bg_referenz, b.bg_parzelle, b.bg_url, b.bg_weg,
    (s.egid IS NOT NULL)                               AS hat_sonde,
    s.sonde_typ, s.sonde_dist_m, s.sonde_datum,
    s.sonde_id, s.sonde_nr, s.sonde_weg, s.sonde_status, s.sonde_laufnummer,
    (p.egid IS NOT NULL)                               AS hat_pv,
    p.pv_datum,
    (w.egid IS NOT NULL)                               AS hat_widerspruch,
    w.ws_art, w.ws_datum,
    -- Gegenbeleg: Laeuft am selben Gebaeude noch eine fossile Heizung? Die einzige
    -- Quelle, die einen Verdacht widerlegen kann. Verfuegbar fuer Genf (Kesselkataster)
    -- und Zug (Oeltankkataster), siehe gegenbeleg_zg.sql.
    COALESCE(f.fossil_aktiv, FALSE)                    AS kessel_aktiv,
    COALESCE(f.fossil_stillgelegt, FALSE)              AS kessel_stillgelegt,
    f.gegenbeleg_quelle
FROM silver_gebaeude_ch g
LEFT JOIN v_gegenbeleg f ON f.egid = g.egid
LEFT JOIN baugesuch   b ON b.egid = g.egid
LEFT JOIN sonde       s ON s.egid = g.egid
LEFT JOIN pv          p ON p.egid = g.egid
LEFT JOIN widerspruch w ON w.egid = g.egid
WHERE g.ist_wohngebaeude
  AND g.ist_fossil                    -- nur fossil Eingetragene koennen veraltet sein
  -- Mindestens ein echter Beleg. Quelle 860 und ein altes Datum heissen nur
  -- "ungeprueft". Ohne diesen Filter stuenden 343'265 Gebaeude auf der Liste, 95 %
  -- davon ohne jeden Beleg (docs/methode.md). Ein Baugesuch zaehlt nur, wenn es
  -- nicht nachgefuehrt ist.
  AND (COALESCE(b.bg_nicht_nachgefuehrt, FALSE) OR s.egid IS NOT NULL
       OR p.egid IS NOT NULL OR w.egid IS NOT NULL);

-- ------------------------------------------------------- Codes des Merkmalskatalogs
-- Code und Klartext des Korrekturvorschlags kommen aus bronze_gwr_kodes, also aus dem
-- Merkmalskatalog des BFS. Ein Code, den es dort nicht gibt, faellt im JOIN heraus.
-- Die Codes von GWAERZH1 sind leicht zu verwechseln: 7410 ist die Waermepumpe, 7430
-- der generische Heizkessel, 7420 die thermische Solaranlage.
CREATE OR REPLACE TABLE gold_vorschlag_kode AS
WITH wahl(klasse, gwaerzh1) AS (
    VALUES ('waermepumpe',  '7410'),     -- Waermepumpe fuer ein Gebaeude
           ('fernwaerme',   '7460'),     -- Waermetauscher, einschliesslich Fernwaerme
           ('holz',         '7430'),     -- Heizkessel (generisch)
           ('solarthermie', '7420')      -- Thermische Solaranlage
)
SELECT w.klasse, w.gwaerzh1,
       'GWAERZH1 ' || w.gwaerzh1 || ' ' || z.CODTXTLD AS gwaerzh1_text
FROM wahl w
JOIN bronze_gwr_kodes z ON z.CMERKM = 'GWAERZH1' AND z.CECODID = w.gwaerzh1;

-- Der Energietraeger haengt an der Waermequelle und nicht an der Klasse: Erdwaermesonde
-- 7511, Grundwasser 7513, Luft 7501. Ist die Quelle unbekannt, bleibt er offen.
CREATE OR REPLACE TABLE gold_traeger_kode AS
WITH wahl(schluessel, genh1) AS (
    VALUES ('erdwaermesonde',     '7511'),
           ('erdregister',        '7512'),
           ('grundwasserfassung', '7513'),
           ('quellfassung',       '7513'),
           ('luft',               '7501'),
           ('fernwaerme',         '7580'),
           ('holz',               '7540'),
           ('solarthermie',       '7570')
)
SELECT w.schluessel, w.genh1,
       'GENH1 ' || w.genh1 || ' ' || e.CODTXTLD AS genh1_text
FROM wahl w
JOIN bronze_gwr_kodes e ON e.CMERKM = 'GENH1' AND e.CECODID = w.genh1;

-- Die Informationsquelle folgt der Herkunft des Belegs: 869 Baubewilligung, 864 Daten
-- des Kantons (Waermenutzungsregister), 865 Daten der Gemeinde.
CREATE OR REPLACE TABLE gold_quelle_kode AS
SELECT CECODID AS code,
       'GWAERSCEH1 ' || CECODID || ' ' || CODTXTLD AS text
FROM bronze_gwr_kodes
WHERE CMERKM = 'GWAERSCEH1' AND CECODID IN ('864', '865', '869');

-- --------------------------------------------------------------------------- Score
-- Zwei Sichten: v_gold_score ohne Filter, v_gold_verdacht mit Gegenbeleg-Filter.
-- Auswertungen gegen die Genfer Labels laufen auf v_gold_score. Der Gegenbeleg-Filter
-- benutzt denselben Kataster, aus dem die Labels stammen, die Messung waere zirkulaer.
CREATE OR REPLACE VIEW v_gold_score AS
-- Gewichte: Gemessen ist, um welchen Faktor eine Belegart die Fehlerquote gegenueber
-- der Grundrate des Kantons anhebt (Labels aus Genf und Zug, reports/groundtruth.md
-- und reports/belegwirkung.md). Die Begruendung steht jeweils am Punktwert.
WITH punkte AS (
    SELECT b.*,
        -- Datum des Belegs. Das Baugesuch ist datiert, die Anlage meistens auch,
        -- ausser in Zuerich: Das AWEL veroeffentlicht kein Bohrdatum.
        COALESCE(bg_datum, sonde_datum)                                 AS beleg_datum,
        -- Ungemessen: In Genf und Zug gibt es keinen zugeordneten Baugesuchsfall, die
        -- Punkte sind eine Annahme.
        CASE WHEN hat_baugesuch AND bg_llm_geprueft THEN 55
             WHEN hat_baugesuch                     THEN 50 ELSE 0 END      AS p_baugesuch,
        -- Pauschal 40 Punkte, ohne Abstufung nach Entfernung. An den Zuger Labels
        -- unterscheiden sich die Distanzklassen nicht (reports/belegwirkung.md):
        --   Zuordnungskaskade            bis 10 m 63,6 % (n=44)   10 bis 20 m 61,5 % (n=65)
        --   Umkreis mit einem Gebaeude   bis 10 m 81,3 % (n=16)   10 bis 20 m 77,1 % (n=35)
        -- Was zaehlt, ist die Eindeutigkeit der Zuordnung, und die stellt v_test5
        -- bereits sicher.
        CASE WHEN hat_sonde THEN 40 ELSE 0 END                              AS p_sonde,
        -- Nur der Untertyp "erzeuger" gibt Punkte. Er kommt in Genf und Zug nicht vor
        -- und ist ungemessen. Die Kombination ist technisch unmoeglich, sagt aber
        -- nicht, welches der beiden Felder falsch ist, deshalb nur 15 Punkte.
        -- Die Warmwasser-Untertypen liegen in Genf unter der Grundrate und geben null:
        -- fernwaerme 4,0 % falsch (Faktor 0,7, n=50), luft und erdwaerme zusammen
        -- 4,4 % (Faktor 0,8, n=90). Die Genfer Fernwaerme-Uebergabestationen dieser
        -- Faelle tragen USAGE = ['ECS'], versorgen also nur das Warmwasser.
        CASE ws_art WHEN 'erzeuger'   THEN 15
                    ELSE 0 END                                              AS p_widerspruch,
        -- Gemessen: Faktor 2 bis 3 gegenueber der Grundrate (Genf und Zug).
        CASE WHEN hat_pv THEN 18 ELSE 0 END                                 AS p_pv,
        -- Merkmale des Eintrags selbst. Quelle und Alter haengen stark zusammen. Im
        -- gemeinsamen Modell traegt das Alter das Signal, deshalb wiegt es mehr.
        CASE WHEN quelle_code = '860'      THEN 12 ELSE 0 END               AS p_quelle,
        CASE WHEN alter_jahre >= 20        THEN 15
             WHEN alter_jahre >= 15        THEN 8
             WHEN quelle_datum IS NULL     THEN 6  ELSE 0 END               AS p_alter,
        -- Baujahr: gemessen ohne Signal (Faktor 0,94, docs/methode.md), null Punkte.
        0                                                                   AS p_baujahr,
        -- Zuerich: die Laufnummer der Sonde gegen die Schwelle des Eintragsjahrs.
        -- Herleitung und Grenzen stehen bei gold_laufnummer_kalibrierung (test5.sql).
        k.schwelle                                                          AS lauf_schwelle,
        -- Alter des Belegs am Tag des Registerabzugs. Unter 18 Monaten kann der Fall
        -- noch in der ordentlichen Nachfuehrung stecken: Bern kennt seit 2023 eine
        -- Meldepflicht fuer den Heizungsersatz ueber eBau, Zuerich seit 2023 das
        -- Meldeverfahren fuer Waermepumpen, und ein Bauamt traegt bei der Abnahme
        -- nach, nicht bei der Bewilligung. Die Faelle bleiben, gekennzeichnet.
        date_diff('month', COALESCE(bg_datum, sonde_datum), stand)         AS beleg_alter_monate,
        (COALESCE(bg_datum, sonde_datum) IS NOT NULL
         AND date_diff('month', COALESCE(bg_datum, sonde_datum), stand) < 18) AS im_nachlauf
    FROM gold_belege b
    LEFT JOIN gold_laufnummer_kalibrierung k
           ON k.kanton = b.kanton AND k.jahr = extract(year FROM b.quelle_datum)
),
-- Die Klasse steht in einer eigenen Stufe, damit die Codetabellen dagegen joinen
-- koennen und die Ableitung nur einmal dasteht.
klassen AS (
    SELECT *,
        COALESCE(
            CASE WHEN hat_baugesuch AND bg_neuer_traeger IS NOT NULL
                      AND bg_neuer_traeger <> 'unklar' THEN bg_neuer_traeger END,
            CASE WHEN hat_sonde THEN CASE WHEN sonde_typ = 'fernwaermeanschluss'
                 THEN 'fernwaerme' ELSE 'waermepumpe' END END,
            CASE ws_art WHEN 'fernwaerme' THEN 'fernwaerme'
                        WHEN 'erdwaerme'  THEN 'waermepumpe'
                        WHEN 'erzeuger'   THEN 'waermepumpe' END,
            'pruefen') AS vorschlag_klasse,
        -- Waermequelle: bei einer zugeordneten Anlage aus den Daten, bei einem
        -- Baugesuch aus dem Text ("Luft-/Wasser-Waermepumpe", "Erdsonden-Waermepumpe").
        CASE
            WHEN sonde_typ IS NOT NULL AND sonde_typ <> 'waermepumpe' THEN sonde_typ
            WHEN regexp_matches(lower(COALESCE(bg_beschrieb, '')),
                 'erdsonde|erdwärmesonde|erdwaermesonde|erdsonden')  THEN 'erdwaermesonde'
            WHEN regexp_matches(lower(COALESCE(bg_beschrieb, '')),
                 'grundwasser|wasser[ /-]{0,3}wasser')               THEN 'grundwasserfassung'
            WHEN regexp_matches(lower(COALESCE(bg_beschrieb, '')),
                 'luft[ /-]{0,3}wasser|luftwasser|aussenaufgestellt|'
                 || 'aussen aufgestellt|aussengerät|aussenaufstellung')  THEN 'luft'
        END AS waermequelle
    FROM punkte
)
SELECT k.* EXCLUDE (vorschlag_klasse, waermequelle),
    LEAST(100, p_baugesuch + p_sonde + p_widerspruch + p_pv
             + p_quelle + p_alter + p_baujahr)                              AS score,
    -- Stufen. Am staerksten trennt die Reihenfolge von Beleg und Registereintrag,
    -- staerker als Belegart oder Entfernung. Wo kein Belegdatum vorliegt, dient das
    -- Alter des Eintrags als Stellvertreter: Quelle 860 oder Stand aelter als 15 Jahre.
    -- Fuer sich allein ist dieses Merkmal kein Beleg, erst zusammen mit einem.
    CASE
        -- COALESCE ist noetig: ws_art ist meist NULL, und FALSE OR FALSE OR NULL
        -- ergibt NULL statt FALSE. Ohne COALESCE greift dieser Zweig nie fuer Faelle
        -- ohne Registerwiderspruch, und reine Photovoltaikfaelle rutschen weiter.
        WHEN NOT (hat_baugesuch OR hat_sonde OR COALESCE(ws_art, '') = 'erzeuger') THEN
            CASE WHEN hat_pv THEN 'nur Solaranlage' ELSE 'nur Metadaten' END
        -- Ist der Beleg juenger als der Registereintrag? Zuger Labels
        -- (reports/belegwirkung.md):
        --   Beleg nach dem Eintrag    80,8 % falsch   n=78
        --   Beleg vor dem Eintrag     13,3 % falsch   n=30
        --   Grundrate im Kanton        8,8 %
        -- Steht nach der Bohrung weiterhin Heizoel im spaeter gesetzten Eintrag, hat
        -- jemand den fossilen Traeger bestaetigt.
        WHEN beleg_datum IS NOT NULL AND quelle_datum IS NOT NULL
             AND beleg_datum >  quelle_datum                THEN 'reihenfolge belegt'
        WHEN beleg_datum IS NOT NULL AND quelle_datum IS NOT NULL
                                                            THEN 'beleg vor eintrag'
        -- Undatiert, aber nummeriert: Liegt die Laufnummer der Zuercher Sonde ueber
        -- der kalibrierten Schwelle des Eintragsjahrs, ist die Reihenfolge plausibel,
        -- aber weder belegt noch gemessen. Deshalb eine eigene Stufe.
        WHEN beleg_datum IS NULL AND sonde_laufnummer IS NOT NULL
             AND lauf_schwelle IS NOT NULL
             AND sonde_laufnummer > lauf_schwelle               THEN 'reihenfolge plausibel'
        -- Undatiert und ohne Laufnummer-Befund: Alter des Eintrags als Stellvertreter.
        WHEN quelle_code = '860' OR alter_jahre >= 15       THEN 'eintrag alt'
        ELSE                                                     'eintrag jung'
    END AS konfidenz,
    -- Korrekturvorschlag: Code und Klartext aus gold_vorschlag_kode.
    k.vorschlag_klasse,
    -- GENH1 (Energietraeger) und GWAERZH1 (Waermeerzeuger) muessen beide geaendert
    -- werden, sonst widerspricht sich der Eintrag danach selbst.
    CASE
        WHEN w.gwaerzh1_text IS NULL THEN 'offen - bitte vor Ort klären'
        WHEN t.genh1_text IS NOT NULL THEN t.genh1_text || ', ' || w.gwaerzh1_text
        -- Waermepumpe ohne bekannte Quelle: Der Erzeuger steht fest, der Traeger
        -- bleibt offen. 7501 und 7511 sind verschiedene Anlagen.
        ELSE 'GENH1 offen - Wärmequelle vor Ort klären (7501 Luft, 7511 Erdwärmesonde, '
             || '7513 Wasser), ' || w.gwaerzh1_text
    END AS vorschlag,
    -- Die Informationsquelle wird mitgeaendert, sie folgt der Herkunft des Belegs.
    q.text AS vorschlag_quelle,
    -- Belegtext: ein Satz je Beleg, als Begruendung fuer den Platz auf der Liste.
    trim(concat_ws(' ',
        CASE WHEN hat_baugesuch THEN
            'Baugesuch vom ' || strftime(bg_datum, '%d.%m.%Y') || ': "'
            || CASE WHEN length(bg_beschrieb) > 110
                    THEN substr(bg_beschrieb, 1, 110) || '...' ELSE bg_beschrieb END || '".'
        END,
        CASE WHEN hat_sonde THEN
            'Registrierte ' || replace(sonde_typ, 'erdwaermesonde', 'Erdwärmesonde')
            || ' in ' || CAST(CAST(sonde_dist_m AS INTEGER) AS VARCHAR) || ' m Entfernung'
            || COALESCE(', bewilligt ' || strftime(sonde_datum, '%Y'), '')
            || CASE WHEN sonde_datum IS NULL AND sonde_laufnummer IS NOT NULL
                         AND lauf_schwelle IS NOT NULL AND sonde_laufnummer > lauf_schwelle
                    THEN ', Laufnummer ' || CAST(sonde_laufnummer AS VARCHAR)
                         || ' (nach Kalibrierung vergeben nach dem Registereintrag)'
                    ELSE '' END
            || '.'
        END,
        CASE ws_art
            WHEN 'erzeuger' THEN
                'Das Register widerspricht sich selbst: als Wärmeerzeuger ist eine '
                || 'Wärmepumpe eingetragen, als Energieträger aber Heizöl.'
            WHEN 'fernwaerme' THEN
                'Das Warmwasser läuft laut Register über Fernwärme'
                || COALESCE(' (Stand ' || strftime(ws_datum, '%Y') || ')', '')
                || ', die Heizung steht weiterhin auf ' || energietraeger_txt || '.'
            WHEN 'erdwaerme' THEN
                'Das Warmwasser läuft laut Register über Erdwärme oder Grundwasser'
                || COALESCE(' (Stand ' || strftime(ws_datum, '%Y') || ')', '')
                || ', die Heizung steht weiterhin auf ' || energietraeger_txt || '.'
            WHEN 'luft' THEN
                'Das Warmwasser läuft laut Register über eine Luft-Wärmepumpe.'
        END,
        CASE WHEN hat_pv THEN
            'Photovoltaikanlage seit ' || strftime(pv_datum, '%Y') || '.'
        END,
        CASE WHEN bg_llm_geprueft AND bg_llm_begruendung IS NOT NULL THEN
            '(Textprüfung: ' || bg_llm_begruendung || ')'
        END
    )) AS beleg_text
FROM klassen k
LEFT JOIN gold_vorschlag_kode w ON w.klasse = k.vorschlag_klasse
-- Schluessel fuer den Traeger: bei einer Waermepumpe die Waermequelle, sonst die Klasse.
LEFT JOIN gold_traeger_kode t
       ON t.schluessel = CASE WHEN k.vorschlag_klasse = 'waermepumpe'
                              THEN k.waermequelle ELSE k.vorschlag_klasse END
LEFT JOIN gold_quelle_kode q
       ON q.code = CASE WHEN k.hat_baugesuch THEN '869'      -- Baubewilligung
                        WHEN k.hat_sonde     THEN '864'      -- kantonale Daten
                        ELSE                      '865' END; -- Daten der Gemeinde

-- Die Listensicht: derselbe Score, ohne die Faelle, die ein Gegenbeleg widerlegt (am
-- Gebaeude laeuft noch eine fossile Heizung). Sie bleiben in gold_belege und
-- v_gold_score, sonst liesse sich die Wirkung des Filters nicht messen. "In Reserve"
-- zaehlt nicht als Gegenbeleg: Ein Spitzenlastkessel gehoert zu einer Hybridanlage.
CREATE OR REPLACE VIEW v_gold_verdacht AS
SELECT * FROM v_gold_score WHERE NOT kessel_aktiv;

-- ------------------------------------------------------------------ Was auf die Liste kommt
-- v_gold_verdacht besteht zum allergroessten Teil aus Faellen, die allein auf einer
-- Photovoltaikanlage beruhen. Deren Trefferquote liegt bei 13,7 % (Genf) und 17,2 %
-- (Zug): ueber der Grundrate, aber zu tief fuer eine Liste, die jemand abarbeitet.
-- Auf die Liste kommt deshalb nur, was auf einem Beleg zur Heizung beruht: Baugesuch,
-- Waermenutzungsanlage am Gebaeude oder Erzeuger-Widerspruch.
CREATE OR REPLACE VIEW v_gold_liste AS
SELECT * FROM v_gold_verdacht
-- 'beleg vor eintrag' fehlt mit Absicht: in Zug zu 13,3 % zutreffend (n=30), kaum
-- ueber der Grundrate von 8,8 %.
WHERE konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel',
                    'eintrag alt', 'eintrag jung');

-- --------------------------------------------------------------------------- Aggregat
CREATE OR REPLACE TABLE gold_verdacht_gemeinde AS
SELECT kanton, bfs_nr, gemeinde,
       count(*)                                                    AS verdachtsfaelle,
       count(*) FILTER (WHERE konfidenz = 'reihenfolge belegt') AS konfidenz_hoch,
       count(*) FILTER (WHERE konfidenz = 'reihenfolge plausibel') AS konfidenz_plausibel,
       count(*) FILTER (WHERE konfidenz IN ('eintrag alt',
                                            'eintrag jung'))       AS konfidenz_mittel,
       count(*) FILTER (WHERE konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel',
                                            'eintrag alt', 'eintrag jung')) AS auf_der_liste,
       count(*) FILTER (WHERE konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel',
                                            'eintrag alt', 'eintrag jung')
                          AND im_nachlauf)                         AS im_nachlauf,
       count(*) FILTER (WHERE hat_baugesuch)                       AS mit_baugesuch,
       count(*) FILTER (WHERE hat_sonde)                           AS mit_sonde,
       count(*) FILTER (WHERE hat_widerspruch)                     AS mit_widerspruch,
       count(*) FILTER (WHERE hat_pv)                              AS mit_pv,
       round(avg(score), 1)                                        AS score_mittel,
       max(score)                                                  AS score_max
FROM v_gold_verdacht
GROUP BY 1, 2, 3;

-- ------------------------------------------------------------------ Archiv der Verdachtsliste
-- Der Gold-Layer wird mit jedem Snapshot neu gerechnet, und ein Fall verlaesst die
-- Liste, sobald das Register ihn nicht mehr fossil fuehrt. Das Archiv haelt je
-- Registerstand einmal fest, was auf der Liste stand, damit sich spaetere Korrekturen
-- im Register gegen die Liste halten lassen. Ein Stand wird nie ueberschrieben.
CREATE TABLE IF NOT EXISTS gold_liste_archiv AS
SELECT stand, egid, kanton, bfs_nr, gemeinde, konfidenz, vorschlag,
       energietraeger_txt, quelle_code, quelle_datum, hat_baugesuch, hat_sonde, im_nachlauf
FROM v_gold_liste WHERE 1 = 0;

INSERT INTO gold_liste_archiv
SELECT stand, egid, kanton, bfs_nr, gemeinde, konfidenz, vorschlag,
       energietraeger_txt, quelle_code, quelle_datum, hat_baugesuch, hat_sonde, im_nachlauf
FROM v_gold_liste v
WHERE NOT EXISTS (SELECT 1 FROM gold_liste_archiv a WHERE a.stand = v.stand);

-- Was seit einem archivierten Stand im Register korrigiert wurde: je Fall der erste
-- juengere Snapshot, in dem der Energietraeger nicht mehr fossil ist. vorschlag_trifft
-- vergleicht den Vorschlag mit genh1_neu, misst also an tatsaechlichen Korrekturen.
CREATE OR REPLACE VIEW v_gold_liste_korrigiert AS
WITH s AS (
    SELECT kanton, snapshot_date, EGID AS egid,
           GENH1::VARCHAR AS genh1_neu, GWAERSCEH1::VARCHAR AS quelle_neu,
           TRY_CAST(GWAERDATH1 AS DATE) AS datum_neu
    FROM bronze_gwr_snapshots
),
erster AS (
    SELECT a.stand AS listenstand, a.egid, a.kanton, a.bfs_nr, a.gemeinde, a.konfidenz,
           a.vorschlag, a.energietraeger_txt AS traeger_alt, a.hat_baugesuch, a.hat_sonde,
           min(s.snapshot_date)                  AS korrigiert_am,
           arg_min(s.genh1_neu, s.snapshot_date) AS genh1_neu,
           arg_min(s.quelle_neu, s.snapshot_date) AS quelle_neu,
           arg_min(s.datum_neu, s.snapshot_date) AS datum_neu
    FROM gold_liste_archiv a
    JOIN s ON s.egid = a.egid AND s.kanton = a.kanton
    WHERE s.snapshot_date > a.stand
      AND s.genh1_neu NOT IN ('7520', '7530')
    GROUP BY a.stand, a.egid, a.kanton, a.bfs_nr, a.gemeinde, a.konfidenz,
             a.vorschlag, a.energietraeger_txt, a.hat_baugesuch, a.hat_sonde
)
-- Trifft der Vorschlag? Er nennt den GENH1-Code als erstes Wort.
SELECT *, regexp_extract(vorschlag, 'GENH1 (\d+)', 1) = genh1_neu AS vorschlag_trifft
FROM erster;
