export interface NavigationLink { label: string; path: string; }
export interface NavigationGroup { label: string; links: NavigationLink[]; }
const link = (label: string, path: string): NavigationLink => ({ label, path });
export const CUSTOMER_LINKS = [link('Catálogo', '/catalog'), link('Recomendaciones', '/recommendations'), link('Vestidor virtual', '/fitting'), link('Carrito', '/cart'), link('Mis pedidos', '/orders'), link('Mis reservas', '/reservations'), link('Perfil', '/profile')];
export const ADMIN_GROUPS: NavigationGroup[] = [
  { label: 'Catálogo', links: [link('Productos', '/admin/products'), link('Categorías', '/admin/categories'), link('Variantes', '/admin/variants'), link('Tallas', '/admin/sizes'), link('Colores', '/admin/colors'), link('Colecciones', '/admin/collections')] },
  { label: 'Inventario', links: [link('Existencias', '/admin/inventory'), link('Proveedores', '/admin/suppliers'), link('Sucursales', '/admin/branches'), link('Ciudades', '/admin/cities')] },
  { label: 'Ventas', links: [link('Venta presencial', '/pos'), link('Pedidos', '/admin/orders'), link('Reservas', '/reservations'), link('Promociones', '/admin/promotions'), link('Devoluciones', '/admin/returns')] },
  { label: 'Usuarios', links: [link('Usuarios', '/admin/users'), link('Seguridad', '/admin/security')] },
  { label: 'Reportes', links: [link('Reportes', '/admin/reports'), link('Bitácora', '/admin/audit')] }
];
export function normalizeRole(role: string | null): string { return (role ?? '').trim().toUpperCase(); }
export function isStaff(role: string): boolean { return ['ADMINISTRADOR', 'ENCARGADO', 'ENCARGADO_SUCURSAL', 'CAJERO'].includes(normalizeRole(role)); }
export function navigationGroups(role: string): NavigationGroup[] {
  switch (normalizeRole(role)) {
    case 'ADMINISTRADOR': return ADMIN_GROUPS;
    case 'ENCARGADO':
    case 'ENCARGADO_SUCURSAL': return [{ label: 'Operaciones', links: [link('Inventario', '/inventory'), link('Reservas', '/reservations')] }];
    case 'CAJERO': return [{ label: 'Ventas', links: [link('Venta presencial', '/pos')] }];
    default: return [];
  }
}
export function homeForRole(role: string): string {
  switch (normalizeRole(role)) {
    case 'ADMINISTRADOR': return '/admin';
    case 'ENCARGADO':
    case 'ENCARGADO_SUCURSAL': return '/inventory';
    case 'CAJERO': return '/pos';
    default: return '/catalog';
  }
}
