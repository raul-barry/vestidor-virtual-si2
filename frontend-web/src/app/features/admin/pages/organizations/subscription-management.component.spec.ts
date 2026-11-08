import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of, Subject, throwError } from 'rxjs';
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
    organizationService = jasmine.createSpyObj<OrganizationAdminService>('OrganizationAdminService', ['list', 'updateStatus']);
    organizationService.list.and.returnValue(of([organization]));
    organizationService.updateStatus.and.returnValue(of({ ...organization, estado: 'INACTIVA' }));
    subscriptionService.current.and.returnValue(of(null));
    subscriptionService.history.and.returnValue(of([]));
    subscriptionService.listPlans.and.returnValue(of([plan, { ...plan, id_plan: 2, codigo: 'MODA', nombre: 'Plan Moda' }]));
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    dialog.open.and.returnValue({ afterClosed: () => of(true) } as never);
    TestBed.configureTestingModule({ imports: [NoopAnimationsModule], providers: [
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

  it('sends the selected organization and plan directly when changing a plan', () => {
    component.selected = { organization, current: subscription };
    component.planControl.setValue(2);
    subscriptionService.change.and.returnValue(of({ ...subscription, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' }));

    component.savePlan();

    expect(dialog.open).not.toHaveBeenCalled();
    expect(subscriptionService.change).toHaveBeenCalledWith(4, { plan_id: 2 });
  });

  it('submits the selected plan through the rendered form button', () => {
    const fixture = TestBed.createComponent(SubscriptionManagementComponent);
    fixture.detectChanges();
    const updated = { ...subscription, id_suscripcion: 11, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' };
    fixture.componentInstance.selected = { organization, current: subscription };
    fixture.componentInstance.rows = [{ organization, current: subscription }];
    fixture.componentInstance.plans = [plan, { ...plan, id_plan: 2, codigo: 'MODA', nombre: 'Plan Moda' }];
    fixture.componentInstance.planControl.setValue(1);
    fixture.componentInstance.planControl.setValue(2);
    subscriptionService.change.and.returnValue(of(updated));
    subscriptionService.current.and.returnValue(of(updated));
    subscriptionService.history.and.returnValue(of([updated, subscription]));
    fixture.detectChanges();

    const submit = fixture.nativeElement.querySelector('.plan-form button[type="button"]') as HTMLButtonElement;
    expect(submit.disabled).toBeFalse();
    submit.click();
    fixture.detectChanges();

    expect(subscriptionService.change).toHaveBeenCalledWith(4, { plan_id: 2 });
    expect(fixture.componentInstance.selected?.current?.plan_codigo).toBe('MODA');
    fixture.destroy();
  });

  it('handles native form submission in Angular without a browser page reload', () => {
    const fixture = TestBed.createComponent(SubscriptionManagementComponent);
    fixture.detectChanges();
    fixture.componentInstance.selected = { organization, current: subscription };
    fixture.componentInstance.rows = [{ organization, current: subscription }];
    fixture.componentInstance.plans = [plan, { ...plan, id_plan: 2, codigo: 'MODA', nombre: 'Plan Moda' }];
    fixture.componentInstance.planControl.setValue(2);
    subscriptionService.change.and.returnValue(of({ ...subscription, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' }));
    subscriptionService.current.and.returnValue(of({ ...subscription, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' }));
    subscriptionService.history.and.returnValue(of([]));
    fixture.detectChanges();

    const form = fixture.nativeElement.querySelector('.plan-form') as HTMLFormElement;
    const event = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(event);
    fixture.detectChanges();

    expect(event.defaultPrevented).toBeTrue();
    expect(subscriptionService.change).toHaveBeenCalledWith(4, { plan_id: 2 });
    fixture.destroy();
  });

  it('shows the backend result immediately and refreshes current plan and history', () => {
    const updated = { ...subscription, id_suscripcion: 11, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' };
    component.selected = { organization, current: subscription };
    component.rows = [{ organization, current: subscription }];
    component.history = [subscription];
    component.planControl.setValue(2);
    subscriptionService.change.and.returnValue(of(updated));
    subscriptionService.current.and.returnValue(of(updated));
    subscriptionService.history.and.returnValue(of([updated, subscription]));

    component.savePlan();

    expect(component.selected?.current?.plan_codigo).toBe('MODA');
    expect(component.rows[0].current?.plan_codigo).toBe('MODA');
    expect(component.history.map(item => item.plan_codigo)).toEqual(['MODA', 'ESTILO']);
    expect(subscriptionService.current).toHaveBeenCalledWith(4);
    expect(subscriptionService.history).toHaveBeenCalledWith(4);
  });

  it('prevents duplicate plan changes while the confirmed request is pending', () => {
    const response = new Subject<SubscriptionAdmin>();
    component.selected = { organization, current: subscription };
    component.planControl.setValue(2);
    subscriptionService.change.and.returnValue(response);

    component.savePlan();
    component.savePlan();
    component.savePlan();

    expect(dialog.open).not.toHaveBeenCalled();
    expect(subscriptionService.change).toHaveBeenCalledTimes(1);
    response.next({ ...subscription, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda' });
    response.complete();
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
      component.selected = { organization, current: subscription };
      component.planControl.setValue(2);
      subscriptionService.change.and.returnValue(throwError(() => new HttpErrorResponse({
        status,
        error: status === 409 ? { detail: { message: expected } } : { detail: 'rejected' },
      })));

      component.savePlan();

      expect(component.operationError).toBe(expected);
      expect(component.selected?.current?.plan_id).toBe(1);
    });
  }
});
