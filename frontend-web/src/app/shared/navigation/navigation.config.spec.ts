import { CUSTOMER_LINKS, navigationGroups, homeForRole, isStaff } from './navigation.config';
import { routes } from '../../app.routes';
import { ADMIN_ROUTES } from '../../features/admin/admin.routes';
describe('Role navigation', () => {
  it('keeps customer shopping separate from staff modules', () => {
    expect(isStaff('CLIENTE')).toBeFalse();
    expect(navigationGroups('CLIENTE')).toEqual([]);
    expect(homeForRole('CLIENTE')).toBe('/catalog');
    expect(CUSTOMER_LINKS.map(x => x.path)).toEqual(['/catalog', '/recommendations', '/fitting', '/cart', '/orders', '/reservations', '/profile/loyalty', '/profile']);
  });
  for (const role of ['ENCARGADO', 'ENCARGADO_SUCURSAL']) {
    it('shows only operational modules for ' + role, () => {
      expect(navigationGroups(role).flatMap(x => x.links.map(y => y.path))).toEqual(['/inventory', '/reservations', '/admin/exchanges']);
      expect(homeForRole(role)).toBe('/inventory');
    });
  }
  it('allows cashiers to access POS and their branch garment exchanges', () => {
    expect(navigationGroups('CAJERO').flatMap(x => x.links.map(y => y.path))).toEqual(['/pos', '/admin/exchanges']);
    expect(homeForRole('CAJERO')).toBe('/pos');
    expect(routes.find(x => x.path === 'admin/exchanges')?.data?.['roles']).toContain('CAJERO');
  });
  it('groups administration into five categories', () => {
    expect(navigationGroups('ADMINISTRADOR').map(x => x.label)).toEqual(['Catálogo', 'Inventario', 'Ventas', 'Usuarios', 'Reportes']);
    expect(homeForRole('ADMINISTRADOR')).toBe('/admin');
    expect(isStaff(' encargado ')).toBeTrue();
  });
  it('shows global role management only to platform administrators', () => {
    expect(navigationGroups('ADMINISTRADOR').flatMap(x => x.links.map(y => y.path))).not.toContain('/platform/roles');
    expect(navigationGroups('ADMINISTRADOR').flatMap(x => x.links.map(y => y.path))).not.toContain('/admin/roles');
    expect(navigationGroups('ADMINISTRADOR_PLATAFORMA').flatMap(x => x.links.map(y => y.path))).toContain('/platform/roles');
    expect(navigationGroups('ADMINISTRADOR_PLATAFORMA').flatMap(x => x.links.map(y => y.path))).toContain('/platform/subscriptions');
    expect(navigationGroups('ADMINISTRADOR_PLATAFORMA').flatMap(x => x.links.map(y => y.path))).toContain('/platform/plans');
    expect(navigationGroups('ADMINISTRADOR_PLATAFORMA').flatMap(x => x.links.map(y => y.path))).toContain('/platform/ai');
    expect(routes.find(x => x.path === 'platform/roles')?.canActivate).toBeDefined();
  });
  it('resolves every navigation destination against the existing routes', () => {
    const links = [...CUSTOMER_LINKS, ...['ADMINISTRADOR', 'ADMINISTRADOR_PLATAFORMA', 'ENCARGADO', 'CAJERO'].flatMap(role => navigationGroups(role).flatMap(x => x.links))];
    for (const link of links) {
      const path = link.path.slice(1);
      const exists = path === 'profile/loyalty'
        ? routes.find(x => x.path === 'profile')?.loadChildren !== undefined
        : path === 'admin/exchanges'
        ? routes.some(x => x.path === path)
        : path.startsWith('admin/')
          ? ADMIN_ROUTES[0].children?.some(x => x.path === path.slice(6))
          : routes.some(x => x.path === path);
      expect(exists).withContext(link.path).toBeTrue();
    }
    expect(routes.find(x => x.path === '')?.redirectTo).toBe('catalog');
  });
});
