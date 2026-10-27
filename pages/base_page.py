"""Acciones comunes sobre cualquier pantalla de la T6 (esperas, toques, lectura de textos)."""
import html
import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from config import settings

_BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


class BasePage:
    def __init__(self, driver, timeout=settings.TIMEOUT):
        self.driver = driver
        self.timeout = timeout

    def _wait(self, timeout=None):
        return WebDriverWait(self.driver, timeout or self.timeout, poll_frequency=0.5,
                             ignored_exceptions=(StaleElementReferenceException,))

    # ---------- esperas ----------
    def esperar(self, loc, timeout=None):
        """Espera a que exista el elemento. En el WebView no se usa is_displayed(): UiAutomator2 solo
        expone los nodos que están en pantalla."""
        return self._wait(timeout).until(lambda d: (d.find_elements(*loc) or [None])[0], message=f"No apareció: {loc[1]}")

    def esperar_alguno(self, opciones, timeout=None):
        """opciones = {'nombre': loc}. Regresa el nombre del primero que aparezca."""
        def _alguno(d):
            for nombre, loc in opciones.items():
                if d.find_elements(*loc):
                    return nombre
            return False
        return self._wait(timeout).until(_alguno, message=f"No apareció ninguno de: {list(opciones)}")

    def esperar_que_desaparezca(self, loc, timeout=None):
        return self._wait(timeout).until(lambda d: not d.find_elements(*loc), message=f"No desapareció: {loc[1]}")

    def existe(self, loc, timeout=3):
        try:
            self.esperar(loc, timeout)
            return True
        except TimeoutException:
            return False

    # ---------- acciones ----------
    def tocar(self, loc, timeout=None):
        """El WebView re-renderiza durante las animaciones: si el nodo se invalida, se vuelve a buscar."""
        for intento in range(3):
            try:
                self.esperar(loc, timeout).click()
                return
            except StaleElementReferenceException:
                if intento == 2:
                    raise
                time.sleep(0.5)

    def doble_toque(self, loc):
        """Dos toques rápidos (CP-IC-ROM-002)."""
        el = self.esperar(loc)
        self.driver.execute_script("mobile: doubleClickGesture", {"elementId": el.id})

    def atras(self):
        self.driver.back()

    # ---------- lectura ----------
    def texto(self, loc, timeout=None):
        return (self.esperar(loc, timeout).get_attribute("text") or "").strip()

    def habilitado(self, loc):
        return self.esperar(loc).get_attribute("enabled") == "true"

    def textos(self):
        """Todos los textos visibles en pantalla, en orden (de una sola lectura del XML)."""
        # Un content-desc de Flutter (pinpad) puede traer varias líneas (ej. 'Transacción aprobada' y la cuenta regresiva)
        return [linea.strip() for _, t, _, _ in self.nodos() for linea in t.splitlines() if linea.strip()]

    def contiene_texto(self, fragmento):
        return any(fragmento in t for t in self.textos())

    def nodos(self):
        """[(clase, texto, clickable, (x1, y1, x2, y2))] de la pantalla actual, leído del XML (una sola llamada)."""
        resultado = []
        for n in re.finditer(r"<([\w.]+) ([^>]*)>", self.driver.page_source):
            attrs = dict(re.findall(r'([\w:-]+)="([^"]*)"', n.group(2)))
            m = _BOUNDS.match(attrs.get("bounds", ""))
            if m:
                # El pinpad de Memphis (Flutter) no llena @text: su texto visible está en @content-desc
                texto = attrs.get("text", "") or attrs.get("content-desc", "")
                resultado.append((n.group(1), html.unescape(texto), attrs.get("clickable") == "true",
                                  tuple(int(v) for v in m.groups())))
        return resultado

    def fuera_de_pantalla(self, nodos=None):
        """Textos cuyo recuadro se sale de la pantalla (cortados o desbordados)."""
        tam = self.driver.get_window_size()
        return [t for _, t, _, (x1, y1, x2, y2) in (nodos or self.nodos())
                if t and (x1 < 0 or y1 < 0 or x2 > tam["width"] or y2 > tam["height"])]

    def esperar_estable(self, segundos=1.0):
        """Las transiciones del WebView animan la pantalla: pequeña espera antes de leer o capturar."""
        time.sleep(segundos)
