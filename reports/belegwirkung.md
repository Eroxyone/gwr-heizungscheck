# Belegwirkung: Trefferquote der Verdachtsfälle je Belegart

Registerstand 14.09.2026. Gemessen wird, wie oft der Registereintrag falsch
ist, wenn zu einem Gebäude ein Beleg vorliegt: je Belegart und für die Verdachtsliste.
Gegenquellen sind der Genfer Wärmeerzeuger-Layer (61'895 Anlagen mit EGID, darunter 9'615
Wärmepumpen und 3'181 Fernwärme-Übergabestationen) und der Zuger Tankkataster (nur Heizöl).

## Warum je Belegart und nicht nach Rang gemessen wird

Der Verdachtsscore kennt nur wenige mögliche Summen, und viele Fälle teilen dieselbe
Punktzahl, in Genf mehrere hundert. Bei einem Rangschnitt (die obersten 20, 100 oder 500
Fälle) entscheidet innerhalb gleicher Punktzahl die Sortierung nach EGID, welche Fälle oben
stehen. Eine Trefferquote entlang der Rangfolge misst dann diese Sortierung und nicht das
Verfahren.

Eine Belegart ist klar abgegrenzt und kommt ohne Rangfolge aus. Die Quoten unten sind
deshalb reproduzierbar.

## Trefferquote je Belegart

"Davon falsch" heisst: Die Gegenquelle zeigt einen anderen Wärmeerzeuger als das Register.
Die Grundrate ist der Anteil falscher Einträge unter allen auswertbaren Gebäuden des Kantons,
der Faktor das Verhältnis der Trefferquote zu dieser Grundrate. Der Vertrauensbereich
(von, bis) ist das Wilson-Intervall zu 95 Prozent. Gezeigt sind Belegarten ab fünf Fällen.

| Kanton   | Belegart                |   Fälle |   davon falsch |   Trefferquote % |   Grundrate % |   Faktor |   von % |   bis % |
|:---------|:------------------------|--------:|---------------:|-----------------:|--------------:|---------:|--------:|--------:|
| GE       | nur Photovoltaik        |    3251 |            445 |             13,7 |           5,4 |      2,5 |    12,5 |    14,9 |
| GE       | Warmwasser-Wärmepumpe   |      90 |              4 |              4,4 |           5,4 |      0,8 |     1,7 |    10,9 |
| GE       | Warmwasser an Fernwärme |      50 |              2 |              4,0 |           5,4 |      0,7 |     1,1 |    13,5 |
| ZG       | Anlage bis 10 m         |      44 |             28 |             63,6 |           8,8 |      7,3 |    48,9 |    76,2 |
| ZG       | Anlage 10 bis 20 m      |      65 |             40 |             61,5 |           8,8 |      7,0 |    49,4 |    72,4 |
| ZG       | nur Photovoltaik        |     279 |             48 |             17,2 |           8,8 |      2,0 |    13,2 |    22,1 |
| ZG       | Warmwasser-Wärmepumpe   |      14 |              1 |              7,1 |           8,8 |      0,8 |     1,3 |    31,5 |

## Der Status der Anlage entscheidet

Als Beleg zählt eine Anlage nur, wenn ihr Status eine laufende oder entstehende Wärmepumpe
belegt (Merkmal `belegt_anlage` in `sql/test5.sql`). Der Grund ist Genf: Das dortige
Bohrungsregister führt für fast alle Bohrungen den Status "Inconnu" oder "Exploitable".
"Exploitable" stuft die Ressource ein und sagt, dass dort gebohrt werden könnte; eine
laufende Anlage belegt dieser Status nicht. Ohne die Einschränkung treffen in Genf 2 von
30 Anlagenfällen zu, und der Unterschied zu Zug sähe aus wie ein Unterschied zwischen den
Kantonen.

Die Zuger Anlagen sind gemischt. Von den 51 Fällen mit genau einem Gebäude im Umkreis
(Abschnitt "Übertragbarkeit auf Zürich") tragen 24 den Status "in Betrieb" (22 davon
treffen zu) und 27 den Status "unbekannt" (18 treffen zu). "Unbekannt" heisst in Zug, dass
der Kanton den Betriebszustand nicht führt; diese Anlagen zählen deshalb als Beleg.

Mit dem Statusfilter verliert Genf fast alle prüfbaren Anlagenfälle. Der Anlagenbeleg
lässt sich dort nicht messen.

Anlagen je Status (Zeilen mit mehr als 500 Anlagen oder mit Anlagen, die nicht als Beleg
zählen):

| Kanton   | Status                             |   Anlagen |   zählt als Beleg |
|:---------|:-----------------------------------|----------:|------------------:|
| AI       | Bohrung ausgeführt                 |      2419 |              2419 |
| BE       | Ausgeführt                         |     10423 |             10423 |
| BE       | Anlage ausser Betrieb              |      2101 |                 0 |
| BE       | In Ausführung                      |       968 |               968 |
| BE       | Abgelaufen                         |       780 |                 0 |
| BE       | Bewilligung vollständig            |       365 |                 0 |
| BE       | Bewilligung unvollständig          |        24 |                 0 |
| BL       | Bohrung ausgeführt                 |      2629 |              2629 |
| GE       | Inconnu                            |      2800 |                 0 |
| GE       | Exploitable                        |       720 |                 0 |
| GE       | Cimenté / Rebouché                 |         2 |                 0 |
| GE       | Défectueux                         |         1 |                 0 |
| LU       | Bohrung realisiert                 |     14717 |             14717 |
| LU       | bewilligt oder geplant             |      7066 |                 0 |
| SG       | bestehend, vorhanden               |     26073 |             26073 |
| SG       | geplant                            |      2004 |                 0 |
| SG       | (kein Statusfeld)                  |      1000 |              1000 |
| SG       | aufgehoben, zugeschüttet, versiegt |        56 |                 0 |
| SG       | geplant, nicht umgesetzt           |         3 |                 0 |
| SH       | Erdsonde                           |      1144 |              1144 |
| SO       | WP mit Erdwärmesonde               |      8805 |              8805 |
| SZ       | (kein Statusfeld)                  |      1675 |              1675 |
| TG       | ausgebaut, in Nutzung              |      4528 |              4528 |
| TG       | verfüllt                           |         2 |                 0 |
| UR       | Konzession erteilt                 |       847 |                 0 |
| ZG       | unbekannt                          |      1474 |              1474 |
| ZG       | in Betrieb                         |       918 |               918 |
| ZG       | nicht erstellt                     |       376 |                 0 |
| ZG       | ausser Betrieb                     |        23 |                 0 |
| ZH       | (kein Statusfeld)                  |     39470 |             39470 |

Zürich und Schwyz führen kein Statusfeld, in St. Gallen fehlt es bei einem Teil der Anlagen.
Dort gelten alle veröffentlichten Anlagen als bestehend. Diese Annahme lässt sich nicht
prüfen. In Schaffhausen und Solothurn nennt das Feld die Anlagenart ("Erdsonde",
"WP mit Erdwärmesonde") und keinen Betriebszustand; auch diese Anlagen zählen als Beleg.

## Die Verdachtsliste

Die Tabelle oben misst Belegarten. Die Verdachtsliste ist eine Auswahl aus mehreren
Belegarten, gegliedert nach Stufen. Deshalb dieselbe Messung für die Fälle mit Listenstufe:

| Kanton   |   Fälle |   davon falsch |   Trefferquote % |   von % |   bis % |
|:---------|--------:|---------------:|-----------------:|--------:|--------:|
| ZG       |      79 |             64 |             81,0 |    71,0 |    88,1 |
| GE       |       1 |              0 |              0,0 |     0,0 |    79,3 |

Je Stufe:

| Kanton   | Stufe              |   Fälle |   davon falsch |   Trefferquote % |   Grundrate % |   Faktor |   von % |   bis % |
|:---------|:-------------------|--------:|---------------:|-----------------:|--------------:|---------:|--------:|--------:|
| GE       | Reihenfolge belegt |       1 |              0 |              0,0 |           5,4 |      0,0 |     0,0 |    79,3 |
| ZG       | Reihenfolge belegt |      78 |             63 |             80,8 |           8,8 |      9,2 |    70,7 |    88,0 |
| ZG       | Eintrag jung       |       1 |              1 |            100,0 |           8,8 |     11,4 |    20,7 |   100,0 |

Gemessen wird auf `v_gold_score`, also vor dem Gegenbeleg-Filter der Liste: Der Filter
benutzt dieselben Kataster, aus denen die Labels stammen, die Messung wäre sonst zirkulär.

Die Stufe "Beleg vor Eintrag" steht nicht auf der Liste und fehlt deshalb in der Tabelle.
Liegt der Beleg vor dem Registereintrag, trifft der Verdacht in Zug in 4 von
30 prüfbaren Fällen zu, also nahe der Grundrate. Zusammen mit diesen Fällen sind in Zug
109 Fälle mit Anlagenbeleg prüfbar.

Am stärksten trennt damit die Reihenfolge von Beleg und Registereintrag, stärker als die
Belegart. Ein Beleg sagt, dass am Gebäude etwas an der Heizung geschehen ist. Ob das im
Register steht, hängt daran, ob der Eintrag danach noch bearbeitet wurde.

Für Genf ist die Tabelle keine Messung: Nach dem Statusfilter bleibt dort kaum ein
prüfbarer Fall mit Listenstufe (Anzahl: 1).

### Überleitung der Zuger Fallzahlen

Die Berichte nennen für Zug mehrere Fallzahlen. Sie zählen verschiedene Mengen:

| Zuger Fälle | Anzahl |
|---|---:|
| mit Listenstufe, Öl- und Gaseinträge (`v_gold_score`) | 144 |
| davon Gaseinträge, am Tankkataster nicht prüfbar | 22 |
| davon Öleinträge | 122 |
| Öleinträge ohne Tank im Kataster (ungeklärt) | 43 |
| Öleinträge mit Tank im Kataster (prüfbar) | 79 |
| davon Eintrag falsch (Tank ausser Betrieb) | 64 |
| davon Eintrag stimmt (Tank in Betrieb) | 15 |
| auf der Verdachtsliste (`v_gold_liste`: mit Listenstufe, ohne Tank in Betrieb) | 129 |

## Übertragbarkeit auf Zürich

Zug ordnet seine Anlagen über die amtliche EGID oder die Adresse zu; der Kanton nennt also
selbst das Gebäude zur Sonde. Zürich liefert das nicht: 38'553 Bohrungen ohne EGID, ohne
Adresse, ohne Status. Dort bleibt nur der 20-Meter-Umkreis.

Deshalb dieselbe Zuger Messung noch einmal, ausschliesslich über den Umkreis zugeordnet,
also mit dem Verfahren, das für Zürich gilt:

| Eindeutigkeit        | Distanz     |   Fälle |   davon falsch |   Trefferquote % |   von % |   bis % |
|:---------------------|:------------|--------:|---------------:|-----------------:|--------:|--------:|
| 1 Gebäude im Umkreis | bis 10 m    |      16 |             13 |             81,3 |    57,0 |    93,4 |
| 1 Gebäude im Umkreis | 10 bis 20 m |      35 |             27 |             77,1 |    61,0 |    87,9 |
| 2 Gebäude im Umkreis | bis 10 m    |      17 |             12 |             70,6 |    46,9 |    86,7 |
| 2 Gebäude im Umkreis | 10 bis 20 m |      94 |             18 |             19,1 |    12,5 |    28,3 |
| 3 und mehr           | bis 10 m    |      17 |              2 |             11,8 |     3,3 |    34,3 |
| 3 und mehr           | 10 bis 20 m |      77 |             12 |             15,6 |     9,1 |    25,3 |

**Die Eindeutigkeit des Umkreises entscheidet.** Liegt genau ein Gebäude im
20-Meter-Umkreis der Anlage, trifft der Verdacht in rund vier von fünf Fällen zu, auch ohne
amtliche Zuordnung. Liegen drei oder mehr Gebäude darin, fällt die Quote in die Nähe der
Grundrate.

Die Zuordnung übernimmt eine Zürcher Anlage deshalb nur, wenn genau ein Gebäude in ihrem
Umkreis liegt (`sql/zuordnung_anlagen.sql`).

## Woraus die Listen bestehen

Zusammensetzung der Verdachtsliste je Kanton nach Belegart (Zeilen ab fünf Fällen):

| Kanton   | Belegart                   |   Fälle |   davon Reihenfolge belegt |   Gemeinden |
|:---------|:---------------------------|--------:|---------------------------:|------------:|
| AI       | Anlage 10 bis 20 m         |       7 |                          7 |           2 |
| BE       | Anlage bis 10 m            |     330 |                        328 |         125 |
| BE       | Anlage 10 bis 20 m         |     268 |                        266 |         112 |
| BE       | Baugesuch                  |      57 |                         57 |          31 |
| BL       | Anlage 10 bis 20 m         |      25 |                         25 |          14 |
| BL       | Anlage bis 10 m            |      11 |                         11 |          10 |
| SG       | Anlage 10 bis 20 m         |      23 |                         23 |          17 |
| SG       | Anlage bis 10 m            |      19 |                         19 |          14 |
| SH       | Anlage 10 bis 20 m         |      17 |                          0 |           8 |
| SH       | Anlage bis 10 m            |      12 |                          0 |           9 |
| SH       | Baugesuch                  |       8 |                          8 |           6 |
| SH       | Register widerspricht sich |       6 |                          0 |           3 |
| SO       | Anlage 10 bis 20 m         |     129 |                        128 |          54 |
| SO       | Anlage bis 10 m            |      84 |                         82 |          51 |
| SZ       | Anlage bis 10 m            |      36 |                         27 |          13 |
| SZ       | Anlage 10 bis 20 m         |      17 |                         16 |          11 |
| TG       | Anlage 10 bis 20 m         |      44 |                         44 |          32 |
| TG       | Anlage bis 10 m            |      35 |                         35 |          21 |
| VS       | Baugesuch                  |      11 |                         11 |           9 |
| ZG       | Anlage 10 bis 20 m         |      82 |                         82 |           9 |
| ZG       | Anlage bis 10 m            |      47 |                         46 |           7 |
| ZH       | Anlage 10 bis 20 m         |    1006 |                          0 |         124 |
| ZH       | Anlage bis 10 m            |     999 |                          0 |         125 |
| ZH       | Baugesuch                  |     138 |                        138 |          37 |

## Wer aus der Messung fällt

Gemessen werden kann nur, wozu der Tankkataster etwas sagt. Kennt er zu einem Gebäude
keinen Tank, gilt der Fall als ungeklärt und fällt heraus. Das ist nicht gleichmässig
verteilt (Zuger Wohngebäude mit Öleintrag):

| Gruppe           |   Gebäude |   ungeklärt |   Anteil % |
|:-----------------|----------:|------------:|-----------:|
| sonstiger Beleg  |        69 |          28 |       40,6 |
| mit Listenstufe  |       122 |          43 |       35,2 |
| nur Photovoltaik |       422 |         138 |       32,7 |
| kein Beleg       |      5335 |        1309 |       24,5 |

Gebäude mit einem Beleg fallen häufiger aus der Messung als Gebäude ohne, rund ein Drittel
gegenüber einem Viertel. Zwei Lesarten sind möglich, und mit diesen Daten lässt sich keine
ausschliessen:

- **Zugunsten der Liste:** Wer von Öl auf eine Wärmepumpe wechselt, lässt den Tank
  ausbauen. Gebäude ohne Tankeintrag wären dann überdurchschnittlich oft die gesuchten
  Fälle, und die gemessene Quote wäre zu tief.
- **Zuungunsten der Liste:** Der Kataster führt stillgelegte Tanks weiter
  (388 Gebäude mit stillgelegtem Tank). "Kein Tank" heisst dann eher
  "nie erfasst", und die herausgefallenen Fälle sind eine Mischung wie alle anderen.

Dazu kommt eine zweite Lücke derselben Art: 713 der 3'423 Fälle der
Verdachtsliste sind Gaseinträge, in Zug 22 von 144 Fällen mit Listenstufe.
Ein Öltankkataster sagt über Gas nichts; auch diese Fälle sind ungeprüft.

Ein erheblicher Teil der Fälle mit Listenstufe ist in Zug also nicht prüfbar, und dieser
Anteil ist höher als bei Gebäuden ohne Beleg. Die gemessene Quote gilt nur zusammen mit
dieser Einschränkung.

## Was ungemessen bleibt

Das Baugesuch nennt den neuen Energieträger im Klartext und ist datiert. Für diesen Beleg
gibt es keine Messung: In den beiden Labelkantonen Genf und Zug kommt kein prüfbarer Fall
mit Baugesuch-Beleg vor. Die 223 Fälle der Verdachtsliste mit
Baugesuch-Beleg beruhen damit auf einer Annahme.
