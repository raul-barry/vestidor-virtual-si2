# CU33: pagos offline e intermitentes

## Integraciones disponibles

- Tarjeta online usa Stripe PaymentIntent y webhook firmado (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CURRENCY`). El modo de simulación solo se habilita en desarrollo/pruebas. La UI solo puede confirmar endpoints de demostración cuando el registro está marcado como simulado.
- No se encontró un proveedor bancario QR. El endpoint QR devuelve una carga de demostración únicamente en desarrollo/pruebas; no constituye un cobro. En otros entornos informa que no hay proveedor configurado.
- Devoluciones Stripe conservan el ID del PaymentIntent y usan la clave idempotente de la operación. Efectivo/transferencia requieren evidencia antes de completarse.
- No se encontró configuración Firebase, FCM ni APNs; confirmaciones y rechazos se reflejan en la UI/Outbox y se consultan al recuperar conexión. Push requiere configurar un proveedor y credenciales por plataforma.

## Datos y seguridad

Las solicitudes offline usan `pago.solicitar` dentro del Outbox existente de CU28. La solicitud incluye UUID, scope de organización, usuario, pedido y método, pero nunca datos de tarjeta ni credenciales. El backend toma identidad y tenant de la sesión/credencial y calcula el monto desde el pedido. La venta offline conserva el pago en la misma operación para que el servidor calcule el total de las líneas aceptadas y el cambio en efectivo.

`payment_refund` conserva devoluciones monetarias con idempotencia por organización; `payment_adjustment` conserva cobros por diferencias positivas de cambios CU29. Las migraciones `20261106_0035` y `20261106_0036` agregan estas tablas y metadatos de pago.

## Limitaciones operativas

- QR bancario real aún requiere proveedor, credenciales, endpoint de verificación y webhook.
- Stripe requiere configurar las tres credenciales indicadas y comprobar el webhook en el entorno objetivo. Esta implementación no fue conectada a una cuenta bancaria real.
- Para pedidos con tarjeta/QR registrados offline, el servidor crea un pago pendiente tras sincronizar. El cliente debe volver al primer plano para completar la autorización Stripe; el sistema operativo no permite garantizar una autorización bancaria automática en segundo plano sin interacción.
- Las notificaciones push no están habilitadas mientras no exista proveedor configurado.
