import { Routes } from '@angular/router';

export const CATALOG_ROUTES: Routes = [
  {
    path: 'product/:id',
    loadComponent: () => import('./pages/product-detail/product-detail.component').then(
      (component) => component.ProductDetailComponent
    )
  },
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./pages/catalog-list/catalog-list.component').then(
      (component) => component.CatalogListComponent
    )
  }
];
