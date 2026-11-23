# Detailauswertung Kanton Zürich: Baugesuche gegen Registerstand

Datenstand GWR 2026-09-13, Baugesuche bis 2026-09-11. Gemessen wird, ob Heizungs-Baugesuche
und Wärmenutzungsanlagen im Gebäude- und Wohnungsregister (GWR) nachgeführt sind: im Kanton
Zürich im Detail, bei den Wärmenutzungsanlagen für 13 Kantone.

Erzeugt von `src/report.py` aus `src/report_template.md`. Tabellen und Kennzahlen kommen aus
der Pipeline. Einzelne Werte im Fliesstext und die Sensitivitätsrechnung in Abschnitt 2.6
stehen fest in der Vorlage und stammen aus dem Lauf vom September 2026.

---

## Kurzfassung

Die Studie fragt, ob sich veraltete Heizungsangaben im GWR aus offenen Daten erkennen lassen
und ob es dafür genug Belege gibt. Die Antwort aus den Daten ist zweigeteilt.

**Die Datenlücke ist real und gross.** Von 458 eindeutig zugeordneten Heizungs-Baugesuchen,
die mindestens sechs Monate zurückliegen, zeigt das GWR bei **40,6 %** immer noch den alten
Energieträger mit einem Aktualisierungsdatum vor dem Baugesuch. 43,2 % sind sauber
nachgeführt, in der weiten Auslegung 49,1 %. Auch bei Baugesuchen, die 18 Monate und
länger zurückliegen, bleibt die Lücke bei 36,2 %. Das erste Abbruchkriterium der Studie
(über 80 % nachgeführt) ist damit nicht erfüllt.

**Die Belege sind für die meisten Gemeinden zu dünn.** Im ganzen Kanton finden sich rund
569 Heizungs-Baugesuche pro Jahr. Die mittlere Gemeinde kommt
auf **1,6 Gesuche pro Jahr**, drei Viertel der Gemeinden liegen unter 3,1.
Für eine Auswertung je Gemeinde reicht das nicht; nur Zürich und Winterthur haben genug
Fälle. Damit ist das zweite Abbruchkriterium der Studie erfüllt (Test 2: nur eine Handvoll
Gesuche pro Gemeinde und Jahr).

**Ein dritter Befund relativiert die ersten beiden.** Neun Kantone veröffentlichen ihre
Wärmenutzungsanlagen mit Datum (Abschnitt 2.7). Von den Anlagen, die dort als gebaut gelten,
sind 66,5 % im GWR sichtbar, und der Wert hängt am Alter: Anlagen aus den letzten
2 bis 4 Jahren sind zu 77,3 % erfasst, Anlagen ab 20 Jahren zu 62,4 %.
**Die Nachführung wird besser.** Der Rückstand liegt überwiegend im Altbestand.

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.** Details in Abschnitt 5.

Ein methodischer Nebenbefund: Die Informationsquelle im GWR (Code 860 "Volkszählung 2000")
taugt nicht als Indikator für Datenqualität. Die Stadt Zürich hat 0 % Einträge mit Quelle 860
und wäre nach Test 1 sauber. In Test 3 fehlt dort trotzdem bei 70,7 % der
Heizungs-Baugesuche die Nachführung. Veraltete Einträge zeigen sich erst, wenn Ereignisse
gegen den Registerstand geprüft werden; die Metadaten allein zeigen sie nicht.

---

## 1 Datenbasis

### 1.1 Quellen

| Quelle                                                                  | Datei                                                       | MB    | URL                                                                                                                                                                                                                                  |
|:------------------------------------------------------------------------|:------------------------------------------------------------|:------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| GWR öffentliche Daten Stufe A                                           | gwr_zh.zip                                                  | 121,7 | https://public.madd.bfs.admin.ch/zh.zip                                                                                                                                                                                              |
| Baugesuche im Kanton ZH                                                 | baugesuche_zh.csv                                           | 9,5   | https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006183.csv                                                                                                                                                        |
| Georeferenzierte Baugesuche im Kanton ZH ab 2025 (Statistisches Amt ZH) | baugesuche_zh_geo.gpkg                                      | 12,0  | https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006403.gpkg                                                                                                                                                       |
| Elektrizitätsproduktionsanlagen CH (BFE)                                | epa.zip                                                     | 17,3  | https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip                                                                                     |
| Elektrizitätsproduktionsanlagen CH (BFE)                                | epa_egid.zip                                                | 8,6   | https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip                                                                                                               |
| Erdwärmesonden Kanton ZH (AWEL)                                         | waermenutzung_zh/erdwaermesonden.json                       | 11,8  | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:erdwaermesonden&outputFormat=geojson                                                                                            |
| Erdregister Kanton ZH (AWEL)                                            | waermenutzung_zh/erdregister.json                           | 0,0   | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:erdregister&outputFormat=geojson                                                                                                |
| Grundwasserfassungen mit Wärmenutzung                                   | waermenutzung_zh/grundwasserfassung-waermenutzung.json      | 0,5   | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:grundwasserfassung-waermenutzung&outputFormat=geojson                                                                           |
| Quellfassungen mit Wärmenutzung                                         | waermenutzung_zh/quellfassung-waermenutzung.json            | 0,0   | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:quellfassung-waermenutzung&outputFormat=geojson                                                                                 |
| Erdwärmesonden Kanton SZ                                                | waermenutzung_weitere/SZ_erdwaermesonden.gml                | 1,3   | https://map.geo.sz.ch/mapserv_proxy?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=ms:ch.sz.a034c.waermenutzung.erdwaermeanlage.erdwaermesonde                                                                                |
| Erdsondenbohrungen Kanton BL                                            | waermenutzung_weitere/BL_erdsonden.gml                      | 5,4   | https://geowms.bl.ch/?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=ms:grundwasser_erdsonden                                                                                                                                 |
| Thermische Zentralen Kanton SG                                          | waermenutzung_weitere/SG_thermischezentralen.gml            | 106,4 | https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=geoportal%3Aq352_thermischezentralen                                                                                                    |
| Erdwärmesondenbohrungen Kanton AI                                       | waermenutzung_weitere/AI_erdwaermesonden.gml                | 15,6  | https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=geoportal%3Af211_ai_erdwaermesonden                                                                                                     |
| Erdwärmesondenanlagen Kanton ZG                                         | waermenutzung_weitere/ZG_erdwaermenutzung.gpkg              | 4,0   | https://services.geo.zg.ch/datarepo/Erdwaerme/geopackage/Erdwaermenutzung.gpkg                                                                                                                                                       |
| Konzessionen Grundwasserwärmepumpen Kanton UR                           | waermenutzung_weitere/UR_grundwasserwaermepumpen.json       | 0,1   | https://geo.ur.ch/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=energie%3Aur031_konzessionen_grundwasserwaermepumpen&outputFormat=application%2Fjson                                                                     |
| Luft-Wasser-Wärmepumpen Kanton LU                                       | waermenutzung_weitere/LU_luftwasserwaermepumpen.json        | 2,9   | https://public.geo.lu.ch/ogd/services/managed/LUFWAWPO_DS_V1_MP/MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature&typeNames=esri%3ALuft-Wasser-W%C3%A4rmepumpen__geplante_und_bewilligte_Anlagen&outputFormat=GEOJSON |
| Feuerungskataster Kanton GE                                             | waermenutzung_weitere/GE_feuerungen.json                    | 28,8  | https://vector.sitg.ge.ch/arcgis/rest/services/SCANE_CHAUDIERE/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=geojson                                                                                          |
| Tankkataster Kanton ZG: Tanks im oder am Gebäude                        | waermenutzung_weitere/ZG_tank_gebaeude_in_betrieb.gml       | 4,6   | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_in_betrieb                                                                                                    |
| Tankkataster Kanton ZG: Tanks im oder am Gebäude                        | waermenutzung_weitere/ZG_tank_gebaeude_ausser_betrieb.gml   | 2,4   | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_ausser_betrieb                                                                                                |
| Tankkataster Kanton ZG: erdverlegte Tanks                               | waermenutzung_weitere/ZG_tank_erdverlegt_in_betrieb.gml     | 0,9   | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_in_betrieb                                                                                                     |
| Tankkataster Kanton ZG: erdverlegte Tanks                               | waermenutzung_weitere/ZG_tank_erdverlegt_ausser_betrieb.gml | 0,5   | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_ausser_betrieb                                                                                                 |

