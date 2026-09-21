# Cierre profesional — 17 de septiembre de 2026

## Estado y alcance

Versión funcional preparada para demostración académica y documentación. Se conserva arquitectura, modelos y módulos existentes. Producción preparada mediante un Compose separado; no desplegada. Una tienda pública con cobros y recuperación por correo requiere las integraciones detalladas al final.

La auditoría combina lectura de rutas, dependencias de autorización, servicios, suites existentes y recorrido API conectado a PostgreSQL. No equivale a una revisión exhaustiva de seguridad, a pruebas de carga ni a una sesión manual completa en todos los dispositivos.

## Matriz de casos de uso

PG = PostgreSQL real. Las pruebas de API unitarias usan SQLite. Las pantallas se indican por ruta/módulo; algunas incluyen subrutas.

| Caso de uso | Estado | Probado | Pantalla | Errores / observaciones |
|---|---|---|---|---|
| Registro | Completo | API + integral PG + widget | /auth/register; móvil Registro | Sin fallo detectado |
| Login y sesión | Completo | API + integral cuatro roles + Flutter | /auth/login; móvil Login | Rutas operativas endurecidas |
| Recuperación contraseña | Demo completa; producción parcial | API + integral PG | /auth/password-reset; móvil Recuperar contraseña | No existe transporte de correo |
| Perfil | Completo | API + integral PG + widget | /profile; móvil Perfil | Sin fallo detectado |
| Consulta catálogo | Completo | API + integral PG + widget + visual | /catalog; móvil Catálogo | Sin fallo detectado |
| Búsqueda | Completo | test_catalog_search + integral PG | /catalog; móvil Catálogo | Sin fallo detectado |
| Filtros | Completo | API + integral PG + repository Flutter | /catalog; móvil Catálogo | Sin fallo detectado |
| Detalle producto | Completo | API + Angular + widget Flutter | /catalog/product/:id; móvil Producto | Sin fallo detectado |
| Login administrador | Completo | API + integral PG + guard | /auth/login | Sin fallo detectado |
| Dashboard | Completo | test_report_admin + integral PG | /admin | Sin fallo detectado |
| Usuarios | Completo | test_user_admin + integral PG | /admin/users | Sin fallo detectado |
| Productos y variantes | Completo | test_product_admin + test_variant_admin + integral PG | /admin/products; /admin/variants | Sin fallo detectado |
| Inventario | Completo | test_inventory_admin + integral PG + guard | /admin/inventory; /inventory | Guard, paginación de filtros, reset de error y responsive corregidos |
| Reportes | Completo | test_report_admin + integral PG | /admin/reports | Sin fallo detectado |
| Carrito | Completo | test_cart_api + integral PG + widget | /cart; móvil Carrito | Ruta limitada al cliente |
| Checkout | Completo | test_order_api + integral PG + widget | /checkout; móvil Compra | Ruta limitada al cliente |
| Pedido | Completo | test_order_api + integral PG + widget | /orders/:id; móvil Pedido | Sin fallo detectado |
| Pago | Demo completa; producción parcial | test_payment_api + integral PG + widget | /payments; móvil Pago | Simulación bloqueada en producción; sin pasarela externa |
| Historial | Completo | API + integral PG + repository Flutter | /orders; móvil Pedidos | Retirado enlace incorrecto del encargado |
| Reservas | Completo | test_reservations + integral PG + widget | /reservations; móvil Reservas | Ruta restringida por rol |
| Recomendaciones | MVP completo | test_experience + integral PG | /recommendations; móvil Recomendaciones | Sin fallo detectado dentro del alcance MVP |
| Vestidor virtual | MVP completo | test_experience + integral PG + widget | /fitting; móvil Vestidor | Origen de recursos compatible con producción |
| Venta presencial | Completo en alcance local | test_commerce + integral PG | /pos | Ruta limitada a cajero/administrador |

## Roles

| Rol | Menú y rutas | Backend |
|---|---|---|
| ADMINISTRADOR | Dashboard, usuarios, productos, inventario, reportes y administración existente | get_current_admin; inventario y caja también admiten administrador |
| CLIENTE | Catálogo, perfil, carrito, compra, pedidos, reservas y experiencia | Sesión activa y rol CLIENTE en pedidos/pagos/carrito; propiedad del recurso y reservas propias |
| ENCARGADO_SUCURSAL | Inventario y reservas | get_current_staff / require_roles; operaciones acotadas por require_branch |
| CAJERO | Venta presencial | ADMINISTRADOR/CAJERO; stock de sucursal asignada |

El servidor consulta usuario, rol, estado y sesión en la base; no confía solo en el rol del JWT. El guard web mejora navegación, no sustituye autorización del servidor. Catálogo es público. La app Flutter rechaza y revoca sesiones no CLIENTE, según su suite existente. El alias histórico ENCARGADO en navegación no es un rol maestro del seed.

## Correcciones realizadas en este cierre

