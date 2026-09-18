import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { AppComponent } from './app.component';
import { AuthService } from './features/auth/services/auth.service';
import { TokenService } from './core/services/token.service';
describe('Application navigation by role', () => {
  for (const role of ['CLIENTE', 'ADMINISTRADOR', 'ENCARGADO', 'ENCARGADO_SUCURSAL', 'CAJERO', '']) {
    it('renders one navigation experience for ' + (role || 'visitor'), async () => {
      await TestBed.configureTestingModule({imports: [AppComponent], providers: [provideRouter([]), provideNoopAnimations(),
        {provide: AuthService, useValue: {hasSession: () => !!role, getRoleFromToken: () => role, logout: () => of({})}},
        {provide: TokenService, useValue: {getToken: () => 'token'}}]}).compileComponents();
      const fixture = TestBed.createComponent(AppComponent); fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement;
      expect(el.querySelectorAll('app-navbar').length).toBe(1);
      expect(!!el.querySelector('app-admin-sidebar')).toBe(!!role && role !== 'CLIENTE');
      expect(!!el.querySelector('.shop-links')).toBe(!role || role === 'CLIENTE');
      if (role === 'CAJERO') {
        expect(Array.from(el.querySelectorAll('app-admin-sidebar a')).map(a => a.getAttribute('href'))).toEqual(['/pos']);
      }
      if (role && role !== 'CLIENTE') {
        const toggle = el.querySelector<HTMLButtonElement>('.menu-toggle')!;
        toggle.click(); fixture.detectChanges();
        expect(toggle.getAttribute('aria-expanded')).toBe('true');
        el.querySelector<HTMLAnchorElement>('app-admin-sidebar a')!.click(); fixture.detectChanges();
        expect(toggle.getAttribute('aria-expanded')).toBe('false');
      }
    });
  }
});