Alle Quellen sind offen zugänglich; die Nutzungsbedingungen je Quelle stehen in
[lizenzen.md](lizenzen.md). Rohdaten liegen in `data/raw/` und sind bewusst nicht im Git.
`data/raw/manifest.json` hält URL, Grösse, SHA-256 und Downloadzeitpunkt fest.

### 1.2 Umfang

| Datensatz                          |   Zeilen |
|:-----------------------------------|---------:|
| GWR Gebäude ZH, alle Status        |   400142 |
| GWR Gebäude, Status bestehend      |   367385 |
| GWR Gebäude mit Wohnnutzung        |   228968 |
| GWR Eingänge (Adressen)            |   414160 |
| Baugesuche ZH                      |    22780 |
| davon mit Parzellengeometrie       |    11930 |
| davon als Heizungsereignis erkannt |     1753 |
| Photovoltaikanlagen ZH             |    32695 |

### 1.3 Stand und Lücken

- **GWR:** Exportdatum 2026-09-13. Vollständig für den ganzen Kanton.
  Die Codelisten stammen aus der mitgelieferten Datei `kodes_codes_codici.csv`, nicht aus
  Sekundärquellen.
- **Baugesuche:** Publikationen bis 2026-09-11. Die Sammlung des Statistischen Amts ist erst
  ab Herbst 2024 vollständig; frühere Jahre enthalten nur Einzelfälle (2022: 3, 2023: 74).
  Alle Zeitreihen in diesem Report beginnen deshalb im Oktober 2024.
  Die Felder `bfs_nr` und `municipality_name` sind erst ab 2025 gefüllt. Für 2024 ist die
  Gemeinde über das zugeordnete Gebäude beziehungsweise über PLZ und Ortsname hergeleitet;
  danach bleiben 402 von 22'780 Gesuchen ohne Gemeinde.
  Parzellengeometrien gibt es erst ab 2025.
- **Mehrfachpublikationen:** Dasselbe Vorhaben erscheint oft mehrmals. 5'100 von 22'780
  Publikationen (22,4 %) wiederholen einen bereits vorhandenen Beschrieb an derselben
  Adresse; ein Grossprojekt kommt 48-mal vor, offenbar einmal je betroffene
  Liegenschaft. Alle Auswertungen zählen deshalb **Vorhaben, nicht Publikationen**:
  17'680 Vorhaben, davon 1'427 mit Heizungsbezug. Ohne diese Korrektur
  lägen die Fallzahlen rund ein Fünftel zu hoch.
- **Photovoltaik:** letzte Inbetriebnahme im verwendeten Datensatz 2026-05-08.
  Der auf opendata.swiss verlinkte CSV-Pfad `/csv/2056/` liefert
  eine auf exakt 100'000 Zeilen gekürzte Datei, die für den Kanton Zürich nur bis Oktober 2022
  reicht. Sie enthält dafür eine EGID-Spalte. Verwendet wird deshalb das STAC-Asset desselben
  Datensatzes mit 333'313 Anlagen; dort fehlt die EGID, die Zuordnung läuft über die Koordinate.
  Die gekürzte Datei dient als Referenz zur Prüfung genau dieser Zuordnung (Abschnitt 3).

---

## 2 Ergebnisse

### 2.1 Test 1 - Grösse des Problems

Betrachtet werden bestehende Gebäude mit Wohnnutzung (GKAT 1020, 1030, 1040).
Als *Kandidat* gilt ein fossil beheiztes Gebäude (Heizöl oder Gas), dessen Heizungsangabe
entweder die Quelle 860 trägt oder deren Aktualisierungsdatum älter als 15 Jahre ist
oder fehlt.

|   Wohngebäude |   fossil beheizt |   % fossil |   Kandidaten |   % Kandidaten |
|--------------:|-----------------:|-----------:|-------------:|---------------:|
|        228968 |           127030 |       55,5 |        61925 |           27,0 |

**61'925 Kandidaten** von 228'968 Wohngebäuden im Kanton. Verteilung der
Informationsquelle über alle Wohngebäude:

| Code   | Informationsquelle                              |   Gebäude |    % |
|:-------|:------------------------------------------------|----------:|-----:|
| 860    | Gemäss Volkszählung 2000                        |     75506 | 33,0 |
| 869    | Gemäss Baubewilligung                           |     46148 | 20,2 |
| 859    | Andere                                          |     40739 | 17,8 |
| 865    | Gemäss Daten der Gemeinde                       |     27162 | 11,9 |
| 864    | Gemäss kantonalen Daten / Das Gebäudeprogramm   |     20193 |  8,8 |
| 855    | Gemäss Feuerungskontrolle                       |      9265 |  4,0 |
| 870    | Gemäss Versorgungswerk (Gas, Fernwärme)         |      3884 |  1,7 |
| 857    | Gemäss Eigentümer/in / Verwaltung               |      3460 |  1,5 |
| 852    | Gemäss amtlicher Schätzung                      |      1185 |  0,5 |
| 858    | Gemäss Gebäudeenergieausweis der Kantone (GEAK) |       875 |  0,4 |
| (leer) | ohne Angabe                                     |       438 |  0,2 |
| 871    | Gemäss Minergie                                 |       111 |  0,0 |
| 853    | Gemäss Gebäudeversicherung                      |         2 |  0,0 |

