import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { OrganizationDetailComponent } from './organization-detail.component';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { OrganizationUsageService } from '../../services/organization-usage.service';
import { OrganizationActivityService } from '../../services/organization-activity.service';
import { OrganizationAdmin } from '../../models/organization-admin.model';

describe('OrganizationDetailComponent activity text encoding', () => {
  let fixture: ComponentFixture<OrganizationDetailComponent>;
  let activityService: jasmine.SpyObj<OrganizationActivityService>;
  let organizationService: jasmine.SpyObj<OrganizationAdminService>;
  let snack: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    organizationService = jasmine.createSpyObj<OrganizationAdminService>(
      'OrganizationAdminService', ['get', 'listBranches', 'listUsers', 'update']
    );
    organizationService.get.and.returnValue(of({
      id_organizacion: 3, nombre: 'Boutique de prueba', razon_social: null, nit: null,
      correo_contacto: null, telefono_contacto: null, direccion: 'Av. España', logo_url: null,
      slug: 'boutique-prueba', estado: 'ACTIVA', fecha_creacion: '2026-11-01T00:00:00Z',
      fecha_actualizacion: null
    }));
    organizationService.listBranches.and.returnValue(of([]));
    organizationService.listUsers.and.returnValue(of([]));

    const usageService = jasmine.createSpyObj<OrganizationUsageService>('OrganizationUsageService', ['platformUsage']);
    usageService.platformUsage.and.returnValue(of({
      organizacion_id: 3, organizacion_nombre: 'Boutique de prueba', periodo_desde: null, periodo_hasta: null,
      plan_codigo: null, plan_nombre: null, estado_suscripcion: 'SIN_SUSCRIPCION', fecha_inicio_suscripcion: null,
      fecha_fin_suscripcion: null, sucursales_activas: 0, limite_sucursales: null, usuarios_activos: 0,
      productos_registrados: 0, pedidos_periodo: 0, ventas_periodo: '0', reservas_periodo: 0,
      inventario_disponible: 0, inventario_reservado: 0, inventario_vendido: 0
    }));

    activityService = jasmine.createSpyObj<OrganizationActivityService>('OrganizationActivityService', ['list']);
    activityService.list.and.returnValue(of({
      items: [{ id: 1, organizacion_id: 3, usuario_id: null, rol: 'ADMINISTRADOR', accion: 'USUARIO_CREADO',
        entidad: 'Usuario', entidad_id: '4', fecha_hora: '2026-11-01T12:00:00Z', resultado: 'EXITOSO', detalles: {} }],
      total: 1, limit: 25, offset: 0
    }));

    await TestBed.configureTestingModule({
      imports: [OrganizationDetailComponent, NoopAnimationsModule],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '3' } } } },
        { provide: OrganizationAdminService, useValue: organizationService },
        { provide: OrganizationUsageService, useValue: usageService },
        { provide: OrganizationActivityService, useValue: activityService },
        { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
        { provide: MatSnackBar, useValue: snack = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(OrganizationDetailComponent);
    fixture.detectChanges();
  });

  it('renders Spanish accents and ñ in organization and activity content', () => {
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Acción');
    expect(text).not.toContain('AcciÃ³n');
    expect(text).toContain('Información general');
    expect(text).toContain('Dirección');
    expect(text).toContain('España');
    expect(text).toContain('organización');
    expect(text).toContain('Razón social');
  });

  it('renders the correctly encoded session-expired message', () => {
    activityService.list.and.returnValue(throwError(() => new HttpErrorResponse({ status: 401 })));
    fixture.componentInstance.loadActivity(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('La sesión expiró.');
    expect(fixture.nativeElement.textContent).not.toContain('sesiÃ³n');
  });

  it('sends only edited organization fields and updates the displayed organization', () => {
    const updated: OrganizationAdmin = {
      ...fixture.componentInstance.organization!, direccion: 'Santa Cruz',
      fecha_actualizacion: '2026-11-08T12:00:00Z'
    };
    organizationService.update.and.returnValue(of(updated));
    fixture.componentInstance.toggleProfileEdit();
    fixture.componentInstance.profileForm.controls.direccion.setValue('Santa Cruz');
    fixture.componentInstance.profileForm.controls.direccion.markAsDirty();

    fixture.componentInstance.saveProfile();

    expect(organizationService.update).toHaveBeenCalledWith(3, { direccion: 'Santa Cruz' });
    expect(fixture.componentInstance.organization?.direccion).toBe('Santa Cruz');
    expect(fixture.componentInstance.organization?.fecha_actualizacion).toBe(updated.fecha_actualizacion);
    expect(fixture.componentInstance.editingProfile).toBeFalse();
  });

  it('shows the server validation reason for a failed organization update', () => {
    organizationService.update.and.returnValue(throwError(() => new HttpErrorResponse({
      status: 422, error: { detail: [{ msg: 'logo_url debe ser una URL http o https válida' }] }
    })));
    fixture.componentInstance.toggleProfileEdit();
    fixture.componentInstance.profileForm.controls.direccion.setValue('Santa Cruz');
    fixture.componentInstance.profileForm.controls.direccion.markAsDirty();

    fixture.componentInstance.saveProfile();

    expect(fixture.componentInstance.profileError).toBe('logo_url debe ser una URL http o https válida');
  });
});
