"""Bronze-Ingest: GWR fuer alle Kantone laden und als Snapshot ablegen.

Ablauf je Kanton:
  1. ZIP von public.madd.bfs.admin.ch holen
  2. gebaeude-CSV und eingang-CSV daraus lesen, auf die gebrauchten Spalten reduzieren
  3. beide als Parquet unter data/snapshots/gwr/ bzw. gwr_adresse/ ablegen,
     partitioniert nach snapshot_date und kanton

Warum auch die Adressen: Ein Baugesuch aus dem Amtsblattportal bringt ausserhalb Zuerichs
weder Koordinate noch Parzellengeometrie mit, sondern nur Strasse, Hausnummer und PLZ.
Ohne die Eingangstabelle des GWR endet die schweizweite Zuordnung dort.

Der Snapshot ist der Kern des Projekts: Ein einzelner GWR-Stand zeigt nur eine
Momentaufnahme. Erst die Reihe ueber die Zeit macht sichtbar, wie schnell ein Kanton
seine Heizungsdaten nachfuehrt.

Aufruf:
    python src/ingest.py              # alle Kantone, ueberspringt heute schon geladene
    python src/ingest.py ZH BE        # nur diese Kantone
    python src/ingest.py --force      # auch dann laden, wenn der Snapshot schon existiert
    python src/ingest.py --keep-zip   # ZIPs behalten statt nach dem Entpacken zu loeschen
"""
from __future__ import annotations

import concurrent.futures as futures
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

import config

MANIFEST = config.SNAPSHOTS / "ingest_manifest.jsonl"
MAX_PARALLEL = 4
VERSUCHE = 3


def _log(kt: str, text: str) -> None:
    print(f"  [{kt}] {text}", flush=True)