Ein Drittel aller Heizungseinträge im Kanton geht immer noch auf die Volkszählung 2000 zurück.
Die Spannweite zwischen den Gemeinden ist aber enorm:

|   Minimum |   25 % |   Median |   75 % |   Maximum |
|----------:|-------:|---------:|-------:|----------:|
|         0 |   28,6 |     35,6 |   44,6 |      67,8 |

Fokusgemeinden:

| Gemeinde          |   Wohngebäude |   fossil |   % fossil |   Kandidaten |   % Kandidaten |   % Quelle 860 |   % Quelle 869 |
|:------------------|--------------:|---------:|-----------:|-------------:|---------------:|---------------:|---------------:|
| Zürich            |         36996 |    26094 |       70,5 |            0 |            0,0 |            0,0 |            4,7 |
| Winterthur        |         16052 |     8995 |       56,0 |         1148 |            7,2 |            7,8 |           12,4 |
| Illnau-Effretikon |          2834 |     1428 |       50,4 |          156 |            5,5 |            7,8 |            5,1 |
| Volketswil        |          2543 |     1662 |       65,4 |          442 |           17,4 |           19,8 |            8,4 |
| Fehraltorf        |           893 |      419 |       46,9 |          273 |           30,6 |           43,7 |           36,5 |

Zürich hat **null** Einträge mit Quelle 860 und damit null Kandidaten nach dieser Definition,
obwohl die Mehrheit der Wohngebäude dort fossil beheizt ist (Spalte "% fossil").
Die Stadt hat die Volkszählungsdaten flächendeckend durch eigene Einträge ersetzt (Code 859
"Andere"), die zum grossen Teil aus den Jahren 2018 bis 2021 stammen. Nach Test 1 wäre Zürich
also sauber. Test 3 zeigt das Gegenteil. **Die Informationsquelle allein ist kein brauchbarer
Qualitätsindikator.**

Test 1 erfüllt damit kein Abbruchkriterium der Studie (der Anteil ist im Median hoch), trägt
aber auch keine positive Aussage: Die Kennzahl misst Metadaten, nicht die Richtigkeit der
Einträge.

### 2.2 Test 2 - Genug Belege?

1'753 von 22'780 Publikationen sind über Stichworte als Heizungsereignis erkannt; nach
Zusammenfassen der Mehrfachpublikationen bleiben **1'427 Vorhaben**
(Details zur Erkennung in Abschnitt 4). Verteilung des erkannten neuen Energieträgers
über alle Publikationen:

| neuer Energieträger laut Gesuchstext   |   Gesuche |
|:---------------------------------------|----------:|
| Wärmepumpe                             |      1530 |
| unklar                                 |       117 |
| Holz                                   |        51 |
| Fernwärme                              |        43 |
| Solarthermie                           |        12 |

Zeitreihe für den ganzen Kanton:

| Monat   |   Baugesuche |   davon Heizung |
|:--------|-------------:|----------------:|
| 2024-10 |          481 |              34 |
| 2024-11 |          686 |              40 |
| 2024-12 |          215 |               8 |
| 2025-01 |          736 |              42 |
| 2025-02 |          575 |              33 |
| 2025-03 |          545 |              35 |
| 2025-04 |          568 |              41 |
| 2025-05 |          692 |              46 |
| 2025-06 |          565 |              38 |
| 2025-07 |          624 |              67 |
| 2025-08 |          616 |              44 |
| 2025-09 |          477 |              30 |
| 2025-10 |          625 |              54 |
| 2025-11 |          515 |              34 |
| 2025-12 |          244 |              24 |
| 2026-01 |          744 |              50 |
| 2026-02 |          498 |              50 |
| 2026-03 |          542 |              49 |
| 2026-04 |          576 |              62 |
| 2026-05 |          604 |              54 |
| 2026-06 |          617 |              56 |
| 2026-07 |          674 |              77 |
| 2026-08 |          597 |              79 |
| 2026-09 |          293 |              50 |

Der September 2026 ist ein angebrochener Monat (bis zum 2026-09-11), die absolute Zahl dort
ist deshalb nicht vergleichbar. Der Anteil der Heizungsgesuche an allen Baugesuchen nimmt im
Beobachtungszeitraum zu: von 5,9 % im ersten Quartal der Reihe (Q4 2024)
auf 9,6 % im letzten vollständigen Quartal (Q2 2026).

Entscheidend ist die Verteilung über die Gemeinden:

|   Gemeinden |   Minimum |   25 % |   Median |   75 % |   Maximum |
|------------:|----------:|-------:|---------:|-------:|----------:|
|         159 |         0 |    0,5 |      1,6 |    3,1 |     147,7 |

**Hier greift das zweite Abbruchkriterium der Studie.** Die mittlere Gemeinde hat
1,6 Heizungs-Baugesuche pro Jahr, drei Viertel der Gemeinden haben höchstens
3,1. Die Belege konzentrieren sich auf wenige grosse Gemeinden:

| Gemeinde     |   Heizungsgesuche |   pro Jahr |   % zugeordnet |
|:-------------|------------------:|-----------:|---------------:|
| Zürich       |               283 |      147,7 |           92,6 |
| Winterthur   |               144 |       75,1 |           88,9 |
| Uster        |                29 |       15,1 |           89,7 |
| Wädenswil    |                26 |       13,6 |           96,2 |
| Volketswil   |                24 |       12,5 |           87,5 |
| Hinwil       |                20 |       10,4 |           90,0 |
| Wiesendangen |                19 |        9,9 |           78,9 |
| Adliswil     |                15 |        7,8 |           93,3 |
| Dietikon     |                14 |        7,3 |          100,0 |
| Horgen       |                14 |        7,3 |          100,0 |

Fokusgemeinden:

| Gemeinde          |   Baugesuche |   Heizungsgesuche |   % Heizung |   pro Jahr |   mit EGID |   % zugeordnet |   eindeutig |
|:------------------|-------------:|------------------:|------------:|-----------:|-----------:|---------------:|------------:|
| Zürich            |         2706 |               283 |        10,5 |      147,7 |        262 |           92,6 |         136 |
| Winterthur        |          857 |               144 |        16,8 |       75,1 |        128 |           88,9 |          66 |
| Volketswil        |          144 |                24 |        16,7 |       12,5 |         21 |           87,5 |          16 |
| Illnau-Effretikon |          124 |                 4 |         3,2 |        2,1 |          3 |           75,0 |           1 |
| Fehraltorf        |           42 |                 2 |         4,8 |        1,0 |          2 |          100,0 |           1 |

