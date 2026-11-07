import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { RouterModule } from '@angular/router';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { CommercialPlanAdmin, CommercialPlanFeatureUpdate, CommercialPlanUpdate } from '../../models/commercial-plan-admin.model';
import { CommercialPlanAdminService } from '../../services/commercial-plan-admin.service';

@Component({
  selector: 'app-commercial-plan-management',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, MatButtonModule, MatCardModule, MatCheckboxModule, MatDialogModule,
    MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule, MatSnackBarModule],
  template: `
    <main class="page">
      <a class="back" routerLink="/platform/organizations">← Administración SaaS</a>
      <header><p class="eyebrow">PLATAFORMA · SAAS</p><h1>Planes comerciales</h1>
        <p class="muted">Administra los límites y las características incluidas en los planes existentes.</p></header>
      @if (loading) { <div class="loading"><mat-spinner diameter="38" /></div> }
      @else if (pageError) { <p class="error" role="alert">{{pageError}}</p><button mat-stroked-button (click)="load()">Reintentar</button> }
      @else {
        <section class="plan-overview" aria-label="Planes comerciales disponibles">
          @for (plan of plans; track plan.id_plan) {
            <article><h2>{{plan.nombre}}</h2><p>{{plan.codigo}} · {{plan.max_sucursales ?? 'Sucursales sin límite'}}</p>
              <ul>@for(feature of plan.caracteristicas;track feature.codigo){<li>{{feature.nombre}}: {{feature.habilitada ? 'Incluida' : 'No incluida'}}{{feature.limite !== null ? ' · límite ' + feature.limite : ''}}</li>}</ul>
            </article>
          }
        </section>
        <mat-form-field appearance="outline" class="plan-selector"><mat-label>Plan a editar</mat-label>
          <mat-select [(value)]="selectedPlanId">@for(plan of plans;track plan.id_plan){<mat-option [value]="plan.id_plan">{{plan.nombre}}</mat-option>}</mat-select>
        </mat-form-field>
        <section class="plans">
          @for (plan of selectedPlans; track plan.id_plan) {
            <mat-card>
              <mat-card-header><mat-card-title>{{plan.nombre}}</mat-card-title><mat-card-subtitle>Código: {{plan.codigo}} · {{plan.activo ? 'Activo' : 'Inactivo'}}</mat-card-subtitle></mat-card-header>
              <mat-card-content>
                <div class="plan-fields">
                  <mat-form-field appearance="outline"><mat-label>Nombre</mat-label><input matInput [(ngModel)]="plan.nombre" [ngModelOptions]="{standalone:true}"></mat-form-field>
                  <mat-form-field appearance="outline"><mat-label>Descripción</mat-label><textarea matInput rows="2" [(ngModel)]="plan.descripcion" [ngModelOptions]="{standalone:true}"></textarea></mat-form-field>
                  <mat-form-field appearance="outline"><mat-label>Límite de sucursales</mat-label><input matInput type="number" min="1" placeholder="Sin límite" [ngModel]="plan.max_sucursales" (ngModelChange)="setBranchLimit(plan, $event)" [ngModelOptions]="{standalone:true}"><mat-hint>Vacío significa sin límite comercial fijo.</mat-hint></mat-form-field>
                  <mat-checkbox [(ngModel)]="plan.activo" [ngModelOptions]="{standalone:true}">Plan activo</mat-checkbox>
                </div>
                <div class="feature-heading"><h2>Características</h2><span>{{plan.caracteristicas.length}} registradas</span></div>
                @for (feature of plan.caracteristicas; track feature.codigo) {
                  <div class="feature">
                    <div class="feature-title"><mat-checkbox [(ngModel)]="feature.habilitada" [ngModelOptions]="{standalone:true}"><strong>{{feature.nombre}}</strong></mat-checkbox><code>{{feature.codigo}}</code></div>
                    @if (feature.descripcion) { <p class="muted">{{feature.descripcion}}</p> }
                    <div class="feature-fields">
                      <mat-form-field appearance="outline"><mat-label>Límite configurable</mat-label><input matInput type="number" min="0" placeholder="Sin límite" [ngModel]="feature.limite" (ngModelChange)="setFeatureLimit(feature, $event)" [ngModelOptions]="{standalone:true}"></mat-form-field>
                      <mat-form-field appearance="outline" class="json"><mat-label>Configuración JSON</mat-label><textarea matInput rows="2" [(ngModel)]="feature.configuracionTexto" [ngModelOptions]="{standalone:true}"></textarea></mat-form-field>
                    </div>
                  </div>
                }
                @if (planError(plan.id_plan)) { <p class="error" role="alert">{{planError(plan.id_plan)}}</p> }
                <div class="actions"><button mat-stroked-button (click)="refreshPlan(plan)" [disabled]="busyId === plan.id_plan">Recargar</button>
                  <button mat-flat-button color="primary" (click)="save(plan)" [disabled]="busyId === plan.id_plan">{{busyId === plan.id_plan ? 'Guardando…' : 'Guardar cambios'}}</button></div>
              </mat-card-content>
            </mat-card>
          }
        </section>
      }
    </main>
  `,
  styles: [`
    .page{max-width:1320px;margin:0 auto;padding:clamp(1.25rem,3vw,2.5rem)}.back{display:inline-block;margin-bottom:1rem;color:var(--primary);font-weight:700;text-decoration:none}.eyebrow{margin:0 0 .4rem;color:var(--primary);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{margin:0;color:var(--ink);font-size:clamp(1.8rem,3vw,2.5rem)}.muted{color:var(--muted)}.loading{display:grid;place-items:center;padding:4rem}.plan-overview{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem;margin:1.5rem 0}.plan-overview article{min-width:0;padding:1rem;border:1px solid var(--border);border-radius:14px;background:var(--surface)}.plan-overview h2{margin:.1rem 0}.plan-overview ul{padding-left:1.1rem}.plan-selector{width:min(100%,420px)}.plans{display:grid;grid-template-columns:minmax(0,1fr);gap:1.1rem;margin-top:.5rem}mat-card{border:1px solid var(--border);border-radius:18px}mat-card-content{padding-top:1rem}.plan-fields{display:grid;grid-template-columns:1fr 1fr;gap:.2rem .8rem}.plan-fields mat-form-field{width:100%}.feature-heading{display:flex;align-items:center;justify-content:space-between;margin:.6rem 0}.feature-heading h2{font-size:1.1rem}.feature-heading span{color:var(--muted);font-size:.85rem}.feature{padding:.85rem 0;border-top:1px solid var(--border)}.feature-title{display:flex;justify-content:space-between;align-items:center;gap:.5rem}.feature-title code{color:var(--muted);font-size:.75rem}.feature p{margin:.25rem 0 .5rem;font-size:.85rem}.feature-fields{display:grid;grid-template-columns:minmax(120px,.45fr) 1fr;gap:.7rem}.feature-fields mat-form-field{width:100%}.actions{display:flex;justify-content:flex-end;gap:.7rem;margin-top:.5rem}.error{color:var(--danger)}@media(max-width:850px){.plan-overview{grid-template-columns:1fr 1fr}}@media(max-width:550px){.plan-overview,.plan-fields,.feature-fields{grid-template-columns:1fr}.feature-title{align-items:flex-start;flex-direction:column}}
  `],
})
export class CommercialPlanManagementComponent implements OnInit {
  private readonly service = inject(CommercialPlanAdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  plans: CommercialPlanAdmin[] = [];
  selectedPlanId: number | null = null;
  loading = true;
  pageError = '';
  busyId: number | null = null;
  private readonly errors = new Map<number, string>();

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true; this.pageError = '';
    this.service.list().subscribe({
      next: plans => { this.plans = plans.map(plan => this.prepare(plan)); this.selectedPlanId ??= this.plans[0]?.id_plan ?? null; this.loading = false; },
      error: error => { this.pageError = this.message(error); this.loading = false; },
    });
  }

