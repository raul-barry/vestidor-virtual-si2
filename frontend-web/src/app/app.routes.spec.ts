import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { platformAdminGuard } from './core/guards/platform-admin.guard';
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

  it('protects SaaS subscription management with the platform administrator guard', () => {
    const subscriptions = routes.find((route) => route.path === 'platform/subscriptions');
    expect(subscriptions?.canActivate).toContain(platformAdminGuard);
    expect(subscriptions?.loadComponent).toBeDefined();
  });

  it('protects tenant provisioning with the platform administrator guard before the organization id route', () => {
    const provisioningIndex = routes.findIndex((route) => route.path === 'platform/organizations/provision');
    const detailIndex = routes.findIndex((route) => route.path === 'platform/organizations/:id');
    const provisioning = routes[provisioningIndex];
    expect(provisioning?.canActivate).toContain(platformAdminGuard);
    expect(provisioning?.loadComponent).toBeDefined();
    expect(provisioningIndex).toBeLessThan(detailIndex);
  });

  it('protects commercial plan management with the platform administrator guard', () => {
    const plans = routes.find((route) => route.path === 'platform/plans');
    expect(plans?.canActivate).toContain(platformAdminGuard);
    expect(plans?.loadComponent).toBeDefined();
  });

  it('exposes global role management only behind the platform administrator guard', () => {
    const roles = routes.find((route) => route.path === 'platform/roles');
    expect(roles?.canActivate).toContain(platformAdminGuard);
    expect(roles?.loadComponent).toBeDefined();
  });

  it('protects platform AI configuration with the platform administrator guard', () => {
    const ai = routes.find((route) => route.path === 'platform/ai');
    expect(ai?.canActivate).toContain(platformAdminGuard);
    expect(ai?.loadComponent).toBeDefined();
  });
});