Illnau-Effretikon hat unter den Fokusgemeinden den tiefsten Anteil an Heizungsgesuchen,
Winterthur und Volketswil haben den höchsten (Spalte "% Heizung"). Der Unterschied liegt an
der Publikationspraxis: Manche Gemeinden publizieren einen Heizungsersatz als eigenes
Baugesuch, andere behandeln ihn als bewilligungsfrei oder als Nebenpunkt eines grösseren
Vorhabens.

**Grössenordnung zum Vergleich:** Im Kanton stehen rund 127'000 fossil beheizte Wohngebäude.
Bei einer Ersatzrate von 3 bis 5 % pro Jahr wären das 4'000 bis 6'000 Heizungswechsel jährlich.
Gefunden werden über die Baugesuche rund 569 pro Jahr. **Baugesuche erfassen damit
grob geschätzt 10 bis 20 % der tatsächlichen Heizungswechsel.** Der Rest sind Ersatzvorhaben im
Gebäudeinneren, die keine Baubewilligung brauchen. Sichtbar wird vor allem die aussen aufgestellte
Luft/Wasser-Wärmepumpe, weil die wegen Lärm und Grenzabstand bewilligungspflichtig ist.

### 2.3 Test 3 - Werden Baugesuche schon nachgeführt?

Der zentrale Test der Studie. Grundmenge: Heizungs-Baugesuche, deren Publikation mindestens sechs Monate
zurückliegt, die genau einem Gebäude zugeordnet werden konnten und die kein reiner Neubau sind.
Das sind 458 Fälle.

| Status                                                           |   Fälle |    % |
|:-----------------------------------------------------------------|--------:|-----:|
| nachgeführt (neuer Energieträger und Datum nach dem Baugesuch)   |     198 | 43,2 |
| nicht nachgeführt (alter Energieträger, Datum vor dem Baugesuch) |     186 | 40,6 |
| nach dem Baugesuch angefasst, Energieträger passt nicht          |      33 |  7,2 |
| Energieträger passt, Datum älter als das Baugesuch               |      18 |  3,9 |
| unklar (keine Angabe im GWR oder kein Träger im Gesuchstext)     |      14 |  3,1 |
| angefasst, Quelle 869 nach dem Baugesuch                         |       9 |  2,0 |

Zusammengefasst: **43,2 % sauber nachgeführt**, in der weiten Auslegung (inklusive
"Quelle 869 nach dem Gesuch" und "Energieträger passt, Datum älter") **49,1 %**.
Dem stehen **40,6 % klare Lücken** gegenüber.

Der naheliegende Einwand lautet: Sechs Monate sind zu kurz, gebaut wird erst später. Deshalb
dieselbe Auswertung nach Alter des Baugesuchs:

| Alter des Baugesuchs   |   Fälle |   % nachgeführt (eng) |   % nachgeführt (weit) |   % Lücke |
|:-----------------------|--------:|----------------------:|-----------------------:|----------:|
| 6-11 Monate            |      91 |                  19,8 |                   25,3 |      57,1 |
| 12-17 Monate           |      88 |                  45,5 |                   50,0 |      37,5 |
| 18-23 Monate           |      83 |                  33,7 |                   42,2 |      47,0 |
| 24+ Monate             |     196 |                  57,1 |                   62,8 |      31,6 |

Die Nachführung holt mit der Zeit auf, aber sie holt nicht ein. Bei Baugesuchen, die 18 Monate
und länger zurückliegen, sind 50,2 % nachgeführt und **36,2 % weiterhin nicht**.
Die Schwelle von 80 % (Abbruchkriterium der Studie) wird in keinem Altersfenster erreicht.

Was in den Lückenfällen im GWR steht:

| GWR-Energieträger   | GWR-Informationsquelle                        |   Fälle |
|:--------------------|:----------------------------------------------|--------:|
| Gas                 | Andere                                        |      68 |
| Heizöl              | Gemäss Volkszählung 2000                      |      41 |
| Heizöl              | Andere                                        |      15 |
| Gas                 | Gemäss Daten der Gemeinde                     |      12 |
| Elektrizität        | Gemäss Volkszählung 2000                      |       9 |
| Holz (generisch)    | Gemäss Volkszählung 2000                      |       9 |
| Heizöl              | Gemäss kantonalen Daten / Das Gebäudeprogramm |       7 |
| Heizöl              | Gemäss Daten der Gemeinde                     |       6 |
| Heizöl              | Gemäss Baubewilligung                         |       4 |
| Gas                 | Gemäss Volkszählung 2000                      |       2 |

Die Gemeinden streuen stark (Gemeinden mit mindestens 8 auswertbaren Fällen):

| Gemeinde          |   Fälle |   % nachgeführt |   % Lücke |
|:------------------|--------:|----------------:|----------:|
| Kilchberg (ZH)    |       8 |             0,0 |      87,5 |
| Zürich            |     123 |            26,0 |      70,7 |
| Winterthur        |      34 |            29,4 |      55,9 |
| Maur              |       9 |            44,4 |      55,6 |
| Volketswil        |      10 |            20,0 |      40,0 |
| Dietikon          |       9 |            44,4 |      33,3 |
| Rümlang           |       8 |            50,0 |      25,0 |
| Bauma             |       8 |            75,0 |      12,5 |
| Ottenbach         |       9 |            66,7 |      11,1 |
| Pfäffikon         |      10 |            80,0 |      10,0 |
| Opfikon           |      10 |            80,0 |      10,0 |
| Wädenswil         |      11 |            63,6 |       9,1 |
| Wettswil am Albis |      12 |            83,3 |       0,0 |

Fokusgemeinden:

| Gemeinde   |   Fälle |   nachgeführt |   Lücke |   % Lücke |
|:-----------|--------:|--------------:|--------:|----------:|
| Zürich     |     123 |            32 |      87 |      70,7 |
| Winterthur |      34 |            10 |      19 |      55,9 |
| Volketswil |      10 |             2 |       4 |      40,0 |

Illnau-Effretikon und Fehraltorf fehlen in dieser Tabelle: Beide haben nach allen Filtern
null auswertbare Fälle. Für diese Gemeinden lässt sich die Frage aus Test 3 mit Baugesuchen
nicht beantworten.

In Winterthur zeigt sich die Grenze einer Sammelaktualisierung. Die Stadt hat im Februar 2024
die Heizungsdaten flächendeckend aktualisiert; 84 % aller Wohngebäude tragen ein
Aktualisierungsdatum ab 2024. Trotzdem fehlt bei 55,9 % der Heizungs-Baugesuche die
Nachführung, typischerweise mit diesem Muster: Energieträger Gas, Quelle "Gemäss Daten der
Gemeinde", Datum 2024-02-09, Baugesuch für den Wärmepumpenersatz aus 2025 oder 2026. **Eine
Sammelaktualisierung erzeugt einen sauberen Stichtag, aber keinen laufenden Prozess.**

