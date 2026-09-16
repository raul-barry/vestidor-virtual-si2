import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

interface Recommendation {
  id_producto: number;
  id_variante: number;
  nombre: string;
  talla: string;
  color: string;
  precio: number;
  motivo: string;
}

@Component({
  selector: 'app-recommendations-section',
  standalone: true,
  imports: [RouterLink],
  styles: [`section{margin:2rem 0} .items{display:flex;gap:1rem;flex-wrap:wrap} article{border:1px solid #ddd;padding:1rem;flex:1 1 220px} a{color:#2457a6}`],
  template: `<section aria-labelledby="recommendations-title"><h2 id="recommendations-title">Recomendados para ti</h2>
    <p role="status">{{message}}</p>
    <div class="items">@for (item of rows; track item.id_producto) {
      <article><h3>{{item.nombre}}</h3><p>{{item.talla}} · {{item.color}} · Bs {{item.precio}}</p>
        <p>{{item.motivo}}</p><a [routerLink]="['/catalog/product', item.id_producto]">Ver producto</a>
      </article>
    }</div>
    <a routerLink="/experience/recommendations">Ajustar recomendaciones</a>
  </section>`
})
export class RecommendationsSectionComponent implements OnInit {
  private readonly api = inject(ApiService);
  rows: Recommendation[] = [];
  message = 'Cargando recomendaciones...';
  ngOnInit(): void {
    this.api.get<Recommendation[]>('/api/experience/recommendations').subscribe({
      next: rows => {this.rows = rows.slice(0, 6); this.message = rows.length ? '' : 'No hay prendas disponibles.';},
      error: () => this.message = 'No se pudieron cargar las recomendaciones.'
    });
  }
}
