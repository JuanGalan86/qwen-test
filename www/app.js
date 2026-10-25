/* Fruterías de Madrid · MVP Leaflet (vanilla JS)
 * Estado: año seleccionado, capa de distritos (coroplema), puntos de fruterías,
 * metro opcional, gráficos sincronizados en canvas (sin librerías externas). */
(function () {
  "use strict";

  // ---------- datos ----------
  var FR = window.FRUTERIAS;
  if (!FR || !FR.comercios) {
    document.getElementById("aviso-sintetico").hidden = false;
    document.getElementById("aviso-sintetico").innerHTML =
      "❌ No se encontraron datos. Ejecuta <code>python3 scripts/generar_datos_ejemplo.py</code> o el pipeline real.";
    return;
  }
  if (FR.tipo_dato === "SINTETICO_DE_EJEMPLO") {
    document.getElementById("aviso-sintetico").hidden = false;
  }

  var ANIO_MIN = FR.anio_min, ANIO_MAX = FR.anio_max;
  var anioActual = ANIO_MAX;
  var filtroDistrito = "";   // nombre distrito o ""
  var mostrarCerradas = false;

  // ---------- mapa base ----------
  var mapa = L.map("mapa", { zoomControl: true }).setView([40.42, -3.68], 11);
  // Capas base OpenStreetMap (sin API key): tile.openstreetmap.org + alternativa OpenTopoMap
  var capasBase = {
    "OSM estándar": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }),
    "OpenTopoMap": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | &copy; <a href="https://opentopomap.org">OpenTopoMap</a>',
      maxZoom: 17
    })
  };
  capasBase["OSM estándar"].addTo(mapa);
  L.control.layers(capasBase, null, { position: "topright" }).addTo(mapa);

  // ---------- utilidades temporales ----------
  function abiertaEn(c, y) { return c.apertura <= y && (c.cierre == null || c.cierre > y); }
  function cerradaEn(c, y) { return c.cierre != null && c.cierre <= y; }
  function comerciosFiltrados() {
    return filtroDistrito ? FR.comercios.filter(function (c) { return c.distrito === filtroDistrito; })
                          : FR.comercios;
  }

  // ---------- capa de puntos ----------
  var capaPuntos = L.layerGroup().addTo(mapa);
  var hoverInfo = document.getElementById("hover-info");

  function colorPunto(c, y) {
    if (abiertaEn(c, y)) return "#2e7d32";
    if (cerradaEn(c, y)) return "#ef6c00";
    return null; // aún no existía
  }
  function popupHtml(c) {
    return "<b>" + esc(c.nombre) + "</b><br>" + esc(c.direccion) +
           "<br>Distrito: " + esc(c.distrito || "—") +
           "<br>Apertura: " + c.apertura + (c.cierre ? " · Cierre: " + c.cierre : " · <i>en activo</i>");
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (m) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]; }); }

  function renderPuntos() {
    capaPuntos.clearLayers();
    var cs = comerciosFiltrados();
    for (var i = 0; i < cs.length; i++) {
      var c = cs[i];
      var col = colorPunto(c, anioActual);
      if (!col) continue;
      if (col === "#ef6c00" && !mostrarCerradas) continue;
      var m = L.circleMarker([c.lat, c.lon], {
        radius: col === "#2e7d32" ? 5 : 4,
        color: "#fff", weight: 1, fillColor: col, fillOpacity: .9
      });
      m.bindPopup(popupHtml(c));
      m.on("mouseover", function (ev) {
        var cc = ev.target._fr;
        hoverInfo.innerHTML = "<b>" + esc(cc.nombre) + "</b> · " + esc(cc.distrito) +
          " · abre " + cc.apertura + (cc.cierre ? " · cierra " + cc.cierre : " · abierta");
      });
      m._fr = c;
      capaPuntos.addLayer(m);
    }
  }

  // ---------- distritos (geojson + coroplema) ----------
  var capaDistritos = null, geoDistritos = null;
  var labelsLayer = L.layerGroup().addTo(mapa);

  CARGAR_GEOJSON("data/distritos.geojson", function (err, gj) {
    if (err) { console.warn("distritos no disponibles", err); return; }
    geoDistritos = gj;
    capaDistritos = L.geoJSON(gj, { style: styleFn, onEachFeature: onDistrito }).addTo(mapa);
    // etiquetas de distrito
    gj.features.forEach(function (f) {
      var ctr = centroide(f.geometry);
      if (!ctr) return;
      L.marker(ctr, {
        icon: L.divIcon({ className: "distrito-label", html: f.properties.nombre,
                          iconSize: [110, 14], iconAnchor: [55, 7] }),
        interactive: false
      }).addTo(labelsLayer);
    });
    refrescarCoroplema();
  });

  function cuentaPorDistrito(y) {
    var m = {};
    (geoDistritos ? geoDistritos.features : []).forEach(function (f) { m[f.properties.nombre] = 0; });
    FR.comercios.forEach(function (c) { if (abiertaEn(c, y) && m[c.distrito] != null) m[c.distrito]++; });
    return m;
  }
  var MAXCUENTA = 1;
  function escalaColor(n) {
    // verde suave -> intenso
    var t = Math.min(1, n / MAXCUENTA);
    var a = [232, 245, 233], b = [27, 94, 32];
    var rgb = a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); });
    return "rgb(" + rgb.join(",") + ")";
  }
  function styleFn(f) {
    var cuenta = (styleFn._cuentas || {})[f.properties.nombre] || 0;
    return { fillColor: escalaColor(cuenta), fillOpacity: .55, color: "#6b8e6b", weight: 1 };
  }
  function onDistrito(f, layer) {
    layer.on("mouseover", function () {
      var n = (styleFn._cuentas || {})[f.properties.nombre] || 0;
      hoverInfo.innerHTML = "<b>Distrito " + esc(f.properties.nombre) + "</b> · " + n +
        " fruterías abiertas en " + anioActual + ". Clic para filtrar.";
      layer.setStyle({ weight: 2.5, color: "#1b5e20" });
    });
    layer.on("mouseout", function () { if (capaDistritos) capaDistritos.resetStyle(layer); });
    layer.on("click", function () { setDistrito(f.properties.nombre === filtroDistrito ? "" : f.properties.nombre); });
  }
  function refrescarCoroplema() {
    if (!capaDistritos) return;
    var cuentas = cuentaPorDistrito(anioActual);
    styleFn._cuentas = cuentas;
    MAXCUENTA = Math.max.apply(null, Object.keys(cuentas).map(function (k) { return cuentas[k]; })) || 1;
    capaDistritos.setStyle(styleFn);
  }

  function centroide(geom) {
    var pts = [];
    function walk(arr) { if (typeof arr[0] === "number") pts.push(arr); else arr.forEach(walk); }
    walk(geom.coordinates);
    if (!pts.length) return null;
    var x = 0, y = 0;
    pts.forEach(function (p) { x += p[0]; y += p[1]; });
    return [y / pts.length, x / pts.length];
  }

  // ---------- metro (opcional) ----------
  var capaMetro = null;
  CARGAR_GEOJSON("data/metro.geojson", function (err, gj) {
    if (err) {
      document.getElementById("cb-metro").disabled = true;
      document.querySelector("#cb-metro").closest("label").style.opacity = .4;
      return;
    }
    capaMetro = L.geoJSON(gj, {
      pointToLayer: function (f, latlng) {
        return L.circleMarker(latlng, { radius: 3.5, color: "#0d47a1", weight: 1.5, fillColor: "#fff", fillOpacity: 1 });
      },
      onEachFeature: function (f, l) { l.bindTooltip(f.properties.name, { direction: "top" }); }
    });
    document.getElementById("cb-metro").onchange = function (e) {
      if (e.target.checked) capaMetro.addTo(mapa); else if (capaMetro) mapa.removeLayer(capaMetro);
    };
    capaMetro.addTo(mapa);
  });

  // ---------- gráficos canvas ----------
  var cvAnios = document.getElementById("grafico"), ctxA = cvAnios.getContext("2d");
  var cvDis = document.getElementById("grafico-distritos"), ctxD = cvDis.getContext("2d");

  function dpr(canvas, hCss) {
    var r = window.devicePixelRatio || 1;
    var w = canvas.clientWidth || 300;
    canvas.width = w * r; canvas.height = hCss * r;
    canvas.style.height = hCss + "px";
    var ctx = canvas.getContext("2d"); ctx.setTransform(r, 0, 0, r, 0, 0);
    return { w: w, h: hCss };
  }

  function graficoAnios() {
    var dim = dpr(cvAnios, 150), W = dim.w, H = dim.h;
    ctxA.clearRect(0, 0, W, H);
    var cs = comerciosFiltrados();
    var ap = {}, ci = {};
    for (var y = ANIO_MIN; y <= ANIO_MAX; y++) { ap[y] = 0; ci[y] = 0; }
    cs.forEach(function (c) {
      if (c.apertura >= ANIO_MIN && c.apertura <= ANIO_MAX) ap[c.apertura]++;
      if (c.cierre != null && c.cierre >= ANIO_MIN && c.cierre <= ANIO_MAX) ci[c.cierre]++;
    });
    var maxV = 1;
    for (var y2 = ANIO_MIN; y2 <= ANIO_MAX; y2++) maxV = Math.max(maxV, ap[y2], ci[y2]);
    var n = ANIO_MAX - ANIO_MIN + 1, bw = (W - 30) / n;
    // ejes
    ctxA.fillStyle = "#bbb"; ctxA.fillRect(25, 2, 1, H - 22); ctxA.fillRect(25, H - 20, W - 30, 1);
    for (var i = 0; i < n; i++) {
      var yy = ANIO_MIN + i;
      var x = 28 + i * bw;
      var ha = (ap[yy] / maxV) * (H - 30), hc = (ci[yy] / maxV) * (H - 30);
      ctxA.fillStyle = "#2e7d32"; ctxA.fillRect(x, H - 20 - ha, bw * .45, ha);
      ctxA.fillStyle = "#ef6c00"; ctxA.fillRect(x + bw * .5, H - 20 - hc, bw * .45, hc);
      if (yy % 5 === 0) {
        ctxA.save(); ctxA.translate(x + bw / 2, H - 6); ctxA.rotate(-Math.PI / 4);
        ctxA.fillStyle = "#666"; ctxA.font = "9px sans-serif"; ctxA.fillText(yy, 0, 0); ctxA.restore();
      }
    }
    ctxA.fillStyle = "#2e7d32"; ctxA.font = "bold 9px sans-serif"; ctxA.fillText("▲ aperturas", 30, 12);
    ctxA.fillStyle = "#ef6c00"; ctxA.fillText("▼ cierres", 100, 12);
    // marcador del año actual
    var xa = 28 + (anioActual - ANIO_MIN) * bw + bw / 2;
    ctxA.strokeStyle = "#c62828"; ctxA.lineWidth = 1.5;
    ctxA.beginPath(); ctxA.moveTo(xa, 2); ctxA.lineTo(xa, H - 20); ctxA.stroke();
  }

  function graficoDistritos() {
    var dim = dpr(cvDis, 260), W = dim.w, H = dim.h;
    ctxD.clearRect(0, 0, W, H);
    if (!geoDistritos) return;
    var cuentas = cuentaPorDistrito(anioActual);
    var items = geoDistritos.features.map(function (f) { return { n: f.properties.nombre, v: cuentas[f.properties.nombre] || 0 }; })
      .sort(function (a, b) { return b.v - a.v; });
    var maxV = Math.max.apply(null, items.map(function (it) { return it.v; })) || 1;
    var rowH = (H - 10) / items.length, barX = 118;
    items.forEach(function (it, idx) {
      var y = 5 + idx * rowH;
      ctxD.fillStyle = it.n === filtroDistrito ? "#c62828" : (it.n === hoverDistrito ? "#1b5e20" : "#66bb6a");
      var wBar = (it.v / maxV) * (W - barX - 34);
      ctxD.fillRect(barX, y + 1, Math.max(2, wBar), rowH - 4);
      ctxD.fillStyle = "#333"; ctxD.font = "10px sans-serif";
      ctxD.textAlign = "right"; ctxD.fillText(it.n, barX - 5, y + rowH / 2 + 3);
      ctxD.textAlign = "left"; ctxD.fillText(it.v, barX + Math.max(2, wBar) + 4, y + rowH / 2 + 3);
    });
    cvDis._items = items;
  }
  var hoverDistrito = "";
  cvDis.addEventListener("mousemove", function (e) {
    var items = cvDis._items; if (!items) return;
    var rect = cvDis.getBoundingClientRect();
    var idx = Math.floor((e.clientY - rect.top - 5) / ((rect.height - 10) / items.length));
    hoverDistrito = items[idx] ? items[idx].n : "";
    cvDis.style.cursor = items[idx] ? "pointer" : "default";
  });
  cvDis.addEventListener("click", function () { if (hoverDistrito) setDistrito(hoverDistrito === filtroDistrito ? "" : hoverDistrito); });

  // ---------- stats ----------
  function refrescarStats() {
    var cs = comerciosFiltrados(), a = 0, c = 0;
    cs.forEach(function (x) { if (abiertaEn(x, anioActual)) a++; else if (cerradaEn(x, anioActual)) c++; });
    document.getElementById("st-abiertas").textContent = a;
    document.getElementById("st-cerradas").textContent = c;
  }

  // ---------- controles ----------
  var slider = document.getElementById("slider"), lblAnio = document.getElementById("anio");
  slider.min = ANIO_MIN; slider.max = ANIO_MAX; slider.value = anioActual;

  function setAnio(y) {
    anioActual = y; lblAnio.textContent = y; slider.value = y;
    renderPuntos(); refrescarCoroplema(); refrescarStats(); graficoAnios(); graficoDistritos();
  }
  slider.addEventListener("input", function () { pararPlay(); setAnio(+slider.value); });

  var btnPlay = document.getElementById("btn-play"), timer = null;
  function pararPlay() { if (timer) { clearInterval(timer); timer = null; btnPlay.textContent = "▶"; } }
  btnPlay.addEventListener("click", function () {
    if (timer) { pararPlay(); return; }
    if (anioActual >= ANIO_MAX) setAnio(ANIO_MIN);
    btnPlay.textContent = "⏸";
    timer = setInterval(function () {
      if (anioActual >= ANIO_MAX) { pararPlay(); return; }
      setAnio(anioActual + 1);
    }, 900);
  });

  document.getElementById("cb-distritos").addEventListener("change", function (e) {
    if (!capaDistritos) return;
    if (e.target.checked) capaDistritos.addTo(mapa); else mapa.removeLayer(capaDistritos);
  });
  document.getElementById("cb-cerradas").addEventListener("change", function (e) {
    mostrarCerradas = e.target.checked; renderPuntos();
  });

  var sel = document.getElementById("sel-distrito");
  function poblarSelect() {
    if (!geoDistritos) return;
    geoDistritos.features.slice().sort(function (a, b) { return a.properties.nombre.localeCompare(b.properties.nombre); })
      .forEach(function (f) {
        var o = document.createElement("option"); o.value = f.properties.nombre; o.textContent = f.properties.nombre;
        sel.appendChild(o);
      });
  }
  sel.addEventListener("change", function () { setDistrito(sel.value); });
  function setDistrito(nombre) {
    filtroDistrito = nombre; sel.value = nombre;
    renderPuntos(); refrescarStats(); graficoAnios(); graficoDistritos();
    if (nombre && geoDistritos) {
      var f = geoDistritos.features.find(function (x) { return x.properties.nombre === nombre; });
      if (f) { var ctr = centroide(f.geometry); mapa.setView(ctr, 13); }
    }
  }
  // poblar cuando cargue geojson
  var intv = setInterval(function () { if (geoDistritos) { poblarSelect(); clearInterval(intv); } }, 200);

  // ---------- arranque ----------
  setAnio(ANIO_MAX);
  window.addEventListener("resize", function () { graficoAnios(); graficoDistritos(); });
})();
