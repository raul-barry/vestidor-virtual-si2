# Demostración y evidencias

## Preparación

1. Arrancar Docker local según README y comprobar /health.
2. Ejecutar el seed existente y `python scripts/prepare_demo.py` desde backend.
3. Usar cuentas de README; cerrar sesión entre roles. Los datos son ficticios.
4. Capturar web a 1440×900 y 390×844; móvil en emulador o teléfono.
5. Registrar fecha, rol, URL/pantalla y resultado junto a cada captura. Evitar capturar JWT, tokens de recuperación o contraseñas.

## Cliente

Login → catálogo → búsqueda y filtros → detalle y variante → vestidor → carrito → checkout → pago simulado → detalle del pedido → historial.
Después: perfil → reserva de una unidad → lista de reservas → recomendaciones → cerrar sesión.
El vestidor requiere una variante con recurso compatible del seed. Las compras y reservas consumen disponibilidad; no repetir indefinidamente sobre la misma variante.

## Administrador

Login → dashboard → usuarios → productos → variantes → inventario e historial → pedidos → reportes.
Elegir registros existentes para capturas y no desactivar las cuentas demo. Mostrar tablas con datos y filtros legibles.

## Personal

Encargado: login → inventario asignado → reservas → confirmar una reserva.
Cajero: login → venta presencial → cliente → producto de su sucursal → confirmar → cerrar sesión.

## Evidencia automatizada

`npm.cmd run test:visual` guarda capturas y resultados bajo frontend-web/artifacts/visual con datos aislados. Complementar con capturas manuales del recorrido conectado a PostgreSQL y del dispositivo Flutter. No confundir fixtures visuales con datos reales de la API.

## Estados negativos

Probar contraseña incorrecta, búsqueda sin coincidencias, carrito vacío y una ruta administrativa como cliente. Comprobar texto de error, ausencia de desbordamiento horizontal y recuperación de la navegación.
