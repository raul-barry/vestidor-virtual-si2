import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CartService } from './cart.service';

describe('CartService', () => {
  let service: CartService;
  let http: HttpTestingController;
  const cart = { id_carrito: 1, estado: 'ACTIVO', items: [], total: '0' };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(CartService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('gets the authenticated cart', () => {
    service.getCart().subscribe((response) => expect(response).toEqual(cart));
    const request = http.expectOne('http://localhost:8000/api/cart');
    expect(request.request.method).toBe('GET');
    request.flush(cart);
  });

  it('adds a cart item', () => {
    service.addItem(1, 2).subscribe();
    const request = http.expectOne('http://localhost:8000/api/cart/items');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id_variante: 1, cantidad: 2 });
    request.flush(cart);
  });

  it('updates an item quantity', () => {
    service.updateQuantity(3, 5).subscribe();
    const request = http.expectOne('http://localhost:8000/api/cart/items/3');
    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual({ cantidad: 5 });
    request.flush(cart);
  });

  it('removes an item', () => {
    service.removeItem(3).subscribe();
    const request = http.expectOne('http://localhost:8000/api/cart/items/3');
    expect(request.request.method).toBe('DELETE');
    request.flush(cart);
  });
});
