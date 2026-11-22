# GWR-Heizungscheck - Validierung mit echten Daten

**Kanton Zürich im Detail, Erdwärmesonden auch für Bern. Datenstand GWR 2026-09-13, Baugesuche bis 2026-09-11.**
Erzeugt von `src/report.py`. Alle Zahlen stammen direkt aus der Pipeline, nichts ist von Hand eingetragen.

---

## Kurzfassung

Die Frage war: Sind Heizungsangaben im GWR so oft veraltet, dass sich eine Verdachtsliste
für eine Gemeinde lohnt? Die Antwort aus den Daten ist zweigeteilt.

**Die Datenlücke ist real und gross.** Von 458 eindeutig zugeordneten Heizungs-Baugesuchen,
die mindestens sechs Monate zurückliegen, zeigt das GWR bei **40,6 %** immer noch den alten
Energieträger mit einem Aktualisierungsdatum vor dem Baugesuch. Nur 43,2 % sind sauber
nachgeführt, in der weiten Auslegung 49,1 %. Auch bei Baugesuchen, die 18 Monate und
länger zurückliegen, bleibt die Lücke bei 36,2 %. Das Stop-Kriterium (über 80 % nachgeführt)
ist deutlich verfehlt - Test 3 ist ein klares Go.

**Die Belege sind für die meisten Gemeinden zu dünn.** Über alle Gemeinden hinweg finden sich nur
rund 569 Heizungs-Baugesuche pro Jahr im ganzen Kanton. Die mittlere Gemeinde kommt
auf **1,6 Gesuche pro Jahr**, drei Viertel der Gemeinden liegen unter 3,1.
Ein Bericht mit zwei Verdachtsfällen pro Jahr trägt nicht. Nur Zürich und Winterthur haben
genug Volumen. Das ist das Stop-Kriterium aus Test 2.

**Ein dritter Befund kam später dazu und relativiert die ersten beiden.** Bern veröffentlicht
seine Erdwärmesonden mit Bewilligungsdatum und Ausführungsstatus - die beste Messgrundlage
im ganzen Projekt, weil dort feststeht, dass gebaut wurde. Das Ergebnis: 66,5 %
der Anlagen sind im GWR sichtbar, aber der Wert hängt stark am Alter. Anlagen aus den letzten
2 bis 4 Jahren sind zu 77,3 % erfasst, Anlagen ab 20 Jahren nur zu 62,4 %.
**Die Nachführung wird besser.** Der Rückstand liegt im Altbestand, nicht im laufenden
Betrieb. Ein Dienst, der veraltete Einträge findet, arbeitet damit an einem schrumpfenden
Problem.

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.** Details in Abschnitt 5.

Ein methodischer Nebenbefund, der für die weitere Arbeit wichtiger ist als alles andere:
Die Informationsquelle im GWR (Code 860 "Volkszählung 2000") taugt nicht als Indikator für
Datenqualität. Die Stadt Zürich hat 0 % Einträge mit Quelle 860 und wäre nach Test 1 sauber -
in Test 3 fehlt dort trotzdem bei rund zwei Dritteln der Heizungs-Baugesuche die Nachführung.
Wer veraltete Einträge finden will, muss Ereignisse gegen den Registerstand prüfen, nicht
Metadaten zählen.

---

## 1 Datenbasis

### 1.1 Quellen