def _hole(url: str, timeout: int = 600) -> bytes:
    """Laedt eine URL mit Wiederholung bei Netzfehlern."""
    letzter: Exception | None = None
    for versuch in range(1, VERSUCHE + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as fehler:
            letzter = fehler
            if versuch < VERSUCHE:
                time.sleep(2 ** versuch)
    raise RuntimeError(f"Download fehlgeschlagen nach {VERSUCHE} Versuchen: {url}") from letzter


def _snapshot_pfad(stand: str, kt: str, art: str = "gwr") -> Path:
    # Hive-Partitionierung braucht Verzeichnisse je Schluessel, nicht Dateinamen.
    return config.SNAPSHOTS / art / f"snapshot_date={stand}" / f"kanton={kt}" / "data.parquet"


def _bereits_geladen(kt: str) -> Path | None:
    """Gibt den Pfad zurueck, falls fuer diesen Kanton heute schon ein vollstaendiger
    Snapshot liegt. Vollstaendig heisst: Gebaeude UND Adressen. Fehlt die Adressdatei,
    muss der Kanton neu geladen werden - ein halber Snapshot waere schlimmer als keiner,
    weil er unbemerkt zu Luecken in der Zuordnung fuehrt."""
    heute = datetime.now().strftime("%Y-%m-%d")
    for basis in (config.SNAPSHOTS / "gwr").glob("snapshot_date=*"):
        stand = basis.name.split("=", 1)[1]
        pfad = basis / f"kanton={kt}" / "data.parquet"
        adr = _snapshot_pfad(stand, kt, "gwr_adresse")
        if pfad.exists() and adr.exists() and stand >= heute:
            return pfad
    return None


def lade_kanton(kt: str, force: bool = False, keep_zip: bool = False) -> dict:
    """Laedt einen Kanton und schreibt den Parquet-Snapshot. Gibt einen Manifest-Eintrag zurueck."""
    if not force and (vorhanden := _bereits_geladen(kt)):
        _log(kt, f"uebersprungen, Snapshot vorhanden: {vorhanden.parent.name}")
        return {"kanton": kt, "status": "skipped", "pfad": str(vorhanden)}

    url = config.GWR_URL.format(kt=kt.lower())
    _log(kt, "lade ...")
    rohdaten = _hole(url)
    pruefsumme = hashlib.sha256(rohdaten).hexdigest()

    with zipfile.ZipFile(io.BytesIO(rohdaten)) as zf:
        csv_bytes = zf.read(config.GWR_DATEIEN["gebaeude"])
        eingang_bytes = zf.read(config.GWR_DATEIEN["eingang"])
        # Codeliste nur einmal, sie ist fuer alle Kantone identisch
        kodes_ziel = config.RAW / "kodes_codes_codici.csv"
        if not kodes_ziel.exists():
            kodes_ziel.parent.mkdir(parents=True, exist_ok=True)
            kodes_ziel.write_bytes(zf.read(config.GWR_DATEIEN["kodes"]))
        if keep_zip:
            (config.RAW / "gwr").mkdir(parents=True, exist_ok=True)
            (config.RAW / "gwr" / f"{kt.lower()}.zip").write_bytes(rohdaten)

    tmp_csv = config.RAW / "tmp" / f"{kt}_gebaeude.csv"
    tmp_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv.write_bytes(csv_bytes)
    tmp_adr = config.RAW / "tmp" / f"{kt}_eingang.csv"
    tmp_adr.write_bytes(eingang_bytes)

    con = duckdb.connect()
    try:
        spalten = ", ".join(f'"{s}"' for s in config.SNAPSHOT_SPALTEN)
        stand = con.execute(
            f"""SELECT max(GEXPDAT) FROM read_csv('{tmp_csv.as_posix()}',
                delim='\t', header=true, all_varchar=true, encoding='utf-8')"""
        ).fetchone()[0]
        ziel = _snapshot_pfad(stand, kt)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        con.execute(
            f"""COPY (
                    SELECT {spalten}
                    FROM read_csv('{tmp_csv.as_posix()}', delim='\t', header=true,
                                  all_varchar=true, encoding='utf-8')
                ) TO '{ziel.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"""
        )
        zeilen = con.execute(
            f"SELECT count(*) FROM read_parquet('{ziel.as_posix()}')"
        ).fetchone()[0]

        ziel_adr = _snapshot_pfad(stand, kt, "gwr_adresse")
        ziel_adr.parent.mkdir(parents=True, exist_ok=True)
        spalten_adr = ", ".join(f'"{s}"' for s in config.SNAPSHOT_SPALTEN_EINGANG)
        con.execute(
            f"""COPY (
                    SELECT {spalten_adr}
                    FROM read_csv('{tmp_adr.as_posix()}', delim='	', header=true,
                                  all_varchar=true, encoding='utf-8')
                ) TO '{ziel_adr.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"""
        )
        adressen = con.execute(
            f"SELECT count(*) FROM read_parquet('{ziel_adr.as_posix()}')"
        ).fetchone()[0]
    finally:
        con.close()
        tmp_csv.unlink(missing_ok=True)
        tmp_adr.unlink(missing_ok=True)

    mb = (ziel.stat().st_size + ziel_adr.stat().st_size) / 1e6
    _log(kt, f"{zeilen:>9,}".replace(",", "'") + " Gebaeude, "
             + f"{adressen:,}".replace(",", "'")
             + f" Adressen, Stand {stand}, {mb:.1f} MB Parquet")
    return {
        "kanton": kt,
        "status": "ok",
        "url": url,
        "zip_bytes": len(rohdaten),
        "zip_sha256": pruefsumme,
        "snapshot_date": stand,
        "zeilen": zeilen,
        "adressen": adressen,
        "pfad": ziel.relative_to(config.DATA).as_posix(),
        "pfad_adresse": ziel_adr.relative_to(config.DATA).as_posix(),
        "geladen_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def main(argv: list[str]) -> int:
    force = "--force" in argv
    keep_zip = "--keep-zip" in argv
    gewuenscht = [a.upper() for a in argv[1:] if not a.startswith("-")]
    kantone = gewuenscht or list(config.KANTONE)
    unbekannt = [k for k in kantone if k not in config.KANTONE]
    if unbekannt:
        print(f"Unbekannte Kantone: {', '.join(unbekannt)}")
        return 2

    config.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    print(f"GWR-Ingest fuer {len(kantone)} Kantone, {MAX_PARALLEL} parallel\n")
    start = time.time()
    eintraege: list[dict] = []
    fehler: list[str] = []

    with futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        auftraege = {pool.submit(lade_kanton, kt, force, keep_zip): kt for kt in kantone}
        for fertig in futures.as_completed(auftraege):
            kt = auftraege[fertig]
            try:
                eintraege.append(fertig.result())
            # Bewusst breit: Was auch immer bei einem Kanton scheitert (Netz, ZIP, CSV,
            # Platte), darf die uebrigen 25 nicht abbrechen und das Manifest der
            # gelungenen nicht verhindern. Der Fehler wird gemeldet, der Lauf endet mit 1.
            except Exception as ausnahme:
                fehler.append(f"{kt}: {ausnahme}")
                _log(kt, f"FEHLER: {ausnahme}")

    neu = [e for e in eintraege if e["status"] == "ok"]
    if neu:
        with MANIFEST.open("a", encoding="utf-8") as fh:
            for eintrag in sorted(neu, key=lambda e: e["kanton"]):
                fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")

    dauer = time.time() - start
    gesamt = sum(e.get("zeilen", 0) for e in neu)
    print(f"\nfertig in {dauer:.0f} s: {len(neu)} geladen, "
          f"{len(eintraege) - len(neu)} uebersprungen, {len(fehler)} Fehler")
    if neu:
        print(f"{gesamt:,} Gebaeude neu im Snapshot".replace(",", "'"))
    for zeile in fehler:
        print(f"  ! {zeile}")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
