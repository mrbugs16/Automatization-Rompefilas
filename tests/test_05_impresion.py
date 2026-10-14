"""
MÓDULO 05 - IMPRESIÓN Y RECIBO (P5, impresora térmica de la T6)
· CP-RC-ROM-001 a CP-RC-ROM-009, CP-HW-ROM-007, CP-HW-ROM-008

Casi todos requieren un pago aprobado ('pago_aprobado'): hoy quedan Bloqueados por el módulo de pago.
El contenido del ticket físico (folio, voucher, acentos, QR) se revisa a mano.
"""
import time

import pytest

from config import locators as L
from config.datos_prueba import REF_VALIDA
from core.interaccion import pedir_accion
from core.marcadores import caso, interactiva, manual, requiere_tester

pytestmark = [pytest.mark.tarjeta]


def _sesion_limpia(flujo):
    """Tras regresar al inicio no debe quedar nada del contribuyente anterior."""
    flujo.iniciar()
    textos = flujo.identificacion.textos()
    assert REF_VALIDA["contribuyente"] not in textos, "Quedó visible el nombre del contribuyente anterior"
    assert flujo.identificacion.referencia() == L.P1_PLACEHOLDER, \
        f"Quedó capturada la referencia anterior: '{flujo.identificacion.referencia()}'"


@caso("CP-RC-ROM-001")
def test_CP_RC_ROM_001_impresion_y_regreso_al_inicio(flujo, evidencia, pago_aprobado):
    inicio = time.time()
    regreso = flujo.inicio.visible(60)
    segundos = round(time.time() - inicio)
    evidencia.captura(f"Pantalla a los {segundos} s del recibo")
    evidencia.nota("⚠ (Manual) Revisar el ticket: folio, fecha/hora, monto, referencia y sello del Gobierno de Puebla en 58 mm sin cortes")
    assert regreso, "La app no regresó al inicio después del recibo"
    assert segundos <= 40, f"La app tardó {segundos} s en regresar al inicio (esperado ~30 s)"


@caso("CP-RC-ROM-002")
@manual("Revisión del ticket físico: autorización, últimos 4 dígitos, folio, datos del adeudo y voucher sin solaparse")
def test_CP_RC_ROM_002_voucher_tarjeta():
    pass


@caso("CP-RC-ROM-003")
def test_CP_RC_ROM_003_sin_papel_pago_realizado(flujo, evidencia, pantalla_cobro):
    requiere_tester("Requiere abrir la tapa / retirar el papel y presentar una tarjeta con fondos")
    pedir_accion("ABRA la tapa de la impresora o RETIRE el rollo de papel (la suite continúa sola).", timeout=20, evidencia=evidencia)
    resultado = flujo.esperar_tarjeta_del_tester(f"Presente una tarjeta CON FONDOS por {REF_VALIDA['total']}.")
    assert resultado == "aprobado", f"Requiere un pago aprobado y el cobro terminó en '{resultado}'"
    assert flujo.recibo.existe(L.AVISO_SIN_PAPEL, 10), "No se mostró el aviso de falta de papel"
    evidencia.captura("Aviso de falta de papel con el pago aprobado")
    assert flujo.recibo.visible(2), "El pago no aparece como registrado al faltar el papel"
    pedir_accion("CARGUE el papel / cierre la tapa.", timeout=30, evidencia=evidencia)
    assert flujo.recibo.existe(L.P5_BTN_REIMPRIMIR, 5), "No hay opción 'Reimprimir' para el comprobante pendiente"
    flujo.recibo.reimprimir()
    flujo.recibo.esperar_estable(3)
    evidencia.captura("Después de 'Reimprimir'")
    evidencia.nota("⚠ (Manual) Confirmar que se imprimió el comprobante pendiente")


@caso("CP-RC-ROM-004")
@pytest.mark.lento
def test_CP_RC_ROM_004_sesion_expira_tras_comprobante(flujo, evidencia, pago_aprobado):
    vio_cuenta = flujo.recibo.existe(L.P5_CUENTA_REGRESIVA, 20)
    if vio_cuenta:
        evidencia.captura("Cuenta regresiva en el recibo")
    assert flujo.inicio.visible(90), "La sesión no expiró: la app no regresó al inicio"
    evidencia.captura("Regresó al inicio")
    assert vio_cuenta, "No se mostró cuenta regresiva antes de regresar al inicio"
    _sesion_limpia(flujo)


