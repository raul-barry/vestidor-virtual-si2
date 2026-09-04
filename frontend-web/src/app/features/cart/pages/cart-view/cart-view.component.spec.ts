import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { CartService } from '../../services/cart.service';
import { CartViewComponent } from './cart-view.component';

describe('CartViewComponent', () => {
  let component: CartViewComponent;
  let fixture: ComponentFixture<CartViewComponent>;
  let cartService: jasmine.SpyObj<CartService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  let router: jasmine.SpyObj<Router>;

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
    cartService.getCart.and.returnValue(of(cart));

    TestBed.configureTestingModule({
      imports: [CartViewComponent, NoopAnimationsModule],
      providers: [
        { provide: CartService, useValue: cartService },
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

  it('renders the loaded cart', () => {
    fixture.detectChanges();

    expect(cartService.getCart).toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('500.00');
  });

  it('updates an item quantity', () => {
    cartService.updateQuantity.and.returnValue(of({ ...cart, total: '750.00' }));
    fixture.detectChanges();

    component.updateQuantity(cart.items[0], 3);

    expect(cartService.updateQuantity).toHaveBeenCalledWith(1, 3);
    expect(component.cart?.total).toBe('750.00');
  });

  it('removes an item from the cart', () => {
    cartService.removeItem.and.returnValue(of({ ...cart, items: [], total: '0' }));
    fixture.detectChanges();

    component.removeItem(cart.items[0]);

    expect(cartService.removeItem).toHaveBeenCalledWith(1);
    expect(component.cart?.items).toEqual([]);
  });

  it('navigates to checkout', () => {
    component.checkout();

    expect(router.navigate).toHaveBeenCalledWith(['/checkout']);
  });
});