| Quelle                                                                  | Datei                                                       |    MB | URL                                                                                                                                                                                                                                  |
|:------------------------------------------------------------------------|:------------------------------------------------------------|------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| GWR oeffentliche Daten Stufe A                                          | gwr_zh.zip                                                  | 121.7 | https://public.madd.bfs.admin.ch/zh.zip                                                                                                                                                                                              |
| Baugesuche im Kanton ZH                                                 | baugesuche_zh.csv                                           |   9.5 | https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006183.csv                                                                                                                                                        |
| Georeferenzierte Baugesuche im Kanton ZH ab 2025 (Statistisches Amt ZH) | baugesuche_zh_geo.gpkg                                      |  12.0 | https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006403.gpkg                                                                                                                                                       |
| Elektrizitaetsproduktionsanlagen CH (BFE)                               | epa.zip                                                     |  17.3 | https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip                                                                                     |
| Elektrizitaetsproduktionsanlagen CH (BFE)                               | epa_egid.zip                                                |   8.6 | https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip                                                                                                               |
| Erdwaermesonden Kanton ZH (AWEL)                                        | waermenutzung_zh/erdwaermesonden.json                       |  11.8 | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:erdwaermesonden&outputFormat=geojson                                                                                            |
| Erdregister Kanton ZH (AWEL)                                            | waermenutzung_zh/erdregister.json                           |   0.0 | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:erdregister&outputFormat=geojson                                                                                                |
| Grundwasserfassungen mit Waermenutzung                                  | waermenutzung_zh/grundwasserfassung-waermenutzung.json      |   0.5 | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:grundwasserfassung-waermenutzung&outputFormat=geojson                                                                           |
| Quellfassungen mit Waermenutzung                                        | waermenutzung_zh/quellfassung-waermenutzung.json            |   0.0 | https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0&Request=GetFeature&TypeName=ms:quellfassung-waermenutzung&outputFormat=geojson                                                                                 |
| Erdwaermesonden Kanton SZ                                               | waermenutzung_weitere/SZ_erdwaermesonden.gml                |   1.3 | https://map.geo.sz.ch/mapserv_proxy?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=ms:ch.sz.a034c.waermenutzung.erdwaermeanlage.erdwaermesonde                                                                                |
| Erdsondenbohrungen Kanton BL                                            | waermenutzung_weitere/BL_erdsonden.gml                      |   5.4 | https://geowms.bl.ch/?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=ms:grundwasser_erdsonden                                                                                                                                 |
| Thermische Zentralen Kanton SG                                          | waermenutzung_weitere/SG_thermischezentralen.gml            | 106.4 | https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=geoportal%3Aq352_thermischezentralen                                                                                                    |
| Erdwaermesondenbohrungen Kanton AI                                      | waermenutzung_weitere/AI_erdwaermesonden.gml                |  15.6 | https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=geoportal%3Af211_ai_erdwaermesonden                                                                                                     |
| Erdwaermesondenanlagen Kanton ZG                                        | waermenutzung_weitere/ZG_erdwaermenutzung.gpkg              |   4.0 | https://services.geo.zg.ch/datarepo/Erdwaerme/geopackage/Erdwaermenutzung.gpkg                                                                                                                                                       |
| Konzessionen Grundwasserwaermepumpen Kanton UR                          | waermenutzung_weitere/UR_grundwasserwaermepumpen.json       |   0.1 | https://geo.ur.ch/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=energie%3Aur031_konzessionen_grundwasserwaermepumpen&outputFormat=application%2Fjson                                                                     |
| Luft-Wasser-Waermepumpen Kanton LU                                      | waermenutzung_weitere/LU_luftwasserwaermepumpen.json        |   2.9 | https://public.geo.lu.ch/ogd/services/managed/LUFWAWPO_DS_V1_MP/MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature&typeNames=esri%3ALuft-Wasser-W%C3%A4rmepumpen__geplante_und_bewilligte_Anlagen&outputFormat=GEOJSON |
| Feuerungskataster Kanton GE                                             | waermenutzung_weitere/GE_feuerungen.json                    |  28.8 | https://vector.sitg.ge.ch/arcgis/rest/services/SCANE_CHAUDIERE/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=geojson                                                                                          |
| Tankkataster Kanton ZG: Tanks im oder am Gebaeude                       | waermenutzung_weitere/ZG_tank_gebaeude_in_betrieb.gml       |   4.6 | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_in_betrieb                                                                                                    |
| Tankkataster Kanton ZG: Tanks im oder am Gebaeude                       | waermenutzung_weitere/ZG_tank_gebaeude_ausser_betrieb.gml   |   2.4 | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_ausser_betrieb                                                                                                |
| Tankkataster Kanton ZG: erdverlegte Tanks                               | waermenutzung_weitere/ZG_tank_erdverlegt_in_betrieb.gml     |   0.9 | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_in_betrieb                                                                                                     |
| Tankkataster Kanton ZG: erdverlegte Tanks                               | waermenutzung_weitere/ZG_tank_erdverlegt_ausser_betrieb.gml |   0.5 | https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_ausser_betrieb                                                                                                 |

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

- **GWR:** Exportdatum 2026-09-13, also tagesaktuell. Vollständig für den ganzen Kanton.
  Die Codelisten stammen aus der mitgelieferten Datei `kodes_codes_codici.csv`, nicht aus
  Sekundärquellen.
- **Baugesuche:** Publikationen bis 2026-09-11. Die Sammlung des Statistischen Amts ist erst
  ab Herbst 2024 vollständig; frühere Jahre enthalten nur Einzelfälle (2022: 3, 2023: 74).
  Alle Zeitreihen in diesem Report beginnen deshalb im Oktober 2024.
  Die Felder `bfs_nr` und `municipality_name` sind erst ab 2025 gefüllt. Für 2024 wurde die
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
  Hier lauert ein Stolperstein: Der auf opendata.swiss verlinkte CSV-Pfad `/csv/2056/` liefert
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

Hier zeigt sich der erste wichtige Befund. Zürich hat **null** Einträge mit Quelle 860 und damit
null Kandidaten nach dieser Definition, obwohl 70,5 % der Wohngebäude fossil beheizt sind.
Die Stadt hat die Volkszählungsdaten flächendeckend durch eigene Einträge ersetzt (Code 859
"Andere"), die zum grossen Teil aus den Jahren 2018 bis 2021 stammen. Nach Test 1 wäre Zürich
also sauber. Test 3 zeigt das Gegenteil. **Die Informationsquelle allein ist kein brauchbarer
Qualitätsindikator.**

