#!/usr/bin/env python3
"""Convierte el CSV oficial de data.madrid.es en www/data/fruterias.js.

FUENTE OFICIAL (descárgalo tú, este sandbox no tiene acceso a data.madrid.es):
  data.madrid.es → "Comercio" → "Registro de Establecimientos Comerciales"
  (también llamado "Censo de comercios e instalaciones". Contiene tipo de
  actividad —incl. "Elaboración y venta de zumos"/comercio de frutas y
  verduras—, dirección, distrito, código postal y fechas de alta/baja.)

Uso:
  1) Guarda el CSV como  data/fruterias_raw.csv   (o fruterias_2024.csv etc.)
  2) python3 scripts/procesar_fruterias.py --oficial [--dry-run]

El script detecta automáticamente las columnas por nombre (español/catalán/
sensible a mayúsculas) y filtra los establecimientos cuya actividad contiene
"fruta", "verdura", "hortofrut" o "zumos".

Si además quieres geolocalizar direcciones sin coordenadas, usa Google/IGN
Nominatim con moderación (no incluido en el MVP).

Para datos OSM reales alternativos: python3 scripts/fetch_overpass.py
(Overpass API; requiere que tu red pueda acceder a overpass-api.de).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV_ENTRADA = RAIZ / "data" / "fruterias_raw.csv"
OUT = RAIZ / "www" / "data" / "fruterias.js"

PATRON_FRUTA = re.compile(r"fruta|verdur|hortofrut|zumos?|zumo", re.IGNORECASE)

# Candidatos de nombres de columna (el censo oficial varía entre ediciones)
CAMPOS = {
    "nombre": ["denominacion", "denominación", "nombre_comercial", "nombre", "rotulo", "rótulo"],
    "direccion": ["direccion_postal", "dirección", "direccion", "domicilio", "calle"],
    "distrito": ["distrito", "nombre_distrito", "division_territorial"],
    "codigo_distrito": ["codigo_distrito", "cod_distrito", "id_distrito"],
    "cp": ["codigo_postal", "cod_postal", "cp"],
    "apertura": ["fecha_apertura", "fecha_alta", "alta", "apertura"],
    "cierre": ["fecha_cierre", "fecha_baja", "baja", "cierre"],
    "lat": ["latitud", "lat"],
    "lon": ["longitud", "lon", "lng"],
    "actividad": ["tipo_actividad", "actividad", "categoria", "categoría", "epigrafe"],
}


def pick(headers, keys):
    low = {h.lower().strip(): h for h in headers}
    for k in keys:
        if k in low:
            return low[k]
    # coincidencia parcial
    for k in keys:
        for h_low, h in low.items():
            if k in h_low:
                return h
    return None


def anio(valor):
    if not valor:
        return None
    m = re.search(r"(19|20)\d{2}", str(valor))
    return int(m.group()) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", action="store_true", help="Procesar data/fruterias_raw.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.oficial or not CSV_ENTRADA.exists():
        print(f"No existe {CSV_ENTRADA}. Descarga el censo de data.madrid.es y guárdalo ahí.\n"
              "Mientras tanto puedes usar: python3 scripts/generar_datos_ejemplo.py", file=sys.stderr)
        sys.exit(1)

    with open(CSV_ENTRADA, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=None)  # autodetect sniff no soportado; usamos , por defecto
        rows = list(reader)
    if not rows:
        sys.exit("CSV vacío")
    headers = list(rows[0].keys())
    col = {campo: pick(headers, claves) for campo, claves in CAMPOS.items()}
    print("Columnas detectadas:", {k: v for k, v in col.items() if v})

    faltan = [c for c in ("direccion", "apertura") if not col[c]]
    if faltan:
        sys.exit(f"Faltan columnas esenciales: {faltan}. Revisa el CSV.")

    comercios = []
    cid = 1
    for r in rows:
        act = (r.get(col["actividad"]) or "") if col["actividad"] else ""
        nom = (r.get(col["nombre"]) or "") if col["nombre"] else ""
        if not PATRON_FRUTA.search(act + " " + nom):
            continue
        lat = float(r[col["lat"]]) if col["lat"] and r.get(col["lat"]) else None
        lon = float(r[col["lon"]]) if col["lon"] and r.get(col["lon"]) else None
        if lat is None or lon is None:
            continue  # sin coordenadas: se geocodificarían en una fase posterior
        apertura = anio(r.get(col["apertura"])) or 2000
        cierre = anio(r.get(col["cierre"])) if col["cierre"] else None
        comercios.append({
            "id": cid, "nombre": nom.strip()[:80], "direccion": (r.get(col["direccion"]) or "").strip(),
            "distrito": ((r.get(col["distrito"]) or "").strip() if col["distrito"] else ""),
            "codigo_distrito": ((r.get(col["codigo_distrito"]) or "").strip() if col["codigo_distrito"] else ""),
            "lat": round(lat, 6), "lon": round(lon, 6),
            "apertura": apertura, "cierre": cierre,
        })
        cid += 1

    if not comercios:
        sys.exit("No se detectaron fruterías con coordenadas en el CSV.")
    anios = [c["apertura"] for c in comercios]
    payload = {
        "tipo_dato": "OFICIAL_data.madrid.es",
        "aviso": "",
        "anio_min": max(1995, min(anios)),
        "anio_max": 2026,
        "comercios": comercios,
    }
    print(f"Detectadas {len(comercios)} fruterías ({payload['anio_min']}–{payload['anio_max']})")
    if args.dry_run:
        print("(dry-run, no se escribe nada)")
        return
    OUT.write_text("window.FRUTERIAS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";")
    print(f"✔ escrito {OUT}")


if __name__ == "__main__":
    main()
