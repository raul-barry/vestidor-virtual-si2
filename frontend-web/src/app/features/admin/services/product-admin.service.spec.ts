import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ProductAdminService } from './product-admin.service';

describe('ProductAdminService', () => {
  let service: ProductAdminService; let http: HttpTestingController;
  beforeEach(() => { TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]}); service=TestBed.inject(ProductAdminService); http=TestBed.inject(HttpTestingController); });
  afterEach(() => http.verify());
  it('creates a product',()=>{service.create({nombre:'Camisa',precio_base:250,id_categoria:1}).subscribe();const req=http.expectOne('http://localhost:8000/api/admin/products');expect(req.request.method).toBe('POST');req.flush({});});
  it('updates and disables a product',()=>{service.update(1,{nombre:'Camisa Premium'}).subscribe();let req=http.expectOne('http://localhost:8000/api/admin/products/1');expect(req.request.method).toBe('PUT');req.flush({});service.disable(1).subscribe();req=http.expectOne('http://localhost:8000/api/admin/products/1');expect(req.request.method).toBe('DELETE');req.flush({});});
});