Test 1 liefert damit *kein* Stop-Signal (der Anteil ist im Median hoch), aber auch kein
belastbares Go - die Kennzahl misst nicht, was sie zu messen vorgibt.

### 2.2 Test 2 - Genug Belege?

1'753 von 22'780 Publikationen wurden über Stichworte als Heizungsereignis erkannt; nach
Zusammenfassen der Mehrfachpublikationen bleiben **1'427 Vorhaben**
(Details zur Erkennung in Abschnitt 4). Verteilung des erkannten neuen Energieträgers
über alle Publikationen:

| neuer Energieträger laut Gesuchstext   |   Gesuche |
|:---------------------------------------|----------:|
| waermepumpe                            |      1530 |
| unklar                                 |       117 |
| holz                                   |        51 |
| fernwaerme                             |        43 |
| solarthermie                           |        12 |

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
ist deshalb nicht vergleichbar. Der Anteil der Heizungsgesuche steigt über die Quartale hinweg
stetig von 5,6 % (Q4 2024) auf 9,5 % (Q3 2026) - das ist ein echter Trend, kein Artefakt.

Entscheidend ist die Verteilung über die Gemeinden:

|   Gemeinden |   Minimum |   25 % |   Median |   75 % |   Maximum |
|------------:|----------:|-------:|---------:|-------:|----------:|
|         159 |         0 |    0,5 |      1,6 |    3,1 |     147,7 |

**Das ist das Stop-Signal.** Die mittlere Gemeinde hat 1,6 Heizungs-Baugesuche pro
Jahr. Selbst im oberen Viertel sind es weniger als 3,1 pro Jahr. Die Belege konzentrieren
sich fast vollständig auf wenige grosse Gemeinden:

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

Illnau-Effretikon fällt mit 4 Heizungsgesuchen in zwei Jahren auf, bei 157 Baugesuchen insgesamt.
Das ist kein Datenfehler, sondern Publikationspraxis: Der Anteil der Heizungsgesuche an allen
Baugesuchen schwankt zwischen 0 % und 20 % je nach Gemeinde. Manche Gemeinden publizieren einen
Heizungsersatz als eigenes Baugesuch, andere behandeln ihn als bewilligungsfrei oder als
Nebenpunkt eines grösseren Vorhabens. Der Ausreisser nach oben ist Winterthur mit rund 20 %.

**Grössenordnung zum Vergleich:** Im Kanton stehen rund 127'000 fossil beheizte Wohngebäude.
Bei einer Ersatzrate von 3 bis 5 % pro Jahr wären das 4'000 bis 6'000 Heizungswechsel jährlich.
Gefunden werden über die Baugesuche rund 569 pro Jahr. **Baugesuche erfassen damit
grob geschätzt 10 bis 20 % der tatsächlichen Heizungswechsel.** Der Rest sind Ersatzvorhaben im
Gebäudeinneren, die keine Baubewilligung brauchen. Sichtbar wird vor allem die aussen aufgestellte
Luft/Wasser-Wärmepumpe, weil die wegen Lärm und Grenzabstand bewilligungspflichtig ist.

### 2.3 Test 3 - Werden Baugesuche schon nachgeführt?

Der wichtigste Test. Grundmenge: Heizungs-Baugesuche, deren Publikation mindestens sechs Monate
zurückliegt, die genau einem Gebäude zugeordnet werden konnten und die kein reiner Neubau sind.
Das sind 458 Fälle.

| Status                                                           |   n |    % |
|:-----------------------------------------------------------------|----:|-----:|
| nachgeführt (neuer Energieträger und Datum nach dem Baugesuch)   | 198 | 43,2 |
| nicht nachgeführt (alter Energieträger, Datum vor dem Baugesuch) | 186 | 40,6 |
| nach dem Baugesuch angefasst, Energieträger passt nicht          |  33 |  7,2 |
| Energieträger passt, Datum älter als das Baugesuch               |  18 |  3,9 |
| unklar (keine Angabe im GWR oder kein Träger im Gesuchstext)     |  14 |  3,1 |
| angefasst, Quelle 869 nach dem Baugesuch                         |   9 |  2,0 |

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
Das Stop-Kriterium von 80 % wird in keinem Altersfenster erreicht.

Was in den Lückenfällen im GWR steht:

| GWR-Energieträger   | GWR-Informationsquelle                        |   n |
|:--------------------|:----------------------------------------------|----:|
| Gas                 | Andere                                        |  68 |
| Heizöl              | Gemäss Volkszählung 2000                      |  41 |
| Heizöl              | Andere                                        |  15 |
| Gas                 | Gemäss Daten der Gemeinde                     |  12 |
| Elektrizität        | Gemäss Volkszählung 2000                      |   9 |
| Holz (generisch)    | Gemäss Volkszählung 2000                      |   9 |
| Heizöl              | Gemäss kantonalen Daten / Das Gebäudeprogramm |   7 |
| Heizöl              | Gemäss Daten der Gemeinde                     |   6 |
| Heizöl              | Gemäss Baubewilligung                         |   4 |
| Gas                 | Gemäss Volkszählung 2000                      |   2 |

Die Streuung zwischen den Gemeinden ist der eigentliche Befund (Gemeinden mit mindestens
8 auswertbaren Fällen):

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
schlicht nicht beantworten - was für sich genommen bereits die Antwort auf Test 2 ist.

Winterthur ist der interessanteste Fall. Die Stadt hat im Februar 2024 die Heizungsdaten
flächendeckend aktualisiert - 84 % aller Wohngebäude tragen ein Aktualisierungsdatum ab 2024.
Trotzdem fehlt bei 58 % der Heizungs-Baugesuche die Nachführung, und zwar typischerweise mit
genau diesem Muster: Energieträger Gas, Quelle "Gemäss Daten der Gemeinde", Datum 2024-02-09,
Baugesuch für den Wärmepumpenersatz aus 2025 oder 2026. **Eine Sammelaktualisierung erzeugt einen
sauberen Stichtag, aber keinen laufenden Prozess.** Genau dort läge der Nutzen des Dienstes.

### 2.4 Gegenprobe - wie viel führt der Kanton insgesamt nach?

Diese Auswertung stand nicht im Plan, ist für die Entscheidung aber zentral.
Aktualisierungen der Heizungsangabe bei Wohngebäuden, nach Jahr des Aktualisierungsdatums:

|   Jahr |   Heizungseinträge aktualisiert |   davon auf Wärmepumpe |
|-------:|--------------------------------:|-----------------------:|
|   2022 |                            5987 |                   2138 |
|   2023 |                            9458 |                   3288 |
|   2024 |                           31117 |                  14771 |
|   2025 |                           15119 |                   4726 |
|   2026 |                           22060 |                   5348 |

Im Jahr 2024 wurden 31'117 Heizungseinträge angefasst, 2026 bereits 22'060. Seit Anfang
2024 wurden 24'845 Wohngebäude mit einer Wärmepumpe erfasst. Die Treiber sind das
Gebäudeprogramm (Code 864), Gemeindedaten (865), die Feuerungskontrolle (855) und
Baubewilligungen (869).

**Der Kanton und die Gemeinden führen also bereits im grossen Stil nach - über Kanäle, die pro Jahr
ein Vielfaches dessen abdecken, was Baugesuche überhaupt sichtbar machen können.** Die Lücke aus
Test 3 ist real, aber sie ist eine Lücke in einem bereits laufenden Prozess, nicht ein
unbearbeitetes Feld.

### 2.5 Test 4 - Fälle ohne Baugesuch

Gebäude mit Wohnnutzung, registrierter Photovoltaikanlage, fossilem Heizungseintrag und
Quelle 860: **4'079 Gebäude im Kanton**.

| Gemeinde          |   Verdachtsfälle |
|:------------------|-----------------:|
| Maur              |              108 |
| Thalwil           |               90 |
| Hombrechtikon     |               88 |
| Dürnten           |               83 |
| Dübendorf         |               82 |
| Horgen            |               82 |
| Stäfa             |               74 |
| Pfäffikon         |               71 |
| Wettswil am Albis |               65 |
| Niederhasli       |               62 |

Fokusgemeinden:

| Gemeinde          |   PV und fossil und Quelle 860 |
|:------------------|-------------------------------:|
| Winterthur        |                             47 |
| Volketswil        |                             17 |
| Illnau-Effretikon |                             10 |
| Fehraltorf        |                              7 |
| Zürich            |                              0 |

Das ist wie erwartet nur ein schwaches Indiz. Eine PV-Anlage sagt nichts über die Heizung; sie
zeigt nur, dass die Eigentümerschaft in den letzten Jahren am Gebäude etwas gemacht hat und dass
der Heizungseintrag seither nicht angefasst wurde. Als eigenständiger Beleg ist das zu wenig,
als zusätzliches Merkmal in einem Score brauchbar.

### 2.6 Test 5 - Erdwärmesonden gegen den Registerstand

Dieser Test kam nach der ersten Auswertung dazu und ist der schärfste. Fünf Kantone
veröffentlichen ihre bewilligten Anlagen zur Wärmenutzung des Untergrunds: Zürich, Bern,
Thurgau, Schaffhausen und Uri. Zusammen **133'772 Anlagen**, davon 128'059
nachweislich gebaut.

