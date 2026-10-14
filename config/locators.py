"""
Localizadores reales de Rompefilas v1.6.36 (tomados con UiAutomator2 sobre la T6).

La app es un WebView: UiAutomator2 expone el DOM como nodos nativos cuyo texto visible
queda en @text (no en @content-desc). Por eso todo se localiza por texto.

Los marcados con 'TODO confirmar' son pantallas que aún no existen en esta versión
(módulo de pago, recibo, avisos de papel/batería): se ajustan cuando llegue la nueva versión.
"""
from appium.webdriver.common.appiumby import AppiumBy

X = AppiumBy.XPATH


def texto(t):
    return X, f'//*[@text="{t}"]'


def contiene(t):
    return X, f'//*[contains(@text, "{t}")]'


def boton(t):
    return X, f'//android.widget.Button[@text="{t}"]'


def boton_contiene(t):
    return X, f'//android.widget.Button[contains(@text, "{t}")]'


def _cualquiera(*textos):
    return X, "//*[" + " or ".join(f'contains(@text, "{t}")' for t in textos) + "]"


BOTONES = (X, "//android.widget.Button")
CASILLAS = (X, '//*[@checkable="true" or self::android.widget.CheckBox]')

# ==============================================
# COMUNES
# ==============================================
ENCABEZADO_LOGO = (X, '//android.widget.Image[@text="Gobierno de Puebla"]')
FOOTER = contiene("La Capital Imparable")
# Indicador de pasos: 1 Identificar · 2 Adeudos · 3 Método · 4 Pago · 5 Recibo
PASOS = ("Identificar", "Adeudos", "Método", "Pago", "Recibo")

# ==============================================
# INICIO
# ==============================================
INICIO_TITULO = texto("¿Qué desea pagar hoy?")
INICIO_BTN = boton("Toque para iniciar")
INICIO_TEXTO_TARJETAS = contiene("Visa, Mastercard y más")
INICIO_TEXTO_CREDITO_DEBITO = texto("Crédito y Débito")

# ==============================================
# P1 - IDENTIFICAR
# ==============================================
P1_TITULO = texto("Ingrese su referencia de pago")
P1_SUBTITULO = contiene("16 dígitos")
P1_ESCANER_TITULO = texto("Escanee el código de barras")
P1_BTN_CAMARA = boton("Escanear con la cámara")
# El campo de la referencia se lee del XML (IdentificacionPage.referencia): el XPath de UiAutomator2
# no soporta el eje 'preceding::'. Vacío muestra el placeholder:
P1_PLACEHOLDER = "0000000000000000"
P1_TECLA = lambda d: boton(str(d))  # noqa: E731
P1_BTN_BORRAR_TODO = boton("Borrar todo")
P1_BTN_BORRAR = boton("Borrar")
P1_BTN_CUENTA_PREDIAL = boton_contiene("¿Tiene su cuenta predial?")
P1_BTN_CONSULTAR = boton("Consultar adeudos")
P1_BTN_REGRESAR_INICIO = boton("Regresar al inicio")
P1_BTN_PROBAR_IMPRESORA = boton("Probar impresora")
P1_MSG_SIN_ADEUDOS = texto("No se encontraron adeudos")
P1_MSG_SIN_ADEUDOS_DETALLE = contiene("Verifique que su referencia")
# Tarjeta que decodifica la referencia mientras se captura (ej. 'Impuesto Predial ✓ Completa', '10/16')
P1_REF_COMPLETA = contiene("Completa")

# Cuenta predial (PU-5-01)
P1_PREDIAL_TITULO = texto("Seleccione el tipo de cuenta predial")
P1_BTN_PU = boton("PU Predial Urbano")
P1_BTN_PR = boton("PR Predial Rústico")
P1_BTN_FOLIO_16 = boton("Tengo el folio de 16 dígitos")

# Escáner de la cámara (SDK Topwise, otra app)
ESCANER_PAQUETE = "com.android.topwise.topusdkservice"
ESCANER_TITULO = (AppiumBy.ID, "com.android.topwise.topusdkservice:id/qr_code_fl_title")

# ==============================================
# P2 - ADEUDOS
# ==============================================
P2_CONTADOR = contiene("adeudos en esta referencia")
P2_BTN_CAMBIAR_REFERENCIA = boton("Cambiar referencia")
P2_BTN_PAGAR = boton("Pagar ahora")
P2_MONTOS = (X, '//android.widget.TextView[starts-with(@text, "$")]')
P2_SELECCIONAR_TODO = contiene("Seleccionar todo")  # TODO confirmar: no existe en v1.6.36

