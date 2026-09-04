import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import {
  CategoryRanking,
  CustomerReport,
  DashboardReport,
  InventoryReport,
  ProductRanking,
  SalesReport
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
}
