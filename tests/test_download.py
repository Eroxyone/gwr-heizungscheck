"""Download der Rohdaten: Inhaltspruefung, Wiederholung und Blaettern, ohne Netz.

Ein erfundener Dienst (geodienst.example) antwortet aus einem Woerterbuch je URL. So
laesst sich nachstellen, was am 22.11.2026 geschah: Ein Geodienst verlangte eine
Anmeldung, andere antworten in dieser Lage mit Status 200 und einer HTML-Seite.
"""
from __future__ import annotations

import io
import json
import zipfile

import pytest

import config
import download

BASIS = "https://geodienst.example/wfs?layer=sonden"

LOGIN_SEITE = b"<!DOCTYPE html>\n<html><head><title>Anmeldung</title></head><body>Login</body></html>"
WFS_FEHLER = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
              b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
              b"<ows:Exception exceptionCode=\"NoApplicableCode\"/></ows:ExceptionReport>")
WMS_FEHLER = b'<?xml version="1.0"?><ServiceExceptionReport><ServiceException/></ServiceExceptionReport>'
ARCGIS_FEHLER = b'{"error": {"code": 499, "message": "Token Required", "details": []}}'
GML = (b'<?xml version="1.0" encoding="UTF-8"?>\n<!-- Abgabe -->\n'
       b'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"'
       b' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
       b' xsi:schemaLocation="http://www.opengis.net/wfs/2.0 https://geodienst.example/wfs.xsd">'
       b"</wfs:FeatureCollection>")


def _zip(**dateien: bytes) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as zf:
        for name, inhalt in dateien.items():
            zf.writestr(name, inhalt)
    return puffer.getvalue()


def _seite(*nummern: int) -> bytes:
    return json.dumps({"type": "FeatureCollection",
                       "features": [{"type": "Feature", "properties": {"nr": n}} for n in nummern]}).encode()


