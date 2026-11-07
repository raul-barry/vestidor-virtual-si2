import { FormBuilder, NonNullableFormBuilder } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';
import { TestBed } from '@angular/core/testing';
import { OrganizationAdmin } from '../../models/organization-admin.model';
import { OrganizationUsageService } from '../../services/organization-usage.service';
import { OrganizationActivityService } from '../../services/organization-activity.service';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { OrganizationDetailComponent } from './organization-detail.component';

describe('Organization usage in platform company detail', () => {
  let component: OrganizationDetailComponent;
  let organizationService: jasmine.SpyObj<OrganizationAdminService>;
  let usageService: jasmine.SpyObj<OrganizationUsageService>;
  const organization: OrganizationAdmin = {
    id_organizacion: 7, nombre: 'Moda Store', razon_social: null, nit: null,
    correo_contacto: null, telefono_contacto: null, direccion: null, logo_url: null,
    slug: 'moda-store', estado: 'ACTIVA', fecha_creacion: null, fecha_actualizacion: null,
  };
  const usage = {
    organizacion_id: 7, organizacion_nombre: 'Moda Store', periodo_desde: '2026-11-01', periodo_hasta: '2026-11-03',
    plan_codigo: 'MODA', plan_nombre: 'Plan Moda', estado_suscripcion: 'ACTIVA' as const,
    fecha_inicio_suscripcion: '2026-11-01T00:00:00Z', fecha_fin_suscripcion: null,
    sucursales_activas: 2, limite_sucursales: 10, usuarios_activos: 4, productos_registrados: 20,
    pedidos_periodo: 3, ventas_periodo: '450.00', reservas_periodo: 2,
    inventario_disponible: 100, inventario_reservado: 10, inventario_vendido: 5,
  };

  beforeEach(() => {
    organizationService = jasmine.createSpyObj<OrganizationAdminService>(
      'OrganizationAdminService', ['get', 'listBranches', 'listUsers'],
    );
    organizationService.get.and.returnValue(of(organization));
    organizationService.listBranches.and.returnValue(of([]));
    organizationService.listUsers.and.returnValue(of([]));
    usageService = jasmine.createSpyObj<OrganizationUsageService>('OrganizationUsageService', ['platformUsage', 'myUsage']);
    usageService.platformUsage.and.returnValue(of(usage));
    TestBed.configureTestingModule({ providers: [
      { provide: NonNullableFormBuilder, useFactory: () => new FormBuilder().nonNullable },
      { provide: OrganizationAdminService, useValue: organizationService },
      { provide: OrganizationUsageService, useValue: usageService },
      { provide: OrganizationActivityService, useValue: { list: () => of({ items: [], total: 0, limit: 25, offset: 0 }) } },
      { provide: MatDialog, useValue: jasmine.createSpyObj<MatDialog>('MatDialog', ['open']) },
      { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => '7' } } } },
    ] });
    component = TestBed.runInInjectionContext(() => new OrganizationDetailComponent());
  });

  it('loads usage for the selected company and current month period', () => {
    component.ngOnInit();
    expect(usageService.platformUsage).toHaveBeenCalledWith(7, component.usageFrom, component.usageUntil);
    expect(component.usage?.plan_codigo).toBe('MODA');
    expect(component.usage?.ventas_periodo).toBe('450.00');
  });

  it('rejects an inverted date range before sending an HTTP request', () => {
    component.organization = organization;
    component.usageFrom = '2026-11-30';
    component.usageUntil = '2026-11-01';
    component.loadUsageForPeriod();
    expect(usageService.platformUsage).not.toHaveBeenCalled();
    expect(component.usageError).toContain('período válido');
  });

  it('shows authorization and missing-organization HTTP errors', () => {
    for (const [status, expected] of [
      [401, 'La sesión expiró'],
      [403, 'No tienes permisos'],
      [404, 'No se encontró'],
      [422, 'período seleccionado'],
    ] as const) {
      usageService.platformUsage.and.returnValue(throwError(() => new HttpErrorResponse({ status })));
      component.ngOnInit();
      expect(component.usageError).toContain(expected);
    }
  });
});
