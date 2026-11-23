# Detailauswertung Kanton Zürich: Baugesuche gegen Registerstand

Datenstand GWR {stand_gwr}, Baugesuche bis {stand_bg}. Gemessen wird, ob Heizungs-Baugesuche
und Wärmenutzungsanlagen im Gebäude- und Wohnungsregister (GWR) nachgeführt sind: im Kanton
Zürich im Detail, bei den Wärmenutzungsanlagen für 13 Kantone.

Erzeugt von `src/report.py` aus `src/report_template.md`. Tabellen und Kennzahlen kommen aus
der Pipeline. Einzelne Werte im Fliesstext und die Sensitivitätsrechnung in Abschnitt 2.6
stehen fest in der Vorlage und stammen aus dem Lauf vom September 2026.

---

## Kurzfassung

Die Studie fragt, ob sich veraltete Heizungsangaben im GWR aus offenen Daten erkennen lassen
und ob es dafür genug Belege gibt. Die Antwort aus den Daten ist zweigeteilt.

**Die Datenlücke ist real und gross.** Von {t3_n} eindeutig zugeordneten Heizungs-Baugesuchen,
die mindestens sechs Monate zurückliegen, zeigt das GWR bei **{luecke_pct} %** immer noch den alten
Energieträger mit einem Aktualisierungsdatum vor dem Baugesuch. {nachgef_pct} % sind sauber
nachgeführt, in der weiten Auslegung {nachgef_weit} %. Auch bei Baugesuchen, die 18 Monate und
länger zurückliegen, bleibt die Lücke bei {luecke_18} %. Das erste Abbruchkriterium der Studie
(über 80 % nachgeführt) ist damit nicht erfüllt.

**Die Belege sind für die meisten Gemeinden zu dünn.** Im ganzen Kanton finden sich rund
{heiz_pro_jahr_kt} Heizungs-Baugesuche pro Jahr. Die mittlere Gemeinde kommt
auf **{median_gesuche} Gesuche pro Jahr**, drei Viertel der Gemeinden liegen unter {q75_gesuche}.
Für eine Auswertung je Gemeinde reicht das nicht; nur Zürich und Winterthur haben genug
Fälle. Damit ist das zweite Abbruchkriterium der Studie erfüllt (Test 2: nur eine Handvoll
Gesuche pro Gemeinde und Jahr).

**Ein dritter Befund relativiert die ersten beiden.** Neun Kantone veröffentlichen ihre
Wärmenutzungsanlagen mit Datum (Abschnitt 2.7). Von den Anlagen, die dort als gebaut gelten,
sind {t6_nachgefuehrt} % im GWR sichtbar, und der Wert hängt am Alter: Anlagen aus den letzten
2 bis 4 Jahren sind zu {t6_neu} % erfasst, Anlagen ab 20 Jahren zu {t6_alt} %.
**Die Nachführung wird besser.** Der Rückstand liegt überwiegend im Altbestand.

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.** Details in Abschnitt 5.

Ein methodischer Nebenbefund: Die Informationsquelle im GWR (Code 860 "Volkszählung 2000")
taugt nicht als Indikator für Datenqualität. Die Stadt Zürich hat 0 % Einträge mit Quelle 860
und wäre nach Test 1 sauber. In Test 3 fehlt dort trotzdem bei {luecke_zh} % der
Heizungs-Baugesuche die Nachführung. Veraltete Einträge zeigen sich erst, wenn Ereignisse
gegen den Registerstand geprüft werden; die Metadaten allein zeigen sie nicht.

---

## 1 Datenbasis

### 1.1 Quellen

{quellen}

Alle Quellen sind offen zugänglich; die Nutzungsbedingungen je Quelle stehen in
[lizenzen.md](lizenzen.md). Rohdaten liegen in `data/raw/` und sind bewusst nicht im Git.
`data/raw/manifest.json` hält URL, Grösse, SHA-256 und Downloadzeitpunkt fest.

### 1.2 Umfang

{umfang}