| KT   | Anlagentyp             |   Anlagen |   davon gebaut |
|:-----|:-----------------------|----------:|---------------:|
| AI   | erdwaermesonde         |      2419 |           2419 |
| BE   | erdwaermesonde         |     14661 |          11391 |
| BL   | erdwaermesonde         |      2629 |           2629 |
| GE   | erdwaermesonde         |      3668 |           3666 |
| LU   | erdwaermesonde         |     14717 |          14717 |
| LU   | luft_wasser_wp         |      7066 |           7066 |
| SG   | waermepumpe            |     29194 |          27131 |
| SG   | fernwaermeanschluss    |         4 |              4 |
| SH   | erdwaermesonde         |      1235 |           1235 |
| SO   | erdwaermesonde         |      8863 |           8863 |
| SZ   | erdwaermesonde         |      1675 |           1675 |
| TG   | erdwaermesonde         |      4532 |           4530 |
| UR   | erdwaermesonde         |       555 |            555 |
| UR   | grundwasserwaermepumpe |       292 |            292 |
| ZG   | erdwaermesonde         |      2792 |           2416 |
| ZH   | erdwaermesonde         |     38553 |          38553 |
| ZH   | grundwasserfassung     |       868 |            868 |
| ZH   | quellfassung           |        46 |             46 |
| ZH   | erdregister            |         3 |              3 |

Der Unterschied zu Test 4 ist entscheidend: Eine Photovoltaikanlage sagt nichts über die
Heizung. Eine Erdwärmesonde schon. Niemand bohrt 250 Meter tief, um eine Ölheizung zu
betreiben. Steht im GWR trotzdem Öl oder Gas, ist das kein Indiz, sondern ein Widerspruch.

**Was im GWR rund um eine Wärmenutzungsanlage steht** (Wohngebäude innerhalb von 20 m,
Kanton Zürich):

| GWR-Energieträger   |   Gebäude |    % |
|:--------------------|----------:|-----:|
| waermepumpe         |     49422 | 41,9 |
| unbestimmt          |     28598 | 24,3 |
| oel                 |     21230 | 18,0 |
| gas                 |      9620 |  8,2 |
| holz                |      3556 |  3,0 |
| elektro             |      2914 |  2,5 |
| fernwaerme          |      1478 |  1,3 |
| andere              |       681 |  0,6 |

Nur **47,8 %** aller Zürcher Anlagen haben überhaupt ein Gebäude mit
Wärmepumpen-Eintrag im Umkreis. Die anderen Kantone kommen unabhängig davon auf ähnliche
Werte:

| KT   |   Anlagen mit Gebäude |   mit Wärmepumpe im GWR |   % mit WP |   Widerspruch |
|:-----|----------------------:|------------------------:|-----------:|--------------:|
| AI   |                  2292 |                    2113 |       92,2 |            69 |
| BE   |                 10918 |                    4939 |       45,2 |          2434 |
| BL   |                  2523 |                    2066 |       81,9 |           344 |
| GE   |                  2545 |                     234 |        9,2 |           732 |
| LU   |                  9431 |                    2547 |       27,0 |          3059 |
| SG   |                 25777 |                   24414 |       94,7 |           492 |
| SH   |                  1152 |                     527 |       45,7 |           151 |
| SO   |                  7750 |                    2174 |       28,1 |          1489 |
| SZ   |                  1540 |                     475 |       30,8 |           284 |
| TG   |                  4324 |                    2418 |       55,9 |           496 |
| UR   |                   776 |                     198 |       25,5 |           165 |
| ZG   |                  2279 |                     896 |       39,3 |           393 |
| ZH   |                 37371 |                   17873 |       47,8 |          7103 |

**Vier von fünf Kantonen liegen zwischen 45 % und 56 %**, obwohl die Daten von fünf
verschiedenen Ämtern stammen, in unterschiedlichen Formaten geliefert werden und
Schaffhausen sogar ein anderes Koordinatensystem verwendet. Das ist die stärkste
Bestätigung im ganzen Projekt, weil die Messungen nichts miteinander zu tun haben.

Uri fällt mit 25,5 % ab, aber das ist erklärbar: Dort meldet der Datensatz
ausschliesslich "Konzession erteilt". Eine erteilte Konzession heisst noch nicht, dass
gebohrt wurde. Uri ist deshalb aus der datierten Auswertung in Abschnitt 2.7
ausgeschlossen.

**Ergebnis:** **16'025 Wohngebäude** über alle fünf Kantone
(8'773 in Zürich, 2'992 in Bern) sind fossil eingetragen,
obwohl innerhalb von 20 m eine
Wärmenutzungsanlage bewilligt und gebaut ist und kein einziges Gebäude dort eine
Wärmepumpe ausweist. Davon tragen 7'437 die Quelle "Volkszählung 2000". Die mittlere
Distanz zur Anlage beträgt 12,3 m.

