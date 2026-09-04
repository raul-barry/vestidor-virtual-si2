import { Routes } from '@angular/router';
import { adminGuard } from '../../core/guards/admin.guard';
import { AdminLayoutComponent } from './layouts/admin-layout/admin-layout.component';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminLayoutComponent,
    canActivateChild: [adminGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./pages/dashboard/dashboard.component').then(
          (component) => component.DashboardComponent
        )
      },
      { path: 'products', pathMatch: 'full', loadComponent: () => import('./pages/products/product-list/product-list.component').then(c => c.ProductListComponent) },
      { path: 'products/create', loadComponent: () => import('./pages/products/product-form/product-form.component').then(c => c.ProductFormComponent) },
      { path: 'products/edit/:id', loadComponent: () => import('./pages/products/product-form/product-form.component').then(c => c.ProductFormComponent) },
      { path: 'variants', loadComponent: () => import('./pages/variants/variant-list/variant-list.component').then(c => c.VariantListComponent) },
      { path: 'inventory', loadComponent: () => import('./pages/inventory/inventory-list/inventory-list.component').then(c => c.InventoryListComponent) },
      { path: 'orders', pathMatch: 'full', loadComponent: () => import('./pages/orders/order-list/order-list.component').then(c => c.OrderListComponent) },
      { path: 'orders/detail/:id', loadComponent: () => import('./pages/orders/order-detail/order-detail.component').then(c => c.OrderDetailComponent) },
      { path: 'users', pathMatch: 'full', loadComponent: () => import('./pages/users/user-list/user-list.component').then(c => c.UserListComponent) },
      { path: 'users/detail/:id', loadComponent: () => import('./pages/users/user-detail/user-detail.component').then(c => c.UserDetailComponent) },
      { path: 'reports', loadComponent: () => import('./pages/reports/reports.component').then(c => c.ReportsComponent) },
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' }
    ]
  }
];
