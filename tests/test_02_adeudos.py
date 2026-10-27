"""
MÓDULO 02 - ADEUDOS (P2)
· CP-AD-ROM-001 a CP-AD-ROM-004

Regla de negocio (ajuste del 15/10/2026): los adeudos NO se pagan de forma individual; en todos los casos se
pagan en conjunto. P2 no tiene casillas ni 'Seleccionar todo' y 'Pagar ahora' cobra siempre el total.
CP-AD-ROM-001 a 003 validan esa regla (si una versión agrega selección individual, fallan).
"""
from config import locators as L
from config.datos_prueba import REF_INEXISTENTE_2, REF_VALIDA
from core.marcadores import caso

REGLA = "Los adeudos se pagan en conjunto (sin selección individual)"


def _validar_lista(flujo, evidencia):
    """Conceptos y montos completos y dentro de la pantalla."""
    p2 = flujo.adeudos
    adeudos = p2.adeudos()
    evidencia.nota(f"{p2.contador()}: " + ", ".join(f"{a['concepto']} {a['texto_monto']}" for a in adeudos))
    assert len(adeudos) == REF_VALIDA["adeudos"], f"Se esperaban {REF_VALIDA['adeudos']} adeudos y hay {len(adeudos)}"
    fuera = p2.fuera_de_pantalla()
    assert not fuera, f"Conceptos o montos fuera de la pantalla: {fuera}"
    return adeudos


def _cobra_el_total(flujo, evidencia, adeudos):
    """'Pagar ahora' lleva a P3 con la suma de TODOS los adeudos."""
    suma = round(sum(a["monto"] for a in adeudos), 2)
    assert flujo.adeudos.pagar_habilitado(), "'Pagar ahora' está deshabilitado"
    flujo.adeudos.pagar()
    assert flujo.metodo.visible(), "No se avanzó a P3"
    flujo.metodo.esperar_estable(0.8)
    total = flujo.metodo.total()
    flujo._captura(f"P3 - total ${total:,.2f}")
    evidencia.nota(f"Suma de los {len(adeudos)} adeudos: ${suma:,.2f} · Total en P3: ${total:,.2f}")
    assert total == suma, f"P3 cobra ${total:,.2f} y la suma de todos los adeudos es ${suma:,.2f}"
    return total


def _sin_seleccion_individual(flujo, evidencia):
    casillas = flujo.adeudos.casillas()
    evidencia.nota(f"{REGLA}: casillas en P2 = {len(casillas)}, "
                   f"'Seleccionar todo' = {'sí' if flujo.adeudos.existe(L.P2_SELECCIONAR_TODO, 1) else 'no'}")
    assert not casillas, (f"P2 permite seleccionar adeudos de forma individual ({len(casillas)} casillas); "
                          f"la regla es pagar todos en conjunto")


@caso("CP-AD-ROM-001")
def test_CP_AD_ROM_001_pago_en_conjunto(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    adeudos = _validar_lista(flujo, evidencia)
    _sin_seleccion_individual(flujo, evidencia)
    _cobra_el_total(flujo, evidencia, adeudos)


@caso("CP-AD-ROM-002")
def test_CP_AD_ROM_002_todos_los_adeudos_incluidos(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    adeudos = _validar_lista(flujo, evidencia)
    assert not flujo.adeudos.existe(L.P2_SELECCIONAR_TODO, 1), \
        "Existe 'Seleccionar todo': con la regla de pago en conjunto todos los adeudos ya van incluidos"
    total = _cobra_el_total(flujo, evidencia, adeudos)
    assert f"${total:,.2f}" == REF_VALIDA["total"], f"El total no es el esperado {REF_VALIDA['total']}"


@caso("CP-AD-ROM-003")
def test_CP_AD_ROM_003_no_se_puede_quitar_adeudos(flujo, evidencia):
    flujo.ir_a_adeudos(REF_VALIDA["referencia"])
    adeudos = _validar_lista(flujo, evidencia)
    _sin_seleccion_individual(flujo, evidencia)
    # No es posible dejar 0 adeudos: 'Pagar ahora' siempre cobra el total (nunca $0.00)
    total = _cobra_el_total(flujo, evidencia, adeudos)
    assert total > 0, "P3 cobra $0.00"


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
    assert not [t for t in textos if t.lstrip("-").startswith("$")], "Siguen visibles montos del contribuyente anterior"
