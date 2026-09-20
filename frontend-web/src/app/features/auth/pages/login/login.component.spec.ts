import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, UrlTree } from '@angular/router';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, Subject, throwError } from 'rxjs';
import { AuthService, LoginResponse } from '../../services/auth.service';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['login', 'getRoleFromToken']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate', 'createUrlTree', 'serializeUrl']);
    router.createUrlTree.and.returnValue(new UrlTree());
    router.serializeUrl.and.returnValue('');
    Object.assign(router, { events: new Subject() });
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [LoginComponent, NoopAnimationsModule],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
        { provide: ActivatedRoute, useValue: {} },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(LoginComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not submit an invalid form', () => {
    component.submit();

    expect(authService.login).not.toHaveBeenCalled();
    expect(component.loginForm.touched).toBeTrue();
  });

  it('stores the session through AuthService and redirects clients after successful login', () => {
    const response: LoginResponse = {
      access_token: 'jwt-token',
      token_type: 'bearer',
      usuario: { id_usuario: 1, correo: 'cliente@example.com' },
      rol: 'CLIENTE'
    };
    authService.login.and.returnValue(of(response));
    component.loginForm.setValue({ correo: 'cliente@example.com', password: 'password-seguro' });

    component.submit();

    expect(authService.login).toHaveBeenCalledWith({
      correo: 'cliente@example.com',
      password: 'password-seguro'
    });
    expect(router.navigate).toHaveBeenCalledWith(['/catalog']);
    expect(snackBar.open).toHaveBeenCalled();
  });

  it('redirects administrators to admin after successful login', () => {
    const response: LoginResponse = {
      access_token: 'jwt-token',
      token_type: 'bearer',
      usuario: { id_usuario: 1, correo: 'admin@example.com' },
      rol: 'ADMINISTRADOR'
    };
    authService.login.and.returnValue(of(response));
    component.loginForm.setValue({ correo: 'admin@example.com', password: 'password-seguro' });

    component.submit();

    expect(router.navigate).toHaveBeenCalledWith(['/admin']);
  });

  it('uses the token role when the login response does not include one', () => {
    const response = {
      access_token: 'jwt-token',
      token_type: 'bearer',
      usuario: { id_usuario: 1, correo: 'admin@example.com' }
    } as LoginResponse;
    authService.login.and.returnValue(of(response));
    authService.getRoleFromToken.and.returnValue('ADMINISTRADOR');
    component.loginForm.setValue({ correo: 'admin@example.com', password: 'password-seguro' });

    component.submit();

    expect(authService.getRoleFromToken).toHaveBeenCalledWith('jwt-token');
    expect(router.navigate).toHaveBeenCalledWith(['/admin']);
  });

  it('shows an error message when login fails', () => {
    authService.login.and.returnValue(
      throwError(() => ({ error: { message: 'Credenciales inválidas' } }))
    );
    component.loginForm.setValue({ correo: 'cliente@example.com', password: 'incorrecta' });

    component.submit();

    expect(router.navigate).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith('Credenciales inválidas', 'Cerrar', {
      duration: 5000
    });
  });
});
