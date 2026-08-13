# Anexo de evidencias — `trav3pl-sqldb-eastus-prod`

Este anexo acompaña al informe principal. Resume las observaciones de solo lectura y evita incluir credenciales o datos de negocio.

## A. Identidad técnica de la sesión

- Servidor resuelto: `trav3pl-sql-eastus`
- Base efectiva: `trav3pl-sqldb-eastus-prod`
- Motor: SQL Azure, versión reportada `12.0.2000.8`
- Login observado: `TabAdmin`
- Usuario de base: `dbo`
- Base: `ONLINE`, operativamente `READ_WRITE`
- Visibilidad: `VIEW DATABASE STATE = 1`, `VIEW SERVER STATE = 1`
- Transporte usado para el diagnóstico: ODBC Driver 18, cifrado habilitado, certificado validado, `ApplicationIntent=ReadOnly`

## B. Tablas relevantes adicionales

| Tabla | Filas estimadas | MB reservados | Nota |
|---|---:|---:|---|
| `track_ups_deliver` | 406,431 | 109.25 | Tracking de entregas UPS |
| `ShipShipments` | 203,487 | 102.36 | Entidad de shipment derivada |
| `track_fedex_deliver` | 394,713 | 93.44 | Tracking de entregas FedEx |
| `track_ups_exception` | 170,881 | 58.09 | Excepciones UPS |
| `download_rcv856` | 273,277 | 57.79 | Entrada EDI de recepción |
| `preReceiptMaster` | 126,969 | 34.67 | Preparación de recibos |
| `LOCATION_INVENTORY_daily` | 66,596 | 18.63 | Snapshot diario; heap sin PK |
| `staging_track_fedex` | 11,670 | 17.26 | Staging muy ancho, 90 columnas |
| `track_fedex_exception` | 25,398 | 16.12 | Excepciones FedEx |
| `LOCATION_INVENTORY` | 22,605 | 12.20 | Inventario por ubicación; heap |
| `ItemMaster` | 15,924 | 10.52 | Maestro de artículos |
| `ReceiptMasterHeader` | 23,440 | 10.42 | Cabecera de recepción |
| `staging_download_rcv856` | 35,553 | 9.63 | Staging de recepción |
| `upload_adj947` | 11,392 | 8.80 | Interfaz de ajustes |
| `InventoryAdjust` | 15,964 | 8.41 | Ajustes de inventario |

Las cifras de filas provienen de `sys.dm_db_partition_stats`; son apropiadas para inventario y no implican un `COUNT(*)` sobre cada tabla.

## C. Procedimientos y funciones identificados

### Recepción y ajustes

- `sp_download_rcv_075_Cdum_PreReceiptMaster`
- `sp_download_rcv_100_ReceiptMasterHeader`
- `sp_download_rcv_110_ReceiptMasterDetail`
- `sp_rcv_postprocess_015_InterfaceControl`
- `sp_rcv_postprocess_020_from_staging`
- `sp_adj_postprocess_015_InterfaceControl`
- `sp_adj_postprocess_020_from_staging`
- `sp_adj_postprocess_050_adj947`

### Embarques 940

- `sp_download_ship940_015_InterfaceControl`
- `sp_download_ship940_020_from_staging`
- `sp_ship_preprocess_030_dedupe`
- `sp_ship_preprocess_035_initialize`
- `sp_ship_preprocess_040_cleanse`
- `sp_ship_preprocess_050_level1_cats`
- `sp_ship_preprocess_075_level2_cats`
- `sp_ship_preprocess_090_instruction`
- `sp_ship_preprocess_125_load_ShipMaster`
- `sp_ship_preprocess_135_ShipMaster_cleanse`
- `sp_ship_preprocess_145_ship_calendar_today`
- `sp_ship_preprocess_148_autocancel`
- `sp_ship_preprocess_150_zero_day`
- `sp_ship_postprocess_020_ContentsWt`
- `sp_ship_postprocess_030_region`
- `sp_ship_postprocess_050_loads`
- `sp_ship_postprocess_055_orders`
- `sp_ship_postprocess_060_containercontents`
- `sp_ship_postprocess_080_disposition_update`
- `sp_ship_postprocess_110_shipments`
- `sp_ship_postprocess_120_manifest_number`

### Inventario y reportes

- `sp_inv_create_846`
- `sp_item_code_change`
- `sp_calendar_regenerate`
- `sp_rpt_Daily_MRO_Report`
- `sp_rpt_dead_stock`
- `sp_rpt_Inventory2026`
- `sp_rpt_NSN_History`
- `sp_rpt_SCALE_cancel_denial_status`
- `sp_rpt_TRAV3PL_extension_propose`

### Funciones

- `fn_timeZoneUsCentral`
- `fn_timeZoneUsCentral2`
- `fn_columnSplit`

