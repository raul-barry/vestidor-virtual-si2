import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { OrganizationActivityPage } from '../models/organization-activity.model';

@Injectable({ providedIn: 'root' })
export class OrganizationActivityService {
  constructor(private readonly api: ApiService) {}

  list(id: number, options: { desde?: string; hasta?: string; tipo?: string; usuarioId?: number; limit?: number; offset?: number }): Observable<OrganizationActivityPage> {
    const params = new URLSearchParams();
    if (options.desde) params.set('desde', `${options.desde}T00:00:00Z`);
    if (options.hasta) params.set('hasta', `${options.hasta}T23:59:59.999999Z`);
    if (options.tipo) params.set('tipo', options.tipo);
    if (options.usuarioId) params.set('usuario_id', String(options.usuarioId));
    params.set('limit', String(options.limit ?? 25));
    params.set('offset', String(options.offset ?? 0));
    return this.api.get<OrganizationActivityPage>(`/api/platform/organizations/${id}/activity?${params.toString()}`);
  }
}
