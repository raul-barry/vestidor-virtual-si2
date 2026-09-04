import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { VariantAdminService } from './variant-admin.service';
describe('VariantAdminService',()=>{let service:VariantAdminService;let http:HttpTestingController;beforeEach(()=>{TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});service=TestBed.inject(VariantAdminService);http=TestBed.inject(HttpTestingController)});afterEach(()=>http.verify());it('creates and updates variants',()=>{service.create(1,{sku:'SKU',id_talla:1,id_color:2}).subscribe();let req=http.expectOne('http://localhost:8000/api/admin/products/1/variants');expect(req.request.method).toBe('POST');req.flush({});service.update(2,{sku:'SKU2'}).subscribe();req=http.expectOne('http://localhost:8000/api/admin/variants/2');expect(req.request.method).toBe('PUT');req.flush({})})});
