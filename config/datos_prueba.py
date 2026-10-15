"""Datos de prueba y textos exactos que muestra Rompefilas v1.6.36."""
from core import referencias

_DATOS = referencias.cargar()

# Referencia 'disponible' vigente (se resuelve en cada acceso: tras un pago aprobado ya es otra)
REF_VALIDA = referencias.ReferenciaActual()
CUENTA_PREDIAL = _DATOS["cuenta_predial"]
REF_CORTA = _DATOS["corta"]
REF_INEXISTENTE = _DATOS["inexistente"]
REF_INEXISTENTE_2 = _DATOS["inexistente_2"]

MSG_SIN_ADEUDOS = "No se encontraron adeudos"
MSG_APP_PAGO = "No se pudo comunicar con la aplicación de pago"

# Palabras que en pantalla deben llevar acento (CP-MP-ROM-003 / ortografía)
SIN_ACENTO = {
    "Credito": "Crédito", "credito": "crédito", "Debito": "Débito", "debito": "débito",
    "Metodo": "Método", "metodo": "método", "digitos": "dígitos", "Codigo": "Código", "codigo": "código",
    "Como desea": "Cómo desea", "Periodo": "Período", "Delegacion": "Delegación", "Rustico": "Rústico",
    "Rapido": "Rápido", "Facil": "Fácil", "camara": "cámara",
}
