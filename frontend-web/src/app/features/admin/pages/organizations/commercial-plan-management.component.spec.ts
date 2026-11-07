import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { TestBed } from '@angular/core/testing';
import { CommercialPlanAdmin, CommercialPlanFeatureAdmin } from '../../models/commercial-plan-admin.model';
import { CommercialPlanAdminService } from '../../services/commercial-plan-admin.service';
import { CommercialPlanManagementComponent } from './commercial-plan-management.component';

describe('CommercialPlanManagementComponent', () => {
  let service: jasmine.SpyObj<CommercialPlanAdminService>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let component: CommercialPlanManagementComponent;
  const feature: CommercialPlanFeatureAdmin = {
    id_plan_caracteristica: 1, codigo: 'catalogo', nombre: 'Catálogo', descripcion: null,
    habilitada: true, limite: null, configuracion: null,
  };
  const plan: CommercialPlanAdmin = {
    id_plan: 1, codigo: 'ESTILO', nombre: 'Plan Estilo', descripcion: 'Inicial', max_sucursales: 2,
    activo: true, caracteristicas: [feature],
  };

  beforeEach(() => {
    service = jasmine.createSpyObj<CommercialPlanAdminService>('CommercialPlanAdminService', ['list', 'get', 'update', 'updateFeatures']);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    dialog.open.and.returnValue({ afterClosed: () => of(true) } as never);
    TestBed.configureTestingModule({ providers: [
      { provide: CommercialPlanAdminService, useValue: service },
      { provide: MatDialog, useValue: dialog },
      { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) },
    ] });
    component = TestBed.runInInjectionContext(() => new CommercialPlanManagementComponent());
    component.plans = [{ ...plan, caracteristicas: [{ ...feature, configuracionTexto: '' }] }];
  });

  it('loads the existing plans and prepares editable JSON configuration', () => {
    service.list.and.returnValue(of([plan]));
    component.load();
    expect(component.plans[0].codigo).toBe('ESTILO');
    expect(component.plans[0].caracteristicas[0].configuracionTexto).toBe('');
  });

  it('confirms, updates a plan and its feature settings, then refreshes the displayed values', () => {
    const updated = { ...plan, nombre: 'Estilo Plus', max_sucursales: 3 };
    const updatedFeature = { ...feature, habilitada: false, limite: 15, configuracion: { offline: true } };
    service.update.and.returnValue(of(updated));
    service.updateFeatures.and.returnValue(of({ ...updated, caracteristicas: [updatedFeature] }));
    const draft = { ...plan, nombre: 'Estilo Plus', max_sucursales: 3,
      caracteristicas: [{ ...feature, habilitada: false, limite: 15, configuracionTexto: '{"offline":true}' }] };

    component.save(draft);

    expect(dialog.open).toHaveBeenCalled();
    expect(service.update).toHaveBeenCalledWith(1, { nombre: 'Estilo Plus', descripcion: 'Inicial', max_sucursales: 3, activo: true });
    expect(service.updateFeatures).toHaveBeenCalledWith(1, [{ codigo: 'catalogo', habilitada: false, limite: 15, configuracion: { offline: true } }]);
    expect(component.plans[0].caracteristicas[0].habilitada).toBeFalse();
  });

  it('rejects invalid JSON before sending changes', () => {
    component.save({ ...plan, caracteristicas: [{ ...feature, configuracionTexto: '[' }] });
    expect(service.update).not.toHaveBeenCalled();
    expect(component.planError(1)).toContain('JSON');
  });

  it('shows authorization and active-subscription conflicts', () => {
    for (const [status, message] of [[403, 'Solo un administrador de plataforma'], [409, 'Hay suscripciones activas']] as const) {
      service.update.and.returnValue(throwError(() => new HttpErrorResponse({ status, error: { detail: message } })));
      component.save({ ...plan });
      expect(component.planError(1)).toContain(status === 403 ? 'Solo un administrador' : 'suscripciones activas');
    }
  });
});
