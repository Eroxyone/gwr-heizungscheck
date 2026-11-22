# Was ein Beleg wert ist

Stand 14.09.2026. Gemessen an zwei kantonalen Gegenquellen:
dem Genfer Waermeerzeuger-Layer (61'895 Anlagen mit EGID, darunter 9'615 Waermepumpen
und 3'181 Fernwaerme-Uebergabestationen) und dem Zuger Tankkataster (nur Oel).

## Warum dieser Bericht die Top-K-Kurve ersetzt

Der frueher berichtete Wert "die obersten 20 Raenge treffen zu 70 Prozent" war ein
Artefakt. Der Score kennt nur wenige mögliche Summen; in Genf hatten hunderte Faelle
exakt 45 Punkte, und welche davon auf den Raengen 13 bis 20 landeten, entschied die
Sortierung nach EGID. Niedrige EGID heisst in Genf Innenstadt, Innenstadt heisst
Fernwaerme. Die Zahl mass den Tiebreak, nicht das Verfahren.

Je Belegart gibt es keine Rangfolge und damit keinen Tiebreak. Die Quoten unten sind
reproduzierbar.

## Trefferquote je Belegart

"Falsch" heisst: Die Gegenquelle zeigt einen anderen Waermeerzeuger als das Register.
"Faktor" ist der Abstand zur Grundrate desselben Kantons - das ist die Zahl, die zaehlt.
Der Vertrauensbereich ist Wilson, 95 Prozent.

| kanton   | belegart                |    n |   falsch |   praezision |   grundrate |   faktor |   von_% |   bis_% |
|:---------|:------------------------|-----:|---------:|-------------:|------------:|---------:|--------:|--------:|
| GE       | nur Photovoltaik        | 3251 |      445 |         13,7 |         5,4 |      2,5 |    12,5 |    14,9 |
| GE       | Warmwasser-Wärmepumpe   |   90 |        4 |          4,4 |         5,4 |      0,8 |     1,7 |    10,9 |
| GE       | Warmwasser an Fernwärme |   50 |        2 |          4,0 |         5,4 |      0,7 |     1,1 |    13,5 |
| ZG       | Anlage bis 10 m         |   44 |       28 |         63,6 |         8,8 |      7,3 |    48,9 |    76,2 |
| ZG       | Anlage 10 bis 20 m      |   65 |       40 |         61,5 |         8,8 |      7,0 |    49,4 |    72,4 |
| ZG       | nur Photovoltaik        |  279 |       48 |         17,2 |         8,8 |      2,0 |    13,2 |    22,1 |
| ZG       | Warmwasser-Wärmepumpe   |   14 |        1 |          7,1 |         8,8 |      0,8 |     1,3 |    31,5 |

## Der Status der Anlage entscheidet, nicht der Kanton

Eine erste Fassung mass in Genf 2 Treffer auf 30 Faelle und in Zug 40 auf 51 - und
haette beinahe zum Schluss gefuehrt, das Verfahren sei nicht uebertragbar. Der
Unterschied lag woanders: Alle 30 Genfer Faelle hingen an Bohrungen mit Status
"Exploitable" oder "Inconnu". Das ist eine Einstufung der Ressource, keine laufende
Anlage.

Die Zuger Gegenprobe ist dagegen gemischt, und das gehoert genannt: 24 der 51 Faelle
tragen "in Betrieb" (22 davon treffen zu), 27 tragen "unbekannt" (18 treffen zu). Eine
frueher hier stehende Behauptung, alle 51 seien betriebsbestaetigt, war falsch. Der Statusunterschied erklaert den Genfer Ausfall
trotzdem: "unbekannt" heisst in Zug, dass der Kanton den Betriebszustand nicht fuehrt,
waehrend "Exploitable" in Genf ausdruecklich sagt, dass hier nur gebohrt werden
KOENNTE.

Seitdem zaehlt eine Anlage nur noch als Beleg, wenn ihr Status eine laufende oder
entstehende Waermepumpe belegt. Genf verliert damit fast seinen ganzen Bestand an
pruefbaren Anlagenfaellen - und damit die Faehigkeit, diesen Beleg zu messen. Das ist
kein Verlust an Substanz, sondern die Korrektur einer Scheinmessung.

| kanton   | status                             |   anlagen |   zaehlt_als_beleg |
|:---------|:-----------------------------------|----------:|-------------------:|
| AI       | Bohrung ausgefuehrt                |      2419 |               2419 |
| BE       | Ausgeführt                         |     10423 |              10423 |
| BE       | Anlage ausser Betrieb              |      2101 |                  0 |
| BE       | In Ausführung                      |       968 |                968 |
| BE       | Abgelaufen                         |       780 |                  0 |
| BE       | Bewilligung vollständig            |       365 |                  0 |
| BE       | Bewilligung unvollständig          |        24 |                  0 |
| BL       | Bohrung ausgefuehrt                |      2629 |               2629 |
| GE       | Inconnu                            |      2800 |                  0 |
| GE       | Exploitable                        |       720 |                  0 |
| GE       | Cimenté / Rebouché                 |         2 |                  0 |
| GE       | Défectueux                         |         1 |                  0 |
| LU       | Bohrung realisiert                 |     14717 |              14717 |
| LU       | bewilligt oder geplant             |      7066 |                  0 |
| SG       | bestehend, vorhanden               |     26073 |              26073 |
| SG       | geplant                            |      2004 |                  0 |
| SG       | (kein Statusfeld)                  |      1000 |               1000 |
| SG       | aufgehoben, zugeschüttet, versiegt |        56 |                  0 |
| SG       | geplant, nicht umgesetzt           |         3 |                  0 |
| SH       | Erdsonde                           |      1144 |               1144 |
| SO       | WP mit Erdwärmesonde               |      8805 |               8805 |
| SZ       | (kein Statusfeld)                  |      1675 |               1675 |
| TG       | ausgebaut, in Nutzung              |      4528 |               4528 |
| TG       | verfüllt                           |         2 |                  0 |
| UR       | Konzession erteilt                 |       847 |                  0 |
| ZG       | unbekannt                          |      1474 |               1474 |
| ZG       | in Betrieb                         |       918 |                918 |
| ZG       | nicht erstellt                     |       376 |                  0 |
| ZG       | ausser Betrieb                     |        23 |                  0 |
| ZH       | (kein Statusfeld)                  |     39470 |              39470 |

Zuerich, Schwyz und Zuerichs Nachbarn fuehren gar kein Statusfeld. Dort gelten alle
veroeffentlichten Anlagen als bestehend - eine Annahme, die nicht geprueft werden kann
und offengelegt gehoert.

## Die Verdachtsliste selbst

Die Tabelle oben misst Belegarten. Benutzt wird aber eine Liste, und die ist eine
Auswahl aus mehreren Belegarten in einer bestimmten Reihenfolge. Deshalb dasselbe noch
einmal fuer genau das, was in der Mappe steht:

| kanton   |   n |   falsch |   praezision |   von_% |   bis_% |
|:---------|----:|---------:|-------------:|--------:|--------:|
| ZG       |  79 |       64 |           81 |    71,0 |    88,1 |
| GE       |   1 |        0 |            0 |     0,0 |    79,3 |

Und je Stufe, so wie sie in der Mappe benannt sind:

| kanton   | konfidenz          |   n |   falsch |   praezision |   grundrate |   faktor |   von_% |   bis_% |
|:---------|:-------------------|----:|---------:|-------------:|------------:|---------:|--------:|--------:|
| GE       | reihenfolge belegt |   1 |        0 |          0,0 |         5,4 |      0,0 |     0,0 |    79,3 |
| ZG       | reihenfolge belegt |  78 |       63 |         80,8 |         8,8 |      9,2 |    70,7 |    88,0 |
| ZG       | eintrag jung       |   1 |        1 |        100,0 |         8,8 |     11,4 |    20,7 |   100,0 |

Der eigentliche Befund ist, was NICHT in dieser Tabelle steht. Die Stufe "Beleg aelter
als der Eintrag" fehlt, weil sie seit einer Korrektur gar nicht mehr auf der Liste steht:
Sie traf in Zug in 4 von 30 Faellen zu, also fast auf Grundratenniveau. Uebrig bleibt
eine Liste, deren Stufen sich in der Trefferquote kaum noch unterscheiden - der Filter
hat die Arbeit getan, die vorher die Stufen tun mussten.

Nicht die Belegart trennt am staerksten, sondern die Reihenfolge: Ein Beleg sagt, dass
am Gebaeude etwas an der Heizung geschehen ist. Ob das im Register steht, haengt daran,
ob jemand das Register danach noch angefasst hat.

Genf steht in dieser Tabelle nicht mehr sinnvoll: Nach dem Statusfilter bleiben dort
drei pruefbare Faelle. Das ist keine Messung und wird auch nicht als eine ausgewiesen.

## Was davon in Zuerich uebrig bleibt

Zug ordnet seine Anlagen ueber die amtliche EGID oder die Adresse zu - der Kanton sagt
also selbst, zu welchem Gebaeude die Sonde gehoert. Zuerich liefert das nicht: 38'553
Bohrungen ohne EGID, ohne Adresse, ohne Status. Dort bleibt nur der 20-Meter-Umkreis.

Deshalb dieselbe Zuger Messung noch einmal, aber ausschliesslich ueber den Umkreis -
also mit dem Verfahren, das in Zuerich laufen wuerde:

| eindeutigkeit        | distanz     |   n |   falsch |   praezision |   von_% |   bis_% |
|:---------------------|:------------|----:|---------:|-------------:|--------:|--------:|
| 1 Gebäude im Umkreis | bis 10 m    |  16 |       13 |         81,3 |    57,0 |    93,4 |
| 1 Gebäude im Umkreis | 10 bis 20 m |  35 |       27 |         77,1 |    61,0 |    87,9 |
| 2 Gebäude im Umkreis | bis 10 m    |  17 |       12 |         70,6 |    46,9 |    86,7 |
| 2 Gebäude im Umkreis | 10 bis 20 m |  94 |       18 |         19,1 |    12,5 |    28,3 |
| 3 und mehr           | bis 10 m    |  17 |        2 |         11,8 |     3,3 |    34,3 |
| 3 und mehr           | 10 bis 20 m |  77 |       12 |         15,6 |     9,1 |    25,3 |

Das Ergebnis ist der wichtigste Satz dieses Berichts: **Die Eindeutigkeit des Umkreises
entscheidet.** Liegt genau ein Gebaeude im 20-Meter-Umkreis der Anlage, trifft der
Verdacht in rund vier von fuenf Faellen zu - auch ohne amtliche Zuordnung. Liegen drei
oder mehr Gebaeude darin, faellt die Quote auf das Niveau der Grundrate.

Die Zuercher Liste enthaelt ausschliesslich Faelle mit genau einem Gebaeude im Umkreis.

## Woraus die Listen bestehen

Ein Bauamt darf erwarten, dass wir sagen, worauf SEINE Liste beruht.

| kanton   | belegart                   |   faelle |   stark |   gemeinden |
|:---------|:---------------------------|---------:|--------:|------------:|
| AI       | Anlage 10 bis 20 m         |        7 |       7 |           2 |
| BE       | Anlage bis 10 m            |      330 |     328 |         125 |
| BE       | Anlage 10 bis 20 m         |      268 |     266 |         112 |
| BE       | Baugesuch                  |       57 |      57 |          31 |
| BL       | Anlage 10 bis 20 m         |       25 |      25 |          14 |
| BL       | Anlage bis 10 m            |       11 |      11 |          10 |
| SG       | Anlage 10 bis 20 m         |       23 |      23 |          17 |
| SG       | Anlage bis 10 m            |       19 |      19 |          14 |
| SH       | Anlage 10 bis 20 m         |       17 |       0 |           8 |
| SH       | Anlage bis 10 m            |       12 |       0 |           9 |
| SH       | Baugesuch                  |        8 |       8 |           6 |
| SH       | Register widerspricht sich |        6 |       0 |           3 |
| SO       | Anlage 10 bis 20 m         |      129 |     128 |          54 |
| SO       | Anlage bis 10 m            |       84 |      82 |          51 |
| SZ       | Anlage bis 10 m            |       36 |      27 |          13 |
| SZ       | Anlage 10 bis 20 m         |       17 |      16 |          11 |
| TG       | Anlage 10 bis 20 m         |       44 |      44 |          32 |
| TG       | Anlage bis 10 m            |       35 |      35 |          21 |
| VS       | Baugesuch                  |       11 |      11 |           9 |
| ZG       | Anlage 10 bis 20 m         |       82 |      82 |           9 |
| ZG       | Anlage bis 10 m            |       47 |      46 |           7 |
| ZH       | Anlage 10 bis 20 m         |     1006 |       0 |         124 |
| ZH       | Anlage bis 10 m            |      999 |       0 |         125 |
| ZH       | Baugesuch                  |      138 |     138 |          37 |

## Die unbequeme Zahl: wer aus der Messung faellt

Gemessen werden kann nur, wozu der Tankkataster etwas sagt. Wo er gar keinen Tank kennt,
gilt der Fall als ungeklaert und faellt heraus. Das ist nicht gleichmaessig verteilt:

| gruppe              |    n |   ungeklaert |   anteil |
|:--------------------|-----:|-------------:|---------:|
| sonstiger Beleg     |   69 |           28 |     40,6 |
| auf der Verdachtsliste |  122 |           43 |     35,2 |
| nur Photovoltaik    |  422 |          138 |     32,7 |
| kein Beleg          | 5335 |         1309 |     24,5 |

Gebaeude mit einem Beleg fallen haeufiger aus der Messung als Gebaeude ohne - rund ein
Drittel gegenueber einem Viertel. Beide Lesarten sind moeglich, und keine laesst sich
mit diesen Daten entscheiden:

- **Zugunsten der Liste:** Wer von Oel auf eine Waermepumpe wechselt, laesst den Tank
  ausbauen. Gebaeude ohne jeden Tankeintrag waeren dann ueberdurchschnittlich oft
  genau die gesuchten Faelle - und die gemessene Quote waere zu tief.
- **Zuungunsten der Liste:** Der Kataster fuehrt stillgelegte Tanks ausdruecklich
  weiter (388 Stueck). "Kein Tank" heisst dann eher "nie erfasst", und die
  Herausgefallenen sind eine Mischung wie alle anderen auch.

Dazu kommt eine zweite Luecke derselben Art: Ein Fuenftel der Verdachtsliste sind
Gaseintraege, und ein Oeltankkataster sagt ueber Gas nichts. Auch sie sind ungeprueft.

Festhalten laesst sich nur: Ein erheblicher Teil der Faelle auf der Verdachtsliste ist in
Zug nicht pruefbar, und dieser Anteil ist hoeher als bei Gebaeuden ohne Beleg. Wer die
gemessene Quote zitiert, muss diesen Satz mitzitieren.

## Was ungemessen bleibt

Das Baugesuch ist der Beleg, der den neuen Energietraeger im Klartext nennt und datiert
ist - und der einzige, fuer den es keine einzige Messung gibt. In Genf und Zug ist kein
einziger Baugesuchsfall zugeordnet, weil beide Kantone nicht im Amtsblatt-Abzug mit
verwertbarem Objektbeschrieb liegen. Die 228 schweizweiten Faelle mit Baugesuch-Beleg
stehen also auf einer Annahme, nicht auf einer Messung. Das gehoert zu jeder Liste dazu.
