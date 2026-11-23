"""Vergleicht die regelbasierte Stichwortsuche gegen ein einzeln gelabeltes Gold-Set.

Die Stichprobe ist geschichtet gezogen (90 von der Regel erkannt, 40 nicht erkannt aber
mit heizungsnahen Woertern, 20 rein zufaellig). Precision laesst sich daraus direkt
schaetzen. Fuer den Recall muss zurueckgewichtet werden, weil die Schichten
unterschiedlich stark gezogen wurden.

    python src/eval_extraktion.py
"""
from __future__ import annotations

import json
from datetime import date
from math import sqrt

import pandas as pd

import config
import pipeline
from fmt import de, tsd

STICHPROBE = config.LABELS / "label_stichprobe.json"
GOLD = config.LABELS / "gold_labels.json"
ZIEL = config.REPORTS / "extraktion_evaluation.md"

# Die Schichten heissen in der Stichprobendatei technisch; im Bericht stehen sie ausgeschrieben.
SCHICHT_TXT = {
    "erkannt": "von der Regel erkannt",
    "verdaechtig": "nicht erkannt, heizungsnahe Wörter",
    "zufall": "nicht erkannt, Zufallsauswahl",
}
HEIZUNGSNAH = ("'heiz|wärme|waerme|energie|sanierung|kamin|therm|boiler|kessel|brenner|tank|"
               "solar|pellet|holz|klima'")


