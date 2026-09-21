import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { navigationGroups } from '../../../../shared/navigation/navigation.config';
@Component({selector: 'app-admin-sidebar', standalone: true, imports: [RouterLink, RouterLinkActive], templateUrl: './admin-sidebar.component.html', styleUrl: './admin-sidebar.component.scss'})
export class AdminSidebarComponent {
  @Input() role = 'ADMINISTRADOR';
  @Output() navigate = new EventEmitter<void>();
  readonly navigationGroups = navigationGroups;
}
