import { CUSTOMER_LINKS, navigationGroups, homeForRole, isStaff } from './navigation.config';
import { routes } from '../../app.routes';
import { ADMIN_ROUTES } from '../../features/admin/admin.routes';
describe('Role navigation', () => {
  it('keeps customer shopping separate from staff modules', () => {
    expect(isStaff('CLIENTE')).toBeFalse();
    expect(navigationGroups('CLIENTE')).toEqual([]);
    expect(homeForRole('CLIENTE')).toBe('/catalog');
    expect(CUSTOMER_LINKS.map(x => x.path)).toEqual(['/catalog', '/recommendations', '/fitting', '/cart', '/orders', '/reservations', '/profile']);
  });
  for (const role of ['ENCARGADO', 'ENCARGADO_SUCURSAL']) {
    it('shows only operational modules for ' + role, () => {
      expect(navigationGroups(role).flatMap(x => x.links.map(y => y.path))).toEqual(['/inventory', '/reservations']);
      expect(homeForRole(role)).toBe('/inventory');
    });
  }
  it('shows only sales for cashiers', () => {
    expect(navigationGroups('CAJERO').flatMap(x => x.links.map(y => y.path))).toEqual(['/pos']);
    expect(homeForRole('CAJERO')).toBe('/pos');
  });
  it('groups administration into five categories', () => {
    expect(navigationGroups('ADMINISTRADOR').map(x => x.label)).toEqual(['Catálogo', 'Inventario', 'Ventas', 'Usuarios', 'Reportes']);
    expect(homeForRole('ADMINISTRADOR')).toBe('/admin');
    expect(isStaff(' encargado ')).toBeTrue();
  });
  it('resolves every navigation destination against the existing routes', () => {
    const links = [...CUSTOMER_LINKS, ...['ADMINISTRADOR', 'ENCARGADO', 'CAJERO'].flatMap(role => navigationGroups(role).flatMap(x => x.links))];
    for (const link of links) {
      const path = link.path.slice(1);
      expect(path.startsWith('admin/') ? ADMIN_ROUTES[0].children?.some(x => x.path === path.slice(6)) : routes.some(x => x.path === path)).withContext(link.path).toBeTrue();
    }
    expect(routes.find(x => x.path === '')?.redirectTo).toBe('catalog');
  });
});