### 2.4 Gegenprobe - wie viel führt der Kanton insgesamt nach?

Aktualisierungen der Heizungsangabe bei Wohngebäuden, nach Jahr des Aktualisierungsdatums:

|   Jahr |   Heizungseinträge aktualisiert |   davon auf Wärmepumpe |
|-------:|--------------------------------:|-----------------------:|
|   2022 |                            5987 |                   2138 |
|   2023 |                            9458 |                   3288 |
|   2024 |                           31117 |                  14771 |
|   2025 |                           15119 |                   4726 |
|   2026 |                           22060 |                   5348 |

31'117 Heizungseinträge tragen ein Aktualisierungsdatum aus dem Jahr 2024, 22'060 eines
aus 2026 (bis zum Exportdatum). 24'845 Wohngebäude mit Aktualisierungsdatum ab 2024
weisen eine Wärmepumpe aus. Als Informationsquelle tragen die seit 2024 aktualisierten
Einträge vor allem Gemeindedaten (Code 865), kantonale Daten und Gebäudeprogramm (864),
Baubewilligungen (869) und die Feuerungskontrolle (855).

**Der Kanton und die Gemeinden führen also bereits in grossem Umfang nach, über Kanäle, die pro
Jahr ein Vielfaches dessen abdecken, was Baugesuche sichtbar machen.** Die Lücke aus Test 3
ist eine Lücke in einem laufenden Prozess.

### 2.5 Test 4 - Fälle ohne Baugesuch

Gebäude mit Wohnnutzung, registrierter Photovoltaikanlage, fossilem Heizungseintrag und
Quelle 860: **4'079 Gebäude im Kanton**.

| Gemeinde          |   PV und fossil und Quelle 860 |
|:------------------|-------------------------------:|
| Maur              |                            108 |
| Thalwil           |                             90 |
| Hombrechtikon     |                             88 |
| Dürnten           |                             83 |
| Dübendorf         |                             82 |
| Horgen            |                             82 |
| Stäfa             |                             74 |
| Pfäffikon         |                             71 |
| Wettswil am Albis |                             65 |
| Niederhasli       |                             62 |

Fokusgemeinden:

| Gemeinde          |   PV und fossil und Quelle 860 |
|:------------------|-------------------------------:|
| Winterthur        |                             47 |
| Volketswil        |                             17 |
| Illnau-Effretikon |                             10 |
| Fehraltorf        |                              7 |
| Zürich            |                              0 |

Das ist nur ein schwaches Indiz. Eine PV-Anlage sagt nichts über die Heizung; sie
zeigt nur, dass die Eigentümerschaft in den letzten Jahren am Gebäude etwas gemacht hat und dass
der Heizungseintrag seither nicht angefasst wurde. Als eigenständiger Beleg ist das zu wenig,
als zusätzliches Merkmal neben einem anderen Beleg brauchbar.

### 2.6 Test 5 - Wärmenutzungsanlagen gegen den Registerstand

Der Test umfasst die 13 Kantone, die ihre Anlagen zur Wärmenutzung offen
veröffentlichen (überwiegend Erdwärmesonden; die Anlagentypen stehen in der Tabelle).
Zusammen **133'772 Anlagen**. Davon zählt die Pipeline 128'059 als gebaut
(Merkmal `ist_gebaut` in `sql/test5.sql`). Das Merkmal ist grosszügig: Wo ein Kanton kein
Statusfeld führt, gelten alle veröffentlichten Anlagen als bestehend, und auch die Urner
Konzessionen und die Luzerner Luft-Wasser-Wärmepumpen ("bewilligt oder geplant") zählen mit,
obwohl ihre Ausführung nicht belegt ist.

| Kanton   | Anlagentyp             |   Anlagen |   davon gebaut |
|:---------|:-----------------------|----------:|---------------:|
| AI       | Erdwärmesonde          |      2419 |           2419 |
| BE       | Erdwärmesonde          |     14661 |          11391 |
| BL       | Erdwärmesonde          |      2629 |           2629 |
| GE       | Erdwärmesonde          |      3668 |           3666 |
| LU       | Erdwärmesonde          |     14717 |          14717 |
| LU       | Luft-Wasser-Wärmepumpe |      7066 |           7066 |
| SG       | Wärmepumpe             |     29194 |          27131 |
| SG       | Fernwärmeanschluss     |         4 |              4 |
| SH       | Erdwärmesonde          |      1235 |           1235 |
| SO       | Erdwärmesonde          |      8863 |           8863 |
| SZ       | Erdwärmesonde          |      1675 |           1675 |
| TG       | Erdwärmesonde          |      4532 |           4530 |
| UR       | Erdwärmesonde          |       555 |            555 |
| UR       | Grundwasser-Wärmepumpe |       292 |            292 |
| ZG       | Erdwärmesonde          |      2792 |           2416 |
| ZH       | Erdwärmesonde          |     38553 |          38553 |
| ZH       | Grundwasserfassung     |       868 |            868 |
| ZH       | Quellfassung           |        46 |             46 |
| ZH       | Erdregister            |         3 |              3 |

Der Unterschied zu Test 4: Eine Photovoltaikanlage sagt nichts über die Heizung, eine
Erdwärmesonde schon. Steht im GWR an einem solchen Gebäude trotzdem Öl oder Gas, widersprechen
sich die beiden Quellen.

**Was im GWR rund um eine Wärmenutzungsanlage steht** (Wohngebäude innerhalb von 20 m,
alle 13 Kantone):

| GWR-Energieträger   |   Gebäude |    % |
|:--------------------|----------:|-----:|
| Wärmepumpe          |     49422 | 41,9 |
| unbestimmt          |     28598 | 24,3 |
| Heizöl              |     21230 | 18,0 |
| Gas                 |      9620 |  8,2 |
| Holz                |      3556 |  3,0 |
| Elektrizität        |      2914 |  2,5 |
| Fernwärme           |      1478 |  1,3 |
| andere              |       681 |  0,6 |

**47,8 %** der Zürcher Anlagen haben ein Gebäude mit Wärmepumpen-Eintrag im Umkreis.
Die Werte je Kanton:

| Kanton   |   Anlagen mit Gebäude |   mit Wärmepumpe im GWR |   % mit WP |   Widerspruch |
|:---------|----------------------:|------------------------:|-----------:|--------------:|
| AI       |                  2292 |                    2113 |       92,2 |            69 |
| BE       |                 10918 |                    4939 |       45,2 |          2434 |
| BL       |                  2523 |                    2066 |       81,9 |           344 |
| GE       |                  2545 |                     234 |        9,2 |           732 |
| LU       |                  9431 |                    2547 |       27,0 |          3059 |
| SG       |                 25777 |                   24414 |       94,7 |           492 |
| SH       |                  1152 |                     527 |       45,7 |           151 |
| SO       |                  7750 |                    2174 |       28,1 |          1489 |
| SZ       |                  1540 |                     475 |       30,8 |           284 |
| TG       |                  4324 |                    2418 |       55,9 |           496 |
| UR       |                   776 |                     198 |       25,5 |           165 |
| ZG       |                  2279 |                     896 |       39,3 |           393 |
| ZH       |                 37371 |                   17873 |       47,8 |          7103 |

