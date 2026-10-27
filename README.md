# [PUEBLA] Rompefilas T6 · Automatización QA

Pruebas E2E del **Kiosko de Pagos Rompefilas** (`com.exos.kiosko.rompefilas`) en la terminal **T6** (Android 13)
con **Python + Appium (UiAutomator2) + pytest**.
Cubre los 72 casos de `data/RompeFilas.xlsx` (66 + 6 de **6 MSI**) más el happy path, y genera evidencia en cada
ejecución (capturas + reporte HTML con filtros, referencia y monto por caso + copia de la matriz con resultados).

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
  datos_prueba.py    Datos de prueba y textos esperados (REF_VALIDA = referencia 'disponible' vigente)
core/
  driver_factory.py  Sesión de Appium + reinicio de la app entre casos
  adb.py             Red, batería simulada, foco de ventana, reinicio, logcat, screencap
  evidencia.py       Capturas por caso (y XML de la pantalla cuando falla)
  interaccion.py     Pausas guiadas para el tester (INTERACTIVO=true)
  marcadores.py      @caso, @manual, @interactiva, pendiente(), bloqueado(), requiere_tester()
  matriz.py          Lee la matriz y escribe la copia con resultados
  xlsx.py            Guarda el Excel conservando las gráficas del Dashboard
  referencias.py     Catálogo de referencias (disponible / pagada / sin_adeudos)
  reporte_html.py    Reporte HTML con filtros
pages/
  base_page.py       Esperas, toques, lectura de textos/recuadros desde el XML
  kiosko_pages.py    Inicio, P1…P5, modal de inactividad y FlujoKiosko
data/
  RompeFilas.xlsx    Matriz de pruebas (filas 77-82: casos de 6 MSI)
  referencias.txt    Referencias de QA, una por línea (fuente)
  referencias.json   Catálogo: contribuyente, adeudos, total y estado de cada referencia
tools/
  catalogar_referencias.py  Consulta en la T6 las referencias nuevas y llena el catálogo
tests/               Un archivo por módulo de la matriz (test_11_msi.py: 6 MSI)
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
python -m pytest -m msi --abrir-reporte                  # solo los casos de 6 MSI
python -m pytest -m "not msi"                            # todo menos 6 MSI
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
| `TIMEOUT_INTERACCION` | segundos que se espera al tester (recibo, papel) | `120` |
| `TIMEOUT_TARJETA` | segundos para insertar la tarjeta y capturar el NIP (mínimo 120) | `150` |
| `MSI_MONTO_MINIMO` | monto desde el que aplica 6 MSI | `1000` |
| `TIEMPO_MAX_ATENCION` | objetivo de CP-ES-ROM-002 | `90` |
| `MIN_TOQUE_DP` | área táctil mínima (CP-HW-ROM-006) | `48` |

---

## Referencias de prueba

`data/referencias.txt` tiene las referencias de QA (una por línea). Para agregar nuevas, se pegan ahí y se corre:

```bash
python -m tools.catalogar_referencias
```

La herramienta consulta cada referencia nueva en la T6 y guarda en `data/referencias.json` el contribuyente,
los adeudos y el total. Estados:

| Estado | Uso |
|---|---|
| `disponible` | Referencia **nueva**: la toman los casos que consultan o cobran (siempre la primera disponible) |
| `pagada` | Se marca sola cuando un pago se aprueba; la usa CP-IC-ROM-003 (**referencia repetida**) |
| `sin_adeudos` | La consulta no regresó adeudos |
| `sin_consultar` | Importada del .txt, falta catalogarla |

Los casos de 6 MSI eligen la referencia por monto (≥ $1,000 o < $1,000). El reporte HTML muestra en cada caso
la referencia, el contribuyente y el monto cobrado, y la matriz de resultados los agrega en *Observaciones*.

## Módulo de pago: pinpad real de Memphis (27/10/2026)

El cobro ya usa el pinpad real (otra app; la transición con Rompefilas dura de 0.5 a 1.5 s). Pantallas:

