"""
MÓDULO 07 - KIOSKO Y HARDWARE DE LA T6
· CP-IN-ROM-001 a CP-IN-ROM-004, CP-HW-ROM-001 a CP-HW-ROM-006, CP-HW-ROM-009
"""
import time

import pytest

from config import locators as L
from config import settings
from config.datos_prueba import REF_INEXISTENTE, REF_VALIDA
from core import adb
from core.driver_factory import reiniciar_app
from core.marcadores import caso, manual, pendiente

KEYCODES = (("Inicio (HOME)", 3), ("Recientes", 187), ("Atrás", 4))


@caso("CP-IN-ROM-001")
@pytest.mark.reinicio
def test_CP_IN_ROM_001_arranque_automatico(evidencia):
    arranque = adb.reiniciar_y_esperar()
    assert arranque is not None, "La T6 no terminó de arrancar en 3 min"
    evidencia.nota(f"Android arrancó en {arranque} s")
    inicio, foco = time.time(), ""
    while time.time() - inicio < 90:
        foco = adb.ventana_en_foco()
        if settings.APP_PACKAGE in foco:
            break
        time.sleep(2)
    evidencia.captura(f"Pantalla tras el arranque: {foco or 'sin ventana'}")
    assert settings.APP_PACKAGE in foco, f"Rompefilas no se abrió sola tras reiniciar (en pantalla: {foco})"
    evidencia.nota(f"Rompefilas en primer plano {round(time.time() - inicio)} s después del arranque")


@caso("CP-IN-ROM-002")
def test_CP_IN_ROM_002_modo_kiosko(flujo, evidencia):
    escapes = []
    for nombre, keycode in KEYCODES:
        flujo.driver.press_keycode(keycode)
        time.sleep(2)
        foco = adb.ventana_en_foco()
        evidencia.captura(f"Después de '{nombre}': {foco}")
        if settings.APP_PACKAGE not in foco:
            escapes.append(f"'{nombre}' llevó a {foco}")
            flujo.driver.activate_app(settings.APP_PACKAGE)
            time.sleep(3)

    adb.expandir_notificaciones_con_gesto()
    foco = adb.ventana_en_foco()
    evidencia.captura(f"Después de deslizar la barra de notificaciones: {foco}")
    if "NotificationShade" in foco or "systemui" in foco:
        escapes.append("Se abre la barra de notificaciones (acceso a ajustes rápidos)")
    adb.cerrar_notificaciones()
    assert not escapes, "Se puede salir de la app: " + " · ".join(escapes)


def _hay_acceso_operador(flujo):
    return flujo.inicio.existe(L.OPERADOR_BTN_INGRESAR, 2) and not flujo.inicio.existe(L.INICIO_BTN, 1)


@caso("CP-IN-ROM-003")
def test_CP_IN_ROM_003_acceso_operador(flujo, evidencia):
    if not _hay_acceso_operador(flujo):
        pendiente(f"No aplica en v{adb.version_app()}: la app abre directo en el kiosko, sin acceso de operador")
    pendiente("Pantalla de operador detectada: faltan credenciales de operador de pruebas y sus localizadores")


@caso("CP-IN-ROM-004")
def test_CP_IN_ROM_004_acceso_operador_invalido(flujo, evidencia):
    if not _hay_acceso_operador(flujo):
        pendiente(f"No aplica en v{adb.version_app()}: la app abre directo en el kiosko, sin acceso de operador")
    pendiente("Pantalla de operador detectada: faltan sus localizadores")


@caso("CP-HW-ROM-001")
def test_CP_HW_ROM_001_bateria_baja(flujo, evidencia):
    vistos = {}
    try:
        adb.simular_bateria(10)
        evidencia.nota("Batería simulada al 10 % y desconectada (dumpsys battery)")
        # Android muestra su propio diálogo encima de la app (no es un aviso de Rompefilas)
        if flujo.inicio.existe(L.ANDROID_BATERIA_BAJA, 8):
            evidencia.captura("Diálogo de Android 'Recordatorio de baja electricidad'")
            evidencia.nota("⚠ El diálogo de Android muestra la barra de estado y los botones de navegación sobre el kiosko")
            flujo.inicio.tocar(L.ANDROID_BTN_CERRAR)
        # Se reabre la app (equivale a iniciar una atención con la batería ya baja)
        reiniciar_app(flujo.driver)
        vistos["inicio"] = flujo.inicio.existe(L.AVISO_BATERIA_BAJA, 3)
        flujo.iniciar()
        vistos["P1"] = flujo.identificacion.existe(L.AVISO_BATERIA_BAJA, 2)
        flujo.capturar_referencia(REF_VALIDA["referencia"])
        assert flujo.consultar() == "p2", "La referencia válida no mostró adeudos"
        flujo.adeudos.pagar()
        assert flujo.metodo.visible(), "No se avanzó a P3"
        vistos["P3 (antes de cobrar)"] = flujo.metodo.existe(L.AVISO_BATERIA_BAJA, 2)
        flujo._captura("P3 con batería al 10 %")
    finally:
        adb.bateria_real()
    evidencia.nota(f"Aviso de batería baja visto en: {[k for k, v in vistos.items() if v] or 'ninguna pantalla'}")
    assert any(vistos.values()), "La app no avisa la batería baja antes de cobrar"


