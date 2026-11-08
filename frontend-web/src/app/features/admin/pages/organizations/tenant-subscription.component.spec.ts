import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { SubscriptionAdminService } from '../../services/subscription-admin.service';
import { TenantSubscriptionComponent } from './tenant-subscription.component';

describe('TenantSubscriptionComponent', () => {
  let fixture: ComponentFixture<TenantSubscriptionComponent>;
  const service = jasmine.createSpyObj<SubscriptionAdminService>(
    'SubscriptionAdminService', ['currentForMyOrganization', 'usageForMyOrganization', 'listPlans'],
  );

  beforeEach(async () => {
    service.currentForMyOrganization.and.returnValue(of({
      id_suscripcion: 1, organizacion_id: 8, plan_id: 2, plan_codigo: 'MODA', plan_nombre: 'Plan Moda',
      estado: 'ACTIVA', fecha_inicio: '2026-11-01T00:00:00Z', fecha_fin: '2027-11-01T00:00:00Z',
      fecha_creacion: '2026-11-01T00:00:00Z', fecha_actualizacion: '2026-11-01T00:00:00Z', creado_por_id: 1,
    }));
    service.usageForMyOrganization.and.returnValue(of({
      organizacion_id: 8, organizacion_nombre: 'FashionStore', periodo_desde: '2026-11-01', periodo_hasta: '2026-11-30',
      plan_codigo: 'MODA', plan_nombre: 'Plan Moda', estado_suscripcion: 'ACTIVA',
      fecha_inicio_suscripcion: '2026-11-01T00:00:00Z', fecha_fin_suscripcion: '2027-11-01T00:00:00Z',
      sucursales_activas: 4, limite_sucursales: 10, usuarios_activos: 8, productos_registrados: 24,
      pedidos_periodo: 12, ventas_periodo: '5200.00', reservas_periodo: 2,
      inventario_disponible: 36, inventario_reservado: 3, inventario_vendido: 12,
    }));
    service.listPlans.and.returnValue(of([
      { id_plan: 1, codigo: 'ESTILO', nombre: 'Plan Estilo', descripcion: 'Hasta 2 sucursales', max_sucursales: 2,
        caracteristicas: [{ id_plan_caracteristica: 1, codigo: 'catalogo', nombre: 'Catálogo', descripcion: null, habilitada: true, limite: null, configuracion: null }] },
      { id_plan: 2, codigo: 'MODA', nombre: 'Plan Moda', descripcion: 'Hasta 10 sucursales', max_sucursales: 10,
        caracteristicas: [{ id_plan_caracteristica: 2, codigo: 'reportes_ia', nombre: 'Reportes con IA', descripcion: null, habilitada: true, limite: null, configuracion: null }] },
      { id_plan: 3, codigo: 'GLAMOUR', nombre: 'Plan Glamour', descripcion: 'Sin límite', max_sucursales: null,
        caracteristicas: [
          { id_plan_caracteristica: 3, codigo: 'reportes_gemini', nombre: 'Reportes Gemini', descripcion: null, habilitada: true, limite: null, configuracion: null },
          { id_plan_caracteristica: 4, codigo: 'fidelizacion_clientes', nombre: 'Fidelización de clientes', descripcion: null, habilitada: true, limite: null, configuracion: null },
        ] },
    ]));
    await TestBed.configureTestingModule({ imports: [TenantSubscriptionComponent], providers: [provideRouter([])] })
      .overrideComponent(TenantSubscriptionComponent, {
        set: { providers: [{ provide: SubscriptionAdminService, useValue: service }] },
      }).compileComponents();
    fixture = TestBed.createComponent(TenantSubscriptionComponent);
  });

  it('highlights the contracted plan, status, dates, usage, and plan feature availability', () => {
    fixture.detectChanges();
    const component = fixture.componentInstance;
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Plan Moda');
    expect(text).toContain('ACTIVA');
    expect(text).toContain('Renovación / vencimiento');
    expect(text).toContain('4 / 10');
    expect(text).toContain('40% del límite contratado');
    expect(text).toContain('Reportes con IA');
    expect(text).not.toContain('Reportes Gemini');
    expect(component.isFeatureIncluded(component.plans[1], 'reportes_ia')).toBeTrue();
    expect(component.isFeatureIncluded(component.plans[2], 'fidelizacion_clientes')).toBeTrue();
    expect(component.isFeatureIncluded(component.plans[0], 'fidelizacion_clientes')).toBeFalse();
    expect(text).toContain('Fidelización de clientes');
  });

  it('does not invent a branch quota for unlimited plans and caps the visual bar', () => {
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.branchUsagePercent).toBe(40);
    component.usage = { ...component.usage!, sucursales_activas: 12, limite_sucursales: 10 };
    expect(component.branchUsagePercent).toBe(100);
    const glam = component.plans[2];
    expect(glam.max_sucursales).toBeNull();
    expect(component.isFeatureIncluded(glam, 'reportes_ia')).toBeTrue();
  });
});