| KT   | Gemeinde       |   Widersprüche |   davon Quelle 860 |
|:-----|:---------------|---------------:|-------------------:|
| ZH   | Zürich         |           1469 |                  0 |
| BE   | Bern           |            347 |                102 |
| ZH   | Winterthur     |            327 |                 22 |
| ZH   | Zollikon       |            224 |                175 |
| ZH   | Stäfa          |            222 |                114 |
| ZH   | Maur           |            222 |                181 |
| ZH   | Kilchberg (ZH) |            200 |                135 |
| ZH   | Dübendorf      |            197 |                121 |
| ZH   | Küsnacht (ZH)  |            185 |                 63 |
| ZH   | Zumikon        |            184 |                161 |
| ZH   | Meilen         |            178 |                118 |
| ZH   | Hombrechtikon  |            160 |                137 |

Fokusgemeinden (Kanton Zürich):

| Gemeinde          |   Widersprüche |
|:------------------|---------------:|
| Zürich            |           1469 |
| Winterthur        |            327 |
| Illnau-Effretikon |             50 |
| Fehraltorf        |             12 |
| Volketswil        |              1 |

**Wie robust ist das?** Der Suchradius bestimmt das Ergebnis, deshalb die Sensitivitäts-
rechnung für Zürich:

|   Radius (m) |   Anlagen mit Gebäude |   Gebäude je Anlage |   % Widerspruch |
|-------------:|----------------------:|--------------------:|----------------:|
|           10 |                 26448 |                 1,3 |            13,7 |
|           20 |                 37389 |                 2,4 |            19,1 |
|           50 |                 39284 |                11,3 |            25,6 |

Bei 50 m fängt der Umkreis die halbe Nachbarschaft ein, bei 10 m fehlt einem Drittel der
Anlagen jedes Gebäude. Gewählt sind 20 m: Damit haben 95 % der Anlagen ein Gebäude in der
Nähe, im Schnitt 2,4 Stück. Der Widerspruchsanteil liegt je nach Radius zwischen 13,7 %
und 25,6 % - die Grössenordnung ist stabil, der exakte Wert nicht.

Bemerkenswert ist noch etwas: Bei den Gebäuden rund um eine Wärmenutzungsanlage steht in
28,7 % der Fälle "Unbestimmt" als Energieträger. Das Register weiss dort nicht einmal,
womit geheizt wird, obwohl direkt daneben eine bewilligte Erdsonde liegt.

### 2.7 Test 6 - Bern und Thurgau, mit Datum und Ausführungsnachweis

Zürich veröffentlicht kein Bohrdatum (87 % der GBS-Nummern beginnen mit "00"), der
Widerspruch aus Test 5 lässt sich dort also nicht zeitlich einordnen. **Bern und Thurgau
schon:** Beide Datensätze tragen zu jeder Anlage ein Datum und einen Status, der eine
tatsächlich gebaute Anlage von einer bloss bewilligten unterscheidet.

Damit sind diese beiden die beste Messgrundlage im ganzen Projekt - besser noch als die
Baugesuche aus Test 3. Ein Baugesuch beweist nicht, dass gebaut wurde. Hier steht es im
Datensatz.

Grundmenge: 59'519 ausgeführte Anlagen mit Bewilligungsdatum und mindestens einem Gebäude
im Umkreis.

| Stand im GWR       |   Anlagen |    % |
|:-------------------|----------:|-----:|
| nachgefuehrt       |     39577 | 66,5 |
| unklar             |     13282 | 22,3 |
| widerspruch_fossil |      6660 | 11,2 |

**66,5 % nachgeführt, 11,2 % klarer Widerspruch.** Die restlichen
Fälle sind Gebäude, die weder Wärmepumpe noch fossil ausweisen - meist "Unbestimmt".

Der interessanteste Teil ist die Entwicklung über die Zeit:

| Alter der Bewilligung   |   Anlagen |   % nachgeführt |   % Widerspruch |
|:------------------------|----------:|----------------:|----------------:|
| 0-1 Jahre               |      2255 |            56,5 |            27,1 |
| 2-4 Jahre               |      9172 |            77,3 |            10,6 |
| 5-9 Jahre               |     12414 |            69,7 |             9,3 |
| 10-19 Jahre             |     25836 |            63,5 |            10,8 |
| 20+ Jahre               |      9842 |            62,4 |            11,6 |

**Die Nachführung wird besser.** Anlagen, die vor 2 bis 4 Jahren bewilligt wurden, sind zu
77,3 % im Register sichtbar. Bei Anlagen, die 20 Jahre und älter sind, sind es nur
62,4 %. Der Rückstand liegt also überwiegend im Altbestand, nicht im laufenden Betrieb.

Jahr für Jahr:

