"""
Configuración global del proyecto Rompefilas (Kiosko de Pagos en la terminal T6).

Todo se puede sobrescribir con variables de entorno, por ejemplo:
    INTERACTIVO=true T6_UDID=HF3148K000216 pytest
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _bool(nombre, default="false"):
    return os.getenv(nombre, default).strip().lower() in ("1", "true", "si", "sí", "yes")


# ==============================================
# APPIUM -> T6 (ANDROID 13, UIAUTOMATOR2)
# ==============================================
# Base tomada de automated_tests/Automatizacion/T6/v2/config.py (CAPABILITIES).
APPIUM_URL = os.getenv("APPIUM_URL", "http://127.0.0.1:4723")
T6_UDID = os.getenv("T6_UDID", "")  # vacío = primer dispositivo de 'adb devices'
APP_PACKAGE = os.getenv("APP_PACKAGE", "com.exos.kiosko.rompefilas")
APP_ACTIVITY = os.getenv("APP_ACTIVITY", "com.exos.kiosko.MainActivity")
# Apps del módulo de pago que se cierran entre casos (pinpad real de Memphis y simulador)
PAQUETES_PAGO = [p for p in os.getenv("PAQUETES_PAGO", "com.memphis.app.dev,com.memphis.pinpadsimulator").split(",") if p]

CAPABILITIES = {
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:platformVersion": "13",
    "appium:deviceName": "vnd_tb8766p1_64_bsp",
    "appium:appPackage": APP_PACKAGE,
    "appium:appActivity": APP_ACTIVITY,
    "appium:autoGrantPermissions": False,
    # No se borra la app ni sus datos: el reinicio entre casos lo hace la suite (ver driver_factory)
    "appium:noReset": True,
    "appium:dontStopAppOnReset": True,
    "appium:newCommandTimeout": 600,
}
if T6_UDID:
    CAPABILITIES["appium:udid"] = T6_UDID

# Esperas (segundos)
TIMEOUT = int(os.getenv("TIMEOUT", "15"))
TIMEOUT_CONSULTA = int(os.getenv("TIMEOUT_CONSULTA", "30"))      # 'Consultar adeudos' -> P2 o mensaje
TIMEOUT_APP_PAGO = int(os.getenv("TIMEOUT_APP_PAGO", "20"))      # 'Tarjeta' -> módulo de pago o error
TIMEOUT_ARRANQUE = int(os.getenv("TIMEOUT_ARRANQUE", "30"))      # reinicio de la app -> pantalla de inicio

# ==============================================
# TIEMPOS DE NEGOCIO (CONFIRMAR CON DESARROLLO)
# ==============================================
# v1.6.36: el aviso '¿Sigue ahí?' aparece a los ~60 s y regresa al inicio ~20 s después
TIMEOUT_INACTIVIDAD = int(os.getenv("TIMEOUT_INACTIVIDAD", "180"))
TIMEOUT_TARJETA_SIN_ACCION = int(os.getenv("TIMEOUT_TARJETA_SIN_ACCION", "240"))  # matriz: ~45 s; se mide el real
TIEMPO_MAX_ATENCION = int(os.getenv("TIEMPO_MAX_ATENCION", "90"))
MIN_TOQUE_DP = int(os.getenv("MIN_TOQUE_DP", "48"))

# ==============================================
# PRUEBAS CON INTERVENCIÓN FÍSICA
# ==============================================
# false : los casos que requieren tarjeta, recibo físico o retirar el papel salen como 'Manual'
# true  : la suite lleva la app hasta el punto y espera a que el tester haga la acción en la T6
INTERACTIVO = _bool("INTERACTIVO")
TIMEOUT_INTERACCION = int(os.getenv("TIMEOUT_INTERACCION", "120"))
# Pinpad real: tiempo para insertar/deslizar/acercar la tarjeta y, aparte, para capturar el NIP (mínimo 3 min c/u)
TIMEOUT_TARJETA = max(180, int(os.getenv("TIMEOUT_TARJETA", "180")))
TIMEOUT_NIP = max(180, int(os.getenv("TIMEOUT_NIP", "180")))
# Lo que tarda el pinpad en abrir / regresar a Rompefilas (la transición real es de 0.5 a 1.5 s)
TIMEOUT_TRANSICION_PINPAD = int(os.getenv("TIMEOUT_TRANSICION_PINPAD", "15"))

# ==============================================
# DATOS Y EVIDENCIA
# ==============================================
DIR_DATOS = RAIZ / "data"
MATRIZ_XLSX = DIR_DATOS / "RompeFilas.xlsx"
HOJA_MATRIZ = "Matriz Casos de Prueba Puebla"
FILA_ENCABEZADOS = 10
REFERENCIAS_JSON = DIR_DATOS / "referencias.json"
REFERENCIAS_TXT = DIR_DATOS / "referencias.txt"

# ==============================================
# 6 MESES SIN INTERESES
# ==============================================
MSI_MONTO_MINIMO = float(os.getenv("MSI_MONTO_MINIMO", "1000"))
MSI_PLAZO = 6
DIR_EVIDENCIAS = RAIZ / "evidencias"
