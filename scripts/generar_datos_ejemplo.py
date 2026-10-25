#!/usr/bin/env python3
"""Genera www/data/fruterias.js con datos SINTÉTICOS de ejemplo (MVP).

IMPORTANTE: estos datos NO son reales. Simulan el formato final del censo de
fruterías de Madrid (nombre, dirección, distrito, coordenadas y año de
apertura) para poder desarrollar y probar todo el visor (slider temporal,
gráficos sincronizados, capas) mientras se confirma la descarga oficial de
data.madrid.es. Cuando tengas el CSV real, ejecuta:

    python3 scripts/procesar_fruterias.py --oficial

y este archivo será reemplazado por datos reales.

Salida: www/data/fruterias.js  ->  window.FRUTERIAS = { ... }
(usa .js para que el visor funcione también abriendo index.html con file://)
"""
import json
import math
import random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DISTRITOS_RAW = RAIZ / "data" / "distritos_raw.json"
OUT = RAIZ / "www" / "data" / "fruterias.js"

random.seed(42)

# Nombre de distrito -> centroide aproximado (lon, lat) y radio en km
CENTROIDES = {
    "Centro": (-3.7037, 40.4153, 1.2), "Arganzuela": (-3.697, 40.402, 1.3),
    "Retiro": (-3.670, 40.413, 1.1), "Salamanca": (-3.674, 40.431, 1.4),
    "Chamartín": (-3.660, 40.458, 1.4), "Tetuán": (-3.696, 40.453, 1.0),
    "Chamberí": (-3.706, 40.436, 1.1), "Fuencarral - El Pardo": (-3.727, 40.485, 2.6),
    "Moncloa - Aravaca": (-3.760, 40.453, 2.4), "Latina": (-3.777, 40.419, 2.0),
    "Carabanchel": (-3.744, 40.390, 1.8), "Usera": (-3.719, 40.386, 1.2),
    "Puente de Vallecas": (-3.651, 40.393, 1.3), "Moratalaz": (-3.641, 40.413, 1.2),
    "Ciudad Lineal": (-3.631, 40.437, 1.5), "Hortaleza": (-3.619, 40.470, 2.0),
    "Villaverde": (-3.710, 40.353, 1.8), "Villa de Vallecas": (-3.602, 40.355, 2.2),
    "Vicálvaro": (-3.565, 40.397, 1.8), "San Blas - Canillejas": (-3.603, 40.435, 1.8),
    "Barajas": (-3.597, 40.474, 2.0),
}

# Peso relativo de densidad comercial por distrito (muy aproximado, a ojo)
PESO = {"Centro": 2.2, "Salamanca": 1.6, "Chamberí": 1.5, "Arganzuela": 1.3,
        "Tetuán": 1.3, "Ciudad Lineal": 1.2, "Puente de Vallecas": 1.2,
        "Chamartín": 1.1, "Usera": 1.1, "Latina": 1.0, "Carabanchel": 1.0,
        "Retiro": 1.0, "Moratalaz": 0.9, "Hortaleza": 0.9, "San Blas - Canillejas": 0.8,
        "Moncloa - Aravaca": 0.7, "Fuencarral - El Pardo": 0.6, "Villaverde": 0.7,
        "Villa de Vallecas": 0.6, "Vicálvaro": 0.5, "Barajas": 0.5}

CALLES = ["Calle de Alcalá", "Calle Mayor", "Gran Vía", "Calle de Toledo",
          "Calle Bravo Murillo", "Calle de Goya", "Calle Serrano", "Paseo de Extremadura",
          "Calle de Atocha", "Calle López de Hoyos", "Avenida de América",
          "Calle de Vallecas", "Calle Arturo Soria", "Calle García de Paredes",
          "Calle Francos Rodríguez", "Avenida de Andalucía", "Calle Albufera",
          "Calle Modesto Lafuente", "Calle de Cea Bermúdez", "Avenida de Palomeras"]

NOMBRES_BASE = ["Frutas", "Frutería", "La Fruta Fresca", "El Huerto", "Frutas y Verduras",
                "Mercado", "De la Huerta", "Frutorama", "La Bananera", "FrutiMarket"]
SUFIJOS = ["Manolo", "la Esquina", "del Barrio", "Express", "24h", "García", "doña Amparo",
           "la Castellana", "Madrid Central", "el Progreso", "Naturfruit", "la Viña"]


def punto_en_distrito(nombre):
    lon, lat, r_km = CENTROIDES[nombre]
    # distribución gaussiana; 1 deg lat ≈ 111 km
    d_lat = random.gauss(0, r_km / 111.0)
    d_lon = random.gauss(0, r_km / (111.0 * math.cos(math.radians(lat))))
    return round(lon + d_lon, 6), round(lat + d_lat, 6)


def main():
    distritos = json.loads(DISTRITOS_RAW.read_text())["features"]
    nombre_codigo = {f["properties"]["NOMBRE"]: f["properties"].get("COD_DIS_TX")
                     or f["properties"].get("COD_DIS") for f in distritos}

    comercios = []
    cid = 1
    for nombre, codigo in nombre_codigo.items():
        n_total = int(random.uniform(14, 40) * PESO.get(nombre, 1.0))
        for _ in range(n_total):
            apertura = random.choices(
                range(1985, 2027),
                weights=[max(1, w) for w in [1 + (y - 1985) * 0.35 for y in range(1985, 2027)]],
            )[0]
            # algunos cierres: negocios abiertos antes de 2015 que cerraron
            cierre = None
            if apertura < 2018 and random.random() < 0.22:
                cierre = random.randint(apertura + 3, 2025)
            lon, lat = punto_en_distrito(nombre)
            comercios.append({
                "id": cid,
                "nombre": f"{random.choice(NOMBRES_BASE)} {random.choice(SUFIJOS)}".replace("Frutas ", "Frutas "),
                "direccion": f"{random.choice(CALLES)}, {random.randint(1, 150)}",
                "distrito": nombre,
                "codigo_distrito": codigo,
                "lat": lat,
                "lon": lon,
                "apertura": apertura,
                "cierre": cierre,
            })
            cid += 1

    payload = {
        "tipo_dato": "SINTETICO_DE_EJEMPLO",
        "aviso": "Datos simulados para desarrollo del MVP. Reemplazar con el censo oficial de data.madrid.es mediante scripts/procesar_fruterias.py.",
        "anio_min": 1995,
        "anio_max": 2026,
        "comercios": comercios,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.FRUTERIAS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";")
    print(f"✔ {OUT}: {len(comercios)} fruterías sintéticas (aperio {payload['anio_min']}-{payload['anio_max']})")


if __name__ == "__main__":
    main()
