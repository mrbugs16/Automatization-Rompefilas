"""
MÓDULO 01 - IDENTIFICACIÓN (P1: referencia de pago)
· CP-GU-POS-001, CP-ID-ROM-001 a CP-ID-ROM-005
"""
import time

from config import locators as L
from config import settings
from config.datos_prueba import MSG_SIN_ADEUDOS, REF_CORTA, REF_INEXISTENTE, REF_VALIDA
from core import adb
from core.interaccion import pedir_accion
from core.marcadores import caso, interactiva


@caso("CP-GU-POS-001")
def test_CP_GU_POS_001_version_en_footer(flujo, evidencia):
    instalada = adb.version_app()
    footer = flujo.inicio.texto(L.FOOTER)
    evidencia.nota(f"Footer: '{footer}' · versión instalada (dumpsys): {instalada}")
    evidencia.captura("Footer con la versión")
    assert flujo.inicio.version_footer(), f"El footer no muestra una versión: '{footer}'"
    assert flujo.inicio.version_footer() == instalada, \
        f"El footer dice v{flujo.inicio.version_footer()} y la app instalada es {instalada}"


@caso("CP-ID-ROM-001")
def test_CP_ID_ROM_001_referencia_valida_manual(flujo, evidencia):
    flujo.iniciar()
    p1 = flujo.identificacion
    faltan = p1.teclado_completo()
    assert not faltan, f"El teclado numérico no está completo en pantalla; faltan: {faltan}"
    assert not p1.consultar_habilitado(), "'Consultar adeudos' está habilitado sin referencia"

    flujo.capturar_referencia(REF_VALIDA["referencia"])
    assert p1.referencia() == REF_VALIDA["referencia"], f"El campo muestra '{p1.referencia()}'"
    faltan = p1.teclado_completo()
    assert not faltan, f"Con la referencia capturada se ocultó parte del teclado: {faltan}"
    assert p1.existe(L.P1_BTN_CONSULTAR, 2), "El botón 'Consultar adeudos' quedó oculto"
    fuera = p1.fuera_de_pantalla()
    assert not fuera, f"Elementos fuera de la pantalla: {fuera}"
    assert p1.consultar_habilitado(), "'Consultar adeudos' no se habilitó con 16 dígitos"

    resultado = flujo.consultar()
    flujo._captura("Respuesta de 'Consultar adeudos'")
    assert resultado == "p2", f"No se mostró P2 con los adeudos (resultado: {resultado})"
    adeudos = flujo.adeudos.adeudos()
    evidencia.nota(f"{flujo.adeudos.contribuyente()} · {flujo.adeudos.contador()} · "
                   + ", ".join(f"{a['concepto']} {a['texto_monto']}" for a in adeudos))
    assert adeudos, "P2 no muestra adeudos"


@caso("CP-ID-ROM-002")
@interactiva("Requiere un recibo físico con código de barras/QR frente a la cámara de la T6")
def test_CP_ID_ROM_002_escaneo_codigo(flujo, evidencia):
    flujo.iniciar()
    flujo.identificacion.abrir_camara()
    assert flujo.identificacion.existe(L.ESCANER_TITULO, 10), "No se abrió el escáner de la cámara"
    evidencia.captura("Escáner de la cámara abierto")
    inicio = time.time()
    llego = pedir_accion("Coloque el código de barras/QR del recibo frente a la cámara de la T6.",
                         hasta=lambda: flujo.adeudos.existe(L.P2_BTN_PAGAR, 1), evidencia=evidencia)
    segundos = round(time.time() - inicio, 1)
    flujo._captura("Después del escaneo")
    evidencia.nota(f"Tiempo desde que se abrió el escáner hasta P2: {segundos} s (incluye acercar el recibo)")
    assert llego, "No se avanzó a P2 con el código escaneado"


@caso("CP-ID-ROM-003")
def test_CP_ID_ROM_003_referencia_corta(flujo, evidencia):
    flujo.iniciar()
    flujo.capturar_referencia(REF_CORTA)
    habilitado = flujo.identificacion.consultar_habilitado()
    evidencia.nota(f"'Consultar adeudos' con {len(REF_CORTA)} dígitos: {'habilitado' if habilitado else 'deshabilitado'}")
    if not habilitado:
        return  # validación de longitud: no se permite consultar (resultado esperado)
    resultado = flujo.consultar()
    flujo._captura("Respuesta con referencia de 10 dígitos")
    assert resultado == "sin_adeudos", f"Se esperaba '{MSG_SIN_ADEUDOS}' (resultado: {resultado})"
    assert flujo.identificacion.existe(L.P1_MSG_SIN_ADEUDOS_DETALLE, 2), "El mensaje no muestra el detalle completo"
    fuera = flujo.identificacion.fuera_de_pantalla()
    assert not fuera, f"El mensaje no es legible completo; fuera de pantalla: {fuera}"
    evidencia.nota("⚠ No hay validación de longitud: se consulta con menos de 16 dígitos")


@caso("CP-ID-ROM-004")
def test_CP_ID_ROM_004_referencia_inexistente(flujo, evidencia):
    flujo.iniciar()
    flujo.capturar_referencia(REF_INEXISTENTE)
    resultado = flujo.consultar()
    flujo._captura("Respuesta con referencia inexistente")
    assert resultado == "sin_adeudos", f"Se esperaba '{MSG_SIN_ADEUDOS}' (resultado: {resultado})"
    p1 = flujo.identificacion
    assert p1.visible(2), "La app no permaneció en P1"
    p1.borrar_todo()
    assert p1.referencia() == L.P1_PLACEHOLDER, f"'Borrar todo' no limpió el campo: '{p1.referencia()}'"
    p1.teclear("1")
    assert p1.referencia().startswith("1"), "No se puede capturar una nueva referencia tras el error"
    evidencia.captura("P1 lista para un nuevo intento")


@caso("CP-ID-ROM-005")
@interactiva("Requiere un recibo con el código de barras/QR rayado o doblado")
def test_CP_ID_ROM_005_codigo_ilegible(flujo, evidencia):
    flujo.iniciar()
    flujo.identificacion.abrir_camara()
    assert flujo.identificacion.existe(L.ESCANER_TITULO, 10), "No se abrió el escáner de la cámara"
    evidencia.captura("Escáner de la cámara abierto")
    pedir_accion("Coloque el recibo con el código DAÑADO frente a la cámara y espere (no lo retire).",
                 timeout=15, evidencia=evidencia)
    flujo._captura("A los 15 s con el código dañado")
    assert not flujo.adeudos.existe(L.P2_BTN_PAGAR, 1), "Se capturó una referencia con el código dañado"
    regreso = pedir_accion("Espere a que expire el escaneo (no toque la pantalla).",
                           hasta=lambda: flujo.driver.current_package == settings.APP_PACKAGE,
                           timeout=60, evidencia=evidencia)
    flujo._captura("Al expirar el escaneo")
    assert regreso, "El escáner no se cerró solo: la cámara no se libera al expirar el tiempo"
    assert flujo.identificacion.existe(L.P1_TECLA(1), 3), "No se ofrece la captura manual al expirar el escaneo"
