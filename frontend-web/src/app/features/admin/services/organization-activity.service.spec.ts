import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { OrganizationActivityService } from './organization-activity.service';
import { API_URL } from '../../../core/config/api.config';

describe('OrganizationActivityService', () => {
  let service: OrganizationActivityService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] });
    service = TestBed.inject(OrganizationActivityService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('requests the organization activity with filters and pagination', () => {
    service.list(12, { desde: '2026-11-01', hasta: '2026-11-03', tipo: 'PEDIDO_CREADO', usuarioId: 8, limit: 25, offset: 25 }).subscribe();
    const req = http.expectOne(request => request.urlWithParams.startsWith(`${API_URL}/api/platform/organizations/12/activity?`));
    const params = new URL(req.request.urlWithParams).searchParams;
    expect(params.get('desde')).toBe('2026-11-01T00:00:00Z');
    expect(params.get('hasta')).toBe('2026-11-03T23:59:59.999999Z');
    expect(params.get('tipo')).toBe('PEDIDO_CREADO');
    expect(params.get('usuario_id')).toBe('8');
    expect(params.get('offset')).toBe('25');
    req.flush({ items: [], total: 0, limit: 25, offset: 25 });
  });
});
