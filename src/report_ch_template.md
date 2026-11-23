# Heizungsangaben im GWR: Wie gut pflegen die Kantone ihr Register?

Datenstand {stand}, alle 26 Kantone, {gemeinden} Gemeinden, {wohngeb} Wohngebäude. Gemessen
wird je Kanton und Gemeinde, wie vollständig und wie aktuell die Heizungsangaben im GWR sind
und aus welcher Quelle sie stammen.

Erzeugt von `src/report_ch.py` aus den Parquet-Snapshots. Tabellen und Kennzahlen kommen aus
der Pipeline; fest in der Vorlage stehen die Zuger Zuordnungswerte in Abschnitt 5.2
(aus [zuordnung_zg.md](zuordnung_zg.md)) und die Basler Werte unter "Pflegemuster".

Interaktive Fassung: [dashboard.html](dashboard.html).
Die Detailauswertung für den Kanton Zürich mit Baugesuchen steht in [report.md](report.md).

---

## Kurzfassung

Im Gebäude- und Wohnungsregister trägt jedes Gebäude einen Eintrag zu Energieträger und
Wärmeerzeuger, dazu eine Informationsquelle und ein Aktualisierungsdatum. Wie gut dieser
Eintrag gepflegt wird, unterscheidet sich stark zwischen den Kantonen.

- **{pct_vz2000} % aller Schweizer Wohngebäude** ({vz2000} Stück) tragen bei der Heizung
  immer noch die Volkszählung 2000 als Quelle. Der Eintrag ist seit einem Vierteljahrhundert
  nicht bestätigt.
- Das **Median-Alter** der Heizungsangabe liegt schweizweit bei **{median_alter} Jahren**.
- **{pct_fossil} %** der Wohngebäude sind fossil beheizt ({fossil} mit Öl oder Gas),
  **{pct_wp} %** haben eine Wärmepumpe.
- **{kandidaten} Gebäude** ({pct_kandidaten} %) sind Kandidaten: fossil beheizt und der
  Eintrag entweder ungeprüft (Quelle 860) oder älter als 15 Jahre. Ein Kandidat ist noch
  kein Verdachtsfall. Als Verdachtsfall gilt in dieser Studie nur ein Gebäude, zu dem ein
  Beleg vorliegt ([docs/methode.md](../docs/methode.md)).
- Die Spannweite zwischen den Kantonen reicht von **{best_kt} mit {best_idx} Punkten** bis
  **{schlecht_kt} mit {schlecht_idx}**. In **{n_rueckstand} Kantonen** überwiegt der
  unbearbeitete Altbestand.

Eine Einschränkung gilt für die ganze Auswertung: **Der Index misst Pflege, nicht
Richtigkeit.** Wie weit beides auseinanderliegt, zeigt Abschnitt 5.

---

## 1 Der Pflege-Index

Drei Anteile über alle Wohngebäude, gemittelt:

| Bestandteil | Was gemessen wird |
|---|---|
| Vollständigkeit | Anteil mit konkretem Energieträger (nicht leer, nicht "unbestimmt", nicht "andere") |
| Aktualität | Anteil mit Aktualisierungsdatum jünger als 15 Jahre |
| Herkunft | Anteil, der **nicht** aus der Volkszählung 2000 stammt |

Quelle 860 (Volkszählung 2000) heisst ungeprüft, nicht falsch: Der Eintrag ist seit 2000
nicht bestätigt.

Notenklassen: A ab 90, B ab 75, C ab 60, D ab 45, E darunter.

---

## 2 Kantone

{rang}

### Pflegemuster

Der Index allein genügt nicht. Ein Kanton, der einmal alles auf einen Schlag importiert,
sieht darin aus wie einer, der laufend arbeitet. Deshalb wird zusätzlich gemessen, wie sich
die Aktualisierungsdaten verteilen:

- **laufend** - die Daten streuen über viele Tage, es wird kontinuierlich gearbeitet
- **Sammelimport** - mindestens 40 % aller Einträge tragen denselben Tag
- **Rückstand** - weniger als die Hälfte der Gebäude hat überhaupt eine Angabe aus den letzten 15 Jahren
- **sporadisch** - weder das eine noch das andere

{muster}

Die Kantone mit Sammelimport im Detail:

{bulk}

Basel-Stadt ist der Extremfall: 99,1 % aller Wohngebäude tragen dasselbe Aktualisierungsdatum,
Quelle ist zu 99,7 % die Feuerungskontrolle. Der Index von 100 Punkten steht dort für einen
einzigen Schreibvorgang.

### Informationsquellen schweizweit

{quellen_ch}

---

## 3 Gemeinden

{gem_noten}

**{n_gem_de} Gemeinden ({pct_gem_de} %) stehen bei Note D oder E**, {n_gem_rueckstand}
Gemeinden sind im Rückstand.

{gem_muster}

### Grösster Rückstand (ab 500 Wohngebäuden)

{schlecht}

### Vorbildlich laufende Pflege (ab 500 Wohngebäuden)

{gut}

### Meiste Kandidaten in absoluten Zahlen

Die Tabelle zeigt, wo absolut die meisten Gebäude mit fossilem Heizungseintrag liegen, der
ungeprüft oder älter als 15 Jahre ist.

{absolut}

---

## 4 Datenqualität der Quelle

Vor jedem Report läuft `python src/checks.py`, eine Reihe von Datenqualitäts- und
Regressionsprüfungen. Was dabei aufgefallen ist:

- **{zukunft} Einträge tragen ein Aktualisierungsdatum in der Zukunft.** Das sind
  Erfassungsfehler in der Quelle; eine Prüfung überwacht ihre Zahl.
