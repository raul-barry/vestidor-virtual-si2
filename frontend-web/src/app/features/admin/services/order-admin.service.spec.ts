import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OrderAdminService } from './order-admin.service';
describe('OrderAdminService',()=>{let service:OrderAdminService;let http:HttpTestingController;beforeEach(()=>{TestBed.configureTestingModule({providers:[provideHttpClient(),provideHttpClientTesting()]});service=TestBed.inject(OrderAdminService);http=TestBed.inject(HttpTestingController)});afterEach(()=>http.verify());it('gets and updates orders',()=>{service.getOrders({estado:'PENDIENTE'}).subscribe();let r=http.expectOne('http://localhost:8000/api/admin/orders?estado=PENDIENTE');expect(r.request.method).toBe('GET');r.flush([]);service.updateStatus(1,{estado:'CONFIRMADO'}).subscribe();r=http.expectOne('http://localhost:8000/api/admin/orders/1/status');expect(r.request.method).toBe('PUT');r.flush({})})});
