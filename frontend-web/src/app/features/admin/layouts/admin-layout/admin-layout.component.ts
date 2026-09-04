import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { AdminHeaderComponent } from '../../components/admin-header/admin-header.component';
import { AdminSidebarComponent } from '../../components/admin-sidebar/admin-sidebar.component';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [RouterOutlet, MatSidenavModule, AdminHeaderComponent, AdminSidebarComponent],
  templateUrl: './admin-layout.component.html',
  styleUrl: './admin-layout.component.scss'
})
export class AdminLayoutComponent {}
