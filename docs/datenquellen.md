# Datenquellen

Jede Quelle mit Adresse, Herausgeber, Umfang und den Eigenheiten beim Einlesen. Stand
der Abrufe ist September 2026; spätere Änderungen sind datiert. Die Lizenzlage steht in [reports/lizenzen.md](../reports/lizenzen.md), die
Verfügbarkeit je Kanton in [reports/quellenmatrix.md](../reports/quellenmatrix.md).

Alle Quellen sind offen zugänglich. Die meisten verlangen eine Quellenangabe, bei drei
ist die Lizenz nur über die allgemeine Regel des Kantonsportals belegt
([reports/lizenzen.md](../reports/lizenzen.md)).
`data/raw/manifest.json` und `data/snapshots/ingest_manifest.jsonl` halten zu jedem Bezug
URL, Grösse, SHA-256 und Zeitpunkt fest.

## Beschaffung

Zwei Skripte holen alles:

- `python src/ingest.py` lädt das GWR aller Kantone und legt je Kanton einen
  Parquet-Snapshot ab. Wiederholt ausgeführt entsteht daraus die Zeitreihe.
- `python src/download.py` lädt die übrigen 30 Quellen nach `data/raw/`, entpackt die
  Archive und blättert durch Dienste, die ihre Abgabe begrenzen. Ein gescheiterter Abruf wird
  dreimal versucht und hält die übrigen Quellen nicht auf; am Ende steht, was fehlt.

## 1. GWR, öffentliche Daten Stufe A, alle Kantone

- **URL-Muster:** `https://public.madd.bfs.admin.ch/{kt}.zip` mit dem Kantonskürzel in
  Kleinbuchstaben, z. B. `zh.zip`. Alle 26 Kantone verfügbar, zusammen rund 910 MB.
- **Herausgeber:** Bundesamt für Statistik, Sektion Gebäude und Wohnungen
- **Einstiegsseite:** https://www.housing-stat.ch/de/madd/public.html
- **Aktualisierung:** täglich, das Feld `GEXPDAT` trägt das Exportdatum
- **Verwendet:** `gebaeude_batiment_edificio.csv` (tabgetrennt) und
  `eingang_entree_entrata.csv` (Adressen), immer `kodes_codes_codici.csv` (Codelisten)
- Der Ingest schreibt **zwei** Snapshot-Reihen: `data/snapshots/gwr/` mit den Gebäuden und
  `data/snapshots/gwr_adresse/` mit 3'461'446 Adressen. Die Adressen sind kein Beiwerk:
  Ausserhalb Zürichs liefern die Amtsblatt-Baugesuche weder Koordinate noch
  Parzellengeometrie, sondern nur Strasse, Hausnummer und PLZ. Ohne die Eingangstabelle
  endet die schweizweite Zuordnung dort.
- **Wichtig:** Die Codelisten für `GENH1`, `GWAERZH1` und `GWAERSCEH1` stammen aus der
  mitgelieferten Katalogdatei, nie aus Sekundärquellen.
- Die ebenfalls enthaltenen `buildings.geojson` (317 MB) und `data.sqlite` werden nicht
  gebraucht: Die Koordinaten `GKODE`/`GKODN` stehen bereits in der CSV.

## 2. Baugesuche im Kanton Zürich

- **Datensatzseite:** https://opendata.swiss/de/dataset/baugesuche-im-kanton-zurich
- **Volltabelle (CSV):** https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006183.csv
- **Georeferenziert ab 2025 (GPKG):** https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006403.gpkg
- **Herausgeber:** Statistisches Amt des Kantons Zürich, Fachstelle OGD
- **Aktualisierung:** täglich
- **Abdeckung:** Die Sammlung läuft seit Herbst 2024; 2022 und 2023 enthalten nur Einzelfälle.
  `bfs_nr` und `municipality_name` sind erst ab 2025 gefüllt, Parzellengeometrien ebenfalls.
- **Personendaten** sind bereits entfernt. Enthalten sind Projektbeschrieb, Standort,
  BFS- und Katasternummer.
- Metadaten über die CKAN-API; `opendata.swiss` leitet auf `ckan.opendata.swiss` um und
  blockt Anfragen ohne User-Agent:
  `curl -L -H "User-Agent: ..." "https://ckan.opendata.swiss/api/3/action/package_show?id=baugesuche-im-kanton-zurich"`

