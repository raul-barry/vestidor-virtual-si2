import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OrganizationUsageService } from './organization-usage.service';

describe('OrganizationUsageService', () => {
  let service: OrganizationUsageService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OrganizationUsageService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('queries platform usage with the selected organization and period', () => {
    service.platformUsage(7, '2026-11-01', '2026-11-30').subscribe();
    const request = http.expectOne('http://localhost:8000/api/platform/organizations/7/usage?desde=2026-11-01&hasta=2026-11-30');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });

  it('queries the authenticated company usage without accepting an organization id', () => {
    service.myUsage().subscribe();
    const request = http.expectOne('http://localhost:8000/api/organizations/me/usage');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });
});