  setBranchLimit(plan: CommercialPlanAdmin, value: number | string | null): void {
    plan.max_sucursales = value === '' || value === null ? null : Number(value);
  }

  setFeatureLimit(feature: CommercialPlanAdmin['caracteristicas'][number], value: number | string | null): void {
    feature.limite = value === '' || value === null ? null : Number(value);
  }

  planError(id: number): string { return this.errors.get(id) ?? ''; }
  get selectedPlans(): CommercialPlanAdmin[] { return this.plans.filter(plan => plan.id_plan === this.selectedPlanId); }

  save(plan: CommercialPlanAdmin): void {
    const config: CommercialPlanFeatureUpdate[] = [];
    try {
      for (const feature of plan.caracteristicas) {
        const parsed = feature.configuracionTexto?.trim() ? JSON.parse(feature.configuracionTexto) : null;
        if (parsed !== null && (typeof parsed !== 'object' || Array.isArray(parsed))) throw new Error(`La configuración de ${feature.nombre} debe ser un objeto JSON.`);
        config.push({ codigo: feature.codigo, habilitada: feature.habilitada, limite: feature.limite, configuracion: parsed });
      }
    } catch (error) {
      this.errors.set(plan.id_plan, error instanceof Error ? error.message : 'Configuración JSON no válida.'); return;
    }
    const confirm = this.dialog.open(ConfirmDialogComponent, { data: {
      title: 'Guardar plan comercial',
      message: `¿Confirmas guardar los cambios del Plan ${plan.nombre}? Los límites y características se aplicarán en las verificaciones del plan.`,
    } });
    confirm.afterClosed().subscribe(accepted => {
      if (!accepted) return;
      this.busyId = plan.id_plan; this.errors.delete(plan.id_plan);
      const request: CommercialPlanUpdate = { nombre: plan.nombre, descripcion: plan.descripcion, max_sucursales: plan.max_sucursales, activo: plan.activo };
      this.service.update(plan.id_plan, request).subscribe({
        next: updated => this.service.updateFeatures(plan.id_plan, config).subscribe({
          next: complete => this.finishSave(complete),
          error: error => { this.replace(updated); this.finishError(plan.id_plan, error); },
        }),
        error: error => this.finishError(plan.id_plan, error),
      });
    });
  }

