import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { Stripe, StripeElements } from '@stripe/stripe-js';
import { of, throwError } from 'rxjs';
import { OrderService } from '../../../orders/services/order.service';
import { PaymentService } from '../../services/payment.service';
import { PaymentComponent } from './payment.component';

describe('PaymentComponent', () => {
  let component: PaymentComponent;
  let fixture: ComponentFixture<PaymentComponent>;
  let paymentService: jasmine.SpyObj<PaymentService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    paymentService = jasmine.createSpyObj<PaymentService>('PaymentService', ['getPaymentByOrder', 'createPayment', 'createStripeIntent', 'createQrPayment', 'confirmQrPayment', 'getPaymentStatus', 'approvePayment']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    const orderService = jasmine.createSpyObj<OrderService>('OrderService', ['getOrderDetail']);
    orderService.getOrderDetail.and.returnValue(of({ id_pedido: 1, estado: 'PENDIENTE', total: '500.00', detalles: [] }));
    paymentService.getPaymentByOrder.and.returnValue(throwError(() => ({ status: 404 })));

    TestBed.configureTestingModule({
      imports: [PaymentComponent, NoopAnimationsModule],
      providers: [
        { provide: OrderService, useValue: orderService },
        { provide: PaymentService, useValue: paymentService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id_pedido: '1' }) } } }
      ]
    });
    await TestBed.compileComponents();
    fixture = TestBed.createComponent(PaymentComponent);
    component = fixture.componentInstance;
  });

  it('renders the payment form when no payment exists', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Método de pago');
  });

  it('creates a Stripe intent with the selected card method', () => {
    paymentService.createStripeIntent.and.returnValue(of({
      client_secret: 'secret_mock', publishable_key: '', payment: {
        id_pago: 1, id_pedido: 1, metodo_pago: 'TARJETA', monto: '500.00', estado: 'PENDIENTE', fecha_pago: '2026-09-02T00:00:00Z'
      }
    }));
    fixture.detectChanges();
    component.paymentForm.controls.metodo_pago.setValue('TARJETA');

    component.createPayment();

    expect(paymentService.createStripeIntent).toHaveBeenCalledWith(1);
    expect(component.payment?.id_pago).toBe(1);
  });

  it('shows the controlled message when Stripe has no publishable key', () => {
    const internals = component as unknown as {
      cardClientSecret: string;
      mountStripeElement: (key: string) => void;
    };
    internals.cardClientSecret = 'secret_mock';
    fixture.detectChanges();

    internals.mountStripeElement('');

    expect(component.cardReady).toBeFalse();
  });

  it('mounts a mocked Stripe Payment Element', async () => {
    const mount = jasmine.createSpy('mount');
    const create = jasmine.createSpy('create').and.returnValue({ mount });
    const elements = { create } as unknown as StripeElements;
    const stripe = { elements: jasmine.createSpy('elements').and.returnValue(elements) } as unknown as Stripe;
    const internals = component as unknown as {
      cardClientSecret: string;
      paymentElement: { nativeElement: HTMLDivElement };
      stripeLoader: (key: string) => Promise<Stripe | null>;
      mountStripeElement: (key: string) => void;
    };
    internals.cardClientSecret = 'secret_mock';
    internals.paymentElement = { nativeElement: document.createElement('div') };
    internals.stripeLoader = () => Promise.resolve(stripe);
    spyOn(window, 'setTimeout').and.callFake(((handler: TimerHandler) => {
      (handler as () => void)();
      return 0;
    }) as typeof window.setTimeout);

    internals.mountStripeElement('pk_test_mock');
    await Promise.resolve();

    expect(create).toHaveBeenCalledWith('payment');
    expect(mount).toHaveBeenCalled();
  });

  it('confirms a mocked card payment and polls its final state', async () => {
    const confirmPayment = jasmine.createSpy('confirmPayment').and.resolveTo({});
    const internals = component as unknown as { stripe: Stripe; elements: StripeElements };
    internals.stripe = { confirmPayment } as unknown as Stripe;
    internals.elements = {} as StripeElements;
    paymentService.getPaymentStatus.and.returnValue(of({
      payment: { id_pago: 1, id_pedido: 1, metodo_pago: 'TARJETA', monto: '500.00', estado: 'PAGADO', fecha_pago: '2026-09-02T00:00:00Z' },
      order_status: 'CONFIRMADO'
    }));
    fixture.detectChanges();

    await component.confirmCardPayment();

    expect(confirmPayment).toHaveBeenCalled();
    expect(paymentService.getPaymentStatus).toHaveBeenCalledWith(1);
    expect(component.payment?.estado).toBe('PAGADO');
  });
});
