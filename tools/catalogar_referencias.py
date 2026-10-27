"""
Consulta en la T6 las referencias del catálogo y guarda contribuyente, número de adeudos y total.

    python -m tools.catalogar_referencias            # importa data/referencias.txt y consulta las 'sin_consultar'
    python -m tools.catalogar_referencias --todas    # vuelve a consultar todas menos las 'pagada'

Requiere Appium arriba (appium --relaxed-security) y la T6 conectada.
"""
import sys
import time
from datetime import datetime

from core import referencias
from core.driver_factory import crear_driver, reiniciar_app
from pages.kiosko_pages import FlujoKiosko


def _consultar(flujo, referencia):
    flujo.capturar_referencia(referencia, captura=False)
    resultado = flujo.consultar()
    if resultado != "p2":
        flujo.identificacion.borrar_todo()
        estado = {"sin_adeudos": "sin_adeudos", "ref_pagada": "pagada"}.get(resultado, "sin_consultar")
        return {"estado": estado, "notas": f"Consulta: {resultado}"}
    adeudos = flujo.adeudos.adeudos()
    datos = {
        "estado": "disponible",
        "contribuyente": flujo.adeudos.contribuyente(),
        "adeudos": len(adeudos),
        "monto": round(sum(a["monto"] for a in adeudos), 2),
        "conceptos": [f"{a['concepto']} {a['texto_monto']}" for a in adeudos],
    }
    flujo.adeudos.cambiar_referencia()
    assert flujo.identificacion.visible(), "'Cambiar referencia' no regresó a P1"
    flujo.identificacion.borrar_todo()
    return datos


def main():
    nuevas = referencias.importar_txt()
    print(f"📥 {nuevas} referencia(s) nuevas importadas de {referencias.settings.REFERENCIAS_TXT.name}")
    estados = ("sin_consultar", "disponible", "sin_adeudos") if "--todas" in sys.argv else ("sin_consultar",)
    pendientes = [r["referencia"] for r in referencias.catalogo() if r.get("estado") in estados]
    if not pendientes:
        print("✅ No hay referencias por consultar")
        return
    driver = crear_driver()
    try:
        flujo = FlujoKiosko(driver)
        for i, ref in enumerate(pendientes, 1):
            if i == 1 or i % 10 == 0 or flujo.pantalla() != "p1":  # reinicio periódico (evita el aviso de inactividad)
                reiniciar_app(driver)
                flujo.iniciar()
            inicio = time.time()
            try:
                datos = _consultar(flujo, ref)
            except Exception as e:  # noqa: BLE001 - se registra y se sigue con la siguiente
                datos = {"estado": "sin_consultar", "notas": f"Error: {e.__class__.__name__}"}
                reiniciar_app(driver)
                flujo.iniciar()
            datos["consultada"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            referencias.actualizar(ref, **datos)
            monto = f"${datos['monto']:,.2f}" if datos.get("monto") is not None else "-"
            print(f"   [{i:02d}/{len(pendientes)}] {ref} · {datos['estado']:<12} · {monto:>12} · "
                  f"{datos.get('contribuyente', '')} ({round(time.time() - inicio)} s)")
    finally:
        driver.quit()
    resumen = {e: sum(1 for r in referencias.catalogo() if r.get("estado") == e) for e in referencias.ESTADOS}
    print(f"📊 Catálogo: {resumen}")


if __name__ == "__main__":
    main()