- Rutas de inventario, caja, reservas y compra verifican roles usando el guard existente.
- Backend de carrito, pedidos y pagos exige CLIENTE incluso si una cuenta conserva su registro de cliente después de cambiar a un rol de personal; prueba de regresión incluida.
- Menú del encargado deja de enlazar el historial exclusivo del cliente.
- Inventario reinicia error al recargar, vuelve a la primera página al filtrar y adapta filtros a pantallas estrechas.
- Build de producción deja de apuntar a localhost:8000 y utiliza el origen de la web.
- Dockerfile local usa npm ci para reproducir package-lock.json.
- Nginx sirve archivos estáticos, rutas SPA y API; Compose de producción no publica PostgreSQL ni FastAPI, no monta código y no usa reload.
- Configuración rechaza secreto inseguro, exposición de tokens y CORS comodín en producción.
- Seed admite solo roles para producción y bloquea cuentas demo en ese entorno.
- Script de preparación reutiliza endpoints actuales para pedidos y reservas del cliente demo.
- README reemplazó descripciones obsoletas de módulos futuros por instrucciones ejecutables.
- Prueba visual verifica también que la ruta solicitada no fue redirigida.

## Archivos de este cierre

Se conservaron los cambios previos del usuario. Este inventario identifica únicamente los archivos tocados durante esta intervención:

- README.md; .gitignore.
- docker-compose.production.yml; .env.production.example.
- backend/app/core/config.py; backend/app/database/seed.py.
- backend/app/api/cart_router.py; order_router.py; payment_router.py.
- backend/tests/test_customer_role_boundary.py.
- backend/scripts/prepare_demo.py; backend/tests/test_production_config.py.
- frontend-web/angular.json; frontend-web/Dockerfile; frontend-web/Dockerfile.production; frontend-web/nginx.conf.
- frontend-web/src/environments/environment.production.ts.
- frontend-web/src/app/app.routes.ts.
- frontend-web/src/app/core/guards/auth.guard.ts; auth.guard.spec.ts.
- frontend-web/src/app/shared/navigation/navigation.config.ts; navigation.config.spec.ts.
- frontend-web/src/app/features/admin/pages/inventory/inventory-list/inventory-list.component.ts.
- frontend-web/scripts/visual-smoke.cjs.
- docs/CIERRE.md; docs/DEMOSTRACION.md; docs/PRODUCCION.md; docs/npm-audit.json.

## Pruebas de cierre

- Backend `python -m pytest -q`: 121 aprobadas, 1 omitida (integral opt-in).
- Integral `VV_E2E_BASE_URL=http://localhost:8000`: 1 aprobada por separado sobre PostgreSQL, cuatro roles.
- Angular `npm.cmd run build`: correcto; aviso de bundle inicial 567.59 kB frente al presupuesto de aviso 500 kB. No se elevó el umbral para ocultarlo.
- Flutter `flutter analyze`: sin incidencias.
- Flutter `flutter test`: 26 aprobadas.
- `docker compose up -d --build`: reconstrucción final y arranque correctos; database, backend y frontend arrancados, base saludable.
- Comprobación real adicional de permisos: 17 respuestas 200/403 esperadas, cuatro roles, aprobadas.
- Conteo local verificado: 6 usuarios, 10 productos, 17 inventarios, 4 pedidos y 3 reservas (incluye registros preexistentes y de la prueba integral).
- HTTP final tras reconstrucción: /health en puerto 8000 y web en puerto 4200 respondieron 200. Durante la recreación hubo una comprobación transitoria fallida; pasó al completar el arranque.
- Script prepare_demo.py: completado, cliente demo con pedidos y reservas.
- `git diff --check`: sin errores de espacios; avisos de conversión LF/CRLF del repositorio.

- Angular `npm.cmd run test:ci`: 102 aprobadas.
- Visual `npm.cmd run test:visual`: 20 combinaciones de rol/ancho aprobadas (320, 390, 768 y 1440 px), con rutas verificadas y capturas.
- Nginx: `nginx -t` correcto en contenedor temporal sin puertos publicados.
- Configuración de Compose producción validada; imágenes vestidor-production-backend y vestidor-production-frontend construidas correctamente. Producción no arrancada.

## Pendientes reales

1. Conectar correo de recuperación; el flujo actual de desarrollo devuelve token explícitamente.
2. Integrar pasarela de pago si el objetivo cambia de demostración a cobros reales. No se añadió una integración nueva fuera del alcance solicitado.
3. Validar servidor definitivo, TLS, dominio, secretos, copias y restauración antes de despliegue. Crear el administrador propio sin credenciales demo.
4. Completar capturas manuales de flujos reales y prueba en dispositivo físico Flutter; las evidencias visuales automatizadas usan fixtures.
5. Reducir el bundle inicial mediante una revisión posterior acotada; el build no presenta error.
6. Auditoría npm: 55 vulnerabilidades (4 bajas, 27 moderadas, 23 altas, 1 crítica), informe completo en npm-audit.json. Angular common/core/compiler y CLI/build requieren versiones mayores según fixAvailable; la crítica de tar es transitiva de CLI y npm propone CLI 22. No se aplicó --force porque implica una migración mayor fuera del cierre solicitado. Es un bloqueo para exposición pública. Revisar también la deprecación datetime.utcnow de python-jose.
7. Pytest emite avisos por permisos de su caché local; no afectan resultados. PowerShell exigió npm.cmd y Flutter/Docker acceso al SDK/daemon fuera del sandbox.