### 1.3 Stand und Lücken

- **GWR:** Exportdatum {stand_gwr}. Vollständig für den ganzen Kanton.
  Die Codelisten stammen aus der mitgelieferten Datei `kodes_codes_codici.csv`, nicht aus
  Sekundärquellen.
- **Baugesuche:** Publikationen bis {stand_bg}. Die Sammlung des Statistischen Amts ist erst
  ab Herbst 2024 vollständig; frühere Jahre enthalten nur Einzelfälle (2022: 3, 2023: 74).
  Alle Zeitreihen in diesem Report beginnen deshalb im Oktober 2024.
  Die Felder `bfs_nr` und `municipality_name` sind erst ab 2025 gefüllt. Für 2024 ist die
  Gemeinde über das zugeordnete Gebäude beziehungsweise über PLZ und Ortsname hergeleitet;
  danach bleiben 402 von {n_bg} Gesuchen ohne Gemeinde.
  Parzellengeometrien gibt es erst ab 2025.
- **Mehrfachpublikationen:** Dasselbe Vorhaben erscheint oft mehrmals. {n_doppelt} von {n_bg}
  Publikationen ({pct_doppelt} %) wiederholen einen bereits vorhandenen Beschrieb an derselben
  Adresse; ein Grossprojekt kommt {max_doppelt}-mal vor, offenbar einmal je betroffene
  Liegenschaft. Alle Auswertungen zählen deshalb **Vorhaben, nicht Publikationen**:
  {n_vorhaben} Vorhaben, davon {n_heiz_vorhaben} mit Heizungsbezug. Ohne diese Korrektur
  lägen die Fallzahlen rund ein Fünftel zu hoch.
- **Photovoltaik:** letzte Inbetriebnahme im verwendeten Datensatz {stand_pv}.
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

{t1_kanton}

**{n_kandidaten} Kandidaten** von {n_wohngeb} Wohngebäuden im Kanton. Verteilung der
Informationsquelle über alle Wohngebäude:

{t1_quellen}

Ein Drittel aller Heizungseinträge im Kanton geht immer noch auf die Volkszählung 2000 zurück.
Die Spannweite zwischen den Gemeinden ist aber enorm:

{t1_spann}

Fokusgemeinden:

{t1_fokus}

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

{n_heiz} von {n_bg} Publikationen sind über Stichworte als Heizungsereignis erkannt; nach
Zusammenfassen der Mehrfachpublikationen bleiben **{n_heiz_vorhaben} Vorhaben**
(Details zur Erkennung in Abschnitt 4). Verteilung des erkannten neuen Energieträgers
über alle Publikationen:

{t2_traeger}

Zeitreihe für den ganzen Kanton:

{t2_monat}

Der September 2026 ist ein angebrochener Monat (bis zum {stand_bg}), die absolute Zahl dort
ist deshalb nicht vergleichbar. Der Anteil der Heizungsgesuche an allen Baugesuchen nimmt im
Beobachtungszeitraum zu: von {t2_anteil_erstes} % im ersten Quartal der Reihe ({t2_quartal_erstes})
auf {t2_anteil_letztes} % im letzten vollständigen Quartal ({t2_quartal_letztes}).

Entscheidend ist die Verteilung über die Gemeinden:

{t2_spann}

**Hier greift das zweite Abbruchkriterium der Studie.** Die mittlere Gemeinde hat
{median_gesuche} Heizungs-Baugesuche pro Jahr, drei Viertel der Gemeinden haben höchstens
{q75_gesuche}. Die Belege konzentrieren sich auf wenige grosse Gemeinden:

{t2_top}

Fokusgemeinden:

{t2_fokus}

Illnau-Effretikon hat unter den Fokusgemeinden den tiefsten Anteil an Heizungsgesuchen,
Winterthur und Volketswil haben den höchsten (Spalte "% Heizung"). Der Unterschied liegt an
der Publikationspraxis: Manche Gemeinden publizieren einen Heizungsersatz als eigenes
Baugesuch, andere behandeln ihn als bewilligungsfrei oder als Nebenpunkt eines grösseren
Vorhabens.

