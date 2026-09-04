import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { PasswordResetRequestComponent } from './password-reset-request.component';

describe('PasswordResetRequestComponent', () => {
  let component: PasswordResetRequestComponent;
  let fixture: ComponentFixture<PasswordResetRequestComponent>;
  let authService: jasmine.SpyObj<AuthService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['requestPasswordReset']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [PasswordResetRequestComponent, NoopAnimationsModule],
      providers: [
        { provide: AuthService, useValue: authService },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(PasswordResetRequestComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
    fixture = TestBed.createComponent(PasswordResetRequestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('does not submit an invalid email', () => {
    component.requestForm.controls.correo.setValue('correo-invalido');

    component.submit();

    expect(authService.requestPasswordReset).not.toHaveBeenCalled();
  });

  it('submits a valid recovery request', () => {
    authService.requestPasswordReset.and.returnValue(of({ message: 'Solicitud generada' }));
    component.requestForm.controls.correo.setValue('cliente@example.com');

    component.submit();

    expect(authService.requestPasswordReset).toHaveBeenCalledWith('cliente@example.com');
    expect(snackBar.open).toHaveBeenCalledWith('Solicitud enviada correctamente', 'Cerrar', {
      duration: 3000
    });
  });

  it('shows a fallback message when the server is unavailable', () => {
    authService.requestPasswordReset.and.returnValue(throwError(() => new Error('Network error')));
    component.requestForm.controls.correo.setValue('cliente@example.com');

    component.submit();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible enviar la solicitud', 'Cerrar', {
      duration: 5000
    });
  });
});
