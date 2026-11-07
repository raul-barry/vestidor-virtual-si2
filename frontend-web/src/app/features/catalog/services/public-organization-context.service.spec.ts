import { TestBed } from '@angular/core/testing';
import { DefaultUrlSerializer, Router } from '@angular/router';
import { TokenService } from '../../../core/services/token.service';
import { PublicOrganizationContextService } from './public-organization-context.service';

describe('PublicOrganizationContextService', () => {
  let url: string;
  let authenticated: boolean;
  let service: PublicOrganizationContextService;
  const serializer = new DefaultUrlSerializer();

  beforeEach(() => {
    sessionStorage.removeItem('public_organization_slug');
    url = '/catalog';
    authenticated = false;
    TestBed.configureTestingModule({ providers: [
      PublicOrganizationContextService,
      { provide: Router, useValue: { get url() { return url; }, parseUrl: (value: string) => serializer.parse(value) } },
      { provide: TokenService, useValue: { hasToken: () => authenticated, getOrganizationId: () => 12 } }
    ] });
    service = TestBed.inject(PublicOrganizationContextService);
  });

  it('reads and remembers an explicit public URL slug', () => {
    url = '/catalog?organization_slug=urbanvogue';
    expect(service.publicSlug).toBe('urbanvogue');
    expect(sessionStorage.getItem('public_organization_slug')).toBe('urbanvogue');
  });

  it('does not silently choose a tenant when no public context exists', () => {
    expect(service.publicSlug).toBeNull();
    expect(service.canLoadCatalog).toBeFalse();
  });

  it('does not accept a user-selected public slug during an authenticated session', () => {
    url = '/catalog?organization_slug=elegance-boutique';
    authenticated = true;
    expect(service.publicSlug).toBeNull();
    expect(service.organizationId).toBe(12);
  });

  it('validates the selected slug format', () => {
    expect(PublicOrganizationContextService.validateSlug('  UrbanVogue  ')).toBe('urbanvogue');
    expect(PublicOrganizationContextService.validateSlug('fashion store')).toBeNull();
  });
});
