import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import { Chart } from 'chart.js/auto';
import { SalesReport } from '../../models/report.model';

@Component({
  selector: 'app-sales-chart',
  standalone: true,
  template: '<canvas #canvas aria-label="Gráfico de ventas"></canvas>',
  styleUrl: './sales-chart.component.scss'
})
export class SalesChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) sales!: SalesReport;
  @ViewChild('canvas') private canvas!: ElementRef<HTMLCanvasElement>;
  private chart: Chart | null = null;

  ngAfterViewInit(): void { this.renderChart(); }
  ngOnChanges(): void { if (this.chart) this.renderChart(); }
  ngOnDestroy(): void { this.chart?.destroy(); }

  private renderChart(): void {
    this.chart?.destroy();
    this.chart = new Chart(this.canvas.nativeElement, {
      type: 'bar',
      data: {
        labels: ['Ventas del período', 'Compra promedio'],
        datasets: [{ label: 'Bs', data: [Number(this.sales.ventas_totales), Number(this.sales.promedio_compra)], backgroundColor: ['#4f46e5', '#0f766e'] }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
  }
}
