import { Routes } from '@angular/router';
import { adminGuard } from '../../core/guards/admin.guard';
import { AdminLayoutComponent } from './layouts/admin-layout/admin-layout.component';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    component: AdminLayoutComponent,
    canActivateChild: [adminGuard],
    children: [
      { path: 'security', data: {mode: 'security'}, loadComponent: () => import('../experience/experience.component').then(c => c.ExperienceComponent) },
      ...['cities', 'suppliers', 'collections', 'promotions', 'returns', 'audit'].map(mode => ({ path: mode, data: {mode}, loadComponent: () => import('../commerce/commerce.component').then(c => c.CommerceComponent) })),
      { path: 'categories', loadComponent: () => import('./pages/categories/category-list.component').then(c => c.CategoryListComponent) },
      { path: 'sizes', loadComponent: () => import('./pages/sizes/size-list.component').then(c => c.SizeListComponent) },
      { path: 'colors', loadComponent: () => import('./pages/colors/color-list.component').then(c => c.ColorListComponent) },
      { path: 'branches', loadComponent: () => import('./pages/branches/branch-list.component').then(c => c.BranchListComponent) },
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
