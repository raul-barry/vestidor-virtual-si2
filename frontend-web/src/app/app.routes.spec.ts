import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { routes } from './app.routes';

describe('application routes', () => {
  it('configures lazy auth, profile and catalog routes', () => {
    expect(routes.find((route) => route.path === 'auth')?.loadChildren).toBeDefined();
    expect(routes.find((route) => route.path === 'catalog')?.loadChildren).toBeDefined();
    expect(routes.find((route) => route.path === 'profile')?.canActivate).toContain(authGuard);
    expect(routes.find((route) => route.path === 'cart')?.canActivate).toContain(authGuard);
    expect(routes.find((route) => route.path === 'checkout')?.canActivate).toContain(authGuard);
    expect(routes.find((route) => route.path === 'orders')?.canActivate).toContain(authGuard);
    expect(routes.find((route) => route.path === 'payments')?.canActivate).toContain(authGuard);
    expect(routes.find((route) => route.path === 'admin')?.canActivate).toContain(adminGuard);
  });
});