| Pinpad | Qué hace la suite |
|---|---|
| *Acerca, inserta o desliza tu tarjeta* (Resumen · Monto) | Valida el monto y da **3 min** al tester para la tarjeta |
| *Leyendo tarjeta…* | Espera |
| *¿Cuántas mensualidades?* (solo **≥ $1,000**) | **Elige el plan sola**: *Sin mensualidades* en los casos normales, *6 meses sin intereses* en los de 6 MSI |
| *Ingresa tu PIN en el lector* (Resumen · Monto · Mensualidades) | Da **3 min** al tester para el NIP |
| *Transacción aprobada* / *Transacción declinada* / *Tiempo de espera agotado* / *Ingreso de PIN cancelado* | Registra el resultado y espera a Rompefilas |

En Rompefilas: *Pago exitoso* → comprobante *¡Pago exitoso!* (se imprime solo), o *No se pudo procesar el pago* con el
detalle (*No se pudo leer la tarjeta correctamente*, *Error al capturar el nip*…). Cada fase queda en la evidencia.

Los casos con tarjeta física corren con `INTERACTIVO=true` (uno por uno, por ejemplo):

```powershell
$env:INTERACTIVO = "true"; python -m pytest -k HP_ROM_001 --abrir-reporte
```

**Solo los casos del pinpad** (marca `pinpad`: happy path, CP-TJ, CP-SG-001/002, CP-MSI, MP-001, CX-001, IC-002,
CC-004). Los demás casos no se re-ejecutan: el reporte toma su último resultado válido de `evidencias/*` (sin las
corridas con el servicio caído) con la etiqueta *Corrida AAAAMMDD_HHMMSS* y la evidencia de esa corrida. Con
`--heredados-aprobados` todos los heredados salen como *Aprobado*.

```powershell
$env:INTERACTIVO = "true"; python -m pytest --solo-tarjeta --abrir-reporte
```

Sin tester corren CP-MP-ROM-001 (monto e instrucción en el pinpad), CP-TJ-ROM-003 (se deja expirar el pinpad) y
CP-TJ-ROM-012 (la suite toca *Cancelar*). **Cada pago aprobado usa una referencia** (se marca `pagada` sola).

Si el módulo vuelve a ser el simulador (*Approved* / *Declined*), la suite lo detecta y toca el botón sola.

> ⚠ Las referencias pueden traer **condonaciones con monto negativo** (ej. `-$494.28`): la suite las resta del total.

## Regla de negocio: pago de adeudos en conjunto

Los adeudos de una referencia **no se pagan de forma individual**: en todos los casos se pagan todos juntos.
CP-AD-ROM-001 a 003 validan que no haya selección individual y que P3 cobre la suma de todos los adeudos.

## Cobro con tarjeta física (INTERACTIVO=true)

La terminal muestra la indicación con la referencia y el monto, suena la campana y recuerda el tiempo restante
cada 10 s: **3 min para la tarjeta** (`TIMEOUT_TARJETA`) y **3 min para el NIP** (`TIMEOUT_NIP`), nunca menos.

## 6 meses sin intereses (CP-MSI-ROM-001 a 006)

Aplica a transacciones **desde $1,000.00**. **Integrado el 27/10/2026**: tras leer la tarjeta aparece
*¿Cuántas mensualidades?* y el NIP muestra *Mensualidades 6*. La suite elige la referencia por monto (≥ / < $1,000),
verifica el total en P3 y en el pinpad, elige el plan del caso y valida si se ofreció 6 MSI, las mensualidades del NIP
y el comprobante. El tester presenta la tarjeta (crédito participante, débito o no participante según el caso) y el
NIP; el ticket impreso se revisa a mano. En el reporte llevan la etiqueta **6 MSI** (filtro *Tipo de pago*).

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
4. Si se acaban las referencias `disponible`, agregar más a `data/referencias.txt` y correr `python -m tools.catalogar_referencias`.
