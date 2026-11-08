import { Component, OnInit, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { DatePipe } from '@angular/common';
import { OrganizationAdmin, OrganizationBranchAdmin, OrganizationUserAdmin, UpdateOrganizationRequest } from '../../models/organization-admin.model';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { OrganizationUsageService } from '../../services/organization-usage.service';
import { OrganizationUsage } from '../../models/organization-usage.model';
import { OrganizationActivity, OrganizationActivityPage } from '../../models/organization-activity.model';
import { OrganizationActivityService } from '../../services/organization-activity.service';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';
import { ErrorMessageComponent } from '../../shared/components/error-message/error-message.component';

@Component({
  selector: 'app-organization-detail', standalone: true,
  imports: [RouterLink, FormsModule, ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSnackBarModule, MatCardModule, DatePipe, LoadingSpinnerComponent, ErrorMessageComponent],
  template: `
    <main class="page">
      <a routerLink="/platform/organizations" class="back">← Empresas</a>
      @if (loading) { <app-loading-spinner /> }
      @else if (error || !organization) { <app-error-message message="No se pudo cargar esta empresa." /> }
      @else {
        <header class="heading"><div><p class="eyebrow">ADMINISTRACIÓN SAAS</p><h1>{{organization.nombre}}</h1><p class="slug">{{organization.slug}}</p></div>
          <div class="heading-actions"><button mat-stroked-button type="button" (click)="toggleProfileEdit()">{{editingProfile ? 'Cancelar edición' : 'Editar información'}}</button>
          <button mat-flat-button [color]="organization.estado === 'ACTIVA' ? 'warn' : 'primary'" (click)="confirmStatus()">{{organization.estado === 'ACTIVA' ? 'Suspender empresa' : 'Reactivar empresa'}}</button></div></header>
        <section class="grid">
          <mat-card><mat-card-header><mat-card-title>Información general</mat-card-title></mat-card-header><mat-card-content>
            <p><strong>ID:</strong> {{organization.id_organizacion}}</p><p><strong>Nombre comercial:</strong> {{organization.nombre}}</p><p><strong>Razón social:</strong> {{organization.razon_social || 'No registrada'}}</p>
            <p><strong>NIT:</strong> {{organization.nit || 'No registrado'}}</p><p><strong>Correo de contacto:</strong> {{organization.correo_contacto || 'No registrado'}}</p><p><strong>Teléfono:</strong> {{organization.telefono_contacto || 'No registrado'}}</p>
            <p><strong>Dirección:</strong> {{organization.direccion || 'No registrada'}}</p><p><strong>Slug:</strong> {{organization.slug}}</p><p><strong>Estado:</strong> <span class="status" [class.inactive]="organization.estado !== 'ACTIVA'">{{organization.estado === 'ACTIVA' ? 'Activa' : 'Suspendida'}}</span></p>
            <p><strong>Creación:</strong> {{organization.fecha_creacion ? (organization.fecha_creacion | date:'medium') : 'No registrada'}}</p><p><strong>Actualización:</strong> {{organization.fecha_actualizacion ? (organization.fecha_actualizacion | date:'medium') : 'No registrada'}}</p>
            <p><strong>Logo:</strong> @if (organization.logo_url) { <a [href]="organization.logo_url" target="_blank" rel="noopener noreferrer">Abrir logo</a> } @else { No registrado }</p>
          </mat-card-content></mat-card>
          @if (editingProfile) {
            <mat-card><mat-card-header><mat-card-title>Editar información empresarial</mat-card-title></mat-card-header><mat-card-content>
              <form [formGroup]="profileForm" (ngSubmit)="saveProfile()" class="profile-form">
                <mat-form-field appearance="outline"><mat-label>Nombre comercial</mat-label><input matInput formControlName="nombre"><mat-error>Ingresa al menos 2 caracteres.</mat-error></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Razón social</mat-label><input matInput formControlName="razon_social"></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>NIT</mat-label><input matInput formControlName="nit"><mat-error>Usa de 3 a 20 letras, números o guiones.</mat-error></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Correo de contacto</mat-label><input matInput type="email" formControlName="correo_contacto"><mat-error>Ingresa un correo válido.</mat-error></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Teléfono de contacto</mat-label><input matInput formControlName="telefono_contacto"><mat-error>Ingresa un teléfono válido.</mat-error></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Dirección</mat-label><input matInput formControlName="direccion"></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>URL del logo</mat-label><input matInput type="url" formControlName="logo_url"><mat-error>Usa una URL http o https.</mat-error></mat-form-field>
                <mat-form-field appearance="outline"><mat-label>Slug público</mat-label><input matInput formControlName="slug"><mat-error>Usa minúsculas, números y guiones.</mat-error></mat-form-field>
                @if (profileError) { <p class="form-error" role="alert">{{profileError}}</p> }
                <div class="form-actions"><button mat-flat-button color="primary" [disabled]="profileForm.invalid || !profileForm.dirty || profileSaving">{{profileSaving ? 'Guardando…' : 'Guardar cambios'}}</button></div>
              </form>
            </mat-card-content></mat-card>
          }
          <mat-card style="grid-column: 1 / -1"><mat-card-header><mat-card-title>Uso y consumo</mat-card-title><mat-card-subtitle>Métricas operativas de {{organization.nombre}}</mat-card-subtitle></mat-card-header><mat-card-content>
            <form (ngSubmit)="loadUsageForPeriod()" style="display:flex;align-items:end;flex-wrap:wrap;gap:.8rem;margin-bottom:1rem">
              <label>Desde <input type="date" name="usageFrom" [(ngModel)]="usageFrom"></label>
              <label>Hasta <input type="date" name="usageUntil" [(ngModel)]="usageUntil"></label>
              <button mat-stroked-button type="submit" [disabled]="usageLoading">{{usageLoading ? 'Consultando…' : 'Consultar período'}}</button>
            </form>
            @if (usageError) { <p class="form-error" role="alert">{{usageError}}</p> }
            @if (usageLoading) { <app-loading-spinner /> }
            @else if (usage) {
              <div class="grid">
                <div><p><strong>Plan:</strong> {{usage.plan_nombre || 'Sin plan asignado'}}</p><p><strong>Suscripción:</strong> {{usage.estado_suscripcion}}</p><p><strong>Fechas:</strong> {{usage.fecha_inicio_suscripcion ? (usage.fecha_inicio_suscripcion | date:'mediumDate') : '—'}} a {{usage.fecha_fin_suscripcion ? (usage.fecha_fin_suscripcion | date:'mediumDate') : 'Sin vencimiento'}}</p></div>
                <div><p><strong>Sucursales activas:</strong> {{usage.sucursales_activas}} / {{usage.limite_sucursales === null ? (usage.plan_nombre ? 'Sin límite' : '—') : usage.limite_sucursales}}</p><p><strong>Usuarios activos:</strong> {{usage.usuarios_activos}}</p><p><strong>Productos registrados:</strong> {{usage.productos_registrados}}</p></div>
                <div><p><strong>Pedidos del período:</strong> {{usage.pedidos_periodo}}</p><p><strong>Ventas pagadas del período:</strong> Bs {{usage.ventas_periodo}}</p><p><strong>Reservas del período:</strong> {{usage.reservas_periodo}}</p></div>
                <div><p><strong>Inventario disponible:</strong> {{usage.inventario_disponible}}</p><p><strong>Reservado:</strong> {{usage.inventario_reservado}}</p><p><strong>Vendido:</strong> {{usage.inventario_vendido}}</p></div>
              </div>
            }
          </mat-card-content></mat-card>
          <mat-card style="grid-column:1/-1"><mat-card-header><mat-card-title>Historial de actividad</mat-card-title><mat-card-subtitle>Eventos registrados desde la activación de la auditoría.</mat-card-subtitle></mat-card-header><mat-card-content>
            <form (ngSubmit)="loadActivity(true)" style="display:flex;align-items:end;flex-wrap:wrap;gap:.8rem;margin-bottom:1rem">
              <label>Desde <input type="date" name="activityFrom" [(ngModel)]="activityFrom"></label>
              <label>Hasta <input type="date" name="activityUntil" [(ngModel)]="activityUntil"></label>
              <label>Tipo <select name="activityType" [(ngModel)]="activityType"><option value="">Todos</option>@for (kind of activityTypes; track kind) { <option [value]="kind">{{kind}}</option> }</select></label>
              <label>ID usuario <input type="number" min="1" name="activityUser" [(ngModel)]="activityUser"></label>
              <button mat-stroked-button type="submit" [disabled]="activityLoading">Filtrar</button>
            </form>
            @if (activityError) { <p class="form-error" role="alert">{{activityError}}</p> }
            @if (activityLoading) { <app-loading-spinner /> }
            @else if (!activity.length) { <p class="muted">No hay actividad para los filtros seleccionados.</p> }
            @else { <div class="table-scroll"><table><thead><tr><th>Fecha y hora</th><th>Usuario responsable</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Resultado</th></tr></thead><tbody>@for (item of activity; track item.id) { <tr><td>{{item.fecha_hora | date:'medium'}}</td><td>{{actorLabel(item.usuario_id)}}</td><td>{{item.rol}}</td><td>{{item.accion}}</td><td>{{item.entidad}} {{item.entidad_id || ''}}</td><td>{{item.resultado}}</td></tr> }</tbody></table></div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-top:1rem"><span>{{activityPage?.total ?? 0}} registros</span><div><button mat-stroked-button type="button" [disabled]="activityOffset === 0" (click)="activityOffset = activityOffset - activityLimit; loadActivity()">Anterior</button> <button mat-stroked-button type="button" [disabled]="activityOffset + activityLimit >= (activityPage?.total ?? 0)" (click)="activityOffset = activityOffset + activityLimit; loadActivity()">Siguiente</button></div></div> }
          </mat-card-content></mat-card>
          <mat-card><mat-card-header><mat-card-title>Sucursales</mat-card-title></mat-card-header><mat-card-content>
            @if (branchesLoading) { <app-loading-spinner /> }
            @else if (branchesError) { <app-error-message message="No se pudieron cargar las sucursales." /> }
            @else if (!branches.length) { <p class="muted">Esta organización no tiene sucursales registradas.</p> }
            @else { <div class="table-scroll"><table><thead><tr><th>ID</th><th>Nombre</th><th>Dirección</th><th>Ciudad</th><th>Estado</th></tr></thead><tbody>@for (branch of branches; track branch.id_sucursal) { <tr><td>{{branch.id_sucursal}}</td><td>{{branch.nombre}}</td><td>{{branch.direccion}}</td><td>{{branch.ciudad}}</td><td>{{branch.estado}}</td></tr> }</tbody></table></div> }
          </mat-card-content></mat-card>
          <mat-card><mat-card-header><mat-card-title>Usuarios</mat-card-title></mat-card-header><mat-card-content>
            @if (usersLoading) { <app-loading-spinner /> }
            @else if (usersError) { <app-error-message message="No se pudieron cargar los usuarios." /> }
            @else if (!users.length) { <p class="muted">Esta organización no tiene usuarios registrados.</p> }
            @else { <div class="table-scroll"><table><thead><tr><th>ID</th><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Registro</th></tr></thead><tbody>@for (user of users; track user.id_usuario) { <tr><td>{{user.id_usuario}}</td><td>{{user.nombre}}</td><td>{{user.correo}}</td><td>{{user.rol}}</td><td>{{user.estado}}</td><td>{{user.fecha_registro | date:'mediumDate'}}</td></tr> }</tbody></table></div> }
          </mat-card-content></mat-card>
          <mat-card><mat-card-header><mat-card-title>Administrador inicial</mat-card-title><mat-card-subtitle>Crea el acceso principal de esta empresa.</mat-card-subtitle></mat-card-header><mat-card-content>
            <form [formGroup]="form" (ngSubmit)="createAdministrator()">
              <mat-form-field appearance="outline"><mat-label>Nombres</mat-label><input matInput formControlName="nombres" autocomplete="given-name"><mat-error>Ingresa los nombres.</mat-error></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos" autocomplete="family-name"><mat-error>Ingresa los apellidos.</mat-error></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Correo</mat-label><input matInput type="email" formControlName="correo" autocomplete="email"><mat-error>Ingresa un correo válido.</mat-error></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Teléfono (opcional)</mat-label><input matInput formControlName="telefono" autocomplete="tel"></mat-form-field>
              <mat-form-field appearance="outline"><mat-label>Contraseña temporal</mat-label><input matInput type="password" formControlName="password" autocomplete="new-password"><mat-hint>Mínimo 12 caracteres. Entrégala de forma segura.</mat-hint><mat-error>Usa al menos 12 caracteres.</mat-error></mat-form-field>
              @if (formError) { <p class="form-error" role="alert">{{formError}}</p> }
              <button mat-flat-button color="primary" [disabled]="form.invalid || saving">{{saving ? 'Creando…' : 'Crear administrador'}}</button>
            </form>
          </mat-card-content></mat-card>
        </section>
      }
    </main>
  `,
  styles: [`
    .page{max-width:1200px;margin:auto;padding:clamp(1.25rem,3vw,2.5rem)}.back{display:inline-block;margin-bottom:1.3rem;color:var(--primary);font-weight:700;text-decoration:none}.heading{display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1.5rem}.heading-actions{display:flex;gap:.6rem;flex-wrap:wrap}.eyebrow{margin:0 0 .4rem;color:var(--primary);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{margin:0;color:var(--ink);font-size:clamp(1.8rem,3vw,2.5rem)}.slug{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2rem}mat-card{border-radius:18px}mat-card-content{padding-top:1rem}form{display:grid;gap:.35rem}.profile-form{grid-template-columns:repeat(2,minmax(0,1fr))}.form-actions{grid-column:1/-1;display:flex;justify-content:flex-end}.form-error{color:var(--danger)}.status{padding:.3rem .6rem;border-radius:99px;background:#e7f4ed;color:#176b43;font-weight:700}.status.inactive{background:#f9e8e6;color:#a63a31}.muted{color:var(--muted)}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{text-align:left;padding:.7rem;border-bottom:1px solid var(--border);white-space:nowrap}@media(max-width:760px){.heading{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:1fr}.profile-form{grid-template-columns:1fr}.form-actions{grid-column:auto}}
  `]
})
export class OrganizationDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly service = inject(OrganizationAdminService);
  private readonly usageService = inject(OrganizationUsageService);
  private readonly activityService = inject(OrganizationActivityService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  organization: OrganizationAdmin | null = null;
  branches: OrganizationBranchAdmin[] = [];
  users: OrganizationUserAdmin[] = [];
  usage: OrganizationUsage | null = null;
  usageLoading = false;
  usageError = '';
  usageFrom = this.monthStart();
  usageUntil = this.localDate(new Date());
  activity: OrganizationActivity[] = [];
  activityPage: OrganizationActivityPage | null = null;
  activityLoading = false;
  activityError = '';
  activityFrom = this.monthStart();
  activityUntil = this.localDate(new Date());
  activityType = '';
  activityUser: number | null = null;
  activityOffset = 0;
  activityLimit = 25;
  readonly activityTypes = ['USUARIO_CREADO', 'USUARIO_MODIFICADO', 'SUCURSAL_CREADA', 'SUCURSAL_MODIFICADA', 'PRODUCTO_CREADO', 'PRODUCTO_MODIFICADO', 'MOVIMIENTO_INVENTARIO_REGISTRADO', 'RESERVA_CREADA', 'RESERVA_MODIFICADA', 'PEDIDO_CREADO', 'ESTADO_PAGO_CAMBIADO', 'SUSCRIPCION_ASIGNADA', 'SUSCRIPCION_MODIFICADA'];
  loading = true;
  error = false;
  branchesLoading = true;
  usersLoading = true;
  branchesError = false;
  usersError = false;
  editingProfile = false;
  profileSaving = false;
  profileError = '';
  saving = false;
  formError = '';
  readonly profileForm = this.fb.group({
    nombre: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(150)]],
    razon_social: ['', Validators.maxLength(200)],
    nit: ['', [Validators.minLength(3), Validators.maxLength(20), Validators.pattern(/^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/)]],
    correo_contacto: ['', [Validators.email, Validators.maxLength(254)]],
    telefono_contacto: ['', [Validators.pattern(/^[+0-9() .-]{6,30}$/)]],
    direccion: ['', Validators.maxLength(255)],
    logo_url: ['', [Validators.pattern(/^https?:\/\/\S+$/i), Validators.maxLength(2048)]],
    slug: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(160), Validators.pattern(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)]]
  });
  readonly form = this.fb.group({
    nombres: ['', [Validators.required, Validators.maxLength(100)]],
    apellidos: ['', [Validators.required, Validators.maxLength(100)]],
    correo: ['', [Validators.required, Validators.email, Validators.maxLength(254)]],
    telefono: [''],
    password: ['', [Validators.required, Validators.minLength(12)]]
  });

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(id) || id < 1) { this.loading = false; this.error = true; return; }
    this.service.get(id).subscribe({
      next: (organization) => { this.organization = organization; this.loading = false; this.loadOrganizationDetails(id); },
      error: (e: HttpErrorResponse) => { this.loading = false; this.error = true; this.snack.open(this.message(e, 'No se pudo cargar la empresa.'), 'Cerrar', { duration: 5000 }); }
    });
  }

  private loadOrganizationDetails(id: number): void {
    this.service.listBranches(id).subscribe({
      next: (rows) => { this.branches = rows; this.branchesLoading = false; },
      error: () => { this.branchesError = true; this.branchesLoading = false; }
    });
    this.service.listUsers(id).subscribe({
      next: (rows) => { this.users = rows; this.usersLoading = false; },
      error: () => { this.usersError = true; this.usersLoading = false; }
    });
    this.loadUsage(id);
    this.loadActivity(true);
  }

  loadActivity(reset = false): void {
    if (!this.organization) return;
    if (reset) this.activityOffset = 0;
    if (this.activityFrom > this.activityUntil) { this.activityError = 'El período seleccionado no es válido.'; return; }
    this.activityLoading = true; this.activityError = '';
    this.activityService.list(this.organization.id_organizacion, { desde: this.activityFrom, hasta: this.activityUntil, tipo: this.activityType, usuarioId: this.activityUser ?? undefined, limit: this.activityLimit, offset: this.activityOffset }).subscribe({
      next: page => { this.activityPage = page; this.activity = page.items; this.activityLoading = false; },
      error: (e: HttpErrorResponse) => { this.activityLoading = false; this.activityError = e.status === 401 ? 'La sesión expiró.' : e.status === 403 ? 'No tienes permisos para consultar esta actividad.' : 'No se pudo cargar el historial de actividad.'; }
    });
  }

  actorLabel(id: number | null): string {
    if (id === null) return 'Sistema';
    const user = this.users.find(item => item.id_usuario === id);
    return user ? `${user.nombre} (#${id})` : `Usuario #${id}`;
  }

  loadUsageForPeriod(): void {
    if (!this.organization) return;
    if (!this.usageFrom || !this.usageUntil || this.usageFrom > this.usageUntil) {
      this.usageError = 'Selecciona un período válido: la fecha inicial debe ser anterior o igual a la final.';
      return;
    }
    this.loadUsage(this.organization.id_organizacion);
  }

  private loadUsage(id: number): void {
    this.usageLoading = true;
    this.usage = null;
    this.usageError = '';
    this.usageService.platformUsage(id, this.usageFrom, this.usageUntil).subscribe({
      next: (usage) => { this.usage = usage; this.usageLoading = false; },
      error: (error: HttpErrorResponse) => {
        this.usageLoading = false;
        if (error.status === 401) this.usageError = 'La sesión expiró. Inicia sesión nuevamente.';
        else if (error.status === 403) this.usageError = 'No tienes permisos de administrador de plataforma para consultar el consumo.';
        else if (error.status === 404) this.usageError = 'No se encontró la organización solicitada.';
        else if (error.status === 422) this.usageError = 'El período seleccionado no es válido.';
        else this.usageError = 'No se pudo cargar el uso y consumo de la empresa.';
      }
    });
  }

  private monthStart(): string {
    const today = new Date();
    return this.localDate(new Date(today.getFullYear(), today.getMonth(), 1));
  }

  private localDate(value: Date): string {
    const month = `${value.getMonth() + 1}`.padStart(2, '0');
    const day = `${value.getDate()}`.padStart(2, '0');
    return `${value.getFullYear()}-${month}-${day}`;
  }

  toggleProfileEdit(): void {
    this.editingProfile = !this.editingProfile;
    this.profileError = '';
    if (this.editingProfile && this.organization) {
      this.profileForm.patchValue({
        nombre: this.organization.nombre,
        razon_social: this.organization.razon_social ?? '',
        nit: this.organization.nit ?? '',
        correo_contacto: this.organization.correo_contacto ?? '',
        telefono_contacto: this.organization.telefono_contacto ?? '',
        direccion: this.organization.direccion ?? '',
        logo_url: this.organization.logo_url ?? '',
        slug: this.organization.slug
      });
    }
  }

  saveProfile(): void {
    if (!this.organization) return;
    this.profileError = '';
    if (!this.profileForm.dirty) return;
    if (this.profileForm.invalid) { this.profileForm.markAllAsTouched(); return; }
    const values = this.profileForm.getRawValue();
    const changedFields = Object.keys(this.profileForm.controls) as Array<keyof typeof this.profileForm.controls>;
    const payload = Object.fromEntries(changedFields
      .filter((field) => this.profileForm.controls[field].dirty)
      .map((field) => [field, values[field].trim() === '' && field !== 'nombre' && field !== 'slug' ? null : values[field]])) as UpdateOrganizationRequest;
    this.profileSaving = true;
    this.service.update(this.organization.id_organizacion, payload).subscribe({
      next: (updated) => { this.organization = updated; this.profileSaving = false; this.editingProfile = false; this.snack.open('Información empresarial actualizada.', 'Cerrar', { duration: 3500 }); },
      error: (error: HttpErrorResponse) => { this.profileSaving = false; this.profileError = this.message(error, 'No se pudo actualizar la empresa.'); }
    });
  }

  confirmStatus(): void {
    if (!this.organization) return;
    const current = this.organization;
    const next: OrganizationAdmin['estado'] = current.estado === 'ACTIVA' ? 'INACTIVA' : 'ACTIVA';
    const action = next === 'ACTIVA' ? 'reactivar' : 'suspender';
    this.dialog.open(ConfirmDialogComponent, { data: { title: `${action[0].toUpperCase()}${action.slice(1)} empresa`, message: `¿Confirmas ${action} ${current.nombre}?` } }).afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.service.updateStatus(current.id_organizacion, next).subscribe({
        next: (updated) => { this.organization = updated; this.snack.open(`Empresa ${next === 'ACTIVA' ? 'reactivada' : 'suspendida'}.`, 'Cerrar', { duration: 3500 }); },
        error: (e: HttpErrorResponse) => this.snack.open(this.message(e, 'No se pudo cambiar el estado.'), 'Cerrar', { duration: 5000 })
      });
    });
  }

  createAdministrator(): void {
    if (!this.organization) return;
    this.formError = '';
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const request = this.form.getRawValue();
    this.service.createFirstAdministrator(this.organization.id_organizacion, request).subscribe({
      next: (created) => { this.saving = false; this.form.reset(); this.snack.open(`Administrador creado: ${created.correo}`, 'Cerrar', { duration: 5000 }); },
      error: (e: HttpErrorResponse) => { this.saving = false; this.formError = this.message(e, 'No se pudo crear el administrador.'); }
    });
  }

  private message(error: HttpErrorResponse, fallback: string): string {
    if (error.status === 403) return 'Tu cuenta no tiene permiso para administrar empresas.';
    const detail = error.error?.detail ?? error.error?.message;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const validationMessage = detail.find((item) => typeof item?.msg === 'string')?.msg;
      if (typeof validationMessage === 'string') return validationMessage;
    }
    return fallback;
  }
}
