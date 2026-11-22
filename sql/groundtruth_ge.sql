-- Genf als Label-Datensatz: Was heizt dieses Gebaeude tatsaechlich?
--
-- Ein fehlender Kesseleintrag belegt keinen falschen Registereintrag, das Gebaeude kann
-- auch nicht erfasst sein. Genf fuehrt als einziger Kanton den Waermeerzeuger je
-- Gebaeude: OCEN_INSTAL_PROD_CHALEUR_PUB, 61'895 Anlagen mit EGID, Anlagenart und
-- Energiequelle, darunter 9'615 Waermepumpen und 3'181 Fernwaerme-Uebergabestationen.
--
-- Die Labels stammen aus diesem Layer und nicht aus dem Kesselkataster
-- (SCANE_CHAUDIERE). Der kennt nur Feuerungen: Ein Gebaeude, das von Oel auf Fernwaerme
-- oder Waermepumpe gewechselt hat, sieht dort aus wie "nicht erfasst". Der
-- Kesselkataster bleibt geladen, weil er den Betriebszustand traegt (aktiv, Reserve,
-- stillgelegt), den dieser Layer nicht hat.

CREATE OR REPLACE TABLE silver_waermeerzeuger_ge AS
SELECT TRY_CAST(EGID AS BIGINT)          AS egid,
       TYPE_INSTALLATION                 AS anlagenart,
       SOURCE_ENERGIE                    AS energiequelle,
       USAGE                             AS verwendung,
       CAST(CODEICF AS VARCHAR)          AS kessel_nr,
       COMMUNE                           AS gemeinde_txt,
       -- Aus der Anlagenart die Klasse ableiten, in der Sprache des GWR.
       CASE
           WHEN TYPE_INSTALLATION = 'Pompe à chaleur'              THEN 'waermepumpe'
           WHEN TYPE_INSTALLATION = 'Echangeur de chaleur (CAD)'   THEN 'fernwaerme'
           WHEN TYPE_INSTALLATION = 'Chaudière bois'               THEN 'holz'
           WHEN TYPE_INSTALLATION = 'Poele'                        THEN 'holz'
           WHEN TYPE_INSTALLATION = 'Chaudière gaz'                THEN 'gas'
           WHEN TYPE_INSTALLATION = 'Chaudière mazout'             THEN 'oel'
           WHEN TYPE_INSTALLATION = 'Solaire thermique'            THEN 'solarthermie'
           WHEN TYPE_INSTALLATION IN ('Chauffage électrique', 'Boiler électrique')
                                                                   THEN 'elektro'
           ELSE                                                         'andere'
       END                               AS klasse,
       -- Hauptwaermeerzeuger, mit drei Ausschluessen:
       -- 1. Solarthermie und Elektroboiler stehen fast immer neben der Hauptheizung.
       -- 2. Anlagen, die laut USAGE nur das Warmwasser machen (['ECS'] = eau chaude
       --    sanitaire), etwa Waermepumpenboiler neben der Oelheizung. Der Score gibt
       --    dieser Konstellation keine Punkte (p_widerspruch), sie darf hier kein
       --    Traegerwechsel-Label erzeugen.
       -- 3. Der Ofen ('Poele'): Ein Schwedenofen ist keine Zentralheizung.
       (TYPE_INSTALLATION NOT IN ('Solaire thermique', 'Boiler électrique', 'Poele')
        AND CAST(USAGE AS VARCHAR) <> '[ECS]'
        AND CAST(USAGE AS VARCHAR) <> '[''ECS'']')
                                         AS ist_hauptheizung
FROM st_read('data/raw/waermenutzung_weitere/GE_waermeerzeuger.json')
WHERE TRY_CAST(EGID AS BIGINT) IS NOT NULL;

