"""Datos de prueba y textos exactos que muestra Rompefilas v1.6.36."""
import json

from config import settings


def _referencias():
    with open(settings.REFERENCIAS_JSON, encoding="utf-8") as f:
        return json.load(f)


REFERENCIAS = _referencias()
REF_VALIDA = REFERENCIAS["valida"]
CUENTA_PREDIAL = REFERENCIAS["cuenta_predial"]
REF_CORTA = REFERENCIAS["corta"]
REF_INEXISTENTE = REFERENCIAS["inexistente"]
REF_INEXISTENTE_2 = REFERENCIAS["inexistente_2"]
REF_PAGADAS = REFERENCIAS.get("pagadas", [])

MSG_SIN_ADEUDOS = "No se encontraron adeudos"
MSG_APP_PAGO = "No se pudo comunicar con la aplicación de pago"

# Palabras que en pantalla deben llevar acento (CP-MP-ROM-003 / ortografía)
SIN_ACENTO = {
    "Credito": "Crédito", "credito": "crédito", "Debito": "Débito", "debito": "débito",
    "Metodo": "Método", "metodo": "método", "digitos": "dígitos", "Codigo": "Código", "codigo": "código",
    "Como desea": "Cómo desea", "Periodo": "Período", "Delegacion": "Delegación", "Rustico": "Rústico",
    "Rapido": "Rápido", "Facil": "Fácil", "camara": "cámara",
}
