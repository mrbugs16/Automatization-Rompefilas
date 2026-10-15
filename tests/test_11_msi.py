"""
MÓDULO 11 - PAGOS A 6 MESES SIN INTERESES (transacciones a partir de $1,000.00)
· CP-MSI-ROM-001 a CP-MSI-ROM-006

ESTADO (v1.6.37): 6 MSI AÚN NO ESTÁ INTEGRADO. El plan se elige en el módulo de pago y depende de la
animación para insertar la tarjeta y capturar el NIP, que todavía falta (hoy el módulo es el simulador de
Memphis, solo Approved / Declined). Los casos se mantienen para tenerlos listos:

- Lo que sí se automatiza: elegir una referencia por monto (≥ / < $1,000), llegar a P3 y verificar que se
  cobre ese total, y calcular la mensualidad esperada (total / 6). NO se abre el módulo de pago.
- Después el caso queda 'Pendiente' con el motivo y la lista de lo que hay que validar a mano cuando se integre.
En el reporte se distinguen con la etiqueta '6 MSI' y el filtro 'Tipo de pago'.
"""
import pytest

from config import settings
from core import referencias
from core.marcadores import caso, pendiente

pytestmark = [pytest.mark.msi, pytest.mark.tarjeta]

MINIMO = settings.MSI_MONTO_MINIMO
PLAZO = settings.MSI_PLAZO
NO_INTEGRADO = "6 MSI aún no integrado (falta la animación para insertar la tarjeta y capturar el NIP)"


def _preparar(flujo, evidencia, aplica_msi, minimo=None, maximo=None):
    """Toma una referencia 'disponible' en el rango, llega a P3 y valida el total contra la regla de $1,000."""
    try:
        ref = referencias.disponible(minimo, maximo)
    except LookupError as e:
        pendiente(str(e))
    flujo.ir_a_metodo(ref["referencia"])
    total = flujo.metodo.total()
    assert total == ref["monto"], f"P3 cobra ${total:,.2f} y la referencia tiene un total de ${ref['monto']:,.2f}"
    if aplica_msi:
        assert total >= MINIMO, f"El total ${total:,.2f} no alcanza el mínimo de ${MINIMO:,.2f} para 6 MSI"
        evidencia.nota(f"6 MSI aplica: total ${total:,.2f} ≥ ${MINIMO:,.2f} · mensualidad esperada "
                       f"${total / PLAZO:,.2f} × {PLAZO}")
    else:
        assert total < MINIMO, f"El total ${total:,.2f} es ≥ ${MINIMO:,.2f}: no sirve para validar que NO se ofrezca MSI"
        evidencia.nota(f"6 MSI NO aplica: total ${total:,.2f} < ${MINIMO:,.2f}")
    return total


@caso("CP-MSI-ROM-001")
def test_CP_MSI_ROM_001_credito_participante(flujo, evidencia):
    total = _preparar(flujo, evidencia, True, minimo=MINIMO)
    pendiente(f"{NO_INTEGRADO}. Validar: se ofrece y aplica el plan de 6 MSI con tarjeta de crédito participante, "
              f"P5 muestra el plazo y el cargo total es ${total:,.2f} sin intereses (mensualidad ${total / PLAZO:,.2f})")


@caso("CP-MSI-ROM-002")
def test_CP_MSI_ROM_002_menor_a_1000_sin_msi(flujo, evidencia):
    total = _preparar(flujo, evidencia, False, maximo=MINIMO - 0.01)
    pendiente(f"{NO_INTEGRADO}. Validar: con ${total:,.2f} (< ${MINIMO:,.2f}) NO se ofrece 6 MSI y se cobra en una sola exhibición")


@caso("CP-MSI-ROM-003")
def test_CP_MSI_ROM_003_monto_limite(flujo, evidencia):
    total = _preparar(flujo, evidencia, True, minimo=MINIMO, maximo=MINIMO)
    pendiente(f"{NO_INTEGRADO}. Validar: con exactamente ${total:,.2f} se ofrece 6 MSI (mínimo inclusivo)")


@caso("CP-MSI-ROM-004")
def test_CP_MSI_ROM_004_debito_sin_msi(flujo, evidencia):
    total = _preparar(flujo, evidencia, True, minimo=MINIMO)
    pendiente(f"{NO_INTEGRADO}. Validar: con tarjeta de DÉBITO no se ofrecen MSI aunque el total sea ${total:,.2f}")


@caso("CP-MSI-ROM-005")
def test_CP_MSI_ROM_005_comprobante_6_msi(flujo, evidencia):
    total = _preparar(flujo, evidencia, True, minimo=MINIMO)
    pendiente(f"{NO_INTEGRADO}. Validar en P5 y en el ticket: 'Pago a 6 meses sin intereses', total ${total:,.2f}, "
              f"mensualidad ${total / PLAZO:,.2f}, autorización y solo los últimos 4 dígitos")


@caso("CP-MSI-ROM-006")
def test_CP_MSI_ROM_006_credito_no_participante(flujo, evidencia):
    total = _preparar(flujo, evidencia, True, minimo=MINIMO)
    pendiente(f"{NO_INTEGRADO}. Validar: con tarjeta de crédito NO participante no se ofrecen MSI (o se informa) y el "
              f"pago de ${total:,.2f} se completa en una sola exhibición")
