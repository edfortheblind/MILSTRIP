# Diagnóstico técnico de `trav3pl-sqldb-eastus-prod`

**Fecha del análisis:** 11 de agosto de 2026  
**Servidor:** `trav3pl-sql-eastus` (Azure SQL Database)  
**Base:** `trav3pl-sqldb-eastus-prod`  
**Alcance:** análisis estrictamente de solo lectura  

## 1. Resumen ejecutivo

La base soporta un sistema operacional de logística 3PL orientado a recepción, inventario, preparación y expedición de órdenes, integración con DLA/SCALE, mensajes EDI y seguimiento/facturación de transportistas. La arquitectura es principalmente procedimental: los datos entran en tablas de descarga o *staging*, pasan por rutinas numeradas de limpieza/enriquecimiento y terminan en tablas maestras operacionales.

La plataforma está sana en sus opciones básicas: Azure SQL Standard S4, compatibilidad 160, `AUTO_CREATE_STATISTICS` y `AUTO_UPDATE_STATISTICS` habilitados, Query Store activo, `READ_COMMITTED_SNAPSHOT` y Snapshot Isolation activos, `AUTO_SHRINK` deshabilitado y verificación de páginas con checksum.

Los riesgos principales no son de capacidad inmediata, sino de diseño físico y costo de procesamiento:

1. **Estadísticas extremadamente desfasadas en tablas críticas.** Varias estadísticas de `download_ship940` muestran miles de millones de modificaciones acumuladas respecto de unos 2.6 millones de filas actuales, con muestreo de solo 2.34 %. Esto puede producir estimaciones erróneas, planes inestables y paralelismo excesivo.
2. **Procesamiento reiterativo sobre tablas anchas.** Query Store muestra cientos de ejecuciones de transformaciones que recorren cientos de millones de páginas lógicas acumuladas. El patrón dominante son múltiples `UPDATE` secuenciales sobre `download_ship940` y `ShipMaster`.
3. **Paralelismo como espera dominante.** `CXPACKET`, `CXCONSUMER` y `CXSYNC_PORT` encabezan las esperas acumuladas. No constituyen por sí solos un error, pero junto con el CPU y las lecturas de Query Store apuntan a planes paralelos costosos sobre grandes conjuntos.
4. **Modelo relacional casi sin integridad declarativa.** Existen 77 tablas, pero solo una clave foránea y ningún `CHECK`. Treinta y dos tablas son heaps. Buena parte de la integridad parece depender del código de procedimientos.
5. **Oportunidades claras de índices, pero no deben aplicarse mecánicamente.** Las DMVs concentran recomendaciones en `download_ship940`, `ShipMaster` y `ShipOrders`. Algunas sugerencias se solapan y otras proponen índices demasiado anchos; deben consolidarse mediante pruebas de planes y carga de escritura.
6. **Gobierno de datos insuficiente.** No hay clasificaciones de sensibilidad registradas, pese a columnas de nombres, direcciones, teléfonos, correos, órdenes y datos de clientes/destinatarios.

No se realizó ningún cambio en la base.

## 2. Plataforma y configuración

| Propiedad | Resultado | Evaluación |
|---|---:|---|
| Edición / objetivo | Standard S4 | Nivel aprovisionado clásico; conviene contrastar CPU/IO real con Azure Monitor |
| Tamaño máximo | 250 GB | Margen amplio frente a la asignación observada |
| Archivos asignados | 29,016 MB | Aproximadamente 28.34 GiB asignados |
| Datos asignados | 22,544 MB | Aproximadamente 22.02 GiB |
| Log asignado | 6,472 MB | Aproximadamente 6.32 GiB; es asignación, no uso instantáneo |
| Compatibilidad | 160 | Motor lógico equivalente a SQL Server 2022 |
| Collation | `Latin1_General_CI_AS` | No distingue mayúsculas/minúsculas; sensible a acentos |
| Recovery model | FULL | Normal en Azure SQL Database |
| Query Store | Activo | Muy útil para línea base, regresiones y pruebas |
| RCSI | Activo | Reduce bloqueos lector/escritor |
| Snapshot Isolation | ON | Permite transacciones snapshot explícitas |
| Auto-create stats | ON | Correcto |
| Auto-update stats | ON | Correcto, aunque no está manteniendo adecuadamente algunos objetos de alta rotación |
| Auto-update async | OFF | Las compilaciones pueden esperar una actualización síncrona |
| Auto-shrink / auto-close | OFF / OFF | Correcto |
| Page verify | CHECKSUM | Correcto |