Die Spanne reicht von 9,2 % (GE) bis 94,7 % (SG).
4 Kantone liegen zwischen 45 % und 56 % (BE, SH, ZH, TG),
6 darunter (GE, UR, LU, SO, SZ, ZG) und 3 darüber (BL, AI, SG). Ein einheitliches
Bild ergeben die Kantone nicht. Ein Teil der Unterschiede liegt an den Quellen und nicht am
Register: St. Gallen führt ein Anlagenregister mit der Wärmepumpe selbst, die Luzerner
Koordinaten sind nicht gebäudegenau, und in Genf steht bei vielen Gebäuden im Umkreis
"Unbestimmt" als Energieträger ([quellenmatrix.md](quellenmatrix.md),
[docs/datenquellen.md](../docs/datenquellen.md)).

Für Uri (25,5 %) kommt hinzu: Der Datensatz meldet ausschliesslich
"Konzession erteilt". Eine erteilte Konzession heisst noch nicht, dass gebohrt wurde. Uri ist
deshalb aus der datierten Auswertung in Abschnitt 2.7 ausgeschlossen.

**Ergebnis:** **16'025 Wohngebäude** in den ausgewerteten Kantonen
(8'773 in Zürich, 2'992 in Bern) sind fossil eingetragen,
obwohl innerhalb von 20 m eine Wärmenutzungsanlage liegt, die als gebaut gilt, und kein
Gebäude dort eine Wärmepumpe ausweist. Davon tragen 7'437 die Quelle
"Volkszählung 2000". Die mittlere Distanz zur Anlage beträgt 12,3 m.

Diese Zahl stammt aus dem Lauf vom September 2026 und zählt jedes fossil eingetragene
Wohngebäude im Umkreis einer Anlage. Die Verdachtsliste zählt enger: Sie übernimmt eine Anlage
nur, wenn sie genau einem Gebäude zugeordnet ist (`sql/zuordnung_anlagen.sql`,
[docs/methode.md](../docs/methode.md)). Deshalb nennen
[kantonsvergleich.md](kantonsvergleich.md) und die Listenzahlen deutlich kleinere Werte.

| Kanton   | Gemeinde       |   Widersprüche |   davon Quelle 860 |
|:---------|:---------------|---------------:|-------------------:|
| ZH       | Zürich         |           1469 |                  0 |
| BE       | Bern           |            347 |                102 |
| ZH       | Winterthur     |            327 |                 22 |
| ZH       | Zollikon       |            224 |                175 |
| ZH       | Stäfa          |            222 |                114 |
| ZH       | Maur           |            222 |                181 |
| ZH       | Kilchberg (ZH) |            200 |                135 |
| ZH       | Dübendorf      |            197 |                121 |
| ZH       | Küsnacht (ZH)  |            185 |                 63 |
| ZH       | Zumikon        |            184 |                161 |
| ZH       | Meilen         |            178 |                118 |
| ZH       | Hombrechtikon  |            160 |                137 |

Fokusgemeinden (Kanton Zürich):

| Gemeinde          |   Widersprüche |
|:------------------|---------------:|
| Zürich            |           1469 |
| Winterthur        |            327 |
| Illnau-Effretikon |             50 |
| Fehraltorf        |             12 |
| Volketswil        |              1 |

**Wie robust ist das?** Der Suchradius bestimmt das Ergebnis, deshalb die Sensitivitäts-
rechnung für Zürich (fest in der Vorlage, Lauf vom September 2026):

|   Radius (m) |   Anlagen mit Gebäude |   Gebäude je Anlage |   % Widerspruch |
|-------------:|----------------------:|--------------------:|----------------:|
|           10 |                 26448 |                 1,3 |            13,7 |
|           20 |                 37389 |                 2,4 |            19,1 |
|           50 |                 39284 |                11,3 |            25,6 |

Bei 50 m fängt der Umkreis die halbe Nachbarschaft ein, bei 10 m fehlt einem Drittel der
Anlagen jedes Gebäude. Gewählt sind 20 m: Damit haben 95 % der Anlagen ein Gebäude in der
Nähe, im Schnitt 2,4 Stück. Der Widerspruchsanteil liegt je nach Radius zwischen 13,7 %
und 25,6 %. Die Grössenordnung ist stabil, der exakte Wert nicht.

Bei den Gebäuden rund um eine Wärmenutzungsanlage steht zudem häufig "Unbestimmt" als
Energieträger (Tabelle zum Umkreis oben). Das Register nennt dort keinen Energieträger,
obwohl daneben eine Anlage zur Wärmenutzung verzeichnet ist.

### 2.7 Test 6 - Anlagen mit Datum: Nachführung über die Zeit

Zürich veröffentlicht kein Bohrdatum (87 % der GBS-Nummern beginnen mit "00"), der
Widerspruch aus Test 5 lässt sich dort nicht zeitlich einordnen. Neun Kantone liefern zu
ihren Anlagen ein Datum (Bewilligung, Bohrung oder Erstellung): Appenzell Innerrhoden, Bern,
Basel-Landschaft, Genf, St. Gallen, Solothurn, Schwyz, Thurgau und Zug. Luzern ist ebenfalls
datiert, fällt aber wegen der ungenauen Koordinaten heraus; Zürich, Schaffhausen und Uri
liefern kein Datum.

Ausgewertet werden Anlagen, die als gebaut gelten (Abschnitt 2.6), ohne Konzessionen und
ohne bloss bewilligte oder geplante Anlagen. Anders als bei einem Baugesuch steht damit in
den meisten dieser Kantone fest, dass gebaut wurde. Die Einschränkung: Schwyz führt kein
Statusfeld, und Genf führt bei den meisten Bohrungen den Status "Inconnu" oder "Exploitable",
der keinen Betrieb belegt ([belegwirkung.md](belegwirkung.md)).

Grundmenge: 59'519 Anlagen mit Datum und mindestens einem Gebäude im Umkreis.

| Stand im GWR                                       |   Anlagen |    % |
|:---------------------------------------------------|----------:|-----:|
| nachgeführt (Wärmepumpe im Umkreis eingetragen)    |     39577 | 66,5 |
| unklar (weder Wärmepumpe noch fossil)              |     13282 | 22,3 |
| Widerspruch (fossil eingetragen, keine Wärmepumpe) |      6660 | 11,2 |

**66,5 % nachgeführt, 11,2 % im Widerspruch.** Die restlichen
Fälle sind Gebäude, die weder Wärmepumpe noch fossil ausweisen, meist "Unbestimmt".

