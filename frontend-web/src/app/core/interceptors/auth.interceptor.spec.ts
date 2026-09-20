import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { TokenService } from '../services/token.service';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let testing: HttpTestingController;
  let tokenService: jasmine.SpyObj<TokenService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    tokenService = jasmine.createSpyObj<TokenService>('TokenService', ['getToken', 'clearToken']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    Object.defineProperty(router, 'url', { value: '/cart', configurable: true });
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenService },
        { provide: Router, useValue: router }
      ]
    });
    http = TestBed.inject(HttpClient);
    testing = TestBed.inject(HttpTestingController);
  });

  afterEach(() => testing.verify());

  it('adds Bearer to protected requests', () => {
    tokenService.getToken.and.returnValue('valid-token');
    http.get('/api/cart').subscribe();
    const request = testing.expectOne('/api/cart');
    expect(request.request.headers.get('Authorization')).toBe('Bearer valid-token');
    request.flush({});
  });

  it('does not add a token when no session exists', () => {
    tokenService.getToken.and.returnValue(null);
    http.get('/api/catalog/products').subscribe();
    const request = testing.expectOne('/api/catalog/products');
    expect(request.request.headers.has('Authorization')).toBeFalse();
    request.flush([]);
  });

  it('clears an invalid session and redirects once on 401', () => {
    tokenService.getToken.and.returnValue('expired-token');
    http.get('/api/profile').subscribe({ error: () => undefined });
    const request = testing.expectOne('/api/profile');
    request.flush({ detail: 'Token inválido' }, { status: 401, statusText: 'Unauthorized' });
    expect(tokenService.clearToken).toHaveBeenCalled();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login'], { queryParams: { returnUrl: '/cart' } });
  });
});
