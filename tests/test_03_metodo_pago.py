"""
MÓDULO 03 - MÉTODO DE PAGO (P3)
· CP-MP-ROM-001 a CP-MP-ROM-003
"""
import re

import pytest

from config import locators as L
from config import settings
from config.datos_prueba import REF_VALIDA, SIN_ACENTO
from core.marcadores import caso


@caso("CP-MP-ROM-001")
@pytest.mark.tarjeta
def test_CP_MP_ROM_001_tarjeta_en_la_misma_t6(flujo, evidencia, registrar_app_pago):
    estado = flujo.pagar_con_tarjeta(REF_VALIDA["referencia"])
    registrar_app_pago(estado)
    if flujo.pago.existe(L.P4_ERROR_SUGERENCIA_EFECTIVO, 1):
        evidencia.nota("⚠ El error sugiere 'Puede pagar en efectivo como alternativa', pero la T6 no acepta efectivo (CP-MP-ROM-002)")
    assert estado != "error_app_pago", f"P4: {flujo.pago.mensaje_error()}"
    assert estado != "sin_respuesta", f"La app no respondió en {settings.TIMEOUT_APP_PAGO} s al elegir Tarjeta"
    assert not flujo.pago.existe(L.P4_SIN_CONEXION_TERMINAL, 1), "Pide una terminal externa ('No se pudo conectar con la terminal')"

    fuente = flujo.driver.page_source
    evidencia.nota(f"Módulo de pago en primer plano: {flujo.driver.current_package}")
    total = REF_VALIDA["total"].replace("$", "")
    assert total in fuente or total.replace(",", "") in fuente, f"El módulo de pago no muestra el monto {REF_VALIDA['total']}"
    assert flujo.pago.existe(L.P4_INSTRUCCION_TARJETA, 2), "No se muestra la instrucción para insertar, deslizar o acercar la tarjeta"


@caso("CP-MP-ROM-002")
def test_CP_MP_ROM_002_sin_efectivo(flujo, evidencia):
    flujo.ir_a_metodo(REF_VALIDA["referencia"])
    metodos = flujo.metodo.metodos()
    evidencia.nota(f"Métodos de pago mostrados: {metodos}")
    assert not flujo.metodo.existe(L.P3_BTN_EFECTIVO, 1), "La opción 'Efectivo' se muestra en la T6"
    assert not [m for m in metodos if "fectivo" in m], f"Se ofrece efectivo: {metodos}"


@caso("CP-MP-ROM-003")
def test_CP_MP_ROM_003_ortografia_metodo_de_pago(flujo, evidencia):
    textos_inicio = flujo.inicio.textos()
    flujo.ir_a_metodo(REF_VALIDA["referencia"])
    boton = flujo.metodo.boton_tarjeta()
    evidencia.nota(f"Botón de tarjeta: '{boton}'")
    textos = textos_inicio + flujo.metodo.textos()

    errores = [f"'{mal}' (debe ser '{bien}')" for mal, bien in SIN_ACENTO.items()
               for t in textos if re.search(rf"\b{mal}\b", t)]
    assert not errores, f"Palabras sin acento: {sorted(set(errores))}"
    assert "Débito" in boton and "crédito" in boton.lower(), f"El botón de tarjeta no dice 'Débito o crédito': '{boton}'"
    # En el inicio todo el contenido está dentro del botón 'Toque para iniciar' y UiAutomator2 no expone
    # sus textos; 'Crédito y Débito' / 'Visa, Mastercard y más' se validan en la captura del inicio.
    if any("Visa, Mastercard" in t for t in textos_inicio):
        assert "Crédito y Débito" in textos_inicio, "La pantalla de inicio no muestra 'Crédito y Débito'"
        assert any("Visa, Mastercard y más" in t for t in textos_inicio), "La pantalla de inicio no muestra 'Visa, Mastercard y más'"
    else:
        evidencia.nota("⚠ (Manual) Textos del inicio no expuestos por accesibilidad: revisar 'Crédito y Débito' y "
                       "'Visa, Mastercard y más' en la captura 'Inicio'")
    fuera = flujo.metodo.fuera_de_pantalla()
    assert not fuera, f"Textos cortados o fuera de pantalla: {fuera}"
