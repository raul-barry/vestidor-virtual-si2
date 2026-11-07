import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { CartService } from '../../services/cart.service';
import { CartViewComponent } from './cart-view.component';
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';

describe('CartViewComponent', () => {
  let component: CartViewComponent;
  let fixture: ComponentFixture<CartViewComponent>;
  let cartService: jasmine.SpyObj<CartService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let router: jasmine.SpyObj<Router>;
  let outbox: any;

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
    cartService = jasmine.createSpyObj<CartService>('CartService', ['getCart', 'updateQuantity', 'removeItem']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    outbox = {
      saveLocalCart: jasmine.createSpy('saveLocalCart').and.callFake(async () => undefined),
      localCart: jasmine.createSpy('localCart').and.callFake(async () => null),
      updateOfflineCartItem: jasmine.createSpy('updateOfflineCartItem').and.callFake(async () => cart),
      isOfflineModifiedCart: jasmine.createSpy('isOfflineModifiedCart').and.callFake((value: any) => !!value?.offline_modified)
    };
    cartService.getCart.and.returnValue(of(cart));

    TestBed.configureTestingModule({
      imports: [CartViewComponent, NoopAnimationsModule],
      providers: [
        { provide: CartService, useValue: cartService },
        { provide: OutboxSyncService, useValue: outbox },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: Router, useValue: router }
      ]
    }).overrideComponent(CartViewComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(CartViewComponent);
    component = fixture.componentInstance;
  });

  it('renders the loaded cart', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(cartService.getCart).toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('500.00');
  });

  it('updates an item quantity', async () => {
    cartService.updateQuantity.and.returnValue(of({ ...cart, total: '750.00' }));
    fixture.detectChanges();
    await fixture.whenStable();

    component.updateQuantity(cart.items[0], 3);

    expect(cartService.updateQuantity).toHaveBeenCalledWith(1, 3);
    expect(component.cart?.total).toBe('750.00');
  });

  it('removes an item from the cart', async () => {
    cartService.removeItem.and.returnValue(of({ ...cart, items: [], total: '0' }));
    fixture.detectChanges();
    await fixture.whenStable();

    component.removeItem(cart.items[0]);

    expect(cartService.removeItem).toHaveBeenCalledWith(1);
    expect(component.cart?.items).toEqual([]);
  });

  it('navigates to checkout', () => {
    component.checkout();

    expect(router.navigate).toHaveBeenCalledWith(['/checkout']);
  });

  it('keeps the locally modified cart after reconnecting to an empty server cart', async () => {
    const local = { ...cart, estado: 'LOCAL', offline_modified: true };
    cartService.getCart.and.returnValue(of({ id_carrito: 2, estado: 'ACTIVO', items: [], total: '0.00' }));
    outbox.localCart.and.callFake(async () => local);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.cart).toBe(local);
    expect(component.offline).toBeTrue();
    expect(outbox.saveLocalCart).not.toHaveBeenCalled();
  });
});
