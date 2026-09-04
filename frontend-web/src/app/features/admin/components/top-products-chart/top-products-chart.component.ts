import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import { Chart } from 'chart.js/auto';
import { ProductRanking } from '../../models/report.model';

@Component({
  selector: 'app-top-products-chart',
  standalone: true,
  template: '<canvas #canvas aria-label="Gráfico de productos más vendidos"></canvas>',
  styleUrl: './top-products-chart.component.scss'
})
export class TopProductsChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) products: ProductRanking[] = [];
  @ViewChild('canvas') private canvas!: ElementRef<HTMLCanvasElement>;
  private chart: Chart | null = null;

  ngAfterViewInit(): void { this.renderChart(); }
  ngOnChanges(): void { if (this.chart) this.renderChart(); }
  ngOnDestroy(): void { this.chart?.destroy(); }

  private renderChart(): void {
    this.chart?.destroy();
    this.chart = new Chart(this.canvas.nativeElement, {
      type: 'bar',
      data: { labels: this.products.map((product) => product.producto), datasets: [{ label: 'Unidades', data: this.products.map((product) => product.cantidad_vendida), backgroundColor: '#4f46e5' }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
  }
}
