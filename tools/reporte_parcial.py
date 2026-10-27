"""
Arma reporte.html / resultados.json / matriz_resultados.xlsx de una corrida INTERRUMPIDA (sin pytest_sessionfinish),
a partir del log de pytest (-v -s) y de las capturas que sí se guardaron.

    python -m tools.reporte_parcial evidencias/<AAAAMMDD_HHMMSS> ruta/al/log.txt "nota para el reporte"
    python -m tools.reporte_parcial ... --sin-servicio   # las fallas 'sin respuesta' se reportan como Error de ambiente
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from core import adb
from core.matriz import cargar_matriz, escribir_resultados
from core.reporte_html import generar_reporte

ESTADOS = {"PASSED": "Aprobado", "FAILED": "Fallido", "ERROR": "Error", "SKIPPED": "Manual"}
PRUEBA = re.compile(r"tests/test_\w+\.py::(test_\w+)")
PASO = re.compile(r"(📸|📝) \[([\w-]+)\] (?:(\d{2}) )?(.*)")


def _caso_id(nombre_prueba):
    m = re.match(r"test_((?:CP_[A-Z]+_[A-Z]+|HP_ROM)_\d{3})", nombre_prueba)
    return m.group(1).replace("_", "-") if m else nombre_prueba


def _motivos_de_omision():
    """Motivo de los @manual / @interactiva (los skips dinámicos no quedan en el log -v)."""
    motivos = {}
    for archivo in Path("tests").glob("test_*.py"):
        texto = archivo.read_text(encoding="utf-8")
        for m in re.finditer(r'@caso\("([\w-]+)"\)\s*\n(?:@[^\n]*\n)*?@(?:manual|interactiva)\("([^"]+)"', texto):
            motivos[m.group(1)] = m.group(2)
    return motivos


def leer_log(ruta_log, dir_ejecucion):
    resultados, actual, ultimo = {}, None, None
    for linea in Path(ruta_log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = PRUEBA.search(linea)
        if m:
            actual = _caso_id(m.group(1))
            resultados.setdefault(actual, {"estado": "", "obtenido": "", "error": "", "duracion": 0, "pasos_evidencia": []})
        for p in PASO.finditer(linea):
            tipo, caso, numero, descripcion = p.groups()
            r = resultados.setdefault(caso, {"estado": "", "obtenido": "", "error": "", "duracion": 0, "pasos_evidencia": []})
            archivo = None
            if tipo == "📸" and numero:
                encontrados = sorted((dir_ejecucion / "capturas" / caso).glob(f"{numero}_*.png"))
                archivo = encontrados[0].relative_to(dir_ejecucion).as_posix() if encontrados else None
            estado_paso = "fallo" if descripcion.startswith("FALLO") else ("ok" if descripcion == "Resultado final" else "info")
            r["pasos_evidencia"].append({"numero": len(r["pasos_evidencia"]) + 1, "descripcion": descripcion.strip(),
                                         "estado": estado_paso, "archivo": archivo, "hora": "", "pantalla": ""})
            if descripcion.startswith("FALLO - "):
                r["obtenido"] = descripcion[len("FALLO - "):].strip()
            ultimo = caso
        estado = re.search(r"\b(PASSED|FAILED|ERROR|SKIPPED)\b", linea)
        caso_estado = actual or ultimo
        if estado and caso_estado and not resultados[caso_estado]["estado"]:
            resultados[caso_estado]["estado"] = ESTADOS[estado.group(1)]
    return resultados


def main():
    dir_ejecucion, ruta_log = Path(sys.argv[1]), sys.argv[2]
    nota = next((a for a in sys.argv[3:] if not a.startswith("--")), "")
    sin_servicio = "--sin-servicio" in sys.argv
    resultados = leer_log(ruta_log, dir_ejecucion)
    motivos = _motivos_de_omision()
    for caso, r in resultados.items():
        if not r["estado"]:
            r["estado"] = "Error"
            r["obtenido"] = r["obtenido"] or "La corrida se detuvo durante este caso"
        if r["estado"] == "Manual":
            fue_a_pinpad = any("modulo_pago" in p["descripcion"] for p in r["pasos_evidencia"])
            r["obtenido"] = motivos.get(caso) or ("Requiere tarjeta física en el pinpad (correr con INTERACTIVO=true)"
                                                  if fue_a_pinpad else "Omitido (el motivo no queda en el log)")
        if r["estado"] == "Aprobado":
            r["obtenido"] = r["obtenido"] or "Resultado conforme a lo esperado"
        if sin_servicio and r["estado"] in ("Fallido", "Error") and ("sin_respuesta" in r["obtenido"] or "no mostró adeudos" in r["obtenido"]):
            r["estado"] = "Error"
            r["obtenido"] = f"Servicio de consulta de Puebla sin respuesta: {r['obtenido']}"

    matriz = cargar_matriz()
    casos = [{"id": c, "caso": "Happy path: referencia válida → adeudos → tarjeta → recibo", "modulo": "General",
              "escenario": "Transacciones", **r} for c, r in resultados.items() if c not in matriz]
    for caso_id, fila in matriz.items():
        r = resultados.get(caso_id, {"estado": "No ejecutado", "obtenido": "", "error": "", "duracion": 0, "pasos_evidencia": []})
        casos.append({**fila, **r, "tipo_pago": "6 MSI" if caso_id.startswith("CP-MSI-") else ""})

    inicio = datetime.strptime(dir_ejecucion.name, "%Y%m%d_%H%M%S")
    fin = datetime.fromtimestamp(Path(ruta_log).stat().st_mtime)
    datos = {
        "ejecucion": dir_ejecucion.name, "inicio": inicio.strftime("%d/%m/%Y %H:%M:%S"),
        "fin": fin.strftime("%H:%M:%S"), "fin_completo": fin.strftime("%d/%m/%Y %H:%M:%S"),
        "duracion_total": round((fin - inicio).total_seconds()), "dispositivo": adb.info_dispositivo(),
        "interactivo": False, "nota": nota, "casos": casos,
    }
    (dir_ejecucion / "resultados.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    generar_reporte(datos, dir_ejecucion / "reporte.html")
    escribir_resultados({c["id"]: c for c in casos if c["estado"] != "No ejecutado"}, dir_ejecucion / "matriz_resultados.xlsx")
    resumen = {}
    for c in casos:
        resumen[c["estado"]] = resumen.get(c["estado"], 0) + 1
    print(f"📊 {dir_ejecucion / 'reporte.html'} · {resumen}")


if __name__ == "__main__":
    main()
