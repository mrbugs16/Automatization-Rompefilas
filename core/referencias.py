"""
Catálogo de referencias de pago de QA (data/referencias.json, alimentado desde data/referencias.txt).

Cada referencia tiene un estado:
    sin_consultar : se importó del .txt y aún no se consulta en la T6
    disponible    : tiene adeudos; se usa para los casos que necesitan una referencia NUEVA
    pagada        : ya se pagó en la T6; se usa para validar 'referencia repetida' (CP-IC-ROM-003)
    sin_adeudos   : la consulta no regresó adeudos

    python -m tools.catalogar_referencias      # consulta en la T6 las 'sin_consultar' y llena contribuyente/total
"""
import json
from datetime import datetime

from config import settings

ESTADOS = ("sin_consultar", "disponible", "pagada", "sin_adeudos")


def cargar():
    with open(settings.REFERENCIAS_JSON, encoding="utf-8") as f:
        return json.load(f)


def guardar(datos):
    with open(settings.REFERENCIAS_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


def catalogo():
    return cargar().get("catalogo", [])


def importar_txt(ruta=settings.REFERENCIAS_TXT):
    """Agrega al catálogo (como 'sin_consultar') las referencias del .txt que aún no estén. Regresa cuántas."""
    datos = cargar()
    existentes = {r["referencia"] for r in datos.setdefault("catalogo", [])}
    nuevas = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            ref = linea.strip()
            if len(ref) == 16 and ref.isdigit() and ref not in existentes:
                nuevas.append({"referencia": ref, "estado": "sin_consultar"})
                existentes.add(ref)
    datos["catalogo"].extend(nuevas)
    guardar(datos)
    return len(nuevas)


def disponible(minimo=None, maximo=None):
    """Primera referencia 'disponible' cuyo total esté en [minimo, maximo]. LookupError si no hay."""
    for r in catalogo():
        if r.get("estado") != "disponible" or r.get("monto") is None:
            continue
        if (minimo is None or r["monto"] >= minimo) and (maximo is None or r["monto"] <= maximo):
            return r
    rango = " y ".join(t for t in (f"≥ ${minimo:,.2f}" if minimo is not None else "",
                                   f"≤ ${maximo:,.2f}" if maximo is not None else "") if t)
    raise LookupError(f"No hay referencias 'disponible'{' con total ' + rango if rango else ''} en "
                      f"{settings.REFERENCIAS_JSON.name} (agrega más al .txt y corre tools.catalogar_referencias)")


def pagadas():
    return [r for r in catalogo() if r.get("estado") == "pagada"]


def actualizar(referencia, **campos):
    datos = cargar()
    for r in datos.get("catalogo", []):
        if r["referencia"] == referencia:
            r.update(campos)
            break
    else:
        datos.setdefault("catalogo", []).append({"referencia": referencia, **campos})
    guardar(datos)


def marcar_pagada(referencia, caso=""):
    """Tras un pago aprobado: la referencia deja de ser 'nueva' y pasa a 'pagada' (referencia repetida)."""
    actualizar(referencia, estado="pagada", pagada_en=caso, fecha_pago=datetime.now().strftime("%d/%m/%Y %H:%M"))
    print(f"   🔁 Referencia {referencia} marcada como pagada; quedan "
          f"{sum(1 for r in catalogo() if r.get('estado') == 'disponible')} disponible(s)")


class ReferenciaActual(dict):
    """Se comporta como el dict de la referencia 'disponible' vigente, pero se resuelve en cada acceso:
    si un caso paga la referencia, el siguiente caso ya usa otra (REF_VALIDA['referencia'])."""

    def _actual(self):
        r = disponible()
        return {**r, "total": f"${r['monto']:,.2f}"}

    def __getitem__(self, clave):
        return self._actual()[clave]

    def get(self, clave, default=None):
        try:
            return self._actual().get(clave, default)
        except LookupError:
            return default