-- --------------------------------------------------------------- Kessel je Gebaeude
-- Der Kesselkataster sagt, ob eine Feuerung noch laeuft. Zwei Zuordnungswege, beide
-- gelten: die eigene EGID des Kessels und die Beziehungstabelle fuer mitversorgte
-- Gebaeude.
CREATE OR REPLACE TABLE bronze_ge_relation AS
SELECT TRY_CAST(EGID_CHAUDIERE AS BIGINT) AS egid_kessel,
       TRY_CAST(EGID_BATIMENT AS BIGINT)  AS egid_gebaeude,
       CAST(CODE_ICF AS VARCHAR)          AS kessel_nr
FROM st_read('data/raw/waermenutzung_weitere/GE_kessel_gebaeude.json')
WHERE TRY_CAST(EGID_BATIMENT AS BIGINT) IS NOT NULL;

CREATE OR REPLACE TABLE match_feuerung_ge AS
SELECT f.egid AS egid, f.kessel_nr, 'direkt' AS weg,
       f.brennstoff, f.verwendung, f.zustand, f.jahr_kessel, f.leistung_kw,
       f.ist_fossil, f.heizt_gebaeude
FROM silver_feuerung_ge f
UNION
SELECT r.egid_gebaeude AS egid, f.kessel_nr, 'versorgt' AS weg,
       f.brennstoff, f.verwendung, f.zustand, f.jahr_kessel, f.leistung_kw,
       f.ist_fossil, f.heizt_gebaeude
FROM bronze_ge_relation r
JOIN silver_feuerung_ge f USING (kessel_nr);

-- --------------------------------------------------------------- Was laeuft wirklich
CREATE OR REPLACE VIEW v_ge_istzustand AS
SELECT COALESCE(w.egid, k.egid) AS egid,
       w.arten, w.klassen, w.hat_waermepumpe, w.hat_fernwaerme, w.hat_holz,
       w.hat_oel, w.hat_gas, w.hat_elektro, w.n_hauptheizungen,
       k.kessel, k.fossil_aktiv, k.fossil_stillgelegt, k.fossil_reserve,
       k.juengster_fossiler
FROM (
    SELECT egid,
           string_agg(DISTINCT anlagenart, ', ')                        AS arten,
           string_agg(DISTINCT klasse, ', ')                            AS klassen,
           count(*) FILTER (WHERE ist_hauptheizung)                     AS n_hauptheizungen,
           bool_or(klasse = 'waermepumpe'  AND ist_hauptheizung)        AS hat_waermepumpe,
           bool_or(klasse = 'fernwaerme'   AND ist_hauptheizung)        AS hat_fernwaerme,
           bool_or(klasse = 'holz'         AND ist_hauptheizung)        AS hat_holz,
           bool_or(klasse = 'oel'          AND ist_hauptheizung)        AS hat_oel,
           bool_or(klasse = 'gas'          AND ist_hauptheizung)        AS hat_gas,
           bool_or(klasse = 'elektro'      AND ist_hauptheizung)        AS hat_elektro
    FROM silver_waermeerzeuger_ge GROUP BY egid
) w
FULL JOIN (
    SELECT egid, count(*) AS kessel,
           bool_or(heizt_gebaeude AND zustand = 'Active' AND ist_fossil)
                                                                        AS fossil_aktiv,
           bool_or(heizt_gebaeude AND ist_fossil
                   AND zustand = 'Inactive (Hors service)')             AS fossil_stillgelegt,
           bool_or(heizt_gebaeude AND ist_fossil
                   AND zustand IN ('En réserve', '< 100h de service'))  AS fossil_reserve,
           max(CASE WHEN heizt_gebaeude AND ist_fossil THEN jahr_kessel END)
                                                                        AS juengster_fossiler
    FROM match_feuerung_ge GROUP BY egid
) k USING (egid);

