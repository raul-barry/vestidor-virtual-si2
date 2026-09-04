import { Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-password-reset-confirm',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './password-reset-confirm.component.html',
  styleUrl: './password-reset-confirm.component.scss'
})
export class PasswordResetConfirmComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly confirmForm = this.formBuilder.group({
    token: ['', [Validators.required]],
    nueva_password: ['', [Validators.required]]
  });

  isSubmitting = false;

  submit(): void {
    if (this.confirmForm.invalid) {
      this.confirmForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.authService.resetPassword(this.confirmForm.getRawValue()).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: () => {
        this.snackBar.open('Contraseña actualizada correctamente', 'Cerrar', { duration: 3000 });
        void this.router.navigate(['/auth/login']);
      },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible actualizar la contraseña', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }
}
