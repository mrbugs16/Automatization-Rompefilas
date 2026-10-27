"""
Pantallas del Kiosko de Pagos Rompefilas (v1.6.36) y el flujo completo.

    Inicio -> P1 Identificar -> P2 Adeudos -> P3 Método -> P4 Pago (módulo de la T6) -> P5 Recibo
"""
import re
import time

from selenium.common.exceptions import TimeoutException

from config import locators as L
from config import settings
from core import referencias
from core.interaccion import pedir_nip, pedir_tarjeta
from core.marcadores import SIN_ANIMACION_TARJETA, pendiente, requiere_tester
from pages.base_page import BasePage


def a_monto(texto):
    """'$4,452.55' -> 4452.55 · '-$494.28' -> -494.28 (condonaciones) · None si no hay monto."""
    m = re.search(r"(-?)\s*\$\s*([\d,]+\.\d{2})", texto or "")
    return (-1 if m.group(1) else 1) * float(m.group(2).replace(",", "")) if m else None


def es_monto(texto):
    """Texto que es solo un monto ('$1,596.00' o '-$494.28')."""
    return bool(re.fullmatch(r"-?\s*\$\s*[\d,]+\.\d{2}", (texto or "").strip()))


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
            if monto is not None and es_monto(t) and i + 1 < len(textos):
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

    def detalle_error(self):
        """Texto que Rompefilas muestra debajo de 'No se pudo procesar el pago' (ej. 'Error al capturar el nip.')."""
        textos = self.textos()
        if "No se pudo procesar el pago" in textos:
            i = textos.index("No se pudo procesar el pago")
            return textos[i + 1] if i + 1 < len(textos) else ""
        return ""

    def mensaje_error(self):
        textos = self.textos()
        if "No se pudo procesar el pago" not in textos:
            return ""
        partes = ["No se pudo procesar el pago", self.detalle_error()]
        partes += [t for t in textos if t.startswith("No se realizó ningún cargo")]
        return " · ".join(t for t in partes if t)

    def intentar_de_nuevo(self):
        self.tocar(L.P4_BTN_INTENTAR)

    def regresar_al_inicio(self):
        self.tocar(L.P4_BTN_REGRESAR_INICIO)

    # ---------- simulador de pinpad (v1.6.37) ----------
    def es_simulador(self, timeout=3):
        """True si el módulo de pago en pantalla es el simulador de Memphis (Approved / Declined)."""
        return self.existe(L.SIM_BTN_APROBAR, timeout)

    def simular(self, resultado):
        """Toca 'Approved' o 'Declined' en el simulador."""
        self.tocar(L.SIM_BTN_APROBAR if resultado == "aprobado" else L.SIM_BTN_DECLINAR)

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


class PinpadPage(BasePage):
    """Pinpad real de Memphis (otra app): inserción, lectura, mensualidades, NIP y resultado."""

    # Fase de la pantalla según sus textos. El orden importa: la hoja de mensualidades aparece ENCIMA de
    # 'Leyendo tarjeta...' y el resultado del pinpad tapa todo lo demás.
    FASES = (
        ("pin_aprobada", ("Transacción aprobada",)),
        ("pin_tiempo_agotado", ("Tiempo de espera agotado",)),
        ("pin_declinada", ("Transacción declinada",)),
        ("pin_nip_cancelado", ("Ingreso de PIN cancelado",)),
        ("mensualidades", ("Cuántas mensualidades",)),
        ("nip", ("Ingresa tu PIN",)),
        ("leyendo", ("Leyendo tarjeta",)),
        ("insertar", ("inserta o desliza tu tarjeta",)),
    )

    def fase(self, textos=None):
        textos = textos if textos is not None else self.textos()
        unido = " | ".join(textos)
        return next((nombre for nombre, claves in self.FASES if any(c in unido for c in claves)), None)

    def resumen(self, textos=None):
        """{'Monto': '$8935.09', 'Mensualidades': '6'} del recuadro 'Resumen'."""
        textos = textos if textos is not None else self.textos()
        return {t: textos[i + 1] for i, t in enumerate(textos) if t in L.PIN_ETIQUETAS_RESUMEN and i + 1 < len(textos)}

    def opciones_de_pago(self):
        return [t for t in self.textos() if "mensualidades" in t.lower() or "meses sin intereses" in t.lower()]

    def elegir_plan(self, plan):
        """plan: 'contado' (Sin mensualidades) | '6msi' (6 meses sin intereses)."""
        self.tocar(L.PIN_OPC_6MSI if plan == "6msi" else L.PIN_OPC_CONTADO)

    def cancelar(self):
        self.tocar(L.PIN_BTN_CANCELAR)


