"""
MÓDULO 11 - PAGOS A 6 MESES SIN INTERESES (transacciones a partir de $1,000.00)
· CP-MSI-ROM-001 a CP-MSI-ROM-006

Pinpad real (27/10/2026): con montos ≥ $1,000, después de leer la tarjeta aparece '¿Cuántas mensualidades?'
('Sin mensualidades · Pago de contado' / '6 meses sin intereses · MSI') y la pantalla del NIP muestra
'Mensualidades 6'. La suite elige la referencia por monto, verifica el total en P3, abre el pinpad y,
cuando aparece la hoja de mensualidades, elige el plan del caso; el tester presenta la tarjeta y el NIP
(INTERACTIVO=true, 3 min cada uno). El ticket impreso se revisa a mano.
En el reporte se distinguen con la etiqueta '6 MSI' y el filtro 'Tipo de pago'.
"""
import pytest

from config import settings
from core import referencias
from core.marcadores import SIN_ANIMACION_TARJETA, caso, pendiente

pytestmark = [pytest.mark.msi, pytest.mark.tarjeta, pytest.mark.pinpad]

MINIMO = settings.MSI_MONTO_MINIMO
PLAZO = settings.MSI_PLAZO


def _cobrar(flujo, evidencia, cobro, instruccion, plan, aplica_msi, minimo=None, maximo=None):
    """Referencia por monto -> P3 (valida la regla de $1,000) -> pinpad -> tarjeta + NIP del tester."""
    ref = cobro(minimo=minimo, maximo=maximo)
    total = evidencia.monto
    if total != ref["monto"]:  # los adeudos cambian con el tiempo (recargos/descuentos): manda el total actual de P3
        evidencia.nota(f"El total cambió desde la consulta del catálogo: ${ref['monto']:,.2f} -> ${total:,.2f} (P3)")
        referencias.actualizar(ref["referencia"], monto=total)
    if aplica_msi:
        assert total >= MINIMO, f"El total ${total:,.2f} no alcanza el mínimo de ${MINIMO:,.2f} para 6 MSI"
        evidencia.nota(f"6 MSI aplica: total ${total:,.2f} ≥ ${MINIMO:,.2f} · mensualidad esperada "
                       f"${total / PLAZO:,.2f} × {PLAZO}")
    else:
        assert total < MINIMO, f"El total ${total:,.2f} es ≥ ${MINIMO:,.2f}: no sirve para validar que NO se ofrezca MSI"
        evidencia.nota(f"6 MSI NO aplica: total ${total:,.2f} < ${MINIMO:,.2f}")
    if flujo.pago.es_simulador():
        pendiente(f"{SIN_ANIMACION_TARJETA}. El simulador no ofrece planes de mensualidades")
    resultado = flujo.completar_cobro("aprobado", instruccion, plan=plan)
    c = flujo.cobro
    evidencia.nota(f"Pinpad: monto '{c.get('monto_pinpad', '')}' · mensualidades ofrecidas: "
                   f"{'sí' if c.get('plan_ofrecido') else 'no'} {c.get('opciones', [])} · NIP: {c.get('resumen_nip', {})}")
    return total, resultado


def _monto_pinpad_ok(flujo, total):
    monto = flujo.cobro.get("monto_pinpad", "").replace("$", "").replace(",", "")
    if not monto:  # la tarjeta se leyó antes de que la suite viera 'Acerca, inserta o desliza tu tarjeta'
        flujo.ev.nota(f"⚠ (Manual) No se alcanzó a leer el monto del pinpad: verificar ${total:,.2f} en las capturas")
        return
    assert abs(float(monto) - total) < 0.01, \
        f"El pinpad muestra el monto '{flujo.cobro.get('monto_pinpad')}' y se cobra ${total:,.2f}"


def _se_ofrecio_6msi(flujo):
    return flujo.cobro.get("plan_ofrecido") and any("6 meses" in o for o in flujo.cobro.get("opciones", []))


