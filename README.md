# 🍎 Fruterías de Madrid — Mapa interactivo y evolución temporal

Mapa web interactivo (sin backend) con las fruterías del término municipal de Madrid
y un **slider/play** para ver su estado año a año (1995–2026), con gráficos sincronizados
por distrito.

## Estructura

```
www/            → Web estática (esta carpeta es la que se publica en GitHub Pages)
  index.html    → Página principal (Leaflet + slider temporal + gráficos)
  app.js        → Lógica del mapa, capas, animación y gráficos
  data/
    fruterias.js     → Censo de fruterías (actualmente SINTÉTICO, formato compatible con el oficial)
    distritos.geojson → Distritos de Madrid (datos abiertos data.madrid.es, simplificados)
    metro.geojson     → Estaciones de Metro (OpenStreetMap vía Overpass)
data/           → Datos crudos descargados
scripts/        → Utilidades de descarga y procesado (Python)
```

## Ver en local

```bash
cd www && python3 -m http.server 8080
# abrir http://localhost:8080
```

## Publicar en GitHub Pages (gratis)

1. Sube este repositorio a GitHub.
2. En **Settings → Pages**, selecciona:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` / carpeta `/www`
3. Guarda. En 1-2 minutos tu web estará en `https://<usuario>.github.io/<repo>/`.

Alternativa con GitHub Actions: crea un workflow que haga `actions/upload-pages-artifact`
con la carpeta `www/` (pídemelo y lo genero).

## Datos oficiales (sustituir los sintéticos)

El MVP usa **fruterías simuladas** como ejemplo. Para usar el censo oficial:

1. Descarga «Locales de mercado y gran distribución» / «Censo de comercios» desde
   [data.madrid.es](https://opendata.madrid.es) (formato CSV/XLSX).
2. Ejecuta:
   ```bash
   python3 scripts/procesar_fruterias.py --oficial ruta/al/fichero.csv
   ```
   Esto regenera `www/data/fruterias.js` con datos reales manteniendo el mismo formato.

Fuentes usadas:
- Distritos: [data.madrid.es – Organización territorial](https://opendata.madrid.es)
- Metro: OpenStreetMap (Overpass API)
- Fruterías: pendiente de volcar censo oficial (ahora sintético, marcado como tal en la web)

## Aviso

Los datos sintéticos están claramente marcados en la interfaz. No usar para análisis reales
hasta volcar el censo oficial.
