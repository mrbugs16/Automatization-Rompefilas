"""Pausas guiadas para los casos que necesitan una acción física del tester (INTERACTIVO=true)."""
import time

from config import settings


def pedir_accion(mensaje, hasta=None, timeout=None, evidencia=None):
    """Muestra la instrucción en la terminal y espera a que 'hasta()' sea verdadero (o a que pase el tiempo).
    Regresa lo que regrese 'hasta()' (o True si no se pasó condición)."""
    timeout = timeout or settings.TIMEOUT_INTERACCION
    print("\n" + "=" * 70)
    print(f"🙋 ACCIÓN DEL TESTER EN LA T6 ({timeout} s):\n   {mensaje}")
    print("=" * 70)
    if evidencia:
        evidencia.nota(f"Acción del tester: {mensaje}")
    inicio = time.time()
    while time.time() - inicio < timeout:
        if hasta is None:
            restante = int(timeout - (time.time() - inicio))
            print(f"\r   ⏳ continúa en {restante:3d} s ", end="", flush=True)
            time.sleep(1)
            continue
        resultado = hasta()
        if resultado:
            print(f"   ✅ Detectado a los {round(time.time() - inicio)} s")
            return resultado
        time.sleep(1)
    print()
    return hasta is None
