# Seeders de demostración para los cuatro tenants

El fixture contiene datos sintéticos para Magnolia Boutique (GLAMOUR), Punto
Nativo (MODA), Distrito Urbano (ESTILO) y Atelier Sur (GLAMOUR). Prevé 14
sucursales, 90 productos con variantes, 690 ventas pagadas, 54 reservas y 32
solicitudes de cambio. El código no ejecuta migraciones, no llama pasarelas ni
escribe en la bandeja de sincronización.

Distrito Urbano conserva el límite actual de ESTILO: Centro y Plan 3000 están
activas; La Ramada está inactiva. Los planes y características globales no se
modifican. Una ejecución Render tampoco crea roles, categorías, tallas o colores
globales: si falta algún dato maestro, el preflight se bloquea.

## DRY RUN local

Desde `backend`, con destino SQLite o PostgreSQL local:

```powershell
python scripts/seed_exam_tenants.py --dry-run
```

## Acceso Render verificado

El CLI solo admite el recurso Postgres
`dpg-dboh755g1s2s73f6ej8g-a`, la base `vestidor_db`, PostgreSQL 16 y un host
Render cuyo nombre incluya ese ID. También consulta `current_database()` y la
versión del servidor. No imprime el DSN ni datos de autenticación. El modo
Render requiere confirmación explícita del ID y ENVIRONMENT=production.

Para previsualizar y auditar, una vez que el cliente tenga acceso de red al
Postgres, cargar `DATABASE_URL` desde el gestor seguro de secretos y ejecutar:

```powershell
python scripts/seed_exam_tenants.py --render-dry-run `
  --render-postgres-id dpg-dboh755g1s2s73f6ej8g-a `
  --confirm-render-target dpg-dboh755g1s2s73f6ej8g-a
```

El reporte incluye administradores, encargados, cajeros, empleados, clientes,
sucursales, productos, variantes, existencias, movimientos, ventas, pagos,
reservas, cambios y fidelización. Comprueba CU12 (fidelización condicionada al
plan) y CU13 (ventas por sucursal), límites de plan y cruces de tenant. Los dos
tenants GLAMOUR se reportan por separado.

## Respaldo previo

El recurso Render consultado es Free. Render no ofrece backups lógicos ni PITR
para bases Free. Se necesita un respaldo lógico `pg_dump` custom-format. El
host de esta base tiene la lista IP externa vacía; por eso el acceso desde la
sesión Render MCP fue rechazado. No se modificó esa lista. Para generar el dump
desde una máquina externa se requerirá una ventana autorizada de acceso de red,
o ejecutar el comando desde un servicio dentro de la red privada de Render.

Con `DATABASE_URL` apuntando al recurso autorizado y PostgreSQL client tools
instaladas, el helper verifica destino, nombre de base y versión, genera el
dump sin sobrescribir archivos y crea un manifiesto con hash SHA-256:

```powershell
python scripts/create_render_backup.py `
  --output "D:\\backups-seguros\\vestidor-db-20261109.dump" `
  --render-postgres-id dpg-dboh755g1s2s73f6ej8g-a `
  --confirm-render-target dpg-dboh755g1s2s73f6ej8g-a
```

Antes de APPLY, el CLI verifica el ID y base en el manifiesto, que tenga menos
de 24 horas, el hash del archivo y que `pg_restore --list` pueda leerlo y
declare la base esperada. Eso comprueba integridad estructural; no sustituye una
prueba de restauración completa en una instancia PostgreSQL aislada.

## APPLY Render (no ejecutado)

Solo tras la confirmación final, un DRY RUN sin bloqueos y un respaldo
verificado, configurar `DATABASE_URL` mediante el gestor seguro de secretos y
ejecutar el comando controlado. El modo Render genera contraseñas únicas y no
requiere `FASHIONSTORE_SEED_PASSWORD`:

```powershell
python scripts/seed_exam_tenants.py --render-apply `
  --render-postgres-id dpg-dboh755g1s2s73f6ej8g-a `
  --confirm-render-target dpg-dboh755g1s2s73f6ej8g-a `
  --backup-file "D:\\backups-seguros\\vestidor-db-20261109.dump" `
  --backup-manifest "D:\\backups-seguros\\vestidor-db-20261109.dump.manifest.json" `
  --confirm-render-apply APPLY:dpg-dboh755g1s2s73f6ej8g-a
```

`--apply` normal continúa bloqueado para production. La excepción solo existe
para `--render-apply` con el ID/host/base/versión exactos, confirmaciones,
respaldo válido, manifiesto privado de contraseñas y transacción. El seeder usa pagos simulados
internos, no pasarelas; no actualiza ni elimina registros preexistentes,
conserva idempotencia y solo opera sobre los cuatro slugs fijos. No añade datos
globales de roles/catálogo ni toca planes.

En `--render-apply`, el CLI prepara contraseñas criptográficamente aleatorias y
únicas para las 182 cuentas de tenant y el administrador SaaS global mediante
el bootstrap existente. El archivo predeterminado es
`backend/private_credentials/fashionstore-render-credentials.json`; la carpeta
está excluida de Git. El reporte y los logs nunca incluyen contraseñas. El
manifiesto se conserva para permitir reintentos idempotentes y pasa de
`PENDIENTE_APPLY` a `ACTIVO` después de completar el registro de cuentas.
Si ya existen cuentas objetivo sin ese manifiesto, APPLY se detiene y no cambia
ninguna contraseña. Para `--apply` local se conserva el secreto
`FASHIONSTORE_SEED_PASSWORD`.

## Pruebas

Los tests del seeder usan SQLite en memoria. No ejecutan consultas ni APPLY
contra Render. La suite PostgreSQL aislada no se ejecutó porque no hay servidor
PostgreSQL local ni `pg_dump`/`pg_restore` instalados en el host.
