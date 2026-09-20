import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { CUSTOMER_LINKS, homeForRole } from '../../navigation/navigation.config';
@Component({
  selector: 'app-navbar', standalone: true, imports: [RouterLink, RouterLinkActive, MatButtonModule],
  templateUrl: './navbar.component.html', styleUrl: './navbar.component.scss'
})
export class NavbarComponent {
  @Input() signedIn = false;
  @Input() staff = false;
  @Input() role = '';
  @Input() expanded = false;
  @Input() authPage: 'login' | 'register' | '' = '';
  @Output() toggleMenu = new EventEmitter<void>();
  @Output() signOut = new EventEmitter<void>();
  readonly customerLinks = CUSTOMER_LINKS;
  readonly homeForRole = homeForRole;
  get roleLabel(): string { return this.role === 'ADMINISTRADOR' ? 'Administración' : this.role === 'CAJERO' ? 'Caja' : 'Operaciones'; }
}
