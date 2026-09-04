import { AfterViewInit, Component, ElementRef, Input, OnChanges, OnDestroy, ViewChild } from '@angular/core';
import { Chart } from 'chart.js/auto';
import { CategoryRanking } from '../../models/report.model';

@Component({
  selector: 'app-category-chart',
  standalone: true,
  template: '<canvas #canvas aria-label="Gráfico de categorías más vendidas"></canvas>',
  styleUrl: './category-chart.component.scss'
})
export class CategoryChartComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) categories: CategoryRanking[] = [];
  @ViewChild('canvas') private canvas!: ElementRef<HTMLCanvasElement>;
  private chart: Chart | null = null;

  ngAfterViewInit(): void { this.renderChart(); }
  ngOnChanges(): void { if (this.chart) this.renderChart(); }
  ngOnDestroy(): void { this.chart?.destroy(); }

  private renderChart(): void {
    this.chart?.destroy();
    this.chart = new Chart(this.canvas.nativeElement, {
      type: 'doughnut',
      data: { labels: this.categories.map((category) => category.categoria), datasets: [{ data: this.categories.map((category) => category.cantidad_vendida), backgroundColor: ['#4f46e5', '#0f766e', '#f59e0b', '#e11d48', '#0284c7'] }] },
      options: { responsive: true, maintainAspectRatio: false }
    });
  }
}
