# Guía visual de Vestidor Virtual

## Principios
Tienda editorial para clientes, espacio compacto de trabajo para personal. Un único shell mantiene contexto al cambiar entre módulos. Los estados activos no dependen exclusivamente del color: usan peso tipográfico, borde y aria-current.

## Fundamentos
Fuente de interfaz: Segoe UI / Roboto / Arial, sin descargas externas. Georgia en la cabecera editorial del catálogo.

| Token | Valor | Uso |
| --- | --- | --- |
| --primary | #00695c | Enlaces activos y acentos |
| --primary-soft | #e4efeb | Fondos seleccionados |
| --ink | #202b29 | Texto principal |
| --muted | #596864 | Texto secundario |
| --canvas | #f6f5f1 | Fondo de aplicación |
| --surface | #ffffff | Tarjetas y navegación |
| --border | #dce3df | Separadores |
| --danger | #b3261e | Errores |

Espaciado: 4, 8, 12, 16, 24 y 32 px mediante --space-*. Radio: 12 px para superficies, 8 px para controles, 16 px para diálogos. Tipografía fluida en títulos. Tema Material teal 700/brown con rojo para acciones destructivas.

## Componentes
- Navbar: shared/components/navbar. Inputs signedIn, role, staff y expanded; outputs toggleMenu y signOut. No realiza peticiones.
- Sidebar: AdminSidebarComponent, recibe role y emite navigate. Categorías desplegables nativas; el grupo de la ruta activa se abre automáticamente.
- Cards: usar MatCard y los componentes de producto/pedido existentes.
- Botones: mat-flat-button color="primary" para acción principal; mat-stroked-button para secundaria; mat-button para terciaria; warn para destructiva.
- Formularios: reutilizar Material y validadores existentes. Inputs nativos comparten estilo global, sin reemplazar bindings ni validaciones.
- Tablas: conservar MatTable y paginación. Envolver en .table-scroll con role="region", aria-label descriptivo y tabindex="0". Los datos mantienen su semántica de tabla y permiten scroll con teclado.
- Modales: MatDialog y ConfirmDialogComponent compartido. Cancelar no confirma; la acción explícita devuelve true, como antes.
- Estados: componentes compartidos con role="status" o role="alert". No duplicar versiones por módulo.

## Responsive y accesibilidad
Sidebar de 236 px en escritorio; por debajo de 760 px se despliega dentro del flujo con botón Menú, aria-expanded y cierre al elegir destino o pulsar Escape. No es un modal ni necesita bloquear foco. Navbar ecommerce permite desplazamiento horizontal sin desbordar el documento. Catálogo en 3/2/1 columnas; tablas desplazan dentro de su contenedor. Focus visible, enlace Saltar al contenido y respeto a prefers-reduced-motion.

## Cambios futuros
Añadir destinos en navigation.config.ts. Reutilizar los componentes Material y los tokens de styles.scss. No incorporar controles paralelos para la misma función ni colores arbitrarios. Mantener la autorización del backend separada de la visibilidad de navegación.

El modelo actual no incluye fotografía de producto: ProductCard muestra un marcador local explícito de imagen no disponible, sin depender de un proveedor externo.
