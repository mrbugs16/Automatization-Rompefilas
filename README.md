# [PUEBLA] Rompefilas T6 · Automatización QA

Pruebas E2E del **Kiosko de Pagos Rompefilas** (`com.exos.kiosko.rompefilas`) en la terminal **T6** (Android 13)
con **Python + Appium (UiAutomator2) + pytest**.
Cubre los 66 casos de `data/RompeFilas.xlsx` más el happy path, y genera evidencia en cada ejecución
(capturas + reporte HTML con filtros + copia de la matriz con resultados).

Bases reutilizadas:

| De | Qué se tomó |
|---|---|
| `automated_tests/Automatizacion/T6/v2` | Conexión a la T6 (`CAPABILITIES`, `start_driver`) y control por ADB (`utils_system.py`) |
| `Automatization-Paid-Button` | Interfaz de evidencias: `Evidencia`, reporte HTML, marcadores, hooks de pytest y la matriz con resultados |

---

## Flujo de la app (v1.6.36)

```
Inicio ──► P1 Identificar ──► P2 Adeudos ──► P3 Método ──► P4 Pago (módulo de la T6) ──► P5 Recibo
           · 16 dígitos          · lista sin       · Tarjeta       · hoy: "No se pudo comunicar
           · cuenta PU/PR          selección         (único)         con la aplicación de pago"
           · cámara (Topwise)
```

La app es un **WebView**: UiAutomator2 expone el DOM como nodos nativos con el texto en `@text`,
así que todo se localiza por texto (`config/locators.py`).

> **Importante:** Chromium solo arma el árbol de accesibilidad completo si la app se abre *después* de que
> UiAutomator2 está conectado. Por eso la suite **reinicia la app antes de cada caso** (`core/driver_factory.py`).
> Si se inspecciona con Appium Inspector y faltan botones, cerrar y abrir la app con la sesión ya iniciada.

---

## Estructura

```
config/
  settings.py        Appium/T6, tiempos de negocio, modo interactivo (todo sobrescribible por variables de entorno)
  locators.py        Localizadores por pantalla (los 'TODO confirmar' son pantallas que aún no existen)
  datos_prueba.py    Referencias de prueba y textos esperados
core/
  driver_factory.py  Sesión de Appium + reinicio de la app entre casos
  adb.py             Red, batería simulada, foco de ventana, reinicio, logcat, screencap
  evidencia.py       Capturas por caso (y XML de la pantalla cuando falla)
  interaccion.py     Pausas guiadas para el tester (INTERACTIVO=true)
  marcadores.py      @caso, @manual, @interactiva, pendiente(), bloqueado(), requiere_tester()
  matriz.py          Lee la matriz y escribe la copia con resultados
  reporte_html.py    Reporte HTML con filtros
pages/
  base_page.py       Esperas, toques, lectura de textos/recuadros desde el XML
  kiosko_pages.py    Inicio, P1…P5, modal de inactividad y FlujoKiosko
data/
  RompeFilas.xlsx    Matriz de pruebas
  referencias.json   Referencias de QA (válida, inexistentes, pagadas)
tests/               Un archivo por módulo de la matriz
evidencias/<fecha_hora>/  reporte.html · resultados.json · matriz_resultados.xlsx · capturas/<CP-ID>/*.png
```

---

## Instalación (una sola vez)

```bash
pip install -r requirements.txt
npm install -g appium
appium driver install uiautomator2
```

T6 conectada por USB con depuración USB activa (`adb devices` debe listarla).

## Ejecución

1. Levantar Appium en otra terminal: `appium --relaxed-security`
2. Correr las pruebas:

```bash
python -m pytest --abrir-reporte                         # todo, desatendido
python -m pytest -m "not lento" --abrir-reporte          # sin las esperas de inactividad/timeout (~1 min c/u)
python -m pytest -k HP_ROM_001 --abrir-reporte           # happy path
python -m pytest tests/test_01_identificacion.py         # un módulo
python -m pytest -k CP_ID_ROM_004                        # un caso
python -m pytest -m "not red"                            # sin cortar Wi-Fi/datos de la T6
python -m pytest --incluir-reinicio -k CP_IN_ROM_001     # arranque automático (reinicia la T6)
```