def kennzahlen(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else float("nan")
    return {"TP": tp, "FP": fp, "FN": fn,
            "Precision": round(100 * precision, 1),
            "Recall": round(100 * recall, 1),
            "F1": round(100 * f1, 1)}


def wilson(treffer: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95-Prozent-Vertrauensbereich fuer einen Anteil nach Wilson, in Prozent."""
    if n == 0:
        return (0.0, 0.0)
    p = treffer / n
    nenner = 1 + z * z / n
    mitte = (p + z * z / (2 * n)) / nenner
    rand = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
    return (round(max(0.0, 100 * (mitte - rand)), 1), round(min(100.0, 100 * (mitte + rand)), 1))


def tabelle(df: pd.DataFrame) -> str:
    """Markdown-Tabelle mit Dezimalkomma; fehlende Werte als Strich."""
    return de(df.to_markdown(index=False, floatfmt=".1f").replace(" nan", "  – "))


def main() -> None:
    proben = json.loads(STICHPROBE.read_text(encoding="utf-8"))
    gold_datei = json.loads(GOLD.read_text(encoding="utf-8"))
    gold = gold_datei["labels"]

    # Schichtgroessen in der Grundgesamtheit, fuer die Hochrechnung des Recalls
    con = pipeline.connect(schreibend=False)
    grund = {
        "erkannt": con.execute("""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND ist_heizungsereignis""").fetchone()[0],
        "verdaechtig": con.execute(f"""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND NOT ist_heizungsereignis
            AND regexp_matches(lower(beschrieb), {HEIZUNGSNAH})
            """).fetchone()[0],
        "zufall": con.execute(f"""SELECT count(*) FROM silver_baugesuche
            WHERE ist_erstpublikation AND NOT ist_heizungsereignis
            AND NOT regexp_matches(lower(beschrieb), {HEIZUNGSNAH})
            """).fetchone()[0],
    }
    # Umfang des Datensatzes, damit die Schichtsumme einzuordnen ist: Die Schichten zaehlen
    # Vorhaben mit Projektbeschrieb, der Datensatz zaehlt Publikationen.
    n_pub, n_vorhaben, n_ohne_text, n_heiz, stand_bg = con.execute("""
        SELECT count(*), sum(ist_erstpublikation::INT),
               sum((ist_erstpublikation AND beschrieb IS NULL)::INT),
               sum(ist_heizungsereignis::INT), max(pub_datum)
        FROM silver_baugesuche""").fetchone()
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
    ergebnisse.append({"Aufgabe": "Trägerwechsel erkennen (ungewichtet)", **kennzahlen(tp, fp, fn)})

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

    # -------------------------------------------------- Vergleich mit der LLM-Extraktion
    llm_datei = config.PROCESSED / "llm_gold_qwen7b.jsonl"
    llm_abschnitt = LLM_FEHLT
    grenze_fallzahl = "Die Kaskade ist in diesem Lauf nicht gemessen."
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

        regel = messe("nur Stichwortregel", regel_pred)
        nur_llm = messe("nur LLM (`qwen2.5:7b`, lokal)", llm_pred)
        kaskade = messe("Regel als Vorfilter, LLM als Prüfer",
                        {n: regel_pred[n] and llm_pred[n] for n in llm})
        oder = messe("Regel oder LLM", {n: regel_pred[n] or llm_pred[n] for n in llm})
        n_kaskade = kaskade["TP"] + kaskade["FP"]
        ci = wilson(kaskade["TP"], n_kaskade)
        llm_abschnitt = LLM_VORLAGE.format(
            n=len(llm),
            llm_vergleich=tabelle(pd.DataFrame([regel, nur_llm, kaskade, oder])),
            fp_regel=regel["FP"], fp_weg=regel["FP"] - kaskade["FP"],
            fn_llm=nur_llm["FN"], fn_regel=regel["FN"],
            p_regel=de(str(regel["Precision"])), p_kaskade=de(str(kaskade["Precision"])),
            tp_kaskade=kaskade["TP"], fp_kaskade=kaskade["FP"], n_kaskade=n_kaskade,
            ci_von=de(str(ci[0])), ci_bis=de(str(ci[1])),
            n_pub=tsd(n_pub), n_heiz=tsd(n_heiz),
        )
        grenze_fallzahl = (
            f"Die Precision der Kaskade beruht auf n = {n_kaskade} positiven Urteilen "
            f"({kaskade['TP']} richtig, {kaskade['FP']} falsch). Ein einzelner weiterer "
            f"Fehltreffer senkt sie um {de(str(round(100 / n_kaskade, 1)))} Prozentpunkte.")

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

    reihenfolge = ("erkannt", "verdaechtig", "zufall")
    schichten = pd.DataFrame([
        {"Schicht": SCHICHT_TXT[k], "gezogen": gezogen[k],
         "Vorhaben in der Grundgesamtheit": grund[k],
         "Gewicht": round(grund[k] / gezogen[k], 1)}
        for k in reihenfolge
    ])
    # Wo liegen die uebersehenen Faelle? Davon haengt die Unsicherheit des Recalls ab.
    uebersehen = df[(~df.regel_heizung) & (df.gold_heizung)]
    fn_schichten = "; ".join(
        f"{int((uebersehen.gruppe == k).sum())} in der Schicht \"{SCHICHT_TXT[k]}\" "
        f"(Gewicht {de(str(round(grund[k] / gezogen[k], 1)))})"
        for k in reihenfolge if (uebersehen.gruppe == k).any()) or "keiner"
    zufall_heizung = int(df[df.gruppe == "zufall"].gold_heizung.sum())
    zufall_txt = ("liegt kein Heizungsereignis" if zufall_heizung == 0
                  else f"liegen {zufall_heizung} Heizungsereignisse")

    text = VORLAGE.format(
        n=len(df),
        stand_bg=pd.Timestamp(stand_bg).strftime("%d.%m.%Y"),
        label_datum=date.fromisoformat(gold_datei["datum"]).strftime("%d.%m.%Y"),
        gelabelt_von=gold_datei["gelabelt_von"],
        tabelle=tabelle(pd.DataFrame(ergebnisse)),
        schichten=de(schichten.to_markdown(index=False)),
        n_grund=tsd(sum(grund.values())), n_pub=tsd(n_pub), n_vorhaben=tsd(n_vorhaben),
        n_ohne_text=tsd(n_ohne_text),
        fehlerliste=fehlerliste.to_markdown(index=False),
        n_fehler=len(fehler),
        llm_abschnitt=llm_abschnitt,
        fn_schichten=fn_schichten,
        n_zufall=gezogen["zufall"], zufall_txt=zufall_txt, grenze_fallzahl=grenze_fallzahl,
        gewicht_zufall=de(str(round(grund["zufall"] / gezogen["zufall"], 1))),
    )
    ZIEL.write_text(text, encoding="utf-8")
    print(pd.DataFrame(ergebnisse).to_string(index=False))
    print(f"\ngeschrieben: {ZIEL}")


VORLAGE = """# Texterkennung in Baugesuchen: Evaluation an {n} gelabelten Texten

Stand: Baugesuche des Kantons Zürich bis {stand_bg}, Labels vom {label_datum}. Gemessen wird,
wie zuverlässig die Stichwortregel (`sql/silver_baugesuche.sql`) Heizungsereignisse in
Baugesuchstexten erkennt und was eine nachgeschaltete Prüfung durch ein Sprachmodell
(`src/extract_llm.py`) daran ändert.

## Vorgehen

{n} Baugesuchstexte sind einzeln gelabelt (Volltext, nicht nur der Anfang). Die Labels
stammen von einem Sprachmodell (Feld `gelabelt_von` in `data/labels/gold_labels.json`:
"{gelabelt_von}").
Die Stichprobe ist geschichtet gezogen, damit sowohl Fehltreffer als auch übersehene
Fälle sichtbar werden:

{schichten}

Die Schichten zählen Vorhaben mit Projektbeschrieb und summieren deshalb auf {n_grund}, nicht
auf die {n_pub} Publikationen des Datensatzes: Mehrfachpublikationen desselben Vorhabens
sind zusammengefasst ({n_vorhaben} Vorhaben), und {n_ohne_text} Vorhaben ohne Projektbeschrieb
fallen in keine Schicht.

Weil die Schichten unterschiedlich stark gezogen sind, wird der Recall auf die
Grundgesamtheit hochgerechnet. Die Precision lässt sich direkt ablesen.

Gelabelt sind fünf Felder: ob es um einen Wärmeerzeuger geht, ob daraus ein
Trägerwechsel folgt (also etwas, das im GWR nachgeführt werden müsste), der neue und der
bisherige Energieträger, und ob es ein Neubau ist.

## Ergebnis der Stichwortregel

{tabelle}

## Die {n_fehler} Fehler der Stichwortregel im Einzelnen

{fehlerliste}

## Was daraus folgt

Die Stichwortsuche findet Heizungsereignisse zuverlässig. Sie unterscheidet aber nicht,
ob eine Heizung **neu gebaut** oder nur **erwähnt** wird. Drei Fehlermuster kann eine
Stichwortregel nicht lösen:

1. **Bestehende Anlagen.** "Bestehende Pelletsheizung im Hauptgebäude" beschreibt den
   Ist-Zustand, kein Vorhaben.
2. **Wärmepumpe ersetzt Wärmepumpe.** "Ersatz der beiden bestehenden Wärmepumpen" ist ein
   Heizungsereignis, aber der GWR-Eintrag bleibt derselbe.
3. **Wärmepumpen ohne Gebäudebezug.** Pool-Wärmepumpen, Klimageräte, Rückkühler und
   Erdgasleitungen im Boden lösen dieselben Stichwörter aus.

{llm_abschnitt}

## Grenzen dieser Messung

1. **Keine unabhängige Teststichprobe.** Der Systemprompt des Sprachmodells
   (`src/extract_llm.py`) nennt als Sonderfälle genau die Fehlermuster, die in diesem
   Gold-Set gefunden sind: bestehende Pelletsheizung, Wärmepumpe ersetzt Wärmepumpe,
   Pool, Rückkühler, Gasleitung im Boden. Die Precision der Kaskade ist damit auf
   denselben Texten gemessen, an denen der Prompt entwickelt ist. Auf neuen Texten ist
   ein tieferer Wert zu erwarten; wie viel tiefer, ist nicht gemessen.
2. **Kleine Fallzahl.** {grenze_fallzahl}
3. **Labels von einem Sprachmodell.** Die Labels stammen aus einer einzelnen Durchsicht
   durch ein Sprachmodell, ohne Zweitprüfung durch eine Person. Grenzfälle
   (Blockheizkraftwerk, Wärmespeicher, Energiezentrale einer Kläranlage) sind
   konservativ als "kein Gebäude-Wärmeerzeuger" gewertet.
4. **Der hochgerechnete Recall ist unsicher.** Übersehene Heizungsereignisse: {fn_schichten}.
   In der Zufallsschicht ({n_zufall} Texte, Gewicht {gewicht_zufall}) {zufall_txt};
   ein einziger übersehener Fall dort würde den hochgerechneten Recall deutlich senken.

Eine belastbare Messung braucht eine frische Stichprobe, die erst nach dem Festlegen von
Regel und Prompt gezogen wird, Labels von einer Person (besser von zwei unabhängig, damit
sich die Übereinstimmung messen lässt) und ein Vertrauensintervall zur Precision.
"""

LLM_VORLAGE = """## Prüfung durch ein Sprachmodell

Dieselben {n} Texte, durch `src/extract_llm.py` mit einem lokalen `qwen2.5:7b`. Gemessen
ist die Aufgabe "Trägerwechsel erkennen":

{llm_vergleich}

**Das Sprachmodell sortiert {fp_weg} der {fp_regel} Fehltreffer der Regel aus**, und zwar
Fälle aus den drei Mustern oben. Dafür übersieht es {fn_llm} Trägerwechsel, die Regel {fn_regel}.

Zwei dieser Auslassungen sind Modellfehler, bei denen sich die Ausgabe selbst
widerspricht. Bei "Erstellung von 18 Erdwärmesonden" schreibt das Modell als Begründung
"Erdwärmesonden bedeuten eine Wärmepumpe" und setzt das Merkmal trotzdem auf falsch. Ob ein
grösseres Modell das vermeidet, ist nicht gemessen.

**In dieser Messung hat die Kaskade die höchste Precision.** Regel als Vorfilter,
Sprachmodell als Prüfer: Die Precision steigt von {p_regel} % auf {p_kaskade} %
({tp_kaskade} von {n_kaskade} positiven Urteilen richtig, {fp_kaskade} falsch;
Wilson-Intervall zu 95 %: {ci_von} bis {ci_bis} %), bei gleichem Recall wie das
Sprachmodell allein. Der Wert gilt nur mit den Vorbehalten im Abschnitt "Grenzen dieser
Messung". Die Anordnung spart Rechenaufwand: Die Regel läuft über alle {n_pub}
Publikationen, das Sprachmodell prüft nur die {n_heiz} Treffer der Regel.

**Für eine Verdachtsliste zählt Precision mehr als Recall.** Ein Fehltreffer erzeugt
Prüfaufwand ohne Ergebnis, ein übersehener Fall fehlt nur."""

LLM_FEHLT = """## Prüfung durch ein Sprachmodell

_(noch nicht gemessen - `python src/extract_llm.py --gold` ausführen)_"""

if __name__ == "__main__":
    main()
