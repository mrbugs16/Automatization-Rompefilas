"""
MÓDULO 11 - PAGOS A 6 MESES SIN INTERESES (transacciones a partir de $1,000.00)
· CP-MSI-ROM-001 a CP-MSI-ROM-006

El plan de MSI lo ofrece el módulo de pago/adquirente, así que el resultado se valida A MANO.
La suite automatiza lo que sí puede: elegir una referencia por monto (≥ / < $1,000), verificar que P3 cobre
ese total, calcular la mensualidad esperada y dejar el módulo de pago listo para la tarjeta.
Al final el caso queda 'Manual' con la lista de lo que el tester debe confirmar (y la evidencia de lo automatizado).
En el reporte se distinguen con la etiqueta '6 MSI' y el filtro 'Tipo de pago'.
"""
import pytest

from config import settings
from core.marcadores import caso, validacion_manual

pytestmark = [pytest.mark.msi, pytest.mark.tarjeta]

MINIMO = settings.MSI_MONTO_MINIMO
PLAZO = settings.MSI_PLAZO


def _preparar(flujo, evidencia, ref, aplica_msi):
    """Valida el total cobrado contra el catálogo y la regla del monto mínimo. Regresa el total."""
    total = evidencia.monto
    assert total == ref["monto"], f"P3 cobra ${total:,.2f} y la referencia tiene un total de ${ref['monto']:,.2f}"
    if aplica_msi:
        assert total >= MINIMO, f"El total ${total:,.2f} no alcanza el mínimo de ${MINIMO:,.2f} para 6 MSI"
        evidencia.nota(f"6 MSI aplica: total ${total:,.2f} ≥ ${MINIMO:,.2f} · mensualidad esperada "
                       f"${total / PLAZO:,.2f} × {PLAZO}")
    else:
        assert total < MINIMO, f"El total ${total:,.2f} es ≥ ${MINIMO:,.2f}: no sirve para validar que NO se ofrezca MSI"
        evidencia.nota(f"6 MSI NO aplica: total ${total:,.2f} < ${MINIMO:,.2f}")
    return total


def _con_tester(flujo, evidencia, marcar_pagada, instruccion):
    """Con INTERACTIVO=true guía al tester con la tarjeta y registra el resultado (si se aprueba, la referencia
    queda 'pagada'). Sin INTERACTIVO solo deja el módulo de pago abierto como evidencia."""
    if not settings.INTERACTIVO:
        return None
    resultado = flujo.esperar_tarjeta_del_tester(instruccion)
    evidencia.nota(f"Resultado del cobro a 6 MSI: {resultado}")
    if resultado == "aprobado":
        marcar_pagada()
    return resultado


@caso("CP-MSI-ROM-001")
def test_CP_MSI_ROM_001_credito_participante(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(minimo=MINIMO)
    total = _preparar(flujo, evidencia, ref, aplica_msi=True)
    _con_tester(flujo, evidencia, marcar_pagada,
                "Inserte una tarjeta de CRÉDITO participante y elija el plan '6 meses sin intereses'.")
    validacion_manual(f"Confirmar que se ofreció y aplicó el plan de 6 MSI, que P5 muestra el plazo y que el cargo "
                      f"total es ${total:,.2f} sin intereses (mensualidad ${total / PLAZO:,.2f})")


@caso("CP-MSI-ROM-002")
def test_CP_MSI_ROM_002_menor_a_1000_sin_msi(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(maximo=MINIMO - 0.01)
    total = _preparar(flujo, evidencia, ref, aplica_msi=False)
    _con_tester(flujo, evidencia, marcar_pagada,
                "Inserte una tarjeta de CRÉDITO participante y revise si se ofrecen meses sin intereses.")
    validacion_manual(f"Confirmar que con ${total:,.2f} (< ${MINIMO:,.2f}) NO se ofrece 6 MSI y el pago es en una sola exhibición")


@caso("CP-MSI-ROM-003")
def test_CP_MSI_ROM_003_monto_limite(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(minimo=MINIMO, maximo=MINIMO)
    total = _preparar(flujo, evidencia, ref, aplica_msi=True)
    _con_tester(flujo, evidencia, marcar_pagada,
                "Inserte una tarjeta de CRÉDITO participante y revise si se ofrece el plan de 6 MSI.")
    validacion_manual(f"Confirmar que con exactamente ${total:,.2f} se ofrece el plan de 6 MSI (mínimo inclusivo)")


@caso("CP-MSI-ROM-004")
def test_CP_MSI_ROM_004_debito_sin_msi(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(minimo=MINIMO)
    total = _preparar(flujo, evidencia, ref, aplica_msi=True)
    _con_tester(flujo, evidencia, marcar_pagada, "Inserte una tarjeta de DÉBITO y revise las opciones de pago.")
    validacion_manual(f"Confirmar que con tarjeta de débito NO se ofrecen MSI aunque el total sea ${total:,.2f}")


@caso("CP-MSI-ROM-005")
def test_CP_MSI_ROM_005_comprobante_6_msi(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(minimo=MINIMO)
    total = _preparar(flujo, evidencia, ref, aplica_msi=True)
    resultado = _con_tester(flujo, evidencia, marcar_pagada,
                            "Inserte una tarjeta de CRÉDITO participante, elija '6 meses sin intereses' y complete el pago.")
    if resultado == "aprobado":
        evidencia.captura("P5 del pago a 6 MSI")
    validacion_manual(f"Revisar en P5 y en el ticket: 'Pago a 6 meses sin intereses', total ${total:,.2f}, "
                      f"mensualidad ${total / PLAZO:,.2f}, autorización y solo los últimos 4 dígitos")


@caso("CP-MSI-ROM-006")
def test_CP_MSI_ROM_006_credito_no_participante(flujo, evidencia, cobro, marcar_pagada):
    ref = cobro(minimo=MINIMO)
    total = _preparar(flujo, evidencia, ref, aplica_msi=True)
    _con_tester(flujo, evidencia, marcar_pagada,
                "Inserte una tarjeta de CRÉDITO de un banco NO participante y complete el pago.")
    validacion_manual(f"Confirmar que no se ofrecen MSI (o se informa que la tarjeta no participa) y que el pago de "
                      f"${total:,.2f} se completa en una sola exhibición sin errores")
