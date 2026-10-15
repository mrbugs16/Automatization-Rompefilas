"""
MÓDULO 00 - HAPPY PATH (flujo completo de pago en la T6)
· HP-ROM-001 (fuera de la matriz: es la prueba base del flujo P1 -> P5)

Si esta falla, el resto del flujo con tarjeta no se puede validar.
v1.6.36: se detiene en P4 con 'No se pudo comunicar con la aplicación de pago'.
"""
import pytest

from config import settings
from config.datos_prueba import REF_VALIDA
from core.marcadores import caso, requiere_tester

pytestmark = [pytest.mark.tarjeta]


@caso(
    "HP-ROM-001",
    caso="Happy path: referencia válida → adeudos → tarjeta → recibo",
    producto="Rompefilas", modulo="General", escenario="Transacciones", tipo="Funcional", prioridad="Alta",
    precondiciones="App Rompefilas abierta en la T6 en la pantalla de inicio.",
    datos="Primera referencia 'disponible' de data/referencias.json (se marca 'pagada' al aprobarse)",
    pasos="Tocar 'Toque para iniciar'\nCapturar la referencia de 16 dígitos\nConsultar adeudos\n"
          "Pagar ahora\nElegir 'Tarjeta – Débito o crédito'\nPresentar la tarjeta en la T6\nVerificar el recibo (P5)",
    esperado="Se invoca el módulo de pago de la T6 con el total, el pago se aprueba y se muestra el recibo con autorización.",
)
def test_HP_ROM_001_happy_path(flujo, evidencia, registrar_app_pago, marcar_pagada):
    # P1 -> P2
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    contribuyente = flujo.adeudos.contribuyente()
    adeudos = flujo.adeudos.adeudos()
    evidencia.nota(f"Contribuyente: {contribuyente} · {len(adeudos)} adeudos: "
                   + ", ".join(f"{a['concepto']} {a['texto_monto']}" for a in adeudos))
    assert contribuyente == REF_VALIDA["contribuyente"], f"Contribuyente inesperado: '{contribuyente}'"

    # P2 -> P3
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3 '¿Cómo desea pagar?'"
    flujo.metodo.esperar_estable(0.8)
    total = flujo.metodo.total()
    flujo._captura("P3 - ¿Cómo desea pagar?")
    assert total == round(sum(a["monto"] for a in adeudos), 2), \
        f"El total de P3 (${total}) no es la suma de los adeudos de P2"

    # P3 -> P4
    flujo.metodo.elegir_tarjeta()
    estado = flujo.pago.esperar_respuesta()
    registrar_app_pago(estado)
    flujo.pago.esperar_estable(1)
    evidencia.captura(f"P4 - Respuesta al elegir Tarjeta: {estado}")
    assert estado != "error_app_pago", f"P4: {flujo.pago.mensaje_error()}"
    assert estado != "sin_respuesta", f"La app no respondió en {settings.TIMEOUT_APP_PAGO} s al elegir Tarjeta"

    # P4 -> P5 (requiere presentar la tarjeta)
    requiere_tester("Módulo de pago abierto: falta presentar la tarjeta física")
    resultado = flujo.esperar_tarjeta_del_tester("Presente una tarjeta CON FONDOS (chip, banda o contactless).")
    assert resultado == "aprobado", f"El cobro terminó en '{resultado}'"
    marcar_pagada()
    autorizacion = flujo.recibo.autorizacion()
    evidencia.nota(f"Autorización: {autorizacion or '(no se encontró en pantalla)'}")
    assert autorizacion, "El recibo no muestra el número de autorización"
