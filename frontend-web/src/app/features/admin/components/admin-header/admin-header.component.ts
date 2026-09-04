import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { AuthService } from '../../../auth/services/auth.service';

@Component({
  selector: 'app-admin-header',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatToolbarModule],
  templateUrl: './admin-header.component.html',
  styleUrl: './admin-header.component.scss'
})
export class AdminHeaderComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  get sectionTitle(): string {
    const titles: Record<string, string> = {
      '/admin/products': 'Productos',
      '/admin/variants': 'Variantes',
      '/admin/inventory': 'Inventario',
      '/admin/orders': 'Pedidos',
      '/admin/users': 'Usuarios',
      '/admin/reports': 'Reportes'
    };
    return Object.entries(titles).find(([path]) => this.router.url.startsWith(path))?.[1] ?? 'Dashboard';
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => void this.router.navigate(['/auth/login']),
      error: () => void this.router.navigate(['/auth/login'])
    });
  }
}
