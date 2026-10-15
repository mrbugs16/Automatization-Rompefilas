"""
Marcadores para vincular cada prueba con la matriz y clasificar su estado en el reporte.

    @caso("CP-ID-ROM-001")      -> toma nombre, módulo, escenario, etc. de la matriz
    @manual("motivo")           -> 'Manual' (requiere intervención física: tarjeta, recibo, papel...)
    @interactiva("motivo")      -> 'Manual' salvo con INTERACTIVO=true (la suite espera al tester)
    pendiente("motivo")         -> 'Pendiente' (falta un dato, depende de otro caso o no existe en la versión)
"""
import pytest

from config import settings

PREFIJO_PENDIENTE = "PENDIENTE:"
PREFIJO_MANUAL = "MANUAL:"


def caso(caso_id, **meta):
    return pytest.mark.caso(caso_id, **meta)


def manual(motivo):
    return pytest.mark.skip(reason=f"{PREFIJO_MANUAL} {motivo}")


def interactiva(motivo):
    """Caso que necesita una acción física del tester en la T6; corre solo con INTERACTIVO=true."""
    return pytest.mark.skipif(
        not settings.INTERACTIVO,
        reason=f"{PREFIJO_MANUAL} {motivo} (correr con INTERACTIVO=true para que la suite guíe la prueba)",
    )


def requiere_tester(motivo):
    """Igual que @interactiva pero dentro de la prueba: así primero se valida la precondición
    (ej. que el módulo de pago responda) y el caso queda 'Bloqueado' si ni siquiera se llega."""
    if not settings.INTERACTIVO:
        pytest.skip(f"{PREFIJO_MANUAL} {motivo} (correr con INTERACTIVO=true para que la suite guíe la prueba)")


def validacion_manual(motivo):
    """Para casos cuya preparación se automatiza pero el resultado lo valida el tester (ej. 6 MSI):
    se deja la evidencia de lo automatizado y el caso queda 'Manual' con lo que falta revisar."""
    pytest.skip(f"{PREFIJO_MANUAL} {motivo}")


def pendiente(motivo):
    """Para usar dentro de una prueba cuando falta un dato o una funcionalidad de la que depende."""
    pytest.skip(f"{PREFIJO_PENDIENTE} {motivo}")


def bloqueado(motivo):
    """La precondición del caso no se pudo alcanzar (se escribe 'Bloqueado' en la matriz)."""
    pytest.skip(f"{PREFIJO_PENDIENTE} Bloqueado: {motivo}")
