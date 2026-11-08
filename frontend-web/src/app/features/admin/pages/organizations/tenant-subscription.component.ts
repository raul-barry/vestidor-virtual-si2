import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';
import { OrganizationUsage } from '../../models/organization-usage.model';
import { SubscriptionAdmin, SubscriptionPlanAdmin } from '../../models/subscription-admin.model';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';

@Component({
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './tenant-subscription.component.html',
  styleUrl: './tenant-subscription.component.scss',
})
export class TenantSubscriptionComponent implements OnInit {
  private readonly service = inject(SubscriptionAdminService);
  subscription: SubscriptionAdmin | null = null;
  plans: SubscriptionPlanAdmin[] = [];
  usage: OrganizationUsage | null = null;
  loading = true;
  error = '';

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.error = '';
    forkJoin({
      subscription: this.service.currentForMyOrganization(),
      usage: this.service.usageForMyOrganization(),
      plans: this.service.listPlans(),
    }).subscribe({
      next: result => {
        this.subscription = result.subscription;
        this.usage = result.usage;
        this.plans = result.plans;
        this.loading = false;
      },
      error: error => {
        this.loading = false;
        this.error = error.status === 403
          ? 'Esta sección requiere permisos de administrador de empresa.'
          : 'No se pudo cargar la suscripción de esta organización.';
      },
    });
  }

  get currentPlan(): SubscriptionPlanAdmin | undefined {
    return this.plans.find(plan => plan.id_plan === this.subscription?.plan_id);
  }

  get branchUsagePercent(): number {
    const limit = this.usage?.limite_sucursales;
    if (!this.usage || !limit) return 0;
    return Math.min(100, Math.round(this.usage.sucursales_activas / limit * 100));
  }

  get renewalLabel(): string {
    if (!this.subscription) return 'Sin suscripción activa';
    return this.subscription.fecha_fin
      ? `Renueva o vence el ${new Date(this.subscription.fecha_fin).toLocaleDateString()}`
      : 'Sin fecha de vencimiento';
  }

  isFeatureIncluded(plan: SubscriptionPlanAdmin, code: string): boolean {
    const canonical = plan.caracteristicas.find(item => item.codigo === code);
    if (canonical) return canonical.habilitada;
    if (code === 'reportes_ia') {
      return plan.caracteristicas.find(item => item.codigo === 'reportes_gemini')?.habilitada ?? false;
    }
    return false;
  }

  featureLabel(code: string, name: string): string {
    return code === 'reportes_ia' || code === 'reportes_gemini' ? 'Reportes con IA' : name;
  }

  visibleFeatures(plan: SubscriptionPlanAdmin): SubscriptionPlanAdmin['caracteristicas'] {
    const hasCanonical = plan.caracteristicas.some(item => item.codigo === 'reportes_ia');
    return plan.caracteristicas
      .filter(item => item.codigo !== 'reportes_gemini' || !hasCanonical)
      .map(item => item.codigo === 'reportes_gemini'
        ? { ...item, codigo: 'reportes_ia', nombre: 'Reportes con IA', descripcion: 'Reportes empresariales asistidos por inteligencia artificial.' }
        : item);
  }

  trackPlan(_: number, plan: SubscriptionPlanAdmin): number { return plan.id_plan; }
}
