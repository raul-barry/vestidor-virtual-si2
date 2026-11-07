import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import {
  CategoryRanking,
  CustomerReport,
  DashboardReport,
  AiReportRequest,
  AiReportResponse,
  InventoryReport,
  ProductRanking,
  ReportBranch,
  ReportFeatures,
  SalesReport,
  CustomerSegments,
  PredictiveDashboard,
  PredictiveFeatures,
  PredictiveFilters,
  PredictiveHistory
} from '../models/report.model';

@Injectable({ providedIn: 'root' })
export class AdminReportService {
  constructor(private readonly api: ApiService) {}

  getDashboard(): Observable<DashboardReport> {
    return this.api.get<DashboardReport>('/api/admin/reports/dashboard');
  }

  getSales(): Observable<SalesReport> {
    return this.api.get<SalesReport>('/api/admin/reports/sales');
  }

  getTopProducts(): Observable<ProductRanking[]> {
    return this.api.get<ProductRanking[]>('/api/admin/reports/top-products');
  }

  getTopCategories(): Observable<CategoryRanking[]> {
    return this.api.get<CategoryRanking[]>('/api/admin/reports/top-categories');
  }

  getInventory(): Observable<InventoryReport> {
    return this.api.get<InventoryReport>('/api/admin/reports/inventory');
  }

  getCustomers(): Observable<CustomerReport> {
    return this.api.get<CustomerReport>('/api/admin/reports/customers');
  }

  getBranches(): Observable<ReportBranch[]> {
    return this.api.get<ReportBranch[]>('/api/admin/reports/branches');
  }

  getFeatures(): Observable<ReportFeatures> {
    return this.api.get<ReportFeatures>('/api/admin/reports/features');
  }

  generateAiReport(request: AiReportRequest): Observable<AiReportResponse> {
    return this.api.post<AiReportResponse>('/api/admin/reports/ai', request);
  }

  exportAiReport(request: AiReportRequest, format: 'pdf' | 'xlsx'): Observable<Blob> {
    return this.api.postBlob(`/api/admin/reports/export/${format}`, request);
  }

  getPredictiveFeatures(): Observable<PredictiveFeatures> {
    return this.api.get<PredictiveFeatures>('/api/admin/reports/predictive/features');
  }

  getPredictiveDashboard(filters: PredictiveFilters): Observable<PredictiveDashboard> {
    return this.api.get<PredictiveDashboard>(
      `/api/admin/reports/predictive/dashboard${this.toQuery(filters)}`
    );
  }

  getPredictiveHistory(filters: Required<Pick<PredictiveFilters, 'fecha_inicio' | 'fecha_fin'>> & PredictiveFilters): Observable<PredictiveHistory> {
    return this.api.get<PredictiveHistory>(
      `/api/admin/reports/predictive/history${this.toQuery(filters)}`
    );
  }

  getCustomerSegments(fechaCorte?: string, idSucursal?: number): Observable<CustomerSegments> {
    const query = this.toQuery({ fecha_corte: fechaCorte, id_sucursal: idSucursal });
    return this.api.get<CustomerSegments>(`/api/admin/reports/predictive/segments${query}`);
  }

  private toQuery(values: object): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if ((typeof value === 'string' && value !== '') || typeof value === 'number') {
        params.set(key, String(value));
      }
    }
    const query = params.toString();
    return query ? `?${query}` : '';
  }
}
