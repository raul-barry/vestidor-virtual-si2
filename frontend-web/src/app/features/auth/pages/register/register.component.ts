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
  selector: 'app-register',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss'
})
export class RegisterComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly registerForm = this.formBuilder.group({
    nombres: ['', [Validators.required]],
    apellidos: ['', [Validators.required]],
    correo: ['', [Validators.required, Validators.email]],
    telefono: ['', [Validators.required]],
    password: ['', [Validators.required]]
  });

  isSubmitting = false;

  submit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.authService.register(this.registerForm.getRawValue()).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: () => {
        this.snackBar.open('Registro completado correctamente', 'Cerrar', { duration: 3000 });
        void this.router.navigate(['/auth/login']);
      },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible registrar el cliente', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }
}