@caso("CP-HW-ROM-002")
@manual("Apagar/reiniciar la T6 justo después de presentar la tarjeta y conciliar al volver a abrir")
def test_CP_HW_ROM_002_apagado_durante_transaccion():
    pass


@caso("CP-HW-ROM-003")
def test_CP_HW_ROM_003_operacion_cargando(flujo, evidencia, pago_aprobado):
    _, estado = adb.shell("dumpsys battery", silencioso=True)
    alimentacion = [l.strip() for l in estado.splitlines() if "powered: true" in l]
    evidencia.nota(f"Alimentación durante el pago: {alimentacion or 'batería'}")
    assert alimentacion, "La T6 no estaba conectada al cargador durante la prueba"


@caso("CP-HW-ROM-004")
@manual("Escaneo en exterior con luz solar directa y con poca luz")
def test_CP_HW_ROM_004_escaneo_con_luz_variable():
    pass


@caso("CP-HW-ROM-005")
@manual("Legibilidad de la pantalla en exterior")
def test_CP_HW_ROM_005_legibilidad_exterior():
    pass


@caso("CP-HW-ROM-006")
def test_CP_HW_ROM_006_diseno_resolucion_t6(flujo, evidencia):
    dpi = adb.densidad()
    minimo_px = settings.MIN_TOQUE_DP * dpi / 160
    dp = lambda px: round(px * 160 / dpi)  # noqa: E731
    fuera, pequenos = {}, {}

    def revisar(pantalla):
        page = flujo.identificacion
        page.esperar_estable(0.8)
        nodos = page.nodos()
        flujo._captura(f"Diseño - {pantalla}")
        if page.fuera_de_pantalla(nodos):
            fuera[pantalla] = page.fuera_de_pantalla(nodos)
        chicos = sorted({f"'{t}' ({dp(x2 - x1)}×{dp(y2 - y1)} dp)" for clase, t, clic, (x1, y1, x2, y2) in nodos
                         if clase.endswith("Button") and clic and t and min(x2 - x1, y2 - y1) < minimo_px})
        if chicos:
            pequenos[pantalla] = chicos

    revisar("Inicio")
    flujo.iniciar()
    revisar("P1 Identificar")
    flujo.identificacion.tocar(L.P1_BTN_CUENTA_PREDIAL)
    flujo.identificacion.tocar(L.P1_BTN_PU)
    revisar("P1 Cuenta predial PU")
    flujo.identificacion.tocar(L.P1_BTN_FOLIO_16)
    flujo.capturar_referencia(REF_INEXISTENTE, captura=False)
    flujo.consultar()
    revisar("P1 Sin adeudos")
    flujo.identificacion.borrar_todo()
    flujo.capturar_referencia(REF_VALIDA["referencia"], captura=False)
    assert flujo.consultar() == "p2", "La referencia válida no mostró adeudos"
    revisar("P2 Adeudos")
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3"
    revisar("P3 Método")
    flujo.metodo.elegir_tarjeta()
    if flujo.pago.esperar_respuesta() == "error_app_pago":
        revisar("P4 Error de pago")

    orientacion = flujo.driver.orientation
    evidencia.nota(f"Densidad {dpi} dpi · mínimo {settings.MIN_TOQUE_DP} dp = {round(minimo_px)} px · orientación {orientacion}")
    for pantalla, botones in pequenos.items():
        evidencia.nota(f"Botones < {settings.MIN_TOQUE_DP} dp en {pantalla}: {', '.join(botones)}")
    assert orientacion == "PORTRAIT", f"La orientación no es vertical: {orientacion}"
    assert not fuera, f"Textos fuera de la pantalla: {fuera}"
    assert not pequenos, (f"Botones con área táctil menor a {settings.MIN_TOQUE_DP} dp en "
                          f"{len(pequenos)} pantalla(s): " + "; ".join(f"{p}: {', '.join(b)}" for p, b in pequenos.items()))


@caso("CP-HW-ROM-009")
@manual("Sonido o vibración al leer el código y al aprobar/declinar el pago")
def test_CP_HW_ROM_009_retroalimentacion_sonora():
    pass
