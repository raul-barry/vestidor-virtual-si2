import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { PaymentService } from './payment.service';

describe('PaymentService', () => {
  let service: PaymentService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PaymentService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('creates a payment', () => {
    service.createPayment(1, 'QR').subscribe();
    const request = http.expectOne('http://localhost:8000/api/payments');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id_pedido: 1, metodo_pago: 'QR' });
    request.flush({});
  });

  it('gets a payment by order', () => {
    service.getPaymentByOrder(1).subscribe();
    const request = http.expectOne('http://localhost:8000/api/payments/order/1');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });

  it('creates a Stripe intent and reads its final status', () => {
    service.createStripeIntent(1).subscribe();
    const intent = http.expectOne('http://localhost:8000/api/payments/stripe/create-intent');
    expect(intent.request.method).toBe('POST');
    expect(intent.request.body).toEqual({ id_pedido: 1 });
    intent.flush({});

    service.getPaymentStatus(1).subscribe();
    const status = http.expectOne('http://localhost:8000/api/payments/1/status');
    expect(status.request.method).toBe('GET');
    status.flush({});
  });

  it('uses the protected QR endpoint rather than creating a fake QR', () => {
    service.createQrPayment(1).subscribe();
    const request = http.expectOne('http://localhost:8000/api/payments/qr');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id_pedido: 1, metodo_pago: 'QR' });
    request.flush({});
  });

  it('approves a payment', () => {
    service.approvePayment(1).subscribe();
    const request = http.expectOne('http://localhost:8000/api/payments/1/approve');
    expect(request.request.method).toBe('PUT');
    request.flush({});
  });

  it('rejects a payment', () => {
    service.rejectPayment(1).subscribe();
    const request = http.expectOne('http://localhost:8000/api/payments/1/reject');
    expect(request.request.method).toBe('PUT');
    request.flush({});
  });
});
