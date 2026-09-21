import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { TokenService } from '../services/token.service';
import { authGuard } from './auth.guard';

describe('authGuard role restrictions', () => {
  let token: string | null;
  const denied = {} as UrlTree;
  beforeEach(() => {
    token = null;
    TestBed.configureTestingModule({providers: [
      {provide: TokenService, useValue: {hasToken: () => !!token, getToken: () => token}},
      {provide: Router, useValue: {createUrlTree: () => denied}}
    ]});
  });
  for (const role of ['CLIENTE', 'CAJERO', 'ENCARGADO_SUCURSAL', 'ADMINISTRADOR']) {
    it(`restricts inventory access for ${role}`, () => {
      token = `x.${btoa(JSON.stringify({rol: role}))}.x`;
      const result = TestBed.runInInjectionContext(() => authGuard(
        {data: {roles: ['ENCARGADO_SUCURSAL', 'ADMINISTRADOR']}} as never, {} as never));
      expect(result).toBe(['ENCARGADO_SUCURSAL', 'ADMINISTRADOR'].includes(role) ? true : denied);
    });
  }
  it('denies unauthenticated access', () => {
    expect(TestBed.runInInjectionContext(() => authGuard({data: {}} as never, {} as never))).toBe(denied);
  });
});
