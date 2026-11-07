import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { CartService } from '../../../cart/services/cart.service';
import { OrderService } from '../../services/order.service';
import { CheckoutComponent } from './checkout.component';
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';

describe('CheckoutComponent', () => {
  let component: CheckoutComponent;
  let fixture: ComponentFixture<CheckoutComponent>;
  let cartService: jasmine.SpyObj<CartService>;
  let orderService: jasmine.SpyObj<OrderService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let localCart: any | null;
  let offlineModified = false;
  let saveLocalCart: jasmine.Spy;

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
    orderService = jasmine.createSpyObj<OrderService>('OrderService', ['createOrder', 'getDeliveryBranches']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    localCart = null;
    offlineModified = false;
    saveLocalCart = jasmine.createSpy('saveLocalCart').and.callFake(async () => undefined);
    cartService.getCart.and.returnValue(of(cart));
    orderService.getDeliveryBranches.and.returnValue(of([{ id_sucursal: 1, nombre: 'Central', direccion: 'Centro' }]));

    TestBed.configureTestingModule({
      imports: [CheckoutComponent, NoopAnimationsModule],
      providers: [
        { provide: CartService, useValue: cartService },
        { provide: OrderService, useValue: orderService },
        { provide: OutboxSyncService, useValue: { summary$: of(null), saveLocalCart, localCart: async () => localCart, isOfflineModifiedCart: (value: any) => offlineModified && !!value?.offline_modified, localOrders: async () => [], queueOfflineSale: async () => ({}), syncPending: async () => {} } },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(CheckoutComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(CheckoutComponent);
    component = fixture.componentInstance;
  });

  it('renders the cart summary', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    component.deliveryForm.controls.id_sucursal_entrega.setValue(1);

    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('500.00');
  });

  it('creates an order successfully', async () => {
    orderService.createOrder.and.returnValue(of({ id_pedido: 1, estado: 'PENDIENTE', total: '500.00' }));
    fixture.detectChanges();
    await fixture.whenStable();
    component.deliveryForm.controls.id_sucursal_entrega.setValue(1);

    component.createOrder();

    expect(orderService.createOrder).toHaveBeenCalledWith({ tipo_entrega: 'RECOJO_SUCURSAL', id_sucursal_entrega: 1 });
    expect(component.createdOrder?.id_pedido).toBe(1);
  });

  it('shows an API error when order creation fails', async () => {
    orderService.createOrder.and.returnValue(throwError(() => new Error('Network error')));
    fixture.detectChanges();
    await fixture.whenStable();
    component.deliveryForm.controls.id_sucursal_entrega.setValue(1);

    component.createOrder();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible crear el pedido', 'Cerrar', {
      duration: 5000
    });
  });

  it('retains an offline-modified cart when checkout is opened after reconnecting', async () => {
    const offline = { ...cart, estado: 'LOCAL', offline_modified: true };
    cartService.getCart.and.returnValue(of({ id_carrito: 2, estado: 'ACTIVO', items: [], total: '0.00' }));
    localCart = offline;
    offlineModified = true;
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.cart).toBe(offline);
    expect(component.offlineCart).toBeTrue();
    expect(saveLocalCart).not.toHaveBeenCalled();
  });
});