class ReciboPage(BasePage):
    """P5 - Comprobante '¡Pago exitoso!' (v1.6.37)."""

    def visible(self, timeout=None):
        return self.existe(L.P5_TITULO, timeout or settings.TIMEOUT)

    def datos(self):
        """{'Folio', 'Total', 'Nombre', 'Referencia', 'Autorización', 'Tarjeta', 'Fecha', 'Estado'} del comprobante.
        Cada etiqueta toma el texto siguiente (si una etiqueta se repite, se queda la primera)."""
        textos = self.textos()
        datos = {}
        for i, t in enumerate(textos):
            if t in L.P5_CAMPOS and t not in datos and i + 1 < len(textos):
                datos[t] = textos[i + 1]
            elif t.startswith("CONF-"):
                datos["Folio"] = t
            elif t.endswith("MXN") and "Total" not in datos:
                datos["Total"] = t
        datos["Repetidos"] = sorted({t for t in L.P5_CAMPOS if textos.count(t) > 1})
        return datos

    def autorizacion(self):
        return self.datos().get("Autorización", "")

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
        self.pinpad = PinpadPage(driver)
        self.inactividad = InactividadModal(driver)
        self.cobro = {}  # lo que pasó en el pinpad en el último cobro (fases, plan ofrecido/elegido, resumen)
        self.estados_redundantes = False  # CP-RC-ROM-007
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

    def _registrar(self, **datos):
        """Guarda en la evidencia la referencia, el contribuyente y el monto del caso (para el reporte)."""
        if self.ev:
            for clave, valor in datos.items():
                if valor not in (None, ""):
                    setattr(self.ev, clave, valor)

    def capturar_referencia(self, referencia, captura=True):
        # En el reporte se muestra la referencia que sí regresó adeudos; si ninguna, la primera capturada
        self._ultima_referencia = str(referencia)
        if len(str(referencia)) == 16 and self.ev and not self.ev.referencia:
            self._registrar(referencia=str(referencia))
        self.identificacion.teclear(referencia)
        if captura:
            self.identificacion.esperar_estable(0.5)
            self._captura(f"P1 - Referencia capturada ({len(str(referencia))} dígitos)")

    def consultar(self, timeout=None):
        """Toca 'Consultar adeudos'. Regresa 'p2' | 'sin_adeudos' | 'ref_pagada' | 'sin_conexion' | 'sin_respuesta'."""
        self.identificacion.consultar()
        try:
            resultado = self.identificacion.esperar_alguno(
                {"p2": L.P2_BTN_PAGAR, "sin_adeudos": L.P1_MSG_SIN_ADEUDOS, "ref_pagada": L.P1_MSG_REF_PAGADA,
                 "sin_conexion": L.AVISO_SIN_CONEXION},
                timeout or settings.TIMEOUT_CONSULTA)
        except TimeoutException:
            resultado = "sin_respuesta"
        self.identificacion.esperar_estable(0.8)
        if resultado == "p2" and self.ev:
            adeudos = self.adeudos.adeudos()
            self._registrar(referencia=getattr(self, "_ultima_referencia", ""),
                            contribuyente=self.adeudos.contribuyente(),
                            monto=round(sum(a["monto"] for a in adeudos), 2) if adeudos else None)
        return resultado

    def ir_a_adeudos(self, referencia):
        self.iniciar()
        self.capturar_referencia(referencia)
        resultado = self.consultar()
        if resultado == "ref_pagada":
            # Se pagó fuera de la suite: se corrige el catálogo para que los siguientes casos usen otra
            referencias.actualizar(str(referencia), estado="pagada", pagada_en="Detectada por la app: 'Referencia pagada'")
        assert resultado == "p2", f"La referencia {referencia} no mostró adeudos (resultado: {resultado})"
        self._captura("P2 - Adeudos del contribuyente")

    def ir_a_metodo(self, referencia):
        self.ir_a_adeudos(referencia)
        self.adeudos.pagar()
        assert self.metodo.visible(), "No se avanzó a P3 '¿Cómo desea pagar?'"
        self.metodo.esperar_estable(0.8)
        self._registrar(monto=self.metodo.total())  # el monto que se cobra es el de P3
        self._captura("P3 - ¿Cómo desea pagar?")

    def pagar_con_tarjeta(self, referencia):
        """Lleva el flujo hasta el módulo de pago. Regresa el estado de PagoPage.esperar_respuesta()."""
        self.ir_a_metodo(referencia)
        self.metodo.elegir_tarjeta()
        estado = self.pago.esperar_respuesta()
        self.pago.esperar_estable(1)
        self._captura(f"P4 - Respuesta al elegir Tarjeta: {estado}")
        return estado

    # ---------- pinpad real ----------
    FINALES_APP = ("aprobado", "rechazado")
    FINALES_PINPAD = ("pin_aprobada", "pin_tiempo_agotado", "pin_declinada", "pin_nip_cancelado")

    def estado_cobro(self):
        """Estado actual del cobro, sea en Rompefilas o en el pinpad (una sola lectura de la pantalla):
        aprobado | rechazado (Rompefilas) · fase del pinpad (PinpadPage.FASES) · None."""
        textos = self.pago.textos()
        if "¡Pago exitoso!" in textos or "Pago exitoso" in textos:
            return "aprobado"
        if "No se pudo procesar el pago" in textos:
            return "rechazado"
        return self.pinpad.fase(textos)

    def _esperar_estado(self, aceptados, timeout):
        """Espera hasta que el estado del cobro sea uno de 'aceptados'. Regresa el estado (o None)."""
        fin = time.time() + timeout
        while True:
            estado = self.estado_cobro()
            if estado in aceptados:
                return estado
            if time.time() >= fin:
                return None
            time.sleep(0.5)

    def _fase(self, nombre, descripcion):
        self.cobro.setdefault("fases", []).append(nombre)
        self._captura(descripcion)

    def esperar_tarjeta_del_tester(self, instruccion, plan="contado", timeout=None):
        """Con el pinpad real abierto guía el cobro: tarjeta (3 min) -> lectura -> mensualidades (>= $1,000; la suite
        elige 'plan': 'contado' o '6msi') -> NIP (3 min) -> resultado del pinpad -> resultado en Rompefilas.
        Regresa aprobado | rechazado | tiempo_agotado | nip_cancelado | sin_resultado (detalle en self.cobro)."""
        self.cobro = {"fases": [], "plan_ofrecido": False, "opciones": [], "plan_elegido": "", "resumen_nip": {}}
        finales = self.FINALES_APP + self.FINALES_PINPAD
        referencia, monto = getattr(self.ev, "referencia", ""), getattr(self.ev, "monto", None)

        # 1) Pantalla 'Acerca, inserta o desliza tu tarjeta'
        estado = self._esperar_estado(("insertar", "leyendo", "mensualidades", "nip") + finales,
                                      settings.TIMEOUT_TRANSICION_PINPAD)
        if estado == "insertar":
            self.cobro["monto_pinpad"] = self.pinpad.resumen().get("Monto", "")
            self._fase("insertar", f"Pinpad - Acerca, inserta o desliza tu tarjeta (monto {self.cobro['monto_pinpad']})")

            # 2) El tester presenta la tarjeta (3 min)
            estado = pedir_tarjeta(instruccion, referencia=referencia, monto=monto, evidencia=self.ev,
                                   timeout=timeout or settings.TIMEOUT_TARJETA,
                                   hasta=lambda: self._esperar_estado(("leyendo", "mensualidades", "nip") + finales, 0))
        if not estado:
            return self._despues_del_cobro("sin_resultado")

        # 3) 'Leyendo tarjeta...'
        if estado == "leyendo":
            self._fase("leyendo", "Pinpad - Leyendo tarjeta")
            estado = self._esperar_estado(("mensualidades", "nip") + finales, 60)

        # 4) '¿Cuántas mensualidades?' (montos >= $1,000): la suite elige el plan
        if estado == "mensualidades":
            self.cobro["plan_ofrecido"] = True
            self.cobro["opciones"] = self.pinpad.opciones_de_pago()
            self._fase("mensualidades", "Pinpad - ¿Cuántas mensualidades?")
            self.pinpad.elegir_plan(plan)
            self.cobro["plan_elegido"] = plan
            if self.ev:
                self.ev.nota("Plan elegido por la suite: "
                             + ("6 meses sin intereses" if plan == "6msi" else "Sin mensualidades (pago de contado)"))
            estado = self._esperar_estado(("nip",) + finales, 60)

        # 5) 'Ingresa tu PIN en el lector' (3 min)
        if estado == "nip":
            self.cobro["resumen_nip"] = self.pinpad.resumen()
            self._fase("nip", f"Pinpad - Ingresa tu PIN {self.cobro['resumen_nip']}")
            estado = pedir_nip(evidencia=self.ev, timeout=settings.TIMEOUT_NIP,
                               hasta=lambda: self._esperar_estado(finales, 0))
            if not estado:
                return self._despues_del_cobro("sin_resultado")

        # 6) Resultado en el pinpad (dura poco) y después en Rompefilas
        estado_pinpad = ""
        if estado in self.FINALES_PINPAD:
            estado_pinpad = estado
            self._fase(estado, "Pinpad - " + estado.replace("pin_", "").replace("_", " "))
            estado = self._esperar_estado(self.FINALES_APP, 45) or estado
        self.cobro["pinpad"] = estado_pinpad

        if estado == "aprobado":
            resultado = "aprobado"
        elif estado_pinpad == "pin_tiempo_agotado":
            resultado = "tiempo_agotado"
        elif estado_pinpad == "pin_nip_cancelado":
            resultado = "nip_cancelado"
        elif estado in ("rechazado", "pin_declinada"):
            resultado = "rechazado"
        else:
            resultado = "sin_resultado"
        self.cobro["detalle_app"] = self.pago.detalle_error() if resultado != "aprobado" else ""
        if self.ev:
            self.ev.nota(f"Cobro: fases {self.cobro['fases']} · resultado '{resultado}'"
                         + (f" · Rompefilas: '{self.cobro['detalle_app']}'" if self.cobro["detalle_app"] else ""))
        return self._despues_del_cobro(resultado)

    def esperar_sin_tarjeta(self, timeout):
        """Deja el pinpad esperando sin presentar tarjeta hasta que expire (CP-TJ-ROM-003).
        Regresa tiempo_agotado | rechazado | aprobado | sin_resultado."""
        self.cobro = {"fases": []}
        estado = self._esperar_estado(self.FINALES_APP + self.FINALES_PINPAD, timeout)
        estado_pinpad = estado if estado in self.FINALES_PINPAD else ""
        if estado_pinpad:
            self._fase(estado, "Pinpad - " + estado.replace("pin_", "").replace("_", " "))
            estado = self._esperar_estado(self.FINALES_APP, 45) or estado
        self.cobro["pinpad"] = estado_pinpad
        self.cobro["detalle_app"] = self.pago.detalle_error()
        if estado_pinpad == "pin_tiempo_agotado":
            return "tiempo_agotado"
        return estado if estado in self.FINALES_APP else "sin_resultado"

    def completar_cobro(self, simulado="aprobado", instruccion="", plan="contado"):
        """Termina el cobro con el módulo de pago ya abierto.
        Simulador de Memphis: toca 'Approved'/'Declined' según 'simulado' (sin tester).
        Pinpad real: guía al tester con la tarjeta y el NIP (requiere INTERACTIVO=true); 'plan' es lo que la
        suite elige si aparece '¿Cuántas mensualidades?' ('contado' o '6msi')."""
        if self.pago.es_simulador():
            if self.ev:
                self.ev.nota(f"Módulo de pago: simulador de Memphis → '{'Approved' if simulado == 'aprobado' else 'Declined'}'")
            self.pago.simular(simulado)
            resultado = self.pago.esperar_resultado(settings.TIMEOUT_APP_PAGO)
            return self._despues_del_cobro(resultado)
        requiere_tester(f"Pinpad real: {instruccion or 'presentar la tarjeta física'}")
        return self.esperar_tarjeta_del_tester(instruccion or "Presente una tarjeta CON FONDOS.", plan=plan)

    def exigir_pinpad_real(self, motivo):
        """Casos que dependen de la tarjeta física (chip, banda, NIP, contactless): con el simulador quedan
        Pendientes; con el pinpad real requieren al tester (INTERACTIVO=true)."""
        if self.pago.es_simulador():
            pendiente(f"{SIN_ANIMACION_TARJETA}. {motivo}")
        requiere_tester(motivo)

    def _despues_del_cobro(self, resultado):
        """Captura el resultado y, si se aprobó, deja el comprobante en pantalla y marca la referencia 'pagada'."""
        self.estados_redundantes = False
        if resultado == "aprobado":
            self.pago.esperar_estable(0.5)
            # CP-RC-ROM-007: 'Pago exitoso' y 'Pago procesado' a la vez antes del comprobante
            self.estados_redundantes = bool(self.driver.find_elements(*L.P4_PAGO_PROCESADO))
            self._captura("Pago aprobado (transición antes del comprobante)")
            if self.ev and self.ev.referencia:
                referencias.marcar_pagada(self.ev.referencia, self.ev.caso_id)
            self.recibo.visible(15)
            self.recibo.esperar_estable(1)
            self._captura("P5 - Comprobante")
        else:
            self.pago.esperar_estable(1)
            self._captura(f"Resultado del cobro: {resultado}")
        return resultado
