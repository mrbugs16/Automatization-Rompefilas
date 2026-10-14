"""
Pantallas del Kiosko de Pagos Rompefilas (v1.6.36) y el flujo completo.

    Inicio -> P1 Identificar -> P2 Adeudos -> P3 Método -> P4 Pago (módulo de la T6) -> P5 Recibo
"""
import re
import time

from selenium.common.exceptions import TimeoutException

from config import locators as L
from config import settings
from core.interaccion import pedir_accion
from pages.base_page import BasePage


def a_monto(texto):
    """'$4,452.55' -> 4452.55 (None si no hay monto)."""
    m = re.search(r"\$\s*([\d,]+\.\d{2})", texto or "")
    return float(m.group(1).replace(",", "")) if m else None


class InicioPage(BasePage):
    def visible(self, timeout=None):
        return self.existe(L.INICIO_BTN, timeout or settings.TIMEOUT)

    def iniciar(self):
        self.tocar(L.INICIO_BTN)

    def version_footer(self):
        m = re.search(r"v(\d+(?:\.\d+)+)", self.texto(L.FOOTER))
        return m.group(1) if m else ""


class IdentificacionPage(BasePage):
    """P1 - Ingrese su referencia de pago."""

    def visible(self, timeout=None):
        return self.existe(L.P1_TITULO, timeout or settings.TIMEOUT)

    def teclear(self, digitos):
        for d in str(digitos):
            self.tocar(L.P1_TECLA(d))

    def borrar_todo(self):
        self.tocar(L.P1_BTN_BORRAR_TODO)

    def referencia(self):
        """Lo que muestra el campo ('0000000000000000' = vacío). Es el último texto solo-dígitos antes
        del teclado (la tarjeta que decodifica la referencia también muestra números, pero va arriba)."""
        campo = ""
        for clase, texto, _, _ in self.nodos():
            if clase.endswith("Button") and texto == "1":
                return campo
            if clase.endswith("TextView") and texto.isdigit():
                campo = texto
        return campo

    def consultar_habilitado(self):
        return self.habilitado(L.P1_BTN_CONSULTAR)

    def consultar(self):
        self.tocar(L.P1_BTN_CONSULTAR)

    def mensaje_sin_adeudos(self, timeout=3):
        return self.existe(L.P1_MSG_SIN_ADEUDOS, timeout)

    def teclado_completo(self):
        """Regresa los elementos del teclado (0-9, Borrar todo, Borrar) que NO están en pantalla."""
        botones = {t for clase, t, _, _ in self.nodos() if clase.endswith("Button")}
        return [t for t in [*map(str, range(10)), "Borrar todo", "Borrar"] if t not in botones]

    def regresar_al_inicio(self):
        self.tocar(L.P1_BTN_REGRESAR_INICIO)

    # ---------- cuenta predial ----------
    def capturar_cuenta_predial(self, tipo, cuenta, delegacion):
        self.tocar(L.P1_BTN_CUENTA_PREDIAL)
        self.tocar(L.P1_BTN_PU if tipo == "PU" else L.P1_BTN_PR)
        self.teclear(f"{cuenta}{delegacion}")

    # ---------- escáner ----------
    def abrir_camara(self):
        self.tocar(L.P1_BTN_CAMARA)


class AdeudosPage(BasePage):
    """P2 - lista de adeudos del contribuyente."""

    def visible(self, timeout=None):
        return self.existe(L.P2_BTN_PAGAR, timeout or settings.TIMEOUT)

    def contribuyente(self):
        """Primer texto en mayúsculas debajo del indicador de pasos."""
        textos = self.textos()
        try:
            i = textos.index("Recibo")
        except ValueError:
            return ""
        return textos[i + 1] if i + 1 < len(textos) else ""

    def contador(self):
        return self.texto(L.P2_CONTADOR)

    def adeudos(self):
        """[{concepto, monto, texto_monto}] en el orden de la pantalla (el concepto va después del monto)."""
        textos = self.textos()
        lista = []
        for i, t in enumerate(textos):
            monto = a_monto(t)
            if monto is not None and t.strip().startswith("$") and i + 1 < len(textos):
                lista.append({"concepto": textos[i + 1], "monto": monto, "texto_monto": t})
        return lista

    def casillas(self):
        return self.driver.find_elements(*L.CASILLAS)

    def cambiar_referencia(self):
        self.tocar(L.P2_BTN_CAMBIAR_REFERENCIA)

    def pagar_habilitado(self):
        return self.habilitado(L.P2_BTN_PAGAR)

    def pagar(self):
        self.tocar(L.P2_BTN_PAGAR)


