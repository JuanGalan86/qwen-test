#!/usr/bin/env python3
"""Simplificador GeoJSON (Douglas-Peucker) sin dependencias externas.

Uso: python3 scripts/simplify.py entrada.json salida.json [tolerancia_grados]
Redondea coordenadas a 6 decimales y elimina anillos degenerados.
"""
import json
import math
import sys
from pathlib import Path


def _perp_dist(pt, a, b):
    """Distancia perpendicular aproximada (en grados) de pt al segmento a-b."""
    ax, ay = a
    bx, by = b
    px, py = pt
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify_ring(ring, tol):
    """Douglas-Peucker iterativo para un anillo [ [x,y], ... ]."""
    if len(ring) < 4:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        dmax, idx = 0.0, -1
        for k in range(i + 1, j):
            d = _perp_dist(ring[k], ring[i], ring[j])
            if d > dmax:
                dmax, idx = d, k
        if dmax > tol and idx > 0:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    out = [c for c, k in zip(ring, keep) if k]
    if len(out) >= 3 and out[0] != out[-1]:
        out.append(list(out[0]))
    return out if len(out) >= 4 else ring


def round_coords(obj, nd=6):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(v), nd) for v in obj]
        return [round_coords(x, nd) for x in obj]
    return obj


def process(geometry, tol):
    gtype = geometry["type"]
    if gtype in ("Polygon", "MultiPolygon"):
        polys = geometry["coordinates"] if gtype == "MultiPolygon" else [geometry["coordinates"]]
        new_polys = []
        for poly in polys:
            rings = [simplify_ring(round_coords(r), tol) for r in poly]
            rings = [r for r in rings if len(r) >= 4]
            if rings:
                new_polys.append(rings)
        return {"type": gtype, "coordinates": new_polys if gtype == "MultiPolygon" else (new_polys or [[]])}
    return geometry


def main():
    src, dst, tol = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 0.0006
    data = json.loads(src.read_text())
    n_before = n_after = 0
    for f in data.get("features", []):
        geom = f["geometry"]
        def count(g):
            s = json.dumps(g["coordinates"])
            return s.count("[")
        n_before += count(geom)
        props = {"codigo": f["properties"].get("COD_DIS_TX") or f["properties"].get("COD_DIS"),
                 "nombre": f["properties"].get("NOMBRE")}
        f["properties"] = props
        f["geometry"] = process(geom, tol)
        n_after += count(f["geometry"])
    dst.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"Simplificado {src.name}: corchetes {n_before}->{n_after}, "
          f"{dst.stat().st_size} bytes ({len(data['features'])} features)")


if __name__ == "__main__":
    main()
