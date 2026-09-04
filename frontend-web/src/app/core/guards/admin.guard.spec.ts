import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { TokenService } from '../services/token.service';
import { adminGuard } from './admin.guard';

describe('adminGuard', () => {
  let tokenService: jasmine.SpyObj<TokenService>;
  let router: jasmine.SpyObj<Router>;

  function tokenWithRole(rol: string): string {
    return `header.${btoa(JSON.stringify({ rol }))}.signature`;
  }

  beforeEach(() => {
    tokenService = jasmine.createSpyObj<TokenService>('TokenService', ['getToken']);
    router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue({} as UrlTree);
    TestBed.configureTestingModule({
      providers: [
        { provide: TokenService, useValue: tokenService },
        { provide: Router, useValue: router }
      ]
    });
  });

  it('allows an administrator', () => {
    tokenService.getToken.and.returnValue(tokenWithRole('ADMINISTRADOR'));

    const result = TestBed.runInInjectionContext(() => adminGuard({} as never, {} as never));

    expect(result).toBeTrue();
  });

  it('blocks a customer', () => {
    tokenService.getToken.and.returnValue(tokenWithRole('CLIENTE'));

    const result = TestBed.runInInjectionContext(() => adminGuard({} as never, {} as never));

    expect(result).toBe(router.createUrlTree.calls.mostRecent().returnValue);
    expect(router.createUrlTree).toHaveBeenCalledWith(['/catalog']);
  });
});
