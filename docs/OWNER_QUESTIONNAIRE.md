# Owner Decision Questionnaire

**P1-A, P2-A, P3-A y P4-A aprobadas por Ed Lopez (HOC) el 2026-08-14.**

S1 quedó resuelta por evidencia. CSV1-CSV7 y FTP1-FTP8 bloquean las dos partes
de Phase 2. DB1-DB6 permanecen pendientes para Phase 3 hasta que Ed entregue
el layout de tablas.

## Seguridad urgente

### S1 — RESUELTA: placeholder histórico `PWD=`

La cadena no se mostró ni se probó. Se verificó estructuralmente que coincide
con un placeholder común y que aparece en un ejemplo donde servidor, base y
usuario también son literales placeholder. Clasificación: **ficticio/no
secreto**. No requiere rotación ni saneamiento de historial.

## Decisiones para cerrar Phase 1

### P1 — Estado de una reparación determinística

Cuando puntos/elipsis tienen una sola expansión válida, ¿qué estado debe
mostrar la herramienta?

- **A — `REQUIRES_REVIEW` (recomendado):** genera canonical, muestra todos los
  cambios y exige revisión humana antes de cualquier futura entrega.
- **B — `VALID`:** considera suficiente la solución única; menor fricción,
  mayor riesgo operativo.
- **C — `REJECTED`:** nunca repara automáticamente; máxima cautela, menor valor
  para el problema manual.

Decisión aprobada: **A**.

### P2 — Familias DIC admitidas por Travis

Los DLM suministrados contemplan A2_, A5_ y AF6, pero AF6 no está verificado
end-to-end en el proceso Travis. ¿Qué debe hacer Phase 1 con AF6?

- **A — Parsear y `REQUIRES_REVIEW` (recomendado):** preserva/diagnostica sin
  prometer compatibilidad de envío.
- **B — `REJECTED`:** bloquear AF6 hasta confirmar el pipeline.
- **C — Tratarlo como plenamente válido:** requiere evidencia de que Travis lo
  acepta hoy.

Decisión aprobada: **A**.

### P3 — Variante A2 observada versus layout DLM

AP8.25 define 67-69 como fecha de recepción, pero los ejemplos Travis colocan
`SMS` ahí. Para Phase 1, ¿cómo mostramos esa contradicción?

- **A — Preservar y marcar `INFO` (recomendado):** no altera el dato y no frena
  el flujo actual; Phase 3 resolverá el contrato de envío.
- **B — `REQUIRES_REVIEW`:** todo A2 legacy requiere confirmación.
- **C — Reubicar `SMS` automáticamente:** no recomendado sin confirmar el
  staging contract.

Decisión aprobada: **A**.

### P4 — Aceptación del incremento correctivo

Después de revisar la evidencia y el reporte final, ¿autorizas cerrar Phase 1?

- **A — GO:** cambiar status a `PHASE_1_ACCEPTED`.
- **B — NO-GO:** mantener pendiente y registrar los cambios requeridos.

Decisión aprobada: **A — GO**. Phase 1 queda aceptada; este GO no autoriza
Phase 2, conexiones, creación de base ni cambios de producción.

## Decisiones para Phase 2A — Rainbow CSV

Responder junto con el layout oficial y, si es posible, un archivo que Rainbow
ya haya aceptado. Sin estos datos no se debe inventar un CSV provisional.

### CSV1 — Forma del layout

- **A — Una columna con el MILSTRIP canonical de 80 caracteres.**
- **B — Varias columnas derivadas del MILSTRIP.**
- **C — Mezcla de canonical y metadata adicional.**

Entregar nombres, orden, tipo/longitud y obligatoriedad de cada columna.

### CSV2 — Dialecto exacto

Indicar: delimitador, encoding, header sí/no, comillas/escape, terminador de
línea, tratamiento de espacios finales, fecha/hora y si existe trailer.

### CSV3 — Nombre y agrupación

Indicar patrón exacto del filename, zona horaria, máximo de filas/tamaño y si
un archivo corresponde a un ticket, cliente, DODAAC o lote operativo.

### CSV4 — Registros elegibles

- **A — Solo `VALID` (recomendado inicialmente).**
- **B — `VALID` más `REQUIRES_REVIEW` confirmado por operador.**
- **C — Otra regla:** especificar aprobación y evidencia requerida.

`REJECTED` nunca será exportable.

### CSV5 — A5E y metadata fuera de los 80 caracteres

Definir cómo viajan dirección ship-to, ticket/source ID, cliente y cualquier
campo que Rainbow requiera fuera del canonical.

### CSV6 — Colisiones y retención local