Aunque la base reporta `READ_WRITE`, todas las conexiones y consultas de este diagnóstico utilizaron `ApplicationIntent=ReadOnly` y sentencias `SELECT`.

## 3. Modelo funcional inferido

El flujo principal de embarques parece ser:

```text
EDI / descarga 940
    -> staging_upload_ship / download_ship940
    -> sp_ship_preprocess_* (deduplicar, inicializar, limpiar, clasificar)
    -> ShipMaster
    -> sp_ship_postprocess_* (peso, región, loads, orders, contents, shipment)
    -> ShipLoads / ShipOrders / ShipContainerContents / ShipShipments
    -> SCALE y reportes operacionales
```

El flujo de recepción parece ser:

```text
EDI 856 y/o 527
    -> staging_download_rcv856 / download_rcv856 / download_rcv527
    -> preReceiptMaster
    -> ReceiptMasterHeader + ReceiptMasterDetail
    -> postproceso de recepción / integración SCALE
```

Otros subsistemas observados:

- **Inventario:** `InventoryMaster`, `IRMMaster`, `ItemMaster`, `LOCATION_INVENTORY`, `LOCATION_INVENTORY_daily` y generación 846.
- **Ajustes:** `InventoryAdjust`, `upload_adj947` y procedimientos `sp_adj_postprocess_*`.
- **Transportistas:** `invoice_ups`, `invoice_fedex`, tablas de tracking y excepciones UPS/FedEx.
- **Configuración:** tablas `cfg_*` para DODAAC, países, estados, ZIP, calendarios y valores técnicos.
- **Reportería:** procedimientos `sp_rpt_*` para MRO, inventario, historial NSN, dead stock y excepciones.

La numeración de procedimientos (`015`, `020`, `030`, etc.) expresa un pipeline operacional. Es comprensible y útil para operación, pero crea dependencia implícita del orden de ejecución. No se observaron metadatos de orquestación durante este análisis; debe documentarse quién invoca cada etapa, con qué frecuencia y qué control de reintentos/idempotencia existe.

## 4. Inventario estructural

| Tipo de objeto | Cantidad |
|---|---:|
| Tablas de usuario | 77 |
| Vistas | 0 |
| Procedimientos almacenados | 38 |
| Funciones | 3 |
| Triggers de tabla | 0 |
| Claves foráneas | 1 |
| Restricciones CHECK | 0 |
| Tablas heap | 32 |
| Tablas temporales del sistema | 0 |
| Índices persistentes | 98 |
| Índices deshabilitados | 0 |
| Índices hipotéticos | 0 |
| Índices filtrados | 0 |

La única relación declarada encontrada es `shipLoadCharges -> ShipLoads`, con cascada en actualización y eliminación; está habilitada y confiable. Esto es una señal fuerte de que el resto de las relaciones se mantienen por convenciones de nombres y procedimientos, no por el motor.

### Tablas de mayor tamaño

| Tabla | Filas estimadas | Reservado MB | Usado MB | Columnas | PK | Heap |
|---|---:|---:|---:|---:|:---:|:---:|
| `ShipMaster` | 2,342,200 | 6,063.10 | 5,907.25 | 126 | Sí | No |
| `download_ship940` | 2,559,081 | 4,155.11 | 4,151.05 | 102 | Sí | No |
| `ShipOrders` | 1,302,868 | 3,357.57 | 3,285.95 | 95 | Sí | No |
| `ShipContainerContents` | 1,785,079 | 2,394.31 | 2,283.84 | 48 | Sí | No |
| `IRMMaster` | 7,023,930 | 2,334.46 | 2,333.30 | 30 | Sí | No |
| `InventoryMaster` | 7,051,406 | 1,866.27 | 1,782.11 | 7 | Sí | No |
| `invoice_ups` | 866,652 | 470.63 | 470.53 | 34 | Sí | No |
| `invoice_fedex` | 383,927 | 420.23 | 420.03 | 173 | No | Sí |
| `cfg_dodaac` | 343,344 | 182.38 | 176.76 | 16 | Sí | No |
| `ReceiptMasterDetail` | 127,037 | 155.61 | 69.81 | 23 | Sí | No |
| `upload_rcv527` | 128,009 | 146.99 | 133.79 | 38 | Sí | No |
| `download_rcv527` | 422,547 | 144.48 | 143.01 | 48 | Sí | No |

