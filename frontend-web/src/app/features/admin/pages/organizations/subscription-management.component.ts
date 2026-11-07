import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { OrganizationAdmin } from '../../models/organization-admin.model';
import { SubscriptionAdmin, SubscriptionPlanAdmin, SubscriptionRequestAdmin } from '../../models/subscription-admin.model';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { ErrorMessageComponent } from '../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

interface SubscriptionRow {
  organization: OrganizationAdmin;
  current: SubscriptionAdmin | null;
  error?: HttpErrorResponse;
}

@Component({
  selector: 'app-subscription-management',
  standalone: true,
  imports: [
    DatePipe, RouterLink, ReactiveFormsModule, MatButtonModule, MatCardModule, MatDialogModule,
    MatFormFieldModule, MatSelectModule, MatSnackBarModule, ErrorMessageComponent, LoadingSpinnerComponent,
  ],
  template: `
    <main class="page">
      <a class="back" routerLink="/platform/organizations">← Administración de empresas</a>
      <header class="heading">
        <div><p class="eyebrow">PLATAFORMA · SAAS</p><h1>Suscripciones</h1>
          <p class="subtitle">Consulta planes actuales, asígnalos y revisa el historial de cada empresa.</p></div>
        <button mat-stroked-button type="button" (click)="load()" [disabled]="loading">Actualizar</button>
      </header>

      @if (pageError) { <app-error-message [message]="pageError" /> }
      @if (loading) { <app-loading-spinner /> }
      @else if (!rows.length) { <p class="empty">No hay empresas registradas.</p> }
      @else {
        <section class="panel" aria-labelledby="subscription-list-title">
          <div class="section-heading"><div><p class="eyebrow">ORGANIZACIONES</p><h2 id="subscription-list-title">Estado de suscripción</h2></div><span class="count">{{rows.length}} empresas</span></div>
          <div class="table-scroll" role="region" aria-label="Suscripciones por empresa" tabindex="0">
            <table>
              <thead><tr><th>Empresa</th><th>Estado empresa</th><th>Plan</th><th>Suscripción</th><th>Inicio</th><th>Vencimiento</th><th>Días restantes</th><th></th></tr></thead>
              <tbody>
                @for (row of rows; track row.organization.id_organizacion) {
                  <tr [class.selected]="selected?.organization?.id_organizacion === row.organization.id_organizacion">
                    <td><strong>{{row.organization.nombre}}</strong><small>{{row.organization.slug}}</small></td>
                    <td>{{row.organization.estado === 'ACTIVA' ? 'Activa' : 'Suspendida'}}</td>
                    <td>{{row.error ? 'No disponible' : (row.current?.plan_nombre || 'Sin suscripción')}}</td>
                    <td>@if (row.error) { <span class="muted">Error al consultar</span> } @else if (row.current) { <span class="status">{{row.current.estado}}</span> } @else { <span class="muted">—</span> }</td>
                    <td>{{row.current ? (row.current.fecha_inicio | date:'mediumDate') : '—'}}</td>
                    <td>{{row.current?.fecha_fin ? (row.current?.fecha_fin | date:'mediumDate') : (row.current ? 'Sin vencimiento' : '—')}}</td>
                    <td>{{daysRemaining(row.current) ?? '—'}}</td>
                    <td><button mat-button type="button" (click)="select(row)" [disabled]="busy || detailsLoading">{{selected?.organization?.id_organizacion === row.organization.id_organizacion ? 'Gestionando' : 'Gestionar'}}</button></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      @if (selected) {
        <section class="management-grid" aria-label="Administración de suscripción">
          <mat-card class="management-card">
            <mat-card-header><mat-card-title>{{selected.organization.nombre}}</mat-card-title><mat-card-subtitle>Suscripción actual</mat-card-subtitle></mat-card-header>
            <mat-card-content>
              @if (detailsLoading) { <app-loading-spinner /> }
              @else {
                <p><strong>Estado de empresa:</strong> {{selected.organization.estado === 'ACTIVA' ? 'Activa' : 'Suspendida'}}</p>
                <button mat-stroked-button type="button" (click)="confirmOrganizationStatus()" [disabled]="busy">{{selected.organization.estado === 'ACTIVA' ? 'Suspender empresa' : 'Reactivar empresa'}}</button>
                @if (selected.current) {
                  <div class="current-plan"><span class="status">{{selected.current.estado}}</span><h3>{{selected.current.plan_nombre}}</h3>
                    <p><strong>Inicio:</strong> {{selected.current.fecha_inicio | date:'medium'}}</p>
                    <p><strong>Vencimiento:</strong> {{selected.current.fecha_fin ? (selected.current.fecha_fin | date:'medium') : 'Sin vencimiento'}}</p>
                    @if (daysRemaining(selected.current) !== null) { <p><strong>Días restantes:</strong> {{daysRemaining(selected.current)}}</p> }
                  </div>
                  <button mat-stroked-button color="warn" type="button" (click)="confirmCancel()" [disabled]="busy || selected.current.estado !== 'ACTIVA'">Cancelar suscripción</button>
                } @else {
                  <p class="muted">Esta empresa no tiene una suscripción activa.</p>
                  @if (history.length) { <p class="notice">La siguiente asignación renovará el servicio y conservará el historial anterior.</p> }
                }

                <form (ngSubmit)="savePlan()" class="plan-form">
                  <mat-form-field appearance="outline"><mat-label>{{selected.current ? 'Nuevo plan' : 'Plan'}}</mat-label>
                    <mat-select [formControl]="planControl" required>
                      @for (plan of plans; track plan.id_plan) { <mat-option [value]="plan.id_plan">{{plan.nombre}} · {{plan.max_sucursales === null ? 'Sucursales ilimitadas' : plan.max_sucursales + ' sucursales'}}</mat-option> }
                    </mat-select>
                    @if (planControl.invalid && planControl.touched) { <mat-error>Selecciona un plan.</mat-error> }
                  </mat-form-field>
                  @if (selected.current) { <p class="notice">El cambio finaliza el plan actual y conserva su registro en el historial.</p> }
                  @if (operationError) { <p class="error" role="alert">{{operationError}}</p> }
                  <button mat-flat-button color="primary" type="submit" [disabled]="busy || planControl.invalid || plansLoading || planUnchanged">
                    {{busy ? 'Procesando…' : (selected.current ? 'Cambiar plan' : (history.length ? 'Renovar suscripción' : 'Asignar plan'))}}
                  </button>
                </form>
              }
            </mat-card-content>
          </mat-card>

          <mat-card class="history-card">
            <mat-card-header><mat-card-title>Historial de suscripciones</mat-card-title><mat-card-subtitle>{{selected.organization.nombre}}</mat-card-subtitle></mat-card-header>
            <mat-card-content>
              @if (historyLoading) { <app-loading-spinner /> }
              @else if (historyError) { <app-error-message [message]="historyError" /> }
              @else if (!history.length) { <p class="muted">Todavía no hay suscripciones registradas.</p> }
              @else {
                <div class="table-scroll"><table><thead><tr><th>Plan</th><th>Estado</th><th>Inicio</th><th>Finalización</th></tr></thead>
                  <tbody>@for (subscription of history; track subscription.id_suscripcion) {
                    <tr><td>{{subscription.plan_nombre}}</td><td>{{subscription.estado}}</td><td>{{subscription.fecha_inicio | date:'mediumDate'}}</td>
                      <td>{{subscription.fecha_fin ? (subscription.fecha_fin | date:'mediumDate') : (subscription.estado === 'ACTIVA' ? 'Sin vencimiento' : '—')}}</td></tr>
                  }</tbody>
                </table></div>
              }
            </mat-card-content>
          </mat-card>
        </section>
      }
    </main>
  `,
  styles: [`
    .page{max-width:1320px;margin:0 auto;padding:clamp(1.25rem,3vw,2.5rem)}.back{display:inline-block;margin-bottom:1.1rem;color:var(--primary);font-weight:700;text-decoration:none}.heading,.section-heading{display:flex;align-items:center;justify-content:space-between;gap:1rem}.heading{margin-bottom:1.4rem}.eyebrow{margin:0 0 .4rem;color:var(--primary);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{margin:0;color:var(--ink);font-size:clamp(1.8rem,3vw,2.5rem)}h2{margin:0;color:var(--ink);font-size:1.25rem}.subtitle{color:var(--muted)}.panel{padding:clamp(1rem,2vw,1.5rem);border:1px solid var(--border);border-radius:20px;background:var(--surface);box-shadow:0 12px 32px #182b4410}.section-heading{margin-bottom:1rem}.count{padding:.4rem .7rem;border-radius:99px;background:#f5f1eb;font-size:.83rem;font-weight:700}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{text-align:left;padding:.8rem .65rem;border-bottom:1px solid var(--border);white-space:nowrap}td strong,td small{display:block}td small{margin-top:.2rem;color:var(--muted)}tr.selected{background:var(--primary-soft)}.status{display:inline-flex;padding:.32rem .6rem;border-radius:99px;background:#e7f4ed;color:#176b43;font-size:.78rem;font-weight:750}.muted{color:var(--muted)}.management-grid{display:grid;grid-template-columns:minmax(280px,.8fr) minmax(0,1.2fr);gap:1.2rem;margin-top:1.2rem}mat-card{border:1px solid var(--border);border-radius:18px}.management-card mat-card-content,.history-card mat-card-content{padding-top:1rem}.current-plan{margin-bottom:1.1rem}.current-plan h3{margin:.8rem 0;color:var(--ink)}.current-plan p{margin:.45rem 0}.plan-form{display:grid;gap:.7rem;margin-top:1rem}.plan-form mat-form-field{width:100%}.plan-form button{justify-self:start}.notice{margin:0;padding:.75rem;border-radius:12px;background:var(--primary-soft);font-size:.88rem}.error{margin:0;color:var(--danger)}.empty{padding:1.4rem;color:var(--muted)}@media(max-width:820px){.management-grid{grid-template-columns:1fr}}@media(max-width:600px){.heading{align-items:flex-start;flex-direction:column}.section-heading{align-items:flex-start}}
  `],
})
export class SubscriptionManagementComponent implements OnInit {
  private readonly organizations = inject(OrganizationAdminService);
  private readonly subscriptions = inject(SubscriptionAdminService);
  private readonly route = inject(ActivatedRoute);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);

  readonly planControl = new FormControl<number | null>(null, Validators.required);
  rows: SubscriptionRow[] = [];
  plans: SubscriptionPlanAdmin[] = [];
  selected: SubscriptionRow | null = null;
  history: SubscriptionAdmin[] = [];
  loading = true;
  plansLoading = true;
  detailsLoading = false;
  historyLoading = false;
  busy = false;
  pageError = '';
  historyError = '';
  operationError = '';

  ngOnInit(): void {
    this.load();
  }

  get planUnchanged(): boolean {
    return !!this.selected?.current && this.planControl.value === this.selected.current.plan_id;
  }

  daysRemaining(subscription: SubscriptionAdmin | null): number | null {
    if (!subscription?.fecha_fin || subscription.estado !== 'ACTIVA') return null;
    const remaining = new Date(subscription.fecha_fin).getTime() - Date.now();
    return Math.max(0, Math.ceil(remaining / 86_400_000));
  }

  load(): void {
    this.loading = true;
    this.plansLoading = true;
    this.pageError = '';
    forkJoin({ organizations: this.organizations.list(), plans: this.subscriptions.listPlans() }).subscribe({
      next: ({ organizations, plans }) => {
        this.plans = plans;
        this.plansLoading = false;
        if (!organizations.length) {
          this.rows = [];
          this.loading = false;
          return;
        }
        forkJoin(organizations.map((organization) => this.subscriptions.current(organization.id_organizacion).pipe(
          map((current) => ({ organization, current } as SubscriptionRow)),
          catchError((error: HttpErrorResponse) => of({ organization, current: null, error } as SubscriptionRow)),
        ))).subscribe({
          next: (rows) => {
            this.rows = rows;
            this.loading = false;
            const selectedId = Number(this.route.snapshot.queryParamMap.get('organizationId'));
            const row = rows.find((item) => item.organization.id_organizacion === selectedId);
            if (row) this.select(row);
            else if (this.selected) this.selected = rows.find((item) => item.organization.id_organizacion === this.selected?.organization.id_organizacion) ?? null;
          },
          error: (error: HttpErrorResponse) => { this.loading = false; this.pageError = this.errorMessage(error); },
        });
      },
      error: (error: HttpErrorResponse) => {
        this.loading = false;
        this.plansLoading = false;
        this.pageError = this.errorMessage(error);
      },
    });
  }

  select(row: SubscriptionRow): void {
    this.selected = row;
    this.operationError = row.error ? this.errorMessage(row.error) : '';
    this.historyError = '';
    this.planControl.setValue(row.current?.plan_id ?? null);
    this.refreshSelected();
  }

  savePlan(): void {
    if (!this.selected) return;
    if (this.planControl.invalid || this.planControl.value === null) {
      this.planControl.markAsTouched();
      return;
    }
    const selected = this.selected;
    const request: SubscriptionRequestAdmin = { plan_id: this.planControl.value };
    if (!selected.current) {
      this.performPlanChange(selected, request, false);
      return;
    }
    const nextPlan = this.plans.find((plan) => plan.id_plan === request.plan_id);
    this.dialog.open(ConfirmDialogComponent, { data: {
      title: 'Cambiar plan',
      message: `¿Confirmas cambiar ${selected.organization.nombre} de ${selected.current.plan_nombre} a ${nextPlan?.nombre ?? 'el plan seleccionado'}? El plan actual pasará al historial.`,
    } }).afterClosed().subscribe((confirmed) => {
      if (confirmed) this.performPlanChange(selected, request, true);
    });
  }

  confirmCancel(): void {
    const current = this.selected?.current;
    if (!this.selected || !current) return;
    const selected = this.selected;
    this.dialog.open(ConfirmDialogComponent, { data: {
      title: 'Cancelar suscripción',
      message: `¿Confirmas cancelar el plan ${current.plan_nombre} de ${selected.organization.nombre}?`,
    } }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.busy = true;
      this.operationError = '';
      this.subscriptions.cancel(selected.organization.id_organizacion).subscribe({
        next: () => { this.busy = false; this.snack.open('Suscripción cancelada.', 'Cerrar', { duration: 3500 }); this.refreshSelected(); },
        error: (error: HttpErrorResponse) => { this.busy = false; this.operationError = this.errorMessage(error); },
      });
    });
  }

  confirmOrganizationStatus(): void {
    if (!this.selected) return;
    const selected = this.selected;
    const next: OrganizationAdmin['estado'] = selected.organization.estado === 'ACTIVA' ? 'INACTIVA' : 'ACTIVA';
    const verb = next === 'ACTIVA' ? 'reactivar' : 'suspender';
    this.dialog.open(ConfirmDialogComponent, { data: {
      title: `${verb[0].toUpperCase()}${verb.slice(1)} empresa`,
      message: `¿Confirmas ${verb} ${selected.organization.nombre}?`,
    } }).afterClosed().subscribe(confirmed => {
      if (!confirmed) return;
      this.busy = true;
      this.organizations.updateStatus(selected.organization.id_organizacion, next).subscribe({
        next: updated => {
          this.busy = false;
          const refreshed = { ...selected, organization: updated };
          this.selected = refreshed;
          this.rows = this.rows.map(row => row.organization.id_organizacion === updated.id_organizacion ? refreshed : row);
          this.snack.open(`Empresa ${next === 'ACTIVA' ? 'reactivada' : 'suspendida'}.`, 'Cerrar', { duration: 3500 });
        },
        error: error => { this.busy = false; this.operationError = this.errorMessage(error); },
      });
    });
  }

  private performPlanChange(row: SubscriptionRow, request: SubscriptionRequestAdmin, changing: boolean): void {
    this.busy = true;
    this.operationError = '';
    const request$ = changing
      ? this.subscriptions.change(row.organization.id_organizacion, request)
      : this.subscriptions.assign(row.organization.id_organizacion, request);
    request$.subscribe({
      next: () => {
        this.busy = false;
        this.snack.open(changing ? 'Plan actualizado.' : (this.history.length ? 'Suscripción renovada.' : 'Plan asignado.'), 'Cerrar', { duration: 3500 });
        this.refreshSelected();
      },
      error: (error: HttpErrorResponse) => { this.busy = false; this.operationError = this.errorMessage(error); },
    });
  }

  private refreshSelected(): void {
    const organization = this.selected?.organization;
    if (!organization) return;
    const id = organization.id_organizacion;
    this.detailsLoading = true;
    this.historyLoading = true;
    this.historyError = '';
    forkJoin({ current: this.subscriptions.current(id), history: this.subscriptions.history(id) }).subscribe({
      next: ({ current, history }) => {
        const updated: SubscriptionRow = { organization, current };
        this.rows = this.rows.map((row) => row.organization.id_organizacion === id ? updated : row);
        this.selected = updated;
        this.history = history;
        this.planControl.setValue(current?.plan_id ?? null);
        this.detailsLoading = false;
        this.historyLoading = false;
        this.operationError = '';
      },
      error: (error: HttpErrorResponse) => {
        this.detailsLoading = false;
        this.historyLoading = false;
        this.historyError = this.errorMessage(error);
      },
    });
  }

  private errorMessage(error: HttpErrorResponse): string {
    if (error.status === 401) return 'La sesión expiró. Inicia sesión nuevamente.';
    if (error.status === 403) return 'No tienes permisos para administrar suscripciones de plataforma.';
    if (error.status === 409) return this.detailMessage(error) || 'La suscripción cambió o ya existe una activa. Actualiza la información e inténtalo nuevamente.';
    if (error.status === 0) return 'No se pudo conectar con el servicio. Verifica tu conexión e inténtalo nuevamente.';
    return this.detailMessage(error) || 'No se pudo completar la operación de suscripción.';
  }

  private detailMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail.message === 'string') return detail.message;
    if (typeof error.error?.message === 'string') return error.error.message;
    return '';
  }
}
