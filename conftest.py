"""
Fixtures y hooks de pytest:
- driver (una sesión de Appium para toda la corrida; la app se reinicia antes de cada caso)
- evidencia / flujo / pantalla_cobro
- Registro de resultados por caso y generación del reporte HTML + matriz con resultados.
"""
import json
import time
import urllib.request
import webbrowser
from datetime import datetime

import pytest

from config import settings
from config.datos_prueba import MSG_APP_PAGO, REF_VALIDA
from core import adb
from core.driver_factory import crear_driver, reiniciar_app, sesion_viva
from core.evidencia import Evidencia
from core.marcadores import PREFIJO_MANUAL, PREFIJO_PENDIENTE, bloqueado, requiere_tester
from core.matriz import cargar_matriz, escribir_resultados
from core.reporte_html import generar_reporte
from pages.kiosko_pages import FlujoKiosko

EJECUCION = datetime.now().strftime("%Y%m%d_%H%M%S")
DIR_EJECUCION = settings.DIR_EVIDENCIAS / EJECUCION
RESULTADOS = {}
INICIO = datetime.now()
SESION = {"driver": None}
APP_PAGO = {}  # primera respuesta al elegir 'Tarjeta' (para no repetir el intento en cada caso de tarjeta)


def pytest_addoption(parser):
    parser.addoption("--abrir-reporte", action="store_true", help="Abre el reporte HTML al terminar")
    parser.addoption("--incluir-reinicio", action="store_true", help="Corre CP-IN-ROM-001 (reinicia la T6)")


def pytest_configure(config):
    if config.option.collectonly or getattr(config.option, "help", False):
        return
    serial = adb.dispositivo_conectado()
    if not serial:
        pytest.exit("No hay una T6 conectada por ADB (revisa 'adb devices' y la depuración USB).", returncode=3)
    try:
        urllib.request.urlopen(f"{settings.APPIUM_URL}/status", timeout=5)
    except Exception:
        pytest.exit(f"Appium no responde en {settings.APPIUM_URL}. Levántalo con: appium --relaxed-security", returncode=3)
    print(f"\nT6: {serial} · Rompefilas v{adb.version_app() or '?'} · Modo {'INTERACTIVO' if settings.INTERACTIVO else 'desatendido'}")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--incluir-reinicio"):
        omitir = pytest.mark.skip(reason=f"{PREFIJO_MANUAL} Reinicia la T6: correr con --incluir-reinicio")
        for item in items:
            if item.get_closest_marker("reinicio"):
                item.add_marker(omitir)


def _caso_id(item):
    marca = item.get_closest_marker("caso")
    return marca.args[0] if marca else item.name


# ==============================================
# FIXTURES
# ==============================================
@pytest.fixture
def evidencia(request):
    ev = Evidencia(_caso_id(request.node), DIR_EJECUCION)
    request.node.evidencia = ev
    return ev


@pytest.fixture
def driver(evidencia):
    """Reutiliza la sesión de Appium (se recrea si se cayó, ej. tras reiniciar la T6) y reinicia la app."""
    if SESION["driver"] is None or not sesion_viva(SESION["driver"]):
        SESION["driver"] = crear_driver()
    drv = SESION["driver"]
    reiniciar_app(drv)
    evidencia.driver = drv
    yield drv
    adb.cerrar_notificaciones()


@pytest.fixture
def flujo(driver, evidencia):
    return FlujoKiosko(driver, evidencia)


@pytest.fixture
def pantalla_cobro(flujo, evidencia):
    """Lleva el flujo con la referencia válida hasta el módulo de pago de la T6.
    Si la app no se puede comunicar con la aplicación de pago, el caso queda Bloqueado (sin repetir el intento)."""
    previo = APP_PAGO.get("estado")
    if previo in ("error_app_pago", "sin_respuesta"):
        bloqueado(f"'{MSG_APP_PAGO}' al elegir Tarjeta (visto en {APP_PAGO['caso']}); no se puede presentar la tarjeta")
    estado = flujo.pagar_con_tarjeta(REF_VALIDA["referencia"])
    APP_PAGO.setdefault("estado", estado)
    APP_PAGO.setdefault("caso", evidencia.caso_id)
    if estado == "error_app_pago":
        bloqueado(f"'{MSG_APP_PAGO}' al elegir Tarjeta; no se puede presentar la tarjeta")
    if estado == "sin_respuesta":
        bloqueado(f"La app no respondió en {settings.TIMEOUT_APP_PAGO} s al elegir Tarjeta")
    return estado


@pytest.fixture
def pago_aprobado(pantalla_cobro, flujo):
    """Precondición 'pago aprobado': el tester presenta una tarjeta con fondos (INTERACTIVO=true)."""
    requiere_tester("Requiere un pago aprobado con tarjeta física")
    resultado = flujo.esperar_tarjeta_del_tester(
        f"Presente una tarjeta CON FONDOS (débito o crédito) por {REF_VALIDA['total']} y capture el NIP si se pide.")
    if resultado != "aprobado":
        bloqueado(f"Requiere un pago aprobado y el cobro terminó en '{resultado}'")
    return resultado


