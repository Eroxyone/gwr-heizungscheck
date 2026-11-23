"""LLM-Extraktion der Heizungsereignisse aus Baugesuchstexten.

Ersetzt die Stichwortsuche aus silver_baugesuche.sql durch eine Extraktion, die den
Satzbau versteht. Die Evaluation in reports/extraktion_evaluation.md zeigt, wo das
noetig ist: Die Regel erkennt Heizungsereignisse zuverlaessig, kann aber nicht
unterscheiden, ob eine Anlage neu gebaut oder nur erwaehnt wird.

Zwei Backends:
  anthropic  Claude ueber die API, mit structured outputs
  ollama     lokales Modell ueber die Ollama-HTTP-Schnittstelle, fuer den GPU-Server

    python src/extract_llm.py --limit 20                    # Probelauf
    python src/extract_llm.py --gold                         # gegen das Gold-Set messen
    python src/extract_llm.py --test3 --out data/processed/llm_extraktion.jsonl
    python src/extract_llm.py --alle --out data/processed/extraktion.jsonl
    python src/extract_llm.py --backend ollama --model qwen2.5:32b --gold
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

import config
import pipeline

Traeger = Literal["waermepumpe", "fernwaerme", "holz", "solarthermie",
                  "gas", "oel", "elektro", "unbekannt"]


class Heizungsereignis(BaseModel):
    """Was aus einem Baugesuchstext ueber den Waermeerzeuger hervorgeht."""

    betrifft_heizung: bool = Field(
        description="Geht es um einen Waermeerzeuger, der ein Gebaeude beheizt? "
                    "Nein bei Pool-Waermepumpen, Klimageraeten, Rueckkuehlern, "
                    "Fernwaermeleitungen ohne Gebaeudeanschluss und Gasleitungen im Boden.")
    ist_traegerwechsel: bool = Field(
        description="Aendert sich dadurch der Energietraeger des Gebaeudes? "
                    "Nein, wenn eine bestehende Anlage nur beschrieben wird, "
                    "und nein, wenn eine Waermepumpe durch eine Waermepumpe ersetzt wird.")
    neuer_traeger: Traeger = Field(
        description="Energietraeger nach dem Umbau, 'unbekannt' wenn der Text ihn nicht nennt.")
    alter_traeger: Traeger = Field(
        description="Bisheriger Energietraeger, 'unbekannt' wenn der Text ihn nicht nennt.")
    ist_neubau: bool = Field(
        description="Handelt es sich um einen Neubau oder Ersatzneubau statt um einen "
                    "Eingriff im Bestand?")
    heizung_ist_hauptzweck: bool = Field(
        description="Ist die Heizung der Hauptgegenstand des Gesuchs oder nur ein Nebenpunkt?")
    begruendung: str = Field(
        description="Ein kurzer Satz, worauf sich die Einschaetzung stuetzt.")


SYSTEM = """Du liest Projektbeschriebe aus Schweizer Baugesuchen und extrahierst, was sie
ueber den Waermeerzeuger des Gebaeudes aussagen.

Die Auswertung dient dazu, veraltete Heizungseintraege im Gebaeude- und Wohnungsregister
zu finden. Entscheidend ist deshalb nicht, ob das Wort "Waermepumpe" vorkommt, sondern ob
sich der Energietraeger des Gebaeudes tatsaechlich aendert.

Achte besonders auf diese Faelle:
- Eine bestehende Anlage wird nur beschrieben ("bestehende Pelletsheizung im Hauptgebaeude").
  Das ist kein Traegerwechsel.
- Eine Waermepumpe ersetzt eine Waermepumpe. Das ist ein Heizungsereignis, aber kein
  Traegerwechsel, weil der Registereintrag gleich bleibt.
- Waermepumpen ohne Gebaeudebezug: Pool, Klimageraet, Rueckkuehler, Gewaechshaus.
  Das betrifft die Heizung nicht.
- Netzinfrastruktur: Fernwaermeleitungen, Transportleitungen, Gasleitungen im Boden.
  Das betrifft kein einzelnes Gebaeude.
- Erdwaermesonden, Erdsondenbohrungen und Grundwasserfassungen bedeuten eine Waermepumpe.

