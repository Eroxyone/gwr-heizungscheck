"""Bronze-Layer: Rohdaten herunterladen und Manifest schreiben.

Quellen siehe README.md. Alle Downloads landen in data/raw/ (nicht im Git).
"""
from __future__ import annotations

import codecs
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterator
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


class UnerwarteterInhalt(Exception):
    """Der Dienst hat geantwortet, aber nicht mit dem erwarteten Dateiformat."""


# --------------------------------------------------------------------------- Inhaltspruefung
# Ein Geodienst, der eine Anmeldung verlangt oder gerade gestoert ist, antwortet nicht
# immer mit einem HTTP-Fehler. Manche liefern mit Status 200 eine Login-Seite, einen
# WFS-Fehlerbericht oder ein JSON-Fehlerobjekt. Ohne Pruefung laege das unter dem Namen
# der Zieldatei in data/raw, der naechste Lauf uebersprange es als "existiert bereits",
# und erst die Pipeline scheiterte daran. Geprueft wird deshalb vor dem Umbenennen, je
# Dateiendung mit dem billigsten Merkmal, das eine Fehlerseite sicher ausschliesst.
_XML_WURZEL = re.compile(
    rb"(?:<\?xml.*?\?>\s*|<!--.*?-->\s*|<!DOCTYPE[^>]*>\s*)*<(?:[A-Za-z_][\w.-]*:)?([A-Za-z_][\w.-]*)",
    re.S | re.I)
# Wurzelelemente, die keine Daten tragen: HTML-Seiten und die Fehlerberichte von WFS/WMS.
_XML_FEHLERWURZELN = {"html", "exceptionreport", "serviceexceptionreport"}
# ArcGIS meldet Fehler mit Status 200 und einem JSON-Objekt {"error": {...}}.
_JSON_FEHLEROBJEKT = re.compile(rb'\{\s*"error"\s*:')


def _pruefe_zip(pfad: Path, anfang: bytes) -> str | None:
    # is_zipfile sucht das Inhaltsverzeichnis am Dateiende und erkennt damit auch ein
    # abgeschnittenes Archiv.
    return None if zipfile.is_zipfile(pfad) else "kein vollstaendiges ZIP-Archiv"


def _pruefe_sqlite(pfad: Path, anfang: bytes) -> str | None:
    return None if anfang.startswith(b"SQLite format 3\x00") else "keine SQLite-Datei (GeoPackage)"


def _pruefe_parquet(pfad: Path, anfang: bytes) -> str | None:
    with pfad.open("rb") as fh:
        fh.seek(max(0, pfad.stat().st_size - 4))
        ende = fh.read()
    return None if anfang.startswith(b"PAR1") and ende == b"PAR1" else "keine vollstaendige Parquet-Datei"


def _pruefe_json(pfad: Path, anfang: bytes) -> str | None:
    if anfang[:1] not in (b"{", b"["):
        return "beginnt nicht mit { oder ["
    if _JSON_FEHLEROBJEKT.match(anfang):
        return "Fehlerobjekt des Dienstes statt Daten"
    return None


def _pruefe_xml(pfad: Path, anfang: bytes) -> str | None:
    wurzel = _XML_WURZEL.match(anfang)
    if not wurzel:
        return "kein XML"
    name = wurzel.group(1).decode("ascii", errors="replace")
    if name.lower() in _XML_FEHLERWURZELN:
        return f"Wurzelelement <{name}> ist eine HTML- oder Fehlerseite"
    return None


def _pruefe_text(pfad: Path, anfang: bytes) -> str | None:
    # Eine CSV-Kopfzeile beginnt nie mit einer spitzen Klammer, HTML und XML immer.
    return "beginnt mit Markup statt mit Daten" if anfang.startswith(b"<") else None


_PRUEFUNG = {
    ".zip": _pruefe_zip,
    ".gpkg": _pruefe_sqlite, ".sqlite": _pruefe_sqlite,
    ".parquet": _pruefe_parquet,
    ".json": _pruefe_json, ".geojson": _pruefe_json,
    ".gml": _pruefe_xml, ".xml": _pruefe_xml,
    ".csv": _pruefe_text,
}


def pruefe_inhalt(pfad: Path, endung: str) -> None:
    """Wirft UnerwarteterInhalt, wenn die Datei nicht das Format ihrer Endung hat.

    `endung` ist die Endung der Zieldatei (".json", ".gml", ...), nicht die der
    Nebendatei. Unbekannte Endungen werden nur auf Markup geprueft.
    """
    with pfad.open("rb") as fh:
        kopf = fh.read(4096)
    if not kopf:
        raise UnerwarteterInhalt(f"Antwort ist keine {endung}-Datei: leere Antwort.")
    pruefung = _PRUEFUNG.get(endung.lower(), _pruefe_text)
    # Textformate duerfen mit einem BOM und Leerraum beginnen. Die Pruefungen der
    # Binaerformate vertragen das Abschneiden, weil ihre Kennung nicht mit Leerraum beginnt.
    anfang = kopf.removeprefix(codecs.BOM_UTF8).lstrip()
    if (grund := pruefung(pfad, anfang)):
        raise UnerwarteterInhalt(
            f"Antwort ist keine {endung}-Datei: {grund}. Anfang der Antwort: {kopf[:80]!r}")


