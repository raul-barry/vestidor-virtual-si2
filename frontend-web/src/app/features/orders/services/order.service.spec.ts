import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OrderService } from './order.service';

describe('OrderService', () => {
  let service: OrderService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(OrderService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates an order from the active cart', () => {
    service.createOrder({ tipo_entrega: 'RECOJO_SUCURSAL', id_sucursal_entrega: 1 }).subscribe();
    const request = http.expectOne('http://localhost:8000/api/orders');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ tipo_entrega: 'RECOJO_SUCURSAL', id_sucursal_entrega: 1 });
    request.flush({ id_pedido: 1, estado: 'PENDIENTE', total: '500.00' });
  });

  it('gets client orders', () => {
    service.getOrders().subscribe((orders) => expect(orders).toHaveSize(1));
    const request = http.expectOne('http://localhost:8000/api/orders');
    expect(request.request.method).toBe('GET');
    request.flush([{ id_pedido: 1, fecha_pedido: '2026-09-02T00:00:00Z', estado: 'PENDIENTE', total: '500.00' }]);
  });
});
