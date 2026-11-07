# CU28: supuestos de sincronización

No se encontró un enunciado original de CU28 en la documentación disponible. Esta implementación adopta los siguientes límites técnicos sin atribuirlos al contrato académico:

- El endpoint es `POST /api/sync/batch`, requiere JWT y acepta de 1 a 100 operaciones.
- Cada cliente adjunta `tenant_scope` (`org:<id>`) únicamente como comprobación de su scope local. El backend deriva la organización del usuario autenticado y rechaza la discrepancia; nunca usa el ID enviado para seleccionar el tenant.
- El identificador de dispositivo es informativo y no autoriza operaciones. Tokens y credenciales no forman parte del Outbox.
- Se registra el hash del contenido y el resultado, no el payload comercial. Una repetición con el mismo UUID y hash reproduce el resultado almacenado; otro hash produce HTTP 409.
- No se registran handlers comerciales en CU28. Las operaciones desconocidas se conservan como rechazadas y no producen efectos. Reservas, ventas e inventario quedan para los casos de uso posteriores.
- Los resultados de cada operación son independientes dentro del lote. Los handlers futuros deben ejecutar sus efectos y el registro idempotente en la misma transacción.
- Los ocho metadatos SaaS y sus planes no se modifican. La ruta usa la sesión, organización y auditoría existentes; la habilitación comercial de la característica `sincronizacion` no se infiere del nombre registrado.
