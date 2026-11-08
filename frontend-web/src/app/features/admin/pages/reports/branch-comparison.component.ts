import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminReportService } from '../../services/admin-report.service';
import { BranchComparisonFilters, BranchSalesComparison, ReportBranch } from '../../models/report.model';

type SortKey = 'sucursal' | 'ingresos_netos' | 'cantidad_ventas' | 'ticket_promedio' | 'variacion_porcentual';

@Component({
  selector: 'app-branch-comparison',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './branch-comparison.component.html',
  styleUrl: './branch-comparison.component.scss',
})
export class BranchComparisonComponent implements OnInit {
  private readonly reports = inject(AdminReportService);
  readonly today = new Date().toISOString().slice(0, 10);
  dateFrom = this.defaultStart();
  dateTo = this.today;
  branches: ReportBranch[] = [];
  selectedBranches: number[] = [];
  result: BranchSalesComparison | null = null;
  loading = true;
  refreshing = false;
  exporting: 'pdf' | 'xlsx' | null = null;
  allowed = false;
  exportAllowed = false;
  error = '';
  sortKey: SortKey = 'ingresos_netos';
  sortDescending = true;

  ngOnInit(): void {
    this.reports.getBranchComparisonAccess().subscribe({
      next: (access) => {
        this.allowed = access.comparacion_sucursales;
        this.exportAllowed = access.exportacion_pdf_excel;
        if (!this.allowed) { this.loading = false; return; }
        this.reports.getComparisonBranches().subscribe({
          next: (branches) => { this.branches = branches; this.refresh(); },
          error: () => { this.error = 'No fue posible cargar las sucursales autorizadas.'; this.loading = false; },
        });
      },
      error: () => { this.error = 'No fue posible comprobar el permiso para comparar sucursales.'; this.loading = false; },
    });
  }

  refresh(): void {
    if (this.refreshing || !this.allowed) return;
    this.error = '';
    this.refreshing = true;
    this.reports.getBranchSalesComparison(this.filters()).subscribe({
      next: (result) => { this.result = result; this.refreshing = false; this.loading = false; },
      error: (error: { error?: { detail?: unknown } }) => {
        const detail = error.error?.detail;
        this.error = typeof detail === 'string' ? detail : 'No fue posible actualizar la comparación.';
        this.refreshing = false;
        this.loading = false;
      },
    });
  }

  export(format: 'pdf' | 'xlsx'): void {
    if (!this.result || this.exporting) return;
    this.exporting = format;
    this.reports.exportBranchSalesComparison(this.filters(), format).subscribe({
      next: (file) => {
        const url = URL.createObjectURL(file);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `fashionstore-comparacion-sucursales-${this.result?.periodo.desde}-${this.result?.periodo.hasta}.${format}`;
        anchor.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        this.exporting = null;
      },
      error: () => { this.error = `No fue posible generar ${format.toUpperCase()}.`; this.exporting = null; },
    });
  }

  sortBy(key: SortKey): void {
    if (this.sortKey === key) this.sortDescending = !this.sortDescending;
    else { this.sortKey = key; this.sortDescending = key !== 'sucursal'; }
  }

  get sortedRows(): NonNullable<BranchSalesComparison['sucursales']> {
    const rows = [...(this.result?.sucursales ?? [])];
    const multiplier = this.sortDescending ? -1 : 1;
    return rows.sort((a, b) => {
      const left = a[this.sortKey];
      const right = b[this.sortKey];
      if (typeof left === 'string' && typeof right === 'string' && this.sortKey === 'sucursal') {
        return left.localeCompare(right) * multiplier;
      }
      return ((Number(left) || 0) - (Number(right) || 0)) * multiplier;
    });
  }

  branchName(id: number | null): string {
    return this.result?.sucursales.find((row) => row.id_sucursal === id)?.sucursal ?? 'Sin datos';
  }

  barWidth(value: string): number {
    const values = this.result?.sucursales.flatMap((row) => [Number(row.ingresos_netos), Number(row.ingresos_periodo_anterior)]) ?? [];
    const max = Math.max(...values, 0);
    return max > 0 ? Math.max(0, Math.min(100, Number(value) / max * 100)) : 0;
  }

  money(value: string | number): string {
    return new Intl.NumberFormat('es-BO', { style: 'currency', currency: 'BOB', maximumFractionDigits: 2 }).format(Number(value));
  }

  private filters(): BranchComparisonFilters {
    return { fecha_inicio: this.dateFrom, fecha_fin: this.dateTo, id_sucursal: [...this.selectedBranches] };
  }

  private defaultStart(): string {
    const start = new Date();
    start.setDate(start.getDate() - 29);
    return start.toISOString().slice(0, 10);
  }
}
