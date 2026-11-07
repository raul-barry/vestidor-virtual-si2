import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { SubscriptionAdmin, SubscriptionPlanAdmin, SubscriptionRequestAdmin } from '../models/subscription-admin.model';

@Injectable({ providedIn: 'root' })
export class SubscriptionAdminService {
  private readonly base = '/api';

  constructor(private readonly api: ApiService) {}

  listPlans(): Observable<SubscriptionPlanAdmin[]> {
    return this.api.get<SubscriptionPlanAdmin[]>(`${this.base}/subscriptions/plans`);
  }

  currentForMyOrganization(): Observable<SubscriptionAdmin | null> {
    return this.api.get<SubscriptionAdmin | null>(`${this.base}/subscriptions/current`);
  }

  usageForMyOrganization(): Observable<unknown> {
    return this.api.get<unknown>(`${this.base}/organizations/me/usage`);
  }

  current(organizationId: number): Observable<SubscriptionAdmin | null> {
    return this.api.get<SubscriptionAdmin | null>(this.organizationPath(organizationId, '/current'));
  }

  history(organizationId: number): Observable<SubscriptionAdmin[]> {
    return this.api.get<SubscriptionAdmin[]>(this.organizationPath(organizationId, '/history'));
  }

  assign(organizationId: number, request: SubscriptionRequestAdmin): Observable<SubscriptionAdmin> {
    return this.api.post<SubscriptionAdmin>(this.organizationPath(organizationId), request);
  }

  change(organizationId: number, request: SubscriptionRequestAdmin): Observable<SubscriptionAdmin> {
    return this.api.put<SubscriptionAdmin>(this.organizationPath(organizationId, '/current'), request);
  }

  cancel(organizationId: number): Observable<SubscriptionAdmin> {
    return this.api.post<SubscriptionAdmin>(this.organizationPath(organizationId, '/current/cancel'), {});
  }

  private organizationPath(organizationId: number, suffix = ''): string {
    return `${this.base}/platform/organizations/${organizationId}/subscriptions${suffix}`;
  }
}
