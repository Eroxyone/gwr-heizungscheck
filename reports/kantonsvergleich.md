# Heizungsangaben im GWR: Wie gut pflegen die Kantone ihr Register?

**Alle 26 Kantone, 2'110 Gemeinden, 1'808'581 Wohngebäude. Datenstand 2026-09-14.**
Erzeugt von `src/report_ch.py` aus den Parquet-Snapshots. Keine Zahl ist von Hand eingetragen.

Interaktive Fassung: [dashboard.html](dashboard.html).
Die Detailauswertung für den Kanton Zürich mit Baugesuchen steht in [report.md](report.md).

---

## Kurzfassung

Im Gebäude- und Wohnungsregister trägt jedes Gebäude einen Eintrag zu Energieträger und
Wärmeerzeuger, dazu eine Informationsquelle und ein Aktualisierungsdatum. Wie gut dieser
Eintrag gepflegt wird, unterscheidet sich zwischen den Kantonen drastisch.

- **28,6 % aller Schweizer Wohngebäude** (517'478 Stück) tragen bei der Heizung
  immer noch die Volkszählung 2000 als Quelle. Der Eintrag wurde seit einem Vierteljahrhundert
  nicht bestätigt.
- Das **Median-Alter** der Heizungsangabe liegt schweizweit bei **7,0 Jahren**.
- **49,4 %** der Wohngebäude sind fossil beheizt (893'136 mit Öl oder Gas),
  **13,2 %** haben eine Wärmepumpe.
- **333'680 Gebäude** (18,4 %) sind Verdachtsfälle: fossil beheizt und der
  Eintrag entweder ungeprüft oder älter als 15 Jahre.
- Die Spannweite zwischen den Kantonen reicht von **BS mit 100,0 Punkten** bis
  **AG mit 50,1**. In **12 Kantonen** überwiegt der
  unbearbeitete Altbestand.

Ein Befund vorweg, der die ganze Auswertung relativiert: **Der Index misst Pflege, nicht
Richtigkeit.** Wie weit beides auseinanderliegt, zeigt Abschnitt 5.

---

## 1 Der Pflege-Index

Drei Anteile über alle Wohngebäude, gemittelt:

| Bestandteil | Was gemessen wird |
|---|---|
| Vollständigkeit | Anteil mit konkretem Energieträger (nicht leer, nicht "unbestimmt", nicht "andere") |
| Aktualität | Anteil mit Aktualisierungsdatum jünger als 15 Jahre |
| Herkunft | Anteil, der **nicht** aus der Volkszählung 2000 stammt |

Quelle 860 (Volkszählung 2000) heisst nicht falsch, sondern ungeprüft. Ob der Eintrag
stimmt, weiss niemand, weil ihn seit 2000 niemand bestätigt hat.

Notenklassen: A ab 90, B ab 75, C ab 60, D ab 45, E darunter.

---

## 2 Kantone

| KT   | Note   |   Index | Pflegemuster   |   Wohngebäude |   % vollständig |   % aktuell |   % VZ 2000 |   Alter (J.) |   % fossil |   % WP |   % Verdacht |
|:-----|:-------|--------:|:---------------|--------------:|----------------:|------------:|------------:|-------------:|-----------:|-------:|-------------:|
| BS   | A      |   100,0 | Sammelimport   |         23919 |           100,0 |       100,0 |         0,0 |            0 |       43,8 |    9,9 |          0,0 |
| SG   | A      |    99,6 | laufend        |        116251 |            99,6 |        99,9 |         0,6 |            2 |       49,4 |   30,4 |          0,4 |
| BL   | A      |    96,0 | Sammelimport   |         68633 |            98,9 |        93,9 |         4,7 |            4 |       61,9 |   19,8 |          0,9 |
| AI   | A      |    91,5 | Sammelimport   |          5379 |            96,5 |        88,0 |         9,9 |            1 |       32,2 |   30,6 |          4,0 |
| GE   | A      |    90,6 | laufend        |         45254 |            87,7 |        89,8 |         5,6 |            2 |       70,3 |    5,2 |          4,1 |
| NE   | B      |    86,7 | Sammelimport   |         31746 |            96,0 |        78,9 |        14,6 |            1 |       65,3 |   11,9 |         10,6 |
| FR   | B      |    81,1 | laufend        |         76063 |            72,9 |        80,6 |        10,2 |            8 |       32,6 |   17,4 |          3,0 |
| ZG   | B      |    78,9 | laufend        |         16257 |            84,6 |        71,9 |        19,7 |            6 |       54,0 |   12,0 |         12,4 |
| LU   | B      |    78,0 | Sammelimport   |         70855 |            85,0 |        70,2 |        21,2 |            2 |       38,7 |   21,8 |          8,9 |
| BE   | B      |    77,2 | laufend        |        238969 |            89,3 |        67,7 |        25,3 |            6 |       50,4 |   11,9 |         12,1 |
| TI   | B      |    76,5 | laufend        |        114920 |            80,9 |        65,3 |        16,6 |            9 |       40,3 |    9,2 |          9,4 |
| SO   | B      |    76,2 | laufend        |         71254 |            80,3 |        69,9 |        21,7 |            7 |       57,8 |    8,9 |         11,1 |
| VD   | B      |    75,8 | laufend        |        139519 |            87,9 |        64,6 |        25,1 |            9 |       60,2 |    6,5 |         17,3 |
| ZH   | C      |    70,8 | laufend        |        228968 |            86,3 |        59,1 |        33,0 |            8 |       55,5 |   15,9 |         27,0 |
| TG   | C      |    63,3 | Rueckstand     |         68161 |            86,0 |        45,4 |        41,5 |           17 |       51,9 |   17,0 |         37,6 |
| OW   | C      |    62,8 | Rueckstand     |          9569 |            81,3 |        48,3 |        41,3 |           16 |       25,3 |   10,6 |         17,7 |
| VS   | C      |    62,5 | Rueckstand     |        122302 |            85,9 |        42,5 |        41,0 |           17 |       36,4 |    9,0 |         21,1 |
| SZ   | C      |    62,0 | Rueckstand     |         32601 |            83,4 |        45,0 |        42,5 |           17 |       44,6 |    9,8 |         27,7 |
| JU   | C      |    60,8 | Rueckstand     |         25432 |            89,6 |        41,9 |        49,0 |           25 |       51,3 |   16,1 |         35,4 |
| SH   | C      |    60,0 | Rueckstand     |         19756 |            85,8 |        40,9 |        46,6 |           20 |       54,3 |   11,5 |         40,4 |
| UR   | D      |    59,0 | Rueckstand     |         10530 |            83,3 |        41,8 |        48,2 |           24 |       30,3 |    9,3 |         15,4 |
| GL   | D      |    57,7 | Rueckstand     |         14079 |            88,8 |        38,2 |        53,8 |           25 |       45,7 |    6,0 |         24,6 |
| GR   | D      |    56,4 | Rueckstand     |         76543 |            85,9 |        35,3 |        52,0 |           25 |       35,5 |    7,9 |         29,7 |
| NW   | D      |    56,2 | Rueckstand     |          8129 |            78,3 |        39,1 |        48,7 |           24 |       35,3 |   10,0 |         31,1 |
| AR   | D      |    53,7 | Rueckstand     |         16443 |            87,0 |        33,8 |        59,7 |           25 |       48,1 |    8,0 |         36,9 |
| AG   | D      |    50,1 | Rueckstand     |        157049 |            77,4 |        30,5 |        57,4 |           25 |       51,1 |    8,9 |         42,8 |

### Pflegemuster

Der Index allein genügt nicht. Ein Kanton, der einmal alles auf einen Schlag importiert,
sieht darin aus wie einer, der laufend arbeitet. Deshalb wird zusätzlich gemessen, wie sich
die Aktualisierungsdaten verteilen:

- **laufend** - die Daten streuen über viele Tage, es wird kontinuierlich gearbeitet
- **Sammelimport** - mindestens 40 % aller Einträge tragen denselben Tag
- **Rückstand** - weniger als die Hälfte der Gebäude hat überhaupt eine Angabe aus den letzten 15 Jahren
- **sporadisch** - weder das eine noch das andere

| Pflegemuster   |   Kantone | welche                              |
|:---------------|----------:|:------------------------------------|
| Rueckstand     |        12 | TG OW VS SZ JU SH UR GL GR NW AR AG |
| laufend        |         9 | SG GE FR ZG BE TI SO VD ZH          |
| Sammelimport   |         5 | BS BL AI NE LU                      |

Die Kantone mit Sammelimport im Detail:

| KT   |   % am selben Tag |   verschiedene Daten |   aktive Tage 24 Mt. |
|:-----|------------------:|---------------------:|---------------------:|
| BS   |              99,1 |                   63 |                   63 |
| BL   |              94,3 |                  221 |                  130 |
| AI   |              89,2 |                  303 |                   43 |
| NE   |              58,4 |                 2563 |                  389 |
| LU   |              52,4 |                 4491 |                  592 |

Basel-Stadt ist der Extremfall: 99,1 % aller Wohngebäude tragen dasselbe Aktualisierungsdatum,
Quelle ist zu 99,7 % die Feuerungskontrolle. Der Index von 100 Punkten steht für einen
einzigen Schreibvorgang, nicht für einen laufenden Prozess.

### Informationsquellen schweizweit

| Code   | Informationsquelle                              |   Gebäude |    % |
|:-------|:------------------------------------------------|----------:|-----:|
| 860    | Gemäss Volkszählung 2000                        |    517478 | 28,6 |
| 869    | Gemäss Baubewilligung                           |    371692 | 20,6 |
| 864    | Gemäss kantonalen Daten / Das Gebäudeprogramm   |    297596 | 16,5 |
| 855    | Gemäss Feuerungskontrolle                       |    287634 | 15,9 |
| 865    | Gemäss Daten der Gemeinde                       |     99371 |  5,5 |
| 859    | Andere                                          |     80163 |  4,4 |
| 870    | Gemäss Versorgungswerk (Gas, Fernwärme)         |     76698 |  4,2 |
| 858    | Gemäss Gebäudeenergieausweis der Kantone (GEAK) |     25506 |  1,4 |
| 857    | Gemäss Eigentümer/in / Verwaltung               |     24146 |  1,3 |
| (leer) | ohne Angabe                                     |     13391 |  0,7 |
| 871    | Gemäss Minergie                                 |      7902 |  0,4 |
| 852    | Gemäss amtlicher Schätzung                      |      6140 |  0,3 |
| 853    | Gemäss Gebäudeversicherung                      |       864 |  0,0 |

---

## 3 Gemeinden

| Note   |   Gemeinden |   % der Gemeinden |   Wohngebäude |
|:-------|------------:|------------------:|--------------:|
| A      |         207 |               9,8 |        334383 |
| B      |         607 |              28,8 |        552218 |
| C      |         730 |              34,6 |        457435 |
| D      |         453 |              21,5 |        401252 |
| E      |         113 |               5,4 |         63293 |

**566 Gemeinden (26,8 %) stehen bei Note D oder E**, 771
Gemeinden sind im Rückstand.

| Pflegemuster   |   Gemeinden |   Wohngebäude |   Verdachtsfälle |
|:---------------|------------:|--------------:|-----------------:|
| Rueckstand     |         771 |        623502 |           219868 |
| sporadisch     |         649 |        241033 |            24651 |
| laufend        |         376 |        566048 |            63302 |
| Sammelimport   |         314 |        377998 |            25859 |

### Grösster Rückstand (ab 500 Wohngebäuden)

| KT   | Gemeinde           |   Wohngebäude |   Index |   % VZ 2000 |   Alter (J.) |   Verdachtsfälle |
|:-----|:-------------------|--------------:|--------:|------------:|-------------:|-----------------:|
| AG   | Remetschwil        |           608 |    38,0 |        70,1 |           25 |              279 |
| AG   | Bözberg            |           580 |    39,4 |        72,2 |           25 |              218 |
| ZH   | Freienstein-Teufen |           586 |    39,7 |        63,8 |           25 |              185 |
| AG   | Berikon            |           946 |    40,8 |        74,4 |           25 |              599 |
| AG   | Jonen              |           609 |    40,8 |        57,1 |           25 |              199 |
| ZH   | Grüningen          |           829 |    40,9 |        67,9 |           25 |              328 |
| ZH   | Neerach            |           792 |    41,0 |        64,0 |           25 |              351 |
| AG   | Zeiningen          |           749 |    41,1 |        54,1 |           25 |              255 |
| AG   | Böttstein          |           740 |    41,3 |        78,4 |           25 |              133 |
| AG   | Safenwil           |          1120 |    41,6 |        64,4 |           25 |              479 |
| ZH   | Weisslingen        |           969 |    41,9 |        61,5 |           25 |              406 |
| AG   | Sarmenstorf        |           865 |    42,0 |        59,7 |           25 |              340 |
| AG   | Herznach-Ueken     |           761 |    42,0 |        56,9 |           25 |              214 |
| AG   | Boswil             |           741 |    42,1 |        70,4 |           25 |              388 |
| AG   | Schafisheim        |           856 |    42,2 |        63,6 |           25 |              294 |

### Vorbildlich laufende Pflege (ab 500 Wohngebäuden)

| KT   | Gemeinde        |   Wohngebäude |   Index | Pflegemuster   |   aktive Tage 24 Mt. |
|:-----|:----------------|--------------:|--------:|:---------------|---------------------:|
| SG   | Sevelen         |          1465 |   100,0 | laufend        |                   32 |
| SG   | Bad Ragaz       |          1469 |   100,0 | laufend        |                   42 |
| SG   | Amden           |           991 |    99,9 | laufend        |                   41 |
| SG   | Gommiswald      |          1700 |    99,9 | laufend        |                   88 |
| SG   | Oberbüren       |          1101 |    99,9 | laufend        |                   27 |
| SG   | Wattwil         |          2038 |    99,9 | laufend        |                   76 |
| SG   | St. Margrethen  |          1244 |    99,9 | laufend        |                   50 |
| SG   | Degersheim      |          1073 |    99,9 | laufend        |                   58 |
| ZH   | Zürich          |         36996 |    99,8 | laufend        |                  267 |
| SG   | Eschenbach (SG) |          2630 |    99,8 | laufend        |                   80 |
| SG   | Mels            |          2458 |    99,8 | laufend        |                  115 |
| SG   | Wartau          |          1710 |    99,8 | laufend        |                   75 |

### Meiste Verdachtsfälle in absoluten Zahlen

Diese Liste ist für die Praxis interessanter als die Prozentwerte: Hier liegt die grösste
Menge an Gebäuden, bei denen der Heizungseintrag fossil und ungeprüft ist.

| KT   | Gemeinde      |   Wohngebäude |   Verdachtsfälle |   % Verdacht |   Index |
|:-----|:--------------|--------------:|-----------------:|-------------:|--------:|
| SH   | Schaffhausen  |          6742 |             3427 |         50,8 |    62,9 |
| TG   | Frauenfeld    |          4783 |             2407 |         50,3 |    62,1 |
| AG   | Wettingen     |          3378 |             2200 |         65,1 |    44,9 |
| AG   | Wohlen (AG)   |          3312 |             2069 |         62,5 |    51,5 |
| GR   | Chur          |          5066 |             1991 |         39,3 |    67,0 |
| GL   | Glarus Nord   |          5327 |             1816 |         34,1 |    55,0 |
| AG   | Brugg         |          2959 |             1793 |         60,6 |    47,4 |
| BE   | Bern          |         14856 |             1672 |         11,3 |    89,2 |
| TI   | Lugano        |         10518 |             1636 |         15,6 |    76,7 |
| VS   | Crans-Montana |          3761 |             1615 |         42,9 |    54,7 |
| TG   | Kreuzlingen   |          3275 |             1604 |         49,0 |    62,8 |
| ZH   | Dübendorf     |          3449 |             1551 |         45,0 |    59,4 |
| VD   | Lausanne      |          9076 |             1549 |         17,1 |    82,1 |
| AR   | Herisau       |          3223 |             1492 |         46,3 |    58,2 |
| LU   | Luzern        |          7670 |             1477 |         19,3 |    84,3 |

---

## 4 Datenqualität der Quelle

Vor jedem Report läuft `python src/checks.py`, eine Reihe von Datenqualitäts- und
Regressionsprüfungen. Was dabei aufgefallen ist:

- **7 Einträge tragen ein Aktualisierungsdatum in der Zukunft**, im Extremfall neun
  Monate. Erfassungsfehler in der Quelle, nicht korrigierbar, aber überwacht.
- **1'044'538 Gebäude haben überhaupt kein Aktualisierungsdatum.** Das sind überwiegend
  Gebäude ohne Wohnnutzung und ohne Wärmeerzeuger.
- Ein Regressionstest hält die Zürcher Zahlen aus der Detailauswertung fest. Ändert sich die
  Fachlogik, fällt er auf, bevor Zahlen im Report landen.

---

## 5 Die Grenze dieser Auswertung

**Der Index misst dokumentierte Pflege, nicht Richtigkeit.** Das lässt sich in diesem Projekt
belegen, weil für den Kanton Zürich eine unabhängige Gegenprobe existiert: 458 Baugesuche für
einen Heizungsersatz wurden mit dem Registerstand verglichen.

Ergebnis: **Bei 41 % der Fälle zeigt das GWR weiterhin den alten Energieträger**, obwohl das
Baugesuch mindestens ein halbes Jahr zurückliegt. Bei Gesuchen ab 18 Monaten sind es noch 36 %.

Der entscheidende Punkt: **Die Stadt Zürich hat null Einträge aus der Volkszählung 2000.** Nach
dieser Auswertung ist sie sauber. In der Gegenprobe verfehlt sie bei rund zwei Dritteln der
Heizungs-Baugesuche die Nachführung. Metadaten zählen ersetzt nicht, Ereignisse zu prüfen.

Daraus folgt für die Lesart dieses Reports:

1. Ein hoher Index heisst: Das Register wurde angefasst. Nicht: Die Einträge stimmen.
2. Ein niedriger Index ist dagegen aussagekräftig. Wo die Volkszählung 2000 noch die
   Hauptquelle ist, wurde tatsächlich nichts geprüft.
3. Das Pflegemuster trägt mehr Information als der Index. Laufende Pflege über viele Tage
   ist ein besseres Zeichen als ein hoher Punktwert aus einem Import.

Die Auswertung erfasst ausserdem nur Gebäude mit Wohnnutzung (Gebäudekategorien 1020, 1030,
1040) und nur den Status "bestehend". Wärmeerzeuger 2 und Warmwasser bleiben unberücksichtigt.

### 5.1 Wo überhaupt gegengeprüft werden kann

Der Index oben lässt sich für alle 26 Kantone rechnen, weil er nur das GWR braucht.
Die Gegenprobe braucht eine zweite Quelle - und die gibt es nur stellenweise:

| KT   |   Anlagen |   davon datiert |   Widerspruch Anlage |   Verdacht Solar |
|:-----|----------:|----------------:|---------------------:|-----------------:|
| ZH   |     39470 |               0 |                 2013 |             4045 |
| SG   |     29198 |           29198 |                   93 |               59 |
| LU   |     21783 |           14664 |                    0 |              489 |
| BE   |     14661 |           14485 |                  748 |             2648 |
| SO   |      8863 |            8780 |                  257 |              728 |
| TG   |      4532 |            4532 |                  121 |             1282 |
| GE   |      3668 |            3538 |                    3 |              254 |
| ZG   |      2792 |            2791 |                  210 |              151 |
| BL   |      2629 |            2629 |                   81 |               40 |
| AI   |      2419 |            2419 |                   16 |               19 |
| SZ   |      1675 |            1522 |                   87 |              463 |
| SH   |      1235 |               0 |                   30 |              255 |
| UR   |       847 |               0 |                    0 |              110 |
| AG   |         0 |               0 |                    0 |             4784 |
| VD   |         0 |               0 |                    0 |             2122 |
| VS   |         0 |               0 |                    0 |             1271 |
| GR   |         0 |               0 |                    0 |             1043 |
| JU   |         0 |               0 |                    0 |              764 |
| AR   |         0 |               0 |                    0 |              564 |
| TI   |         0 |               0 |                    0 |              494 |
| NE   |         0 |               0 |                    0 |              330 |
| GL   |         0 |               0 |                    0 |              206 |
| FR   |         0 |               0 |                    0 |              141 |
| OW   |         0 |               0 |                    0 |               91 |
| NW   |         0 |               0 |                    0 |               84 |
| BS   |         0 |               0 |                    0 |                0 |

Ein leeres Feld heisst **nicht**, dass der Kanton sauber ist. Es heisst, dass niemand
nachsehen kann. Umgekehrt sieht ein Kanton mit offenen Anlagendaten zwangsläufig
schlechter aus, weil bei ihm überhaupt etwas gefunden werden kann. **Jede Rangliste in
diesem Report ist zuerst eine Rangliste der Datenoffenheit.** Die vollständige
Quellenlage je Kanton steht in `reports/quellenmatrix.md`.

### 5.2 Wie zuverlässig die Zuordnung ist

Ein Beleg nützt nur, wenn er beim richtigen Gebäude landet. Zwei unabhängige Messungen
dazu, mit sehr unterschiedlichem Ergebnis:

| Beleg | Referenz | Treffer |
|---|---|---|
| Photovoltaikanlage | BFE-Datensatz mit EGID-Spalte, 90'558 Anlagen mit beiden Zuordnungswegen | **99,4 %** Übereinstimmung |
| Erdwärmesonde | amtliche EGID des Kantons Zug, 805 Anlagen | **73,8 %** Recall bei 20 m |

Der Unterschied hat einen einfachen Grund: **Eine Solaranlage liegt auf dem Gebäude, eine
Erdsonde daneben.** Bei der Photovoltaik ist die Koordinate praktisch das Gebäude, bei der
Sonde ist sie ein Punkt im Garten - und der kann näher beim Nachbarn liegen. Auch bei 50 m
Radius steigt der Sonden-Recall nur auf 80 %; ein grösserer Umkreis kauft vor allem
Nachbarn dazu (`reports/zuordnung_zg.md`).

Für die Fallzahlen heisst das: Bei den Sonden sind sie eher Unter- als Obergrenzen, weil
rund ein Viertel der echten Fälle gar nicht gefunden wird.

---

## 6 Was als Nächstes gemessen werden sollte

Ein einzelner Snapshot zeigt einen Zustand. Die interessantere Grösse ist die Bewegung:
Wie viele Heizungseinträge ändert ein Kanton pro Monat tatsächlich?

Die Pipeline legt deshalb bei jedem Lauf einen Parquet-Snapshot pro Kanton ab
(`data/snapshots/gwr/snapshot_date=.../kanton=.../data.parquet`, rund 60 MB für die ganze
Schweiz). Sobald zwei Stände vorliegen, liefert `v_gold_veraenderung` die Änderungsrate je
Kanton und Zeitraum. Diese Kennzahl lässt sich nicht nachträglich beschaffen, sie entsteht
nur durch Sammeln ab jetzt.

---

## Reproduzierbarkeit

```bash
pip install -r requirements.txt
python src/ingest.py       # alle 26 Kantone laden, Snapshot schreiben
python src/pipeline.py ch  # Silver- und Gold-Layer rechnen
python src/checks.py       # Datenqualitäts- und Regressionsprüfungen
python src/report_ch.py    # diesen Report erzeugen
```
