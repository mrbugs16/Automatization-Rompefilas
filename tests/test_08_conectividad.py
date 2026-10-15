"""
MÓDULO 08 - CONECTIVIDAD
· CP-CX-ROM-001 a CP-CX-ROM-005

La red se corta con 'svc wifi/data disable' por ADB: la T6 sigue conectada por USB y Appium no se cae.
Siempre se restablece en el finally.
"""
import pytest

from config.datos_prueba import MSG_SIN_ADEUDOS, REF_VALIDA
from core import adb
from core.marcadores import caso, manual

pytestmark = [pytest.mark.red]


@caso("CP-CX-ROM-001")
@pytest.mark.tarjeta
def test_CP_CX_ROM_001_cambio_de_red_durante_cobro(flujo, evidencia, pantalla_cobro):
    try:
        adb.wifi(False)
        evidencia.nota("Wi-Fi apagado con el cobro en curso (si hay SIM, la T6 pasa a datos móviles)")
        resultado = flujo.completar_cobro("aprobado", "Presente la tarjeta CON FONDOS (el Wi-Fi ya se apagó).")
    finally:
        adb.wifi(True)
        adb.esperar_red()
    evidencia.nota(f"Resultado tras el cambio de red: {resultado}")
    assert resultado != "sin_resultado", "La app no informó el resultado tras el cambio de red"
    if resultado == "aprobado":
        assert flujo.recibo.visible(10), "Se aprobó el cobro pero no se mostró el comprobante"
    evidencia.nota("⚠ (Manual) Conciliar en backend que no haya cobro sin registro")


@caso("CP-CX-ROM-002")
def test_CP_CX_ROM_002_sin_conexion_al_consultar(flujo, evidencia):
    flujo.iniciar()
    flujo.capturar_referencia(REF_VALIDA["referencia"])
    try:
        adb.sin_red(True)
        evidencia.nota("Wi-Fi y datos móviles apagados")
        resultado = flujo.consultar()
        textos = flujo.identificacion.textos()
        flujo._captura(f"Consulta sin red: {resultado}")
        evidencia.nota(f"Mensaje sin red: {[t for t in textos if 'onexi' in t or 'adeudos' in t.lower() or 'red' in t.lower()]}")
    finally:
        adb.sin_red(False)
        red = adb.esperar_red()
    assert resultado != "p2", "Mostró adeudos sin conexión (¿datos en caché?)"
    assert resultado != "sin_adeudos", f"Sin red muestra '{MSG_SIN_ADEUDOS}' en lugar de un mensaje de conexión"
    assert resultado == "sin_conexion", f"No se mostró 'Sin conexión, verifique la red' (resultado: {resultado})"

    assert red, "La red no se recuperó para reintentar"
    if flujo.pantalla() == "p1":
        flujo.identificacion.borrar_todo()
        flujo.capturar_referencia(REF_VALIDA["referencia"], captura=False)
        assert flujo.consultar() == "p2", "Al recuperar la red no se pudo reintentar la consulta"
        flujo._captura("Reintento con red")


@caso("CP-CX-ROM-003")
@manual("Cortar la red justo entre la aprobación bancaria y el registro en el Gobierno; conciliar en backend")
def test_CP_CX_ROM_003_red_perdida_tras_aprobacion():
    pass


@caso("CP-CX-ROM-004")
@manual("Simular señal débil / alta latencia (sin root la T6 no permite limitar la red por ADB)")
def test_CP_CX_ROM_004_senal_debil():
    pass


@caso("CP-CX-ROM-005")
@manual("Caminar entre antenas Wi-Fi durante la consulta/cobro")
def test_CP_CX_ROM_005_roaming_wifi():
    pass