@caso("CP-RC-ROM-005")
@interactiva("Requiere retirar el rollo de papel antes de iniciar el flujo")
def test_CP_RC_ROM_005_aviso_sin_papel_antes_de_cobrar(flujo, evidencia):
    pedir_accion("RETIRE el rollo de papel de la T6 (la suite continúa sola).", timeout=20, evidencia=evidencia)
    try:
        avisos = {}
        avisos["inicio"] = flujo.inicio.existe(L.AVISO_SIN_PAPEL, 3)
        flujo.iniciar()
        flujo.identificacion.tocar(L.P1_BTN_PROBAR_IMPRESORA)
        avisos["probar_impresora"] = flujo.identificacion.existe(L.AVISO_SIN_PAPEL, 5)
        flujo._captura("P1 - 'Probar impresora' sin papel")
        if flujo.pantalla() != "p1":
            flujo.driver.back()
        flujo.capturar_referencia(REF_VALIDA["referencia"])
        assert flujo.consultar() == "p2", "La referencia válida no mostró adeudos"
        flujo.adeudos.pagar()
        assert flujo.metodo.visible(), "No se avanzó a P3"
        avisos["antes_de_cobrar"] = flujo.metodo.existe(L.AVISO_SIN_PAPEL, 3)
        flujo._captura("P3 sin papel (antes de cobrar)")
        evidencia.nota(f"Aviso de papel visto en: {[k for k, v in avisos.items() if v] or 'ninguna pantalla'}")
        assert avisos["antes_de_cobrar"] or avisos["inicio"], "La app no avisa la falta de papel antes de cobrar"
    finally:
        pedir_accion("Vuelva a COLOCAR el rollo de papel.", timeout=20)


@caso("CP-RC-ROM-006")
def test_CP_RC_ROM_006_limite_de_reimpresion(flujo, evidencia, pago_aprobado):
    aceptadas = 0
    for intento in range(1, 6):
        boton = flujo.recibo.driver.find_elements(*L.P5_BTN_REIMPRIMIR)
        if not boton or boton[0].get_attribute("enabled") != "true" or flujo.recibo.existe(L.P5_LIMITE_IMPRESIONES, 1):
            break
        boton[0].click()
        aceptadas += 1
        flujo.recibo.esperar_estable(3)
    evidencia.captura(f"Después de {aceptadas} impresiones aceptadas")
    evidencia.nota(f"Toques aceptados en 'Imprimir': {aceptadas} · ⚠ (Manual) contar los tickets físicos")
    assert aceptadas <= 2, f"Se permitieron {aceptadas} impresiones (máximo 2 por transacción)"


@caso("CP-RC-ROM-007")
def test_CP_RC_ROM_007_sin_estados_redundantes(flujo, evidencia, pago_aprobado):
    textos = flujo.recibo.textos()
    exitoso = [t for t in textos if "Pago exitoso" in t]
    evidencia.nota(f"Textos de estado en el recibo: {[t for t in textos if 'Pago' in t]}")
    assert not flujo.recibo.existe(L.P5_PAGO_PROCESADO, 1), "Se muestra 'Pago procesado' además de 'Pago exitoso'"
    assert len(exitoso) == 1, f"'Pago exitoso' aparece {len(exitoso)} veces"


@caso("CP-RC-ROM-008")
@manual("Revisión del ticket físico de infracción de tránsito (word-wrap en 58 mm); requiere un folio de tránsito")
def test_CP_RC_ROM_008_ticket_infraccion():
    pass


@caso("CP-RC-ROM-009")
@manual("Revisión de la ortografía y acentos del comprobante impreso")
def test_CP_RC_ROM_009_ortografia_ticket():
    pass


@caso("CP-HW-ROM-007")
@manual("20 pagos consecutivos con impresión (sobrecalentamiento del cabezal)")
def test_CP_HW_ROM_007_impresion_continua():
    pass


@caso("CP-HW-ROM-008")
@manual("Escanear el QR del ticket impreso con un teléfono")
def test_CP_HW_ROM_008_qr_del_comprobante():
    pass
