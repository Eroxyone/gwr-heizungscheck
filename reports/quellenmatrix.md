# Quellenmatrix: Welche Daten gibt es in welchem Kanton?

Stand 14.09.2026. Die Tabelle zeigt je Kanton, welche offenen Daten neben dem GWR vorliegen (Wärmenutzungsanlagen, Heizungs-Baugesuche) und welche Prüfung des Registers damit möglich ist.

Das GWR deckt die ganze Schweiz ab. Alles, womit sich das GWR **prüfen** lässt, gibt es nur stellenweise. Die Tabelle sagt deshalb weniger über die Kantone aus als über die Grenzen dieser Auswertung.

| Kanton | Gebäude | Anlagen | davon datiert | Heizungs-Baugesuche | Quelle der Baugesuche | Stufe |
|---|---:|---:|---:|---:|---|---|
| BE | 458'537 | 14'661 | 14'485 | 663 | Amtsblattportal | 3 |
| SO | 112'895 | 8'863 | 8'780 | 20 | Amtsblattportal | 3 |
| ZG | 27'403 | 2'792 | 2'791 | 45 | Amtsblattportal | 3 |
| BL | 116'905 | 2'629 | 2'629 | 36 | Amtsblattportal | 3 |
| SZ | 56'606 | 1'675 | 1'522 | 24 | Amtsblattportal | 3 |
| SG | 209'767 | 29'198 | 29'198 | – | – | 2 |
| LU | 137'044 | 21'783 | 14'664 | – | – | 2 |
| TG | 115'799 | 4'532 | 4'532 | – | – | 2 |
| GE | 80'945 | 3'668 | 3'538 | – | – | 2 |
| AI | 9'702 | 2'419 | 2'419 | – | – | 2 |
| AR | 27'864 | – | – | 73 | Amtsblattportal | 2 |
| BS | 30'440 | – | – | 22 | Amtsblattportal | 2 |
| NW | 15'105 | – | – | 26 | Amtsblattportal | 2 |
| OW | 20'094 | – | – | 64 | Amtsblattportal | 2 |
| TI | 190'741 | – | – | 36 | Amtsblattportal | 2 |
| VS | 204'769 | – | – | 867 | Amtsblattportal | 2 |
| ZH | 367'385 | 39'470 | – | 1'427 | OGD Kanton Zürich | 1 |
| SH | 34'117 | 1'235 | – | 78 | Amtsblattportal | 1 |
| UR | 22'649 | 847 | – | – | – | 1 |
| AG | 270'306 | – | – | – | – | 0 |
| FR | 156'664 | – | – | – | – | 0 |
| GL | 26'861 | – | – | – | – | 0 |
| GR | 131'611 | – | – | – | – | 0 |
| JU | 51'321 | – | – | – | – | 0 |
| NE | 62'928 | – | – | – | – | 0 |
| VD | 236'099 | – | – | – | – | 0 |

## Die vier Stufen

| Stufe | Was möglich ist | Kantone |
|---|---|---:|
| 3 | Anlagen mit Datum **und** Baugesuche: auch Anlagen ohne Bohrung werden sichtbar | 5 |
| 2 | datierte Belege: "seit wann nicht nachgeführt" ist beantwortbar | 11 |
| 1 | Anlagen ohne Datum: Widersprüche sichtbar, aber nicht datierbar | 3 |
| 0 | nur GWR: sichtbar ist, wie gepflegt das Register aussieht, nicht ob es stimmt | 7 |

**Diese Ungleichheit begrenzt jeden Kantonsvergleich der Studie.** Ein Kanton auf Stufe 0 (davon gibt es 7) kann in keiner Rangliste schlecht abschneiden, weil eine Gegenquelle fehlt. Umgekehrt sieht ein Kanton mit guter Datenlage zwangsläufig schlechter aus, weil nur bei ihm etwas gefunden werden kann. Jede Kantonsrangliste der Studie ist deshalb zuerst eine Rangliste der Datenoffenheit.

## Befund je Kanton

| Kanton | Stufe | Befund |
|---|---|---|
| AG | 0 | Keine Anlagendaten als Vektor, nur Eignungskarten als WMS. Der Kanton überträgt Energiemerkmale seit 2026 direkt aus dem Bewilligungssystem ins GWR |
| AI | 2 | Bohrkataster mit Erstelljahr. Wie in St. Gallen stehen 86 % schon im GWR |
| AR | 2 | Nur Zulässigkeitsbereiche. Das kantonale EnergyGIS führt eine Heizungskategorie je Gebäude, leitet sie aber aus dem GWR ab und ist als Beleg zirkulär |
| BE | 3 | AGI-Anlagenregister mit Ausführungsstatus; Baugesuche im Amtsblattportal |
| BL | 3 | Bohrregister mit Bohrjahr (Ausführung, nicht Bewilligung) |
| BS | 2 | Nur Energierichtplan-Flächen |
| FR | 0 | Nichts gefunden |
| GE | 2 | SITG-CSV mit Realisierungsdatum |
| GL | 0 | Nichts gefunden |
| GR | 0 | Nichts gefunden; die Baugesuch-Subrubrik AA-GR10 ist angemeldet, aber leer |
| JU | 0 | Nur Bohrbeschränkungszonen |
| LU | 2 | Sonden mit Bohrdatum und als einziger Kanton Luft-Wasser-Wärmepumpen. Die Koordinaten sind nicht gebäudegenau (Median 24 m zum nächsten Gebäude statt 8 bis 9 m); Luzern ist deshalb aus den auswertenden Sichten ausgeschlossen |
| NE | 0 | Nichts gefunden |
| NW | 2 | Erdsondenkataster vorhanden, aber nur als WMS-Bild |
| OW | 2 | Erdsondenkataster vorhanden, aber nur als WMS-Bild |
| SG | 2 | Anlagenregister statt Sondenkataster, führt die Wärmepumpe selbst. 84 % der Gebäude neben einer Anlage tragen sie schon im GWR; der Kanton führt offenbar bereits nach |
| SH | 1 | Sonden ohne Datum, in WGS84 |
| SO | 3 | AFU-Sonden ab 1986, Abgabe auf 5'000 Objekte je Anfrage begrenzt |
| SZ | 3 | Nur über map.geo.sz.ch/mapserv_proxy erreichbar, nicht über wfs.geo.sz.ch |
| TG | 2 | Sonden mit Bohrdatum und Status |
| TI | 2 | Keine Anlagendaten; Baugesuche im Amtsblattportal |
| UR | 1 | Nur Konzessionen (bewilligt, nicht nachweislich gebaut) |
| VD | 0 | Geothermie-Kataster vorhanden, aber kostenpflichtig (10 CHF/km2) |
| VS | 2 | Keine Anlagendaten; Baugesuche im Amtsblattportal |
| ZG | 3 | Einziger Kanton mit EGID an der Anlage |
| ZH | 1 | Vier Layer des AWEL, dazu der OGD-Baugesuchsdatensatz des Statistischen Amts |

Die Suche umfasst den nationalen Metadatenkatalog geocat.ch (deutsch, französisch, italienisch), opendata.swiss, den Themenkatalog von geodienste.ch und einen Endpunkt-Scan aller 26 Kantone. Ein leerer Befund heisst "auf diesen Wegen nicht gefunden", nicht "existiert nicht".
