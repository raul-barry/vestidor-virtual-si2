import { Component } from '@angular/core';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from './features/auth/services/auth.service';
import { TokenService } from './core/services/token.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `<nav style="display:flex;gap:1rem;flex-wrap:wrap;padding:1rem" aria-label="Navegación principal">
    <a routerLink="/catalog">Catálogo</a>
    @if (auth.hasSession()) {
      @if (role === 'CLIENTE') { <a routerLink="/cart">Carrito</a><a routerLink="/orders">Mis pedidos</a> }
      @if (role === 'CLIENTE') { <a routerLink="/recommendations">Recomendaciones</a><a routerLink="/fitting">Vestidor virtual</a> }
      @if (role !== 'CAJERO') { <a routerLink="/reservations">Reservas</a> }
      @if (role === 'ADMINISTRADOR') { <a routerLink="/admin">Administración</a> }
      @if (role === 'CAJERO' || role === 'ADMINISTRADOR') { <a routerLink="/pos">Venta presencial</a> }
      @if (role === 'ENCARGADO_SUCURSAL' || role === 'ENCARGADO') { <a routerLink="/inventory">Inventario</a> }
      <a routerLink="/profile">Perfil</a><button (click)="logout()">Cerrar sesión</button>
    } @else { <a routerLink="/auth/login">Iniciar sesión</a><a routerLink="/auth/register">Registrarse</a> }
  </nav><router-outlet />`
})
export class AppComponent {
  auth = inject(AuthService);
  private tokens = inject(TokenService);
  private router = inject(Router);
  get role(): string | null { return this.auth.getRoleFromToken(this.tokens.getToken() ?? ''); }
  logout(): void { this.auth.logout().subscribe({ next: () => this.router.navigate(['/auth/login']), error: () => this.router.navigate(['/auth/login']) }); }
}