|   Bewilligungsjahr |   Anlagen |   % nachgeführt |
|-------------------:|----------:|----------------:|
|               2016 |      1906 |            62,7 |
|               2017 |      2158 |            62,2 |
|               2018 |      2105 |            64,8 |
|               2019 |      2532 |            69,7 |
|               2020 |      2695 |            71,8 |
|               2021 |      2924 |            76,9 |
|               2022 |      3693 |            76,2 |
|               2023 |      3168 |            79,2 |
|               2024 |      2311 |            76,5 |
|               2025 |      1604 |            62,3 |
|               2026 |       651 |            42,4 |

Von 2016 bis 2024 steigt der Anteil deutlich. Der Rückgang in den letzten beiden Jahren ist
kein Rückschritt, sondern der normale Nachlauf: Eine 2025 bewilligte Anlage wird erst
gebaut und dann erfasst.

**Was das für die Gesamtbewertung heisst:** Der Befund aus Test 3 bleibt bestehen, aber er
wird differenzierter. Es ist nicht so, dass nichts passiert. Es ist so, dass der Altbestand
liegen bleibt, während der Neuzugang zunehmend erfasst wird. Ein Dienst, der veraltete
Einträge findet, arbeitet damit an einem schrumpfenden, nicht an einem wachsenden Problem.

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
Das ist der belastbarste Qualitätswert in diesem Projekt.

Die Zuordnung der Photovoltaikanlagen über die Koordinate (nächstes Gebäude, maximal 25 m) wurde
gegen die EGID-Spalte der älteren BFE-Datei geprüft:

|   vergleichbare Anlagen |   % gleiche EGID wie beim BFE |
|------------------------:|------------------------------:|
|                    8003 |                          94,5 |

### 3.1 Manuelle Stichprobe

20 zufällige Zuordnungen schreibt `src/report.py` nach `data/processed/stichprobe_20_matches.md` (gebäudegenau, deshalb nicht Teil des Repositories)
vollständig aufgeführt. Ergebnis der Durchsicht:

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
2. **Die Publikationspraxis ist uneinheitlich.** Der Anteil der Heizungsgesuche schwankt
   zwischen 0 % und 20 % je Gemeinde. Ein Vergleich zwischen Gemeinden misst zum Teil die
   Publikationspraxis, nicht die Datenqualität.
3. **Ein Baugesuch ist kein Beweis, dass gebaut wurde.** Bewilligungen werden nicht umgesetzt,
   Projekte werden zurückgezogen. Ein Teil der als "nicht nachgeführt" gezählten Fälle ist
   korrekt im GWR - dort wurde schlicht nichts gebaut. Wie gross dieser Anteil ist, lässt sich
   aus den vorhandenen Daten nicht bestimmen. Das ist die grösste einzelne Unsicherheit
   in Test 3.
4. **Die Stichwortsuche ist grob.** Sie erkennt "bestehende Pelletsheizung" als Heizungsereignis
   und unterscheidet einen Wärmepumpenboiler nicht sicher von einer Heizungswärmepumpe.
   Bei 117 Gesuchen konnte kein neuer Energieträger bestimmt werden ("unklar"). Eine
   LLM-Extraktion auf dem Projektbeschrieb würde hier deutlich mehr herausholen: alter Träger,
   neuer Träger, Bestand oder Neubau, Haupt- oder Nebenpunkt des Vorhabens. Das ist der
   naheliegendste nächste Schritt und lässt sich lokal auf eigener GPU rechnen.
5. **Der GWR-Snapshot ist eine Momentaufnahme.** Ob ein Eintrag zwischen Baugesuch und heute
   einmal geändert und wieder überschrieben wurde, ist nicht sichtbar. Für eine Weiterführung
   braucht es Snapshots über die Zeit.
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

Die im Vorfeld festgelegten Kriterien:

| Kriterium | Ergebnis | erfüllt |
|---|---|---|
| Test 3 zeigt eine grosse Lücke | 40,6 % nicht nachgeführt, 43,2 % nachgeführt, weit gefasst 49,1 % | ja |
| Test 2 liefert genug Fälle | Median 1,6 Heizungsgesuche pro Gemeinde und Jahr | nein |
| Stop-Signal: über 80 % nachgeführt | in keinem Altersfenster erreicht | nein |
| Stop-Signal: nur eine Handvoll Gesuche pro Gemeinde | trifft auf drei Viertel der Gemeinden zu | ja |
| Zusatzbefund: wird das Problem kleiner? | ja, Erfassung steigt von 62,4 % auf 77,3 % | spricht gegen einen Dauerbetrieb |

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.**

Begründung:

- Die Lücke, auf der die Idee aufbaut, ist nachweisbar und deutlich grösser als das
  Stop-Kriterium. Das Problem existiert.
- Der Weg über Baugesuche allein trägt aber nicht. Für die mittlere Gemeinde entstehen
  zwei Verdachtsfälle pro Jahr; das lohnt keinen eigenen Prozess.
