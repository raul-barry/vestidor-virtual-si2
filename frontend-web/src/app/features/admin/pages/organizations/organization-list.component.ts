import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { FormControl, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { OrganizationAdmin } from '../../models/organization-admin.model';
import { OrganizationAdminService } from '../../services/organization-admin.service';

@Component({
  selector: 'app-organization-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatSelectModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent],
  template: `
    <main class="page">
      <header class="page-heading">
        <div><p class="eyebrow">PLATAFORMA · SAAS</p><h1>Administración de empresas</h1><p class="subtitle">Gestiona las organizaciones y el acceso inicial de cada equipo.</p></div>
        <div class="heading-actions"><button mat-stroked-button type="button" (click)="openSubscriptions()">Suscripciones</button>
          <button mat-flat-button color="primary" type="button" (click)="openProvisioning()">Aprovisionar empresa</button></div>
      </header>
      <section class="panel list-panel" aria-labelledby="list-title">
        <div class="list-heading"><div><p class="eyebrow">ORGANIZACIONES</p><h2 id="list-title">Empresas registradas</h2></div><span class="count">{{source.data.length}} en total</span></div>
        <div class="filters">
          <mat-form-field appearance="outline"><mat-label>Buscar por nombre o slug</mat-label><input matInput [formControl]="search" (input)="applyFilter()"></mat-form-field>
          <mat-form-field appearance="outline"><mat-label>Estado</mat-label><mat-select [formControl]="status" (selectionChange)="applyFilter()"><mat-option value="">Todos</mat-option><mat-option value="ACTIVA">Activas</mat-option><mat-option value="INACTIVA">Suspendidas</mat-option></mat-select></mat-form-field>
        </div>
        @if (loading) { <app-loading-spinner /> }
        @else if (loadError) { <app-error-message /> }
        @else if (!source.data.length) { <app-empty-state message="Todavía no hay empresas registradas." /> }
        @else if (!source.filteredData.length) { <app-empty-state message="No hay empresas que coincidan con esos filtros." /> }
        @else {
          <div class="table-scroll" role="region" aria-label="Empresas registradas" tabindex="0">
            <table mat-table [dataSource]="source">
              <ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Empresa</th><td mat-cell *matCellDef="let row"><strong>{{row.nombre}}</strong><small class="slug">{{row.slug}}</small></td></ng-container>
              <ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let row"><span class="status" [class.inactive]="row.estado === 'INACTIVA'">{{row.estado === 'ACTIVA' ? 'Activa' : 'Suspendida'}}</span></td></ng-container>
              <ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let row"><button mat-button type="button" (click)="openDetail(row)">Ver detalle</button><button mat-button type="button" [color]="row.estado === 'ACTIVA' ? 'warn' : 'primary'" (click)="confirmStatus(row)">{{row.estado === 'ACTIVA' ? 'Suspender' : 'Reactivar'}}</button></td></ng-container>
              <tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row; columns: columns"></tr>
            </table>
          </div>
          <mat-paginator [pageSize]="10" [pageSizeOptions]="[5, 10, 25]" showFirstLastButtons aria-label="Paginación de empresas" />
        }
      </section>
    </main>
  `,
  styles: [`
    .page{max-width:1320px;margin:0 auto;padding:clamp(1.25rem,3vw,2.5rem)}.page-heading,.list-heading{display:flex;align-items:center;justify-content:space-between;gap:1.25rem}.page-heading{margin-bottom:1.5rem}.heading-actions{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}
    .eyebrow{margin:0 0 .45rem;color:var(--primary);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{margin:0;font-size:clamp(1.8rem,3vw,2.5rem);letter-spacing:-.035em;color:var(--ink)}h2{margin:0;color:var(--ink);font-size:1.25rem}.subtitle{margin:.6rem 0 0;color:var(--muted)}
    .panel{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:clamp(1rem,2vw,1.5rem);box-shadow:0 12px 32px #182b4410}.create-panel{margin-bottom:1.25rem}.notice{padding:.8rem 1rem;border-radius:12px;background:var(--primary-soft);color:var(--ink);font-size:.9rem}
    .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem 1.25rem;margin-top:.75rem}.form-actions{grid-column:1/-1;display:flex;justify-content:flex-end;gap:.5rem}.form-error{grid-column:1/-1;color:var(--danger);margin:0}
    .list-heading{margin-bottom:1rem}.count{border-radius:99px;padding:.45rem .75rem;background:#f5f1eb;color:var(--ink);font-size:.83rem;font-weight:700}.filters{display:flex;gap:1rem;align-items:center;flex-wrap:wrap}.filters mat-form-field:first-child{flex:1;min-width:250px}.filters mat-form-field:last-child{width:190px}
    table{width:100%}td,th{padding:.8rem .75rem}td strong,td .slug{display:block}.slug{margin-top:.2rem;color:var(--muted);font-size:.82rem}.status{display:inline-flex;padding:.35rem .65rem;border-radius:99px;background:#e7f4ed;color:#176b43;font-size:.78rem;font-weight:750}.status.inactive{background:#f9e8e6;color:#a63a31}
    @media(max-width:700px){.page-heading{align-items:flex-start;flex-direction:column}.form-grid{grid-template-columns:1fr}.form-actions{grid-column:auto}.filters mat-form-field:last-child{width:100%}}
  `]
})
export class OrganizationListComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly service = inject(OrganizationAdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  private readonly router = inject(Router);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  readonly source = new MatTableDataSource<OrganizationAdmin>([]);
  readonly search = new FormControl('');
  readonly status = new FormControl('');
  readonly columns = ['nombre', 'estado', 'acciones'];
  readonly form = this.fb.group({
    nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    razon_social: ['', Validators.maxLength(200)],
    nit: ['', [Validators.minLength(3), Validators.maxLength(20), Validators.pattern(/^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/)]],
    correo_contacto: ['', [Validators.email, Validators.maxLength(254)]],
    telefono_contacto: ['', [Validators.pattern(/^[+0-9() .-]{6,30}$/)]],
    direccion: ['', Validators.maxLength(255)],
    logo_url: ['', [Validators.pattern(/^https?:\/\/\S+$/i), Validators.maxLength(2048)]],
    slug: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(160), Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]]
  });
  loading = true; saving = false; showCreate = false; loadError = false; formError = '';

  ngOnInit(): void {
    this.source.filterPredicate = (row, filter) => {
      const criteria = JSON.parse(filter) as { search: string; status: string };
      return `${row.nombre} ${row.slug}`.toLowerCase().includes(criteria.search) && (!criteria.status || row.estado === criteria.status);
    };
    this.form.controls.nombre.valueChanges.subscribe((name) => {
      if (!this.form.controls.slug.dirty) this.form.controls.slug.setValue(this.slugify(name), { emitEvent: false });
    });
    this.load();
  }

  load(): void {
    this.loading = true; this.loadError = false;
    this.service.list().subscribe({
      next: (rows) => { this.source.data = rows; this.loading = false; this.applyFilter(); setTimeout(() => this.source.paginator = this.paginator); },
      error: (error: HttpErrorResponse) => { this.loading = false; this.loadError = true; this.showError(error, 'No se pudieron cargar las empresas.'); }
    });
  }

  applyFilter(): void {
    this.source.filter = JSON.stringify({ search: (this.search.value ?? '').trim().toLowerCase(), status: this.status.value ?? '' });
    if (this.source.paginator) this.source.paginator.firstPage();
  }

  create(): void {
    this.formError = '';
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const request = this.form.getRawValue();
    if (this.source.data.some((row) => row.slug.toLowerCase() === request.slug.toLowerCase())) { this.formError = 'Ese slug ya está registrado. Elige otro.'; return; }
    this.saving = true;
    this.service.create(request).subscribe({
      next: (created) => { this.saving = false; this.form.reset(); this.showCreate = false; this.load(); this.snack.open('Empresa registrada.', 'Cerrar', { duration: 3500 }); void this.router.navigate(['/platform/organizations', created.id_organizacion]); },
      error: (error: HttpErrorResponse) => { this.saving = false; this.formError = this.errorText(error, 'No se pudo registrar la empresa.'); }
    });
  }

  openDetail(row: OrganizationAdmin): void {
    const organizationId = Number(row.id_organizacion);
    if (!Number.isInteger(organizationId) || organizationId < 1) {
      this.snack.open('No se pudo identificar la empresa seleccionada.', 'Cerrar', { duration: 5000 });
      return;
    }
    void this.router.navigate(['/platform/organizations', organizationId]).then((navigated) => {
      if (!navigated) this.snack.open('No se pudo abrir el detalle de la empresa.', 'Cerrar', { duration: 5000 });
    }).catch(() => this.snack.open('No se pudo abrir el detalle de la empresa.', 'Cerrar', { duration: 5000 }));
  }

  openSubscriptions(): void { void this.router.navigate(['/platform/subscriptions']); }

  openProvisioning(): void { void this.router.navigate(['/platform/organizations/provision']); }

  confirmStatus(row: OrganizationAdmin): void {
    const next: OrganizationAdmin['estado'] = row.estado === 'ACTIVA' ? 'INACTIVA' : 'ACTIVA';
    const action = next === 'ACTIVA' ? 'reactivar' : 'suspender';
    this.dialog.open(ConfirmDialogComponent, { data: { title: `${action[0].toUpperCase()}${action.slice(1)} empresa`, message: `¿Confirmas ${action} ${row.nombre}?` } }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.service.updateStatus(row.id_organizacion, next).subscribe({
        next: (updated) => { this.source.data = this.source.data.map((item) => item.id_organizacion === updated.id_organizacion ? updated : item); this.applyFilter(); this.snack.open(`Empresa ${next === 'ACTIVA' ? 'reactivada' : 'suspendida'}.`, 'Cerrar', { duration: 3500 }); },
        error: (error: HttpErrorResponse) => this.showError(error, 'No se pudo cambiar el estado de la empresa.')
      });
    });
  }

  private slugify(value: string): string { return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  private errorText(error: HttpErrorResponse, fallback: string): string {
    if (error.status === 403) return 'Tu cuenta no tiene permiso para administrar empresas.';
    const detail = error.error?.detail ?? error.error?.message;
    return typeof detail === 'string' ? detail : fallback;
  }
  private showError(error: HttpErrorResponse, fallback: string): void { this.snack.open(this.errorText(error, fallback), 'Cerrar', { duration: 5000 }); }
}
