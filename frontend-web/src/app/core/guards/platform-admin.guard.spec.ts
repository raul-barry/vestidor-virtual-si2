import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { TokenService } from '../services/token.service';
import { platformAdminGuard } from './platform-admin.guard';

describe('platformAdminGuard', () => {
  let token: string | null;
  const denied = {} as UrlTree;
  const login = {} as UrlTree;
  beforeEach(() => {
    token = null;
    TestBed.configureTestingModule({ providers: [
      { provide: TokenService, useValue: { getToken: () => token } },
      { provide: Router, useValue: { createUrlTree: (path: string[]) => path[0] === '/auth/login' ? login : denied } }
    ] });
  });
  it('allows platform administrators', () => {
    token = `x.${btoa(JSON.stringify({ rol: 'ADMINISTRADOR_PLATAFORMA' }))}.x`;
    expect(TestBed.runInInjectionContext(() => platformAdminGuard({} as never, {} as never))).toBeTrue();
  });
  for (const role of ['ADMINISTRADOR', 'ENCARGADO_SUCURSAL', 'CLIENTE']) {
    it(`denies ${role}`, () => {
      token = `x.${btoa(JSON.stringify({ rol: role }))}.x`;
      expect(TestBed.runInInjectionContext(() => platformAdminGuard({} as never, {} as never))).toBe(denied);
    });
  }
  it('sends unauthenticated users to login', () => {
    expect(TestBed.runInInjectionContext(() => platformAdminGuard({} as never, {} as never))).toBe(login);
  });
});
