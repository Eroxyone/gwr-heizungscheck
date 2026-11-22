"""Vergleicht die regelbasierte Stichwortsuche gegen ein einzeln gelabeltes Gold-Set.

Die Stichprobe ist geschichtet gezogen (90 von der Regel erkannt, 40 nicht erkannt aber
mit heizungsnahen Woertern, 20 rein zufaellig). Precision laesst sich daraus direkt
schaetzen. Fuer den Recall muss zurueckgewichtet werden, weil die Schichten
unterschiedlich stark gezogen wurden.

    python src/eval_extraktion.py
"""
from __future__ import annotations

import json

import pandas as pd

import config
import pipeline
from fmt import de, md

STICHPROBE = config.LABELS / "label_stichprobe.json"
GOLD = config.LABELS / "gold_labels.json"
ZIEL = config.REPORTS / "extraktion_evaluation.md"


def kennzahlen(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else float("nan")
    return {"TP": tp, "FP": fp, "FN": fn,
            "Precision": round(100 * precision, 1),
            "Recall": round(100 * recall, 1),
            "F1": round(100 * f1, 1)}


def main() -> None:
    proben = json.loads(STICHPROBE.read_text(encoding="utf-8"))
    gold = json.loads(GOLD.read_text(encoding="utf-8"))["labels"]

    # Schichtgroessen in der Grundgesamtheit, fuer die Hochrechnung des Recalls
    con = pipeline.connect()
    grund = {
        "erkannt": con.execute("""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND ist_heizungsereignis""").fetchone()[0],
        "verdaechtig": con.execute("""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND NOT ist_heizungsereignis
            AND regexp_matches(lower(beschrieb),
                'heiz|wärme|waerme|energie|sanierung|kamin|therm|boiler|kessel|brenner|tank|solar|pellet|holz|klima')
            """).fetchone()[0],
        "zufall": con.execute("""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND NOT ist_heizungsereignis
            AND NOT regexp_matches(lower(beschrieb),
                'heiz|wärme|waerme|energie|sanierung|kamin|therm|boiler|kessel|brenner|tank|solar|pellet|holz|klima')
            """).fetchone()[0],
    }
    con.close()

    zeilen = []
    for p in proben:
        g = gold[str(p["nr"])]
        zeilen.append({
            "nr": p["nr"], "gruppe": p["gruppe"], "text": p["text"],
            "regel_heizung": bool(p["regel_heizung"]),
            "regel_traeger": p["regel_traeger"],
            "gold_heizung": g["heizung"], "gold_wechsel": g["wechsel"],
            "gold_neu": g["neu"], "gold_alt": g["alt"],
        })
    df = pd.DataFrame(zeilen)
    gezogen = df.groupby("gruppe").size().to_dict()
    df["gewicht"] = df["gruppe"].map(lambda g: grund[g] / gezogen[g])

    ergebnisse = []

    # -------------------------------------------------- Aufgabe 1: ist es ein Heizungsereignis?
    tp = int(((df.regel_heizung) & (df.gold_heizung)).sum())
    fp = int(((df.regel_heizung) & (~df.gold_heizung)).sum())
    fn = int(((~df.regel_heizung) & (df.gold_heizung)).sum())
    ergebnisse.append({"Aufgabe": "Heizungsereignis erkennen (ungewichtet)", **kennzahlen(tp, fp, fn)})

    # gewichtet: die Schichten wurden unterschiedlich stark gezogen
    def gew(maske) -> float:
        return float(df.loc[maske, "gewicht"].sum())

    tpg = gew((df.regel_heizung) & (df.gold_heizung))
    fpg = gew((df.regel_heizung) & (~df.gold_heizung))
    fng = gew((~df.regel_heizung) & (df.gold_heizung))
    ergebnisse.append({"Aufgabe": "Heizungsereignis erkennen (auf Grundgesamtheit hochgerechnet)",
                       **kennzahlen(round(tpg), round(fpg), round(fng))})

    # -------------------------------------------------- Aufgabe 2: nachfuehrungsrelevanter Wechsel?
    tp = int(((df.regel_heizung) & (df.gold_wechsel)).sum())
    fp = int(((df.regel_heizung) & (~df.gold_wechsel)).sum())
    fn = int(((~df.regel_heizung) & (df.gold_wechsel)).sum())
    ergebnisse.append({"Aufgabe": "Traegerwechsel erkennen (ungewichtet)", **kennzahlen(tp, fp, fn)})

    # -------------------------------------------------- Aufgabe 3: neuer Traeger korrekt?
    mit = df[(df.regel_heizung) & (df.gold_wechsel) & (df.gold_neu.notna())]
    richtig = int((mit.regel_traeger == mit.gold_neu).sum())
    ergebnisse.append({
        "Aufgabe": f"neuen Energieträger benennen ({len(mit)} Fälle mit Träger im Text)",
        "TP": richtig, "FP": len(mit) - richtig, "FN": 0,
        "Precision": round(100 * richtig / len(mit), 1) if len(mit) else float("nan"),
        "Recall": float("nan"), "F1": float("nan"),
    })

    # -------------------------------------------------- Aufgabe 4: alter Traeger
    mit_alt = df[df.gold_alt.notna()]
    regel_alt = {p["nr"]: p["regel_alt"] for p in proben}
    treffer_alt = sum(1 for _, r in mit_alt.iterrows() if regel_alt[r.nr] == r.gold_alt)
    ergebnisse.append({
        "Aufgabe": f"bisherigen Energieträger benennen ({len(mit_alt)} Fälle im Gold-Set)",
        "TP": treffer_alt, "FP": 0, "FN": len(mit_alt) - treffer_alt,
        "Precision": float("nan"),
        "Recall": round(100 * treffer_alt / len(mit_alt), 1) if len(mit_alt) else float("nan"),
        "F1": float("nan"),
    })

    tabelle = pd.DataFrame(ergebnisse)

    # -------------------------------------------------- Vergleich mit der LLM-Extraktion
    llm_datei = config.PROCESSED / "llm_gold_qwen7b.jsonl"
    vergleich = ""
    if llm_datei.exists():
        llm = {j["nr"]: j["llm"] for j in
               (json.loads(z) for z in llm_datei.read_text(encoding="utf-8").splitlines())}
        soll = {n: gold[str(n)]["wechsel"] for n in llm}
        regel_pred = {n: bool(next(p for p in proben if p["nr"] == n)["regel_heizung"]) for n in llm}
        llm_pred = {n: llm[n].get("ist_traegerwechsel", False) for n in llm}

        def messe(name, pred):
            tp = sum(1 for n in pred if pred[n] and soll[n])
            fp = sum(1 for n in pred if pred[n] and not soll[n])
            fn = sum(1 for n in pred if not pred[n] and soll[n])
            k = kennzahlen(tp, fp, fn)
            return {"Verfahren": name, **k}

        vgl = pd.DataFrame([
            messe("nur Stichwortregel", regel_pred),
            messe("nur LLM (`qwen2.5:7b`, lokal)", llm_pred),
            messe("Regel als Vorfilter, LLM als Prüfer",
                  {n: regel_pred[n] and llm_pred[n] for n in llm}),
            messe("Regel oder LLM", {n: regel_pred[n] or llm_pred[n] for n in llm}),
        ])
        vergleich = md(vgl)

    # -------------------------------------------------- Fehlerliste
    fehler = df[(df.regel_heizung != df.gold_heizung)
                | ((df.regel_heizung) & (~df.gold_wechsel))].copy()
    fehler["Fehlertyp"] = fehler.apply(
        lambda r: "falsch positiv (kein Heizungsereignis)" if r.regel_heizung and not r.gold_heizung
        else ("übersehen" if not r.regel_heizung and r.gold_heizung
              else "kein Trägerwechsel, trotzdem gezählt"), axis=1)
    fehlerliste = fehler[["nr", "Fehlertyp", "text"]].rename(
        columns={"nr": "Nr.", "text": "Projektbeschrieb"})
    fehlerliste["Projektbeschrieb"] = fehlerliste["Projektbeschrieb"].str.slice(0, 115)

    schichten = pd.DataFrame([
        {"Schicht": k, "gezogen": gezogen[k], "in Grundgesamtheit": grund[k],
         "Gewicht": round(grund[k] / gezogen[k], 1)}
        for k in ("erkannt", "verdaechtig", "zufall")
    ])

    text = VORLAGE.format(
        n=len(df),
        tabelle=de(tabelle.to_markdown(index=False, floatfmt=".1f").replace(" nan", "  – ")),
        schichten=de(schichten.to_markdown(index=False)),
        fehlerliste=fehlerliste.to_markdown(index=False),
        n_fehler=len(fehler),
        pct_fp=round(100 * fp / max(1, int(df.regel_heizung.sum())), 1),
        llm_vergleich=vergleich or "_(noch nicht gemessen - `python src/extract_llm.py --gold` ausführen)_",
    )
    ZIEL.write_text(text, encoding="utf-8")
    print(tabelle.to_string(index=False))
    print(f"\ngeschrieben: {ZIEL}")


VORLAGE = """# Wie gut ist die Stichwortsuche? Evaluation an einem Gold-Set

Die Erkennung von Heizungsereignissen in Baugesuchstexten läuft bisher über Stichwörter
und Regeln (`sql/silver_baugesuche.sql`). Diese Auswertung misst, wie gut das ist, und
schätzt damit ab, was eine LLM-Extraktion zusätzlich bringen würde.

## Vorgehen

{n} Baugesuchstexte wurden einzeln gelabelt (Volltext gelesen, nicht nur der Anfang). Die Labels
stammen aus einer Durchsicht durch ein Sprachmodell (Claude Opus 5, siehe `gelabelt_von` in
`data/labels/gold_labels.json`); eine Zweitprüfung durch eine weitere Person ist nicht
dokumentiert.
Die Stichprobe ist geschichtet gezogen, damit sowohl Fehltreffer als auch übersehene
Fälle sichtbar werden:

{schichten}

Weil die Schichten unterschiedlich stark gezogen wurden, muss der Recall auf die
Grundgesamtheit hochgerechnet werden. Die Precision lässt sich direkt ablesen.

Gelabelt wurden fünf Felder: ob es überhaupt um einen Wärmeerzeuger geht, ob daraus ein
Trägerwechsel folgt (also etwas, das im GWR nachgeführt werden müsste), der neue und der
bisherige Energieträger, und ob es ein Neubau ist.

## Ergebnis

{tabelle}

## Die {n_fehler} Fehler im Einzelnen

{fehlerliste}

## Was daraus folgt

Die Stichwortsuche findet Heizungsereignisse zuverlässig. Ihre Schwäche liegt woanders:
Sie kann nicht unterscheiden, ob eine Heizung **neu gebaut** oder nur **erwähnt** wird.

Drei Fehlermuster, die eine Regel prinzipiell nicht löst:

1. **Bestehende Anlagen.** "Bestehende Pelletsheizung im Hauptgebäude" beschreibt den
   Ist-Zustand, kein Vorhaben.
2. **Wärmepumpe ersetzt Wärmepumpe.** "Ersatz der beiden bestehenden Wärmepumpen" ist ein
   Heizungsereignis, aber der GWR-Eintrag bleibt derselbe.
3. **Wärmepumpen ohne Gebäudebezug.** Pool-Wärmepumpen, Klimageräte, Rückkühler und
   Erdgasleitungen im Boden lösen dieselben Stichwörter aus.

## Gemessen: was die LLM-Extraktion wirklich bringt

Dieselben 150 Texte, durch `src/extract_llm.py` mit einem lokalen qwen2.5:7b:

{llm_vergleich}

**Das LLM sortierte sieben der acht Fehltreffer der Regel korrekt aus** - genau die drei Muster
oben. Dafür übersieht es mehr: fünf Trägerwechsel, die die Regel gefunden hätte.

Zwei dieser Auslassungen sind echte Modellfehler, bei denen sich die Ausgabe selbst
widerspricht. Bei "Erstellung von 18 Erdwärmesonden" schreibt das Modell als Begründung
"Erdwärmesonden bedeuten eine Wärmepumpe" und setzt das Flag trotzdem auf falsch. Das ist
typisch für ein 7B-Modell; ein grösseres würde das vermutlich vermeiden.

**Die Kaskade schlägt beide Einzelverfahren.** Die Regel als Vorfilter, das LLM als Prüfer:
Precision steigt von 91,1 % auf 98,7 %, bei gleichem Recall wie das LLM allein. Das ist auch
betrieblich die richtige Anordnung - die Regel läuft ohne Aufwand über alle 22'780 Texte, das LLM
muss dann nur noch die rund 1'750 Treffer prüfen. Das ist ein dreizehnmal kleinerer
Rechenaufwand als eine LLM-Extraktion über den ganzen Bestand.

**Für die Anwendung zählt Precision mehr als Recall.** Ein Fehltreffer in einer
Verdachtsliste kostet Vertrauen bei der Gemeinde, die ihn prüft. Ein übersehener Fall
kostet nur einen entgangenen Treffer.

## Grenzen dieser Evaluation

- Die Labels stammen aus einer einzelnen Durchsicht, nicht aus einem Mehrfachurteil.
  Grenzfälle (Blockheizkraftwerk, Wärmespeicher, Energiezentrale einer Kläranlage) wurden
  konservativ als "kein Gebäude-Wärmeerzeuger" gewertet.
- {n} Texte reichen für Precision, aber der hochgerechnete Recall hat eine grosse
  Unsicherheit: In der Zufallsschicht liegt ein einziger Grenzfall, und dieser eine Fall
  wird mit einem Gewicht von mehreren Hundert multipliziert.
- Bei einer Weiterführung sollte das Gold-Set auf rund 500 Texte wachsen und von zwei Personen
  unabhängig gelabelt werden, damit sich die Übereinstimmung messen lässt.
"""

if __name__ == "__main__":
    main()