Antworte nur mit den geforderten Feldern, ohne Vorrede."""


def _prompt(text: str) -> str:
    return f"Projektbeschrieb:\n\n{text}"


# --------------------------------------------------------------------------- Backends
def extrahiere_anthropic(text: str, modell: str, effort: str) -> Heizungsereignis:
    import anthropic

    client = anthropic.Anthropic()
    antwort = client.messages.parse(
        model=modell,
        max_tokens=2000,
        system=SYSTEM,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": _prompt(text)}],
        output_format=Heizungsereignis,
    )
    return antwort.parsed_output


def extrahiere_ollama(text: str, modell: str, host: str,
                      num_gpu: int | None = None) -> Heizungsereignis:
    """Lokales Modell ueber Ollama. Schema wird als JSON-Schema mitgegeben.

    num_gpu=0 erzwingt CPU. Noetig, wenn Ollamas CUDA-Build nicht zum installierten
    Treiber passt - der Server bricht dann mit "PTX was compiled with an unsupported
    toolchain" ab und liefert HTTP 500.
    """
    optionen: dict = {"temperature": 0}
    if num_gpu is not None:
        optionen["num_gpu"] = num_gpu
    rumpf = json.dumps({
        "model": modell,
        "stream": False,
        "format": Heizungsereignis.model_json_schema(),
        "options": optionen,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _prompt(text)},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/chat", data=rumpf, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        daten = json.loads(resp.read())
    return Heizungsereignis.model_validate_json(daten["message"]["content"])


def extrahiere(text: str, backend: str, modell: str, effort: str, host: str,
               num_gpu: int | None = None) -> dict:
    try:
        if backend == "anthropic":
            ergebnis = extrahiere_anthropic(text, modell, effort)
        else:
            ergebnis = extrahiere_ollama(text, modell, host, num_gpu)
        return ergebnis.model_dump()
    # Bewusst breit: Die beiden Backends scheitern auf verschiedene Arten (Netz, HTTP 500,
    # ungueltiges JSON, Schemaverletzung, Fehlerklassen des Anthropic-SDK). Ein einzelner
    # Text darf einen Lauf ueber Tausende nicht abbrechen. Der Fehler steht mit seinem
    # Typ im Ergebnis, und silver_llm.sql wertet solche Zeilen nicht als Urteil.
    except Exception as fehler:
        return {"fehler": f"{type(fehler).__name__}: {fehler}"}


# --------------------------------------------------------------------------- Laeufe
def texte_aus_db(limit: int | None) -> list[dict]:
    con = pipeline.connect()
    grenze = f"LIMIT {limit}" if limit else ""
    zeilen = con.execute(f"""
        SELECT bg_id, beschrieb, ist_heizungsereignis, neuer_traeger
        FROM silver_baugesuche
        WHERE ist_erstpublikation AND beschrieb IS NOT NULL
        ORDER BY hash(beschrieb || 'extract') {grenze}
    """).fetchall()
    con.close()
    return [{"bg_id": z[0], "text": z[1], "regel_heizung": z[2], "regel_traeger": z[3]}
            for z in zeilen]


def texte_aus_test3() -> list[dict]:
    """Genau die Baugesuche, die im Verdachts-Layer als Beleg zaehlen koennten.

    Dedupliziert nach Text: Derselbe Beschrieb ergibt dasselbe Urteil, und es sind
    rund 8 Prozent Wiederholungen im Bestand.
    """
    con = pipeline.connect()
    zeilen = con.execute("""
        SELECT any_value(bg_id) AS bg_id, beschrieb,
               any_value(neuer_traeger) AS regel_traeger,
               any_value(alter_traeger_genannt) AS regel_alt
        FROM v_test3
        WHERE n_gebaeude = 1 AND NOT ist_reiner_neubau AND beschrieb IS NOT NULL
        GROUP BY beschrieb ORDER BY beschrieb
    """).fetchall()
    con.close()
    return [{"bg_id": z[0], "text": z[1], "regel_heizung": True,
             "regel_traeger": z[2], "regel_alt": z[3]} for z in zeilen]


def texte_aus_gold() -> list[dict]:
    proben = json.loads((config.LABELS / "label_stichprobe.json").read_text(encoding="utf-8"))
    gold = json.loads((config.LABELS / "gold_labels.json").read_text(encoding="utf-8"))["labels"]
    for p in proben:
        p["gold"] = gold[str(p["nr"])]
    return proben


def vergleiche_mit_gold(ergebnisse: list[dict]) -> None:
    tp = fp = fn = tn = 0
    wechsel_tp = wechsel_fp = wechsel_fn = 0
    traeger_richtig = traeger_total = 0
    for e in ergebnisse:
        if "fehler" in e["llm"]:
            continue
        g, urteil = e["gold"], e["llm"]
        if urteil["betrifft_heizung"] and g["heizung"]:
            tp += 1
        elif urteil["betrifft_heizung"] and not g["heizung"]:
            fp += 1
        elif not urteil["betrifft_heizung"] and g["heizung"]:
            fn += 1
        else:
            tn += 1
        if urteil["ist_traegerwechsel"] and g["wechsel"]:
            wechsel_tp += 1
        elif urteil["ist_traegerwechsel"] and not g["wechsel"]:
            wechsel_fp += 1
        elif not urteil["ist_traegerwechsel"] and g["wechsel"]:
            wechsel_fn += 1
        if g["wechsel"] and g["neu"]:
            traeger_total += 1
            if urteil["neuer_traeger"] == g["neu"]:
                traeger_richtig += 1

    def quote(a: int, b: int) -> str:
        return f"{100 * a / b:.1f} %" if b else "  -  "

    print("\n=== LLM gegen Gold-Set ===")
    print(f"Heizungsereignis   Precision {quote(tp, tp + fp)}   Recall {quote(tp, tp + fn)}"
          f"   (TP {tp}, FP {fp}, FN {fn}, TN {tn})")
    print(f"Traegerwechsel     Precision {quote(wechsel_tp, wechsel_tp + wechsel_fp)}"
          f"   Recall {quote(wechsel_tp, wechsel_tp + wechsel_fn)}")
    print(f"neuer Traeger      Trefferquote {quote(traeger_richtig, traeger_total)}"
          f"   ({traeger_total} Faelle mit Traeger im Gold-Set)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--backend", choices=("anthropic", "ollama"), default="anthropic")
    p.add_argument("--model", default=None,
                   help="Standard: claude-opus-5 bzw. qwen2.5:32b bei ollama")
    p.add_argument("--effort", default="medium", choices=("low", "medium", "high"),
                   help="nur fuer das Anthropic-Backend")
    p.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    p.add_argument("--limit", type=int, default=None,
                   help="nur die ersten N Texte, fuer Probelaeufe")
    p.add_argument("--alle", action="store_true", help="alle Baugesuche statt --limit")
    p.add_argument("--gold", action="store_true", help="auf dem gelabelten Gold-Set laufen")
    p.add_argument("--test3", action="store_true",
                   help="genau die Baugesuche, die im Verdachts-Layer als Beleg zaehlen")
    p.add_argument("--parallel", type=int, default=8)
    p.add_argument("--cpu", action="store_true",
                   help="Ollama auf CPU zwingen (num_gpu=0), wenn der CUDA-Build klemmt")
    p.add_argument("--out", default=None, help="Ergebnisse als JSONL wegschreiben")
    a = p.parse_args(argv)

    modell = a.model or ("claude-opus-5" if a.backend == "anthropic" else "qwen2.5:32b")
    if a.backend == "anthropic" and not (
            os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("Hinweis: kein ANTHROPIC_API_KEY gesetzt. Der SDK versucht ein "
              "Anmeldeprofil aus 'ant auth login'. Schlaegt das fehl, entweder "
              "'ant auth login' ausfuehren oder --backend ollama verwenden.",
              file=sys.stderr)

    if a.gold:
        proben = texte_aus_gold()
    elif a.test3:
        proben = texte_aus_test3()
    else:
        proben = texte_aus_db(None if a.alle else (a.limit or 20))
    if a.limit and (a.gold or a.test3):
        proben = proben[:a.limit]
    print(f"{len(proben)} Texte, Backend {a.backend}, Modell {modell}")

    ergebnisse: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=a.parallel) as pool:
        auftraege = {
            pool.submit(extrahiere, pr["text"], a.backend, modell, a.effort, a.host,
                        0 if a.cpu else None): pr
            for pr in proben
        }
        for i, fertig in enumerate(futures.as_completed(auftraege), 1):
            pr = auftraege[fertig]
            ergebnisse.append({**pr, "llm": fertig.result()})
            if i % 10 == 0 or i == len(proben):
                print(f"  {i}/{len(proben)}", flush=True)

    fehler = [e for e in ergebnisse if "fehler" in e["llm"]]
    if fehler:
        print(f"\n{len(fehler)} Fehler, erster: {fehler[0]['llm']['fehler']}")

    if a.out:
        # "data/..." meint das Datenverzeichnis, auch wenn GWR_DATA_DIR es verlegt hat
        aus = Path(a.out)
        if aus.is_absolute():
            ziel = aus
        elif aus.parts[:1] == ("data",):
            ziel = config.DATA.joinpath(*aus.parts[1:])
        else:
            ziel = config.ROOT / aus
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with ziel.open("w", encoding="utf-8") as fh:
            for e in ergebnisse:
                fh.write(json.dumps({k: v for k, v in e.items() if k != "gold"},
                                    ensure_ascii=False) + "\n")
        print(f"geschrieben: {ziel}")

    if a.gold:
        vergleiche_mit_gold(ergebnisse)
    return 1 if fehler and len(fehler) == len(ergebnisse) else 0


if __name__ == "__main__":
    raise SystemExit(main())
