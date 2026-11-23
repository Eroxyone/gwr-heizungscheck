# Zuordnung von Anlagen zu Gebäuden: Prüfung an den amtlichen EGID des Kantons Zug

Registerstand 13.09.2026. Gemessen wird, wie oft der Umkreis einer Erdwärmesondenanlage das Gebäude enthält, das der Kanton Zug der Anlage amtlich zuordnet. Der Kanton führt an 805 Anlagen die EGID mit; das ist die einzige unabhängige Referenz für die räumliche Zuordnung in dieser Studie.

| Radius | Anlagen | mit Gebäude im Umkreis | amtliche EGID dabei | Recall | nächstes Gebäude richtig | Gebäude je Anlage |
|---:|---:|---:|---:|---:|---:|---:|
| 10 m | 805 | 361 | 261 | 32,4 % | 30,8 % | 0,50 |
| 15 m | 805 | 637 | 503 | 62,5 % | 56,3 % | 1,20 |
| 20 m | 805 | 730 | 594 | 73,8 % | 64,7 % | 1,87 |
| 30 m | 805 | 773 | 633 | 78,6 % | 67,0 % | 3,77 |
| 50 m | 805 | 795 | 646 | 80,2 % | 67,2 % | 9,48 |

## Was daraus folgt

Beim gewählten Radius von 20 m liegt die amtliche EGID in 73,8 % der Fälle unter den Gebäuden im Umkreis, bei im Schnitt 1,87 Gebäuden je Anlage. Das nächstgelegene Gebäude allein trifft in 64,7 % der Fälle. Die Anlage liegt also oft näher bei einem Nachbargebäude als bei dem Gebäude, das sie heizt.

Die Pipeline verlässt sich deshalb nicht auf das nächstgelegene Gebäude. Sie übernimmt eine Zuordnung nur, wenn sie eindeutig ist (`sql/zuordnung_anlagen.sql`): zuerst über die amtliche EGID, wenn der Kanton genau eine nennt, sonst über die Adresse der Anlage, wenn sie auf genau ein Gebäude passt, und sonst über den Umkreis, wenn genau ein Gebäude innerhalb von 20 m liegt. Liegen mehrere Gebäude im Umkreis, bleibt die Anlage ohne Zuordnung und führt zu keinem Verdachtsfall.

Auch bei 50 m Radius steigt der Recall nur auf 80,2 %. Bei rund 20 % der Anlagen liegt das amtlich zugeordnete Gebäude also weiter entfernt als 50 m. Ein grösserer Radius löst das nicht, er nimmt vor allem Nachbargebäude dazu: 1,87 Gebäude je Anlage bei 20 m, 9,48 bei 50 m. **Die Zuordnung über Koordinaten erreicht höchstens etwa vier Fünftel der Anlagen.** Mehr braucht Parzellengeometrie oder eine Adresse.

Für die Verdachtsliste heisst das: Bei rund einem Viertel der Anlagen liegt das richtige Gebäude nicht im 20-m-Umkreis, und Anlagen mit mehreren Gebäuden im Umkreis werden nicht zugeordnet. Die ausgewiesenen Fallzahlen sind damit eher Unter- als Obergrenzen.

## Grenzen

Zug ist ein dicht bebauter, flacher Kanton. In Streusiedlungsgebieten dürfte derselbe Radius besser trennen, in Stadtzentren schlechter. Die Zahlen sind eine Grössenordnung. Die amtliche EGID des Kantons Zug ist die beste verfügbare Referenz, aber selbst nicht fehlerfrei.