Die Entwicklung über die Zeit:

| Alter der Anlage   |   Anlagen |   % nachgeführt |   % Widerspruch |
|:-------------------|----------:|----------------:|----------------:|
| 0-1 Jahre          |      2255 |            56,5 |            27,1 |
| 2-4 Jahre          |      9172 |            77,3 |            10,6 |
| 5-9 Jahre          |     12414 |            69,7 |             9,3 |
| 10-19 Jahre        |     25836 |            63,5 |            10,8 |
| 20+ Jahre          |      9842 |            62,4 |            11,6 |

**Die Nachführung wird besser.** Anlagen, deren Datum 2 bis 4 Jahre zurückliegt, sind zu
77,3 % im Register sichtbar. Bei Anlagen, die 20 Jahre und älter sind, sind es
62,4 %. Der Rückstand liegt überwiegend im Altbestand.

Jahr für Jahr:

|   Jahr der Anlage |   Anlagen |   % nachgeführt |
|------------------:|----------:|----------------:|
|              2016 |      1906 |            62,7 |
|              2017 |      2158 |            62,2 |
|              2018 |      2105 |            64,8 |
|              2019 |      2532 |            69,7 |
|              2020 |      2695 |            71,8 |
|              2021 |      2924 |            76,9 |
|              2022 |      3693 |            76,2 |
|              2023 |      3168 |            79,2 |
|              2024 |      2311 |            76,5 |
|              2025 |      1604 |            62,3 |
|              2026 |       651 |            42,4 |

Von 2016 bis 2023 steigt der Anteil in der Tendenz. Der Rückgang in den jüngsten Jahren ist
der normale Nachlauf: Eine 2025 bewilligte Anlage wird erst gebaut und dann erfasst.

**Was das für die Gesamtbewertung heisst:** Der Befund aus Test 3 bleibt bestehen, wird aber
differenzierter. Der Altbestand bleibt liegen, während der Neuzugang zunehmend erfasst wird.
Die Menge veralteter Einträge aus dieser Quelle nimmt damit eher ab als zu.

---

## 3 Qualität der Zuordnung

Baugesuche werden auf zwei unabhängigen Wegen einem EGID zugeordnet:

- **über die Parzelle:** Der GWR-Gebäudepunkt liegt im Parzellenpolygon aus dem Geopackage
  des Statistischen Amts. Exakt, aber erst ab 2025 verfügbar.
- **über die Adresse:** normalisierte Strasse, Hausnummer und PLZ gegen die GWR-Eingänge.
  Auch für 2024 verfügbar, scheitert bei Sammeladressen wie "Rietstrasse 4b, 4c, 4d".

|   Heizungsgesuche |   mit EGID |   % zugeordnet |   genau 1 Gebäude |   über Parzelle |   über Adresse |
|------------------:|-----------:|---------------:|------------------:|----------------:|---------------:|
|              1753 |       1545 |           88,1 |               832 |            1214 |           1012 |

Insgesamt **88,1 % der Heizungsgesuche** konnten zugeordnet werden, ab 2025 mit
Parzellengeometrie **95,5 %**.

Die beiden Wege dienen sich gegenseitig als Kontrolle:

|   Gesuche mit beiden Wegen |   mindestens ein gemeinsames EGID |   % konsistent |
|---------------------------:|----------------------------------:|---------------:|
|                       7214 |                              7135 |           98,9 |

**98,9 % Übereinstimmung** bei den Gesuchen, die über beide Wege zugeordnet werden.

Die Zuordnung der Photovoltaikanlagen über die Koordinate (nächstes Gebäude, maximal 25 m) ist
gegen die EGID-Spalte der gekürzten BFE-Datei geprüft:

|   vergleichbare Anlagen |   % gleiche EGID wie beim BFE |
|------------------------:|------------------------------:|
|                    8003 |                          94,5 |

### 3.1 Manuelle Stichprobe

`src/report.py` schreibt 20 zufällige Zuordnungen nach
`data/processed/stichprobe_20_matches.md`. Die Datei ist gebäudegenau und deshalb nicht Teil
des Repositories. Ergebnis der Durchsicht:

- **19 von 20** Gesuchstexten betreffen tatsächlich eine Heizung.
- **1 Fehltreffer:** "Einbau Wohnung im Dachgeschoss der Scheune ... **Bestehende** Pelletsheizung
  im Hauptgebäude, WW: WP-Boiler". Die Stichwortsuche kann "bestehend" nicht von "neu" trennen.
  Im ganzen Datensatz enthalten 54 der 1'753 erkannten Gesuche das Wort "bestehend"; das ist
  die Obergrenze für diesen Fehlertyp, rund 3 %.
- Die Zuordnung auf das Gebäude ist bei Fällen mit genau einem Gebäude auf der Parzelle
  überzeugend. Bei Parzellen mit mehreren Gebäuden (z. B. "Gebäude Assek.-Nr. 245 und 246",
  4 Gebäude auf der Parzelle) ist unklar, welches Gebäude gemeint ist. Deshalb arbeitet Test 3
  nur mit den eindeutigen Fällen.

---

## 4 Grenzen der Methode

1. **Baugesuche decken nur einen Teil der Heizungswechsel ab.** Geschätzt 10 bis 20 %
   (Abschnitt 2.2). Der Heizungsersatz im Gebäudeinneren ist in vielen Gemeinden nicht
   bewilligungspflichtig und taucht deshalb nie auf.
2. **Die Publikationspraxis ist uneinheitlich.** Der Anteil der Heizungsgesuche an allen
   Baugesuchen unterscheidet sich stark zwischen den Gemeinden (Abschnitt 2.2). Ein Vergleich
   zwischen Gemeinden misst zum Teil die Publikationspraxis und nicht die Datenqualität.
3. **Ein Baugesuch ist kein Beweis, dass gebaut wurde.** Bewilligungen werden nicht umgesetzt,
   Projekte werden zurückgezogen. Ein Teil der als "nicht nachgeführt" gezählten Fälle ist
   korrekt im GWR, weil dort nichts gebaut wurde. Wie gross dieser Anteil ist, lässt sich
   aus den vorhandenen Daten nicht bestimmen. Das ist die grösste einzelne Unsicherheit
   in Test 3.
4. **Die Stichwortsuche ist grob.** Sie erkennt "bestehende Pelletsheizung" als Heizungsereignis
   und unterscheidet einen Wärmepumpenboiler nicht sicher von einer Heizungswärmepumpe.
   Bei 117 Gesuchen ist kein neuer Energieträger bestimmt ("unklar"). Wie viel eine Prüfung
   der Texte durch ein Sprachmodell daran verbessert, steht in
   [extraktion_evaluation.md](extraktion_evaluation.md).
