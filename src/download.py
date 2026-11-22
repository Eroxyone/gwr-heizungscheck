"""Bronze-Layer: Rohdaten herunterladen und Manifest schreiben.

Quellen siehe README.md. Alle Downloads landen in data/raw/ (nicht im Git).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import config

RAW = config.RAW
MANIFEST = RAW / "manifest.json"
VERSUCHE = 3
SOURCES = config.QUELLEN


UA = {"User-Agent": config.USER_AGENT}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(key: str, force: bool = False) -> dict:
    src = SOURCES[key]
    target = RAW / src["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    frisch = force or not target.exists()
    if not frisch:
        print(f"[skip] {key}: {target.name} existiert bereits")
    else:
        print(f"[get ] {key}: {src['url']}")
        req = urllib.request.Request(src["url"], headers=UA)
        # Erst in eine Nebendatei, dann umbenennen: Bricht die Uebertragung ab, bleibt keine
        # halbe Datei liegen, die der naechste Lauf als "existiert bereits" ueberspringt.
        teil = target.with_name(target.name + ".part")
        with urllib.request.urlopen(req, timeout=300) as resp, teil.open("wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
        teil.replace(target)
    # Manche WFS geben hoechstens 5000 Objekte ab. Dann weiterblaettern, bis nichts
    # mehr kommt, und alles zu einer Datei zusammenfuegen. Nur nach einem frischen Abruf:
    # Auf einer schon zusammengefuegten Datei haengte ein zweiter Lauf dieselben Seiten
    # noch einmal an.
    if frisch and src.get("paging") and target.suffix == ".json":
        import json as _json
        daten = _json.loads(target.read_text(encoding="utf-8"))
        schritt = src["paging"]
        index = schritt
        while True:
            seite_url = f"{src['url']}&maxFeatures={schritt}&startIndex={index}"
            req = urllib.request.Request(seite_url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as resp:
                seite = _json.loads(resp.read())
            weitere = seite.get("features") or []
            if not weitere:
                break
            daten["features"].extend(weitere)
            _log_seite = len(weitere)
            print(f"       + {_log_seite} weitere ab Index {index}")
            index += schritt
        target.write_text(_json.dumps(daten, ensure_ascii=False), encoding="utf-8")

    # ArcGIS-Dienste geben hoechstens maxRecordCount Objekte je Anfrage heraus und
    # blaettern ueber resultOffset. Ohne dieses Blaettern kaeme ein Bruchteil der Daten
    # zurueck, und zwar ohne jede Fehlermeldung - derselbe stille Abschnitt wie beim
    # 5000er-Limit von Solothurn.
    if frisch and src.get("arcgis_paging"):
        import json as _json
        daten = _json.loads(target.read_text(encoding="utf-8"))
        schritt = src["arcgis_paging"]
        offset = len(daten.get("features") or [])
        while True:
            req = urllib.request.Request(
                f"{src['url']}&resultOffset={offset}&resultRecordCount={schritt}",
                headers=UA)
            with urllib.request.urlopen(req, timeout=300) as resp:
                seite = _json.loads(resp.read())
            weitere = seite.get("features") or []
            if not weitere:
                break
            daten["features"].extend(weitere)
            print(f"       + {len(weitere)} weitere ab Offset {offset}")
            offset += len(weitere)
        target.write_text(_json.dumps(daten, ensure_ascii=False), encoding="utf-8")

    # GML traegt eine schemaLocation, die GDAL beim Lesen ueber HTTPS nachladen will.
    # Hinter einer Firewall mit eigenem Wurzelzertifikat scheitert das, und zwar mit
    # einer SSL-Meldung, die nichts mit der eigentlichen Datei zu tun hat. Das Schema
    # steht ohnehin im Dokument - also die Referenz entfernen.
    if target.suffix == ".gml":
        roh = target.read_text(encoding="utf-8", errors="replace")
        ohne = re.sub(r'\s+xsi:schemaLocation="[^"]*"', "", roh)
        if ohne != roh:
            target.write_text(ohne, encoding="utf-8")

    # Archive entpacken, damit die Pipeline die Dateien darin lesen kann. Zielordner ist
    # der Name des Archivs ohne Endung, ausser die Quelle nennt mit "entpacken" einen
    # anderen. Nur Datendateien: Die Archive des BFS enthalten zusaetzlich GeoJSON und
    # SQLite mit mehreren hundert MB, die niemand braucht.
    if target.suffix == ".zip":
        ordner = RAW / src["entpacken"] if "entpacken" in src else target.parent / target.stem
        with zipfile.ZipFile(target) as zf:
            for name in zf.namelist():
                if name.lower().endswith((".gpkg", ".csv")):
                    zf.extract(name, ordner)

    return {
        "url": src["url"],
        "file": src["file"],
        "desc": src["desc"],
        # Ohne Lizenzangabe ist ein Datensatz fuer eine Weitergabe nicht brauchbar,
        # auch wenn er frei herunterladbar war. Siehe config.LIZENZEN.
        **config.lizenz(key),
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
        "downloaded_utc": datetime.fromtimestamp(
            target.stat().st_mtime, tz=UTC
        ).isoformat(),
    }


def main(argv: list[str]) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    force = "--force" in argv
    keys = [a for a in argv[1:] if not a.startswith("-")] or list(SOURCES)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    unbekannt = [k for k in keys if k not in SOURCES]
    if unbekannt:
        print(f"Unbekannte Quellen: {', '.join(unbekannt)}")
        return 2

    # Dreissig Quellen auf einem guten Dutzend fremder Server: Irgendeiner antwortet immer
    # gerade nicht. Der Schaffhauser WFS etwa quittierte einen Abruf mit HTTP 401 und den
    # naechsten eine Minute spaeter mit 200. Deshalb je Quelle mehrere Versuche, und ein
    # endgueltiger Ausfall haelt die uebrigen Quellen nicht auf.
    fehler: dict[str, str] = {}
    for key in keys:
        for versuch in range(1, VERSUCHE + 1):
            try:
                manifest[key] = download(key, force=force)
                print(f"       {manifest[key]['bytes']:,} bytes")
                fehler.pop(key, None)
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError) as ausnahme:
                fehler[key] = str(ausnahme)
                print(f"       Versuch {versuch}/{VERSUCHE} gescheitert: {ausnahme}")
                if versuch < VERSUCHE:
                    time.sleep(5 * versuch)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest: {MANIFEST}")
    if fehler:
        print(f"\n{len(fehler)} von {len(keys)} Quellen nicht geladen:")
        for key, grund in fehler.items():
            print(f"  ! {key}: {grund}")
        print("Erneut versuchen mit:  python src/download.py " + " ".join(fehler))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
