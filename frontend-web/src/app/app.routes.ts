import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
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
