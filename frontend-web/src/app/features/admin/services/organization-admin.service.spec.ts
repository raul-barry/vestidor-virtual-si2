import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OrganizationAdminService } from './organization-admin.service';

describe('OrganizationAdminService', () => {
  let service: OrganizationAdminService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OrganizationAdminService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('lists and creates organizations using the platform API', () => {
    service.list().subscribe();
    const listing = http.expectOne('http://localhost:8000/api/platform/organizations');
    expect(listing.request.method).toBe('GET');
    listing.flush([]);
    const request = { nombre: 'Tienda Uno', slug: 'tienda-uno' };
    service.create(request).subscribe();
    const creation = http.expectOne('http://localhost:8000/api/platform/organizations');
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(request);
    creation.flush({});
  });
  it('gets an organization and its branches and users from scoped endpoints', () => {
    service.get(5).subscribe();
    let request = http.expectOne('http://localhost:8000/api/platform/organizations/5');
    expect(request.request.method).toBe('GET');
    request.flush({ id_organizacion: 5, nombre: 'Tienda Cinco', slug: 'tienda-cinco', estado: 'ACTIVA' });
    service.listBranches(5).subscribe();
    request = http.expectOne('http://localhost:8000/api/platform/organizations/5/branches');
    expect(request.request.method).toBe('GET');
    request.flush([]);
    service.listUsers(5).subscribe();
    request = http.expectOne('http://localhost:8000/api/platform/organizations/5/users');
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });
  it('patches a company business profile', () => {
    const requestBody = { razon_social: 'Casa Estilo SRL', nit: '123456789', correo_contacto: 'info@example.test' };
    service.update(5, requestBody).subscribe();
    const request = http.expectOne('http://localhost:8000/api/platform/organizations/5');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual(requestBody);
    request.flush({});
  });
  it('updates organization status and creates its first administrator', () => {
    service.updateStatus(8, 'INACTIVA').subscribe();
    const status = http.expectOne('http://localhost:8000/api/platform/organizations/8/status');
    expect(status.request.method).toBe('PATCH');
    expect(status.request.body).toEqual({ estado: 'INACTIVA' });
    status.flush({});
    const admin = { nombres: 'Ana', apellidos: 'Paz', correo: 'ana@example.com', telefono: '', password: 'segura-12345' };
    service.createFirstAdministrator(8, admin).subscribe();
    const creation = http.expectOne('http://localhost:8000/api/platform/organizations/8/administrators');
    expect(creation.request.method).toBe('POST');
    expect(creation.request.body).toEqual(admin);
    creation.flush({ id_usuario: 1, id_organizacion: 8, correo: admin.correo, rol: 'ADMINISTRADOR' });
  });

  it('provisions an organization, its first administrator, and subscription in one request', () => {
    const payload = {
      organization: { nombre: 'Empresa', slug: 'empresa' },
      administrator: { nombres: 'Ana', apellidos: 'Paz', correo: 'ana@example.com', password: '123456789012' },
      subscription: { plan_id: 2, fecha_fin: null }
    };
    service.provision(payload).subscribe();
    const request = http.expectOne('http://localhost:8000/api/platform/organizations/provision');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({});
  });
});