**Grössenordnung zum Vergleich:** Im Kanton stehen rund 127'000 fossil beheizte Wohngebäude.
Bei einer Ersatzrate von 3 bis 5 % pro Jahr wären das 4'000 bis 6'000 Heizungswechsel jährlich.
Gefunden werden über die Baugesuche rund {heiz_pro_jahr_kt} pro Jahr. **Baugesuche erfassen damit
grob geschätzt 10 bis 20 % der tatsächlichen Heizungswechsel.** Der Rest sind Ersatzvorhaben im
Gebäudeinneren, die keine Baubewilligung brauchen. Sichtbar wird vor allem die aussen aufgestellte
Luft/Wasser-Wärmepumpe, weil die wegen Lärm und Grenzabstand bewilligungspflichtig ist.

### 2.3 Test 3 - Werden Baugesuche schon nachgeführt?

Der zentrale Test der Studie. Grundmenge: Heizungs-Baugesuche, deren Publikation mindestens sechs Monate
zurückliegt, die genau einem Gebäude zugeordnet werden konnten und die kein reiner Neubau sind.
Das sind {t3_n} Fälle.

{t3_haupt}

Zusammengefasst: **{nachgef_pct} % sauber nachgeführt**, in der weiten Auslegung (inklusive
"Quelle 869 nach dem Gesuch" und "Energieträger passt, Datum älter") **{nachgef_weit} %**.
Dem stehen **{luecke_pct} % klare Lücken** gegenüber.

Der naheliegende Einwand lautet: Sechs Monate sind zu kurz, gebaut wird erst später. Deshalb
dieselbe Auswertung nach Alter des Baugesuchs:

{t3_alter}

Die Nachführung holt mit der Zeit auf, aber sie holt nicht ein. Bei Baugesuchen, die 18 Monate
und länger zurückliegen, sind {nachgef_18} % nachgeführt und **{luecke_18} % weiterhin nicht**.
Die Schwelle von 80 % (Abbruchkriterium der Studie) wird in keinem Altersfenster erreicht.

Was in den Lückenfällen im GWR steht:

{t3_gwr_bei_luecke}

Die Gemeinden streuen stark (Gemeinden mit mindestens 8 auswertbaren Fällen):

{t3_gemeinden}

Fokusgemeinden:

{t3_fokus}

Illnau-Effretikon und Fehraltorf fehlen in dieser Tabelle: Beide haben nach allen Filtern
null auswertbare Fälle. Für diese Gemeinden lässt sich die Frage aus Test 3 mit Baugesuchen
nicht beantworten.

In Winterthur zeigt sich die Grenze einer Sammelaktualisierung. Die Stadt hat im Februar 2024
die Heizungsdaten flächendeckend aktualisiert; 84 % aller Wohngebäude tragen ein
Aktualisierungsdatum ab 2024. Trotzdem fehlt bei {luecke_win} % der Heizungs-Baugesuche die
Nachführung, typischerweise mit diesem Muster: Energieträger Gas, Quelle "Gemäss Daten der
Gemeinde", Datum 2024-02-09, Baugesuch für den Wärmepumpenersatz aus 2025 oder 2026. **Eine
Sammelaktualisierung erzeugt einen sauberen Stichtag, aber keinen laufenden Prozess.**

### 2.4 Gegenprobe - wie viel führt der Kanton insgesamt nach?

Aktualisierungen der Heizungsangabe bei Wohngebäuden, nach Jahr des Aktualisierungsdatums:

{t3_volumen}

{akt_2024} Heizungseinträge tragen ein Aktualisierungsdatum aus dem Jahr 2024, {akt_2026} eines
aus 2026 (bis zum Exportdatum). {wp_seit_2024} Wohngebäude mit Aktualisierungsdatum ab 2024
weisen eine Wärmepumpe aus. Als Informationsquelle tragen die seit 2024 aktualisierten
Einträge vor allem Gemeindedaten (Code 865), kantonale Daten und Gebäudeprogramm (864),
Baubewilligungen (869) und die Feuerungskontrolle (855).

