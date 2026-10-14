"""Genera evidencias/<ejecucion>/reporte.html (portado de Automatization-Paid-Button).

Contenido del reporte:
- Resumen de la corrida (veredicto, datos de ejecución, conteo por estado y por módulo).
- Casos con atención (fallidos / error) al inicio para ir directo a ellos.
- Por caso: ficha, precondiciones, esperado vs obtenido, pasos de la matriz y la
  ejecución paso a paso con hora, tiempo transcurrido, pantalla de la T6 (app · actividad) y captura.
- Visor de capturas con navegación entre los pasos del caso (← → Esc).
"""
import json

PLANTILLA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte Rompefilas T6</title>
<style>
:root{
  --bg:#f4f5f9;--panel:#ffffff;--panel-2:#f8f9fc;--text:#1a2133;--muted:#5d6779;--line:#e2e5ec;
  --brand:#7b2142;--brand-2:#b8975a;--on-brand:#ffffff;--focus:#b8975a;
  --ok:#17804a;--ok-bg:#e2f4ea;--bad:#c0291f;--bad-bg:#fde6e4;--pend:#8a5d00;--pend-bg:#fff2cf;
  --man:#1d5fa3;--man-bg:#e1edfa;--none:#667085;--none-bg:#eceef2;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08);
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --bg:#0f131b;--panel:#171c26;--panel-2:#1c2230;--text:#e7eaf0;--muted:#99a3b3;--line:#2a3141;
  --brand:#e58aa8;--brand-2:#d9bb80;--on-brand:#0f131b;--focus:#d9bb80;
  --ok:#6fd49a;--ok-bg:#15301f;--bad:#ff8a80;--bad-bg:#3a1a18;--pend:#f2c14e;--pend-bg:#382d10;
  --man:#8cbcf0;--man-bg:#16283c;--none:#99a3b3;--none-bg:#242a36;--shadow:none;
}}
:root[data-theme=dark]{
  --bg:#0f131b;--panel:#171c26;--panel-2:#1c2230;--text:#e7eaf0;--muted:#99a3b3;--line:#2a3141;
  --brand:#e58aa8;--brand-2:#d9bb80;--on-brand:#0f131b;--focus:#d9bb80;
  --ok:#6fd49a;--ok-bg:#15301f;--bad:#ff8a80;--bad-bg:#3a1a18;--pend:#f2c14e;--pend-bg:#382d10;
  --man:#8cbcf0;--man-bg:#16283c;--none:#99a3b3;--none-bg:#242a36;--shadow:none;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 "Segoe UI",-apple-system,Roboto,Helvetica,Arial,sans-serif}
button,select,input{font:inherit}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.mono{font-family:ui-monospace,"Cascadia Code",Menlo,Consolas,monospace}
.vacio{color:var(--muted);font-style:italic}

/* ---------- Encabezado ---------- */
.top{background:#7b2142;color:#fff;border-bottom:4px solid #b8975a}
.top-in{max-width:1240px;margin:0 auto;padding:18px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.logo{width:40px;height:40px;position:relative;flex:none}
.logo i{position:absolute;width:24px;height:24px;border-radius:5px;transform:rotate(45deg);top:8px}
.logo i:first-child{background:#fff;left:2px}
.logo i:last-child{background:#b8975a;left:14px;mix-blend-mode:normal;opacity:.95}
.top h1{margin:0;font-size:20px;font-weight:650;letter-spacing:-.01em}
.top p{margin:2px 0 0;opacity:.8;font-size:13px}
.top .acciones{margin-left:auto;display:flex;gap:8px}
.btn-top{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px}
.btn-top:hover{background:rgba(255,255,255,.2)}

main{max-width:1240px;margin:0 auto;padding:20px 16px 72px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}
h2.seccion{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:26px 0 10px;font-weight:650}

/* ---------- Resumen ---------- */
.resumen{display:grid;grid-template-columns:340px 1fr;gap:14px}
.veredicto{padding:18px;display:flex;gap:16px;align-items:center}
.dona{width:110px;height:110px;border-radius:50%;flex:none;display:grid;place-items:center;position:relative}
.dona::after{content:"";position:absolute;inset:14px;border-radius:50%;background:var(--panel)}
.dona b{position:relative;z-index:1;font-size:24px}
.veredicto h3{margin:0 0 4px;font-size:16px}
.veredicto p{margin:0;color:var(--muted);font-size:13px}
.meta{padding:14px 18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px 18px;align-content:center}
.meta div span{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.meta div b{font-weight:600;font-size:14px;word-break:break-word}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:14px}
.kpi{padding:12px 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel);cursor:pointer;text-align:left;color:var(--text);box-shadow:var(--shadow);border-top:3px solid var(--c,var(--none))}
.kpi b{display:block;font-size:24px;line-height:1.2}
.kpi span{color:var(--muted);font-size:12px}
.kpi[aria-pressed=true]{outline:2px solid var(--c,var(--brand));outline-offset:-1px}
.barra{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--none-bg);margin-top:14px}
.barra div{height:100%}

/* ---------- Atención ---------- */
.atencion{padding:4px 0;max-height:340px;overflow-y:auto}
.atencion a{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;padding:10px 16px;color:var(--text);text-decoration:none;border-bottom:1px solid var(--line)}
.atencion a:last-child{border-bottom:0}
.atencion a:hover{background:var(--panel-2)}
.atencion small{grid-column:2;color:var(--bad);font-size:12px}

/* ---------- Módulos ---------- */
.tabla-wrap{overflow-x:auto}
table.modulos{width:100%;border-collapse:collapse;font-size:13px}
.modulos th,.modulos td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.modulos th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em;background:var(--panel-2)}
.modulos th:first-child,.modulos td:first-child{text-align:left;white-space:normal;min-width:220px}
.modulos tr:last-child td{border-bottom:0}
.modulos tbody tr{cursor:pointer}
.modulos tbody tr:hover{background:var(--panel-2)}
.mini{display:flex;height:6px;border-radius:3px;overflow:hidden;background:var(--none-bg);width:120px;margin-left:auto}

/* ---------- Filtros ---------- */
.filtros{padding:12px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;position:sticky;top:0;z-index:5;margin-top:26px}
.chips{display:flex;flex-wrap:wrap;gap:6px;width:100%}
.chip{border:1px solid var(--line);background:transparent;color:var(--text);border-radius:999px;padding:4px 12px;cursor:pointer;font-size:13px}
.chip[aria-pressed=true]{background:var(--brand);border-color:var(--brand);color:var(--on-brand)}
select,input[type=search]{background:var(--panel-2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:13px;max-width:100%}
input[type=search]{flex:1;min-width:200px}
.btn{background:var(--panel-2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px}
.btn:hover{border-color:var(--brand)}
.contador{color:var(--muted);font-size:13px;margin:12px 2px 8px}

/* ---------- Caso ---------- */
.caso{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--none);border-radius:12px;margin-bottom:10px;box-shadow:var(--shadow);scroll-margin-top:180px}
.caso[data-estado=Aprobado]{border-left-color:var(--ok)}
.caso[data-estado=Fallido],.caso[data-estado=Error]{border-left-color:var(--bad)}
.caso[data-estado=Pendiente]{border-left-color:var(--pend)}
.caso[data-estado=Manual]{border-left-color:var(--man)}
.caso>summary{list-style:none;cursor:pointer;padding:12px 16px;display:grid;grid-template-columns:110px 1fr auto;gap:12px;align-items:center}
.caso>summary::-webkit-details-marker{display:none}
.caso>summary:hover{background:var(--panel-2);border-radius:0 12px 12px 0}
.id{font-weight:650;font-size:13px}
.titulo{font-weight:550}
.titulo small{display:block;color:var(--muted);font-size:12px;font-weight:400}
.tags{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.tag{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--none-bg);color:var(--none);white-space:nowrap}
.estado-Aprobado{background:var(--ok-bg);color:var(--ok)}
.estado-Fallido,.estado-Error{background:var(--bad-bg);color:var(--bad)}
.estado-Pendiente{background:var(--pend-bg);color:var(--pend)}
.estado-Manual{background:var(--man-bg);color:var(--man)}
.tag.estado{font-weight:650}
.tag.modulo{background:var(--brand);color:var(--on-brand)}
.tag.escenario{border:1px solid var(--line);background:transparent;color:var(--text)}

.detalle{padding:4px 16px 18px;border-top:1px solid var(--line)}
.detalle h4{margin:18px 0 6px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:650}
.detalle p{margin:0;white-space:pre-wrap;word-break:break-word}
.ficha{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px 16px;margin-top:14px;padding:12px 14px;background:var(--panel-2);border-radius:10px}
.ficha span{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.ficha b{font-weight:600;font-size:13px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.comparacion{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:6px}
.cuadro{border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.cuadro.obtenido{border-color:var(--c,var(--line));background:var(--cb,transparent)}
.cuadro .cab{display:flex;justify-content:space-between;gap:8px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:650;margin-bottom:4px}
ol.plan{margin:0;padding-left:22px}
ol.plan li{margin:3px 0}

/* ---------- Línea de tiempo ---------- */
.timeline{list-style:none;margin:6px 0 0;padding:0;position:relative}
.timeline::before{content:"";position:absolute;left:15px;top:6px;bottom:6px;width:2px;background:var(--line)}
.evento{position:relative;padding:0 0 18px 46px}
.evento:last-child{padding-bottom:0}
.marca-paso{position:absolute;left:0;top:0;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;background:var(--panel);border:2px solid var(--none);color:var(--none)}
.evento.ok .marca-paso{border-color:var(--ok);color:var(--ok);background:var(--ok-bg)}
.evento.fallo .marca-paso{border-color:var(--bad);color:var(--bad);background:var(--bad-bg)}
.evento.info .marca-paso{border-color:var(--brand);color:var(--brand)}
.evento.nota .marca-paso{border-style:dashed}
.ev-cab{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;padding-top:5px}
.ev-cab b{font-weight:600}
.ev-cab .t{color:var(--muted);font-size:12px}
.ev-ctx{color:var(--muted);font-size:12px;margin-top:2px;word-break:break-all}
.ev-ctx a{color:var(--muted)}
.evento.nota .ev-cab b{font-weight:500;font-style:italic}
.pantalla{margin:8px 0 0;width:min(100%,280px);border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel-2);cursor:zoom-in;display:block;padding:0}
.evento.fallo .pantalla{border-color:var(--bad)}
.pantalla img{display:block;width:100%;max-height:620px;object-fit:contain;object-position:top;background:var(--panel-2)}
.galeria{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:6px}
.galeria button{padding:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--panel-2);cursor:zoom-in;text-align:left;color:var(--text)}
.galeria img{width:100%;height:260px;object-fit:cover;object-position:top;display:block}
.galeria span{display:block;padding:4px 6px;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
details.error{margin-top:14px;border:1px solid var(--bad);border-radius:10px;background:var(--bad-bg)}
details.error summary{cursor:pointer;padding:8px 12px;color:var(--bad);font-weight:600;font-size:13px}
details.error pre{margin:0;padding:10px 12px;font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow:auto;background:var(--panel);border-radius:0 0 10px 10px}
.vistas{display:flex;gap:4px;margin-left:auto}
.vistas button{font-size:12px;padding:3px 10px}
.vistas button[aria-pressed=true]{background:var(--brand);color:var(--on-brand);border-color:var(--brand)}
.ttl-row{display:flex;align-items:center;gap:8px;margin:18px 0 6px}
.ttl-row h4{margin:0}

/* ---------- Visor ---------- */
#visor{position:fixed;inset:0;background:rgba(8,10,16,.96);display:none;z-index:30;grid-template-rows:auto 1fr auto;color:#fff}
#visor.abierto{display:grid}
#visor header{display:flex;align-items:center;gap:12px;padding:10px 16px;font-size:13px}
#visor header b{font-weight:600}
#visor header a,#visor header button{margin-left:auto;color:#fff}
#visor header button{margin-left:0;background:none;border:1px solid rgba(255,255,255,.3);border-radius:8px;padding:4px 10px;cursor:pointer}
#visor .lienzo{display:flex;align-items:center;justify-content:center;min-height:0;padding:0 64px}
#visor img{max-width:100%;max-height:100%;border-radius:6px;object-fit:contain}
#visor .nav{position:fixed;top:50%;transform:translateY(-50%);background:rgba(255,255,255,.12);border:0;color:#fff;width:44px;height:44px;border-radius:50%;cursor:pointer;font-size:20px}
#visor .nav:hover{background:rgba(255,255,255,.25)}
#visor .prev{left:12px}#visor .next{right:12px}
#visor footer{padding:10px 16px 16px;font-size:13px;text-align:center;opacity:.85;word-break:break-all}

@media (max-width:820px){
  .resumen{grid-template-columns:1fr}
  .caso>summary{grid-template-columns:1fr}.tags{justify-content:flex-start}
  .grid2,.comparacion{grid-template-columns:1fr}
  #visor .lienzo{padding:0 8px}
  .top .acciones{margin-left:0}
  .filtros{position:static}
}
@media print{
  .filtros,.acciones,#visor,.vistas{display:none!important}
  body{background:#fff}.panel,.caso{box-shadow:none}
  .caso{break-inside:avoid-page}
  .pantalla img{max-height:420px}
}
</style>
</head>
<body>
<div class="top">
  <div class="top-in">
    <div class="logo" aria-hidden="true"><i></i><i></i></div>
    <div>
      <h1>Rompefilas T6 · Reporte de ejecución</h1>
      <p id="subtitulo"></p>
    </div>
    <div class="acciones">
      <button class="btn-top" id="btnTema" type="button">Tema: automático</button>
      <button class="btn-top" id="btnImprimir" type="button">Imprimir / PDF</button>
    </div>
  </div>
</div>
<main>
  <section class="resumen">
    <div class="panel veredicto" id="veredicto"></div>
    <div class="panel meta" id="meta"></div>
  </section>
  <section class="kpis" id="kpis"></section>
  <div class="barra" id="barra" role="img"></div>

  <div id="bloqueAtencion" hidden>
    <h2 class="seccion">Requieren atención</h2>
    <div class="panel atencion" id="atencion"></div>
  </div>

  <h2 class="seccion">Resultados por módulo</h2>
  <div class="panel tabla-wrap"><table class="modulos" id="modulos"></table></div>

  <section class="panel filtros">
    <div class="chips" id="chips"></div>
    <select id="fModulo" aria-label="Módulo"><option value="">Todos los módulos</option></select>
    <select id="fEscenario" aria-label="Escenario"><option value="">Todos los escenarios</option></select>
    <select id="fTipo" aria-label="Tipo"><option value="">Todos los tipos de prueba</option></select>
    <select id="fPrioridad" aria-label="Prioridad"><option value="">Todas las prioridades</option></select>
    <input type="search" id="fTexto" placeholder="Buscar por ID, caso, paso, pantalla o mensaje…">
    <button class="btn" id="btnAbrir" type="button">Expandir todo</button>
    <button class="btn" id="btnCerrar" type="button">Contraer todo</button>
  </section>
  <p class="contador" id="contador"></p>
  <section id="lista"></section>
</main>

<div id="visor" role="dialog" aria-modal="true" aria-label="Visor de capturas">
  <header><b id="vTitulo"></b><span id="vCuenta"></span><a id="vOriginal" target="_blank" rel="noopener">Abrir original</a><button type="button" id="vCerrar">Cerrar ✕</button></header>
  <div class="lienzo"><img alt="" id="vImg"></div>
  <footer id="vPie"></footer>
  <button class="nav prev" type="button" aria-label="Anterior">‹</button>
  <button class="nav next" type="button" aria-label="Siguiente">›</button>
</div>

<script id="datos" type="application/json">__DATOS__</script>
<script>
const D = JSON.parse(document.getElementById('datos').textContent);
const $ = id => document.getElementById(id);
const ESTADOS = ['Aprobado','Fallido','Error','Pendiente','Manual','No ejecutado'];
const COLOR = {Aprobado:'var(--ok)',Fallido:'var(--bad)',Error:'var(--bad)',Pendiente:'var(--pend)',Manual:'var(--man)','No ejecutado':'var(--none)'};
const FONDO = {Aprobado:'var(--ok-bg)',Fallido:'var(--bad-bg)',Error:'var(--bad-bg)',Pendiente:'var(--pend-bg)',Manual:'var(--man-bg)','No ejecutado':'var(--none-bg)'};
const DESCRIPCION_ESTADO = {
  Aprobado:'El resultado coincide con lo esperado.',
  Fallido:'Falló una validación: es un defecto a reportar.',
  Error:'Falló la preparación (ambiente, driver o datos), no la validación.',
  Pendiente:'Bloqueado: depende de otro caso, falta un dato o la funcionalidad aún no existe en esta versión.',
  Manual:'Requiere intervención física en la T6 (tarjeta, recibo, papel...).',
  'No ejecutado':'No se incluyó en esta corrida.'
};
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cls = s => String(s || '').replace(/\s+/g, '_');
const dur = s => { s = Math.round(Number(s) || 0); if (s < 60) return s + ' s'; const m = Math.floor(s / 60); return m < 60 ? `${m} min ${s % 60} s` : `${Math.floor(m / 60)} h ${m % 60} min`; };
const seg = h => { const p = String(h || '').split(':').map(Number); return p.length === 3 && p.every(n => !isNaN(n)) ? p[0]*3600 + p[1]*60 + p[2] : null; };
const pasosPlan = t => String(t || '').split(/\r?\n/).map(l => l.replace(/^\s*\d+[.)-]\s*/, '').trim()).filter(Boolean);

let filtroEstado = '';
let vista = 'linea';

/* ---------- Tema ---------- */
const TEMAS = ['auto', 'light', 'dark'], NOMBRE_TEMA = {auto:'automático', light:'claro', dark:'oscuro'};
let tema = 'auto';
try { tema = localStorage.getItem('reporte-tema') || 'auto'; } catch (e) {}
const aplicarTema = () => {
  if (tema === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', tema);
  $('btnTema').textContent = 'Tema: ' + NOMBRE_TEMA[tema];
};
$('btnTema').onclick = () => { tema = TEMAS[(TEMAS.indexOf(tema) + 1) % 3]; try { localStorage.setItem('reporte-tema', tema); } catch (e) {} aplicarTema(); };
aplicarTema();

/* ---------- Resumen ---------- */
const cuenta = e => D.casos.filter(c => c.estado === e).length;
const total = D.casos.length;
const aprobados = cuenta('Aprobado'), fallidos = cuenta('Fallido') + cuenta('Error');
const ejecutados = aprobados + fallidos;
const pct = ejecutados ? Math.round(aprobados * 100 / ejecutados) : 0;
const capturas = D.casos.reduce((n, c) => n + (c.pasos_evidencia || []).filter(p => p.archivo).length, 0);
const duracionCasos = D.casos.reduce((n, c) => n + (Number(c.duracion) || 0), 0);

$('subtitulo').textContent = `Kiosko de Pagos · Gobierno de Puebla · ${D.dispositivo?.modelo || 'T6'} · Ejecución ${D.ejecucion}`;
const colorDona = fallidos ? 'var(--bad)' : 'var(--ok)';
$('veredicto').innerHTML = `
  <div class="dona" style="background:conic-gradient(var(--ok) ${pct}%, ${ejecutados ? 'var(--bad)' : 'var(--none-bg)'} 0)"><b>${ejecutados ? pct + '%' : '—'}</b></div>
  <div>
    <h3 style="color:${ejecutados ? colorDona : 'var(--muted)'}">${!ejecutados ? 'Sin casos ejecutados' : fallidos ? `${fallidos} caso${fallidos > 1 ? 's' : ''} con falla` : 'Todos los ejecutados aprobaron'}</h3>
    <p>${aprobados} de ${ejecutados} casos ejecutados aprobaron.<br>${total - ejecutados} sin resultado definitivo (pendientes, manuales o no ejecutados).</p>
  </div>`;

const META = [
  ['Inicio', D.inicio], ['Fin', D.fin_completo || D.fin],
  ['Duración total', D.duracion_total != null ? dur(D.duracion_total) : dur(duracionCasos)],
  ['Dispositivo', `${D.dispositivo?.modelo || '—'} · ${D.dispositivo?.serial || '—'}`], ['Android', D.dispositivo?.android || '—'],
  ['Versión de la app', D.dispositivo?.app || '—'], ['Modo', D.interactivo ? 'Interactivo (con tester)' : 'Desatendido'], ['Capturas', capturas],
];
$('meta').innerHTML = META.map(([k, v]) => `<div><span>${k}</span><b>${esc(v)}</b></div>`).join('') + (D.nota ? `<div style="grid-column:1/-1"><span>Nota</span><b>${esc(D.nota)}</b></div>` : '');

$('kpis').innerHTML = [['', 'Total de casos', total, 'var(--brand)'], ...ESTADOS.map(e => [e, e, cuenta(e), COLOR[e]])]
  .filter(([e, , n]) => !e || n)
  .map(([e, t, n, c]) => `<button type="button" class="kpi" data-estado="${esc(e)}" style="--c:${c}" title="${esc(DESCRIPCION_ESTADO[e] || 'Mostrar todos')}"><b>${n}</b><span>${esc(t)}</span></button>`).join('');
$('kpis').addEventListener('click', ev => { const b = ev.target.closest('.kpi'); if (b) fijarEstado(b.dataset.estado); });
$('barra').setAttribute('aria-label', ESTADOS.map(e => `${e}: ${cuenta(e)}`).join(', '));
$('barra').innerHTML = ESTADOS.map(e => { const n = cuenta(e); return n ? `<div title="${e}: ${n}" style="width:${n * 100 / total}%;background:${COLOR[e]}"></div>` : ''; }).join('');

/* ---------- Requieren atención ---------- */
const conFalla = D.casos.filter(c => c.estado === 'Fallido' || c.estado === 'Error');
if (conFalla.length) {
  $('bloqueAtencion').hidden = false;
  $('atencion').innerHTML = conFalla.map(c => `<a href="#${esc(c.id)}" data-abrir="${esc(c.id)}">
    <span class="id mono">${esc(c.id)}</span><span>${esc(c.caso)}</span>
    <small>${esc(c.estado)} · ${esc(c.obtenido || 'Sin mensaje')}</small></a>`).join('');
}

/* ---------- Por módulo ---------- */
const modulos = [...new Set(D.casos.map(c => c.modulo || 'Sin módulo'))];
const COLS = [['Aprobado', ['Aprobado']], ['Fallido', ['Fallido', 'Error']], ['Pendiente', ['Pendiente']], ['Manual', ['Manual']], ['No ejec.', ['No ejecutado']]];
$('modulos').innerHTML = `<thead><tr><th>Módulo</th><th>Casos</th>${COLS.map(([t]) => `<th>${t}</th>`).join('')}<th>Avance</th></tr></thead><tbody>` +
  modulos.map(m => {
    const cs = D.casos.filter(c => (c.modulo || 'Sin módulo') === m);
    const n = e => cs.filter(c => e.includes(c.estado)).length;
    const barra = ESTADOS.map(e => { const k = cs.filter(c => c.estado === e).length; return k ? `<div style="width:${k * 100 / cs.length}%;background:${COLOR[e]}"></div>` : ''; }).join('');
    return `<tr data-modulo="${esc(m)}" title="Filtrar por este módulo"><td>${esc(m)}</td><td>${cs.length}</td>${COLS.map(([, e]) => `<td>${n(e) || '<span class="vacio">0</span>'}</td>`).join('')}<td><div class="mini">${barra}</div></td></tr>`;
  }).join('') + '</tbody>';
$('modulos').addEventListener('click', ev => {
  const tr = ev.target.closest('tr[data-modulo]'); if (!tr) return;
  $('fModulo').value = tr.dataset.modulo === 'Sin módulo' ? '' : tr.dataset.modulo; pintar();
  document.querySelector('.filtros').scrollIntoView({behavior: 'smooth'});
});

/* ---------- Filtros ---------- */
const chips = $('chips');
['', ...ESTADOS].forEach(e => {
  const n = e ? cuenta(e) : total;
  if (e && !n) return;
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'chip'; b.dataset.estado = e; b.textContent = `${e || 'Todos'} (${n})`;
  b.onclick = () => fijarEstado(e);
  chips.appendChild(b);
});
function fijarEstado(e) {
  filtroEstado = e;
  document.querySelectorAll('.chip,.kpi').forEach(x => x.setAttribute('aria-pressed', x.dataset.estado === e));
  pintar();
}
const llenar = (id, campo) => [...new Set(D.casos.map(c => c[campo]).filter(Boolean))].sort()
  .forEach(v => $(id).insertAdjacentHTML('beforeend', `<option>${esc(v)}</option>`));
llenar('fModulo', 'modulo'); llenar('fTipo', 'tipo'); llenar('fPrioridad', 'prioridad');
llenar('fEscenario', 'escenario');
['fModulo','fEscenario','fTipo','fPrioridad','fTexto'].forEach(id => $(id).addEventListener('input', pintar));
$('btnAbrir').onclick = () => document.querySelectorAll('.caso').forEach(d => d.open = true);
$('btnCerrar').onclick = () => document.querySelectorAll('.caso').forEach(d => d.open = false);

/* ---------- Tarjeta de caso ---------- */
function lineaDeTiempo(c) {
  const pasos = c.pasos_evidencia || [];
  if (!pasos.length) return '<p class="vacio">Sin pasos registrados en esta ejecución.</p>';
  const t0 = seg(pasos[0].hora);
  let iImg = -1;
  return `<ol class="timeline">${pasos.map(p => {
    const t = seg(p.hora), trans = t0 != null && t != null ? t - t0 : null;
    const tipo = p.archivo ? (p.estado || 'info') : (p.estado === 'info' ? 'nota' : p.estado);
    if (p.archivo) iImg++;
    const ctx = [p.pantalla ? `Pantalla: ${esc(p.pantalla)}` : '', p.fuente ? `<a href="${esc(p.fuente)}" target="_blank" rel="noopener">XML de la pantalla</a>` : ''].filter(Boolean).join(' · ');
    return `<li class="evento ${esc(tipo)}">
      <span class="marca-paso">${p.estado === 'fallo' ? '✕' : p.estado === 'ok' ? '✓' : p.numero}</span>
      <div class="ev-cab"><b>${esc(p.descripcion)}</b>
        <span class="t mono">${esc(p.hora)}${trans != null && trans > 0 ? ` · +${dur(trans)}` : ''}</span>
        ${p.archivo ? '' : '<span class="tag">Nota</span>'}</div>
      ${ctx ? `<div class="ev-ctx">${ctx}</div>` : ''}
      ${p.archivo ? `<button type="button" class="pantalla" data-caso="${esc(c.id)}" data-i="${iImg}" aria-label="Ampliar captura: ${esc(p.descripcion)}"><img loading="lazy" src="${esc(p.archivo)}" alt="${esc(p.descripcion)}"></button>` : ''}
    </li>`;
  }).join('')}</ol>`;
}
function galeria(c) {
  const imgs = (c.pasos_evidencia || []).filter(p => p.archivo);
  if (!imgs.length) return '<p class="vacio">Sin capturas.</p>';
  return `<div class="galeria">${imgs.map((p, i) => `<button type="button" data-caso="${esc(c.id)}" data-i="${i}" title="${esc(p.descripcion)}"><img loading="lazy" src="${esc(p.archivo)}" alt="${esc(p.descripcion)}"><span>${p.numero}. ${esc(p.descripcion)}</span></button>`).join('')}</div>`;
}
function tarjeta(c) {
  const plan = pasosPlan(c.pasos);
  const nPasos = (c.pasos_evidencia || []).length, nImg = (c.pasos_evidencia || []).filter(p => p.archivo).length;
  const ficha = [
    ['Producto', c.producto], ['Módulo', c.modulo], ['Escenario', c.escenario], ['Tipo de prueba', c.tipo],
    ['Prioridad', c.prioridad], ['Automatización', c.automatizacion],
    ['Duración', c.duracion ? dur(c.duracion) : ''], ['Pasos / capturas', nPasos ? `${nPasos} / ${nImg}` : ''],
  ].filter(([, v]) => v);
  return `<details class="caso" id="${esc(c.id)}" data-estado="${esc(c.estado)}">
    <summary>
      <span class="id mono">${esc(c.id)}</span>
      <span class="titulo">${esc(c.caso)}<small>${esc(c.modulo)}</small></span>
      <span class="tags">
        ${c.modulo ? `<span class="tag modulo">${esc(c.modulo)}</span>` : ''}
        ${c.escenario ? `<span class="tag escenario">${esc(c.escenario)}</span>` : ''}
        ${c.tipo ? `<span class="tag">${esc(c.tipo)}</span>` : ''}${c.prioridad ? `<span class="tag">${esc(c.prioridad)}</span>` : ''}
        ${c.duracion ? `<span class="tag">${dur(c.duracion)}</span>` : ''}
        <span class="tag estado estado-${cls(c.estado)}" title="${esc(DESCRIPCION_ESTADO[c.estado])}">${esc(c.estado)}</span>
      </span>
    </summary>
    <div class="detalle">
      ${ficha.length ? `<div class="ficha">${ficha.map(([k, v]) => `<div><span>${k}</span><b>${esc(v)}</b></div>`).join('')}</div>` : ''}
      ${c.descripcion ? `<h4>Descripción</h4><p>${esc(c.descripcion)}</p>` : ''}
      ${c.precondiciones ? `<h4>Precondiciones</h4><p>${esc(c.precondiciones)}</p>` : ''}
      <h4>Resultado</h4>
      <div class="comparacion">
        <div class="cuadro"><div class="cab">Esperado</div><p>${esc(c.esperado) || '<span class="vacio">—</span>'}</p></div>
        <div class="cuadro obtenido" style="--c:${COLOR[c.estado]};--cb:${FONDO[c.estado]}"><div class="cab"><span>Obtenido</span><span style="color:${COLOR[c.estado]}">${esc(c.estado)}</span></div>
          <p>${esc(c.obtenido) || `<span class="vacio">${esc(DESCRIPCION_ESTADO[c.estado] || '—')}</span>`}</p></div>
      </div>
      <div class="grid2">
        <div><h4>Pasos a seguir (matriz)</h4>${plan.length ? `<ol class="plan">${plan.map(p => `<li>${esc(p)}</li>`).join('')}</ol>` : '<p class="vacio">—</p>'}</div>
        <div><h4>Datos de prueba</h4><p>${esc(c.datos) || '<span class="vacio">—</span>'}</p>
          ${c.observaciones ? `<h4>Observaciones</h4><p>${esc(c.observaciones)}</p>` : ''}</div>
      </div>
      <div class="ttl-row"><h4>Ejecución paso a paso</h4>
        <div class="vistas" role="group" aria-label="Vista de la evidencia">
          <button type="button" class="btn" data-vista="linea" aria-pressed="${vista === 'linea'}">Línea de tiempo</button>
          <button type="button" class="btn" data-vista="galeria" aria-pressed="${vista === 'galeria'}">Galería</button>
        </div></div>
      <div class="evidencia">${vista === 'linea' ? lineaDeTiempo(c) : galeria(c)}</div>
      ${c.error ? `<details class="error"><summary>Detalle técnico del error</summary><pre>${esc(c.error)}</pre></details>` : ''}
    </div>
  </details>`;
}

let visibles = [];
function pintar() {
  const m = fModulo.value, e = fEscenario.value, t = fTipo.value, p = fPrioridad.value, q = fTexto.value.trim().toLowerCase();
  const abiertos = new Set([...document.querySelectorAll('.caso[open]')].map(d => d.id));
  visibles = D.casos.filter(c =>
    (!filtroEstado || c.estado === filtroEstado) && (!m || c.modulo === m) && (!e || c.escenario === e) && (!t || c.tipo === t) &&
    (!p || c.prioridad === p) &&
    (!q || [c.id, c.caso, c.modulo, c.escenario, c.obtenido, c.error, c.pasos, c.datos,
            ...(c.pasos_evidencia || []).map(x => `${x.descripcion} ${x.pantalla || ''}`)].join(' ').toLowerCase().includes(q)));
  $('contador').textContent = `Mostrando ${visibles.length} de ${total} casos`;
  $('lista').innerHTML = visibles.map(tarjeta).join('') || '<p class="vacio">Sin resultados con esos filtros.</p>';
  abiertos.forEach(id => { const d = document.getElementById(id); if (d) d.open = true; });
}
fijarEstado('');

$('lista').addEventListener('click', ev => {
  const b = ev.target.closest('[data-vista]');
  if (!b) return;
  vista = b.dataset.vista;
  document.querySelectorAll('.caso[open]').forEach(d => {
    const c = D.casos.find(x => x.id === d.id);
    d.querySelector('.evidencia').innerHTML = vista === 'linea' ? lineaDeTiempo(c) : galeria(c);
    d.querySelectorAll('[data-vista]').forEach(x => x.setAttribute('aria-pressed', x.dataset.vista === vista));
  });
});

/* ---------- Abrir caso por enlace (#CP-XX-ROM-xxx) ---------- */
function abrirCaso(id) {
  let d = document.getElementById(id);
  if (!d) { fijarEstado(''); ['fModulo','fEscenario','fTipo','fPrioridad','fTexto'].forEach(x => $(x).value = ''); pintar(); d = document.getElementById(id); }
  if (d) { d.open = true; d.scrollIntoView({behavior: 'smooth', block: 'start'}); }
}
document.addEventListener('click', ev => { const a = ev.target.closest('[data-abrir]'); if (a) { ev.preventDefault(); history.replaceState(null, '', '#' + a.dataset.abrir); abrirCaso(a.dataset.abrir); } });
if (location.hash) abrirCaso(decodeURIComponent(location.hash.slice(1)));

/* ---------- Visor ---------- */
const visor = $('visor');
let vImgs = [], vI = 0, vCaso = '';
function mostrar() {
  const p = vImgs[vI];
  $('vImg').src = p.archivo; $('vImg').alt = p.descripcion; $('vOriginal').href = p.archivo;
  $('vTitulo').textContent = `${vCaso} · Paso ${p.numero}`;
  $('vCuenta').textContent = `Captura ${vI + 1} de ${vImgs.length}`;
  $('vPie').textContent = [p.descripcion, p.hora, p.pantalla].filter(Boolean).join('  ·  ');
}
function abrirVisor(casoId, i) {
  const c = D.casos.find(x => x.id === casoId);
  vImgs = (c.pasos_evidencia || []).filter(p => p.archivo); vI = i; vCaso = casoId;
  if (!vImgs.length) return;
  visor.classList.add('abierto'); mostrar(); $('vCerrar').focus();
}
const cerrarVisor = () => visor.classList.remove('abierto');
const mover = d => { vI = (vI + d + vImgs.length) % vImgs.length; mostrar(); };
document.addEventListener('click', ev => {
  const b = ev.target.closest('.pantalla,.galeria button');
  if (b) return abrirVisor(b.dataset.caso, Number(b.dataset.i));
  if (!visor.classList.contains('abierto')) return;
  if (ev.target.closest('.prev')) mover(-1);
  else if (ev.target.closest('.next')) mover(1);
  else if (ev.target.closest('#vCerrar') || ev.target.classList.contains('lienzo')) cerrarVisor();
});
document.addEventListener('keydown', ev => {
  if (!visor.classList.contains('abierto')) return;
  if (ev.key === 'Escape') cerrarVisor();
  if (ev.key === 'ArrowLeft') mover(-1);
  if (ev.key === 'ArrowRight') mover(1);
});

/* ---------- Imprimir: expande los casos visibles ---------- */
$('btnImprimir').onclick = () => window.print();
window.addEventListener('beforeprint', () => document.querySelectorAll('.caso').forEach(d => d.open = true));
</script>
</body>
</html>
"""


def generar_reporte(datos, destino):
    contenido = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    destino.write_text(PLANTILLA.replace("__DATOS__", contenido), encoding="utf-8")
