-- Der Feuerungskataster des Kantons Genf: die Gegenrichtung.
--
-- Die uebrigen Quellen zeigen, dass eine Waermepumpe gebaut, eine Sonde gebohrt oder ein
-- Baugesuch publiziert wurde. Keine davon sagt, ob die alte Oelheizung noch laeuft. Der
-- Kanton Genf fuehrt als einziger einen offenen Feuerungskataster mit EGID: 55'378
-- Kessel mit Brennstoff, Betriebszustand, Verwendungszweck und Baujahr.
--
-- Der Betriebszustand ist feiner als "an oder aus":
--   Active                   laeuft -> widerlegt den Verdacht
--   En reserve               Spitzenlast- oder Notkessel neben einer Waermepumpe, der
--                            Normalfall einer Hybridanlage. Stuetzt und widerlegt nichts.
--   < 100h de service        praktisch stillgelegt, aber nicht abgemeldet
--   Inactive (Hors service)  stillgelegt -> stuetzt den Verdacht

CREATE OR REPLACE TABLE silver_feuerung_ge AS
SELECT TRY_CAST(EGID AS BIGINT)                        AS egid,
       CAST(CODEICF AS VARCHAR)                        AS kessel_nr,
       LIBELLE_COMBUSTIBLE                             AS brennstoff,
       TYPE_INSTALLATION                               AS verwendung,
       ETAT_INSTALLATION                               AS zustand,
       TRY_CAST(ANNEE_CHAUDIERE AS INTEGER)            AS jahr_kessel,
       TRY_CAST(PUISS_NOM_CHAUDIERE AS DOUBLE)         AS leistung_kw,
       -- HEL ist "huile extra legere", also Heizoel. Bois a/b/c ist Holz, Solaire und
       -- Geothermie sind erneuerbar, Electricite ist ein Elektroeinsatz.
       LIBELLE_COMBUSTIBLE IN ('Gaz', 'HEL', 'Huile Lourde', 'Charbon', 'GPL')
                                                       AS ist_fossil,
       COALESCE(TYPE_INSTALLATION, '') IN ('Chauffage', 'Chauffage-eau chaude')
                                                       AS heizt_gebaeude
FROM st_read('data/raw/waermenutzung_weitere/GE_feuerungen.json')
WHERE TRY_CAST(EGID AS BIGINT) IS NOT NULL;

-- Je Gebaeude die schaerfste Aussage, die der Kataster hergibt.
CREATE OR REPLACE VIEW v_feuerung_ge AS
SELECT egid,
       count(*)                                                     AS kessel,
       bool_or(ist_fossil AND heizt_gebaeude AND zustand = 'Active') AS fossil_aktiv,
       bool_or(ist_fossil AND heizt_gebaeude
               AND zustand IN ('En réserve', '< 100h de service'))   AS fossil_reserve,
       bool_or(ist_fossil AND heizt_gebaeude
               AND zustand = 'Inactive (Hors service)')              AS fossil_stillgelegt,
       bool_or(NOT ist_fossil AND heizt_gebaeude AND zustand = 'Active')
                                                                     AS erneuerbar_aktiv,
       max(CASE WHEN ist_fossil AND heizt_gebaeude THEN jahr_kessel END)
                                                                     AS juengster_fossiler_kessel
FROM silver_feuerung_ge
GROUP BY egid;