  refreshPlan(plan: CommercialPlanAdmin): void {
    this.busyId = plan.id_plan;
    this.service.get(plan.id_plan).subscribe({
      next: fresh => { this.replace(fresh); this.busyId = null; this.errors.delete(plan.id_plan); },
      error: error => this.finishError(plan.id_plan, error),
    });
  }

  private prepare(plan: CommercialPlanAdmin): CommercialPlanAdmin {
    return { ...plan, caracteristicas: plan.caracteristicas.map(feature => ({
      ...feature, configuracionTexto: feature.configuracion ? JSON.stringify(feature.configuracion, null, 2) : '',
    })) };
  }

  private replace(plan: CommercialPlanAdmin): void { this.plans = this.plans.map(item => item.id_plan === plan.id_plan ? this.prepare(plan) : item); }

  private finishSave(plan: CommercialPlanAdmin): void {
    this.replace(plan); this.busyId = null; this.snack.open(`Plan ${plan.nombre} actualizado.`, 'Cerrar', { duration: 3500 });
  }

  private finishError(id: number, error: HttpErrorResponse): void { this.errors.set(id, this.message(error)); this.busyId = null; }

  private message(error: HttpErrorResponse): string {
    const detail = error.error?.detail;
    const serverMessage = typeof detail === 'string' ? detail : detail?.message ?? error.error?.message;
    if (error.status === 401) return 'La sesión expiró. Inicia sesión nuevamente.';
    if (error.status === 403) return 'Solo un administrador de plataforma puede modificar planes.';
    if (error.status === 409) return serverMessage || 'El plan no puede modificarse por sus suscripciones activas.';
    if (error.status === 0) return 'No se pudo conectar con el servicio.';
    return serverMessage || 'No se pudo guardar el plan comercial.';
  }
}