@pytest.fixture
def registrar_app_pago(evidencia):
    """Para que el caso que valida el módulo de pago comparta su resultado con los de tarjeta."""
    def _registrar(estado):
        APP_PAGO.setdefault("estado", estado)
        APP_PAGO.setdefault("caso", evidencia.caso_id)
    return _registrar


def _cerrar_sesion():
    if SESION["driver"] is not None:
        try:
            SESION["driver"].quit()
        except Exception:
            pass


# ==============================================
# REGISTRO DE RESULTADOS
# ==============================================
def _clasificar(reporte):
    if reporte.passed:
        return "Aprobado", "Resultado conforme a lo esperado"
    if reporte.skipped:
        motivo = reporte.longrepr[2] if isinstance(reporte.longrepr, tuple) else str(reporte.longrepr)
        motivo = motivo.replace("Skipped: ", "")
        if motivo.startswith(PREFIJO_MANUAL):
            return "Manual", motivo[len(PREFIJO_MANUAL):].strip()
        if motivo.startswith(PREFIJO_PENDIENTE):
            return "Pendiente", motivo[len(PREFIJO_PENDIENTE):].strip()
        return "Pendiente", motivo
    if reporte.when == "call":
        return "Fallido", ""
    return "Error", ""


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    salida = yield
    reporte = salida.get_result()
    caso_id = _caso_id(item)

    # Solo nos interesa el resultado de la ejecución, o el setup si falló/se omitió
    if reporte.when == "setup" and reporte.passed:
        item._inicio = time.time()
        return
    if reporte.when == "teardown" and (reporte.passed or caso_id in RESULTADOS):
        return

    estado, obtenido = _clasificar(reporte)
    ev = getattr(item, "evidencia", None)
    error = ""
    if estado in ("Fallido", "Error"):
        error = reporte.longreprtext[-4000:]
        mensaje = str(call.excinfo.value) if call.excinfo else ""
        obtenido = mensaje.splitlines()[0] if mensaje else "Error durante la ejecución"
        if ev:
            ev.captura(f"FALLO - {obtenido[:80]}", estado="fallo", guardar_fuente=True)
    elif estado == "Aprobado" and ev:
        ev.captura("Resultado final", estado="ok")
    elif estado == "Pendiente" and ev and ev.driver is not None:
        ev.captura("Pantalla al quedar bloqueado")

    marca = item.get_closest_marker("caso")
    RESULTADOS[caso_id] = {
        "estado": estado,
        "obtenido": obtenido,
        "error": error,
        "duracion": round(time.time() - getattr(item, "_inicio", time.time()), 1),
        "pasos_evidencia": ev.pasos if ev else [],
        "meta": dict(marca.kwargs) if marca else {"caso": item.name},
    }


def pytest_sessionfinish(session, exitstatus):
    _cerrar_sesion()
    if not RESULTADOS:
        return
    DIR_EJECUCION.mkdir(parents=True, exist_ok=True)
    matriz = cargar_matriz()

    casos = []
    # 1) Casos fuera de la matriz (ej. happy path de punta a punta)
    for caso_id, r in RESULTADOS.items():
        if caso_id not in matriz:
            casos.append({"id": caso_id, **r["meta"], **{k: v for k, v in r.items() if k != "meta"}})
    # 2) Los casos de la matriz, en su orden, ejecutados o no
    for caso_id, fila in matriz.items():
        r = RESULTADOS.get(caso_id, {"estado": "No ejecutado", "obtenido": "", "error": "", "duracion": 0, "pasos_evidencia": []})
        casos.append({**fila, **{k: v for k, v in r.items() if k != "meta"}})

    fin = datetime.now()
    datos_reporte = {
        "ejecucion": EJECUCION,
        "inicio": INICIO.strftime("%d/%m/%Y %H:%M:%S"),
        "fin": fin.strftime("%H:%M:%S"),
        "fin_completo": fin.strftime("%d/%m/%Y %H:%M:%S"),
        "duracion_total": round((fin - INICIO).total_seconds()),
        "dispositivo": adb.info_dispositivo(),
        "interactivo": settings.INTERACTIVO,
        "casos": casos,
    }
    (DIR_EJECUCION / "resultados.json").write_text(json.dumps(datos_reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    reporte = DIR_EJECUCION / "reporte.html"
    generar_reporte(datos_reporte, reporte)
    escribir_resultados(
        {c["id"]: c for c in casos if c["estado"] != "No ejecutado"},
        DIR_EJECUCION / "matriz_resultados.xlsx",
    )

    print(f"\n📊 Reporte: {reporte}")
    if session.config.getoption("--abrir-reporte"):
        webbrowser.open(reporte.as_uri())
