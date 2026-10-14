"""
MÓDULO 09 - INTEGRIDAD DE COBRO
· CP-IC-ROM-001 a CP-IC-ROM-003
"""
import pytest

from config import locators as L
from config.datos_prueba import REF_PAGADAS, REF_VALIDA
from core import adb
from core.marcadores import bloqueado, caso, manual, pendiente


@caso("CP-IC-ROM-001")
@manual("Pagar la misma referencia en el Tótem/Kiosco y luego intentarlo en la T6")
def test_CP_IC_ROM_001_misma_referencia_totem_y_t6():
    pass


def _instancias_en_pila():
    """Actividades en la pila de tareas (para detectar dos módulos de pago abiertos)."""
    _, salida = adb.shell("dumpsys activity activities", silencioso=True)
    return [l.strip() for l in salida.splitlines() if "ActivityRecord{" in l and "Hist" in l]


@caso("CP-IC-ROM-002")
@pytest.mark.tarjeta
def test_CP_IC_ROM_002_doble_toque(flujo, evidencia, registrar_app_pago):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])

    # Doble toque en 'Pagar ahora': una sola navegación a P3
    flujo.adeudos.doble_toque(L.P2_BTN_PAGAR)
    assert flujo.metodo.visible(), "El doble toque en 'Pagar ahora' no llevó a P3"
    flujo.metodo.esperar_estable(1)
    flujo._captura("P3 tras doble toque en 'Pagar ahora'")
    flujo.metodo.regresar_a_adeudos()
    assert flujo.adeudos.visible(5), "'Regresar a adeudos' no regresó a P2 (¿se apilaron dos P3?)"
    flujo._captura("P2 tras 'Regresar a adeudos'")
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3"

    # Doble toque en 'Tarjeta': una sola solicitud de cobro
    pila_antes = len(_instancias_en_pila())
    flujo.metodo.doble_toque(L.P3_BTN_TARJETA)
    estado = flujo.pago.esperar_respuesta()
    registrar_app_pago(estado)
    flujo.pago.esperar_estable(1)
    flujo._captura(f"Tras doble toque en 'Tarjeta': {estado}")
    if estado in ("error_app_pago", "sin_respuesta"):
        bloqueado("Doble toque en 'Pagar ahora' OK (una sola P3); el de 'Tarjeta' requiere el módulo de pago "
                  f"('{flujo.pago.mensaje_error() or estado}')")
    nuevas = len(_instancias_en_pila()) - pila_antes
    evidencia.nota(f"Actividades nuevas en la pila tras el doble toque: {nuevas}")
    assert nuevas <= 1, f"El doble toque abrió {nuevas} pantallas de cobro (se esperaba una)"
    evidencia.nota("⚠ (Manual) Confirmar en el adquirente que solo hubo una solicitud de cobro")


@caso("CP-IC-ROM-003")
def test_CP_IC_ROM_003_referencia_ya_pagada(flujo, evidencia):
    if not REF_PAGADAS:
        pendiente("Sin referencias pagadas en data/referencias.json -> 'pagadas' (se agregan tras un pago aprobado)")
    flujo.iniciar()
    flujo.capturar_referencia(REF_PAGADAS[-1])
    resultado = flujo.consultar()
    flujo._captura(f"Consulta de la referencia pagada: {resultado}")
    if resultado == "p2":
        pendientes = flujo.adeudos.adeudos()
        evidencia.nota(f"Adeudos mostrados: {[(a['concepto'], a['texto_monto']) for a in pendientes]}")
        assert not flujo.adeudos.existe(L.P2_BTN_PAGAR, 1) or not pendientes, \
            "La referencia ya pagada sigue mostrando adeudos pendientes para cobrar"
    else:
        assert resultado == "sin_adeudos", f"Respuesta inesperada al consultar la referencia pagada: {resultado}"
