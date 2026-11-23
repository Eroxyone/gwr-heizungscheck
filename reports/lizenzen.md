# Lizenzlage der Quellen

Stand 22.11.2026. Geprüft ist je Quelle, unter welchen Nutzungsbedingungen sie
veröffentlicht ist und ob die benutzte Ebene selbst belegt ist.

## Warum das zählt

Frei herunterladbar ist nicht dasselbe wie frei weiterverwertbar. Die Pauschalaussage
"alles offene Daten" genügt nicht, sobald Ergebnisse weitergegeben werden: Wer eine
Auswertung weiterverwendet, die auf diesen Quellen beruht, muss wissen, unter welchen
Bedingungen er das darf.

## Wie geprüft ist

Über die CKAN-Schnittstelle von opendata.swiss. Dort trägt jede Ressource einen von vier
Standardtermen:

| Term | Bedeutung | für die Weitergabe |
|---|---|---|
| `terms_open` | freie Nutzung | tauglich |
| `terms_by` | freie Nutzung, Quellenangabe Pflicht | tauglich, Quelle nennen |
| `terms_ask` | kommerzielle Nutzung nur mit Bewilligung | **nicht** ohne Rückfrage |
| `terms_by_ask` | beides | **nicht** ohne Rückfrage |

**Keine der verwendeten Quellen trägt `terms_ask`.**

## Stand

23 von 30 Quellen sind mit der benutzten Ebene selbst auf
opendata.swiss belegt. Bei **7** ist nur die kantonsweite Regel des
Datenportals belegt, die Ebene selbst ist dort nicht einzeln aufgeführt - das betrifft
374 der 2738 Fälle auf der Verdachtsliste.

| Quelle                                                      | Host                     | Kanton   |   Fälle auf der Liste | Stufe       | Lizenz                                                                  |
|:------------------------------------------------------------|:-------------------------|:---------|----------------------:|:------------|:------------------------------------------------------------------------|
| baugesuche_zh.csv                                           | daten.statistik.zh.ch    | ZH       |                  1473 | belegt      | Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt  |
| baugesuche_zh_geo.gpkg                                      | daten.statistik.zh.ch    | ZH       |                  1473 | belegt      | Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt  |
| waermenutzung_zh/erdwaermesonden.json                       | maps.zh.ch               | ZH       |                  1473 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_zh/erdregister.json                           | maps.zh.ch               | ZH       |                  1473 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_zh/quellfassung-waermenutzung.json            | maps.zh.ch               | ZH       |                  1473 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_be/erdsond.gpkg.zip                           | geofiles.be.ch           | BE       |                   650 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/TG_erdwaermesonden.json               | ows.geo.tg.ch            | TG       |                    79 | belegt      | opendata.swiss terms_by: freie Nutzung, Quellenangabe Pflicht           |
| waermenutzung_weitere/SZ_erdwaermesonden.gml                | map.geo.sz.ch            | SZ       |                    49 | belegt      | opendata.swiss terms_by: freie Nutzung, Quellenangabe Pflicht           |
| waermenutzung_weitere/SH_erdwaermesonden.json               | wfs.geo.sh.ch            | SH       |                    41 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/SG_thermischezentralen.gml            | www.geoportal.ch         | SG       |                    35 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/AI_erdwaermesonden.gml                | www.geoportal.ch         | AI       |                     9 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/LU_luftwasserwaermepumpen.json        | public.geo.lu.ch         | LU       |                     1 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| gwr_zh.zip                                                  | public.madd.bfs.admin.ch |          |                     0 | belegt      | GWR Stufe A: öffentlich zugängliche Daten, uneingeschränkt nutzbar      |
| epa.zip                                                     | data.geo.admin.ch        |          |                     0 | belegt      | Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt  |
| waermenutzung_zh/grundwasserfassung-waermenutzung.json      | maps.zh.ch               |          |                     0 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/UR_erdsonden.json                     | geo.ur.ch                |          |                     0 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/GE_waermeerzeuger.json                | vector.sitg.ge.ch        |          |                     0 | belegt      | SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe          |
| waermenutzung_weitere/GE_kessel_gebaeude.json               | vector.sitg.ge.ch        |          |                     0 | belegt      | SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe          |
| waermenutzung_weitere/GE_feuerungen.json                    | vector.sitg.ge.ch        |          |                     0 | belegt      | SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe          |
| waermenutzung_weitere/UR_grundwasserwaermepumpen.json       | geo.ur.ch                | UR       |                     0 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/LU_erdwaermesonden.json               | public.geo.lu.ch         |          |                     0 | belegt      | opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt           |
| waermenutzung_weitere/GE_sonden.zip                         | ge.ch                    |          |                     0 | belegt      | SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe          |
| epa_egid.zip                                                | data.geo.admin.ch        |          |                     0 | belegt      | Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt  |
| waermenutzung_weitere/SO_erdwaermesonden.json               | geo.so.ch                | SO       |                   212 | kantonsweit | opendata.swiss terms_open für die Datensätze des Kantons Solothurn      |
| waermenutzung_weitere/ZG_erdwaermenutzung.gpkg              | services.geo.zg.ch       | ZG       |                   126 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Zug              |
| waermenutzung_weitere/BL_erdsonden.gml                      | geowms.bl.ch             | BL       |                    36 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Basel-Landschaft |
| waermenutzung_weitere/ZG_tank_gebaeude_in_betrieb.gml       | services.geo.zg.ch       |          |                     0 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Zug              |
| waermenutzung_weitere/ZG_tank_gebaeude_ausser_betrieb.gml   | services.geo.zg.ch       |          |                     0 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Zug              |
| waermenutzung_weitere/ZG_tank_erdverlegt_in_betrieb.gml     | services.geo.zg.ch       |          |                     0 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Zug              |
| waermenutzung_weitere/ZG_tank_erdverlegt_ausser_betrieb.gml | services.geo.zg.ch       |          |                     0 | kantonsweit | opendata.swiss terms_by für die Datensätze des Kantons Zug              |

## Offene Punkte

Für Solothurn, Zug und Basel-Landschaft gilt die kantonsweite Regel ihres Datenportals,
die benutzte Ebene ist dort aber nicht einzeln aufgeführt. Das ist ein schwächerer Beleg
als eine eigene Datensatzseite.

Klären lässt sich das durch eine Anfrage beim jeweiligen Amt für Geoinformation, ob die
bezogene Ebene weiterverwendet und weitergegeben werden darf. Die Antwort gehört mit Datum
in `config.LIZENZEN`, Feld `beleg`.

Für jede Weitergabe von Ergebnissen gilt: Zu nennen ist, auf welchen Quellen sie beruhen
und welche davon eine Quellenangabe verlangen. Eine pauschale Zusicherung, dass alles frei
weiterverwertbar sei, ist durch diese Prüfung nicht gedeckt.
