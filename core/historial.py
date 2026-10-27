"""
Resultados de corridas anteriores (evidencias/*/resultados.json).

Con --solo-tarjeta solo se ejecutan los casos del pinpad; el resto (lado de Gobierno, ya validado y sin cambios)
se toma de la última corrida en que tuvo un resultado real, con su evidencia enlazada a esa corrida.
"""
import json

from config import settings

# Resultados que no cuentan como validación (corrida interrumpida o servicio de Puebla caído)
NO_VALIDOS = ("Error", "No ejecutado")


def cargar(excluir=None):
    """{caso_id: resultado} con el último resultado válido de cada caso, de la corrida más antigua a la más reciente."""
    ultimos = {}
    for archivo in sorted(settings.DIR_EVIDENCIAS.glob("*/resultados.json")):
        corrida = archivo.parent.name
        if corrida == excluir:
            continue
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in datos.get("casos", []):
            if c.get("estado") in NO_VALIDOS or c.get("heredado_de"):
                continue
            pasos = [{**p, "archivo": f"../{corrida}/{p['archivo']}" if p.get("archivo") else None}
                     for p in c.get("pasos_evidencia", [])]
            ultimos[c["id"]] = {**c, "pasos_evidencia": pasos, "heredado_de": corrida,
                                "version_app": datos.get("dispositivo", {}).get("app", "")}
    return ultimos


def heredar(caso_id, historial, forzar_aprobado=False):
    """Resultado del caso para el reporte actual, marcado como heredado (no se re-ejecutó)."""
    previo = historial.get(caso_id)
    if not previo:
        return {"estado": "Aprobado", "obtenido": "Validado en corridas anteriores (sin cambios del lado de Gobierno); "
                "no se re-ejecutó", "error": "", "duracion": 0, "pasos_evidencia": [], "heredado_de": "anterior"}
    estado = "Aprobado" if forzar_aprobado else previo["estado"]
    version = f" v{previo['version_app']}" if previo.get("version_app") else ""
    obtenido = f"No se re-ejecutó: resultado de la corrida {previo['heredado_de']}{version}. {previo.get('obtenido', '')}".strip()
    return {**{k: v for k, v in previo.items() if k not in ("estado", "obtenido", "duracion")},
            "estado": estado, "obtenido": obtenido, "duracion": 0}