class MetodoPage(BasePage):
    """P3 - ¿Cómo desea pagar?"""

    def visible(self, timeout=None):
        return self.existe(L.P3_TITULO, timeout or settings.TIMEOUT)

    def boton_tarjeta(self):
        return self.texto(L.P3_BTN_TARJETA)

    def total(self):
        return a_monto(self.boton_tarjeta())

    def metodos(self):
        """Textos de los botones de método de pago (entre el título y 'Regresar a adeudos')."""
        textos = self.textos()
        try:
            return textos[textos.index("¿Cómo desea pagar?") + 1:textos.index("Regresar a adeudos")]
        except ValueError:
            return []

    def elegir_tarjeta(self):
        self.tocar(L.P3_BTN_TARJETA)

    def regresar_a_adeudos(self):
        self.tocar(L.P3_BTN_REGRESAR_ADEUDOS)

    def cancelar_y_salir(self):
        self.tocar(L.P3_BTN_CANCELAR)


class PagoPage(BasePage):
    """P4 - módulo de pago integrado de la T6 y sus resultados."""

    def esperar_respuesta(self, timeout=None):
        """Tras tocar 'Tarjeta' regresa:
        'error_app_pago' : la app no pudo comunicarse con la aplicación de pago (v1.6.36)
        'modulo_pago'    : se abrió otra app en primer plano (módulo de cobro de la T6)
        'instruccion'    : la propia app muestra la instrucción para presentar la tarjeta
        'recibo'         : ya se mostró el resultado aprobado
        """
        fin = time.time() + (timeout or settings.TIMEOUT_APP_PAGO)
        while time.time() < fin:
            if self.driver.find_elements(*L.P4_ERROR_TITULO):
                return "error_app_pago"
            if self.driver.find_elements(*L.P5_PAGO_EXITOSO):
                return "recibo"
            try:
                if self.driver.current_package not in (settings.APP_PACKAGE, ""):
                    return "modulo_pago"
            except Exception:
                pass
            if self.driver.find_elements(*L.P4_INSTRUCCION_TARJETA):
                return "instruccion"
            time.sleep(0.5)
        return "sin_respuesta"

    def mensaje_error(self):
        return " · ".join(t for t in self.textos() if t in (
            "No se pudo procesar el pago", "No se pudo comunicar con la aplicación de pago.",
            "No se realizó ningún cargo a su tarjeta")) or ""

    def intentar_de_nuevo(self):
        self.tocar(L.P4_BTN_INTENTAR)

    def regresar_al_inicio(self):
        self.tocar(L.P4_BTN_REGRESAR_INICIO)

    def esperar_resultado(self, timeout):
        """Espera a que el módulo de pago regrese a Rompefilas con un resultado."""
        opciones = {
            "aprobado": L.P5_PAGO_EXITOSO,
            "rechazado": L.P4_ERROR_TITULO,
            "tiempo_agotado": L.P4_TIEMPO_AGOTADO,
            "nip_incorrecto": L.P4_NIP_INCORRECTO,
            "no_aceptada": L.P4_TARJETA_NO_ACEPTADA,
        }
        try:
            return self.esperar_alguno(opciones, timeout)
        except TimeoutException:
            return "sin_resultado"


class ReciboPage(BasePage):
    """P5 - Recibo / Pago exitoso. TODO confirmar localizadores cuando exista en la app."""

    def visible(self, timeout=None):
        return self.existe(L.P5_PAGO_EXITOSO, timeout or settings.TIMEOUT)

    def autorizacion(self):
        textos = self.textos()
        for i, t in enumerate(textos):
            if "utorización" in t:
                m = re.search(r"\d{4,}", t) or (re.search(r"\d{4,}", textos[i + 1]) if i + 1 < len(textos) else None)
                return m.group(0) if m else ""
        return ""

    def reimprimir(self):
        self.tocar(L.P5_BTN_REIMPRIMIR)


class InactividadModal(BasePage):
    def esperar_aviso(self, timeout=None):
        """Espera el aviso '¿Sigue ahí?'. Regresa los segundos que tardó en aparecer (None si no apareció)."""
        inicio = time.time()
        try:
            self._wait(timeout or settings.TIMEOUT_INACTIVIDAD).until(
                lambda d: d.find_elements(*L.INACTIVIDAD_TITULO) or d.find_elements(*L.INICIO_BTN))
        except TimeoutException:
            return None
        return round(time.time() - inicio) if self.driver.find_elements(*L.INACTIVIDAD_TITULO) else None

    def cuenta_regresiva(self):
        """El texto cambia cada segundo (el nodo se reemplaza): se lee del XML completo."""
        for _ in range(3):
            texto = next((t for t in self.textos() if "se cerrará en" in t), "")
            if texto:
                return texto
            time.sleep(0.5)
        return ""

    def continuar(self):
        self.tocar(L.INACTIVIDAD_BTN_CONTINUAR)


