import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-password-reset-request',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './password-reset-request.component.html',
  styleUrl: './password-reset-request.component.scss'
})
export class PasswordResetRequestComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);

  readonly requestForm = this.formBuilder.group({
    correo: ['', [Validators.required, Validators.email]]
  });
  readonly tokenForm = this.formBuilder.group({ token: ['', [Validators.required]] });

  isSubmitting = false;
  tokenSectionVisible = false;
  submit(): void {
    if (this.requestForm.invalid) {
      this.requestForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.authService.requestPasswordReset(this.requestForm.controls.correo.value).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: (response) => {
        this.snackBar.open('Solicitud enviada correctamente', 'Cerrar', { duration: 3000 });
        this.tokenSectionVisible = true;
        if (response.token) this.tokenForm.controls.token.setValue(response.token);
      },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible enviar la solicitud', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  continueWithToken(): void {
    if (this.tokenForm.invalid || this.isSubmitting) {
      this.tokenForm.markAllAsTouched();
      return;
    }
    this.isSubmitting = true;
    this.authService.validatePasswordResetToken(this.tokenForm.controls.token.value).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: () => void this.router.navigate(['/auth/password-reset/confirm'], { queryParams: { token: this.tokenForm.controls.token.value } }),
      error: (error: { error?: { message?: string } }) => this.snackBar.open(error.error?.message ?? 'Token inválido o expirado', 'Cerrar', { duration: 5000 })
    });
  }
}
