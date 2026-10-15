"""
MÓDULO 04 - TARJETA (P4: cobro en el módulo de pago integrado de la T6)
· CP-TJ-ROM-001 a CP-TJ-ROM-012, CP-SG-ROM-001, CP-SG-ROM-002

v1.6.37: el módulo de pago es el simulador de Memphis (solo 'Approved' / 'Declined'):
- Se automatizan los resultados que el simulador sí produce: rechazo (CP-TJ-ROM-002) y pago aprobado
  (CP-SG-ROM-001 vía 'pago_aprobado').
- Los que dependen de la tarjeta física (chip, banda, contactless, NIP, timeout de lectura, cancelar en el
  pinpad) quedan Pendientes hasta que se integre la animación para insertar la tarjeta y capturar el NIP.
  Con el pinpad real se guían con INTERACTIVO=true.
"""
import re
import time

import pytest

from config import locators as L
from config import settings
from core import adb
from core.marcadores import SIN_ANIMACION_TARJETA, caso, manual, pendiente

pytestmark = [pytest.mark.tarjeta]


def _luhn(numero):
    digitos = [int(d) for d in numero][::-1]
    total = sum(d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2) for i, d in enumerate(digitos))
    return total % 10 == 0


def _tarjeta_aprobada(flujo, instruccion, evidencia, tipo=""):
    flujo.exigir_pinpad_real(instruccion)
    resultado = flujo.esperar_tarjeta_del_tester(instruccion)
    assert resultado == "aprobado", f"El cobro terminó en '{resultado}'"
    assert flujo.recibo.visible(5), "No se avanzó a P5 con la confirmación de pago"
    autorizacion = flujo.recibo.autorizacion()
    evidencia.nota(f"Autorización: {autorizacion or '(no visible)'}")
    assert autorizacion, "P5 no muestra el número de autorización"
    if tipo:
        evidencia.nota(f"⚠ (Manual) Verificar en el ticket que la transacción se identifique como '{tipo}'")


@caso("CP-TJ-ROM-001")
def test_CP_TJ_ROM_001_debito_chip_aprobado(flujo, evidencia, pantalla_cobro):
    _tarjeta_aprobada(flujo, "Inserte una tarjeta de DÉBITO con chip y capture el NIP en la pantalla segura.", evidencia, "Débito")


@caso("CP-TJ-ROM-002")
def test_CP_TJ_ROM_002_tarjeta_declinada(flujo, evidencia, pantalla_cobro):
    resultado = flujo.completar_cobro("rechazado", "Inserte una tarjeta SIN FONDOS suficientes y capture el NIP.")
    assert resultado == "rechazado", f"Se esperaba 'No se pudo procesar el pago' y el cobro terminó en '{resultado}'"
    evidencia.nota(f"Mensaje: {flujo.pago.mensaje_error()} · "
                   f"{next((t for t in flujo.pago.textos() if 'Declined' in t), '')}")
    assert flujo.pago.existe(L.P4_ERROR_SIN_CARGO, 2), "No se informa que no se realizó ningún cargo"
    assert flujo.pago.existe(L.P4_BTN_INTENTAR, 2), "Falta la opción 'Intentar de nuevo'"
    assert flujo.pago.existe(L.P4_BTN_REGRESAR_INICIO, 2), "Falta la opción 'Regresar al inicio'"
    assert not flujo.recibo.visible(2), "Se mostró el comprobante de un pago declinado"
    evidencia.nota("⚠ (Manual) Confirmar que NO se imprimió comprobante")
    # El adeudo debe seguir pendiente: la misma referencia se puede volver a consultar con adeudos
    flujo.pago.regresar_al_inicio()
    assert flujo.inicio.visible(), "'Regresar al inicio' no regresó a la pantalla de inicio"
    flujo.iniciar()
    flujo.capturar_referencia(evidencia.referencia, captura=False)
    assert flujo.consultar() == "p2", "Tras el rechazo la referencia ya no muestra adeudos (se registró como pagada)"
    flujo._captura("La referencia sigue con adeudos tras el rechazo")


