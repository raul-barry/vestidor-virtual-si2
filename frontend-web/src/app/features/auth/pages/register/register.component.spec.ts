import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { RegisterComponent } from './register.component';

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['register']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [RegisterComponent, NoopAnimationsModule],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(RegisterComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not submit an invalid form', () => {
    component.submit();

    expect(authService.register).not.toHaveBeenCalled();
    expect(component.registerForm.touched).toBeTrue();
  });

  it('registers a client and redirects to login', () => {
    authService.register.and.returnValue(of({
      id_usuario: 1,
      nombres: 'Carlos',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '70000000',
      rol: 'CLIENTE'
    }));
    component.registerForm.setValue({
      nombres: 'Carlos',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '70000000',
      password: 'password-seguro'
    });

    component.submit();

    expect(authService.register).toHaveBeenCalledWith(component.registerForm.getRawValue());
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
    expect(snackBar.open).toHaveBeenCalled();
  });

  it('shows the duplicate email message', () => {
    authService.register.and.returnValue(
      throwError(() => ({ error: { message: 'El correo ya está registrado' } }))
    );
    component.registerForm.setValue({
      nombres: 'Carlos',
      apellidos: 'Perez',
      correo: 'cliente@example.com',
      telefono: '70000000',
      password: 'password-seguro'
    });

    component.submit();

    expect(router.navigate).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith('El correo ya está registrado', 'Cerrar', {
      duration: 5000
    });
  });
});
