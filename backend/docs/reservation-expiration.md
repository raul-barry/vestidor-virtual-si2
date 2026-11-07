# Procesamiento de reservas vencidas

El comando `python -m scripts.process_expired_reservations` procesa hasta 500
reservas por ejecucion. Debe programarse diariamente desde el programador
operativo del entorno que ejecuta el backend, con el mismo `DATABASE_URL` y
entorno virtual. El comando no instala ni inicia un programador por si mismo.

Ejemplo cron (02:15 diariamente):

```cron
15 2 * * * cd /ruta/al/proyecto/backend && .venv/bin/python -m scripts.process_expired_reservations
```

En Windows Task Scheduler, configurar una tarea diaria que ejecute
`backend\\.venv\\Scripts\\python.exe` con el argumento
`-m scripts.process_expired_reservations` y directorio inicial `backend`.
Proveer las variables de base de datos en el contexto protegido del programador;
nunca incluir credenciales como argumentos.

El servicio procesa reservas activas vencidas que no tengan pedido asociado.
Conserva estados completados y filas vinculadas al ciclo de pedidos o pagos.
El cambio de estado, la liberacion de inventario y el evento de auditoria se
confirman en una transaccion. `FOR UPDATE SKIP LOCKED` permite multiples
workers sin procesar dos veces la misma reserva. Las inconsistencias de stock
se dejan intactas y el comando devuelve codigo 2 para alertar al operador.