## Baugesuche schweizweit über das Amtsblattportal

`src/ingest_baugesuche.py` holt Baugesuche aus dem
[Amtsblattportal](https://www.amtsblattportal.ch/docs/api/), einer offenen API ohne
Anmeldung. Welche Mandanten überhaupt eine Baugesuch-Subrubrik führen, wurde nicht
geraten, sondern aus `/api/v1/rubrics` gelesen und über `/api/v1/tenants` mit dem Kanton
verknüpft: **13 Kantone**. Graubünden (`AA-GR10`) ist im Katalog als aktiv geführt,
enthält aber keine einzige Publikation.

**Entscheidend ist, wo der Projektbeschrieb steht.** Die Mandanten zerfallen in zwei
Gruppen:

| Modus | Mandanten | Titel | Folge |
|---|---|---|---|
| `titel` | BL, SO, NW, OW, SH, VS, AM-DA50 | "Baugesuch – Ersatz Ölheizung durch Luft/Wasser-Wärmepumpe, Stans" | Die Listenabfrage reicht als Filter, nur Treffer brauchen einen Detailabruf |
| `voll` | ZH, BE, BS, TI, ZG, AR, SZ | "Kommunale Baugesuchspublikation: Sprungstrasse 13a, Unterägeri" | Ein Titelfilter findet fast nichts - in Zürich griff er bei **1 von 6'743** Publikationen. Hier muss jedes Detail geholt werden |

Ein Abzug, der nur die Titel filtert, meldet für ZH, BE, BS, TI, ZG, AR und SZ also null
Heizungsbaugesuche, obwohl sie vorhanden sind.

**Drei weitere Fallen im Detail-XML:**

1. *Die Adresse der Bauverwaltung statt die des Vorhabens.* Der Block
   `registrationOffice` trägt das Gemeindehaus, `buildingContractor` und `projectFramer`
   tragen Bauherrschaft und Planer. In einer Zuger Publikation stand so die Adresse eines
   Haustechnikbetriebs aus Wolhusen LU als Standort. Die Objektadresse steht in
   `projectLocation` (ZH, BE, BS, TI, ZG, AR) oder im Element `projectAddress`
   (SO, NW, OW, SH, AM-DA50). Alles andere wird vor der Suche entfernt.
2. *Die Beschriftung statt den Wert.* Ein `<element>` enthält
   `<term><de>Projektbeschreibung</de></term>` **und** `<valueRichText><de>…</de></valueRichText>`.
   Wer das erste `<de>` nimmt, erhält bei jeder Schwyzer Publikation den Text
   "Projektbeschreibung". Der Richtext ist zudem doppelt HTML-kodiert.
3. *Wallis vergibt dem Titel-Element gar keinen `<key>`* - es steht nur als erstes Element
   unter `<primary>`.

**Personendaten.** Schwyz und Tessin publizieren den Beschrieb als Fliesstext und nennen
darin Planverfasser und Grundeigentümer mit Namen und Wohnadresse. Diese Felder werden
bereits beim Einlesen durch `[entfernt]` ersetzt, nicht erst bei der Auswertung: Was nie
gespeichert wird, kann auch nicht versehentlich in einen Bericht geraten. Das Tessiner
Formular wird ausserdem auf seine Sachfelder reduziert (`Genere dell'opera`,
`Destinazione`, `N. di mappa`).

Für den Titel gilt das nicht: Schaffhausen und Wallis stellen die Bauherrschaft vor den
Objektbeschrieb in den Titel. Der Titel wird roh abgelegt und erst im Silver-Layer
bereinigt (`titel_anonym` in `sql/silver_baugesuche_ch.sql`); eine Prüfung in `checks.py`
stellt sicher, dass kein Belegtext der Liste das Namensmuster trägt. Der rohe Abzug
bleibt lokal und gehört nicht ins Git.

**Zürich ist standardmässig ausgeschaltet.** Der Kanton publiziert dieselben Baugesuche
als offenen Datensatz des Statistischen Amts - mit Parzellenpolygonen, täglich
aktualisiert, in einer Tabelle. Der Portalabzug wäre die schlechtere Kopie und kostet
6'743 Detailabrufe, also fast die Hälfte der Laufzeit. Mit `--kantone ZH` lässt er sich
trotzdem holen, etwa um beide Quellen gegeneinander zu prüfen.

Der Lauf schreibt jede Antwort sofort in eine Zwischendatei und nimmt einen
abgebrochenen Lauf dort wieder auf, wo er stand. Bei fünfstelligen Abrufzahlen über
Stunden ist das nötig.

## 3. Wärmenutzungsanlagen weiterer Kantone

13 Kantone publizieren ihre Anlagen offen, zusammen **133'772 Objekte**. Jeder in einem
eigenen Format, mit eigenen Feldnamen und eigenen Eigenheiten:

| Kanton | Quelle | Anlagen | Datum | Eigenheit |
|---|---|---|---|---|
| ZH | WFS `maps.zh.ch`, vier Layer | 39'470 | nein | siehe Abschnitt 5 |
| SG | WFS `geoportal.ch`, Layer `q352_thermischezentralen` | 29'198 | ja, ab 1900 | **kein Sonden-, sondern ein Anlagenregister**: führt die Wärmepumpe selbst, mit Anlageart und baulichem Zustand. Braucht zwingend WFS 2.0.0 mit `TYPENAMES`, Version 1.1.0 antwortet mit HTTP 500 |
| LU | WFS `public.geo.lu.ch`, zwei Datensätze | 14'717 + 7'066 | Bohrung: ja | einziger Kanton mit **Luft-Wasser-Wärmepumpen** (7'066). Die sind laut Kanton "erstellt oder in Planung" und zählen deshalb nur wie eine Bewilligung |
| BE | WFS AGI | 14'661 | ja, ab 1980 | Status "Ausgeführt" |
| SO | WFS `geo.so.ch/api/wfs`, Layer `ch.so.afu.erdwaerme.sonde` | 8'863 | ja, ab 1986 | **Abgabe auf 5'000 Objekte begrenzt**, muss über `startIndex` geblättert werden; liefert WGS84 |
| TG | WFS `ows.geo.tg.ch`, Layer `ms:erdwaerme_erdwaermesondenbohrungen` | 4'532 | ja | Status "ausgebaut, in Nutzung" |
| GE | CSV über `ge.ch/sitg`, `GOL_SONDES_GEOTH` | 3'668 | ja | LV95 in eigenen Spalten, Datum als Zahl JJJJMMTT |
| ZG | GeoPackage aus `services.geo.zg.ch/datarepo` | 2'792 | ja, Bohrdatum | **liefert als einziger Kanton die EGID mit** (805 Anlagen). Damit lässt sich die eigene Zuordnung prüfen, siehe `reports/zuordnung_zg.md`. Ein Datensatz trägt 2105 als Bohrdatum |
| BL | WFS `geowms.bl.ch`, Layer `ms:grundwasser_erdsonden` | 2'629 | ja, Bohrjahr | **Bohr-, nicht Anlagenregister**: das Jahr meint die Ausführung. Nur WFS 1.1.0 mit GML, JSON quittiert das Amt mit HTTP 500 |
| AI | WFS `geoportal.ch`, Layer `f211_ai_erdwaermesonden` | 2'419 | ja, Erstelljahr | führt eine Eigentümerspalte, die in der Pipeline bewusst nicht übernommen wird |
| SZ | **`map.geo.sz.ch/mapserv_proxy`**, Layer `ch.sz.a034c.waermenutzung...` | 1'675 | ja, ab 1986 | siehe unten |
| SH | WFS `wfs.geo.sh.ch` | 1'235 | nein | braucht WFS **1.1.0**, Version 2.0.0 scheitert; liefert WGS84 |
| UR | WFS `geo.ur.ch`, Layer `energie:ur033_konzessionen_erdsonden` und `ur031_...grundwasserwaermepumpen` | 847 | nein | nur "Konzession erteilt", aus Test 6 ausgeschlossen |

**Stand 22.11.2026: St. Gallen und Appenzell Innerrhoden sind nicht mehr offen
beziehbar.** Der WFS von `geoportal.ch`, über den beide Kantone ihre Anlagen ausliefern,
beantwortete am 22.11.2026 jede Anfrage mit HTTP 401 und verlangte eine Anmeldung, auch
`GetCapabilities`. Im September 2026 lieferte derselbe Aufruf die Daten ohne Zugang. Die
Zahlen in den Berichten stammen aus dem damaligen Abzug. Wer die Pipeline heute neu rechnet,
bekommt elf statt 13 Kantone: `download.py` meldet die beiden Quellen als nicht geladen, und
`sql/test5.sql` lässt Kantone ohne Rohdatei aus, statt abzubrechen. Offene Register sind
nicht für immer offen; genau deshalb hält das Manifest zu jedem Bezug Zeitpunkt und
Prüfsumme fest.

**Schwyz: die richtige Adresse.** Der WFS unter `wfs.geo.sz.ch` liefert einen
vollständigen Capabilities-Katalog mit 1'018 Layern, beantwortet aber jedes `GetFeature`
erneut mit den Capabilities. Die Daten kommen unter `map.geo.sz.ch/mapserv_proxy` heraus,
dem Dienst, auf den die Capabilities selbst verweisen.

**Nicht jede Koordinate meint dasselbe - der Fall Luzern.**

Luzern liefert den attributreichsten Anlagendatensatz der Schweiz: Bewilligungsdatum,
Realisierungsdatum der Bohrung, Betriebszustand, Nutzungszweck, dazu als einziger Kanton
7'066 Luft-Wasser-Wärmepumpen. Trotzdem ist er für die Gebäudezuordnung unbrauchbar.

Gemessen wurde die Entfernung jeder Anlage zum nächstgelegenen Gebäude, Stichprobe 3'000
je Kanton:

| Kanton | Median | unter 20 m |
|---|---:|---:|
| ZH | 8,0 m | 95,3 % |
| BE | 8,8 m | 95,0 % |
| SG | 9,3 m | 93,3 % |
| **LU** | **24,2 m** | **42,5 %** |

Es ist kein Versatz, den man herausrechnen könnte: Der mittlere Verschiebungsvektor zum
nächsten Gebäude ist mit -2,7/-4,7 m klein, die Streuung mit 40,2 m mittlerer Distanz
gross. Die Koordinate meint offenbar die Parzelle, nicht das Gebäude.

Der entscheidende Beleg steht im Ergebnis selbst: **In Luzern tragen 18,2 % der Gebäude im
Umkreis von 0 bis 5 m eine Wärmepumpe - bei einer kantonalen Hintergrundrate von 21,8 %.**
Selbst die nächstgelegenen Gebäude sind also *seltener* Wärmepumpen als ein zufällig
gezogenes Luzerner Wohngebäude. St. Gallen kommt an derselben Stelle auf 84,4 % bei einer
Hintergrundrate von 30,4 %.

Luzern bleibt deshalb im Silver-Layer - die Daten sind gesammelt, die Attribute sind gut -
wird aber über `v_lage_ungenau` aus den auswertenden Sichten herausgehalten. Ohne diese
Korrektur hätte Luzern 3'029 Widerspruchsfälle beigesteuert, die grösstenteils Nachbarn
gewesen wären. `checks.py` misst das Muster nach, damit nicht unbemerkt ein weiterer
Kanton in dieselbe Lage gerät.

**St. Gallen und Appenzell Innerrhoden führen ihre Anlagen bereits nach.** Bei 84 bzw.
86 % der nächstgelegenen Gebäude steht die Wärmepumpe schon im GWR. Wo ein Kanton die
Bewilligungsdaten ins Register überträgt, findet ein Abgleich aus offenen Daten wenig.
Zürich liegt an derselben Stelle bei 39,9 % bei einer Hintergrundrate von 15,9 %.

**Geprüft und verworfen:**

| Kanton | Befund |
|---|---|
| AG | veröffentlicht nur Eignungskarten als WMS; der WFS-Endpunkt liefert keine Layer. Aargau überträgt Energiemerkmale seit 2026 ohnehin direkt aus dem Bewilligungssystem ins GWR |
| VD | "Cadastre de géothermie basse température" existiert, ist aber **kostenpflichtig** (10 CHF/km²) und enthält vor allem thermische Karten, keine Anlagen |
| JU | nur Bohrbeschränkungszonen und Tiefengeothermie-Perimeter |
| AR | nur Zulässigkeitsbereiche und geologische Angaben. Das kantonale EnergyGIS führt zwar eine Heizungskategorie je Gebäude, leitet sie aber aus dem GWR ab - als Beleg gegen das GWR also zirkulär |
| BS | nur Energierichtplan-Flächen und Solarpotenzial |
| NW, OW | Erdsondenkataster vorhanden, aber ausschliesslich als WMS (Bild) über `gis-daten.ch`; ein WFS existiert nicht, die Vektordaten laufen über einen Bestellshop |
| GR, GL, FR, NE, TI, VS | über geocat.ch, opendata.swiss, geodienste.ch und die Portal-Endpunkte kein Anlagendatensatz auffindbar |

Die Suche umfasst vier Wege: den nationalen Metadatenkatalog
[geocat.ch](https://www.geocat.ch) (Elasticsearch-API, deutsch/französisch/italienisch),
opendata.swiss, den Themenkatalog von
[geodienste.ch](https://geodienste.ch/info/services.json) und einen Endpunkt-Scan
aller 26 Kantone nach den Mustern `map.geo.<kt>.ch/mapserv_proxy`, `wfs.geo.<kt>.ch`,
`geo.<kt>.ch/wfs` und ArcGIS-REST. Das harmonisierte Thema "Versorgungsgebiete thermische
Netze" auf geodienste.ch wäre der naheliegende Weg zu einem schweizweiten Fernwärme-Layer,
ist aber als "Im Aufbau" gekennzeichnet und liefert noch keine Daten.

**Genf ist ein Sonderfall.** Nur 9,2 % der Genfer Anlagen haben ein Gebäude mit
Wärmepumpen-Eintrag im Umkreis; die übrigen zwölf Kantone liegen zwischen 25,5 % (UR) und
94,7 % (SG), Stand 14.09.2026 ([reports/report.md](../reports/report.md), Abschnitt 2.6).
Der Grund liegt in der Erfassung: Bei fast der Hälfte der Gebäude im Sondenumkreis steht
"Unbestimmt" als Energieträger. Genf erfasst, ohne den Träger zu benennen. Ein Check
überwacht diese Erklärung.

## 3b. Gegenbelege: läuft die fossile Heizung noch?

Alle bisherigen Quellen zeigen in dieselbe Richtung: Hier wurde eine Wärmepumpe gebaut,
hier eine Sonde gebohrt, hier ein Baugesuch publiziert. Keine davon kann sagen, ob die
alte Ölheizung daneben **noch läuft**. Das ist aber die eigentliche Frage: Ein
Verdachtsfall ist nur dann ein Fehler im Register, wenn der fossile Eintrag nicht mehr
stimmt.

Zwei Kantone liefern diese Gegenrichtung:

| Quelle | Umfang | Was sie kann |
|---|---:|---|
| **Genf, Feuerungskataster** `SCANE_CHAUDIERE` | 55'372 Kessel | mit **EGID**, Brennstoff, Betriebszustand (Active / En réserve / Inactive) und Baujahr. ArcGIS-Dienst, gibt höchstens 4'000 Objekte je Anfrage heraus |
| **Zug, Tankkataster** `services.geo.zg.ch/ows/tankanlagen` | 8'319 Heizöltanks | vier Layer, **getrennt nach "in Betrieb" und "ausser Betrieb"**. Die entscheidende Unterscheidung steckt schon in der Layerwahl. Ohne EGID, dafür mit Koordinate im Gebäude |

Der Betriebszustand ist feiner als "an oder aus", und das ist wichtig: Ein Kessel **"En
réserve"** neben einer Wärmepumpe ist kein Widerspruch, sondern der Normalfall einer
Hybridanlage. Er zählt hier weder als Beleg noch als Gegenbeleg.

**Die Messung an diesen Quellen steht in
[reports/belegwirkung.md](../reports/belegwirkung.md).** Gemessen am Zuger Tankkataster
treffen 80,8 % der Fälle zu, bei denen der Beleg jünger ist als der Registereintrag (63 von
78), gegenüber 13,3 % bei älterem Beleg und einer Grundrate von 8,8 %. Die Vorstufe
[reports/precision.md](../reports/precision.md) misst nur, ob noch ein aktiver fossiler
Kessel oder Tank geführt wird, und ist nicht massgebend.

Gegenbelege wirken **filternd, nicht punktend**: Wo ein fossiler Kessel als in Betrieb
geführt wird, verschwindet der Fall aus `v_gold_verdacht`. In Genf sind das am 14.09.2026
2'365 Fälle, 1'259 bleiben ([reports/precision.md](../reports/precision.md)). Der Fall
bleibt in `gold_belege` stehen, sonst liesse sich die Wirkung nicht messen.

**Nicht gefunden, und zwar geprüft:** Fernwärme-Hausanschlüsse (der BFE-Layer
`ch.bfe.thermische-netze` enthält 1'664 Punkte - die Heizzentralen, nicht die Anschlüsse;
das harmonisierte Thema auf geodienste.ch ist "Im Aufbau"), Bauvollendungs- oder
Abnahmemeldungen (im gesamten Rubrikenkatalog des Amtsblattportals gibt es keine solche
Subrubrik), Minergie-Gebäude (das STAC-Asset liefert 404) und der Zürcher Tankkataster
(hinter einer Anmeldung, HTTP 401).

## 4. Wärmenutzungsanlagen Kanton Bern

- **URL:** https://geofiles.be.ch/geoportal/pub/download/ERDSOND/erdsond.gpkg.zip
- **Herausgeber:** Amt für Geoinformation des Kantons Bern
- **Layer:** `geodb.erdsond_erdsondb_vw`, 14'661 Bohrungen
- **Der entscheidende Vorteil:** Bern führt ein **Bewilligungsdatum** (ab 1980) und einen
  **Status**, der "Ausgeführt" von "nur bewilligt" unterscheidet. 11'391 Anlagen sind
  nachweislich gebaut. Damit lässt sich die Nachführung datieren, was mit den Zürcher
  Daten nicht geht.

## 5. Wärmenutzungsanlagen Kanton Zürich

- **WFS:** `https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS` (GetCapabilities für die Layerliste)
- **Herausgeber:** AWEL, Amt für Abfall, Wasser, Energie und Luft, Kanton Zürich
- **Verwendete Layer:** `ms:erdwaermesonden` (38'553), `ms:grundwasserfassung-waermenutzung`
  (868), `ms:quellfassung-waermenutzung` (46), `ms:erdregister` (3)
- Abruf als GeoJSON über `outputFormat=geojson`, gelesen mit `st_read` der
  DuckDB-Spatial-Extension.
- **Einschränkung:** kein Bohrdatum. 87 % der GBS-Nummern beginnen mit "00", das Feld
  kodiert kein Jahr. Als Ersatz dient die Laufnummer der Sonde, kalibriert an Neubauten
  ([methode.md](methode.md)); eine amtliche Datierung ist das nicht.

## 6. Elektrizitätsproduktionsanlagen (Photovoltaik)

- **Datensatzseite:** https://opendata.swiss/de/dataset/elektrizitatsproduktionsanlagen
- **Verwendet (vollständig):** https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip
- **Referenzdatei mit EGID (gekürzt):** https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip
- **Herausgeber:** Bundesamt für Energie, Daten aus dem Herkunftsnachweissystem (Pronovo)

**Achtung, Falle:** Der auf opendata.swiss verlinkte Pfad `/csv/2056/` liefert eine auf exakt
100'000 Zeilen gekürzte Datei, die für den Kanton Zürich nur bis Oktober 2022 reicht. Sie
enthält dafür eine `EGID`-Spalte. Das STAC-Asset unter `/elektrizitaetsproduktionsanlagen/`
enthält alle 333'313 Anlagen und ist aktuell, hat aber keine `EGID`; die Zuordnung läuft dort
über die Koordinaten `_x`/`_y` (LV95). Beide werden geladen: die vollständige für die
Auswertung, die gekürzte zur Prüfung der räumlichen Zuordnung.

**Der Test läuft schweizweit** (`sql/test4_ch.sql`): 328'930 Photovoltaikanlagen, zwei getrennt geführte Zuordnungswege (EGID-Spalte und
20-m-Umkreis über die Koordinaten). Wo beide greifen - 90'558 Anlagen - nennen sie in
**99,4 %** der Fälle dasselbe Gebäude.

Bei den Erdwärmesonden liegt die vergleichbare Trefferquote gegen die amtliche EGID des
Kantons Zug bei 65 % ([reports/zuordnung_zg.md](../reports/zuordnung_zg.md)). Der Grund:
**Eine Solaranlage liegt auf dem Gebäude, eine Erdsonde daneben.** Derselbe 20-m-Umkreis
ist beim einen Beleg beinahe exakt und beim anderen eine Nachbarschaftssuche.

Deshalb wird bei der Photovoltaik genau **ein** Gebäude je Anlage gezählt. Ohne diese
Regel steigt der Befund von 22'425 auf 40'586 Gebäude - die Differenz sind Nachbarn.

Aktuelle Asset-URLs jederzeit prüfbar über die STAC-API:
`https://data.geo.admin.ch/api/stac/v1/collections/ch.bfe.elektrizitaetsproduktionsanlagen/items`
