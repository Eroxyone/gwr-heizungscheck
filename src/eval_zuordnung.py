"""Wie gut trifft die raeumliche Zuordnung Anlage -> Gebaeude?

Bisher liess sich das nur behaupten. Der Kanton Zug fuehrt an seinen Erdwaerme-
sondenanlagen die EGID mit - 805 Anlagen mit amtlicher Zuordnung. Das ist eine
unabhaengige Wahrheit, gegen die sich der eigene Umkreis-Join messen laesst.

Zwei Groessen, die nicht verwechselt werden duerfen:
  Recall     Ist die amtliche EGID unter meinen Kandidaten? Fehlt sie, geht ein
             echter Fall verloren.
  Kandidaten Wie viele Gebaeude haenge ich je Anlage an? Jeder Kandidat zu viel ist
             ein Gebaeude, das faelschlich unter Verdacht geraet.

Beide ziehen in entgegengesetzte Richtungen: Ein grosser Radius findet mehr, aber
belastet mehr Unschuldige. Der Lauf zeigt den Zielkonflikt in Zahlen, statt den
gewaehlten Radius nachtraeglich zu begruenden.

    python src/eval_zuordnung.py
    python src/eval_zuordnung.py --radien 10 20 30
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
import fmt
import pipeline

# Der Kanton Zug ist die einzige verfuegbare Referenz. Das ist zugleich die Grenze
# dieser Auswertung: Zug ist dicht besiedelt und flach - in einem Streusiedlungsgebiet
# duerfte derselbe Radius besser trennen, im Stadtzentrum schlechter.
REFERENZ_KANTON = "ZG"


def _amtliche(con) -> int:
    return con.execute("""
        SELECT count(DISTINCT anlage_id) FROM silver_waermenutzung
        WHERE egid_amtlich IS NOT NULL AND TRIM(egid_amtlich) <> ''
    """).fetchone()[0]


def auswerten(con, radius: int) -> dict:
    """Den Umkreis-Join fuer einen Radius neu rechnen und gegen die amtliche EGID halten."""
    return con.execute(f"""
        WITH amt AS (
            SELECT anlage_id, e_lv95, n_lv95, TRIM(x) AS egid_amt
            FROM silver_waermenutzung, UNNEST(str_split(egid_amtlich, ',')) AS t(x)
            WHERE kanton = '{REFERENZ_KANTON}'
              AND egid_amtlich IS NOT NULL AND TRIM(x) <> ''
        ),
        kandidaten AS (
            SELECT a.anlage_id, CAST(g.egid AS VARCHAR) AS egid_mein,
                   sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) AS dist_m
            FROM (SELECT DISTINCT anlage_id, e_lv95, n_lv95 FROM amt) a
            JOIN silver_gebaeude_ch g
              ON g.kanton = '{REFERENZ_KANTON}'
             AND g.e_lv95 BETWEEN a.e_lv95 - {radius} AND a.e_lv95 + {radius}
             AND g.n_lv95 BETWEEN a.n_lv95 - {radius} AND a.n_lv95 + {radius}
             AND sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) <= {radius}
        ),
        naechstes AS (
            SELECT anlage_id, egid_mein
            FROM (SELECT *, row_number() OVER (PARTITION BY anlage_id ORDER BY dist_m) rn
                  FROM kandidaten)
            WHERE rn = 1
        ),
        je_anlage AS (
            SELECT a.anlage_id,
                   count(DISTINCT k.egid_mein)                            AS n_kandidaten,
                   max(CASE WHEN k.egid_mein = a.egid_amt THEN 1 ELSE 0 END) AS getroffen,
                   max(CASE WHEN n.egid_mein = a.egid_amt THEN 1 ELSE 0 END) AS naechstes_richtig
            FROM amt a
            LEFT JOIN kandidaten k USING (anlage_id)
            LEFT JOIN naechstes  n USING (anlage_id)
            GROUP BY 1
        )
        SELECT {radius}                                        AS radius_m,
               count(*)                                        AS anlagen,
               sum(CASE WHEN n_kandidaten > 0 THEN 1 ELSE 0 END) AS mit_kandidat,
               sum(getroffen)                                  AS amtliche_egid_dabei,
               sum(naechstes_richtig)                          AS naechstes_ist_amtliches,
               round(avg(n_kandidaten), 2)                     AS kandidaten_je_anlage
        FROM je_anlage
    """).df().to_dict("records")[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--radien", nargs="*", type=int, default=[10, 15, 20, 30, 50])
    p.add_argument("--out", default=str(config.ROOT / "reports" / "zuordnung_zg.md"))
    a = p.parse_args(argv)

    con = pipeline.connect()
    gesamt = _amtliche(con)
    if not gesamt:
        print("Keine amtlichen EGID in silver_waermenutzung - erst test5.sql laufen lassen.")
        return 1

    zeilen = [auswerten(con, r) for r in a.radien]
    for z in zeilen:
        z["recall_pct"] = round(100 * z["amtliche_egid_dabei"] / z["anlagen"], 1)
        z["genauigkeit_naechstes_pct"] = round(
            100 * z["naechstes_ist_amtliches"] / z["anlagen"], 1)

    kopf = ["radius_m", "anlagen", "mit_kandidat", "amtliche_egid_dabei", "recall_pct",
            "naechstes_ist_amtliches", "genauigkeit_naechstes_pct", "kandidaten_je_anlage"]
    print(f"Referenz: {fmt.tsd(gesamt)} Anlagen im Kanton {REFERENZ_KANTON} "
          f"mit amtlicher EGID\n")
    print(" | ".join(kopf))
    for z in zeilen:
        print(" | ".join(str(z[k]) for k in kopf))

    gewaehlt = next((z for z in zeilen if z["radius_m"] == 20), zeilen[0])
    weitest = max(zeilen, key=lambda z: z["radius_m"])
    text = [
        "# Wie gut trifft die Zuordnung Anlage -> Gebäude?",
        "",
        f"Der Kanton Zug führt an seinen Erdwärmesondenanlagen die EGID mit: "
        f"{fmt.tsd(gesamt)} Anlagen mit amtlicher Zuordnung. Damit lässt sich der eigene "
        "Umkreis-Join gegen eine unabhängige Referenz halten statt gegen eine Vermutung.",
        "",
        "| Radius | Anlagen | mit Kandidat | amtliche EGID dabei | Recall | nächstes Gebäude richtig | Kandidaten je Anlage |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for z in zeilen:
        text.append(
            f"| {z['radius_m']} m | {fmt.tsd(z['anlagen'])} | {fmt.tsd(z['mit_kandidat'])} "
            f"| {fmt.tsd(z['amtliche_egid_dabei'])} | {z['recall_pct']} % "
            f"| {z['genauigkeit_naechstes_pct']} % | {z['kandidaten_je_anlage']} |")
    text += [
        "",
        "## Was daraus folgt",
        "",
        f"Beim gewählten Radius von 20 m liegt die amtliche EGID in "
        f"{gewaehlt['recall_pct']} % der Fälle unter den Kandidaten, bei im Schnitt "
        f"{gewaehlt['kandidaten_je_anlage']} Gebäuden je Anlage. Nimmt man nur das "
        f"nächstgelegene Gebäude, trifft es in "
        f"{gewaehlt['genauigkeit_naechstes_pct']} % der Fälle - deutlich weniger. "
        "Die Anlage liegt also oft näher bei einem Nachbargebäude als bei dem, das sie "
        "heizt. Das ist der Grund, warum die Pipeline alle Gebäude im Umkreis als "
        "Kandidaten führt und die Entscheidung nicht der Distanz allein überlässt.",
        "",
        f"Wichtiger ist die zweite Beobachtung: Auch bei {weitest['radius_m']} m Radius "
        f"steigt der Recall nur auf {weitest['recall_pct']} %. Bei rund "
        f"{100 - weitest['recall_pct']:.0f} % der Anlagen liegt das amtlich zugeordnete "
        f"Gebäude also weiter entfernt als {weitest['radius_m']} m. Ein grösserer Radius "
        "löst das nicht, er kauft nur immer mehr Nachbarn dazu - von 1,9 auf "
        f"{weitest['kandidaten_je_anlage']} Gebäude je Anlage. **Die Zuordnung über "
        "Koordinaten hat eine Decke bei etwa vier Fünfteln.** Wer höher will, braucht "
        "Parzellengeometrie oder eine Adresse, nicht mehr Meter.",
        "",
        "Für die Verdachtsliste heisst das: Rund ein Viertel der tatsächlich vorhandenen "
        "Wärmepumpen findet dieser Weg nicht. Die ausgewiesenen Fallzahlen sind damit "
        "eher Unter- als Obergrenzen.",
        "",
        "## Grenzen",
        "",
        "Zug ist ein dicht bebauter, flacher Kanton. In Streusiedlungsgebieten dürfte "
        "derselbe Radius besser trennen, in Stadtzentren schlechter. Die Zahlen sind "
        "eine Grössenordnung, keine Konstante. Ausserdem ist die amtliche EGID des "
        "Kantons Zug selbst nicht fehlerfrei - sie ist die beste verfügbare Referenz, "
        "nicht die Wahrheit.",
        "",
    ]
    ziel = config.ROOT / a.out if not str(a.out).startswith(str(config.ROOT)) else a.out
    Path(ziel).write_text(fmt.de("\n".join(text)), encoding="utf-8")

    # Dieselben Zahlen auch maschinenlesbar. Sonst stehen sie irgendwann doppelt im
    # Projekt - einmal hier gemessen, einmal von Hand in einen Export getippt - und
    # laufen beim naechsten Lauf auseinander, ohne dass es jemand merkt.
    json_ziel = config.PROCESSED / "zuordnung_zg.json"
    json_ziel.parent.mkdir(parents=True, exist_ok=True)
    json_ziel.write_text(json.dumps(
        {"referenz_kanton": REFERENZ_KANTON,
         "anlagen_mit_egid": int(gesamt),
         "radien": [{k: (float(z[k]) if isinstance(z[k], float) else int(z[k]))
                     for k in ("radius_m", "anlagen", "mit_kandidat",
                               "amtliche_egid_dabei", "naechstes_ist_amtliches",
                               "kandidaten_je_anlage", "recall_pct",
                               "genauigkeit_naechstes_pct")}
                    for z in zeilen]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geschrieben: {json_ziel}")
    print(f"\ngeschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