@pytest.fixture
def dienst(monkeypatch, tmp_path):
    """Ersetzt Netz, Quellenliste und Datenverzeichnis. Gibt die Quellenliste, die
    Antworten je URL und das Protokoll der Abrufe zurueck."""
    quellen: dict[str, dict] = {}
    antworten: dict[str, bytes | list[bytes]] = {}
    abrufe: list[str] = []

    def urlopen(req, timeout=None):
        abrufe.append(req.full_url)
        antwort = antworten[req.full_url]
        # Eine Liste steht fuer aufeinanderfolgende Antworten derselben URL.
        return io.BytesIO(antwort.pop(0) if isinstance(antwort, list) else antwort)

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(download.time, "sleep", lambda sekunden: None)
    monkeypatch.setattr(download, "RAW", tmp_path)
    monkeypatch.setattr(download, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(download, "SOURCES", quellen)
    monkeypatch.setattr(config, "QUELLEN", quellen)
    return quellen, antworten, abrufe


def _quelle(datei: str, **optionen) -> dict:
    return {"url": BASIS, "file": datei, "desc": "erfundene Quelle", **optionen}


# --------------------------------------------------------------------------- Inhaltspruefung

@pytest.mark.parametrize(("endung", "inhalt"), [
    (".zip", _zip(**{"a.csv": b"x;y\n1;2\n"})),
    (".gpkg", b"SQLite format 3\x00" + bytes(84)),
    (".parquet", b"PAR1" + bytes(16) + b"PAR1"),
    (".json", b'{"type": "FeatureCollection", "features": []}'),
    (".json", b'\xef\xbb\xbf\n  {"type": "FeatureCollection", "features": []}'),      # BOM und Leerraum
    (".geojson", b"[]"),
    (".gml", GML),
    (".gml", b'<gml:FeatureCollection xmlns:gml="http://www.opengis.net/gml"/>'),     # ohne XML-Deklaration
    (".xml", b'<?xml version="1.0"?><!DOCTYPE daten SYSTEM "daten.dtd"><daten/>'),
    (".csv", b"\xef\xbb\xbfxtf_id,Address,PostCode\n1,Musterweg 1,9000\n"),
    (".txt", b"irgendein Text"),                                                       # unbekannte Endung
])
def test_inhalt_im_erwarteten_format_wird_angenommen(tmp_path, endung, inhalt):
    datei = tmp_path / "antwort.part"
    datei.write_bytes(inhalt)
    download.pruefe_inhalt(datei, endung)


@pytest.mark.parametrize(("endung", "inhalt", "grund"), [
    # Die Login-Seite, unter jeder Endung
    (".zip", LOGIN_SEITE, "kein vollstaendiges ZIP-Archiv"),
    (".gpkg", LOGIN_SEITE, "keine SQLite-Datei"),
    (".parquet", LOGIN_SEITE, "keine vollstaendige Parquet-Datei"),
    (".json", LOGIN_SEITE, "beginnt nicht mit { oder ["),
    (".gml", LOGIN_SEITE, "Wurzelelement <html>"),
    (".gml", b"<html><body>Wartung</body></html>", "Wurzelelement <html>"),
    (".csv", LOGIN_SEITE, "beginnt mit Markup"),
    (".txt", LOGIN_SEITE, "beginnt mit Markup"),
    # Fehlerberichte, die selbst gueltiges XML oder JSON sind
    (".gml", WFS_FEHLER, "Wurzelelement <ExceptionReport>"),
    (".gml", WMS_FEHLER, "Wurzelelement <ServiceExceptionReport>"),
    (".json", WFS_FEHLER, "beginnt nicht mit { oder ["),
    (".json", ARCGIS_FEHLER, "Fehlerobjekt des Dienstes"),
    (".gml", b'{"error": "kein XML"}', "kein XML"),
    # Abgebrochene Uebertragung
    (".zip", _zip(**{"a.csv": b"x;y\n1;2\n"})[:40], "kein vollstaendiges ZIP-Archiv"),
    (".parquet", b"PAR1" + bytes(16), "keine vollstaendige Parquet-Datei"),
    (".json", b"", "leere Antwort"),
    (".zip", b"", "leere Antwort"),
])
def test_fehlerseite_oder_abgebrochene_datei_wird_zurueckgewiesen(tmp_path, endung, inhalt, grund):
    datei = tmp_path / "antwort.part"
    datei.write_bytes(inhalt)
    with pytest.raises(download.UnerwarteterInhalt, match=grund.replace("[", r"\[").replace("{", r"\{")):
        download.pruefe_inhalt(datei, endung)


# --------------------------------------------------------------------------- Abruf

def test_login_seite_wird_nicht_zur_zieldatei(dienst, tmp_path):
    quellen, antworten, _ = dienst
    quellen["sonden"] = _quelle("kanton/sonden.gml")
    antworten[BASIS] = LOGIN_SEITE

    with pytest.raises(download.UnerwarteterInhalt, match="keine .gml-Datei"):
        download.download("sonden")
    # Weder die Zieldatei noch die Nebendatei bleibt liegen
    assert list((tmp_path / "kanton").iterdir()) == []


def test_vorhandene_rohdatei_ueberlebt_eine_fehlerseite(dienst, tmp_path):
    # --force bei einem Dienst, der inzwischen eine Anmeldung verlangt: Der lokale Abzug
    # ist dann der einzige, den es noch gibt.
    quellen, antworten, _ = dienst
    quellen["sonden"] = _quelle("sonden.json")
    antworten[BASIS] = LOGIN_SEITE
    (tmp_path / "sonden.json").write_bytes(_seite(1, 2))

    with pytest.raises(download.UnerwarteterInhalt):
        download.download("sonden", force=True)
    assert (tmp_path / "sonden.json").read_bytes() == _seite(1, 2)
    assert not (tmp_path / "sonden.json.part").exists()


def test_gueltige_antwort_wird_abgelegt_und_im_manifest_gefuehrt(dienst, tmp_path):
    quellen, antworten, abrufe = dienst
    quellen["sonden"] = _quelle("sonden.gml")
    antworten[BASIS] = GML

    assert download.main(["download.py", "sonden"]) == 0
    assert abrufe == [BASIS]
    abgelegt = (tmp_path / "sonden.gml").read_bytes()
    # Die schemaLocation wird entfernt, der Rest bleibt
    assert b"schemaLocation" not in abgelegt
    assert abgelegt == GML.replace(
        b' xsi:schemaLocation="http://www.opengis.net/wfs/2.0 https://geodienst.example/wfs.xsd"', b"")
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sonden"]["bytes"] == len(abgelegt)
    assert not (tmp_path / "sonden.gml.part").exists()


def test_fehlerseite_zaehlt_als_gescheiterter_abruf(dienst, tmp_path):
    # Drei Versuche, dann Exit 1. Die zweite Quelle wird trotzdem geladen.
    quellen, antworten, abrufe = dienst
    quellen["gesperrt"] = {**_quelle("gesperrt.json"), "url": BASIS + "&gesperrt"}
    quellen["offen"] = _quelle("offen.json")
    antworten[BASIS + "&gesperrt"] = LOGIN_SEITE
    antworten[BASIS] = _seite(1)

    assert download.main(["download.py"]) == 1
    assert abrufe == [BASIS + "&gesperrt"] * download.VERSUCHE + [BASIS]
    assert not (tmp_path / "gesperrt.json").exists()
    assert (tmp_path / "offen.json").exists()
    assert list(json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))) == ["offen"]


