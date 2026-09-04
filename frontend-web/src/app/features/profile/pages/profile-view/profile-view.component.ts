import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Usuario } from '../../../../shared/models/usuario.model';
import { ProfileService } from '../../services/profile.service';

@Component({
  selector: 'app-profile-view',
  standalone: true,
  imports: [RouterLink, MatButtonModule, MatCardModule, MatSnackBarModule],
  templateUrl: './profile-view.component.html',
  styleUrl: './profile-view.component.scss'
})
export class ProfileViewComponent implements OnInit {
  private readonly profileService = inject(ProfileService);
  private readonly snackBar = inject(MatSnackBar);

  profile: Usuario | null = null;
  isLoading = true;

  ngOnInit(): void {
    this.profileService.getProfile().subscribe({
      next: (profile) => {
        this.profile = profile;
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
}
