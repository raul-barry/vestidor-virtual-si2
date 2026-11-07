import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { of, throwError } from 'rxjs';
import { TestBed } from '@angular/core/testing';
import { OrganizationAdminService } from '../../services/organization-admin.service';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';
import { OrganizationAdmin } from '../../models/organization-admin.model';
import { SubscriptionAdmin, SubscriptionPlanAdmin } from '../../models/subscription-admin.model';
import { SubscriptionManagementComponent } from './subscription-management.component';

describe('SubscriptionManagementComponent', () => {
  let component: SubscriptionManagementComponent;
  let subscriptionService: jasmine.SpyObj<SubscriptionAdminService>;
  let organizationService: jasmine.SpyObj<OrganizationAdminService>;
  let dialog: jasmine.SpyObj<MatDialog>;

  const organization: OrganizationAdmin = {
    id_organizacion: 4, nombre: 'Casa Estilo', razon_social: null, nit: null,
    correo_contacto: null, telefono_contacto: null, direccion: null, logo_url: null,
    slug: 'casa-estilo', estado: 'ACTIVA', fecha_creacion: null, fecha_actualizacion: null,
  };
  const plan: SubscriptionPlanAdmin = {
    id_plan: 1, codigo: 'ESTILO', nombre: 'Plan Estilo', descripcion: null,
    max_sucursales: 2, caracteristicas: [],
  };
  const subscription: SubscriptionAdmin = {
    id_suscripcion: 10, organizacion_id: 4, plan_id: 1, plan_codigo: 'ESTILO',
    plan_nombre: 'Plan Estilo', estado: 'ACTIVA', fecha_inicio: '2026-11-03T00:00:00Z',
    fecha_fin: null, fecha_creacion: '2026-11-03T00:00:00Z',
    fecha_actualizacion: '2026-11-03T00:00:00Z', creado_por_id: 1,
  };

  beforeEach(() => {
    subscriptionService = jasmine.createSpyObj<SubscriptionAdminService>(
      'SubscriptionAdminService', ['listPlans', 'current', 'history', 'assign', 'change', 'cancel'],
    );
    organizationService = jasmine.createSpyObj<OrganizationAdminService>('OrganizationAdminService', ['updateStatus']);
    organizationService.updateStatus.and.returnValue(of({ ...organization, estado: 'INACTIVA' }));
    subscriptionService.current.and.returnValue(of(null));
    subscriptionService.history.and.returnValue(of([]));
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    dialog.open.and.returnValue({ afterClosed: () => of(true) } as never);
    TestBed.configureTestingModule({ providers: [
      { provide: OrganizationAdminService, useValue: organizationService },
      { provide: SubscriptionAdminService, useValue: subscriptionService },
      { provide: MatDialog, useValue: dialog },
      { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
      { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => null } } } },
    ] });
    component = TestBed.runInInjectionContext(() => new SubscriptionManagementComponent());
    component.selected = { organization, current: null };
    component.plans = [plan, { ...plan, id_plan: 2, codigo: 'MODA', nombre: 'Plan Moda' }];
    component.planControl.setValue(1);
  });

  it('assigns a plan when the company has no active subscription', () => {
    subscriptionService.assign.and.returnValue(of(subscription));

    component.savePlan();

    expect(subscriptionService.assign).toHaveBeenCalledWith(4, { plan_id: 1 });
    expect(dialog.open).not.toHaveBeenCalled();
    expect(subscriptionService.current).toHaveBeenCalledWith(4);
    expect(subscriptionService.history).toHaveBeenCalledWith(4);
  });

  it('asks for confirmation before changing a plan', () => {
    component.selected = { organization, current: subscription };
    component.planControl.setValue(2);
    subscriptionService.change.and.returnValue(of({ ...subscription, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' }));

    component.savePlan();

    expect(dialog.open).toHaveBeenCalled();
    expect(subscriptionService.change).toHaveBeenCalledWith(4, { plan_id: 2 });
  });

  it('asks for confirmation before cancelling', () => {
    component.selected = { organization, current: subscription };
    subscriptionService.cancel.and.returnValue(of({ ...subscription, estado: 'CANCELADA' }));

    component.confirmCancel();

    expect(dialog.open).toHaveBeenCalled();
    expect(subscriptionService.cancel).toHaveBeenCalledWith(4);
    expect(subscriptionService.history).toHaveBeenCalledWith(4);
  });

  it('computes remaining days for an active dated subscription', () => {
    const end = new Date(Date.now() + 5 * 86_400_000).toISOString();
    expect(component.daysRemaining({ ...subscription, fecha_fin: end })).toBe(5);
    expect(component.daysRemaining({ ...subscription, estado: 'VENCIDA', fecha_fin: end })).toBeNull();
    expect(component.daysRemaining(subscription)).toBeNull();
  });

  it('confirms and refreshes a company suspension or reactivation', () => {
    component.selected = { organization, current: subscription };
    component.confirmOrganizationStatus();
    expect(dialog.open).toHaveBeenCalled();
    expect(organizationService.updateStatus).toHaveBeenCalledWith(4, 'INACTIVA');
    expect(component.selected?.organization.estado).toBe('INACTIVA');
  });

  for (const [status, expected] of [
    [401, 'La sesión expiró. Inicia sesión nuevamente.'],
    [403, 'No tienes permisos para administrar suscripciones de plataforma.'],
    [409, 'La suscripción cambió. Actualiza e inténtalo nuevamente.'],
  ] as const) {
    it(`shows a clear HTTP ${status} error`, () => {
      subscriptionService.assign.and.returnValue(throwError(() => new HttpErrorResponse({
        status,
        error: status === 409 ? { detail: { message: expected } } : { detail: 'rejected' },
      })));

      component.savePlan();

      expect(component.operationError).toBe(expected);
    });
  }
});