La presencia de dos funciones de zona Central amerita revisar duplicidad semántica y tratamiento de horario de verano. No se recomienda consolidarlas sin revisar dependencias y resultados históricos.

## D. Índices destacados y contadores observados

| Tabla / índice | MB | Seeks | Scans | Lookups | Updates |
|---|---:|---:|---:|---:|---:|
| `ShipMaster.PK_ShipMaster_ShipMasterID` | 5,364.24 | 5,284 | 1,596 | 2,661 | 7,631 |
| `download_ship940.PK_download_ship940` | 3,712.10 | 421 | 8,827 | 1,434 | 8,410 |
| `ShipOrders` PK | 2,811.77 | 3,467 | 249 | 152 | 3,688 |
| `ShipContainerContents` PK | 1,488.03 | 1,025 | 176 | 24 | 1,128 |
| `IRMMaster` PK | 1,299.80 | 0 | 12 | 17 | 6 |
| `InventoryMaster` PK | 1,204.95 | 0 | 0 | 18 | 6 |
| `IRMMaster.UQ_IRMMaster_composite` | 507.40 | 24 | 0 | 0 | 6 |
| `InventoryMaster.IX_InventoryMaster_ITEM` | 432.90 | 0 | 0 | 0 | 6 |
| `IRMMaster.IX_IRMMaster_NSN` | 399.12 | 0 | 0 | 0 | 6 |
| `download_ship940.IX_download_ship940_ERPORDER` | 228.84 | 66 | 0 | 0 | 486 |

Estos contadores son evidencia contextual. No deben usarse solos para eliminar índices.

## E. Candidatos de índice detectados

Las combinaciones más repetidas por las DMVs fueron:

1. `download_ship940(ranker, DICType, LastProcessStamp)`.
2. Variaciones adicionales por dirección: `SHIPTOCITY`, `SHIPTOSTATE`, `SHIPTOCOUNTRY`, `SHIPTOZIP`, `DELIVERYZIP` y campos finales.
3. `ShipMaster(SCALEInterfaceAction, calendarDate3PL)` con columnas de orden como cobertura.
4. `ShipMaster(QtyRemainder)` con `ERP_ORDER` y `ORDERQTY`.
5. `download_ship940(MROID)`.
6. `ShipOrders(TimeStampUpload, dayActivity, TCN)`.

La señal de mayor valor estimado fue para `download_ship940` sobre `ranker`, `DICType` y `LastProcessStamp`. Sin embargo, las recomendaciones derivan de consultas individuales; se deben agrupar por prefijo, revisar índices actuales y minimizar columnas incluidas.

## F. Hipótesis técnicas para probar

1. **Estadísticas viejas -> cardinalidad incorrecta -> planes paralelos costosos.** Evidencia: muestreo 2.34 %, miles de millones de modificaciones y waits paralelos dominantes.
2. **Actualizaciones por etapas -> múltiples lecturas del mismo universo.** Evidencia: numerosas consultas 574 veces en siete días, cada una con cientos de millones de lecturas acumuladas.
3. **Falta de índice de estado de proceso.** Evidencia: sugerencias repetidas sobre `ranker`, `DICType`, `LastProcessStamp` y `SCALEInterfaceAction`.
4. **Reglas no sargables.** Evidencia: uso frecuente de `SUBSTRING`, `UPPER`, `CASE`, `LIKE '%...%'` y transformaciones sobre columnas en predicados.
5. **Procesamiento histórico innecesario.** Algunas condiciones de fecha o estado podrían abarcar más historia de la necesaria; se debe validar semántica y distribución.
6. **Modelo ancho amplifica escritura.** Actualizar tablas de 95–126 columnas, con varios índices, aumenta log y páginas afectadas incluso si se cambian pocas columnas.

## G. Consultas futuras recomendadas, aún no ejecutadas

Por seguridad operativa, las siguientes tareas deben programarse y revisarse antes de ejecutarse:

- Distribución de estados activos en `download_ship940.LastProcessStamp`, `DICType`, `ranker` y `ShipMaster.SCALEInterfaceAction`.
- Duplicados según las claves de negocio verdaderas.
- Huérfanos entre cabecera/detalle, shipments/orders/containers y tablas maestras.
- Retención real por fechas de creación/proceso.
- Fragmentación física con modo `LIMITED` y filtros por tamaño.
- Planes reales de las consultas principales con parámetros representativos.
- Dependencias de procedimientos mediante `sys.sql_expression_dependencies` y validación manual de SQL dinámico.
- Permisos efectivos por usuario/rol y auditoría de accesos.
- Métricas de Azure Monitor del servidor y base.

## H. Declaración de no modificación

Durante el análisis no se ejecutaron sentencias `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, DDL, mantenimiento, cambios de configuración, cambios de permisos ni despliegues. Las sentencias de escritura citadas en el informe provienen exclusivamente del texto histórico almacenado en Query Store.