@caso("CP-TJ-ROM-003")
@pytest.mark.lento
def test_CP_TJ_ROM_003_timeout_sin_tarjeta(flujo, evidencia, pantalla_cobro):
    if flujo.pago.es_simulador():
        pendiente(f"{SIN_ANIMACION_TARJETA}. El simulador no expira (esperó 45 s sin cambio el 15/10/2026)")
    inicio = time.time()
    resultado = flujo.pago.esperar_resultado(settings.TIMEOUT_TARJETA_SIN_ACCION)
    segundos = round(time.time() - inicio)
    flujo.pago.esperar_estable(1)
    evidencia.captura(f"Sin tarjeta después de {segundos} s: {resultado}")
    evidencia.nota(f"Tiempo hasta cancelar la lectura: {segundos} s (matriz: ~45 s)")
    assert not flujo.pago.existe(L.P4_SIN_CONEXION_TERMINAL, 1), \
        "Muestra 'No se pudo conectar con la terminal' (la terminal es la misma T6)"
    assert resultado == "tiempo_agotado", \
        f"A los {settings.TIMEOUT_TARJETA_SIN_ACCION} s no se mostró el mensaje de tiempo agotado (resultado: {resultado})"
    assert flujo.pago.existe(L.P4_BTN_INTENTAR, 2) or flujo.pago.existe(L.P2_BTN_CAMBIAR_REFERENCIA, 2), \
        "No se ofrece reintentar o cambiar referencia"


@caso("CP-TJ-ROM-004")
def test_CP_TJ_ROM_004_credito_chip_aprobado(flujo, evidencia, pantalla_cobro):
    _tarjeta_aprobada(flujo, "Inserte una tarjeta de CRÉDITO con chip y capture el NIP si se pide.", evidencia, "Crédito")


@caso("CP-TJ-ROM-005")
def test_CP_TJ_ROM_005_contactless_sin_nip(flujo, evidencia, pantalla_cobro):
    _tarjeta_aprobada(flujo, "Acerque una tarjeta/teléfono NFC a la zona contactless (monto debajo del límite: no debe pedir NIP).", evidencia)
    evidencia.nota("⚠ (Manual) Confirmar que no se pidió NIP y que la lectura tomó ≤ 2 s")


@caso("CP-TJ-ROM-006")
def test_CP_TJ_ROM_006_contactless_sobre_limite(flujo, evidencia, pantalla_cobro):
    _tarjeta_aprobada(flujo, "Acerque una tarjeta NFC (monto sobre el límite contactless) y capture el NIP o inserte el chip cuando se pida.", evidencia)


@caso("CP-TJ-ROM-007")
def test_CP_TJ_ROM_007_banda_magnetica(flujo, evidencia, pantalla_cobro):
    _tarjeta_aprobada(flujo, "Deslice una tarjeta por el lector de BANDA de la T6 y confirme si se solicita.", evidencia)


@caso("CP-TJ-ROM-008")
def test_CP_TJ_ROM_008_nip_incorrecto(flujo, evidencia, pantalla_cobro):
    flujo.exigir_pinpad_real("Requiere capturar un NIP incorrecto")
    resultado = flujo.esperar_tarjeta_del_tester("Inserte la tarjeta y capture un NIP INCORRECTO (una vez).")
    assert resultado == "nip_incorrecto", f"Se esperaba 'NIP incorrecto' y el cobro terminó en '{resultado}'"
    assert not flujo.recibo.visible(2), "Se registró el pago con NIP incorrecto"


@caso("CP-TJ-ROM-009")
def test_CP_TJ_ROM_009_nip_intentos_maximos(flujo, evidencia, pantalla_cobro):
    flujo.exigir_pinpad_real("Requiere capturar un NIP incorrecto en el número máximo de intentos")
    resultado = flujo.esperar_tarjeta_del_tester("Capture un NIP INCORRECTO en todos los intentos que permita la T6.",
                                                 timeout=settings.TIMEOUT_TARJETA * 2)
    assert resultado in ("rechazado", "nip_incorrecto"), f"La transacción no se declinó (resultado: {resultado})"
    assert flujo.pago.existe(L.P4_BTN_INTENTAR, 2) or flujo.pago.existe(L.P4_BTN_REGRESAR_INICIO, 2), \
        "No se permite elegir otra tarjeta o regresar al inicio"