Las seis tablas principales ocupan cerca de 20.2 GB reservados. El volumen está concentrado, por lo que optimizar los pipelines de embarque e inventario tendrá un efecto mucho mayor que ajustes dispersos.

## 5. Rendimiento observado

### 5.1 Esperas acumuladas

| Espera | Segundos | Interpretación |
|---|---:|---|
| `CXPACKET` | 29,699.6 | Coordinación de paralelismo; revisar consultas, cardinalidad y MAXDOP antes de tocar configuración |
| `CXCONSUMER` | 18,300.2 | Consumo de ramas paralelas; suele acompañar a CXPACKET |
| `CXSYNC_PORT` | 11,809.3 | Sincronización de operadores paralelos |
| `ASYNC_NETWORK_IO` | 2,836.3 | Clientes consumiendo resultados lentamente o result sets excesivos |
| `PAGEIOLATCH_SH` | 853.9 | Lectura física o presión de caché/IO |
| `LOG_RATE_GOVERNOR` | 749.3 | Momentos limitados por tasa de log del nivel de servicio |
| `WAIT_ON_SYNC_STATISTICS_REFRESH` | 316.5 | Compilaciones esperando estadísticas síncronas |
| `SOS_SCHEDULER_YIELD` | 264.1 | Presión de CPU acumulada |
| `BPSORT` | 246.5 | Trabajo de ordenamiento/batch processing |
| `WRITELOG` | 102.0 | Latencia o caudal de escritura al log |

Estas métricas son acumulativas y pueden reiniciarse por failover, mantenimiento o cambios de servicio. Sin la hora exacta del último reinicio, sirven como distribución relativa, no como SLA temporal.

### 5.2 Query Store: patrón dominante de costo

En los últimos siete días, los mayores consumidores están ligados al pipeline 940. Se observaron, entre otros:

- Un `UPDATE` que calcula `ranker` y `DICType`: 574 ejecuciones, aproximadamente 1,114 segundos de duración agregada, 809 segundos de CPU agregada, 282.5 millones de lecturas lógicas y un máximo individual cercano a 122 segundos.
- Varias normalizaciones de país/estado/direcciones en `download_ship940`: cada una con alrededor de 272–276 millones de lecturas lógicas acumuladas en 574 ejecuciones.
- `UPDATE ShipMaster SET SCALEInterfaceAction='queued' WHERE ... IS NULL`: cerca de 398.5 millones de lecturas lógicas acumuladas.
- Una extracción operacional desde `ShipMaster` ejecutada 730 veces: alrededor de 506.7 millones de lecturas lógicas y 992 segundos de CPU agregada.
- La creación de `ReceiptMasterHeader`: 551 ejecuciones y unos 24.2 millones de lecturas lógicas.

El hallazgo importante no es una consulta aislada: el pipeline realiza muchas pasadas completas o casi completas sobre las mismas tablas anchas. Es probable que una estrategia de procesamiento por lote/estado y un índice pequeño sobre la cola activa produzcan más beneficio que decenas de índices generales.

### 5.3 Índices y uso

Los índices más grandes incluyen:

- PK clustered de `ShipMaster`: 5,364 MB.
- PK clustered de `download_ship940`: 3,712 MB.
- PK clustered de `ShipOrders`: 2,812 MB.
- PK clustered de `ShipContainerContents`: 1,488 MB.
- PK clustered de `IRMMaster`: 1,300 MB.
- PK clustered de `InventoryMaster`: 1,205 MB.
- Índice único compuesto de `IRMMaster`: 507 MB.

Algunos índices grandes registraron poco o ningún uso de lectura en la ventana acumulada de la DMV (`IX_InventoryMaster_ITEM`, `IX_IRMMaster_NSN`, PK de `invoice_ups`). Esto **no autoriza eliminarlos**: los contadores se reinician, pueden soportar cargas periódicas y los índices únicos pueden imponer integridad.

Las sugerencias de índices faltantes se concentran en:

- `download_ship940`: combinaciones de `ranker`, `DICType`, `LastProcessStamp`, país/estado/ZIP y `MROID`.
- `ShipMaster`: `SCALEInterfaceAction`, `calendarDate3PL` y `QtyRemainder`.
- `ShipOrders`: `TimeStampUpload`, `dayActivity`, `TCN` y `VendorExceptionOK`.