**Der Kanton und die Gemeinden führen also bereits in grossem Umfang nach, über Kanäle, die pro
Jahr ein Vielfaches dessen abdecken, was Baugesuche sichtbar machen.** Die Lücke aus Test 3
ist eine Lücke in einem laufenden Prozess.

### 2.5 Test 4 - Fälle ohne Baugesuch

Gebäude mit Wohnnutzung, registrierter Photovoltaikanlage, fossilem Heizungseintrag und
Quelle 860: **{t4_kanton} Gebäude im Kanton**.

{t4_top}

Fokusgemeinden:

{t4_fokus}

Das ist nur ein schwaches Indiz. Eine PV-Anlage sagt nichts über die Heizung; sie
zeigt nur, dass die Eigentümerschaft in den letzten Jahren am Gebäude etwas gemacht hat und dass
der Heizungseintrag seither nicht angefasst wurde. Als eigenständiger Beleg ist das zu wenig,
als zusätzliches Merkmal neben einem anderen Beleg brauchbar.

### 2.6 Test 5 - Wärmenutzungsanlagen gegen den Registerstand

Der Test umfasst die {t5_n_kantone} Kantone, die ihre Anlagen zur Wärmenutzung offen
veröffentlichen (überwiegend Erdwärmesonden; die Anlagentypen stehen in der Tabelle).
Zusammen **{t5_anlagen_total} Anlagen**. Davon zählt die Pipeline {t5_gebaut} als gebaut
(Merkmal `ist_gebaut` in `sql/test5.sql`). Das Merkmal ist grosszügig: Wo ein Kanton kein
Statusfeld führt, gelten alle veröffentlichten Anlagen als bestehend, und auch die Urner
Konzessionen und die Luzerner Luft-Wasser-Wärmepumpen ("bewilligt oder geplant") zählen mit,
obwohl ihre Ausführung nicht belegt ist.

{t5_anlagen}

Der Unterschied zu Test 4: Eine Photovoltaikanlage sagt nichts über die Heizung, eine
Erdwärmesonde schon. Steht im GWR an einem solchen Gebäude trotzdem Öl oder Gas, widersprechen
sich die beiden Quellen.

**Was im GWR rund um eine Wärmenutzungsanlage steht** (Wohngebäude innerhalb von 20 m,
alle {t5_n_kantone} Kantone):

{t5_umkreis}

**{t5_pct_wp} %** der Zürcher Anlagen haben ein Gebäude mit Wärmepumpen-Eintrag im Umkreis.
Die Werte je Kanton:

{t5_kantone}

Die Spanne reicht von {t5_pct_min} % ({t5_kt_min}) bis {t5_pct_max} % ({t5_kt_max}).
{t5_n_mitte} Kantone liegen zwischen 45 % und 56 % ({t5_kt_mitte}),
{t5_n_tief} darunter ({t5_kt_tief}) und {t5_n_hoch} darüber ({t5_kt_hoch}). Ein einheitliches
Bild ergeben die Kantone nicht. Ein Teil der Unterschiede liegt an den Quellen und nicht am
Register: St. Gallen führt ein Anlagenregister mit der Wärmepumpe selbst, die Luzerner
Koordinaten sind nicht gebäudegenau, und in Genf steht bei vielen Gebäuden im Umkreis
"Unbestimmt" als Energieträger ([quellenmatrix.md](quellenmatrix.md),
[docs/datenquellen.md](../docs/datenquellen.md)).

Für Uri ({t5_pct_wp_ur} %) kommt hinzu: Der Datensatz meldet ausschliesslich
"Konzession erteilt". Eine erteilte Konzession heisst noch nicht, dass gebohrt wurde. Uri ist
deshalb aus der datierten Auswertung in Abschnitt 2.7 ausgeschlossen.

