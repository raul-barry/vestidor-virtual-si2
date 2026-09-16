# CU20 / CU22: demostración integrada

Arranque: `docker compose up -d --build` desde la raíz. El backend aplica Alembic
y el seed idempotente; agrega cinco recursos SVG transparentes a los productos
de demostración existentes. Las ilustraciones están incluidas en `app/assets/fitting`.

1. Abrir `http://localhost:4200` e ingresar con `cliente@vestidor.local` / `Cliente123!`.
2. En el catálogo aparece **Recomendados para ti**. Un cliente sin historial ve
   productos disponibles, sin atribuirle preferencias inexistentes.
3. Abrir una camisa, seleccionar talla/color y, opcionalmente, marcar su categoría favorita.
4. Elegir **Probar en vestidor**. La ruta `/experience/fitting` conserva producto y variante.
5. Ajustar posición, tamaño y opacidad sobre el maniquí o una foto local.
6. Volver al catálogo o abrir `/experience/recommendations` para consultar el ranking actualizado.

## Contratos y extensión

- `GET /api/experience/recommendations` y alias `GET /api/recommendations`:
  ranking por compras confirmadas/enviadas/entregadas, vistas, favoritos y selecciones.
  Parámetros opcionales: `talla`, `color`, `categoria`. Una variante disponible por producto.
- `POST /api/experience/preferences`: `tipo` (`vista`, `seleccion`, `favorita`),
  `id_producto`, `id_variante` (obligatorio para selección). Identidad desde JWT;
  reutiliza Bitacora y evita repetir la misma señal por usuario.
- `GET /api/experience/fitting`: variantes disponibles con imagen activa.
- `GET /api/experience/virtual-fitting/{producto_id}`: variantes y recursos reales;
  devuelve 404 si no hay imagen activa o stock. Todas estas rutas requieren sesión.
- `recurso_virtual`: relación con Producto; `tipo_recurso` admite `imagen` y
  `modelo_3d`. El visor MVP usa únicamente imágenes. Nuevas imágenes se asocian
  mediante esta tabla con una URL servida por el backend; no hay editor de recursos.

El servicio interno usa puntuaciones explicables, no un modelo externo. El vestidor
es una superposición orientativa, sin estimación de medidas, AR ni Blender.
Los recursos se asocian al producto: su imagen de referencia no representa
automáticamente colores adicionales de variantes. La foto del cliente no se sube.

## Verificación

- Backend: `python -m pytest -q` en `backend`.
- Web: `npm run build` en `frontend-web` (en PowerShell, `npm.cmd run build`).
- Navegador contra servicios iniciados: `python frontend-web/scripts/smoke-experience.py`.
  Requiere Chrome local, `httpx` y `websockets`; admite `CHROME_BIN` y `VV_WEB_URL`.
  Comprueba login, catálogo, detalle, carga de imagen, controles, cambio de prenda
  y recomendaciones. Solo usa la cuenta de demostración.
