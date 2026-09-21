import { Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-password-reset-confirm', standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatSnackBarModule],
  templateUrl: './password-reset-confirm.component.html', styleUrl: './password-reset-confirm.component.scss'
})
export class PasswordResetConfirmComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly snackBar = inject(MatSnackBar);
  readonly confirmForm = this.formBuilder.group({
    nueva_password: ['', [Validators.required, Validators.minLength(8)]],
    confirmar_password: ['', [Validators.required]]
  });
  isSubmitting = false;
  completed = false;
  private readonly token = this.route.snapshot.queryParamMap.get('token') ?? '';

  submit(): void {
    const password = this.confirmForm.controls.nueva_password.value;
    const confirmation = this.confirmForm.controls.confirmar_password.value;
    if (!this.token) { this.snackBar.open('Token de recuperación inválido o expirado', 'Cerrar', { duration: 5000 }); return; }
    if (this.confirmForm.invalid || password !== confirmation) {
      this.confirmForm.markAllAsTouched();
      if (password !== confirmation) this.snackBar.open('Las contraseñas no coinciden', 'Cerrar', { duration: 4000 });
      return;
    }
    this.isSubmitting = true;
    this.authService.resetPassword({ token: this.token, nueva_password: password }).pipe(finalize(() => (this.isSubmitting = false))).subscribe({
      next: () => { this.completed = true; this.snackBar.open('Contraseña actualizada correctamente.', 'Cerrar', { duration: 3000 }); },
      error: (error: { error?: { message?: string } }) => this.snackBar.open(error.error?.message ?? 'No fue posible actualizar la contraseña', 'Cerrar', { duration: 5000 })
    });
  }
  goToLogin(): void { void this.router.navigate(['/auth/login']); }
}
