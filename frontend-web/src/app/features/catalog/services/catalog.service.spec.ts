import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CatalogService } from './catalog.service';
import { PublicOrganizationContextService } from './public-organization-context.service';

describe('CatalogService tenant context', () => {
  let api: jasmine.SpyObj<ApiService>;
  let context: { isAuthenticated: boolean; publicSlug: string | null; canLoadCatalog: boolean };
  let service: CatalogService;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get']);
    api.get.and.returnValue(of([]));
    context = { isAuthenticated: false, publicSlug: 'urbanvogue', canLoadCatalog: true };
    TestBed.configureTestingModule({ providers: [
      CatalogService,
      { provide: ApiService, useValue: api },
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
});