# --------------------------------------------------------------------------- Abruf
def _seite(roh: bytes, was: str) -> dict:
    """Liest eine Seite eines blaetternden Dienstes und weist Fehlerantworten zurueck."""
    try:
        seite = json.loads(roh)
    except ValueError as fehler:
        raise UnerwarteterInhalt(
            f"{was} ist kein JSON: {fehler}. Anfang der Antwort: {roh[:80]!r}") from fehler
    if not isinstance(seite, dict) or "error" in seite:
        raise UnerwarteterInhalt(
            f"{was} ist ein Fehlerobjekt statt Daten. Anfang der Antwort: {roh[:80]!r}")
    return seite


def _folgeseite(url: str) -> list:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as resp:
        # Die letzte Seite kommt je nach Dienst ohne das Feld oder mit einer leeren Liste.
        return _seite(resp.read(), "Die Folgeseite").get("features") or []


def _folgeseiten_wfs(url: str, schritt: int) -> Iterator[list]:
    """Manche WFS geben hoechstens 5000 Objekte ab und blaettern ueber startIndex, in
    festen Schritten."""
    index = schritt
    while weitere := _folgeseite(f"{url}&maxFeatures={schritt}&startIndex={index}"):
        print(f"       + {len(weitere)} weitere ab Index {index}")
        yield weitere
        index += schritt


def _folgeseiten_arcgis(url: str, schritt: int, schon_geladen: int) -> Iterator[list]:
    """ArcGIS-Dienste geben hoechstens maxRecordCount Objekte je Anfrage heraus und
    blaettern ueber resultOffset. Ohne dieses Blaettern kaeme ein Bruchteil der Daten
    zurueck, und zwar ohne jede Fehlermeldung - derselbe stille Abschnitt wie beim
    5000er-Limit von Solothurn."""
    offset = schon_geladen
    while weitere := _folgeseite(f"{url}&resultOffset={offset}&resultRecordCount={schritt}"):
        print(f"       + {len(weitere)} weitere ab Offset {offset}")
        yield weitere
        offset += len(weitere)


def _blaettere(src: dict, teil: Path) -> None:
    """Haengt an die erste Seite alle Folgeseiten an, bis der Dienst nichts mehr liefert."""
    wfs = src.get("paging") if Path(src["file"]).suffix == ".json" else None
    arcgis = src.get("arcgis_paging")
    if not (wfs or arcgis):
        return
    daten = _seite(teil.read_bytes(), "Die erste Seite")
    if not isinstance(daten.get("features"), list):
        raise UnerwarteterInhalt("Die erste Seite traegt keine Liste 'features'.")
    if wfs:
        for weitere in _folgeseiten_wfs(src["url"], wfs):
            daten["features"].extend(weitere)
    if arcgis:
        for weitere in _folgeseiten_arcgis(src["url"], arcgis, len(daten["features"])):
            daten["features"].extend(weitere)
    teil.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")


def _hole(src: dict, target: Path) -> None:
    """Laedt eine Quelle vollstaendig und legt sie erst dann unter ihrem Namen ab.

    Abruf, Inhaltspruefung und Blaettern laufen auf einer Nebendatei. Scheitert einer
    der Schritte, bleibt keine halbe oder falsche Datei liegen, die der naechste Lauf
    als "existiert bereits" ueberspringt.
    """
    teil = target.with_name(target.name + ".part")
    try:
        req = urllib.request.Request(src["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=300) as resp, teil.open("wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
        pruefe_inhalt(teil, target.suffix)
        _blaettere(src, teil)
        teil.replace(target)
    finally:
        teil.unlink(missing_ok=True)


def download(key: str, force: bool = False) -> dict:
    src = SOURCES[key]
    target = RAW / src["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if force or not target.exists():
        print(f"[get ] {key}: {src['url']}")
        _hole(src, target)
    else:
        print(f"[skip] {key}: {target.name} existiert bereits")

    # GML traegt eine schemaLocation, die GDAL beim Lesen ueber HTTPS nachladen will.
    # Hinter einer Firewall mit eigenem Wurzelzertifikat scheitert das, und zwar mit
    # einer SSL-Meldung, die nichts mit der eigentlichen Datei zu tun hat. Das Schema
    # steht ohnehin im Dokument - also die Referenz entfernen. Auf Bytes, damit Kodierung
    # und Zeilenenden der Datei unveraendert bleiben.
    if target.suffix == ".gml":
        roh = target.read_bytes()
        ohne = re.sub(rb'\s+xsi:schemaLocation="[^"]*"', b"", roh)
        if ohne != roh:
            target.write_bytes(ohne)

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
    # endgueltiger Ausfall haelt die uebrigen Quellen nicht auf. Eine Antwort mit
    # falschem Inhalt (Login-Seite, Fehlerbericht) zaehlt wie ein Netzfehler.
    fehler: dict[str, str] = {}
    for key in keys:
        for versuch in range(1, VERSUCHE + 1):
            try:
                manifest[key] = download(key, force=force)
                print(f"       {manifest[key]['bytes']:,} bytes")
                fehler.pop(key, None)
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    UnerwarteterInhalt) as ausnahme:
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
