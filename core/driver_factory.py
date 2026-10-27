"""
Sesión de Appium contra la T6 (UiAutomator2), basada en utils.start_driver() de automated_tests.

Requisitos (una sola vez):
    appium driver install uiautomator2
    appium --relaxed-security             # levantar el server

Importante: Rompefilas es un WebView. Chromium solo arma el árbol de accesibilidad completo
si la app se abre DESPUÉS de que UiAutomator2 está conectado; si la app ya estaba abierta,
el árbol llega incompleto (faltan botones). Por eso reiniciar_app() se llama antes de cada caso.
"""
import time

from appium import webdriver as appium_webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait

from config import locators as L
from config import settings
from core import adb


def crear_driver():
    print("🚀 Iniciando sesión de Appium en la T6...")
    opciones = UiAutomator2Options().load_capabilities(settings.CAPABILITIES)
    driver = appium_webdriver.Remote(settings.APPIUM_URL, options=opciones)
    driver.implicitly_wait(0)
    print(f"   ✅ Sesión iniciada · {driver.capabilities.get('deviceModel', '')} "
          f"{driver.capabilities.get('deviceUDID', '')}")
    return driver


def sesion_viva(driver):
    try:
        driver.current_package
        return True
    except Exception:
        return False


def reiniciar_app(driver, esperar_inicio=True):
    """Cierra y abre Rompefilas para iniciar cada caso limpio y con el árbol de accesibilidad completo.
    Antes cierra por ADB el módulo de pago y el escáner: el pinpad real (com.memphis.app.dev) corre en su propia
    tarea y, si un caso lo deja pidiendo tarjeta, queda encima de Rompefilas aunque se reabra la app."""
    paquetes = [settings.APP_PACKAGE, L.ESCANER_PAQUETE, *settings.PAQUETES_PAGO]
    try:
        encima = driver.current_package
        if encima and encima not in paquetes and "launcher" not in encima and encima != "com.android.systemui":
            paquetes.append(encima)
    except Exception:
        pass
    for paquete in paquetes:
        adb.shell(f"am force-stop {paquete}", silencioso=True)
    time.sleep(1)
    driver.activate_app(settings.APP_PACKAGE)
    if esperar_inicio:
        WebDriverWait(driver, settings.TIMEOUT_ARRANQUE, 0.5).until(
            lambda d: d.find_elements(*L.INICIO_BTN), message="La app no mostró la pantalla de inicio")
