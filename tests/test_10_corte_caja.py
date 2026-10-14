"""
MÓDULO 10 - CORTE DE CAJA, HISTORIAL Y OPERACIÓN DEL EQUIPO
· CP-CC-ROM-001 a CP-CC-ROM-006

v1.6.36 no tiene menú de operador (corte, historial, cancelaciones): esos casos se detectan solos
en cuanto la app los muestre (locators.MENU_CORTE / MENU_HISTORIAL).
"""
import time

import pytest

from config import locators as L
from core import adb
from core.marcadores import caso, manual, pendiente, requiere_tester


def _buscar_menu(flujo, loc):
    """Busca la opción en el inicio y en P1 (donde podría estar el acceso de operador)."""
    if flujo.inicio.existe(loc, 2):
        return True
    flujo.iniciar()
    return flujo.identificacion.existe(loc, 2)


@caso("CP-CC-ROM-001")
def test_CP_CC_ROM_001_corte_de_caja(flujo, evidencia):
    if not _buscar_menu(flujo, L.MENU_CORTE):
        pendiente(f"No disponible en v{adb.version_app()}: no existe 'Corte de caja' / 'Cierre de lote'")
    pendiente("Menú de corte detectado: faltan los localizadores del reporte de corte")


@caso("CP-CC-ROM-002")
def test_CP_CC_ROM_002_reimpresion_desde_historial(flujo, evidencia):
    if not _buscar_menu(flujo, L.MENU_HISTORIAL):
        pendiente(f"No disponible en v{adb.version_app()}: no existe historial de transacciones")
    pendiente("Historial detectado: faltan sus localizadores")


@caso("CP-CC-ROM-003")
def test_CP_CC_ROM_003_cancelacion_por_supervisor(flujo, evidencia):
    if not _buscar_menu(flujo, L.MENU_HISTORIAL):
        pendiente(f"No aplica en v{adb.version_app()}: sin historial no hay cancelación (void) de transacciones")
    pendiente("Historial detectado: faltan credencial de supervisor y localizadores de cancelación")


@caso("CP-CC-ROM-004")
@pytest.mark.tarjeta
def test_CP_CC_ROM_004_notificacion_durante_cobro(flujo, evidencia, pantalla_cobro):
    requiere_tester("Requiere presentar una tarjeta mientras llega una notificación")
    try:
        print("\n🙋 Presente la tarjeta CON FONDOS: en 5 s la suite enviará una notificación del sistema.")
        time.sleep(5)
        adb.shell("cmd notification post -S bigtext -t 'QA Rompefilas' qa_rompefilas 'Notificación de prueba durante el cobro'")
        evidencia.nota("Notificación del sistema enviada durante el cobro")
        resultado = flujo.esperar_tarjeta_del_tester("Termine la operación con la tarjeta (NIP si se pide).")
    finally:
        adb.shell("cmd notification cancel qa_rompefilas", silencioso=True)
    assert resultado == "aprobado", f"El cobro no concluyó con la notificación (resultado: {resultado})"


@caso("CP-CC-ROM-005")
@manual("Publicar una actualización OTA y forzar su descarga durante un pago")
def test_CP_CC_ROM_005_ota_durante_transaccion():
    pass


@caso("CP-CC-ROM-006")
def test_CP_CC_ROM_006_fecha_y_hora(flujo, evidencia, pago_aprobado):
    _, fecha_t6 = adb.shell("date '+%d/%m/%Y %H:%M:%S %Z'", silencioso=True)
    _, zona = adb.shell("getprop persist.sys.timezone", silencioso=True)
    evidencia.nota(f"Hora de la T6 al aprobar: {fecha_t6.strip()} ({zona.strip()}) · PC: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    assert "Mexico" in zona or "America/" in zona, f"Zona horaria de la T6 inesperada: {zona.strip()}"
    evidencia.nota("⚠ (Manual) Comparar la hora del ticket contra la hora oficial (Puebla)")
