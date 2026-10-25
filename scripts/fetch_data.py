#!/usr/bin/env python3
"""
Descarga y prepara los datos estáticos del MVP "Fruterías de Madrid".

Fuentes:
  - Distritos de Madrid (21): GeoJSON de ejemplo publicado en data.madrid.es
    (repositorio espejo en GitHub). Se simplifica para reducir tamaño.
  - Metro de Madrid (estaciones): Overpass API (OpenStreetMap).
    Si el servidor no responde, se regenera desde la copia local ya descargada
    o se omite (la capa de metro es opcional en el visor).

Salidas (carpeta www/data/):
  - distritos.geojson   : distritos simplificados {codigo, nombre}
  - metro.geojson       : estaciones de metro {name}
  - fuentes.json        : metadatos de las fuentes usadas

Uso:
  python3 scripts/fetch_data.py [--simplify 0.0006]

Nota sobre las fruterías: el Ayuntamiento de Madrid publica el censo de
establecimientos comerciales en data.madrid.es ("Registro de Establecimientos
Comerciales" / "Directorio de Comercio"). Como este sandbox no tiene acceso a
ese dominio, el pipeline espera un CSV local en data/fruterias_raw.csv (ver
scripts/procesar_fruterias.py) que puedes generar de dos formas equivalentes:
  1) Descargando el CSV oficial de data.madrid.es en tu navegador y guardándolo
     como data/fruterias_raw.csv  ->  python3 scripts/procesar_fruterias.py --oficial
  2) Ejecutando esta descarga real vía Overpass (OSM) desde tu máquina:
        python3 scripts/fetch_overpass.py
"""
import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA_IN = RAIZ / "data"
DATA_OUT = RAIZ / "www" / "data"

URL_DISTRITOS = (
    "https://raw.githubusercontent.com/pedrojavierpablos-del/Distritosmadrid/"
    "main/DISTRITOS.json"
)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://api.overpass-api.de/api/interpreter",
]
# Área aproximada del municipio de Madrid
BBOX_METRO = "40.30,-3.89,40.65,-3.51"


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "fruterias-madrid-mvp/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def overpass(query: str) -> dict:
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            data = urllib.parse.urlencode({"data": query}).encode()
            req = urllib.request.Request(
                endpoint, data=data,
                headers={"User-Agent": "fruterias-madrid-mvp/1.0",
                         "Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  ! fallo en {endpoint}: {e}", file=sys.stderr)
    raise RuntimeError(f"Overpass inaccesible: {last_err}")


def simplify_geojson(raw_path: Path, out_path: Path, tol: float) -> int:
    """Simplifica con scripts/simplify.py (sin dependencias externas)."""
    if not raw_path.exists():
        return 0
    subprocess.run([sys.executable, str(RAIZ / "scripts" / "simplify.py"),
                    str(raw_path), str(out_path), str(tol)], check=True)
    d = json.loads(out_path.read_text())
    print(f"  ✔ distritos: {len(d['features'])} ({out_path.stat().st_size} bytes)")
    return len(d["features"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--simplify", type=float, default=0.0006, help="Tolerancia de simplificación (grados)")
    args = ap.parse_args()

    DATA_IN.mkdir(exist_ok=True)
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    # 1) Distritos ----------------------------------------------------------
    raw_distritos = DATA_IN / "distritos_raw.json"
    if not raw_distritos.exists():
        print("Descargando distritos de Madrid…")
        raw_distritos.write_bytes(http_get(URL_DISTRITOS))
    n = simplify_geojson(raw_distritos, DATA_OUT / "distritos.geojson", args.simplify)
    if n != 21:
        print(f"  AVISO: se esperaban 21 distritos, hay {n}", file=sys.stderr)

    # 2) Metro de Madrid ----------------------------------------------------
    metro_cache = DATA_IN / "metro_overpass.json"
    metro_out = DATA_OUT / "metro.geojson"
    if True:
        try:
            if not metro_cache.exists():
                print("Consultando Overpass por estaciones de metro…")
                q = (
                    f'[out:json][timeout:90];node["railway"="station"]'
                    f'["station"="subway"]({BBOX_METRO});out center tags;'
                )
                metro_cache.write_text(json.dumps(overpass(q)))
            osm = json.loads(metro_cache.read_text())
            feats = []
            for el in osm.get("elements", []):
                lat, lon = el.get("lat") or el.get("center", {}).get("lat"), \
                           el.get("lon") or el.get("center", {}).get("lon")
                if lat is None or lon is None:
                    continue
                name = el.get("tags", {}).get("name", "")
                feats.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                    "properties": {"name": name},
                })
            metro_out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
            print(f"  ✔ estaciones de metro: {len(feats)}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! metro no disponible ({e}); la capa de metro se omitirá en el visor",
                  file=sys.stderr)

    # 3) Metadatos de fuentes ----------------------------------------------
    fuentes = {
        "generado": "2026-10-26",
        "distritos": {
            "descripcion": "Distritos municipales de Madrid (21)",
            "fuente": "Ejemplo geojson Ayuntamiento de Madrid (data.madrid.es) vía espejo GitHub pedrojavierpablos-del/Distritosmadrid",
            "licencia": "CC-BY 4.0 (Datos Abiertos Madrid)",
        },
        "metro": {
            "descripcion": "Estaciones de Metro de Madrid",
            "fuente": "OpenStreetMap via Overpass API",
            "licencia": "ODbL 1.0",
        },
        "comercios": {
            "descripcion": "Censo de establecimientos comerciales (incluye fruterías)",
            "fuente": "data.madrid.es — Registro de Establecimientos Comerciales (descarga manual requerida: ver README)",
            "licencia": "CC-BY 4.0 (Datos Abiertos Madrid)",
        },
    }
    (DATA_OUT / "fuentes.json").write_text(json.dumps(fuentes, ensure_ascii=False, indent=2))
    print("✔ fetch_data completado")


if __name__ == "__main__":
    main()
