import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AdminReportService } from '../../services/admin-report.service';
import { BranchComparisonAccessCache } from '../../../../core/services/branch-comparison-access-cache.service';
import { NavigationGroup, normalizeRole, navigationGroups as groupsForRole } from '../../../../shared/navigation/navigation.config';
@Component({selector: 'app-admin-sidebar', standalone: true, imports: [RouterLink, RouterLinkActive], templateUrl: './admin-sidebar.component.html', styleUrl: './admin-sidebar.component.scss'})
export class AdminSidebarComponent {
  private currentRole = 'ADMINISTRADOR';
  comparisonAllowed = false;
  constructor(private readonly reports: AdminReportService, private readonly accessCache: BranchComparisonAccessCache) {}
  @Input() set role(value: string) {
    this.currentRole = normalizeRole(value);
    this.comparisonAllowed = false;
    if (['ENCARGADO', 'ENCARGADO_SUCURSAL', 'GERENTE'].includes(this.currentRole)) {
      this.comparisonAllowed = !navigator.onLine && this.accessCache.read() === true;
      if (navigator.onLine) this.reports.getBranchComparisonAccess().subscribe({
        next: (access) => { this.accessCache.write(access.comparacion_sucursales); this.comparisonAllowed = access.comparacion_sucursales; },
        error: () => this.comparisonAllowed = this.accessCache.read() === true
      });
    }
  }
  get role(): string { return this.currentRole; }
  get visibleGroups(): NavigationGroup[] {
    const groups = groupsForRole(this.currentRole);
    if (this.comparisonAllowed) groups.push({ label: 'Reportes', links: [{ label: 'Comparación por sucursal', path: '/reports/branch-comparison' }] });
    return groups;
  }
  @Output() navigate = new EventEmitter<void>();
}
