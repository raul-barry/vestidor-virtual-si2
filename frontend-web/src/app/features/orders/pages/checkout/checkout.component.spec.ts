import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { CartService } from '../../../cart/services/cart.service';
import { OrderService } from '../../services/order.service';
import { CheckoutComponent } from './checkout.component';

describe('CheckoutComponent', () => {
  let component: CheckoutComponent;
  let fixture: ComponentFixture<CheckoutComponent>;
  let cartService: jasmine.SpyObj<CartService>;
  let orderService: jasmine.SpyObj<OrderService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  const cart = {
    id_carrito: 1,
    estado: 'ACTIVO',
    items: [{
      id_detalle: 1,
      producto: 'Camisa Oxford',
      talla: 'M',
      color: 'Blanco',
      cantidad: 2,
      precio_unitario: '250.00'
    }],
    total: '500.00'
  };

  beforeEach(async () => {
    cartService = jasmine.createSpyObj<CartService>('CartService', ['getCart']);
    orderService = jasmine.createSpyObj<OrderService>('OrderService', ['createOrder']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    cartService.getCart.and.returnValue(of(cart));

    TestBed.configureTestingModule({
      imports: [CheckoutComponent, NoopAnimationsModule],
      providers: [
        { provide: CartService, useValue: cartService },
        { provide: OrderService, useValue: orderService },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(CheckoutComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(CheckoutComponent);
    component = fixture.componentInstance;
  });

  it('renders the cart summary', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('500.00');
  });

  it('creates an order successfully', () => {
    orderService.createOrder.and.returnValue(of({ id_pedido: 1, estado: 'PENDIENTE', total: '500.00' }));
    fixture.detectChanges();

    component.createOrder();

    expect(orderService.createOrder).toHaveBeenCalled();
    expect(component.createdOrder?.id_pedido).toBe(1);
  });

  it('shows an API error when order creation fails', () => {
    orderService.createOrder.and.returnValue(throwError(() => new Error('Network error')));
    fixture.detectChanges();

    component.createOrder();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible crear el pedido', 'Cerrar', {
      duration: 5000
    });
  });
});