# ==============================================
# P3 - MÉTODO DE PAGO
# ==============================================
P3_TITULO = texto("¿Cómo desea pagar?")
P3_REFERENCIA = contiene("Ref: ")
P3_BTN_TARJETA = boton_contiene("Tarjeta")
P3_BTN_EFECTIVO = boton_contiene("Efectivo")
P3_BTN_REGRESAR_ADEUDOS = boton("Regresar a adeudos")
P3_BTN_CANCELAR = boton("Cancelar y salir")

# ==============================================
# P4 - PAGO (módulo de pago de la T6)
# ==============================================
P4_ERROR_TITULO = texto("No se pudo procesar el pago")
P4_ERROR_APP_PAGO = contiene("No se pudo comunicar con la aplicación de pago")
P4_ERROR_SIN_CARGO = contiene("No se realizó ningún cargo")
P4_ERROR_SUGERENCIA_EFECTIVO = contiene("pagar en efectivo")
P4_BTN_INTENTAR = boton("Intentar de nuevo")
P4_BTN_REGRESAR_INICIO = boton("Regresar al inicio")
# TODO confirmar con la nueva versión (pantalla del módulo de pago y sus mensajes)
P4_INSTRUCCION_TARJETA = _cualquiera("Inserte", "inserte", "Deslice", "Acerque", "acerque")
P4_TIEMPO_AGOTADO = _cualquiera("Tiempo agotado", "tiempo de espera", "Tiempo de espera")
P4_NIP_INCORRECTO = _cualquiera("NIP incorrecto", "PIN incorrecto")
P4_TARJETA_NO_ACEPTADA = _cualquiera("no aceptada", "no soportada", "vencida")
P4_BTN_CANCELAR_COBRO = (X, '//*[@text="Cancelar" or @text="CANCELAR" or @content-desc="Cancelar"]')
P4_SIN_CONEXION_TERMINAL = contiene("No se pudo conectar con la terminal")

# ==============================================
# P5 - RECIBO (TODO confirmar con la nueva versión)
# ==============================================
P5_PAGO_EXITOSO = _cualquiera("Pago exitoso", "Pago aprobado")
P5_PAGO_PROCESADO = contiene("Pago procesado")
P5_AUTORIZACION = _cualquiera("Autorización", "autorización")
P5_BTN_REIMPRIMIR = _cualquiera("Reimprimir", "Imprimir")
P5_LIMITE_IMPRESIONES = contiene("Límite de impresiones")
P5_CUENTA_REGRESIVA = _cualquiera("Regresando al inicio", "regresará al inicio")

# ==============================================
# AVISOS (TODO confirmar: no existen en v1.6.36)
# ==============================================
AVISO_SIN_PAPEL = _cualquiera("papel", "Papel")
AVISO_BATERIA_BAJA = (X, '//*[@package="com.exos.kiosko.rompefilas"][contains(@text, "batería") or contains(@text, "Batería")]')
# Diálogo del sistema Android (no de la app) al bajar la batería
ANDROID_BATERIA_BAJA = contiene("baja electricidad")
ANDROID_BTN_CERRAR = (X, '//*[@text="CERRAR" or @text="Cerrar"][not(@package="com.exos.kiosko.rompefilas")]')
AVISO_SIN_CONEXION = _cualquiera("conexión", "Conexión", "Sin red", "sin red")

# ==============================================
# MODAL DE INACTIVIDAD
# ==============================================
# Por XPath: con AppiumBy.ID, UiAutomator2 antepone el paquete ('com.exos...:id/') y no lo encuentra
INACTIVIDAD_TITULO = (X, '//*[@resource-id="inactivity-title"]')
INACTIVIDAD_CUENTA = contiene("La sesión se cerrará en")
INACTIVIDAD_BTN_CONTINUAR = boton("Continuar usando el kiosco")

# ==============================================
# ACCESO DE OPERADOR (TODO confirmar: no existe en v1.6.36)
# ==============================================
OPERADOR_USUARIO = (X, '//android.widget.EditText[1]')
OPERADOR_BTN_INGRESAR = boton("Ingresar")
OPERADOR_ERROR = _cualquiera("incorrect", "inválid")

# ==============================================
# CORTE DE CAJA / HISTORIAL (TODO confirmar: no existe en v1.6.36)
# ==============================================
MENU_CORTE = _cualquiera("Corte de caja", "Cierre de lote")
MENU_HISTORIAL = _cualquiera("Historial", "Transacciones")
