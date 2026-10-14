"""
Control de la T6 por ADB (lo que Appium no alcanza: red, batería, reinicio, ventana en foco).

Basado en automated_tests/Automatizacion/T6/v2/utils_system.py.
Requiere 'adb' en el PATH y la T6 conectada por USB (adb devices).
"""
import re
import subprocess
import time

from config import settings

TIMEOUT_ADB = 15


def adb(comando, timeout=TIMEOUT_ADB, silencioso=False):
    """Ejecuta 'adb [-s serial] <comando>'. Regresa (ok, salida)."""
    serial = ["-s", settings.T6_UDID] if settings.T6_UDID else []
    cmd = ["adb", *serial, *comando.split()] if isinstance(comando, str) else ["adb", *serial, *comando]
    if not silencioso:
        print(f"   🔧 ADB: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except FileNotFoundError:
        return False, "adb no está en el PATH"


def shell(comando, timeout=TIMEOUT_ADB, silencioso=False):
    return adb(["shell", comando], timeout, silencioso)


def dispositivo_conectado():
    ok, salida = adb("devices", silencioso=True)
    lineas = [l for l in salida.splitlines()[1:] if "\tdevice" in l]
    if settings.T6_UDID:
        lineas = [l for l in lineas if l.startswith(settings.T6_UDID)]
    return lineas[0].split("\t")[0] if lineas else None


def prop(nombre):
    return shell(f"getprop {nombre}", silencioso=True)[1].strip()


def version_app(paquete=settings.APP_PACKAGE):
    _, salida = shell(f"dumpsys package {paquete}", silencioso=True)
    m = re.search(r"versionName=(\S+)", salida)
    return m.group(1) if m else ""


def ventana_en_foco():
    """Ventana con el foco, ej. 'com.exos.kiosko.rompefilas/com.exos.kiosko.MainActivity' o 'NotificationShade'."""
    _, salida = shell("dumpsys window", silencioso=True)
    m = re.search(r"mCurrentFocus=Window\{\S+ \S+ ([^}]+)\}", salida)
    return m.group(1).strip() if m else ""


def densidad():
    """DPI efectivo (la T6 trae 'Override density: 228' sobre 270 físico)."""
    _, salida = shell("wm density", silencioso=True)
    valores = re.findall(r"density: (\d+)", salida)
    return int(valores[-1]) if valores else 160


def screencap(ruta):
    """Captura por ADB (respaldo cuando no hay sesión de Appium, ej. justo después de reiniciar la T6)."""
    serial = ["-s", settings.T6_UDID] if settings.T6_UDID else []
    r = subprocess.run(["adb", *serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=TIMEOUT_ADB)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("screencap falló")
    with open(ruta, "wb") as f:
        f.write(r.stdout)


def info_dispositivo():
    return {
        "serial": dispositivo_conectado() or "-",
        "modelo": prop("ro.product.model"),
        "android": prop("ro.build.version.release"),
        "app": version_app(),
    }


# ==============================================
# RED
# ==============================================
def wifi(encender):
    shell(f"svc wifi {'enable' if encender else 'disable'}")


def datos_moviles(encender):
    shell(f"svc data {'enable' if encender else 'disable'}")


def sin_red(activar=True):
    """Corta Wi-Fi y datos móviles (la T6 sigue conectada por USB, así que Appium no se cae)."""
    wifi(not activar)
    datos_moviles(not activar)
    time.sleep(3)


def esperar_red(timeout=40):
    inicio = time.time()
    while time.time() - inicio < timeout:
        ok, salida = shell("ping -c 1 -W 2 8.8.8.8", timeout=6, silencioso=True)
        if ok and "1 received" in salida:
            return True
        time.sleep(2)
    return False


# ==============================================
# BATERÍA (simulada; siempre restablecer con bateria_real())
# ==============================================
def simular_bateria(nivel, cargando=False):
    shell("dumpsys battery unplug" if not cargando else "dumpsys battery set ac 1")
    shell(f"dumpsys battery set level {nivel}")


def bateria_real():
    shell("dumpsys battery reset")


# ==============================================
# SISTEMA
# ==============================================
def expandir_notificaciones_con_gesto():
    """Desliza desde el borde superior como lo haría un usuario."""
    shell("input swipe 360 2 360 900 300")
    time.sleep(1.5)


def cerrar_notificaciones():
    shell("cmd statusbar collapse", silencioso=True)


def reiniciar_y_esperar(timeout=180):
    """Reinicia la T6 y espera a que termine de arrancar (sys.boot_completed=1)."""
    adb("reboot", timeout=30)
    time.sleep(10)
    adb("wait-for-device", timeout=timeout)
    inicio = time.time()
    while time.time() - inicio < timeout:
        if prop("sys.boot_completed") == "1":
            return round(time.time() - inicio)
        time.sleep(2)
    return None


def logcat(filtro=None, max_lineas=4000):
    """Logcat reciente del dispositivo (para buscar datos sensibles o eventos)."""
    _, salida = adb(["logcat", "-d", "-v", "time", "-t", str(max_lineas)], timeout=30, silencioso=True)
    lineas = salida.splitlines()
    return [l for l in lineas if not filtro or filtro.lower() in l.lower()]