- **A — Nunca sobrescribir; crear nombre único y conservar según retención
  definida (recomendado).**
- **B — Reemplazo controlado:** indicar cuándo y quién lo autoriza.
- **C — No conservar después de entrega:** requiere definir evidencia/auditoría.

### CSV7 — Criterio de aceptación

Indicar quién puede certificar que el golden CSV es correcto y proporcionar
al menos un caso válido y casos rechazables para pruebas byte-for-byte.

## Decisiones para Phase 2B — Rainbow FTP

### FTP1 — Protocolo real

- **A — SFTP.**
- **B — FTPS explícito/implícito.**
- **C — FTP plano:** requiere excepción de seguridad explícita.

### FTP2 — Ambientes y endpoints

Entregar host, puerto, DNS/IP restrictions y carpetas remotas para DEV/TEST y
PROD. Preferencia: endpoint no productivo separado antes de cualquier prueba.

### FTP3 — Autenticación y secretos

Indicar usuario por ambiente y mecanismo: SSH key, certificado o password.
Los secretos no se guardarán en el repo ni en el `.bat`.

### FTP4 — Activación del upload

- **A — Crear CSV, mostrar resumen y pedir confirmación antes de subir
  (recomendado para el primer release).**
- **B — Subir automáticamente si todas las filas son `VALID`.**
- **C — Crear solamente; el operador sube por otro medio.**

### FTP5 — Publicación atómica

Confirmar si Rainbow soporta upload con nombre temporal y rename final, y el
sufijo/nombre temporal esperado. Esto evita que el proceso lea un archivo a
medio transferir.

### FTP6 — Éxito y acknowledgement

Definir qué prueba significa `DELIVERED`: respuesta del servidor, presencia y
tamaño remoto, movimiento a carpeta de procesados, ACK separado u otra señal.

### FTP7 — Retry, duplicados y resubmission

Definir timeouts, cantidad/intervalo de retries, idempotency key, detección de
filename repetido y procedimiento para una corrección intencional.

### FTP8 — Soporte y operación

Indicar owner técnico/operativo de Rainbow, ventana de operación, alertas,
retención de logs sin PII/secrets y proceso cuando un archivo queda atascado.

## Decisiones para Phase 3 — base nueva (responder junto con el layout)

### DB1 — Plataforma preferida

- **A — Azure SQL (recomendado inicialmente):** encaja con el SQL legado,
  T-SQL, Azure y las capacidades operativas actuales.
- **B — PostgreSQL:** mayor separación tecnológica, pero añade otro motor y un
  adaptador hacia Azure SQL.
- **C — Evaluar ambas después del layout:** aplaza la selección hasta estimar
  contratos, costo y migración.

### DB2 — Propiedad del layout que vas a entregar

- **A — Es propuesta de la nueva aplicación:** puede modificarse durante diseño.
- **B — Es contrato obligatorio existente:** debemos adaptarnos sin cambiarlo.
- **C — Mezcla:** identifica qué tablas/columnas son obligatorias y cuáles son
  propuestas.

### DB3 — Datos que la nueva base puede conservar

- **A — Payload completo + derivados, con retención definida.**
- **B — Solo MILSTRIP/canonical y resultados; no correo completo (recomendado
  por minimización).**
- **C — Solo hashes/identificadores y estado; payload permanece en Freshservice.**

Indica también el período de retención requerido.

### DB4 — Entornos

- **A — DEV, TEST y PROD separados (recomendado).**
- **B — DEV/TEST compartido y PROD separado.**
- **C — Otro:** especificar restricciones actuales.

### DB5 — Identidades de conexión

- **A — Identidad administrada/Entra cuando el hosting se defina; cuentas SQL
  restringidas como fallback (recomendado).**
- **B — Cuentas SQL dedicadas desde el inicio.**
- **C — Reutilizar una cuenta existente:** no recomendado sin revisar permisos.

Se requieren identidades separadas para lectura de referencias y envío.

### DB6 — Fuente de verdad y handoff

¿Cuándo se considera entregada una orden?

- **A — Cuando se crea la fila de staging.**
- **B — Cuando aparece en `download_ship940` (recomendado según discovery).**
- **C — Cuando llega a `ShipMaster` o más abajo:** amplía la responsabilidad y
  contradice el boundary actual salvo decisión explícita.

## Decisiones externas aún necesarias

Estas requieren confirmación de negocio/seguridad, no solo arquitectura:

- clasificación, copyright y política de retención de los datos DLA;
- definición de duplicado y resubmission;
- lista exacta de DIC de producción;
- comportamiento esperado de A5E y agrupación de clientes;
- forma exacta del tail A2 que acepta `staging_download_shipMILS`.
