"""Pausas guiadas para los casos que necesitan una acción física del tester (INTERACTIVO=true)."""
import time

from config import settings

AVISO_CADA = 10  # segundos entre cada recordatorio del tiempo restante


def _banner(titulo, lineas, timeout):
    print("\a\n" + "=" * 72)  # \a: campana de la terminal para llamar la atención del tester
    print(f"🙋 {titulo} — tiene {timeout} s")
    for linea in lineas:
        print(f"   {linea}")
    print("=" * 72)


def pedir_accion(mensaje, hasta=None, timeout=None, evidencia=None, pasos=None):
    """Muestra la instrucción en la terminal y espera a que 'hasta()' sea verdadero (o a que pase el tiempo),
    recordando el tiempo restante cada 10 s. Regresa lo que regrese 'hasta()' (o True si no hay condición)."""
    timeout = timeout or settings.TIMEOUT_INTERACCION
    _banner("ACCIÓN DEL TESTER EN LA T6", [mensaje, *(pasos or [])], timeout)
    if evidencia:
        evidencia.nota(f"Acción del tester ({timeout} s): {mensaje}")
    inicio, siguiente_aviso = time.time(), AVISO_CADA
    while (transcurrido := time.time() - inicio) < timeout:
        if hasta is not None:
            resultado = hasta()
            if resultado:
                print(f"   ✅ Detectado a los {round(time.time() - inicio)} s")
                return resultado
        if transcurrido >= siguiente_aviso:
            print(f"   ⏳ Quedan {int(timeout - transcurrido)} s", flush=True)
            siguiente_aviso += AVISO_CADA
        time.sleep(1)
    print(f"   ⌛ Se agotaron los {timeout} s")
    return hasta is None


def pedir_tarjeta(instruccion, referencia="", monto=None, hasta=None, timeout=None, evidencia=None):
    """Indicación para el cobro: presentar la tarjeta y capturar el NIP (mínimo 120 s, ver TIMEOUT_TARJETA)."""
    timeout = max(timeout or settings.TIMEOUT_TARJETA, 120)
    cobro = " · ".join(t for t in (f"Referencia {referencia}" if referencia else "",
                                   f"Monto ${monto:,.2f}" if monto else "") if t)
    pasos = [
        *([f"💳 {cobro}"] if cobro else []),
        "1) INSERTE la tarjeta en el lector de chip (o deslícela por la banda / acérquela si es contactless)",
        "2) CAPTURE el NIP en la pantalla segura de la T6 y confirme",
        "3) NO retire la tarjeta hasta que la T6 lo indique; la suite detecta el resultado sola",
    ]
    return pedir_accion(instruccion, hasta=hasta, timeout=timeout, evidencia=evidencia, pasos=pasos)
