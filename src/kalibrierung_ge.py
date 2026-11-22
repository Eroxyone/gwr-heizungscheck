"""Den Verdachtsscore an den Genfer Labels kalibrieren statt ihn zu raten.

Der bisherige Score vergibt Punkte nach Augenmass: Baugesuch 50, Sonde 35, Quelle 860
zwoelf, Baujahr vier. Keine dieser Zahlen war je gemessen. Seit groundtruth_ge.sql gibt
es fuer 21'510 Genfer Wohngebaeude ein echtes Label - der Feuerungskataster sagt, was
tatsaechlich im Keller steht. Damit laesst sich nachrechnen, was ein Merkmal wirklich
wert ist.

Zwei Dinge, die dieses Skript bewusst trennt:

  Belege      Was am Gebaeude beobachtet wurde: Baugesuch, Anlage, Photovoltaik,
              Registerwiderspruch. Diese Merkmale sollten uebertragbar sein.
  Metadaten   Wie der Eintrag gepflegt wurde: Quellcode, Alter. Diese Merkmale sind
              stark, aber kantonal sehr verschieden. Genf bezieht 86 % seiner Eintraege
              aus kantonalen Daten, Zuerich hat eine voellig andere Mischung.

Deshalb werden drei Modelle gerechnet und verglichen: nur Belege, nur Metadaten, beides.
Faellt die Guete ohne Metadaten kaum ab, ist das Modell eher uebertragbar.

    python src/kalibrierung_ge.py
    python src/kalibrierung_ge.py --seed 7
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

import config
import pipeline

# Merkmale, getrennt nach Herkunft. Die Trennung ist der Kern dieses Skripts.
BELEG_MERKMALE = ["hat_baugesuch", "sonde_nah", "sonde_fern", "hat_pv",
                  "ws_erzeuger", "ws_fernwaerme", "ws_erdwaerme", "ws_luft"]
META_MERKMALE = ["quelle_860", "quelle_869", "quelle_864", "alt_15", "alt_20",
                 "ohne_datum", "vor_1990", "ist_efh"]


def daten(con) -> pd.DataFrame:
    return con.execute("""
        SELECT l.egid, l.eintrag_falsch::INT AS ziel,
               COALESCE(b.hat_baugesuch, FALSE)::INT                        AS hat_baugesuch,
               (COALESCE(b.hat_sonde, FALSE)
                AND COALESCE(b.sonde_dist_m, 99) <= 10)::INT                AS sonde_nah,
               (COALESCE(b.hat_sonde, FALSE)
                AND COALESCE(b.sonde_dist_m, 99) > 10)::INT                 AS sonde_fern,
               COALESCE(b.hat_pv, FALSE)::INT                               AS hat_pv,
               (b.ws_art = 'erzeuger')::INT                                 AS ws_erzeuger,
               (b.ws_art = 'fernwaerme')::INT                               AS ws_fernwaerme,
               (b.ws_art = 'erdwaerme')::INT                                AS ws_erdwaerme,
               (b.ws_art = 'luft')::INT                                     AS ws_luft,
               (l.quelle_code = '860')::INT                                 AS quelle_860,
               (l.quelle_code = '869')::INT                                 AS quelle_869,
               (l.quelle_code = '864')::INT                                 AS quelle_864,
               (COALESCE(l.alter_jahre, 0) >= 15)::INT                      AS alt_15,
               (COALESCE(l.alter_jahre, 0) >= 20)::INT                      AS alt_20,
               (l.quelle_datum IS NULL)::INT                                AS ohne_datum,
               (COALESCE(l.baujahr, 9999) < 1990)::INT                      AS vor_1990,
               (l.gkat = '1030')::INT                                       AS ist_efh
        FROM v_ge_label_klar l
        LEFT JOIN gold_belege b USING (egid)
    """).df().fillna(0)


def modell(df: pd.DataFrame, merkmale: list[str], seed: int) -> dict:
    x, y = df[merkmale].to_numpy(float), df["ziel"].to_numpy(int)
    x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.3, random_state=seed,
                                              stratify=y)
    # class_weight="balanced", weil nur 6,7 % der Faelle positiv sind. Ohne das lernt
    # das Modell, immer "stimmt" zu sagen, und hat damit fast recht - aber nichts gesagt.
    m = LogisticRegression(max_iter=2000, class_weight="balanced")
    m.fit(x_tr, y_tr)
    p = m.predict_proba(x_te)[:, 1]
    return {
        "merkmale": merkmale,
        "n_train": len(y_tr), "n_test": len(y_te), "positiv_test": int(y_te.sum()),
        "auc": round(float(roc_auc_score(y_te, p)), 3),
        # Average Precision passt bei 6,7 % Positivrate besser als Accuracy: Sie misst,
        # wie gut die obersten Raenge sind - genau das, was eine Pruefliste braucht.
        "ap": round(float(average_precision_score(y_te, p)), 3),
        "basisrate": round(float(y_te.mean()), 4),
        "koeffizienten": {k: round(float(v), 3)
                          for k, v in zip(merkmale, m.coef_[0], strict=True)},
    }


def top_k_guete(df: pd.DataFrame, merkmale: list[str], seed: int) -> list[dict]:
    """Was eine Gemeinde tatsaechlich erlebt: Wenn sie die obersten N Faelle prueft,
    wie viele davon sind echte Fehler? Das ist die Zahl, die ein Bauamt wissen will."""
    x, y = df[merkmale].to_numpy(float), df["ziel"].to_numpy(int)
    x_tr, x_te, y_tr, y_te = train_test_split(x, y, test_size=0.3, random_state=seed,
                                              stratify=y)
    m = LogisticRegression(max_iter=2000, class_weight="balanced").fit(x_tr, y_tr)
    p = m.predict_proba(x_te)[:, 1]
    rang = np.argsort(-p)
    zeilen = []
    for k in (20, 50, 100, 200, 500):
        if k > len(rang):
            break
        treffer = int(y_te[rang[:k]].sum())
        zeilen.append({"top": k, "treffer": treffer,
                       "quote_pct": round(100 * treffer / k, 1)})
    return zeilen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=str(config.PROCESSED / "kalibrierung_ge.json"))
    a = p.parse_args(argv)

    con = pipeline.connect()
    df = daten(con)
    print(f"{len(df)} Genfer Gebaeude mit Label, davon {int(df.ziel.sum())} mit "
          f"falschem Eintrag ({100 * df.ziel.mean():.1f} %)\n")

    ergebnisse = {}
    for name, merkmale in [("nur Belege", BELEG_MERKMALE),
                           ("nur Metadaten", META_MERKMALE),
                           ("beides", BELEG_MERKMALE + META_MERKMALE)]:
        r = modell(df, merkmale, a.seed)
        ergebnisse[name] = r
        print(f"{name:16s} AUC {r['auc']}   AP {r['ap']}   "
              f"(Testmenge {r['n_test']}, davon {r['positiv_test']} positiv)")

    print("\nKoeffizienten des vollen Modells, nach Staerke:")
    voll = ergebnisse["beides"]["koeffizienten"]
    for k, v in sorted(voll.items(), key=lambda kv: -abs(kv[1])):
        richtung = "spricht fuer Fehler" if v > 0 else "spricht dagegen"
        print(f"  {k:16s} {v:+.3f}   {richtung}")

    print("\nWas eine Gemeinde erlebt, wenn sie die obersten N Faelle prueft:")
    for z in top_k_guete(df, BELEG_MERKMALE + META_MERKMALE, a.seed):
        print(f"  Top {z['top']:4d}: {z['treffer']:4d} echte Fehler "
              f"= {z['quote_pct']} %")

    ziel = Path(a.out) if str(a.out).startswith(str(config.ROOT)) else config.ROOT / a.out
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(
        {"seed": a.seed, "n": len(df), "positivrate": round(float(df.ziel.mean()), 4),
         "modelle": ergebnisse,
         "top_k": top_k_guete(df, BELEG_MERKMALE + META_MERKMALE, a.seed)},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ngeschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