En PowerShell, el modo interactivo (la suite lleva la app al punto y espera a que el tester presente la
tarjeta, el recibo o retire el papel):

```powershell
$env:INTERACTIVO = "true"; python -m pytest --abrir-reporte
```

### Variables de entorno principales

| Variable | Valores | Default |
|---|---|---|
| `INTERACTIVO` | `true` / `false` | `false` (los casos con tarjeta/recibo/papel salen *Manual*) |
| `T6_UDID` | serial de `adb devices` | primer dispositivo |
| `APPIUM_URL` | URL del server | `http://127.0.0.1:4723` |
| `TIMEOUT_INACTIVIDAD` | segundos máx. para ver '¿Sigue ahí?' | `180` |
| `TIMEOUT_TARJETA_SIN_ACCION` | segundos máx. para el timeout de lectura (CP-TJ-ROM-003) | `90` |
| `TIMEOUT_INTERACCION` | segundos que se espera al tester | `120` |
| `TIEMPO_MAX_ATENCION` | objetivo de CP-ES-ROM-002 | `90` |
| `MIN_TOQUE_DP` | área táctil mínima (CP-HW-ROM-006) | `48` |

---

## Estados del reporte → columna *Estatus* de la matriz

| Reporte | Matriz | Significado |
|---|---|---|
| Aprobado | Pasó | El resultado coincide con lo esperado |
| Fallido | Falló | Falló una validación: es un defecto a reportar |
| Error | Bloqueado | Falló la preparación (Appium, T6, datos), no la validación |
| Pendiente | Bloqueado | Depende de otro caso (ej. el módulo de pago), falta un dato o la función no existe en la versión |
| Manual | Sin Ejecutar | Requiere intervención física; con `INTERACTIVO=true` la suite la guía |

En `matriz_resultados.xlsx` también se llenan *Estatus Automatización* y *Tipo de Ejecución* (`Automatizada`),
*Fecha de Ejecución*, *Evidencia* (vínculo a `reporte.html#CP-ID`) y *Observaciones* (resultado obtenido).

---

## Hallazgos en v1.6.36 (corrida desatendida del 13/10/2026)

10 aprobados · 6 fallidos · 32 bloqueados/pendientes · 19 manuales.

| Caso | Hallazgo |
|---|---|
| HP-ROM-001 / CP-MP-ROM-001 | Al elegir *Tarjeta*: "No se pudo comunicar con la aplicación de pago". Bloquea los 26 casos de tarjeta, recibo e impresión |
| CP-AD-ROM-001 | P2 no permite seleccionar adeudos individuales: siempre se cobra el total |
| CP-CX-ROM-002 | Sin red, la consulta muestra "No se encontraron adeudos" en lugar de un mensaje de conexión |
| CP-HW-ROM-001 | La app no avisa la batería baja (solo aparece el diálogo de Android, que además muestra barra de estado y navegación sobre el kiosko) |
| CP-HW-ROM-006 | 11 botones con área táctil < 48 dp (ej. 'Pagar ahora' 37 dp de alto, 'Probar impresora' 46×37 dp) |

Observaciones (no fallan el caso): no hay validación de longitud (se consulta con 10 dígitos); el aviso de
inactividad sale a los ~60 s y regresa al inicio a los ~80 s (la matriz habla de > 2 min); el error de pago
sugiere "pagar en efectivo", que la T6 no ofrece; no existen acceso de operador, corte de caja ni historial.

---

## Cuando llegue una versión nueva

Las pantallas que aún no existen tienen localizadores marcados `TODO confirmar` en `config/locators.py`
(módulo de pago, recibo P5, avisos de papel/batería/conexión, acceso de operador, corte de caja).
Los casos que dependen de ellas **se activan solos** cuando la app las muestre:

1. Correr `python -m pytest -k HP_ROM_001` y revisar el XML de la pantalla en `capturas/HP-ROM-001/*.xml`.
2. Ajustar los localizadores `TODO confirmar` con los textos reales.
3. Correr con `INTERACTIVO=true` los casos de tarjeta e impresión.
4. Tras un pago aprobado, mover la referencia a `pagadas` en `data/referencias.json` y registrar una nueva `valida`.
