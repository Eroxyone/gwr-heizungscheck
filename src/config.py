"""Zentrale Konfiguration: Pfade, Kantone, Quellen, Codelisten.

Einziger Ort, an dem Pfade und Quell-URLs stehen. Alle anderen Module importieren von hier.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# ---------------------------------------------------------------- TLS
# Manche kantonalen Geodienste laufen hinter einer Firewall, die TLS aufbricht und mit
# einem eigenen Wurzelzertifikat neu signiert. Dieses Zertifikat liegt im Windows-Zert-
# speicher, nicht in dem von Python - die Folge ist ein CERTIFICATE_VERIFY_FAILED, das
# nichts mit dem Dienst zu tun hat. truststore legt den Systemspeicher unter Python;
# damit bleibt die Pruefung eingeschaltet, statt sie abzuschalten.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - ohne truststore gilt der Python-Speicher
    pass

# Datenverzeichnis. Standard ist data/ im Repo. GWR_DATA_DIR legt es an einen anderen Ort,
# etwa auf ein Volume, wenn die Pipeline im Container laeuft. Rohdaten, Snapshots und die
# Datenbank liegen darunter; die Labels gehoeren zum Repo und bleiben dort.
DATA = Path(os.environ.get("GWR_DATA_DIR") or ROOT / "data").resolve()
RAW = DATA / "raw"
SNAPSHOTS = DATA / "snapshots"
PROCESSED = DATA / "processed"
LABELS = ROOT / "data" / "labels"
SQL = ROOT / "sql"
REPORTS = ROOT / "reports"
DB = PROCESSED / "gwr.duckdb"

USER_AGENT = "gwr-heizungscheck/0.2 (Validierungsprojekt, Kontakt via GitHub)"

# --------------------------------------------------------------------------- Kantone
# Reihenfolge nach BFS-Kantonsnummer. Der Kuerzel ist zugleich der Dateiname beim BFS.
KANTONE: dict[str, str] = {
    "ZH": "Zürich",        "BE": "Bern",             "LU": "Luzern",
    "UR": "Uri",           "SZ": "Schwyz",           "OW": "Obwalden",
    "NW": "Nidwalden",     "GL": "Glarus",           "ZG": "Zug",
    "FR": "Freiburg",      "SO": "Solothurn",        "BS": "Basel-Stadt",
    "BL": "Basel-Landschaft", "SH": "Schaffhausen",  "AR": "Appenzell Ausserrhoden",
    "AI": "Appenzell Innerrhoden", "SG": "St. Gallen", "GR": "Graubünden",
    "AG": "Aargau",        "TG": "Thurgau",          "TI": "Tessin",
    "VD": "Waadt",         "VS": "Wallis",           "NE": "Neuenburg",
    "GE": "Genf",          "JU": "Jura",
}

# Grossregionen des BFS, fuer die Aggregation im Gold-Layer
GROSSREGION: dict[str, str] = {
    "GE": "Genferseeregion", "VD": "Genferseeregion", "VS": "Genferseeregion",
    "BE": "Espace Mittelland", "FR": "Espace Mittelland", "SO": "Espace Mittelland",
    "NE": "Espace Mittelland", "JU": "Espace Mittelland",
    "BS": "Nordwestschweiz", "BL": "Nordwestschweiz", "AG": "Nordwestschweiz",
    "ZH": "Zürich",
    "GL": "Ostschweiz", "SH": "Ostschweiz", "AR": "Ostschweiz", "AI": "Ostschweiz",
    "SG": "Ostschweiz", "GR": "Ostschweiz", "TG": "Ostschweiz",
    "LU": "Zentralschweiz", "UR": "Zentralschweiz", "SZ": "Zentralschweiz",
    "OW": "Zentralschweiz", "NW": "Zentralschweiz", "ZG": "Zentralschweiz",
    "TI": "Tessin",
}

GWR_URL = "https://public.madd.bfs.admin.ch/{kt}.zip"

# Datei im Kantons-ZIP, die wir tatsaechlich brauchen
GWR_DATEIEN = {
    "gebaeude": "gebaeude_batiment_edificio.csv",
    "eingang": "eingang_entree_entrata.csv",
    "kodes": "kodes_codes_codici.csv",
}

# --------------------------------------------------------------------------- Sonstige Quellen
QUELLEN = {
    # Der Zuercher Detailstrang rechnet auf dem Rohexport des Kantons, nicht auf den
    # Snapshots: build_db.py liest die CSV aus data/raw/gwr_zh/.
    "gwr_zh": {
        "url": GWR_URL.format(kt="zh"),
        "file": "gwr_zh.zip",
        "desc": "GWR Kanton ZH, Rohexport fuer den Zuercher Detailstrang (BFS)",
    },
    "baugesuche_csv": {
        "url": "https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006183.csv",
        "file": "baugesuche_zh.csv",
        "desc": "Baugesuche im Kanton ZH, Volltabelle (Statistisches Amt ZH)",
    },
    "baugesuche_gpkg": {
        "url": "https://daten.statistik.zh.ch/ogd/daten/ressourcen/KTZH_00002982_00006403.gpkg",
        "file": "baugesuche_zh_geo.gpkg",
        "desc": "Georeferenzierte Baugesuche im Kanton ZH ab 2025 (Statistisches Amt ZH)",
    },
    "epa_csv": {
        "url": "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen"
               "/elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip",
        "file": "epa.zip",
        "desc": "Elektrizitaetsproduktionsanlagen CH (BFE), vollstaendiges STAC-Asset",
    },
    "erdwaermesonden_zh": {
        "url": "https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0"
               "&Request=GetFeature&TypeName=ms:erdwaermesonden&outputFormat=geojson",
        "file": "waermenutzung_zh/erdwaermesonden.json",
        "desc": "Erdwaermesonden Kanton ZH (AWEL), bewilligte Bohrungen",
    },
    "erdregister_zh": {
        "url": "https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0"
               "&Request=GetFeature&TypeName=ms:erdregister&outputFormat=geojson",
        "file": "waermenutzung_zh/erdregister.json",
        "desc": "Erdregister Kanton ZH (AWEL)",
    },
    "grundwasserfassung_zh": {
        "url": "https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0"
               "&Request=GetFeature&TypeName=ms:grundwasserfassung-waermenutzung&outputFormat=geojson",
        "file": "waermenutzung_zh/grundwasserfassung-waermenutzung.json",
        "desc": "Grundwasserfassungen mit Waermenutzung, Kanton ZH (AWEL)",
    },
    "quellfassung_zh": {
        "url": "https://maps.zh.ch/wfs/AwelGSWaermewwwZHWFS?Service=WFS&Version=2.0.0"
               "&Request=GetFeature&TypeName=ms:quellfassung-waermenutzung&outputFormat=geojson",
        "file": "waermenutzung_zh/quellfassung-waermenutzung.json",
        "desc": "Quellfassungen mit Waermenutzung, Kanton ZH (AWEL)",
    },
    "erdwaermesonden_be": {
        "url": "https://geofiles.be.ch/geoportal/pub/download/ERDSOND/erdsond.gpkg.zip",
        "file": "waermenutzung_be/erdsond.gpkg.zip",
        "entpacken": "waermenutzung_be",
        "desc": "Erdwaermesonden Kanton BE (AGI), mit Bewilligungsdatum und Status",
    },
    "erdwaermesonden_tg": {
        "url": "https://ows.geo.tg.ch/geofy_access_proxy/erdwaerme?Service=WFS&Version=2.0.0"
               "&Request=GetFeature&TypeName=ms:erdwaerme_erdwaermesondenbohrungen"
               "&outputFormat=geojson",
        "file": "waermenutzung_weitere/TG_erdwaermesonden.json",
        "desc": "Erdwaermesondenbohrungen Kanton TG, mit Bohrdatum und Status",
    },
    "erdwaermesonden_sh": {
        "url": "https://wfs.geo.sh.ch/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature"
               "&typeName=sh.energie.erdsonden.waermenutzungen_erdwaermesonden"
               "&outputFormat=application/json",
        "file": "waermenutzung_weitere/SH_erdwaermesonden.json",
        "desc": "Erdwaermesonden Kanton SH. Braucht WFS 1.1.0 und liefert WGS84 statt LV95",
    },
    "erdwaermesonden_ur": {
        "url": "https://geo.ur.ch/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
               "&TYPENAMES=energie:ur033_konzessionen_erdsonden&outputFormat=application/json",
        "file": "waermenutzung_weitere/UR_erdsonden.json",
        "desc": "Konzessionen Erdsonden Kanton UR. Nur bewilligt, nicht nachweislich gebohrt",
    },
    "erdwaermesonden_so": {
        "url": "https://geo.so.ch/api/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature"
               "&typeName=ch.so.afu.erdwaerme.sonde&outputFormat=application/json",
        "file": "waermenutzung_weitere/SO_erdwaermesonden.json",
        "desc": "Erdwaermesonden Kanton SO, mit Bewilligungsdatum. Abgabe auf 5000 Objekte "
                "begrenzt, wird beim Download geblaettert",
        "paging": 5000,
    },
    # ---------------------------------------------------------------- Gegenbelege
    # Die uebrigen Quellen zeigen, dass eine Waermepumpe da ist. Diese zeigen, ob die
    # alte fossile Heizung noch laeuft. Zug fuehrt seinen Tankkataster getrennt nach
    # "in Betrieb" und "ausser Betrieb", die Unterscheidung liegt in der Layerwahl
    # statt in einem Statusfeld.
    "tank_zg_tank_gebaeude_in_betrieb": {
        "url": "https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0"
               "&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_in_betrieb",
        "file": "waermenutzung_weitere/ZG_tank_gebaeude_in_betrieb.gml",
        "desc": "Tankkataster Kanton ZG: Tanks im oder am Gebaeude, in Betrieb (5214)",
    },
    "tank_zg_tank_gebaeude_ausser_betrieb": {
        "url": "https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0"
               "&REQUEST=GetFeature&typeName=zg_tank_im_am_gebaude_ausser_betrieb",
        "file": "waermenutzung_weitere/ZG_tank_gebaeude_ausser_betrieb.gml",
        "desc": "Tankkataster Kanton ZG: Tanks im oder am Gebaeude, ausser Betrieb (2705)",
    },
    "tank_zg_tank_erdverlegt_in_betrieb": {
        "url": "https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0"
               "&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_in_betrieb",
        "file": "waermenutzung_weitere/ZG_tank_erdverlegt_in_betrieb.gml",
        "desc": "Tankkataster Kanton ZG: erdverlegte Tanks, in Betrieb (1023)",
    },
    "tank_zg_tank_erdverlegt_ausser_betrieb": {
        "url": "https://services.geo.zg.ch/ows/tankanlagen?SERVICE=WFS&VERSION=1.1.0"
               "&REQUEST=GetFeature&typeName=zg_erdverlegter_tank_ausser_betrieb",
        "file": "waermenutzung_weitere/ZG_tank_erdverlegt_ausser_betrieb.gml",
        "desc": "Tankkataster Kanton ZG: erdverlegte Tanks, ausser Betrieb (613)",
    },
    "waermeerzeuger_ge": {
        # Der Kanton Genf fuehrt hier je Gebaeude den tatsaechlichen Waermeerzeuger,
        # mit EGID, Anlagenart, Energiequelle und Datenstand. Anders als der
        # Kesselkataster (SCANE_CHAUDIERE) kennt dieser Layer auch "Pompe a chaleur"
        # und "Echangeur de chaleur (CAD)". Im Kesselkataster sieht ein an die
        # Fernwaerme angeschlossenes Gebaeude aus wie "nicht erfasst".
        "url": "https://vector.sitg.ge.ch/arcgis/rest/services"
               "/OCEN_INSTAL_PROD_CHALEUR_PUB/FeatureServer/0/query"
               "?where=1%3D1&outFields=*&returnGeometry=false&f=geojson",
        "file": "waermenutzung_weitere/GE_waermeerzeuger.json",
        "desc": "Waermeerzeuger je Gebaeude Kanton GE, mit EGID, Anlagenart und "
                "Energiequelle (inkl. Waermepumpe und Fernwaerme)",
        "arcgis_paging": 4000,
    },
    "feuerung_ge_relation": {
        # Eine Zentralheizung versorgt oft mehrere Gebaeude. Der Kesselkataster traegt
        # nur die EGID des Heizraums, diese Tabelle liefert die versorgten Gebaeude.
        # CODE_ICF verbindet beide Seiten.
        "url": "https://vector.sitg.ge.ch/arcgis/rest/services"
               "/SCANE_RELATION_BATI_CHAUDIERE/FeatureServer/0/query"
               "?where=1%3D1&outFields=*&returnGeometry=false&f=geojson",
        "file": "waermenutzung_weitere/GE_kessel_gebaeude.json",
        "desc": "Beziehung Kessel zu versorgten Gebaeuden, Kanton GE",
        "arcgis_paging": 2000,
    },
    "feuerung_ge": {
        # Zeigt, ob am Gebaeude noch ein Oel- oder Gaskessel in Betrieb ist, mit EGID,
        # Zustand und Baujahr. ArcGIS-Dienst, gibt hoechstens 4000 Objekte je Anfrage
        # heraus.
        "url": "https://vector.sitg.ge.ch/arcgis/rest/services/SCANE_CHAUDIERE"
               "/FeatureServer/0/query?where=1%3D1&outFields=*&returnGeometry=false"
               "&f=geojson",
        "file": "waermenutzung_weitere/GE_feuerungen.json",
        "desc": "Feuerungskataster Kanton GE, 55378 Kessel mit EGID, Brennstoff, "
                "Betriebszustand und Baujahr",
        "arcgis_paging": 4000,
    },
    "luftwasserwp_lu": {
        # Luzern fuehrt als einziger Kanton auch die Luft-Wasser-Waermepumpen, die in
        # allen Sondenkatastern fehlen. Laut Datensatz koennen die Anlagen "bereits
        # erstellt oder noch in Planung" sein. Er wird deshalb wie eine Bewilligung
        # behandelt und nicht wie ein Ausfuehrungsnachweis.
        "url": "https://public.geo.lu.ch/ogd/services/managed/LUFWAWPO_DS_V1_MP"
               "/MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature"
               "&typeNames=esri%3ALuft-Wasser-W%C3%A4rmepumpen__geplante_und_bewilligte_Anlagen"
               "&outputFormat=GEOJSON",
        "file": "waermenutzung_weitere/LU_luftwasserwaermepumpen.json",
        "desc": "Luft-Wasser-Waermepumpen Kanton LU, geplante und bewilligte Anlagen",
    },
    "erdwaermesonden_zg": {
        # Der einzige Kanton, der zu einem Teil seiner Anlagen die EGID mitliefert.
        # Daran laesst sich die eigene raeumliche Zuordnung gegen eine amtliche
        # Referenz messen (reports/zuordnung_zg.md). GeoPackage direkt aus dem
        # Datenrepository, kein WFS noetig.
        "url": "https://services.geo.zg.ch/datarepo/Erdwaerme/geopackage/"
               "Erdwaermenutzung.gpkg",
        "file": "waermenutzung_weitere/ZG_erdwaermenutzung.gpkg",
        "desc": "Erdwaermesondenanlagen Kanton ZG, mit EGID, Bohrdatum, Bewilligungs-"
                "datum, Verwendungszweck und Heizleistung",
    },
    "grundwasserwp_ur": {
        "url": "https://geo.ur.ch/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature"
               "&typeName=energie%3Aur031_konzessionen_grundwasserwaermepumpen"
               "&outputFormat=application%2Fjson",
        "file": "waermenutzung_weitere/UR_grundwasserwaermepumpen.json",
        "desc": "Konzessionen Grundwasserwaermepumpen Kanton UR",
    },
    "waermepumpen_sg": {
        # Kein Sonden-, sondern ein Anlagenregister: Jede Zeile ist eine thermische
        # Zentrale mit Anlageart ("Waermepumpe"), Anlagetyp ("Heizung") und
        # Erstellungsjahr. Der Dienst braucht WFS 2.0.0 mit TYPENAMES, Version 1.1.0
        # antwortet mit HTTP 500.
        "url": "https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0"
               "&REQUEST=GetFeature&TYPENAMES=geoportal%3Aq352_thermischezentralen",
        "file": "waermenutzung_weitere/SG_thermischezentralen.gml",
        "desc": "Thermische Zentralen Kanton SG, Waermepumpen mit Erstellungsjahr, "
                "Anlageart, Erdsondenzahl und -laenge",
    },
    "erdwaermesonden_ai": {
        "url": "https://www.geoportal.ch/services/wfs?SERVICE=WFS&VERSION=2.0.0"
               "&REQUEST=GetFeature&TYPENAMES=geoportal%3Af211_ai_erdwaermesonden",
        "file": "waermenutzung_weitere/AI_erdwaermesonden.gml",
        "desc": "Erdwaermesondenbohrungen Kanton AI, mit Erstelljahr und Bohrzweck",
    },
    "erdwaermesonden_sz": {
        # Der Kanton Schwyz fuehrt zwei WFS-Adressen. wfs.geo.sz.ch liefert einen
        # vollstaendigen Capabilities-Katalog, beantwortet aber jedes GetFeature erneut
        # mit den Capabilities. Nur der mapserv_proxy gibt Daten heraus.
        "url": "https://map.geo.sz.ch/mapserv_proxy?SERVICE=WFS&VERSION=1.1.0"
               "&REQUEST=GetFeature"
               "&typeName=ms:ch.sz.a034c.waermenutzung.erdwaermeanlage.erdwaermesonde",
        "file": "waermenutzung_weitere/SZ_erdwaermesonden.gml",
        "desc": "Erdwaermesonden Kanton SZ, mit Bewilligungsdatum und Bohrtiefe",
    },
    "erdwaermesonden_bl": {
        # Kein Anlagen-, sondern ein Bohrregister: jede Zeile ist eine ausgefuehrte
        # Bohrung mit Jahr. Das ist ein staerkerer Beleg als eine Bewilligung.
        "url": "https://geowms.bl.ch/?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature"
               "&typeName=ms:grundwasser_erdsonden",
        "file": "waermenutzung_weitere/BL_erdsonden.gml",
        "desc": "Erdsondenbohrungen Kanton BL, mit Bohrjahr, Tiefe und Gemeinde",
    },
    "erdwaermesonden_lu": {
        "url": "https://public.geo.lu.ch/ogd/services/managed/EWNUTZXX_COL_V3_MP"
               "/MapServer/WFSServer?service=WFS&version=2.0.0&request=GetFeature"
               "&typeNames=esri%3AErdw%C3%A4rmenutzung__Anlagen&outputFormat=GEOJSON",
        "file": "waermenutzung_weitere/LU_erdwaermesonden.json",
        "desc": "Erdwaermenutzung Kanton LU, mit Bewilligungs- und Realisierungsdatum, "
                "Betriebszustand und Nutzungszweck",
    },
    "erdwaermesonden_ge": {
        "url": "https://ge.ch/sitg/geodata/SITG/OPENDATA/GOL_SONDES_GEOTH-CSV.zip",
        "file": "waermenutzung_weitere/GE_sonden.zip",
        "desc": "Sondes geothermiques verticales Kanton GE, CSV mit LV95 und Realisierungsdatum",
    },
    "epa_egid_csv": {
        "url": "https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen"
               "/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip",
        "file": "epa_egid.zip",
        "desc": "Elektrizitaetsproduktionsanlagen CH (BFE), Variante mit EGID-Spalte, "
                "auf 100000 Zeilen gekuerzt. Nur als Referenz zur Pruefung des Abgleichs.",
    },
}

# --------------------------------------------------------------------------- Fachlogik
# Spalten, die in den Snapshot wandern. Bewusst schlank: der Snapshot soll woechentlich
# laufen koennen, ohne dass die Ablage explodiert.
SNAPSHOT_SPALTEN = [
    "EGID", "GDEKT", "GGDENR", "GGDENAME", "GKODE", "GKODN",
    "GSTAT", "GKAT", "GKLAS", "GBAUJ", "GAREA", "GASTW", "GANZWHG",
    "GWAERZH1", "GENH1", "GWAERSCEH1", "GWAERDATH1",
    "GWAERZW1", "GENW1", "GWAERSCEW1", "GWAERDATW1",
    "GEXPDAT",
]

# Die Eingangstabelle traegt die Adresse. Ohne sie laesst sich ein Baugesuch ausserhalb
# Zuerichs keinem Gebaeude zuordnen: Die meisten Amtsblatt-Mandanten liefern weder
# Koordinate noch Parzellengeometrie, sondern nur Strasse, Hausnummer und PLZ.
SNAPSHOT_SPALTEN_EINGANG = [
    "EGID", "EDID", "EGAID", "DEINR", "ESID", "STRNAME", "STRNAMK",
    "DPLZ4", "DPLZZ", "DPLZNAME", "DKODE", "DKODN", "DOFFADR", "DEXPDAT",
]

# ------------------------------------------------------------------------- Lizenzen
# Das Manifest fuehrt URL, Groesse, Pruefsumme und Zeitpunkt je Quelle, aber keine
# Lizenz. Die Lizenzen stammen aus der CKAN-Schnittstelle von opendata.swiss. Dort
# fuehrt jede Ressource einen von vier Standardtermen:
#
#   terms_open     Freie Nutzung
#   terms_by       Freie Nutzung, Quellenangabe Pflicht
#   terms_ask      Freie Nutzung, kommerzielle Nutzung nur mit Bewilligung
#   terms_by_ask   beides
#
# Nur die ersten beiden erlauben jede Art von Weitergabe ohne Rueckfrage. Abfrage vom
# 14.09.2026: Keine der verwendeten Quellen traegt terms_ask. Drei Kantone (SO, ZG,
# BL) belegen nur eine kantonsweite Regel, nicht die benutzte Ebene selbst.
LIZENZ_UNGEPRUEFT = "ungeprüft - vor einer Weitergabe klären"

# stufe: "belegt"      die benutzte Ebene ist selbst auf opendata.swiss gelistet
#        "kantonsweit" nur die allgemeine Regel des Kantonsportals ist belegt
LIZENZEN: dict[str, dict[str, str]] = {
    # --- Bund und Portale mit eigenen Nutzungsbedingungen
    "public.madd.bfs.admin.ch": {
        "lizenz": "GWR Stufe A: öffentlich zugängliche Daten, uneingeschränkt nutzbar",
        "stufe": "belegt", "beleg": "https://www.housing-stat.ch/de/madd/public.html"},
    "data.geo.admin.ch": {
        "lizenz": "Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt",
        "stufe": "belegt", "beleg": "https://www.geo.admin.ch/de/nutzungsbedingungen"},
    "daten.statistik.zh.ch": {
        "lizenz": "Opendata BY: freie Nutzung, Quellenangabe Pflicht, kommerziell erlaubt",
        "stufe": "belegt", "beleg": "https://www.zh.ch/de/politik-staat/opendata.html"},
    "vector.sitg.ge.ch": {
        "lizenz": "SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe",
        "stufe": "belegt",
        "beleg": "https://sitg.ge.ch/ressources/conditions-utilisation-donnees"},
    "ge.ch": {
        "lizenz": "SITG: Nutzung inkl. kommerzieller Verwertung mit Quellenangabe",
        "stufe": "belegt",
        "beleg": "https://sitg.ge.ch/ressources/conditions-utilisation-donnees"},

    # --- Kantonale Geodienste, Ebene selbst auf opendata.swiss gelistet
    "maps.zh.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Geoinformation Kanton Zürich, "
                 "Datensätze \"Erdwärmesonden\" und \"Wärmenutzung (Vektor)\""},
    "geofiles.be.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Amt für Geoinformation des Kantons Bern, "
                 "Datensatz \"Erdwärmesonden\""},
    "www.geoportal.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, AREG Kanton St. Gallen, Datensatz "
                 "\"Erdwärmesondenbohrungen\" - Appenzell Innerrhoden teilt dieses "
                 "Portal, ist aber nicht einzeln gelistet"},
    "wfs.geo.sh.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Amt für Geoinformation Kanton Schaffhausen, "
                 "Datensatz \"Energie Erdwärmesonden Kanton Schaffhausen\""},
    "map.geo.sz.ch": {
        "lizenz": "opendata.swiss terms_by: freie Nutzung, Quellenangabe Pflicht",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Amt für Geoinformation Kanton Schwyz, "
                 "Datensatz \"Wärmenutzungsanlagen\""},
    "geo.ur.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Lisag AG / Geoinformation Kanton Uri, Datensätze "
                 "\"Konzessionen Grundwasserwärmepumpen\" und \"Konzessionen Erdsonden\""},
    "public.geo.lu.ch": {
        "lizenz": "opendata.swiss terms_open: freie Nutzung, kommerziell erlaubt",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Dienststelle Umwelt und Energie Luzern, Datensätze "
                 "\"Erdwärmenutzung: Anlagen\" und \"Luft-Wasser-Wärmepumpen\""},
    "ows.geo.tg.ch": {
        "lizenz": "opendata.swiss terms_by: freie Nutzung, Quellenangabe Pflicht",
        "stufe": "belegt",
        "beleg": "opendata.swiss, Amt für Tiefbau und Geoinformation Thurgau, "
                 "Datensatz \"Erdsondenkarte\""},

    # --- Nur die kantonsweite Regel belegt, die benutzte Ebene selbst nicht gelistet
    "geo.so.ch": {
        "lizenz": "opendata.swiss terms_open für die Datensätze des Kantons Solothurn",
        "stufe": "kantonsweit",
        "beleg": "opendata.swiss, Kanton Solothurn - die Erdwärmesonden-Ebene selbst "
                 "ist dort nicht aufgeführt"},
    "services.geo.zg.ch": {
        "lizenz": "opendata.swiss terms_by für die Datensätze des Kantons Zug",
        "stufe": "kantonsweit",
        "beleg": "opendata.swiss, Kanton Zug - die Erdwärmesonden- und Tankebenen "
                 "selbst sind dort nicht aufgeführt"},
    "geowms.bl.ch": {
        "lizenz": "opendata.swiss terms_by für die Datensätze des Kantons Basel-Landschaft",
        "stufe": "kantonsweit",
        "beleg": "opendata.swiss, Kanton Basel-Landschaft - die Erdwärmesonden-Ebene "
                 "selbst ist dort nicht aufgeführt"},
}


def lizenz(schluessel: str) -> dict[str, str]:
    """Lizenzangabe zu einer Quelle, mit ehrlichem Rueckfall."""
    from urllib.parse import urlparse
    host = urlparse(QUELLEN[schluessel]["url"]).netloc
    return LIZENZEN.get(host, {"lizenz": LIZENZ_UNGEPRUEFT, "stufe": "ungeprüft",
                               "beleg": ""})
