import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { OrderService } from '../../../orders/services/order.service';
import { PaymentService } from '../../services/payment.service';
import { PaymentComponent } from './payment.component';

describe('PaymentComponent', () => {
  let component: PaymentComponent;
  let fixture: ComponentFixture<PaymentComponent>;
  let paymentService: jasmine.SpyObj<PaymentService>;

  beforeEach(async () => {
    paymentService = jasmine.createSpyObj<PaymentService>('PaymentService', ['getPaymentByOrder', 'createPayment']);
    const orderService = jasmine.createSpyObj<OrderService>('OrderService', ['getOrderDetail']);
    orderService.getOrderDetail.and.returnValue(of({ id_pedido: 1, estado: 'PENDIENTE', total: '500.00', detalles: [] }));
    paymentService.getPaymentByOrder.and.returnValue(throwError(() => ({ status: 404 })));

    TestBed.configureTestingModule({
      imports: [PaymentComponent, NoopAnimationsModule],
      providers: [
        { provide: OrderService, useValue: orderService },
        { provide: PaymentService, useValue: paymentService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
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

  it('creates a payment with the selected method', () => {
    paymentService.createPayment.and.returnValue(of({
      id_pago: 1, id_pedido: 1, metodo_pago: 'TARJETA', monto: '500.00', estado: 'PENDIENTE', fecha_pago: '2026-09-02T00:00:00Z'
    }));
    fixture.detectChanges();
    component.paymentForm.controls.metodo_pago.setValue('TARJETA');

    component.createPayment();

    expect(paymentService.createPayment).toHaveBeenCalledWith(1, 'TARJETA');
    expect(component.payment?.id_pago).toBe(1);
  });
});
