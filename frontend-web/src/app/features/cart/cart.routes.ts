import { Routes } from '@angular/router';

export const CART_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./pages/cart-view/cart-view.component').then(
      (component) => component.CartViewComponent
    )
  }
];
