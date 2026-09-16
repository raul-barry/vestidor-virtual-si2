import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  ...['recommendations', 'fitting'].map(mode => ({path: 'experience/' + mode, canActivate: [authGuard], data: {mode}, loadComponent: () => import('./features/experience/experience.component').then(c => c.ExperienceComponent)})),
  ...['recommendations', 'fitting'].map(mode => ({path: mode, canActivate: [authGuard], data: {mode}, loadComponent: () => import('./features/experience/experience.component').then(c => c.ExperienceComponent)})),
  { path: 'pos', canActivate: [authGuard], data: {mode: 'pos'}, loadComponent: () => import('./features/commerce/commerce.component').then(c => c.CommerceComponent) },
  { path: 'reservations', canActivate: [authGuard], loadComponent: () => import('./features/reservations/reservations.component').then(c => c.ReservationsComponent) },
  { path: 'inventory', canActivate: [authGuard], loadComponent: () => import('./features/admin/pages/inventory/inventory-list/inventory-list.component').then(c => c.InventoryListComponent) },
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
    loadChildren: () => import('./features/cart/cart.routes').then((routes) => routes.CART_ROUTES)
  },
  {
    path: 'checkout',
    canActivate: [authGuard],
    loadComponent: () => import('./features/orders/pages/checkout/checkout.component').then(
      (component) => component.CheckoutComponent
    )
  },
  {
    path: 'orders',
    canActivate: [authGuard],
    loadChildren: () => import('./features/orders/orders.routes').then((routes) => routes.ORDER_ROUTES)
  },
  {
    path: 'payments',
    canActivate: [authGuard],
    loadChildren: () => import('./features/payments/payments.routes').then((routes) => routes.PAYMENT_ROUTES)
  },
  {
    path: 'admin',
    canActivate: [adminGuard],
    loadChildren: () => import('./features/admin/admin.routes').then((routes) => routes.ADMIN_ROUTES)
  },
{
  path: '',
  pathMatch: 'full',
  redirectTo: 'auth/login'
},
{
  path: '**',
  redirectTo: 'auth/login'
}];
