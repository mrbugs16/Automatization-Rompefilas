"""
MÓDULO 10 - CORTE DE CAJA, HISTORIAL Y OPERACIÓN DEL EQUIPO
· CP-CC-ROM-001 a CP-CC-ROM-006

v1.6.36 no tiene menú de operador (corte, historial, cancelaciones): esos casos se detectan solos
en cuanto la app los muestre (locators.MENU_CORTE / MENU_HISTORIAL).
"""
import re
import time
from datetime import datetime

import pytest

from config import locators as L
from core import adb
from core.marcadores import caso, manual, pendiente

MESES = {m: i for i, m in enumerate(('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
                                     'septiembre', 'octubre', 'noviembre', 'diciembre'), 1)}


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
    try:
        adb.shell("cmd notification post -S bigtext -t 'QA Rompefilas' qa_rompefilas 'Notificación de prueba durante el cobro'")
        evidencia.nota("Notificación del sistema enviada con el cobro en curso")
        time.sleep(2)
        evidencia.captura("Notificación con el módulo de pago abierto")
        resultado = flujo.completar_cobro("aprobado", "Termine la operación con la tarjeta (NIP si se pide).")
    finally:
        adb.shell("cmd notification cancel qa_rompefilas", silencioso=True)
    assert resultado == "aprobado", f"El cobro no concluyó con la notificación (resultado: {resultado})"
    assert flujo.recibo.visible(10), "Tras la notificación no se mostró el comprobante"


@caso("CP-CC-ROM-005")
@manual("Publicar una actualización OTA y forzar su descarga durante un pago")
def test_CP_CC_ROM_005_ota_durante_transaccion():
    pass


@caso("CP-CC-ROM-006")
def test_CP_CC_ROM_006_fecha_y_hora(flujo, evidencia, pago_aprobado):
    """Compara la fecha/hora del comprobante con el reloj de la T6 (zona horaria de Puebla)."""
    datos = flujo.recibo.datos()
    _, zona = adb.shell("getprop persist.sys.timezone", silencioso=True)
    _, reloj = adb.shell("date '+%d/%m/%Y %H:%M'", silencioso=True)
    evidencia.nota(f"Comprobante: '{datos.get('Fecha', '')}' · T6: {reloj.strip()} ({zona.strip()})")
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4}) (\d{1,2}):(\d{2})", datos.get("Fecha", ""))
    assert m, f"El comprobante no muestra fecha y hora: '{datos.get('Fecha', '')}'"
    dia, mes, anio, hora, minuto = m.groups()
    comprobante = datetime(int(anio), MESES[mes.lower()], int(dia), int(hora), int(minuto))
    t6 = datetime.strptime(reloj.strip(), "%d/%m/%Y %H:%M")
    diferencia = round((comprobante - t6).total_seconds() / 60)
    evidencia.nota(f"Diferencia comprobante − reloj de la T6: {diferencia} min")
    assert abs(diferencia) <= 5, (f"La hora del comprobante ({comprobante:%d/%m/%Y %H:%M}) difiere {diferencia} min de la "
                                  f"hora de la T6 ({t6:%d/%m/%Y %H:%M}, {zona.strip()})")
    evidencia.nota("⚠ (Manual) Comparar también la hora del ticket impreso")