Varias sugerencias tienen `avg_user_impact` estimado entre 96 % y 100 %, pero otras incluyen decenas de columnas. No se recomienda materializarlas literalmente. La mejor hipótesis inicial es un índice estrecho orientado a la cola activa, posiblemente filtrado si la semántica y distribución lo permiten.

## 6. Estadísticas y cardinalidad

Este es el hallazgo técnico de mayor prioridad.

Varias estadísticas automáticas de `download_ship940` tenían:

- fecha de actualización aproximada de septiembre de 2025;
- 2,229,105 filas al momento de actualización;
- solo 52,135 filas muestreadas (2.34 %);
- contador de modificaciones superior a 5,039 millones.

También aparecen contadores anormalmente altos en `staging_track_fedex`, `ItemMaster` y `ShipSCALEStatus`. El contador puede crecer muy por encima de la cardinalidad cuando las mismas filas reciben actualizaciones repetidas, exactamente el patrón observado en los procedimientos.

Consecuencias probables:

- estimaciones de cardinalidad deficientes;
- elección excesiva de paralelismo;
- joins y memoria concedida de forma inadecuada;
- recompilaciones o esperas por actualización síncrona;
- variación significativa entre ejecuciones.

Antes de cambiar índices o nivel S4, debe diseñarse una política de estadísticas para las tablas de alta rotación. Esto requiere una ventana controlada y pruebas, porque `FULLSCAN` sobre tablas de varios GB consume recursos.

## 7. Integridad, calidad y mantenibilidad

### Fortalezas

- Las tablas operacionales principales tienen PK clustered.
- La única FK está habilitada y confiable.
- No hay índices deshabilitados ni hipotéticos.
- Las opciones de concurrencia y protección de páginas son razonables.
- Los procedimientos tienen nombres y fases que comunican el orden del pipeline.

### Riesgos

- Solo una FK para 77 tablas y cero restricciones CHECK.
- 32 heaps; algunos son staging legítimo, pero `invoice_fedex` es un heap de 420 MB con 173 columnas y sin PK.
- Tablas extremadamente anchas y muy nullable: `ShipMaster` tiene 117 columnas nullable de 126; `download_ship940`, 99 de 102; `invoice_fedex`, 173 de 173.
- No existen vistas que encapsulen el modelo de lectura o presenten contratos estables.
- No hay triggers; esto simplifica diagnóstico, pero toda regla depende de procedimientos/aplicaciones.
- Nombres de tablas como `zzz_*`, `special_*`, `force_*`, copias con fecha y tablas temporales persistentes sugieren deuda operacional y artefactos ad hoc.
- Reglas comerciales complejas están codificadas en grandes bloques `CASE`, valores literales, DODAAC, países, teléfonos y fechas. Esto eleva el riesgo de divergencia y dificulta auditoría.

No se realizaron escaneos exhaustivos de nulos, duplicados u huérfanos porque serían costosos sobre producción y el esquema carece de relaciones declaradas suficientes para definirlos con seguridad. Deben ejecutarse por dominio, con reglas de negocio acordadas.

## 8. Seguridad y gobierno

La identidad usada para diagnosticar apareció como `TabAdmin` y usuario `dbo`, con `VIEW DATABASE STATE` y `VIEW SERVER STATE`. Para tareas diagnósticas recurrentes conviene usar una identidad dedicada de solo lectura y permisos mínimos. `ApplicationIntent=ReadOnly` expresa intención, pero no reemplaza una denegación real de escritura.

La base no contiene clasificaciones de sensibilidad registradas (`sys.sensitivity_classifications = 0`). Sin embargo, se observaron columnas que razonablemente contienen:

- nombres de destinatarios y clientes;
- direcciones postales nacionales e internacionales;
- correos y teléfonos;
- números de requisición, órdenes y envíos;
- datos de facturación y tracking.

Se recomienda un ejercicio de clasificación, retención, masking y acceso basado en rol. No se inspeccionaron valores de esas columnas durante el diagnóstico.

## 9. Recomendaciones priorizadas

### P0 — antes de cualquier tuning

1. Capturar una línea base de Azure Monitor y Query Store: CPU, Data IO, Log IO, workers, sesiones, bloqueos y duración por procedimiento durante al menos una semana representativa.
2. Confirmar la ventana de reinicio de DMVs y retención/configuración de Query Store.
3. Sustituir la cuenta administrativa de diagnóstico por una identidad explícitamente read-only.
4. Documentar el orquestador, frecuencia, concurrencia e idempotencia de cada `sp_*_preprocess_*` y `sp_*_postprocess_*`.

