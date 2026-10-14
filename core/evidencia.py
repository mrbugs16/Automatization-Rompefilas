"""
Evidencia por caso de prueba (misma estructura que Automatization-Paid-Button).

Estructura generada en cada ejecución:
    evidencias/<AAAAMMDD_HHMMSS>/
        reporte.html
        resultados.json
        matriz_resultados.xlsx
        capturas/<CP-ID>/01_descripcion.png, 02_..., 99_FALLO.png (+ .xml de la pantalla al fallar)
"""
import re
import unicodedata
from datetime import datetime

from core import adb


def _slug(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_")[:60] or "captura"


class Evidencia:
    def __init__(self, caso_id, dir_ejecucion):
        self.caso_id = caso_id
        self.dir_ejecucion = dir_ejecucion
        self.dir_caso = dir_ejecucion / "capturas" / caso_id
        self.pasos = []
        self.driver = None

    def _contexto(self, driver):
        """En la T6 no hay URL: se registra la app y la actividad en pantalla."""
        try:
            return driver.current_package, driver.current_activity
        except Exception:
            return "", ""

    def captura(self, descripcion, estado="info", driver=None, guardar_fuente=False):
        """Toma screenshot y lo registra como paso. estado: info | ok | fallo.
        Con guardar_fuente=True también guarda el XML de la pantalla (útil para depurar localizadores)."""
        driver = driver or self.driver
        numero = len(self.pasos) + 1
        archivo = fuente = None
        paquete = actividad = ""
        self.dir_caso.mkdir(parents=True, exist_ok=True)
        ruta = self.dir_caso / f"{numero:02d}_{_slug(descripcion)}.png"
        try:
            if driver is None:
                raise RuntimeError("sin sesión de Appium")
            paquete, actividad = self._contexto(driver)
            driver.save_screenshot(str(ruta))
            archivo = ruta.relative_to(self.dir_ejecucion).as_posix()
        except Exception:
            try:  # la sesión pudo haberse cerrado (ej. reinicio de la T6): se captura por ADB
                adb.screencap(ruta)
                archivo = ruta.relative_to(self.dir_ejecucion).as_posix()
                paquete = adb.ventana_en_foco()
            except Exception as e:
                descripcion = f"{descripcion} (sin captura: {e.__class__.__name__})"
        if driver is not None and guardar_fuente:
            try:
                ruta_xml = ruta.with_suffix(".xml")
                ruta_xml.write_text(driver.page_source, encoding="utf-8")
                fuente = ruta_xml.relative_to(self.dir_ejecucion).as_posix()
            except Exception:
                pass
        self.pasos.append({
            "numero": numero,
            "descripcion": descripcion,
            "estado": estado,
            "archivo": archivo,
            "fuente": fuente,
            "hora": datetime.now().strftime("%H:%M:%S"),
            "pantalla": " · ".join(p for p in (paquete, actividad) if p),
        })
        print(f"   📸 [{self.caso_id}] {numero:02d} {descripcion}")
        return archivo

    def nota(self, descripcion, estado="info"):
        """Registra un paso sin captura (ej. tiempos medidos u observaciones)."""
        self.pasos.append({
            "numero": len(self.pasos) + 1,
            "descripcion": descripcion,
            "estado": estado,
            "archivo": None,
            "hora": datetime.now().strftime("%H:%M:%S"),
        })
        print(f"   📝 [{self.caso_id}] {descripcion}")