**Ergebnis:** **{t5_widerspruch} Wohngebäude** in den ausgewerteten Kantonen
({t5_widerspruch_zh} in Zürich, {t5_widerspruch_be} in Bern) sind fossil eingetragen,
obwohl innerhalb von 20 m eine Wärmenutzungsanlage liegt, die als gebaut gilt, und kein
Gebäude dort eine Wärmepumpe ausweist. Davon tragen {t5_vz2000} die Quelle
"Volkszählung 2000". Die mittlere Distanz zur Anlage beträgt {t5_med_dist} m.

Diese Zahl stammt aus dem Lauf vom September 2026 und zählt jedes fossil eingetragene
Wohngebäude im Umkreis einer Anlage. Die Verdachtsliste zählt enger: Sie übernimmt eine Anlage
nur, wenn sie genau einem Gebäude zugeordnet ist (`sql/zuordnung_anlagen.sql`,
[docs/methode.md](../docs/methode.md)). Deshalb nennen
[kantonsvergleich.md](kantonsvergleich.md) und die Listenzahlen deutlich kleinere Werte.

{t5_gemeinden}

Fokusgemeinden (Kanton Zürich):

{t5_fokus}

**Wie robust ist das?** Der Suchradius bestimmt das Ergebnis, deshalb die Sensitivitäts-
rechnung für Zürich (fest in der Vorlage, Lauf vom September 2026):

{t5_radius}

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

Grundmenge: {t6_n} Anlagen mit Datum und mindestens einem Gebäude im Umkreis.

{t6_status}

**{t6_nachgefuehrt} % nachgeführt, {t6_widerspruch} % im Widerspruch.** Die restlichen
Fälle sind Gebäude, die weder Wärmepumpe noch fossil ausweisen, meist "Unbestimmt".

Die Entwicklung über die Zeit:

{t6_alter}

**Die Nachführung wird besser.** Anlagen, deren Datum 2 bis 4 Jahre zurückliegt, sind zu
{t6_neu} % im Register sichtbar. Bei Anlagen, die 20 Jahre und älter sind, sind es
{t6_alt} %. Der Rückstand liegt überwiegend im Altbestand.

Jahr für Jahr:

{t6_jahre}

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

{match_quote}

Insgesamt **{match_pct} % der Heizungsgesuche** konnten zugeordnet werden, ab 2025 mit
Parzellengeometrie **{match_pct_2025} %**.

Die beiden Wege dienen sich gegenseitig als Kontrolle:

{match_konsistenz}

**{konsistenz_pct} % Übereinstimmung** bei den Gesuchen, die über beide Wege zugeordnet werden.

Die Zuordnung der Photovoltaikanlagen über die Koordinate (nächstes Gebäude, maximal 25 m) ist
gegen die EGID-Spalte der gekürzten BFE-Datei geprüft:

{pv_valid}

### 3.1 Manuelle Stichprobe

`src/report.py` schreibt 20 zufällige Zuordnungen nach
`data/processed/stichprobe_20_matches.md`. Die Datei ist gebäudegenau und deshalb nicht Teil
des Repositories. Ergebnis der Durchsicht:

- **19 von 20** Gesuchstexten betreffen tatsächlich eine Heizung.
- **1 Fehltreffer:** "Einbau Wohnung im Dachgeschoss der Scheune ... **Bestehende** Pelletsheizung
  im Hauptgebäude, WW: WP-Boiler". Die Stichwortsuche kann "bestehend" nicht von "neu" trennen.
  Im ganzen Datensatz enthalten 54 der {n_heiz} erkannten Gesuche das Wort "bestehend"; das ist
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
7. **Mehrfachpublikationen verzerren rohe Zählungen.** {pct_doppelt} % der Publikationen
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
| Test 3 zeigt eine grosse Lücke | {luecke_pct} % nicht nachgeführt, {nachgef_pct} % nachgeführt, weit gefasst {nachgef_weit} % | ja |
| Test 2 liefert genug Fälle | Median {median_gesuche} Heizungsgesuche pro Gemeinde und Jahr | nein |
| Abbruchkriterium: über 80 % nachgeführt | in keinem Altersfenster erreicht | nein |
| Abbruchkriterium: nur eine Handvoll Gesuche pro Gemeinde | trifft auf drei Viertel der Gemeinden zu | ja |
| Zusatzbefund: Liegt der Rückstand im Altbestand? | ja, Erfassung {t6_alt} % bei Anlagen ab 20 Jahren, {t6_neu} % bei Anlagen aus den letzten 2 bis 4 Jahren | kein Kriterium |

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.**

