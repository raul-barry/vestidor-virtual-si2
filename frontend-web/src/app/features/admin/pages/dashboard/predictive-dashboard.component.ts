import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import {
  CustomerSegments,
  PredictiveDashboard,
  PredictiveFilters,
  PredictiveHistory,
  PredictiveFeatures,
  ReportBranch,
} from '../../models/report.model';
import { AdminReportService } from '../../services/admin-report.service';

@Component({
  selector: 'app-predictive-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './predictive-dashboard.component.html',
  styleUrl: './predictive-dashboard.component.scss',
})
export class PredictiveDashboardComponent implements OnInit {
  private readonly reports = inject(AdminReportService);

  features: PredictiveFeatures = {
    machine_learning: false,
    prediccion_demanda: false,
    segmentacion_kmeans: false,
    dashboard_predictivo: false,
  };
  branches: ReportBranch[] = [];
  dashboard: PredictiveDashboard | null = null;
  history: PredictiveHistory | null = null;
  segments: CustomerSegments | null = null;
  startDate = this.defaultStartDate();
  endDate = new Date().toISOString().slice(0, 10);
  selectedBranch = '';
  selectedProduct = '';
  isLoading = true;
  isRefreshing = false;
  error = '';

  ngOnInit(): void {
    forkJoin({
      features: this.reports.getPredictiveFeatures(),
      branches: this.reports.getBranches(),
    }).subscribe({
      next: ({ features, branches }) => {
        this.features = features;
        this.branches = branches;
        this.isLoading = false;
        if (features['dashboard_predictivo']) this.refresh();
        if (features['segmentacion_kmeans']) this.refreshSegments();
      },
      error: () => {
        this.isLoading = false;
        this.error = 'No fue posible consultar las capacidades del dashboard predictivo.';
      },
    });
  }

  refresh(): void {
    if (!this.features['dashboard_predictivo']) return;
    this.error = '';
    this.isRefreshing = true;
    const filters: PredictiveFilters = {
      fecha_inicio: this.startDate || undefined,
      fecha_fin: this.endDate || undefined,
      id_sucursal: this.selectedBranch ? Number(this.selectedBranch) : undefined,
      id_producto: this.selectedProduct ? Number(this.selectedProduct) : undefined,
    };
    if (!filters.fecha_inicio || !filters.fecha_fin) {
      this.isRefreshing = false;
      this.error = 'Selecciona el inicio y fin del período.';
      return;
    }
    forkJoin({
      dashboard: this.reports.getPredictiveDashboard(filters),
      history: this.reports.getPredictiveHistory({
        ...filters,
        fecha_inicio: filters.fecha_inicio,
        fecha_fin: filters.fecha_fin,
      }),
    }).subscribe({
      next: ({ dashboard, history }) => {
        this.dashboard = dashboard;
        this.history = history;
        this.isRefreshing = false;
      },
      error: (error: { error?: { detail?: unknown } }) => {
        this.error = typeof error.error?.detail === 'string'
          ? error.error.detail
          : 'No fue posible calcular las predicciones.';
        this.isRefreshing = false;
      },
    });
    if (this.features['segmentacion_kmeans']) this.refreshSegments();
  }

  refreshSegments(): void {
    if (!this.features['segmentacion_kmeans']) return;
    this.reports.getCustomerSegments(
      this.endDate || undefined,
      this.selectedBranch ? Number(this.selectedBranch) : undefined,
    ).subscribe({
      next: (segments) => { this.segments = segments; },
      error: () => { this.error = 'No fue posible calcular la segmentación de clientes.'; },
    });
  }

  onFiltersChanged(): void {
    if (this.features['dashboard_predictivo']) this.refresh();
    else this.refreshSegments();
  }

  get productOptions(): Array<{ id: number; name: string }> {
    const unique = new Map<number, string>();
    for (const prediction of this.dashboard?.predicciones ?? []) {
      unique.set(prediction.producto_id, prediction.producto);
    }
    return [...unique].map(([id, name]) => ({ id, name }));
  }

  get maxPredictedDemand(): number {
    return Math.max(1, ...(this.dashboard?.predicciones ?? [])
      .map((item) => item.prediccion_7_dias?.demanda_esperada ?? 0));
  }

  get maxHistoryDemand(): number {
    return Math.max(1, ...(this.history?.resultados ?? [])
      .map((item) => Math.max(item.demanda_predicha, item.demanda_real)));
  }

  barWidth(value: number, maximum: number): number {
    return Math.max(value > 0 ? 2 : 0, Math.min(100, value / maximum * 100));
  }

  private defaultStartDate(): string {
    const start = new Date();
    start.setDate(start.getDate() - 179);
    return start.toISOString().slice(0, 10);
  }
}