@caso("CP-TJ-ROM-010")
def test_CP_TJ_ROM_010_retiro_prematuro(flujo, evidencia, pantalla_cobro):
    flujo.exigir_pinpad_real("Requiere retirar la tarjeta a mitad del procesamiento")
    resultado = flujo.esperar_tarjeta_del_tester("Inserte la tarjeta y RETÍRELA antes de que termine el procesamiento.")
    assert resultado != "aprobado", "El pago se aprobó aunque la tarjeta se retiró antes de tiempo"
    assert resultado != "sin_resultado", "La app no informó nada al usuario tras retirar la tarjeta"
    evidencia.nota("⚠ (Manual) Confirmar en el adquirente que no quedó cargo")


@caso("CP-TJ-ROM-011")
def test_CP_TJ_ROM_011_tarjeta_no_soportada(flujo, evidencia, pantalla_cobro):
    flujo.exigir_pinpad_real("Requiere una tarjeta no aceptada (vales, marca no aceptada o vencida)")
    resultado = flujo.esperar_tarjeta_del_tester("Presente una tarjeta de marca NO aceptada, de vales o VENCIDA.")
    assert resultado in ("no_aceptada", "rechazado"), f"No se informó tarjeta no aceptada (resultado: {resultado})"
    assert flujo.pago.existe(L.P4_BTN_INTENTAR, 2), "No se ofrece usar otra tarjeta"


@caso("CP-TJ-ROM-012")
def test_CP_TJ_ROM_012_cancelar_antes_de_tarjeta(flujo, evidencia, pantalla_cobro):
    if flujo.pago.es_simulador():
        pendiente(f"{SIN_ANIMACION_TARJETA}. El simulador no tiene botón 'Cancelar'")
    assert flujo.pago.existe(L.P4_BTN_CANCELAR_COBRO, 5), "La pantalla de cobro no tiene botón 'Cancelar'"
    flujo.pago.tocar(L.P4_BTN_CANCELAR_COBRO)
    flujo.pago.esperar_estable(2)
    pantalla = flujo.pantalla()
    evidencia.captura(f"Después de cancelar el cobro: {pantalla}")
    assert pantalla in ("p3", "p2"), f"No se regresó a P3/P2 al cancelar (pantalla: {pantalla})"
    if pantalla == "p2":
        flujo.adeudos.pagar()
        assert flujo.metodo.visible(), "No se pudo volver a P3"
    flujo.metodo.elegir_tarjeta()
    assert flujo.pago.esperar_respuesta() in ("modulo_pago", "instruccion"), "El lector no quedó disponible para un nuevo cobro"
    evidencia.captura("Nuevo cobro disponible")


@caso("CP-SG-ROM-001")
def test_CP_SG_ROM_001_datos_de_tarjeta_enmascarados(flujo, evidencia, pago_aprobado):
    datos = flujo.recibo.datos()
    evidencia.nota(f"Comprobante: {datos}")
    textos = flujo.recibo.textos()
    completos = [t for t in textos for n in re.findall(r"\d{13,19}", t.replace(" ", "")) if _luhn(n)]
    assert not completos, f"P5 muestra un número de tarjeta completo: {completos}"
    assert re.search(r"\*{4}\d{4}$", datos.get("Tarjeta", "")), \
        f"La tarjeta no se muestra enmascarada con los últimos 4 dígitos: '{datos.get('Tarjeta', '')}'"
    en_logs = sorted({n for l in adb.logcat() for n in re.findall(r"(?<!\d)\d{13,19}(?!\d)", l) if _luhn(n)})
    evidencia.nota(f"Números con formato de tarjeta (Luhn) en logcat: {len(en_logs)}")
    assert not en_logs, f"El logcat contiene números de tarjeta completos: {[n[:6] + '…' + n[-4:] for n in en_logs]}"
    evidencia.nota("⚠ (Manual) Revisar el ticket impreso: solo los últimos 4 dígitos")


@caso("CP-SG-ROM-002")
@manual("Inspección visual de la pantalla segura de NIP (teclado aleatorio, asteriscos, sin capturas posibles). "
        "Aún no integrada: falta la animación para capturar el NIP")
def test_CP_SG_ROM_002_nip_en_pantalla_segura():
    pass