-- ------------------------------------------------------------------------- Die Labels
-- Die Reihenfolge der Faelle ist entscheidend, weil ein Gebaeude mehrere Waermeerzeuger
-- haben kann.
CREATE OR REPLACE VIEW v_ge_label AS
SELECT g.egid, g.bfs_nr, g.gemeinde, g.baujahr, g.gkat, g.energie_klasse,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.alter_jahre,
       i.arten, i.klassen, i.n_hauptheizungen,
       i.hat_waermepumpe, i.hat_fernwaerme, i.hat_holz, i.hat_oel, i.hat_gas,
       i.fossil_aktiv, i.fossil_stillgelegt, i.fossil_reserve, i.juengster_fossiler,
       CASE
           -- Keine Aussage moeglich: Das Gebaeude kommt in keiner Genfer Quelle vor,
           -- oder es ist erfasst, aber ohne Hauptwaermeerzeuger und ohne Kessel.
           WHEN i.egid IS NULL
                OR (COALESCE(i.n_hauptheizungen, 0) = 0
                    AND i.kessel IS NULL)                        THEN 'ungeklaert'
           -- Der Eintrag stimmt: derselbe Traeger ist als Hauptheizung gefuehrt
           WHEN g.energie_klasse = 'oel' AND i.hat_oel           THEN 'stimmt'
           WHEN g.energie_klasse = 'gas' AND i.hat_gas           THEN 'stimmt'
           -- Hybrid: fossil und erneuerbar zugleich gefuehrt. Beide Eintraege koennen
           -- zutreffen, deshalb eine eigene Klasse ausserhalb der Quoten.
           WHEN (i.hat_oel OR i.hat_gas)
                AND (i.hat_waermepumpe OR i.hat_fernwaerme OR i.hat_holz)
                                                                 THEN 'hybrid'
           -- Falscher fossiler Traeger: immer noch fossil, aber der andere
           WHEN i.hat_oel OR i.hat_gas                           THEN 'falscher_traeger'
           -- Der gesuchte Fall: kein fossiler Erzeuger mehr, dafuer ein erneuerbarer
           -- oder ein Fernwaermeanschluss.
           WHEN i.hat_waermepumpe                                THEN 'veraltet_waermepumpe'
           WHEN i.hat_fernwaerme                                 THEN 'veraltet_fernwaerme'
           WHEN i.hat_holz                                       THEN 'veraltet_holz'
           -- Nur noch eine Elektroheizung, oder nur der Kesselkataster mit
           -- stillgelegter Feuerung: wahrscheinlich veraltet, neuer Traeger unbekannt.
           WHEN i.hat_elektro                                    THEN 'veraltet_elektro'
           WHEN i.fossil_aktiv                                   THEN 'stimmt'
           WHEN i.fossil_stillgelegt                             THEN 'veraltet_stillgelegt'
           ELSE                                                       'ungeklaert'
       END AS label
FROM silver_gebaeude_ch g
LEFT JOIN v_ge_istzustand i USING (egid)
WHERE g.kanton = 'GE' AND g.ist_wohngebaeude AND g.ist_fossil;

-- Die auswertbare Teilmenge. Hybrid und ungeklaert fallen heraus, beide erlauben keine
-- Aussage.
CREATE OR REPLACE VIEW v_ge_label_klar AS
SELECT *, label <> 'stimmt' AS eintrag_falsch,
       -- Sicherheit des Labels: Wo ein anderer Waermeerzeuger gefuehrt ist, steht der
       -- Fehler fest. Wo nur die Stilllegung der Feuerung bekannt ist, ist er
       -- erschlossen.
       CASE WHEN label = 'veraltet_stillgelegt' THEN 'stilllegungsproxy'
            ELSE 'direkter_vergleich' END AS label_sicherheit
FROM v_ge_label
WHERE label NOT IN ('ungeklaert', 'hybrid');

-- Nur die direkt beobachteten Faelle.
CREATE OR REPLACE VIEW v_ge_label_strikt AS
SELECT * FROM v_ge_label_klar WHERE label_sicherheit = 'direkter_vergleich';