def test_zweiter_versuch_mit_gueltiger_antwort_gelingt(dienst, tmp_path):
    quellen, antworten, abrufe = dienst
    quellen["sonden"] = _quelle("sonden.json")
    antworten[BASIS] = [LOGIN_SEITE, _seite(1, 2)]

    assert download.main(["download.py", "sonden"]) == 0
    assert abrufe == [BASIS, BASIS]
    assert (tmp_path / "sonden.json").read_bytes() == _seite(1, 2)


# --------------------------------------------------------------------------- Blaettern

def _nummern(datei) -> list[int]:
    return [f["properties"]["nr"] for f in json.loads(datei.read_text(encoding="utf-8"))["features"]]


def test_wfs_blaettert_in_festen_schritten_bis_zur_leeren_seite(dienst, tmp_path):
    quellen, antworten, abrufe = dienst
    quellen["sonden"] = _quelle("sonden.json", paging=2)
    antworten[BASIS] = _seite(1, 2)
    antworten[BASIS + "&maxFeatures=2&startIndex=2"] = _seite(3, 4)
    antworten[BASIS + "&maxFeatures=2&startIndex=4"] = _seite(5)
    antworten[BASIS + "&maxFeatures=2&startIndex=6"] = _seite()

    download.download("sonden")
    assert _nummern(tmp_path / "sonden.json") == [1, 2, 3, 4, 5]
    assert len(abrufe) == 4


def test_arcgis_blaettert_ab_der_zahl_der_erhaltenen_objekte(dienst, tmp_path):
    # Der Dienst gibt drei Objekte je Anfrage ab, obwohl vier verlangt sind. Der naechste
    # Abruf beginnt deshalb bei 3 und nicht bei 4.
    quellen, antworten, abrufe = dienst
    quellen["kessel"] = _quelle("kessel.json", arcgis_paging=4)
    antworten[BASIS] = _seite(1, 2, 3)
    antworten[BASIS + "&resultOffset=3&resultRecordCount=4"] = _seite(4, 5, 6)
    antworten[BASIS + "&resultOffset=6&resultRecordCount=4"] = _seite(7)
    antworten[BASIS + "&resultOffset=7&resultRecordCount=4"] = b'{"features": []}'

    download.download("kessel")
    assert _nummern(tmp_path / "kessel.json") == [1, 2, 3, 4, 5, 6, 7]
    assert len(abrufe) == 4


@pytest.mark.parametrize("folgeseite", [LOGIN_SEITE, ARCGIS_FEHLER])
def test_fehler_auf_einer_folgeseite_hinterlaesst_keine_halbe_datei(dienst, tmp_path, folgeseite):
    # Bliebe die erste Seite unter dem Zielnamen liegen, uebersprange der naechste Lauf
    # sie als "existiert bereits", und zwei Drittel der Objekte fehlten ohne Meldung.
    quellen, antworten, _ = dienst
    quellen["kessel"] = _quelle("kessel.json", arcgis_paging=3)
    antworten[BASIS] = _seite(1, 2, 3)
    antworten[BASIS + "&resultOffset=3&resultRecordCount=3"] = folgeseite

    with pytest.raises(download.UnerwarteterInhalt, match="Die Folgeseite"):
        download.download("kessel")
    assert list(tmp_path.iterdir()) == []
