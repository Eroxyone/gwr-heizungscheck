# Welche Daten gibt es in welchem Kanton?

Das GWR deckt die ganze Schweiz ab. Alles, womit sich das GWR **prüfen** lässt, gibt es nur stellenweise. Diese Tabelle sagt deshalb weniger über die Kantone aus als über die Grenzen dieser Auswertung.

| Kt | Gebäude | Anlagen | davon datiert | Heizungs-Baugesuche | Quelle | Stufe |
|---|---:|---:|---:|---:|---|---|
| BE | 458'537 | 14'661 | 14'485 | 663 | portal | 3 |
| SO | 112'895 | 8'863 | 8'780 | 20 | portal | 3 |
| ZG | 27'403 | 2'792 | 2'791 | 45 | portal | 3 |
| BL | 116'905 | 2'629 | 2'629 | 36 | portal | 3 |
| SZ | 56'606 | 1'675 | 1'522 | 24 | portal | 3 |
| SG | 209'767 | 29'198 | 29'198 | – | - | 2 |
| LU | 137'044 | 21'783 | 14'664 | – | - | 2 |
| TG | 115'799 | 4'532 | 4'532 | – | - | 2 |
| GE | 80'945 | 3'668 | 3'538 | – | - | 2 |
| AI | 9'702 | 2'419 | 2'419 | – | - | 2 |
| AR | 27'864 | – | – | 73 | portal | 2 |
| BS | 30'440 | – | – | 22 | portal | 2 |
| NW | 15'105 | – | – | 26 | portal | 2 |
| OW | 20'094 | – | – | 64 | portal | 2 |
| TI | 190'741 | – | – | 36 | portal | 2 |
| VS | 204'769 | – | – | 867 | portal | 2 |
| ZH | 367'385 | 39'470 | – | 1'427 | ogd | 1 |
| SH | 34'117 | 1'235 | – | 78 | portal | 1 |
| UR | 22'649 | 847 | – | – | - | 1 |
| AG | 270'306 | – | – | – | - | 0 |
| FR | 156'664 | – | – | – | - | 0 |
| GL | 26'861 | – | – | – | - | 0 |
| GR | 131'611 | – | – | – | - | 0 |
| JU | 51'321 | – | – | – | - | 0 |
| NE | 62'928 | – | – | – | - | 0 |
| VD | 236'099 | – | – | – | - | 0 |

## Die vier Stufen

| Stufe | Was möglich ist | Kantone |
|---|---|---:|
| 3 | Anlagen mit Datum **und** Baugesuche – auch Anlagen ohne Bohrung werden sichtbar | 5 |
| 2 | datierte Belege – "seit wann nicht nachgeführt" ist beantwortbar | 11 |
| 1 | Anlagen ohne Datum – Widersprüche sichtbar, aber nicht datierbar | 3 |
| 0 | nur GWR – man sieht, wie gepflegt das Register *aussieht*, nicht ob es stimmt | 7 |

**Das ist die wichtigste Einschränkung des ganzen Projekts.** Ein Kanton auf Stufe 0 – davon gibt es 7 – kann in keiner Rangliste schlecht abschneiden, weil es nichts gibt, woran er scheitern könnte. Umgekehrt sieht ein Kanton mit guter Datenlage zwangsläufig schlechter aus: Wer hinschauen lässt, bei dem wird etwas gefunden. Jede Kantonsrangliste in diesem Projekt ist zuerst eine Rangliste der Offenheit.

## Befund je Kanton

| Kt | Stufe | Befund |
|---|---|---|
| AG | 0 | Keine Anlagendaten als Vektor, nur Eignungskarten als WMS. Der Kanton uebertraegt Energiemerkmale seit 2026 direkt aus dem Bewilligungssystem ins GWR |
| AI | 2 | Bohrkataster mit Erstelljahr. Wie St. Gallen: 86 % stehen schon im GWR |
| AR | 2 | Nur Zulaessigkeitsbereiche. Das kantonale EnergyGIS fuehrt eine Heizungs-kategorie je Gebaeude, leitet sie aber aus dem GWR ab - als Beleg zirkulaer |
| BE | 3 | AGI-Anlagenregister mit Ausfuehrungsstatus; Baugesuche im Amtsblattportal |
| BL | 3 | Bohrregister mit Bohrjahr - Ausfuehrung, nicht Bewilligung |
| BS | 2 | Nur Energierichtplan-Flaechen |
| FR | 0 | Nichts gefunden |
| GE | 2 | SITG-CSV mit Realisierungsdatum |
| GL | 0 | Nichts gefunden |
| GR | 0 | Nichts gefunden; die Baugesuch-Subrubrik AA-GR10 ist angemeldet, aber leer |
| JU | 0 | Nur Bohrbeschraenkungszonen |
| LU | 2 | Reichster Kantonsdatensatz: Sonden mit Bohrdatum plus als einziger Kanton Luft-Wasser-Waermepumpen. Die Koordinaten sind aber nicht gebaeudegenau (Median 24 m zum naechsten Gebaeude statt 8 bis 9 m) - Luzern ist deshalb aus den auswertenden Sichten ausgeschlossen |
| NE | 0 | Nichts gefunden |
| NW | 2 | Erdsondenkataster vorhanden, aber nur als WMS-Bild |
| OW | 2 | Erdsondenkataster vorhanden, aber nur als WMS-Bild |
| SG | 2 | Anlagenregister statt Sondenkataster - fuehrt die Waermepumpe selbst. 84 % der Gebaeude neben einer Anlage haben sie schon im GWR: Der Kanton fuehrt offenbar bereits nach |
| SH | 1 | Sonden ohne Datum, in WGS84 |
| SO | 3 | AFU-Sonden ab 1986, Abgabe auf 5000 Objekte begrenzt |
| SZ | 3 | Nur ueber map.geo.sz.ch/mapserv_proxy erreichbar, nicht ueber wfs.geo.sz.ch |
| TG | 2 | Sonden mit Bohrdatum und Status |
| TI | 2 | Keine Anlagendaten; Baugesuche im Amtsblattportal |
| UR | 1 | Nur Konzessionen - bewilligt, nicht nachweislich gebaut |
| VD | 0 | Geothermie-Kataster vorhanden, aber kostenpflichtig (10 CHF/km2) |
| VS | 2 | Keine Anlagendaten; Baugesuche im Amtsblattportal |
| ZG | 3 | Einziger Kanton mit EGID an der Anlage |
| ZH | 1 | Vier Layer des AWEL, dazu der OGD-Baugesuchsdatensatz des Statistischen Amts |

Gesucht wurde über den nationalen Metadatenkatalog geocat.ch (deutsch, französisch, italienisch), über opendata.swiss, über den Themenkatalog von geodienste.ch und über einen Endpunkt-Scan aller 26 Kantone. Ein leerer Befund heisst "auf diesen Wegen nicht gefunden", nicht "existiert nicht".