### P1 — rendimiento inmediato

1. Diseñar mantenimiento dirigido de estadísticas para `download_ship940`, `ShipMaster`, `ShipOrders`, `ShipContainerContents` y tablas staging activas.
2. Analizar el plan real del cálculo de `ranker/DICType`, que presentó una ejecución máxima cercana a 122 segundos.
3. Probar un índice consolidado y estrecho para el conjunto activo de `download_ship940`, empezando por las columnas de estado `DICType`, `ranker` y `LastProcessStamp`.
4. Evaluar un índice para la cola `ShipMaster(SCALEInterfaceAction, calendarDate3PL)` con includes mínimos justificados por la consulta consumidora.
5. Reducir pasadas repetidas: fusionar transformaciones compatibles en una sola actualización o materializar el conjunto activo una sola vez por lote.
6. Parametrizar fechas literales como `calendarDate3PL >= '2025-04-01'` y revisar si siguen siendo correctas operacionalmente.

### P2 — modelo e integridad

1. Construir un diccionario de claves de negocio: `ERP_ORDER`, `ID940`, `TCN`, `NSN`, shipment/container IDs, requisición y DODAAC.
2. Agregar integridad declarativa gradualmente donde la calidad actual lo permita; primero validar huérfanos y duplicados.
3. Revisar los 32 heaps y clasificarlos: staging deliberado, archivo, tabla temporal persistente o tabla operacional.
4. Definir política de archivo/purga para `download_*`, tracking, facturas, auditorías y copias fechadas.
5. Inventariar y retirar de forma controlada objetos `zzz_*`, `special_*`, `force_*` y copias con fecha que ya no tengan dueño o dependencia.

### P3 — gobierno y operabilidad

1. Clasificar columnas sensibles y aplicar acceso por roles.
2. Extraer reglas comerciales literales a tablas de configuración versionadas cuando sea posible.
3. Crear documentación de linaje y contratos de cada interfaz EDI.
4. Añadir telemetría por lote: filas leídas, insertadas, actualizadas, descartadas, duplicadas, duración y error.
5. Definir SLO operacionales para recepción, inventario, embarques y publicación a SCALE.

## 10. Plan de validación recomendado

Antes de implementar cambios:

1. Restaurar o clonar una copia representativa en un entorno no productivo.
2. Capturar planes y parámetros de las 10 consultas más costosas.
3. Actualizar estadísticas de manera controlada y comparar planes, CPU, lecturas y duración.
4. Probar uno o dos índices consolidados; medir impacto de lectura y costo adicional de escritura/log.
5. Probar la fusión de pasos de actualización sobre un lote real.
6. Validar resultados fila por fila o mediante hashes/agregados de control.
7. Desplegar con Query Store y plan de reversión.

## 11. Límites del diagnóstico

- No se consultaron datos personales ni muestras de filas.
- No se ejecutaron conteos exhaustivos de duplicados/nulos ni validaciones de negocio sobre millones de filas.
- No se ejecutó `sys.dm_db_index_physical_stats`, porque puede generar IO significativo.
- No se cambió configuración, estadística, índice, objeto, permiso ni dato.
- Las DMVs de uso/esperas son acumulativas y su fecha de reinicio no fue determinada.
- Las recomendaciones de índices faltantes son señales del optimizador, no instrucciones listas para producción.
- Dos consultas iniciales de catálogo se detuvieron al exceder el tiempo prudente; una primera versión multiplicó métricas por columnas y fue descartada. Todas las cifras publicadas en este informe provienen de la versión agregada corregida.

## 12. Conclusión

La base es comprensible y operacionalmente coherente: implementa un pipeline 3PL rico en reglas para DLA/SCALE, EDI, inventario, recepción, embarques y carriers. Su mayor deuda está en que esas reglas se ejecutan como numerosas pasadas sobre tablas muy anchas y de alta rotación, mientras las estadísticas relevantes han quedado muy atrás. La combinación explica razonablemente el CPU, paralelismo, lecturas lógicas y sugerencias de índices observados.

La prioridad no debería ser aumentar capacidad ni crear indiscriminadamente todos los índices sugeridos. El orden más seguro es: **línea base -> estadísticas -> planes reales -> índice consolidado de cola activa -> reducción de pasadas -> integridad y gobierno**.

