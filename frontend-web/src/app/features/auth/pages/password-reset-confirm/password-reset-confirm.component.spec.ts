import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { PasswordResetConfirmComponent } from './password-reset-confirm.component';

describe('PasswordResetConfirmComponent', () => {
  let component: PasswordResetConfirmComponent;
  let fixture: ComponentFixture<PasswordResetConfirmComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['resetPassword']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [PasswordResetConfirmComponent, NoopAnimationsModule],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap({ token: 'token-valido' }) } } },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(PasswordResetConfirmComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(PasswordResetConfirmComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not submit without a token', () => {
    component.confirmForm.controls.nueva_password.setValue('password-nueva');

    component.submit();

    expect(authService.resetPassword).not.toHaveBeenCalled();
  });

  it('updates the password and lets the user return to login', () => {
    authService.resetPassword.and.returnValue(of({ message: 'Contraseña actualizada' }));
    component.confirmForm.setValue({ nueva_password: 'password-nueva', confirmar_password: 'password-nueva' });

    component.submit();

    expect(authService.resetPassword).toHaveBeenCalledWith({
      token: 'token-valido',
      nueva_password: 'password-nueva'
    });
    expect(component.completed).toBeTrue();
    component.goToLogin();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });

  it('shows the invalid token message', () => {
    authService.resetPassword.and.returnValue(
      throwError(() => ({ error: { message: 'Token de recuperación inválido o expirado' } }))
    );
    component.confirmForm.setValue({ nueva_password: 'password-nueva', confirmar_password: 'password-nueva' });

    component.submit();

    expect(router.navigate).not.toHaveBeenCalled();
    expect(snackBar.open).toHaveBeenCalledWith(
      'Token de recuperación inválido o expirado',
      'Cerrar',
      { duration: 5000 }
    );
  });
});