Begründung:

- Die Lücke ist nachweisbar: Der Anteil nachgeführter Baugesuche liegt weit unter der
  Schwelle von 80 %.
- Baugesuche allein reichen als Beleg nicht. Die mittlere Gemeinde kommt auf
  {median_gesuche} Heizungs-Baugesuche pro Jahr; für eine Auswertung je Gemeinde ist das
  zu wenig.
- Gleichzeitig wird bereits in grossem Umfang nachgeführt: {akt_2026} aktualisierte
  Heizungseinträge allein 2026. Ein Abgleich aus offenen Daten kann vor allem die Lücke
  zwischen zwei Sammelaktualisierungen sichtbar machen.
- **Der Rückstand liegt im Altbestand.** Der Zeitverlauf der datierten Anlagen (Abschnitt 2.7)
  zeigt es: {t6_alt} % Erfassung bei Anlagen ab 20 Jahren, {t6_neu} % bei Anlagen aus den
  letzten 2 bis 4 Jahren. Das spricht für eine einmalige Bereinigung und gegen eine
  Dauerüberwachung.
- Methodisch ist die Fragestellung gut prüfbar: offene Daten in brauchbarer Qualität, eine
  Zuordnungsaufgabe (Entity Resolution), eine Textextraktion und eine Evaluation gegen
  kantonale Gegenquellen.

### Was aus dem Befund folgt

Für eine Weiterführung des Abgleichs ergibt sich aus den Daten:

- **Die passende Ebene ist der Kanton oder eine Stadt, nicht die einzelne Gemeinde.** Zürich und
  Winterthur haben mit Abstand die meisten Heizungs-Baugesuche (Abschnitt 2.2), und beide
  zeigen mit {luecke_zh} % und {luecke_win} % grosse Lücken.
- **Baugesuche reichen als Belegquelle nicht.** Es braucht weitere Quellen, etwa
  Feuerungskontrolle, Förderdaten des Gebäudeprogramms, Gasnetz-Abmeldungen und die
  Pronovo-Anlagendaten. Welche davon offen zugänglich sind, steht in
  [quellenvergleich.md](quellenvergleich.md).
- **Wärmenutzungsanlagen sind die ergiebigste offene Quelle.** Sie liefern einen direkten
  Widerspruch statt eines Indizes, sind in {t5_n_kantone} Kantonen offen verfügbar und in
  neun davon datiert.
- **Naheliegend ist eine einmalige Bereinigung, keine Dauerüberwachung.** Der Rückstand
  liegt im Altbestand.
- **Offen ist die Sicht der kantonalen Fachstelle.** Ob die fehlende Nachführung bei
  {luecke_zh} % der Stadtzürcher Heizungs-Baugesuche dort als Problem gilt und wer dafür
  zuständig ist, lässt sich aus den Daten nicht beantworten.

---

## 6 Folgearbeiten

Die Detailauswertung vom September 2026 nennt fünf Folgearbeiten. Ihr Stand:

1. **Textextraktion mit einem Sprachmodell.** Umgesetzt als Prüfschritt nach der
   Stichwortsuche und an 150 gelabelten Texten gemessen
   ([extraktion_evaluation.md](extraktion_evaluation.md)).
2. **Weitere Belegquellen.** Umgesetzt für Wärmenutzungsanlagen aus {t5_n_kantone} Kantonen,
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
