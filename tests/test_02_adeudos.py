"""
MÓDULO 02 - ADEUDOS (P2)
· CP-AD-ROM-001 a CP-AD-ROM-004

v1.6.36: P2 lista los adeudos sin casillas ni 'Seleccionar todo'; 'Pagar ahora' cobra siempre el total.
Si una versión nueva agrega la selección, estas pruebas la usan automáticamente (ver locators.CASILLAS).
"""
from config import locators as L
from config.datos_prueba import REF_INEXISTENTE_2, REF_VALIDA
from core import adb
from core.marcadores import caso, pendiente


def _validar_lista(flujo, evidencia):
    """Conceptos y montos completos y dentro de la pantalla."""
    p2 = flujo.adeudos
    adeudos = p2.adeudos()
    evidencia.nota(f"{p2.contador()}: " + ", ".join(f"{a['concepto']} {a['texto_monto']}" for a in adeudos))
    assert len(adeudos) == REF_VALIDA["adeudos"], f"Se esperaban {REF_VALIDA['adeudos']} adeudos y hay {len(adeudos)}"
    fuera = p2.fuera_de_pantalla()
    assert not fuera, f"Conceptos o montos fuera de la pantalla: {fuera}"
    return adeudos


@caso("CP-AD-ROM-001")
def test_CP_AD_ROM_001_seleccion_individual(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    adeudos = _validar_lista(flujo, evidencia)
    casillas = flujo.adeudos.casillas()
    assert casillas, (f"P2 no permite seleccionar un adeudo individual (no hay casillas en v{adb.version_app()}); "
                      f"'Pagar ahora' cobra los {len(adeudos)} adeudos juntos")
    casillas[0].click()
    flujo._captura("Un adeudo seleccionado")
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3"
    total = flujo.metodo.total()
    flujo._captura("P3 con un adeudo")
    assert total == adeudos[0]["monto"], f"P3 cobra ${total} en lugar de {adeudos[0]['texto_monto']}"


@caso("CP-AD-ROM-002")
def test_CP_AD_ROM_002_seleccionar_todo(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    adeudos = _validar_lista(flujo, evidencia)
    suma = round(sum(a["monto"] for a in adeudos), 2)
    if flujo.adeudos.existe(L.P2_SELECCIONAR_TODO, 1):
        flujo.adeudos.tocar(L.P2_SELECCIONAR_TODO)
        marcadas = [c for c in flujo.adeudos.casillas() if c.get_attribute("checked") == "true"]
        assert len(marcadas) == len(adeudos), f"'Seleccionar todo' marcó {len(marcadas)} de {len(adeudos)}"
    else:
        evidencia.nota(f"⚠ No existe 'Seleccionar todo' en v{adb.version_app()}: la app cobra siempre todos los adeudos")
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3"
    flujo.metodo.esperar_estable(0.8)
    total = flujo.metodo.total()
    flujo._captura(f"P3 - total ${total:,.2f}")
    evidencia.nota(f"Suma de P2: ${suma:,.2f} · Total en P3: ${total:,.2f} · Esperado: {REF_VALIDA['total']}")
    assert total == suma, f"El total de P3 (${total:,.2f}) no es la suma de los adeudos (${suma:,.2f})"
    assert f"${total:,.2f}" == REF_VALIDA["total"], f"El total no es el esperado {REF_VALIDA['total']}"


@caso("CP-AD-ROM-003")
def test_CP_AD_ROM_003_sin_seleccion(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    casillas = flujo.adeudos.casillas()
    if not casillas:
        pendiente(f"No aplica en v{adb.version_app()}: P2 no tiene selección de adeudos "
                  "(siempre se cobran todos, no es posible dejar 0 seleccionados)")
    for c in casillas:
        if c.get_attribute("checked") == "true":
            c.click()
    flujo._captura("Ningún adeudo seleccionado")
    if flujo.adeudos.pagar_habilitado():
        flujo.adeudos.pagar()
        assert not flujo.metodo.visible(3), "Se avanzó a P3 sin adeudos seleccionados"


@caso("CP-AD-ROM-004")
def test_CP_AD_ROM_004_cambiar_referencia(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    contribuyente = flujo.adeudos.contribuyente()
    flujo.adeudos.cambiar_referencia()
    p1 = flujo.identificacion
    assert p1.visible(), "'Cambiar referencia' no regresó a P1"
    p1.esperar_estable(0.5)
    flujo._captura("P1 después de 'Cambiar referencia'")
    if p1.referencia() != L.P1_PLACEHOLDER:
        evidencia.nota(f"El campo conserva la referencia anterior ('{p1.referencia()}'); se limpia con 'Borrar todo'")
        p1.borrar_todo()
    flujo.capturar_referencia(REF_INEXISTENTE_2)
    resultado = flujo.consultar()
    flujo._captura("Respuesta con la referencia nueva")
    assert resultado == "sin_adeudos", f"Se esperaba 'No se encontraron adeudos' (resultado: {resultado})"
    textos = p1.textos()
    assert contribuyente not in textos, f"Siguen visibles datos del contribuyente anterior ({contribuyente})"
    assert not [t for t in textos if t.startswith("$")], "Siguen visibles montos del contribuyente anterior"
