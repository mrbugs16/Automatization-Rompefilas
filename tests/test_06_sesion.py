"""
MÓDULO 06 - SESIÓN (inactividad, tiempo de atención y limpieza entre contribuyentes)
· CP-ES-ROM-001, CP-ES-ROM-002, CP-SG-ROM-003
"""
import time

import pytest

from config import locators as L
from config import settings
from config.datos_prueba import REF_VALIDA
from core.marcadores import caso


def _sin_datos_del_contribuyente(flujo, evidencia, momento):
    """Inicia una atención nueva y verifica que no quede nada de la anterior."""
    flujo.iniciar()
    flujo._captura(f"Nueva atención después de {momento}")
    p1 = flujo.identificacion
    textos = p1.textos()
    # Datos del contribuyente atendido (no REF_VALIDA: tras un pago ya apunta a la siguiente referencia)
    restos = [t for t in textos if t == evidencia.contribuyente or t.startswith("$") or evidencia.referencia in t]
    assert not restos, f"Después de {momento} siguen visibles datos del contribuyente anterior: {restos}"
    assert p1.referencia() == L.P1_PLACEHOLDER, f"Después de {momento} quedó la referencia '{p1.referencia()}' en el campo"


@caso("CP-ES-ROM-001")
@pytest.mark.lento
def test_CP_ES_ROM_001_inactividad(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    inicio = time.time()
    segundos_aviso = flujo.inactividad.esperar_aviso(settings.TIMEOUT_INACTIVIDAD)
    assert segundos_aviso is not None, f"No apareció el aviso de inactividad en {settings.TIMEOUT_INACTIVIDAD} s"
    cuenta = flujo.inactividad.cuenta_regresiva()
    evidencia.captura(f"Aviso '¿Sigue ahí?' a los {segundos_aviso} s")
    evidencia.nota(f"Aviso a los {segundos_aviso} s sin actividad · '{cuenta}'")
    assert "se cerrará en" in cuenta, "El aviso no muestra la cuenta regresiva"

    assert flujo.inicio.visible(90), "Al terminar la cuenta regresiva no regresó al inicio"
    total = round(time.time() - inicio)
    evidencia.captura(f"Regresó al inicio a los {total} s")
    evidencia.nota(f"Regreso al inicio a los {total} s sin actividad (matriz: '> 2 minutos'; confirmar el tiempo de negocio)")
    _sin_datos_del_contribuyente(flujo, evidencia, "la expiración")
    assert not flujo.pago.existe(L.P4_ERROR_TITULO, 1), "Quedó un intento de cobro tras la expiración"


@caso("CP-ES-ROM-002")
def test_CP_ES_ROM_002_tiempo_total_de_atencion(flujo, evidencia, pago_aprobado):
    total = round(time.time() - flujo.t_inicio)
    regreso = flujo.inicio.visible(60)
    evidencia.nota(f"Tiempo de 'Toque para iniciar' al pago aprobado: {total} s (objetivo ≤ {settings.TIEMPO_MAX_ATENCION} s)")
    assert regreso, "No regresó al inicio tras el pago"
    assert total <= settings.TIEMPO_MAX_ATENCION, f"La atención tomó {total} s (objetivo ≤ {settings.TIEMPO_MAX_ATENCION} s)"


@caso("CP-SG-ROM-003")
def test_CP_SG_ROM_003_limpieza_entre_atenciones(flujo, evidencia, request):
    # Salidas que hoy sí se pueden recorrer
    flujo.ir_a_metodo(REF_VALIDA["referencia"])
    flujo.metodo.cancelar_y_salir()
    assert flujo.inicio.visible(), "'Cancelar y salir' no regresó al inicio"
    _sin_datos_del_contribuyente(flujo, evidencia, "'Cancelar y salir'")

    flujo.capturar_referencia(REF_VALIDA["referencia"])
    assert flujo.consultar() == "p2", "La referencia válida no mostró adeudos"
    flujo.adeudos.cambiar_referencia()
    flujo.identificacion.regresar_al_inicio()
    assert flujo.inicio.visible(), "'Regresar al inicio' no regresó al inicio"
    _sin_datos_del_contribuyente(flujo, evidencia, "'Regresar al inicio'")

    # La precondición de la matriz es un pago completado del contribuyente A (simulador: 'Approved')
    flujo.identificacion.regresar_al_inicio()
    assert flujo.inicio.visible(), "'Regresar al inicio' no regresó al inicio"
    request.getfixturevalue("pago_aprobado")
    evidencia.nota(f"Pago completado del contribuyente A: {evidencia.contribuyente} · ref {evidencia.referencia}")
    assert flujo.inicio.visible(60), "No regresó al inicio después del pago"
    _sin_datos_del_contribuyente(flujo, evidencia, "un pago completado")
