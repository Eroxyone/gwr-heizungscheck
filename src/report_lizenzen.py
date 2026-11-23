"""Lizenzlage der Quellen: Welche darf weiterverwendet werden, welche ist ungeprueft?

Frei herunterladbar ist nicht dasselbe wie frei weiterverwertbar. Das Manifest fuehrt zu
jeder Quelle URL, Groesse, Pruefsumme und Zeitpunkt, aber keine Lizenz.

Dieser Bericht weist die Lizenzangaben aus config.LIZENZEN je Quelle aus und gewichtet
die offenen Punkte danach, wie viele Faelle der Verdachtsliste an der Quelle haengen.

    python src/report_lizenzen.py
"""
from __future__ import annotations

import argparse
from datetime import date
from urllib.parse import urlparse

import pandas as pd

import config
import fmt
import pipeline

ZIEL = config.ROOT / "reports" / "lizenzen.md"

# Welche Quelle liefert die Belege welchen Kantons? Nur grob, aber es genuegt, um die
# ungepruefte Quelle mit dem groessten Hebel zu finden.
KANTON_VON_SCHLUESSEL = {
    "erdwaermesonden_zh": "ZH", "erdregister_zh": "ZH", "grundwasser_zh": "ZH",
    "quellfassung_zh": "ZH", "baugesuche_csv": "ZH", "baugesuche_gpkg": "ZH",
    "erdwaermesonden_be": "BE", "erdwaermesonden_so": "SO", "erdwaermesonden_tg": "TG",
    "erdwaermesonden_sh": "SH", "erdwaermesonden_sz": "SZ", "erdwaermesonden_bl": "BL",
    "erdwaermesonden_ai": "AI", "erdwaermesonden_zg": "ZG", "waermepumpen_sg": "SG",
    "grundwasserwp_ur": "UR", "luftwasserwp_lu": "LU",
}


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    con = pipeline.connect(schreibend=False)

    faelle = dict(con.execute(
        "SELECT kanton, count(*) FROM v_gold_liste GROUP BY 1").fetchall())

    zeilen = []
    for schluessel, quelle in config.QUELLEN.items():
        angabe = config.lizenz(schluessel)
        kanton = KANTON_VON_SCHLUESSEL.get(schluessel)
        zeilen.append({
            "Quelle": quelle["file"],
            "Host": urlparse(quelle["url"]).netloc,
            "Kanton": kanton or "",
            "Fälle auf der Liste": faelle.get(kanton, 0) if kanton else 0,
            "Stufe": angabe["stufe"],
            "Lizenz": angabe["lizenz"],
        })
    df = pd.DataFrame(zeilen).sort_values(
        ["Stufe", "Fälle auf der Liste"], ascending=[True, False])

    offen = df[df["Stufe"] != "belegt"]
    # Je Kanton nur einmal zaehlen: An Zuerich haengen drei Ebenen, aber es sind
    # dieselben 2'143 Faelle. Die Summe ueber die Zeilen waere das Dreifache.
    betroffen = int(offen.drop_duplicates("Kanton")["Fälle auf der Liste"].sum())
    gesamt = int(con.execute("SELECT count(*) FROM v_gold_liste").fetchone()[0])

    text = f"""# Lizenzlage der Quellen

Stand {date.today().strftime('%d.%m.%Y')}. Geprüft ist je Quelle, unter welchen Nutzungsbedingungen sie
veröffentlicht ist und ob die benutzte Ebene selbst belegt ist.

## Warum das zählt

Frei herunterladbar ist nicht dasselbe wie frei weiterverwertbar. Die Pauschalaussage
"alles offene Daten" genügt nicht, sobald Ergebnisse weitergegeben werden: Wer eine
Auswertung weiterverwendet, die auf diesen Quellen beruht, muss wissen, unter welchen
Bedingungen er das darf.

## Wie geprüft ist

Über die CKAN-Schnittstelle von opendata.swiss. Dort trägt jede Ressource einen von vier
Standardtermen:

| Term | Bedeutung | für die Weitergabe |
|---|---|---|
| `terms_open` | freie Nutzung | tauglich |
| `terms_by` | freie Nutzung, Quellenangabe Pflicht | tauglich, Quelle nennen |
| `terms_ask` | kommerzielle Nutzung nur mit Bewilligung | **nicht** ohne Rückfrage |
| `terms_by_ask` | beides | **nicht** ohne Rückfrage |

**Keine der verwendeten Quellen trägt `terms_ask`.**

## Stand

{len(df) - len(offen)} von {len(df)} Quellen sind mit der benutzten Ebene selbst auf
opendata.swiss belegt. Bei **{len(offen)}** ist nur die kantonsweite Regel des
Datenportals belegt, die Ebene selbst ist dort nicht einzeln aufgeführt - das betrifft
{betroffen} der {gesamt} Fälle auf der Verdachtsliste.

{fmt.md(df)}

## Offene Punkte

Für Solothurn, Zug und Basel-Landschaft gilt die kantonsweite Regel ihres Datenportals,
die benutzte Ebene ist dort aber nicht einzeln aufgeführt. Das ist ein schwächerer Beleg
als eine eigene Datensatzseite.

Klären lässt sich das durch eine Anfrage beim jeweiligen Amt für Geoinformation, ob die
bezogene Ebene weiterverwendet und weitergegeben werden darf. Die Antwort gehört mit Datum
in `config.LIZENZEN`, Feld `beleg`.

Für jede Weitergabe von Ergebnissen gilt: Zu nennen ist, auf welchen Quellen sie beruhen
und welche davon eine Quellenangabe verlangen. Eine pauschale Zusicherung, dass alles frei
weiterverwertbar sei, ist durch diese Prüfung nicht gedeckt.
"""
    ZIEL.write_text(fmt.de(text), encoding="utf-8")
    print(f"{ZIEL} geschrieben - {len(offen)} ungeprüfte Quellen, "
          f"{betroffen} betroffene Fälle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
