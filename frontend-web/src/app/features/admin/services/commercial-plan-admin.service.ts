import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { CommercialPlanAdmin, CommercialPlanFeatureUpdate, CommercialPlanUpdate } from '../models/commercial-plan-admin.model';

@Injectable({ providedIn: 'root' })
export class CommercialPlanAdminService {
  private readonly base = '/api/platform/plans';
  constructor(private readonly api: ApiService) {}

  list(): Observable<CommercialPlanAdmin[]> { return this.api.get<CommercialPlanAdmin[]>(this.base); }
  get(id: number): Observable<CommercialPlanAdmin> { return this.api.get<CommercialPlanAdmin>(`${this.base}/${id}`); }
  update(id: number, request: CommercialPlanUpdate): Observable<CommercialPlanAdmin> {
    return this.api.put<CommercialPlanAdmin>(`${this.base}/${id}`, request);
  }
  updateFeatures(id: number, caracteristicas: CommercialPlanFeatureUpdate[]): Observable<CommercialPlanAdmin> {
    return this.api.put<CommercialPlanAdmin>(`${this.base}/${id}/features`, { caracteristicas });
  }
}
