import { Component, inject } from '@angular/core';
import { ReactiveFormsModule, NonNullableFormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly loginForm = this.formBuilder.group({
    correo: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]]
  });

  isSubmitting = false;

  submit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.authService.login(this.loginForm.getRawValue()).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: (response) => {
        this.snackBar.open('Sesión iniciada correctamente', 'Cerrar', { duration: 3000 });
        const rol = (response.rol ?? this.authService.getRoleFromToken(response.access_token))?.trim().toUpperCase();

        if (rol === 'ADMINISTRADOR') {
          void this.router.navigate(['/admin']);
          return;
        }
        void this.router.navigate([rol === 'CAJERO' ? '/pos' : rol === 'ENCARGADO_SUCURSAL' ? '/inventory' : '/catalog']);
      },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible iniciar sesión', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }
}
