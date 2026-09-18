# Auditoría del frontend

## Alcance
Refactorización de presentación y navegación. Backend, endpoints, servicios, modelos y operaciones de negocio conservados. README.md y backend/requirements.txt tenían cambios previos del usuario y no se editaron.

## Hallazgos iniciales
- AppComponent renderizaba una navegación inline para todos los roles; AdminLayout añadía otro header y sidebar.
- Sidebar con más de veinte enlaces sin categorías.
- AdminLayout imponía un mínimo de 48rem en móvil, causando desbordamiento.
- La entrada raíz y el fallback dirigían al login aunque el catálogo es público.
- Colores y espaciados repetidos; Material ya ofrece botones, cards, tablas, formularios y modales reutilizables.
- Cuatro componentes de estado/confirmación duplicados en shared y admin/shared.
- Tablas sin contenedor de desplazamiento horizontal.
- Login reconocía ENCARGADO_SUCURSAL, pero no ENCARGADO, como destino de inventario.
- tsconfig.json tenía texto ajeno al JSON antes del objeto de configuración e impedía el build. Se conservó el objeto y se retiró solamente ese prefijo.

## Arquitectura resultante
AppComponent es el único shell de navegación. NavbarComponent presenta marca, cuenta y navegación ecommerce. AdminSidebarComponent se reutiliza para los tres roles internos; las categorías y destinos viven en shared/navigation/navigation.config.ts. AdminLayout conserva el outlet anidado sin duplicar la navegación.

| Experiencia | Navegación |
| --- | --- |
| Visitante | Catálogo, iniciar sesión, crear cuenta |
| Cliente | Catálogo, recomendaciones, vestidor, carrito, pedidos, reservas y perfil |
| Administrador | Dashboard y grupos Catálogo, Inventario, Ventas, Usuarios, Reportes |
| Encargado / Encargado de sucursal | Inventario, reservas y enlace existente a pedidos |
| Cajero | Venta presencial |

Las rutas existentes, incluidas las variantes /experience/recommendations y /experience/fitting y las rutas de detalle, se conservan. Raíz y fallback muestran el catálogo. Login usa el mismo mapa de destinos que la marca del navbar.

## Límite funcional encontrado
La separación implementada corresponde a navegación visible, no a una modificación de autorizaciones. authGuard y adminGuard se conservan.

El backend de /api/admin/orders exige get_current_admin. /api/orders consulta pedidos asociados al cliente autenticado. Por tanto, el enlace /orders del encargado conserva la pantalla existente, pero NO habilita una gestión operativa de pedidos de sucursal. Cumplir esa capacidad requiere otro alcance de permisos/API; no puede resolverse honestamente con un cambio visual. Asimismo, ocultar módulos del menú no revoca el acceso directo que autorizaban los guards anteriores.

## Pantallas afectadas
- Shell global, login (destino), layout y menú administrativo.
- Catálogo y tarjetas de producto: cabecera editorial, proporción vertical, rejilla responsive, teclado Enter/Espacio.
- Carrito, checkout, pedidos y detalle, pagos, perfil, autenticación: estilos comunes y tokens.
- Dashboard y gráficos: tokens y rejilla que se reduce en móvil.
- Tablas de productos, categorías, tallas, colores, sucursales, variantes, inventario e historial, pedidos y usuarios; también vistas de comercio y seguridad: 21 tablas con contenedor accesible.
- Todos los módulos reciben tema Material, botones, formularios y diálogos comunes.

## Reutilización
- ProductCardComponent, ProductFilterComponent, VariantSelectorComponent y OrderCardComponent.
- MatCard, MatTable/MatPaginator, MatButton, MatFormField/MatInput/MatSelect y MatDialog. Se evita crear wrappers sin funcionalidad adicional.
- LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent y ConfirmDialogComponent compartidos. Los antiguos imports de admin/shared se mantienen como reexports, sin implementaciones duplicadas.
