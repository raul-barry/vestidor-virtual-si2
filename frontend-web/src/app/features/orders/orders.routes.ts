import { Routes } from '@angular/router';

export const ORDER_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./pages/order-history/order-history.component').then(
      (component) => component.OrderHistoryComponent
    )
  },
  {
    path: 'detail/:id',
    loadComponent: () => import('./pages/order-detail/order-detail.component').then(
      (component) => component.OrderDetailComponent
    )
  }
];
