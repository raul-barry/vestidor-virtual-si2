import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CommercialPlanAdminService } from './commercial-plan-admin.service';

describe('CommercialPlanAdminService', () => {
  let service: CommercialPlanAdminService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CommercialPlanAdminService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists plans and queries individual plan details', () => {
    service.list().subscribe();
    const list = http.expectOne('http://localhost:8000/api/platform/plans');
    expect(list.request.method).toBe('GET'); list.flush([]);
    service.get(3).subscribe();
    const detail = http.expectOne('http://localhost:8000/api/platform/plans/3');
    expect(detail.request.method).toBe('GET'); detail.flush({});
  });

  it('updates plan properties and feature configuration using the admin API', () => {
    service.update(3, { nombre: 'Estilo Pro', max_sucursales: 4, activo: true }).subscribe();
    const plan = http.expectOne('http://localhost:8000/api/platform/plans/3');
    expect(plan.request.method).toBe('PUT');
    expect(plan.request.body).toEqual({ nombre: 'Estilo Pro', max_sucursales: 4, activo: true });
    plan.flush({});
    service.updateFeatures(3, [{ codigo: 'catalogo', habilitada: false, limite: 20, configuracion: { offline: true } }]).subscribe();
    const features = http.expectOne('http://localhost:8000/api/platform/plans/3/features');
    expect(features.request.method).toBe('PUT');
    expect(features.request.body.caracteristicas[0].habilitada).toBeFalse();
    expect(features.request.body.caracteristicas[0].limite).toBe(20);
    features.flush({});
  });
});
