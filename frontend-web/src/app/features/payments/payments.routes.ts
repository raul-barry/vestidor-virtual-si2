import { Routes } from '@angular/router';

export const PAYMENT_ROUTES: Routes = [
  {
    path: ':id_pedido',
    loadComponent: () => import('./pages/payment/payment.component').then((component) => component.PaymentComponent)
  }
];
