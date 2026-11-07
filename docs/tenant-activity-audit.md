# Auditoría de actividad empresarial

CU25.2 agrega la tabla `audit_log` (migración `20261103_0030`) y un listener transaccional de SQLAlchemy. El registro cubre creación y modificación de usuarios, sucursales y productos; movimientos de inventario; reservas; pedidos; cambios de estado de pagos; y cambios de suscripciones. Los registros se escriben en la misma transacción que la operación empresarial.

Los detalles almacenan nombres de campos modificados y, cuando corresponde, estados anterior/nuevo. No guardan cuerpos de petición, nombres, correos, teléfonos, credenciales, hashes, tokens ni datos de tarjeta. Los eventos históricos anteriores a la migración no se reconstruyen.

La API solo expone lectura: `GET /api/platform/organizations/{id}/activity` para `ADMINISTRADOR_PLATAFORMA` y `GET /api/organizations/me/activity` para `ADMINISTRADOR`. Ambas consultan con `organizacion_id` explícito y permiten filtrar por intervalo UTC, código de acción e ID de usuario, además de paginar (`limit`, `offset`). El ORM también impide actualizar o borrar filas de auditoría.

Limitación: la base registra operaciones exitosas que llegan a la transacción; rechazos de autorización/validación no se guardan. La identidad de sistemas o webhooks sin usuario autenticado queda con rol `SISTEMA` y usuario nulo.
