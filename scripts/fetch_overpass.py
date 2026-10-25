#!/usr/bin/env python3
"""Descarga fruterías REALES de OpenStreetMap (Overpass API) para Madrid.

Ejecútalo desde una red con acceso a overpass-api.de (este sandbox está
bloqueado). Genera www/data/fruterias.js con datos reales OSM y, si no hay
fechas de apertura, asigna el año actual como apertura (el slider mostrará
solo el estado presente; la evolución temporal completa requiere históricos
del censo de data.madrid.es o snapshots anuales de OSM).

Uso: python3 scripts/fetch_overpass.py [--year 2026]
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "www" / "data" / "fruterias.js"
ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]

QUERY = """
[out:json][timeout:180];
area["name"="Madrid"]["boundary"="administrative"]["admin_level"="8"]->.a;
(
  node(area.a)["shop"="greengrocer"];
  way(area.a)["shop"="greengrocer"];
  node(area.a)["amenity"="marketplace"]["product"="fruit"];
);
out center tags;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    args = ap.parse_args()
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    last = None
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=data, headers={"User-Agent": "fruterias-madrid/1.0"})
            with urllib.request.urlopen(req, timeout=240) as r:
                osm = json.loads(r.read().decode())
            break
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"! {ep}: {e}")
    else:
        raise SystemExit(f"Overpass inaccesible: {last}")

    comercios, cid = [], 1
    for el in osm.get("elements", []):
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        t = el.get("tags", {})
        addr = ", ".join(x for x in [t.get("addr:street"), t.get("addr:housenumber")] if x)
        nombre = t.get("name") or t.get("brand") or "Frutería (sin nombre)"
        distrito = t.get("addr:district") or t.get("addr:suburb") or ""
        op = t.get("start_date") or t.get("opening_date")
        apertura = int(op[:4]) if op and op[:4].isdigit() else args.year
        comercios.append({
            "id": cid, "nombre": nombre[:80], "direccion": addr,
            "distrito": distrito, "codigo_distrito": "",
            "lat": round(lat, 6), "lon": round(lon, 6),
            "apertura": min(apertura, args.year), "cierre": None,
        })
        cid += 1

    payload = {
        "tipo_dato": "OSM_Overpass_real",
        "aviso": "Datos reales de OpenStreetMap (ODbL). Sin histórico de aperturas completas.",
        "anio_min": 1995, "anio_max": args.year,
        "comercios": comercios,
    }
    OUT.write_text("window.FRUTERIAS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";")
    print(f"✔ {len(comercios)} fruterías OSM escritas en {OUT}")


if __name__ == "__main__":
    main()
