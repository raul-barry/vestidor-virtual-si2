import { Component, OnInit, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs';
import { ProfileService } from '../../services/profile.service';

@Component({
  selector: 'app-profile-edit',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './profile-edit.component.html',
  styleUrl: './profile-edit.component.scss'
})
export class ProfileEditComponent implements OnInit {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly profileService = inject(ProfileService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly profileForm = this.formBuilder.group({
    nombres: ['', [Validators.required]],
    apellidos: ['', [Validators.required]],
    telefono: ['', [Validators.required]]
  });

  isLoading = true;
  isSubmitting = false;

  ngOnInit(): void {
    this.profileService.getProfile().subscribe({
      next: (profile) => {
        this.profileForm.setValue({
          nombres: profile.nombres ?? '',
          apellidos: profile.apellidos ?? '',
          telefono: profile.telefono ?? ''
        });
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => {
        this.isLoading = false;
        this.snackBar.open(error.error?.message ?? 'No fue posible cargar el perfil', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }

  submit(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    this.profileService.updateProfile(this.profileForm.getRawValue()).pipe(
      finalize(() => (this.isSubmitting = false))
    ).subscribe({
      next: () => {
        this.snackBar.open('Perfil actualizado correctamente', 'Cerrar', { duration: 3000 });
        void this.router.navigate(['/profile/view']);
      },
      error: (error: { error?: { message?: string } }) => {
        this.snackBar.open(error.error?.message ?? 'No fue posible actualizar el perfil', 'Cerrar', {
          duration: 5000
        });
      }
    });
  }
}