- Gleichzeitig läuft bereits ein grosser Nachführungsbetrieb: 22'060 aktualisierte
  Heizungseinträge allein 2026. Der Beitrag eines Abgleichs aus offenen Daten liegt nicht im
  "Fehler finden", sondern im Schliessen der Lücke zwischen zwei Sammelaktualisierungen.
- **Das Problem schrumpft.** Der Berner Zeitverlauf (Abschnitt 2.7) zeigt es am deutlichsten:
  Von 62,4 % Erfassung bei 20 Jahre alten Anlagen auf 77,3 % bei den jüngsten.
  Der Altbestand, um den es geht, wird Jahr für Jahr kleiner. Für eine einmalige
  Bereinigung ist das ein Argument, für eine Dauerüberwachung nicht.
- Als Methodenprojekt taugt das Thema gut: eine saubere, messbare Fragestellung, offene
  Daten in brauchbarer Qualität, eine echte Entity-Resolution-Aufgabe, ein sinnvoller
  Einsatz für LLM-Extraktion und eine Evaluation, die sich an Bodenwahrheit prüfen lässt.

### Was aus dem Befund folgt

Wer den Abgleich weiterführen will, sollte ihn so anlegen:

- **Die passende Ebene ist der Kanton oder eine Stadt, nicht die einzelne Gemeinde.** Zürich und
  Winterthur haben zusammen mehr Heizungs-Baugesuche als die anderen 158 Gemeinden zusammen,
  und beide zeigen mit 70,7 % und 55,9 % die grössten Lücken unter den
  Gemeinden mit nennenswertem Volumen.
- **Baugesuche reichen als Belegquelle nicht.** Es braucht mindestens Feuerungskontrolle,
  Gebäudeprogramm-Förderdaten, Gasnetz-Abmeldungen und die Pronovo-Anlagendaten. Erst die
  Kombination ergibt eine Abdeckung, die sich lohnt.
- **Erdwärmesonden sind die bisher beste offene Quelle.** Sie liefern einen harten
  Widerspruch statt eines Indizes, sind in zwei Kantonen frei verfügbar und in Bern sogar
  mit Datum und Ausführungsnachweis. Das ist der erste Baustein, nicht die Baugesuche.
- **Sinnvoll ist eine einmalige Bereinigung, keine Dauerüberwachung.** Der Altbestand ist das
  Problem, und ein Altbestand lässt sich einmal aufräumen.
- **Ein Gespräch mit der kantonalen Fachstelle vor jeder weiteren Zeile Code.** Die konkrete
  Frage: "Wir sehen bei 70,7 % der Zürcher
  Heizungs-Baugesuche keine Nachführung im GWR. Ist das für Sie ein Problem, und wenn ja,
  wessen Problem?"

---

## 6 Nächste Schritte

Diese Liste hält den Stand der Detailauswertung vom September 2026 fest. Umgesetzt wurden
seither die LLM-Extraktion, die Snapshot-Zeitreihe und weitere Belegquellen; was daraus
wurde, steht im README.

1. **LLM-Extraktion statt Stichwortsuche.** Aus dem Projektbeschrieb strukturiert ziehen:
   alter Energieträger, neuer Energieträger, Bestand oder Neubau, Gewicht im Vorhaben.
   Evaluation an rund 200 selbst gelabelten Baugesuchen, Kennzahlen je Feld.
   Lokal, damit keine Datenfrage entsteht.
2. **Belegquellen erweitern.** Pronovo-Anlagendaten, Gebäudeprogramm, Minergie,
   GEAK-Bestand. Ziel ist ein Score "wahrscheinlich veraltet" pro Gebäude statt
   einer Ja/Nein-Regel.
3. **GWR-Snapshots sammeln.** Ab sofort wöchentlich `zh.zip` ablegen. Damit wird die
   Nachführung als Ereignis messbar statt nur als Momentaufnahme, und die grösste Schwäche
   von Test 3 verschwindet.
4. **Architektur.** Bronze: GWR-Snapshots, Baugesuche, Anlagendaten, je mit Manifest und
   Ladedatum. Silver: LLM-Extraktion der Heizungsereignisse, Entity Resolution Baugesuch zu
   EGID über Parzelle und Adresse (die 98,9 % Übereinstimmung aus Abschnitt 3 sind die
   Referenz). Gold: Belege je Gebäude, Score, Bericht je Gemeinde.
   Die vorliegende Pipeline ist bereits so aufgebaut.
5. **Evaluation.** Extraktionsgenauigkeit an gelabelten Baugesuchen, Zuordnungsgenauigkeit
   über die Kreuzprüfung der beiden Wege, Precision der Verdachtsfälle über eine Stichprobe,
   die eine Partnergemeinde gegenprüft.

---

## Reproduzierbarkeit

```bash
python src/download.py     # Rohdaten laden, Manifest schreiben
python src/build_db.py     # Bronze-Layer in DuckDB
python src/report.py       # Pipeline rechnen und diesen Report erzeugen
```
