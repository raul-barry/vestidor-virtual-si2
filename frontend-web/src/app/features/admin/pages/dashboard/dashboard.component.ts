import { Component, OnInit, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { CategoryChartComponent } from '../../components/category-chart/category-chart.component';
import { SalesChartComponent } from '../../components/sales-chart/sales-chart.component';
import { TopProductsChartComponent } from '../../components/top-products-chart/top-products-chart.component';
import { CategoryRanking, DashboardReport, ProductRanking, SalesReport } from '../../models/report.model';
import { AdminReportService } from '../../services/admin-report.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [MatCardModule, MatProgressSpinnerModule, MatSnackBarModule, SalesChartComponent, TopProductsChartComponent, CategoryChartComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  private readonly reportService = inject(AdminReportService);
  private readonly snackBar = inject(MatSnackBar);

  dashboard: DashboardReport | null = null;
  sales: SalesReport | null = null;
  topProducts: ProductRanking[] = [];
  topCategories: CategoryRanking[] = [];
  isLoading = true;
  hasError = false;

  ngOnInit(): void {
    forkJoin({
      dashboard: this.reportService.getDashboard(),
      sales: this.reportService.getSales(),
      products: this.reportService.getTopProducts(),
      categories: this.reportService.getTopCategories(),
      inventory: this.reportService.getInventory(),
      customers: this.reportService.getCustomers()
    }).subscribe({
      next: (reports) => {
        this.dashboard = reports.dashboard;
        this.sales = reports.sales;
        this.topProducts = reports.products;
        this.topCategories = reports.categories;
        this.isLoading = false;
      },
      error: (error: { error?: { message?: string } }) => {
        this.isLoading = false;
        this.hasError = true;
        this.snackBar.open(error.error?.message ?? 'No fue posible cargar los reportes', 'Cerrar', { duration: 5000 });
      }
    });
  }
}
