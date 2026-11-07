import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { OrganizationUsage } from '../models/organization-usage.model';

@Injectable({ providedIn: 'root' })
export class OrganizationUsageService {
  constructor(private readonly api: ApiService) {}

  platformUsage(id: number, desde?: string, hasta?: string): Observable<OrganizationUsage> {
    return this.api.get<OrganizationUsage>(this.path(`/api/platform/organizations/${id}/usage`, desde, hasta));
  }

  myUsage(desde?: string, hasta?: string): Observable<OrganizationUsage> {
    return this.api.get<OrganizationUsage>(this.path('/api/organizations/me/usage', desde, hasta));
  }

  private path(base: string, desde?: string, hasta?: string): string {
    const params = new URLSearchParams();
    if (desde) params.set('desde', desde);
    if (hasta) params.set('hasta', hasta);
    const query = params.toString();
    return query ? `${base}?${query}` : base;
  }
}
