import { Component, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { AuthService } from './features/auth/services/auth.service';
import { TokenService } from './core/services/token.service';
import { NavbarComponent } from './shared/components/navbar/navbar.component';
import { AdminSidebarComponent } from './features/admin/components/admin-sidebar/admin-sidebar.component';
import { isStaff, normalizeRole } from './shared/navigation/navigation.config';
@Component({
  selector: 'app-root', standalone: true, imports: [RouterOutlet, NavbarComponent, AdminSidebarComponent],
  template: `
    <a class="skip-link" href="#page-content">Saltar al contenido</a>
    <app-navbar [signedIn]="auth.hasSession()" [staff]="staff" [role]="role" [expanded]="menuOpen" [authPage]="authPage" (toggleMenu)="menuOpen = !menuOpen" (signOut)="logout()" />
    <div class="application-shell" [class.workspace]="staff">
      @if (staff) {
        <aside id="workspace-navigation" class="workspace-navigation" [class.mobile-open]="menuOpen" (keydown.escape)="closeMenu()">
          <app-admin-sidebar [role]="role" (navigate)="closeMenu()" />
        </aside>
      }
      <div id="page-content" class="page-content" tabindex="-1" (keydown.escape)="closeMenu()"><router-outlet (activate)="closeMenu()" /></div>
    </div>`,
  styleUrl: './app.component.scss'
})
export class AppComponent {
  readonly auth = inject(AuthService);
  private readonly tokens = inject(TokenService);
  private readonly router = inject(Router);
  menuOpen = false;
  get role(): string { return normalizeRole(this.auth.getRoleFromToken(this.tokens.getToken() ?? '')); }
  get staff(): boolean { return this.auth.hasSession() && isStaff(this.role); }
  get authPage(): 'login' | 'register' | '' { return this.router.url.startsWith('/auth/login') ? 'login' : this.router.url.startsWith('/auth/register') ? 'register' : ''; }
  closeMenu(): void { this.menuOpen = false; }
  logout(): void { this.closeMenu(); this.auth.logout().subscribe({ next: () => this.router.navigate(['/auth/login']), error: () => this.router.navigate(['/auth/login']) }); }
}
