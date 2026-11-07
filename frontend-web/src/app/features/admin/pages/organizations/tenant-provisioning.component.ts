import { Component, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';
import { OrganizationAdminRequest, TenantProvisionRequest, TenantProvisionResult } from '../../models/organization-admin.model';
import { SubscriptionPlanAdmin } from '../../models/subscription-admin.model';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-tenant-provisioning', standalone: true,
  imports: [DatePipe, RouterLink, ReactiveFormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule, LoadingSpinnerComponent],
  template: `
    <main class="page">
      <a class="back" routerLink="/platform/organizations">← Administración de empresas</a>
      <header><p class="eyebrow">PLATAFORMA · SAAS</p><h1>Aprovisionar empresa</h1><p class="subtitle">Configura la organización, su administrador y la suscripción en una sola operación.</p></header>
      @if (result) {
        <mat-card class="summary"><mat-card-header><mat-card-title>Empresa aprovisionada</mat-card-title></mat-card-header><mat-card-content>
          <p><strong>Empresa:</strong> {{result.organization.nombre}} ({{result.organization.slug}})</p>
          <p><strong>Administrador:</strong> {{result.administrator.nombres}} {{result.administrator.apellidos}} · {{result.administrator.correo}}</p>
          <p><strong>Plan:</strong> {{result.subscription.plan_nombre}} · {{result.subscription.estado}}</p>
          <p><strong>Vigencia:</strong> {{result.subscription.fecha_inicio | date:'mediumDate'}} a {{result.subscription.fecha_fin ? (result.subscription.fecha_fin | date:'mediumDate') : 'Sin vencimiento'}}</p>
          <button mat-flat-button color="primary" type="button" (click)="openDetail()">Ver empresa</button>
          <button mat-button type="button" routerLink="/platform/organizations">Volver al listado</button>
        </mat-card-content></mat-card>
      } @else {
        <nav class="steps" aria-label="Pasos de aprovisionamiento">@for (label of labels; track label; let index = $index) { <span [class.current]="step === index + 1" [class.done]="step > index + 1">{{index + 1}}. {{label}}</span> }</nav>
        @if (plansLoading) { <app-loading-spinner /> }
        @else if (plansError) { <p class="error" role="alert">No se pudieron cargar los planes disponibles.</p> }
        <form [formGroup]="form" (ngSubmit)="step === 4 ? submit() : next()">
          @if (step === 1) {
            <mat-card><mat-card-header><mat-card-title>1. Datos de empresa</mat-card-title></mat-card-header><mat-card-content class="fields" formGroupName="organization">
              <mat-form-field appearance="outline"><mat-label>Nombre comercial</mat-label><input matInput formControlName="nombre"><mat-error>Ingresa al menos 2 caracteres.</mat-error></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Razón social</mat-label><input matInput formControlName="razon_social"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>NIT</mat-label><input matInput formControlName="nit"><mat-error>Formato de NIT no válido.</mat-error></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Correo de contacto</mat-label><input matInput type="email" formControlName="correo_contacto"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Teléfono de contacto</mat-label><input matInput formControlName="telefono_contacto"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Dirección</mat-label><input matInput formControlName="direccion"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Logo URL</mat-label><input matInput formControlName="logo_url"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Slug</mat-label><input matInput formControlName="slug"><mat-error>Usa minúsculas, números y guiones.</mat-error></mat-form-field>
            </mat-card-content></mat-card>
          }
          @if (step === 2) {
            <mat-card><mat-card-header><mat-card-title>2. Administrador inicial</mat-card-title></mat-card-header><mat-card-content class="fields" formGroupName="administrator">
              <mat-form-field appearance="outline"><mat-label>Nombres</mat-label><input matInput formControlName="nombres" autocomplete="given-name"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos" autocomplete="family-name"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Correo de acceso</mat-label><input matInput type="email" formControlName="correo" autocomplete="email"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Teléfono</mat-label><input matInput formControlName="telefono" autocomplete="tel"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Contraseña temporal</mat-label><input matInput type="password" formControlName="password" autocomplete="new-password"><mat-hint>Mínimo 12 caracteres.</mat-hint></mat-form-field>
            </mat-card-content></mat-card>
          }
          @if (step === 3) {
            <mat-card><mat-card-header><mat-card-title>3. Selección del plan</mat-card-title></mat-card-header><mat-card-content>
              <mat-form-field appearance="outline" class="wide"><mat-label>Plan comercial</mat-label><mat-select formControlName="plan_id"><mat-option [value]="0">Selecciona un plan</mat-option>@for (plan of plans; track plan.id_plan) { <mat-option [value]="plan.id_plan">{{plan.nombre}} · {{plan.max_sucursales === null ? 'Sin límite fijo' : plan.max_sucursales + ' sucursales'}}</mat-option> }</mat-select><mat-error>Selecciona un plan activo.</mat-error></mat-form-field>
              @if (selectedPlan) { <p>{{selectedPlan.descripcion || 'Plan activo'}} · {{selectedPlan.caracteristicas.length}} características configuradas.</p> }
            </mat-card-content></mat-card>
          }
          @if (step === 4) {
            <mat-card><mat-card-header><mat-card-title>4. Configuración de suscripción</mat-card-title></mat-card-header><mat-card-content>
              <p>La suscripción comenzará al confirmar el aprovisionamiento.</p>
              <mat-form-field appearance="outline"><mat-label>Fecha de vencimiento (opcional)</mat-label><input matInput type="date" formControlName="fecha_fin"><mat-hint>Déjala vacía para una vigencia sin fecha de fin.</mat-hint></mat-form-field>
              @if (selectedPlan) { <section class="review"><h3>Resumen de configuración</h3><p><strong>Empresa:</strong> {{form.controls.organization.controls.nombre.value}}</p><p><strong>Administrador:</strong> {{form.controls.administrator.controls.nombres.value}} {{form.controls.administrator.controls.apellidos.value}} · {{form.controls.administrator.controls.correo.value}}</p><p><strong>Plan:</strong> {{selectedPlan.nombre}}</p><p><strong>Vencimiento:</strong> {{form.controls.fecha_fin.value || 'Sin vencimiento'}}</p></section> }
            </mat-card-content></mat-card>
          }
          @if (error) { <p class="error" role="alert">{{error}}</p> }
          <div class="actions"><button mat-button type="button" routerLink="/platform/organizations">Cancelar</button><span></span>@if (step > 1) { <button mat-stroked-button type="button" (click)="step = step - 1" [disabled]="saving">Anterior</button> }<button mat-flat-button color="primary" type="submit" [disabled]="saving || plansLoading || plansError">{{saving ? 'Aprovisionando…' : (step === 4 ? 'Confirmar aprovisionamiento' : 'Continuar')}}</button></div>
        </form>
      }
    </main>
  `,
  styles: [`
    .page{max-width:1000px;margin:auto;padding:clamp(1.25rem,3vw,2.5rem)}.back{display:inline-block;margin-bottom:1rem;color:var(--primary);font-weight:700;text-decoration:none}header{margin-bottom:1.4rem}.eyebrow{color:var(--primary);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{margin:.2rem 0;color:var(--ink)}.subtitle{color:var(--muted)}.steps{display:flex;gap:.5rem;flex-wrap:wrap;margin:1.5rem 0}.steps span{padding:.55rem .75rem;border-radius:99px;background:#f3f0eb;color:var(--muted);font-size:.85rem}.steps .current{background:var(--primary);color:white}.steps .done{background:#e7f4ed;color:#176b43}.fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.25rem 1rem;padding-top:1rem}.wide{width:min(100%,520px);margin-top:1rem}.review,.summary{margin-top:1rem}.review{padding:1rem;border-radius:12px;background:#f7f5f1}.actions{display:flex;align-items:center;gap:.5rem;margin-top:1rem}.actions span{flex:1}.error{color:var(--danger)}mat-card{border-radius:18px}@media(max-width:680px){.fields{grid-template-columns:1fr}.steps{display:grid;grid-template-columns:1fr 1fr}}
  `]
})
export class TenantProvisioningComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly organizations = inject(OrganizationAdminService);
  private readonly subscriptions = inject(SubscriptionAdminService);
  private readonly router = inject(Router);
  readonly labels = ['Empresa', 'Administrador', 'Plan', 'Suscripción'];
  readonly form = this.fb.group({
    organization: this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
      razon_social: ['', Validators.maxLength(200)], nit: ['', [Validators.minLength(3), Validators.maxLength(20), Validators.pattern(/^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/)]],
      correo_contacto: ['', [Validators.email, Validators.maxLength(254)]], telefono_contacto: ['', [Validators.pattern(/^[+0-9() .-]{6,30}$/)]],
      direccion: ['', Validators.maxLength(255)], logo_url: ['', [Validators.pattern(/^https?:\/\/\S+$/i), Validators.maxLength(2048)]],
      slug: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(160), Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]]
    }),
    administrator: this.fb.group({ nombres: ['', [Validators.required, Validators.maxLength(100)]], apellidos: ['', [Validators.required, Validators.maxLength(100)]],
      correo: ['', [Validators.required, Validators.email, Validators.maxLength(255)]], telefono: [''], password: ['', [Validators.required, Validators.minLength(12), Validators.maxLength(128)]] }),
    plan_id: [0, [Validators.required, Validators.min(1)]], fecha_fin: ['']
  });
  plans: SubscriptionPlanAdmin[] = [];
  step = 1; plansLoading = true; plansError = false; saving = false; error = '';
  result: TenantProvisionResult | null = null;

  ngOnInit(): void {
    this.subscriptions.listPlans().subscribe({ next: plans => { this.plans = plans; this.plansLoading = false; }, error: () => { this.plansLoading = false; this.plansError = true; } });
    this.form.controls.organization.controls.nombre.valueChanges.subscribe(value => {
      const slug = this.form.controls.organization.controls.slug;
      if (!slug.dirty) slug.setValue(this.slugify(value), { emitEvent: false });
    });
  }

  get selectedPlan(): SubscriptionPlanAdmin | undefined { return this.plans.find(plan => plan.id_plan === this.form.controls.plan_id.value); }

  next(): void {
    const group = this.step === 1 ? this.form.controls.organization : this.step === 2 ? this.form.controls.administrator : this.form.controls.plan_id;
    if (group.invalid) { group.markAllAsTouched(); return; }
    if (this.step < 4) this.step += 1;
  }

  submit(): void {
    if (this.form.controls.fecha_fin.value) {
      const end = new Date(`${this.form.controls.fecha_fin.value}T23:59:59Z`);
      if (Number.isNaN(end.getTime()) || end.getTime() <= Date.now()) { this.error = 'La fecha de vencimiento debe ser futura.'; return; }
    }
    if (this.form.invalid || !this.selectedPlan) { this.form.markAllAsTouched(); this.error = 'Revisa los datos de los cuatro pasos.'; return; }
    this.error = ''; this.saving = true;
    const administrator: OrganizationAdminRequest = this.form.controls.administrator.getRawValue();
    const organization = this.form.controls.organization.getRawValue();
    const request: TenantProvisionRequest = {
      organization: { ...organization, razon_social: organization.razon_social || null, nit: organization.nit || null,
        correo_contacto: organization.correo_contacto || null, telefono_contacto: organization.telefono_contacto || null,
        direccion: organization.direccion || null, logo_url: organization.logo_url || null }, administrator,
      subscription: { plan_id: this.form.controls.plan_id.value,
        fecha_fin: this.form.controls.fecha_fin.value ? new Date(`${this.form.controls.fecha_fin.value}T23:59:59Z`).toISOString() : null }
    };
    this.organizations.provision(request).subscribe({
      next: result => { this.result = result; this.saving = false; this.form.controls.administrator.controls.password.reset(''); },
      error: (e: HttpErrorResponse) => { this.saving = false; this.error = e.status === 401 ? 'La sesión expiró. Inicia sesión nuevamente.' : e.status === 403 ? 'Solo el administrador de plataforma puede aprovisionar empresas.' : e.status === 409 ? 'El NIT, slug o correo ya está registrado, o existe un conflicto de suscripción.' : e.status === 422 ? 'Revisa los formatos y fechas indicados.' : 'No se pudo completar el aprovisionamiento. No se guardaron cambios parciales.'; }
    });
  }

  openDetail(): void { if (this.result) void this.router.navigate(['/platform/organizations', this.result.organization.id_organizacion]); }
  private slugify(value: string): string { return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
}
