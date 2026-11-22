# Wie gut trifft die Zuordnung Anlage -> Gebäude?

Der Kanton Zug führt an seinen Erdwärmesondenanlagen die EGID mit: 805 Anlagen mit amtlicher Zuordnung. Damit lässt sich der eigene Umkreis-Join gegen eine unabhängige Referenz halten statt gegen eine Vermutung.

| Radius | Anlagen | mit Kandidat | amtliche EGID dabei | Recall | nächstes Gebäude richtig | Kandidaten je Anlage |
|---:|---:|---:|---:|---:|---:|---:|
| 10 m | 805 | 361 | 261 | 32,4 % | 30,8 % | 0,5 |
| 15 m | 805 | 637 | 503 | 62,5 % | 56,3 % | 1,2 |
| 20 m | 805 | 730 | 594 | 73,8 % | 64,7 % | 1,87 |
| 30 m | 805 | 773 | 633 | 78,6 % | 67,0 % | 3,77 |
| 50 m | 805 | 795 | 646 | 80,2 % | 67,2 % | 9,48 |

## Was daraus folgt

Beim gewählten Radius von 20 m liegt die amtliche EGID in 73,8 % der Fälle unter den Kandidaten, bei im Schnitt 1,87 Gebäuden je Anlage. Nimmt man nur das nächstgelegene Gebäude, trifft es in 64,7 % der Fälle - deutlich weniger. Die Anlage liegt also oft näher bei einem Nachbargebäude als bei dem, das sie heizt. Das ist der Grund, warum die Pipeline alle Gebäude im Umkreis als Kandidaten führt und die Entscheidung nicht der Distanz allein überlässt.

Wichtiger ist die zweite Beobachtung: Auch bei 50 m Radius steigt der Recall nur auf 80,2 %. Bei rund 20 % der Anlagen liegt das amtlich zugeordnete Gebäude also weiter entfernt als 50 m. Ein grösserer Radius löst das nicht, er kauft nur immer mehr Nachbarn dazu - von 1,9 auf 9,48 Gebäude je Anlage. **Die Zuordnung über Koordinaten hat eine Decke bei etwa vier Fünfteln.** Wer höher will, braucht Parzellengeometrie oder eine Adresse, nicht mehr Meter.

Für die Verdachtsliste heisst das: Rund ein Viertel der tatsächlich vorhandenen Wärmepumpen findet dieser Weg nicht. Die ausgewiesenen Fallzahlen sind damit eher Unter- als Obergrenzen.

## Grenzen

Zug ist ein dicht bebauter, flacher Kanton. In Streusiedlungsgebieten dürfte derselbe Radius besser trennen, in Stadtzentren schlechter. Die Zahlen sind eine Grössenordnung, keine Konstante. Ausserdem ist die amtliche EGID des Kantons Zug selbst nicht fehlerfrei - sie ist die beste verfügbare Referenz, nicht die Wahrheit.
