import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CatalogService } from './catalog.service';
import { PublicOrganizationContextService } from './public-organization-context.service';
import { CatalogOfflineStore } from './catalog-offline.store';

describe('CatalogService tenant context', () => {
  let api: jasmine.SpyObj<ApiService>;
  let context: { isAuthenticated: boolean; publicSlug: string | null; canLoadCatalog: boolean };
  let service: CatalogService;
  let offlineStore: jasmine.SpyObj<any>;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get']);
    api.get.and.returnValue(of([]));
    offlineStore = jasmine.createSpyObj('CatalogOfflineStore', ['get', 'put']);
    offlineStore.get.and.resolveTo({ key: 'slug:urbanvogue', products: [{
      id_producto: 9, nombre: 'Camisa Urban', descripcion: null, precio_base: '30.00', estado: 'ACTIVO',
      categoria: { id_categoria: 1, nombre: 'Camisas' }, variantes: []
    }], syncedAt: 123 });
    context = { isAuthenticated: false, publicSlug: 'urbanvogue', canLoadCatalog: true };
    TestBed.configureTestingModule({ providers: [
      CatalogService,
      { provide: ApiService, useValue: api },
      { provide: CatalogOfflineStore, useValue: offlineStore },
      { provide: PublicOrganizationContextService, useValue: context }
    ] });
    service = TestBed.inject(CatalogService);
  });

  it('uses a public slug for products, search, variants and availability', () => {
    service.getProducts().subscribe();
    service.searchProducts({ nombre: 'camisa', precio_max: 300 }).subscribe();
    service.getProductVariants(7).subscribe();
    service.getProductAvailability(7).subscribe();
    expect(api.get.calls.allArgs().map(([url]) => url)).toEqual([
      '/api/catalog/products?organization_slug=urbanvogue',
      '/api/catalog/products/search?organization_slug=urbanvogue&nombre=camisa&precio_max=300',
      '/api/catalog/products/7/variants?organization_slug=urbanvogue',
      '/api/catalog/products/7/availability?organization_slug=urbanvogue'
    ]);
  });

  it('does not include a user-selected tenant in authenticated requests', () => {
    context.isAuthenticated = true;
    context.publicSlug = 'elegance-boutique';
    service.getProducts().subscribe();
    service.getProductVariants(3).subscribe();
    expect(api.get.calls.allArgs().map(([url]) => url)).toEqual([
      '/api/catalog/products?',
      '/api/catalog/products/3/variants?'
    ]);
  });

  it('fails closed when a public slug is absent', () => {
    context.publicSlug = null;
    expect(() => service.getProducts()).toThrowError(/organization_slug/);
    expect(api.get).not.toHaveBeenCalled();
  });

  it('falls back to the selected tenant snapshot when online search cannot reach the API', (done) => {
    api.get.and.returnValue(throwError(() => ({ status: 0 })));
    service.searchProducts({ nombre: 'urban' }).subscribe(products => {
      expect(products.map(product => product.id_producto)).toEqual([9]);
      expect(service.servingOfflineData).toBeTrue();
      done();
    });
  });
});