5. **Der GWR-Snapshot ist eine Momentaufnahme.** Ob ein Eintrag zwischen Baugesuch und
   Exportdatum einmal geändert und wieder überschrieben wurde, ist nicht sichtbar. Die
   Bewegung im Register über die Zeit steht in [zeitreihe.md](zeitreihe.md).
6. **Einzelne Gemeinden haben zu wenige Fälle.** Die Gemeindetabelle in Test 3 ist auf
   Gemeinden mit mindestens 8 Fällen beschränkt; darunter wird der Anteil zu instabil.
7. **Mehrfachpublikationen verzerren rohe Zählungen.** 22,4 % der Publikationen
   wiederholen ein bereits vorhandenes Vorhaben. Wer die Rohdaten ohne Deduplizierung
   auswertet, kommt auf rund ein Fünftel zu hohe Fallzahlen.
8. **Keine Personendaten.** Die Baugesuchsdaten sind bereits um Namen und Adressen der
   Beteiligten bereinigt. Gebäudegenaue Ergebnisse werden nicht veröffentlicht; die
   Verdachtslisten liegen ausserhalb des Git.

---

## 5 Entscheidung

Die vor der Auswertung festgelegten Kriterien der Studie:

| Kriterium | Ergebnis | erfüllt |
|---|---|---|
| Test 3 zeigt eine grosse Lücke | 40,6 % nicht nachgeführt, 43,2 % nachgeführt, weit gefasst 49,1 % | ja |
| Test 2 liefert genug Fälle | Median 1,6 Heizungsgesuche pro Gemeinde und Jahr | nein |
| Abbruchkriterium: über 80 % nachgeführt | in keinem Altersfenster erreicht | nein |
| Abbruchkriterium: nur eine Handvoll Gesuche pro Gemeinde | trifft auf drei Viertel der Gemeinden zu | ja |
| Zusatzbefund: Liegt der Rückstand im Altbestand? | ja, Erfassung 62,4 % bei Anlagen ab 20 Jahren, 77,3 % bei Anlagen aus den letzten 2 bis 4 Jahren | kein Kriterium |

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.**

Begründung:

- Die Lücke ist nachweisbar: Der Anteil nachgeführter Baugesuche liegt weit unter der
  Schwelle von 80 %.
- Baugesuche allein reichen als Beleg nicht. Die mittlere Gemeinde kommt auf
  1,6 Heizungs-Baugesuche pro Jahr; für eine Auswertung je Gemeinde ist das
  zu wenig.
- Gleichzeitig wird bereits in grossem Umfang nachgeführt: 22'060 aktualisierte
  Heizungseinträge allein 2026. Ein Abgleich aus offenen Daten kann vor allem die Lücke
  zwischen zwei Sammelaktualisierungen sichtbar machen.
- **Der Rückstand liegt im Altbestand.** Der Zeitverlauf der datierten Anlagen (Abschnitt 2.7)
  zeigt es: 62,4 % Erfassung bei Anlagen ab 20 Jahren, 77,3 % bei Anlagen aus den
  letzten 2 bis 4 Jahren. Das spricht für eine einmalige Bereinigung und gegen eine
  Dauerüberwachung.
- Methodisch ist die Fragestellung gut prüfbar: offene Daten in brauchbarer Qualität, eine
  Zuordnungsaufgabe (Entity Resolution), eine Textextraktion und eine Evaluation gegen
  kantonale Gegenquellen.

### Was aus dem Befund folgt

Für eine Weiterführung des Abgleichs ergibt sich aus den Daten:

- **Die passende Ebene ist der Kanton oder eine Stadt, nicht die einzelne Gemeinde.** Zürich und
  Winterthur haben mit Abstand die meisten Heizungs-Baugesuche (Abschnitt 2.2), und beide
  zeigen mit 70,7 % und 55,9 % grosse Lücken.
- **Baugesuche reichen als Belegquelle nicht.** Es braucht weitere Quellen, etwa
  Feuerungskontrolle, Förderdaten des Gebäudeprogramms, Gasnetz-Abmeldungen und die
  Pronovo-Anlagendaten. Welche davon offen zugänglich sind, steht in
  [quellenvergleich.md](quellenvergleich.md).
- **Wärmenutzungsanlagen sind die ergiebigste offene Quelle.** Sie liefern einen direkten
  Widerspruch statt eines Indizes, sind in 13 Kantonen offen verfügbar und in
  neun davon datiert.
- **Naheliegend ist eine einmalige Bereinigung, keine Dauerüberwachung.** Der Rückstand
  liegt im Altbestand.
- **Offen ist die Sicht der kantonalen Fachstelle.** Ob die fehlende Nachführung bei
  70,7 % der Stadtzürcher Heizungs-Baugesuche dort als Problem gilt und wer dafür
  zuständig ist, lässt sich aus den Daten nicht beantworten.

---

## 6 Folgearbeiten

Die Detailauswertung vom September 2026 nennt fünf Folgearbeiten. Ihr Stand:

1. **Textextraktion mit einem Sprachmodell.** Umgesetzt als Prüfschritt nach der
   Stichwortsuche und an 150 gelabelten Texten gemessen
   ([extraktion_evaluation.md](extraktion_evaluation.md)).
2. **Weitere Belegquellen.** Umgesetzt für Wärmenutzungsanlagen aus 13 Kantonen,
   Baugesuche aus dem Amtsblattportal und Photovoltaik in allen Kantonen
   ([quellenmatrix.md](quellenmatrix.md), [docs/datenquellen.md](../docs/datenquellen.md)).
3. **GWR-Snapshots.** Seit September 2026 liegt je Woche ein Snapshot vor. Damit ist die
   Nachführung als Ereignis messbar ([zeitreihe.md](zeitreihe.md)).
4. **Architektur.** Bronze: GWR-Snapshots, Baugesuche, Anlagendaten, je mit Manifest und
   Ladedatum. Silver: Textextraktion der Heizungsereignisse, Zuordnung Baugesuch zu EGID
   über Parzelle und Adresse. Gold: Belege je Gebäude, Stufe, Auswertung je Gemeinde
   ([docs/methode.md](../docs/methode.md)).
5. **Evaluation.** Extraktion: [extraktion_evaluation.md](extraktion_evaluation.md).
   Zuordnung: Abschnitt 3 und [zuordnung_zg.md](zuordnung_zg.md). Trefferquote der
   Verdachtsfälle: [belegwirkung.md](belegwirkung.md), gemessen an kantonalen Gegenquellen.
   Eine Gegenprüfung durch eine Gemeinde ist nicht Teil dieser Studie.

---

## Reproduzierbarkeit

```bash
python src/download.py     # Rohdaten laden, Manifest schreiben
python src/build_db.py     # Bronze-Layer in DuckDB
python src/report.py       # Pipeline rechnen und diesen Report erzeugen
```
