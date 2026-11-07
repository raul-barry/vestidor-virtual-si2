import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { platformAdminGuard } from './core/guards/platform-admin.guard';

export const routes: Routes = [
  { path: 'admin/exchanges', canActivate: [authGuard], data: {roles: ['ADMINISTRADOR', 'ENCARGADO_SUCURSAL']}, loadComponent: () => import('./features/admin/pages/exchanges/exchange-management.component').then(c => c.ExchangeManagementComponent) },
  ...['recommendations', 'fitting'].map(mode => ({path: 'experience/' + mode, canActivate: [authGuard], data: {mode}, loadComponent: () => import('./features/experience/experience.component').then(c => c.ExperienceComponent)})),
  ...['recommendations', 'fitting'].map(mode => ({path: mode, canActivate: [authGuard], data: {mode}, loadComponent: () => import('./features/experience/experience.component').then(c => c.ExperienceComponent)})),
  { path: 'pos', canActivate: [authGuard], data: {roles: ['ADMINISTRADOR', 'CAJERO']}, loadComponent: () => import('./features/commerce/pos.component').then(c => c.PosComponent) },
  { path: 'reservations', canActivate: [authGuard], data: {roles: ['CLIENTE', 'ADMINISTRADOR', 'ENCARGADO_SUCURSAL']}, loadComponent: () => import('./features/reservations/reservations.component').then(c => c.ReservationsComponent) },
  { path: 'inventory', canActivate: [authGuard], data: {roles: ['ADMINISTRADOR', 'ENCARGADO_SUCURSAL']}, loadComponent: () => import('./features/admin/pages/inventory/inventory-list/inventory-list.component').then(c => c.InventoryListComponent) },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then((routes) => routes.AUTH_ROUTES)
  },
  {
    path: 'profile',
    canActivate: [authGuard],
    loadChildren: () => import('./features/profile/profile.routes').then((routes) => routes.PROFILE_ROUTES)
  },
  {
    path: 'catalog',
    loadChildren: () => import('./features/catalog/catalog.routes').then((routes) => routes.CATALOG_ROUTES)
  },
  {
    path: 'cart',
    canActivate: [authGuard],
    data: {roles: ['CLIENTE']},
    loadChildren: () => import('./features/cart/cart.routes').then((routes) => routes.CART_ROUTES)
  },
  {
    path: 'checkout',
    canActivate: [authGuard],
    data: {roles: ['CLIENTE']},
    loadComponent: () => import('./features/orders/pages/checkout/checkout.component').then(
      (component) => component.CheckoutComponent
    )
  },
  {
    path: 'orders',
    canActivate: [authGuard],
    data: {roles: ['CLIENTE']},
    loadChildren: () => import('./features/orders/orders.routes').then((routes) => routes.ORDER_ROUTES)
  },
  {
    path: 'payments',
    canActivate: [authGuard],
    data: {roles: ['CLIENTE']},
    loadChildren: () => import('./features/payments/payments.routes').then((routes) => routes.PAYMENT_ROUTES)
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadChildren: () => import('./features/admin/admin.routes').then((routes) => routes.ADMIN_ROUTES)
  },
  { path: 'platform/organizations', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/organizations/organization-list.component').then(c => c.OrganizationListComponent) },
  { path: 'platform/organizations/provision', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/organizations/tenant-provisioning.component').then(c => c.TenantProvisioningComponent) },
  { path: 'platform/organizations/:id', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/organizations/organization-detail.component').then(c => c.OrganizationDetailComponent) },
  { path: 'platform/subscriptions', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/organizations/subscription-management.component').then(c => c.SubscriptionManagementComponent) },
  { path: 'platform/plans', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/organizations/commercial-plan-management.component').then(c => c.CommercialPlanManagementComponent) },
  { path: 'platform/security', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/security-overview.component').then(c => c.SecurityOverviewComponent) },
  { path: 'platform/roles', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/roles/role-list.component').then(c => c.RoleListComponent) },
  { path: 'platform/ai', canActivate: [platformAdminGuard], loadComponent: () => import('./features/admin/pages/platform-ai-settings.component').then(c => c.PlatformAISettingsComponent) },
{
  path: '',
  pathMatch: 'full',
  redirectTo: 'catalog'
},
{
  path: '**',
  redirectTo: 'catalog'
}];