@caso("CP-MSI-ROM-001")
def test_CP_MSI_ROM_001_credito_participante(flujo, evidencia, cobro):
    total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de CRÉDITO de un banco participante en 6 MSI.",
                               "6msi", True, minimo=MINIMO)
    _monto_pinpad_ok(flujo, total)
    assert _se_ofrecio_6msi(flujo), "Con un total ≥ $1,000 no se ofreció '6 meses sin intereses'"
    if flujo.cobro.get("resumen_nip"):
        assert flujo.cobro["resumen_nip"].get("Mensualidades") == str(PLAZO), \
            f"La pantalla del NIP no muestra 'Mensualidades {PLAZO}': {flujo.cobro.get('resumen_nip')}"
    else:  # la pantalla segura de Topwise no expone sus textos
        evidencia.nota(f"⚠ (Manual) Verificar 'Mensualidades {PLAZO}' en la captura de la pantalla del NIP")
    assert resultado == "aprobado", f"El pago a 6 MSI terminó en '{resultado}'"
    datos = flujo.recibo.datos()
    evidencia.nota(f"Comprobante: {datos}")
    assert datos.get("Total", "").startswith(f"${total:,.2f}"), \
        f"El cargo total ({datos.get('Total')}) no es el adeudo ${total:,.2f} (no debe haber intereses)"
    evidencia.nota("⚠ (Manual) Confirmar en el ticket el plazo de 6 meses y que no hay intereses ni comisiones")


@caso("CP-MSI-ROM-002")
def test_CP_MSI_ROM_002_menor_a_1000_sin_msi(flujo, evidencia, cobro):
    total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de CRÉDITO de un banco participante.",
                               "contado", False, maximo=MINIMO - 0.01)
    assert not flujo.cobro.get("plan_ofrecido"), \
        f"Con ${total:,.2f} (< ${MINIMO:,.2f}) se mostró '¿Cuántas mensualidades?': {flujo.cobro.get('opciones')}"
    assert resultado == "aprobado", f"El pago de contado terminó en '{resultado}'"


@caso("CP-MSI-ROM-003")
def test_CP_MSI_ROM_003_monto_limite(flujo, evidencia, cobro):
    _total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de CRÉDITO de un banco participante.",
                                "6msi", True, minimo=MINIMO, maximo=MINIMO)
    assert _se_ofrecio_6msi(flujo), f"Con exactamente ${MINIMO:,.2f} no se ofreció 6 MSI (el mínimo debe ser inclusivo)"
    assert resultado == "aprobado", f"El pago a 6 MSI terminó en '{resultado}'"


@caso("CP-MSI-ROM-004")
def test_CP_MSI_ROM_004_debito_sin_msi(flujo, evidencia, cobro):
    total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de DÉBITO.", "contado", True, minimo=MINIMO)
    assert not _se_ofrecio_6msi(flujo), \
        f"Con tarjeta de débito se ofreció 6 MSI (total ${total:,.2f}): {flujo.cobro.get('opciones')}"
    assert resultado == "aprobado", f"El pago con débito terminó en '{resultado}'"


@caso("CP-MSI-ROM-005")
def test_CP_MSI_ROM_005_comprobante_6_msi(flujo, evidencia, cobro):
    total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de CRÉDITO de un banco participante en 6 MSI.",
                               "6msi", True, minimo=MINIMO)
    assert resultado == "aprobado", f"El pago a 6 MSI terminó en '{resultado}'"
    textos = flujo.recibo.textos()
    datos = flujo.recibo.datos()
    evidencia.nota(f"Comprobante: {datos}")
    menciones = [t for t in textos if "MSI" in t or "meses sin intereses" in t.lower() or "mensualidad" in t.lower()]
    evidencia.nota(f"Menciones de MSI en el comprobante: {menciones or 'ninguna'} · mensualidad esperada ${total / PLAZO:,.2f}")
    assert menciones, "El comprobante (P5) no indica que el pago fue a 6 meses sin intereses"
    assert datos.get("Autorización"), "El comprobante no muestra la autorización"
    assert datos.get("Tarjeta", "").count("*") >= 4, f"La tarjeta no aparece enmascarada: '{datos.get('Tarjeta')}'"
    evidencia.nota("⚠ (Manual) Revisar en el ticket impreso: plazo, mensualidad, autorización y últimos 4 dígitos")


@caso("CP-MSI-ROM-006")
def test_CP_MSI_ROM_006_credito_no_participante(flujo, evidencia, cobro):
    total, resultado = _cobrar(flujo, evidencia, cobro, "Inserte una tarjeta de CRÉDITO de un banco NO participante en MSI.",
                               "contado", True, minimo=MINIMO)
    assert not _se_ofrecio_6msi(flujo), \
        f"Con una tarjeta no participante se ofreció 6 MSI: {flujo.cobro.get('opciones')}"
    assert resultado == "aprobado", f"El pago de ${total:,.2f} en una sola exhibición terminó en '{resultado}'"