class FlujoKiosko:
    """Orquesta las pantallas y deja captura de cada paso en la evidencia."""

    def __init__(self, driver, evidencia=None):
        self.driver = driver
        self.ev = evidencia
        self.inicio = InicioPage(driver)
        self.identificacion = IdentificacionPage(driver)
        self.adeudos = AdeudosPage(driver)
        self.metodo = MetodoPage(driver)
        self.pago = PagoPage(driver)
        self.recibo = ReciboPage(driver)
        self.inactividad = InactividadModal(driver)
        self.t_inicio = None  # momento en que se tocó 'Toque para iniciar' (CP-ES-ROM-002)

    def _captura(self, descripcion, **kw):
        if self.ev:
            self.ev.captura(descripcion, **kw)

    def pantalla(self):
        """Pantalla actual: inicio | p1 | p2 | p3 | p4_error | p5 | inactividad | otra_app | desconocida."""
        d = self.driver
        try:
            if d.current_package != settings.APP_PACKAGE:
                return "otra_app"
        except Exception:
            pass
        for nombre, loc in (("inactividad", L.INACTIVIDAD_TITULO), ("p5", L.P5_PAGO_EXITOSO),
                            ("p4_error", L.P4_ERROR_TITULO), ("p3", L.P3_TITULO), ("p2", L.P2_BTN_PAGAR),
                            ("p1", L.P1_TITULO), ("inicio", L.INICIO_BTN)):
            if d.find_elements(*loc):
                return nombre
        return "desconocida"

    # ---------- pasos ----------
    def iniciar(self):
        assert self.inicio.visible(), "No se mostró la pantalla de inicio ('Toque para iniciar')"
        self._captura("Inicio - ¿Qué desea pagar hoy?")
        self.t_inicio = time.time()
        self.inicio.iniciar()
        assert self.identificacion.visible(), "No se mostró P1 'Ingrese su referencia de pago'"
        self.identificacion.esperar_estable(0.5)

    def capturar_referencia(self, referencia, captura=True):
        self.identificacion.teclear(referencia)
        if captura:
            self.identificacion.esperar_estable(0.5)
            self._captura(f"P1 - Referencia capturada ({len(str(referencia))} dígitos)")

    def consultar(self, timeout=None):
        """Toca 'Consultar adeudos'. Regresa 'p2' | 'sin_adeudos' | 'sin_respuesta'."""
        self.identificacion.consultar()
        try:
            resultado = self.identificacion.esperar_alguno(
                {"p2": L.P2_BTN_PAGAR, "sin_adeudos": L.P1_MSG_SIN_ADEUDOS, "sin_conexion": L.AVISO_SIN_CONEXION},
                timeout or settings.TIMEOUT_CONSULTA)
        except TimeoutException:
            resultado = "sin_respuesta"
        self.identificacion.esperar_estable(0.8)
        return resultado

    def ir_a_adeudos(self, referencia):
        self.iniciar()
        self.capturar_referencia(referencia)
        resultado = self.consultar()
        assert resultado == "p2", f"La referencia {referencia} no mostró adeudos (resultado: {resultado})"
        self._captura("P2 - Adeudos del contribuyente")

    def ir_a_metodo(self, referencia):
        self.ir_a_adeudos(referencia)
        self.adeudos.pagar()
        assert self.metodo.visible(), "No se avanzó a P3 '¿Cómo desea pagar?'"
        self.metodo.esperar_estable(0.8)
        self._captura("P3 - ¿Cómo desea pagar?")

    def pagar_con_tarjeta(self, referencia):
        """Lleva el flujo hasta el módulo de pago. Regresa el estado de PagoPage.esperar_respuesta()."""
        self.ir_a_metodo(referencia)
        self.metodo.elegir_tarjeta()
        estado = self.pago.esperar_respuesta()
        self.pago.esperar_estable(1)
        self._captura(f"P4 - Respuesta al elegir Tarjeta: {estado}")
        return estado

    def esperar_tarjeta_del_tester(self, instruccion, timeout=None):
        """Con el módulo de pago abierto, pide al tester la acción con la tarjeta y espera el resultado
        (aprobado | rechazado | tiempo_agotado | nip_incorrecto | no_aceptada | sin_resultado)."""
        def _resultado():
            r = self.pago.esperar_resultado(2)
            return r if r != "sin_resultado" else False
        resultado = pedir_accion(instruccion, hasta=_resultado, timeout=timeout, evidencia=self.ev) or "sin_resultado"
        self.pago.esperar_estable(1)
        self._captura(f"Resultado del cobro: {resultado}")
        return resultado
