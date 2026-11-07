import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TokenService } from '../../../core/services/token.service';

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

@Injectable({ providedIn: 'root' })
export class PublicOrganizationContextService {
  private readonly router = inject(Router);
  private readonly tokens = inject(TokenService);

  get isAuthenticated(): boolean {
    return this.tokens.hasToken();
  }

  get organizationId(): number | null {
    return this.tokens.getOrganizationId();
  }

  get publicSlug(): string | null {
    if (this.isAuthenticated) return null;
    const value = this.router.parseUrl(this.router.url).queryParams['organization_slug'];
    if (typeof value === 'string' && SLUG_PATTERN.test(value)) {
      sessionStorage.setItem('public_organization_slug', value);
      return value;
    }
    const saved = sessionStorage.getItem('public_organization_slug');
    return saved && SLUG_PATTERN.test(saved) ? saved : null;
  }

  get canLoadCatalog(): boolean {
    return this.isAuthenticated || this.publicSlug !== null;
  }

  static validateSlug(value: string): string | null {
    const slug = value.trim().toLowerCase();
    return SLUG_PATTERN.test(slug) ? slug : null;
  }
}
