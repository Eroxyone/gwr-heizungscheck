-- Silver-Layer Baugesuche: Normalisierung + Stichwort-Klassifikation der Heizungsereignisse.
-- Bewusst konservativ: lieber ein paar Treffer verlieren als viele Fehltreffer einsammeln.

CREATE OR REPLACE TABLE silver_baugesuche AS
WITH b AS (
    SELECT
        id                                                      AS bg_id,
        publicationNumber                                       AS publikationsnr,
        TRY_CAST(publicationDate AS DATE)                       AS pub_datum,
        TRY_CAST(bfs_nr AS INTEGER)                             AS bfs_nr_roh,
        municipality_name                                       AS gemeinde_txt,
        -- Anonymisierung. Der Zuercher OGD-Datensatz gilt als personendatenfrei. Eine
        -- Gemeinde haengt aber die Bauherrschaft mit "K Nachname Vorname" an den
        -- Objektbeschrieb an:
        --   "2025-000 Wärmepumpe (aussen aufgestellt), GS 00, Musterweg 2f,
        --    K <Nachname> <Vorname>"
        -- Die Regel schneidet ab " K " plus grossgeschriebenem Wort bis zum Ende. Sie
        -- ist absichtlich grob: Lieber geht ein Stueck Objektbeschrieb verloren, als
        -- dass ein Name stehen bleibt.
        -- RE2 kennt keine Lookaheads, deshalb wird der Treffer mitsamt Vorspann
        -- ersetzt statt davor geschnitten.
        regexp_replace(projectDescription,
                       ',?\s*(Lk\s*/\s*)?\bK [A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ''-]+.*$',
                       ' [Bauherrschaft entfernt]')             AS beschrieb,
        projectLocation_address_street                          AS strasse,
        projectLocation_address_houseNumber                     AS hausnummer,
        projectLocation_address_swissZipCode                    AS plz,
        projectLocation_address_town                            AS ort,
        districtCadastre_relation_cadastre                      AS kataster_nr,
        -- Die Stichwortsuche laeuft auf demselben bereinigten Text, damit ein
        -- Heizungswort im entfernten Namensteil nicht mehr klassifiziert.
        lower(regexp_replace(COALESCE(projectDescription, ''),
                             ',?\s*(Lk\s*/\s*)?\bK [A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ''-]+.*$',
                             ' '))                              AS t
    FROM bronze_baugesuche
),
flags AS (
    SELECT b.*,
        regexp_matches(t, 'wärmepumpe|waermepumpe|wärmepumpen|luft[ /-]{0,3}wasser|erdsonde|erdwärmesonde|erdwärme|erdregister|geothermie|sole[ /-]{0,3}wasser|wasser[ /-]{0,3}wasser.{0,15}pumpe') AS kw_wp,
        regexp_matches(t, 'fernwärme|wärmeverbund|wärmenetz|anergienetz|energieverbund|fernheiz')                       AS kw_fw,
        regexp_matches(t, 'pellet|holzschnitzel|stückholz|holzheizung|holzfeuerung|schnitzelheizung|holzkessel')        AS kw_holz,
        regexp_matches(t, 'solarthermie|sonnenkollektor|thermische solar|thermischen solar')                            AS kw_solarth,
        regexp_matches(t, 'gasheizung|gasfeuerung|erdgas|gastherme|gaskessel|gasbrenner')                               AS kw_gas,
        regexp_matches(t, 'ölheizung|ölfeuerung|öltank|ölkessel|ölbrenner|heizöl|oelheizung')                           AS kw_oel,
        regexp_matches(t, 'elektroheizung|elektro-heizung|elektrospeicherheizung|widerstandsheizung')                   AS kw_elektro,
        regexp_matches(t, 'heizungsersatz|heizungssanierung|heizungserneuerung|heizungsanlage|heizzentrale|energiezentrale|wärmeerzeug|heizung.{0,12}ersetz|ersatz.{0,12}heizung|neue heizung|heizungsumbau|heizungsinstallation') AS kw_generisch,
        -- Ausschluesse
        regexp_matches(t, 'leitung|trasse|erschliessung|leitungsbau|rohrleitung')                                       AS kw_leitung,
        regexp_matches(t, 'heizungsraum|heizraum|heizungskeller')                                                       AS kw_heizraum,
        regexp_matches(t, 'wärmepumpenboiler|wp-boiler|warmwasser.{0,10}wärmepumpe')                                    AS kw_wwwp,
        regexp_matches(t, 'neubau|ersatzneubau|abbruch')                                                                AS kw_neubau,
        regexp_matches(t, 'ersatz|ersetz|sanierung|erneuerung|umbau|umstell|austausch|umrüst|statt')                    AS kw_ersatz
    FROM b
)
SELECT
    bg_id, publikationsnr, pub_datum, bfs_nr_roh, gemeinde_txt, beschrieb,
    -- Dasselbe Vorhaben wird oft mehrfach publiziert, ein Grossprojekt je betroffene
    -- Liegenschaft. vorhaben_id fasst identische Publikationen zusammen,
    -- ist_erstpublikation markiert die erste. Auswertungen zaehlen Vorhaben.
    md5(COALESCE(beschrieb, '') || '|' || COALESCE(gemeinde_txt, '') || '|'
        || COALESCE(strasse, '') || '|' || COALESCE(hausnummer, ''))      AS vorhaben_id,
    row_number() OVER (
        PARTITION BY COALESCE(beschrieb, ''), COALESCE(gemeinde_txt, ''),
                     COALESCE(strasse, ''), COALESCE(hausnummer, '')
        ORDER BY pub_datum, bg_id) = 1                                     AS ist_erstpublikation,
    strasse, hausnummer, plz, ort, kataster_nr,
    kw_wp, kw_fw, kw_holz, kw_solarth, kw_gas, kw_oel, kw_elektro, kw_generisch,
    kw_leitung, kw_neubau, kw_ersatz,
    -- reines Netzprojekt ohne Gebaeudebezug -> kein Heizungsereignis am Gebaeude
    (kw_fw AND kw_leitung AND NOT kw_wp AND NOT kw_generisch)                     AS ist_netzprojekt,
    -- Beschrieb nennt Heizungsraum, aber keinen Energietraeger -> Raumumnutzung
    (kw_heizraum AND NOT (kw_wp OR kw_fw OR kw_holz OR kw_gas OR kw_oel OR kw_generisch)) AS ist_raumumnutzung,
    kw_wwwp                                                                       AS ist_ww_waermepumpe,
    (kw_wp OR kw_fw OR kw_holz OR kw_solarth OR kw_gas OR kw_oel OR kw_elektro OR kw_generisch)
      AND NOT (kw_fw AND kw_leitung AND NOT kw_wp AND NOT kw_generisch)
      AND NOT (kw_heizraum AND NOT (kw_wp OR kw_fw OR kw_holz OR kw_gas OR kw_oel OR kw_generisch))
                                                                                  AS ist_heizungsereignis,
    -- vermuteter neuer Energietraeger nach dem Umbau
    CASE
        WHEN kw_wp                          THEN 'waermepumpe'
        WHEN kw_fw AND NOT kw_leitung       THEN 'fernwaerme'
        WHEN kw_holz                        THEN 'holz'
        WHEN kw_solarth                     THEN 'solarthermie'
        WHEN kw_generisch                   THEN 'unklar'
        WHEN kw_gas OR kw_oel OR kw_elektro THEN 'unklar'
        ELSE NULL
    END                                                                           AS neuer_traeger,
    -- im Text genannter alter (zu ersetzender) Energietraeger
    CASE
        WHEN kw_oel AND kw_gas THEN 'oel_und_gas'
        WHEN kw_oel            THEN 'oel'
        WHEN kw_gas            THEN 'gas'
        WHEN kw_elektro        THEN 'elektro'
        ELSE NULL
    END                                                                           AS alter_traeger_genannt,
    regexp_replace(
      replace(replace(replace(replace(replace(lower(COALESCE(strasse, '')),
        'ä','a'),'ö','o'),'ü','u'),'é','e'),'è','e'),
      '[^a-z0-9]', '', 'g')                                                       AS strasse_norm,
    lower(regexp_replace(COALESCE(hausnummer, ''), '[^0-9a-zA-Z]', '', 'g'))      AS hnr_norm
FROM flags;

-- Geometrie (Parzellen-Polygone) zu den Baugesuchen ab 2025
CREATE OR REPLACE TABLE silver_baugesuche_geo AS
SELECT id AS bg_id, address AS adresse_txt, url, geom
FROM bronze_baugesuche_geo;
