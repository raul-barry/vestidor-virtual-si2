import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';
import { SubscriptionAdmin, SubscriptionPlanAdmin } from '../../models/subscription-admin.model';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';

@Component({
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `<main><a routerLink="/admin/dashboard">← Administración</a><h1>Mi suscripción</h1>
    @if(loading){<p role="status">Cargando información…</p>}
    @else if(error){<p role="alert">{{error}}</p><button (click)="load()">Reintentar</button>}
    @else {
      @if(subscription){<section><h2>{{subscription.plan_nombre}}</h2><p>Estado: <strong>{{subscription.estado}}</strong></p>
        <p>Vigencia: {{subscription.fecha_inicio | date:'mediumDate'}} — {{subscription.fecha_fin ? (subscription.fecha_fin | date:'mediumDate') : 'Sin vencimiento'}}</p>
      </section>} @else {<p>La organización no tiene una suscripción activa registrada.</p>}
      @if(usage){<section><h2>Consumo actual</h2><dl>
        <dt>Sucursales activas</dt><dd>{{usage.sucursales_activas}} / {{usage.limite_sucursales ?? 'Sin límite'}}</dd>
        <dt>Usuarios activos</dt><dd>{{usage.usuarios_activos}}</dd>
        <dt>Productos</dt><dd>{{usage.productos_registrados}}</dd>
        <dt>Pedidos del período</dt><dd>{{usage.pedidos_periodo}}</dd>
        <dt>Ventas del período</dt><dd>Bs {{usage.ventas_periodo}}</dd>
        <dt>Inventario disponible / reservado / vendido</dt><dd>{{usage.inventario_disponible}} / {{usage.inventario_reservado}} / {{usage.inventario_vendido}}</dd>
      </dl></section>}
      <section><h2>Planes disponibles</h2><div class="plans">@for(plan of plans;track plan.id_plan){<article><h3>{{plan.nombre}}</h3><p>{{plan.descripcion}}</p><p>Sucursales: {{plan.max_sucursales ?? 'Sin límite'}}</p><ul>@for(feature of plan.caracteristicas;track feature.codigo){<li>{{feature.nombre}}: {{feature.habilitada ? 'Incluida' : 'No incluida'}}{{feature.limite !== null ? ' · límite ' + feature.limite : ''}}</li>}</ul></article>}</div>
        <p>Los cambios de plan los gestiona el administrador de plataforma conforme a la suscripción y las reglas comerciales vigentes.</p>
      </section>
    }</main>`,
  styles: [`main{max-width:1100px;margin:auto;padding:2rem;color:var(--ink)}section{margin:1rem 0;padding:1.25rem;border:1px solid var(--border);border-radius:14px;background:var(--surface)}dl{display:grid;grid-template-columns:minmax(220px,1fr) 1fr;gap:.5rem}dt{font-weight:600}.plans{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}.plans article{padding:1rem;border:1px solid var(--border);border-radius:12px}@media(max-width:800px){.plans{grid-template-columns:1fr}}`]
})
export class TenantSubscriptionComponent implements OnInit {
  private readonly service = inject(SubscriptionAdminService);
  subscription: SubscriptionAdmin | null = null;
  plans: SubscriptionPlanAdmin[] = [];
  usage: any = null;
  loading = true;
  error = '';
  ngOnInit(): void { this.load(); }
  load(): void {
    this.loading = true; this.error = '';
    forkJoin({ subscription: this.service.currentForMyOrganization(), usage: this.service.usageForMyOrganization(), plans: this.service.listPlans() }).subscribe({
      next: result => { this.subscription = result.subscription; this.usage = result.usage; this.plans = result.plans; this.loading = false; },
      error: error => { this.loading = false; this.error = error.status === 403 ? 'Esta sección requiere permisos de administrador de empresa.' : 'No se pudo cargar la suscripción de esta organización.'; }
    });
  }
}
