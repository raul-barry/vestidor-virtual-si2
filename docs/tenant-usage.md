# Métricas de uso por organización

## API

- `GET /api/platform/organizations/{id}/usage`: exclusivo de `ADMINISTRADOR_PLATAFORMA`.
- `GET /api/organizations/me/usage`: exclusivo de `ADMINISTRADOR`; determina la organización desde el JWT autenticado.
- Ambos aceptan `desde` y `hasta` opcionales como fechas ISO `YYYY-MM-DD`. Las dos fechas son inclusivas y los límites de tiempo se interpretan en UTC. Si no se envían, pedidos, pagos y reservas se agregan desde el inicio del histórico.

Ambos endpoints usan `TenantUsageService`; sus consultas filtran por la organización concreta y responden únicamente con agregados, nunca con nombres, correos ni credenciales de usuarios.

## Definición de métricas

- **Plan y suscripción:** último registro de suscripción. La consulta marca una suscripción vencida conforme a la lógica existente.
- **Sucursales:** sucursales cuyo estado, normalizado a mayúsculas, es `ACTIVA`; el límite viene del plan del último registro de suscripción.
- **Usuarios activos:** usuarios de la organización en estado `ACTIVO`, excluyendo `ADMINISTRADOR_PLATAFORMA`, que es un rol global.
- **Productos registrados:** todos los productos cuya propiedad es la organización; es un total acumulado.
- **Pedidos del período:** pedidos con al menos una línea de producto de la organización, filtrados por `Pedido.fecha_pedido`.
- **Ventas del período:** suma de `Pago.monto` para pagos `PAGADO` asociados a líneas de productos de la organización, filtrada por `Pago.fecha_pago`. Pagos pendientes o fallidos no se consideran venta.
- **Reservas del período:** cantidad de registros de reserva, de cualquier estado, cuyo usuario y sucursal de inventario pertenecen a la organización; se filtran por `Reserva.fecha`.
- **Inventario:** suma actual de disponible, reservado y vendido en inventarios de todas las sucursales de la organización. El modelo no conserva snapshots históricos de stock, por lo que el selector de período no cambia estos valores.

Las fechas fiables permiten comparar pedidos, pagos y reservas por período. El sistema no infiere actividad a partir de logs ni crea métricas históricas donde el modelo no las almacena.