- **{ohne_datum} Gebäude haben überhaupt kein Aktualisierungsdatum.** Das sind überwiegend
  Gebäude ohne Wohnnutzung und ohne Wärmeerzeuger.
- Ein Regressionstest hält die Zürcher Zahlen aus der Detailauswertung fest. Ändert sich die
  Fachlogik, fällt er auf, bevor Zahlen im Report landen.

---

## 5 Die Grenze dieser Auswertung

**Der Index misst dokumentierte Pflege, nicht Richtigkeit.** Das lässt sich in diesem Projekt
belegen, weil für den Kanton Zürich eine unabhängige Gegenprobe existiert: {t3_n} Baugesuche für
einen Heizungsersatz wurden mit dem Registerstand verglichen.

Ergebnis: **Bei {t3_luecke} % der Fälle zeigt das GWR weiterhin den alten Energieträger**, obwohl das
Baugesuch mindestens ein halbes Jahr zurückliegt. Bei Gesuchen ab 18 Monaten sind es noch {t3_luecke18} %.

**Die Stadt Zürich hat null Einträge aus der Volkszählung 2000.** Nach dieser Auswertung
ist sie sauber. In der Gegenprobe fehlt bei gut zwei Dritteln ihrer Heizungs-Baugesuche die
Nachführung ([report.md](report.md), Abschnitt 2.3). Die Metadaten zeigen das nicht.

Daraus folgt für die Lesart dieses Reports:

1. Ein hoher Index heisst, dass das Register bearbeitet ist. Er heisst nicht, dass die
   Einträge stimmen.
2. Ein niedriger Index ist dagegen aussagekräftig. Wo die Volkszählung 2000 noch die
   Hauptquelle ist, ist der Bestand ungeprüft.
3. Das Pflegemuster trägt mehr Information als der Index. Laufende Pflege über viele Tage
   ist ein besseres Zeichen als ein hoher Punktwert aus einem Import.

Die Auswertung erfasst ausserdem nur Gebäude mit Wohnnutzung (Gebäudekategorien 1020, 1030,
1040) und nur den Status "bestehend". Wärmeerzeuger 2 und Warmwasser bleiben unberücksichtigt.

### 5.1 Wo überhaupt gegengeprüft werden kann

Der Index oben lässt sich für alle 26 Kantone rechnen, weil er nur das GWR braucht.
Die Gegenprobe braucht eine zweite Quelle - und die gibt es nur stellenweise:

{belege}

"Widerspruch Anlage" zählt fossil eingetragene Wohngebäude, denen eine Wärmenutzungsanlage
eindeutig zugeordnet ist. "Solaranlage und Quelle 860" zählt Wohngebäude mit
Photovoltaikanlage und fossilem Eintrag aus der Volkszählung 2000; das ist nur ein schwaches
Indiz.

Eine Null heisst nicht, dass der Kanton sauber ist, sondern dass eine offene Gegenquelle
fehlt. Umgekehrt sieht ein Kanton mit offenen Anlagendaten zwangsläufig schlechter aus,
weil nur bei ihm etwas gefunden werden kann. **Jede Rangliste in diesem Report ist zuerst
eine Rangliste der Datenoffenheit.** Die vollständige Quellenlage je Kanton steht in
[quellenmatrix.md](quellenmatrix.md).

### 5.2 Wie zuverlässig die Zuordnung ist

Ein Beleg nützt nur, wenn er beim richtigen Gebäude landet. Zwei unabhängige Messungen
dazu, mit sehr unterschiedlichem Ergebnis:

| Beleg | Referenz | Treffer |
|---|---|---|
| Photovoltaikanlage | BFE-Datensatz mit EGID-Spalte, {solar_beide} Anlagen mit beiden Zuordnungswegen | **{solar_pct} %** Übereinstimmung |
| Erdwärmesonde | amtliche EGID des Kantons Zug, 805 Anlagen | **73,8 %** Recall bei 20 m |

Der Unterschied hat einen einfachen Grund: **Eine Solaranlage liegt auf dem Gebäude, eine
Erdsonde daneben.** Bei der Photovoltaik ist die Koordinate praktisch das Gebäude, bei der
Sonde ist sie ein Punkt im Garten - und der kann näher beim Nachbarn liegen. Auch bei 50 m
Radius steigt der Sonden-Recall nur auf 80 %; ein grösserer Umkreis nimmt vor allem
Nachbargebäude dazu ([zuordnung_zg.md](zuordnung_zg.md)).

Für die Fallzahlen heisst das: Bei den Sonden sind sie eher Unter- als Obergrenzen, weil
rund ein Viertel der echten Fälle gar nicht gefunden wird.

---

## 6 Bewegung im Register

Ein einzelner Snapshot zeigt einen Zustand. Wie viele Heizungseinträge ein Kanton
tatsächlich ändert, zeigt erst der Vergleich mehrerer Stände.

Die Pipeline legt deshalb bei jedem Lauf einen Parquet-Snapshot pro Kanton ab
(`data/snapshots/gwr/snapshot_date=.../kanton=.../data.parquet`, rund 60 MB für die ganze
Schweiz). Aus zwei oder mehr Ständen liefert `v_gold_veraenderung` die Änderungsrate je
Kanton und Zeitraum. Die Auswertung der Wochen-Snapshots steht in
[zeitreihe.md](zeitreihe.md).

---

## Reproduzierbarkeit

```bash
pip install -r requirements.txt
python src/ingest.py       # alle 26 Kantone laden, Snapshot schreiben
python src/pipeline.py ch  # Silver- und Gold-Layer rechnen
python src/checks.py       # Datenqualitäts- und Regressionsprüfungen
python src/report_ch.py    # diesen Report erzeugen
```
