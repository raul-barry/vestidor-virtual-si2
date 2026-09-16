import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
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

  readonly requestForm = this.formBuilder.group({
    correo: ['', [Validators.required, Validators.email]]
  });

  isSubmitting = false;
  resetToken = '';

  submit(): void {
    if (this.requestForm.invalid) {
      this.requestForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.authService.requestPasswordReset(this.requestForm.controls.correo.value).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: (response) => { this.resetToken = response.token ?? ''; this.snackBar.open('Solicitud enviada correctamente', 'Cerrar', { duration: 3000 }); },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible enviar la solicitud', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }
}
