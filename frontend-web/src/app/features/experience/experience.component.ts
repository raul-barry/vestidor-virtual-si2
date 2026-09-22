import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { ApiService } from '../../core/services/api.service';
import { API_URL } from '../../core/config/api.config';
import { FittingThreeViewerComponent } from './components/fitting-three-viewer.component';
import { PreferredSizeResolver } from './services/preferred-size-resolver.service';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatButtonModule, FittingThreeViewerComponent],
  styleUrl: './experience.component.scss',
  template: `
    <main class="experience-page">
      @if (mode === 'recommendations') {
        <div class="recommendation-shell">
          <section class="recommendation-content" aria-labelledby="recommendations-title">
            <header class="experience-hero recommendation-hero">
              <div><p class="eyebrow">PERSONALIZADO PARA TI</p><h1 id="recommendations-title">Recomendaciones para ti</h1><p>Estas recomendaciones están basadas en tu perfil, tallas, colores preferidos, estilos e historial de interacción.</p></div>
            </header>
            @if (profileSummaryVisible) { <div class="profile-summary"><strong>Tu perfil</strong><span>Talla: {{ profileSize || '—' }}</span><span>Colores: {{ profileColors || '—' }}</span><span>Estilo: {{ profileStyles || '—' }}</span></div> }
            <p class="status-message-inline" role="status">{{ recommendationMessage }}</p>
            <div class="recommendation-grid">
              @for (r of recommendationRows; track r.id_variante) {
                <article class="recommendation-card">
                  <img class="recommendation-image" [src]="imageUrl(r)" [alt]="r.nombre" (error)="useFallbackImage($event)" />
                  <div class="recommendation-card-body"><p class="card-kicker">{{ r.categoria || 'SELECCIÓN FASHION STORE' }}</p><h2>{{ r.nombre }}</h2><p class="variant-line">Talla {{ r.talla }} · {{ r.color }}</p><strong class="price">Bs {{ r.precio }}</strong><p class="reason">{{ r.motivo }}</p><div class="card-actions"><a mat-button [routerLink]="['/catalog/product', r.id_producto]">Ver producto</a><a mat-button [routerLink]="['/experience/fitting']" [queryParams]="{producto_id:r.id_producto,variante_id:r.id_variante,talla:r.talla,color:r.color}">Probar en vestidor</a><button mat-flat-button color="primary" (click)="add(r.id_variante)">Agregar</button></div></div>
                </article>
              } @empty { <p class="empty-copy">No encontramos recomendaciones disponibles.</p> }
            </div>
            <a class="catalog-cta" mat-flat-button color="primary" routerLink="/catalog">Ver más en catálogo</a>
            <p class="ai-prompt">¿Quieres más opciones? Pregunta a Fashion AI.</p>
          </section>
          <aside class="fashion-ai" aria-labelledby="fashion-ai-title"><p class="eyebrow">TU ASESOR</p><h2 id="fashion-ai-title">FASHION AI</h2><p class="assistant-intro">Asistente personal de moda</p><p class="assistant-reply">{{ assistantReply || 'Cuéntame qué buscas y te ayudaré a encontrar tu próximo look.' }}</p><input [(ngModel)]="assistantQuery" (keyup.enter)="askAssistant()" placeholder="Escribe aquí..." aria-label="Pregunta a Fashion AI"><button mat-flat-button color="primary" (click)="askAssistant()" [disabled]="assistantLoading">{{ assistantLoading ? 'Buscando…' : 'Enviar' }}</button>@if (assistantError) { <p class="assistant-error">{{ assistantError }}</p> }@if (assistantRows.length) { <div class="assistant-results"><p class="assistant-label">Opciones sugeridas</p>@for (r of assistantRows.slice(0,4); track r.id_variante) { <article><strong>{{ r.nombre }}</strong><span>Talla {{ r.talla }} · {{ r.color }} · Bs {{ r.precio }}</span><small>{{ r.motivo }}</small><a [routerLink]="['/catalog/product',r.id_producto]">Ver producto</a></article> }</div> }</aside>
        </div>
      }
      @if (mode === 'fitting') {
        <header class="fitting-hero"><h1>Vestidor virtual 3D</h1></header>@if (!bodyProfile && !genericAvatar) { <section class="security-card"><p>No tienes un perfil corporal configurado.</p><a routerLink="/profile/body">Crear mi perfil corporal</a><button (click)="genericAvatar=true">Continuar con avatar genérico</button></section> }<section class="fitting-layout"><app-fitting-three-viewer [garment]="selected" [accessory]="accessory" [bodyProfile]="bodyProfile"/><aside class="fitting-panel"><label>Prenda<select [(ngModel)]="variantId" (ngModelChange)="selectionChanged()"><option [ngValue]="0">Seleccionar prenda</option>@for (r of rows; track r.id_variante) { <option [ngValue]="r.id_variante">{{ r.nombre }} · {{ r.talla }} · {{ r.color }}</option> }</select></label><p>{{ sizeWarning }}</p><button (click)="tryOn()" [disabled]="!variantId || busy">Probar en 3D</button><div class="photo-try-on"><h2>Probador con tu foto</h2><p class="fitting-note">Toma una foto frontal con buena luz y deja visible la prenda completa.</p><label class="camera-button">{{ photoBusy ? 'Editando foto…' : 'Tomar foto y probar' }}<input type="file" accept="image/jpeg,image/png,image/webp" capture="user" [disabled]="!variantId || photoBusy" (change)="tryOnPhoto($any($event.target).files?.[0])"></label>@if (photoError) { <p class="photo-error" role="alert">{{ photoError }}</p> }@if (photoResult) { <img class="photo-result" [src]="photoResult" alt="Resultado del probador virtual con la prenda puesta"> }</div>@if (selected) { <p>{{ selected.talla }} · {{ selected.color }}</p><button (click)="add(selected.id_variante)">Agregar al carrito</button> }</aside></section><p class="fitting-note">Representación visual aproximada. No constituye una simulación física exacta del ajuste de la prenda.</p>
      }
    </main>`
})
export class ExperienceComponent implements OnInit {
  private api = inject(ApiService); private route = inject(ActivatedRoute);
  mode = ''; rows: any[] = []; recommendationRows: any[] = []; selected: any = null; variantId = 0; bodyProfile: any = null; preferences: any = {}; genericAvatar = false; accessory = false; busy = false; photoBusy = false; photoResult = ''; photoError = ''; sizeWarning = ''; recommendationMessage = 'Cargando recomendaciones...'; assistantQuery = ''; assistantReply = ''; assistantRows: any[] = []; assistantLoading = false; assistantError = '';
  ngOnInit(): void { this.api.get('/api/body-profile').subscribe({ next: p => this.bodyProfile = p, error: () => this.bodyProfile = null }); this.api.get('/api/users/profile/preferences').subscribe({ next: p => this.preferences = p, error: () => {} }); this.route.data.subscribe(d => { this.mode = d['mode']; this.load(); }); }
  get profileSize(): string { return this.preferences.talla_superior || this.preferences.talla_pantalon || ''; }
  get profileColors(): string { return (this.preferences.colores || []).join(', '); }
  get profileStyles(): string { return (this.preferences.estilos || []).join(', '); }
  get profileSummaryVisible(): boolean { return !!(this.profileSize || this.profileColors || this.profileStyles); }
  imageUrl(row: any): string { return row.imagen_url || `${API_URL}/assets/catalog/catalog-prenda-${row.id_producto}.png`; }
  useFallbackImage(event: Event): void { const image = event.target as HTMLImageElement; image.onerror = null; image.src = `${API_URL}/assets/catalog/catalog-prenda-1.png`; }
  load(): void { const path = this.mode === 'recommendations' ? 'recommendations' : 'fitting'; this.api.get<any[]>('/api/experience/' + path).subscribe({ next: rows => { this.rows = rows; if (this.mode === 'recommendations') { this.recommendationRows = rows.slice(0, 4); this.recommendationMessage = rows.length ? '' : 'No hay prendas disponibles.'; } else this.applyInitialSelection(); }, error: e => { this.recommendationMessage = e.error?.detail || 'No fue posible cargar las recomendaciones.'; this.assistantError = this.recommendationMessage; } }); }
  private valid(v: any): boolean { return !!v && v.estado !== 'INACTIVO' && v.stock_disponible !== 0; }
  private applyInitialSelection(): void { const q = this.route.snapshot.queryParamMap; const product = Number(q.get('producto_id')); const requested = Number(q.get('variante_id')); const candidates = this.rows.filter(x => !product || x.id_producto === product); let v = candidates.find(x => x.id_variante === requested && this.valid(x)); if (!v) { const size = q.get('talla'), color = q.get('color'); v = candidates.find(x => this.valid(x) && (!size || x.talla === size) && (!color || x.color === color)); } if (!v && candidates.length) { const result = PreferredSizeResolver.resolve(candidates[0], this.preferences, candidates); v = result.variant; this.sizeWarning = result.warning || ''; } if (!v && !requested && !q.get('talla')) v = candidates.find(x => this.valid(x)); if (v) { this.variantId = v.id_variante; this.tryOn(); } }
  selectionChanged(): void { this.selected = null; this.photoResult = ''; this.photoError = ''; this.sizeWarning = ''; }
  tryOnPhoto(file: File | undefined): void {
    if (!file || !this.variantId || this.photoBusy) return;
    const variant = this.rows.find(x => x.id_variante === this.variantId);
    if (!this.valid(variant)) { this.photoError = 'Selecciona una prenda disponible.'; return; }
    this.photoBusy = true; this.photoResult = ''; this.photoError = '';
    const form = new FormData();
    form.append('product_id', String(variant.id_producto));
    form.append('variant_id', String(variant.id_variante));
    form.append('photo', file, file.name || 'foto.jpg');
    this.api.post<any>('/api/experience/virtual-try-on', form).subscribe({
      next: result => { this.photoResult = `data:${result.mime_type || 'image/png'};base64,${result.image_base64}`; this.photoBusy = false; },
      error: error => { this.photoError = error.error?.detail || 'No fue posible editar la foto.'; this.photoBusy = false; },
    });
  }
  tryOn(): void { const v = this.rows.find(x => x.id_variante === this.variantId); if (!this.valid(v)) { this.sizeWarning = 'La variante no está disponible actualmente.'; return; } this.busy = true; this.api.post<any>('/api/experience/fitting', { id_variante: v.id_variante }).subscribe({ next: x => { this.selected = { ...v, ...x }; this.busy = false; }, error: () => this.busy = false }); }
  add(id: number): void { const v = this.rows.find(x => x.id_variante === id); if (!this.valid(v) && this.mode === 'fitting') { this.sizeWarning = 'La variante no está disponible actualmente.'; return; } this.api.post('/api/cart/items', { id_variante: id, cantidad: 1 }).subscribe(); }
  askAssistant(): void { if (!this.assistantQuery.trim()) return; this.assistantLoading = true; this.assistantError = ''; this.api.post<any>('/api/experience/fashion-assistant', { mensaje: this.assistantQuery }).subscribe({ next: r => { this.assistantRows = r.recomendaciones || []; this.assistantReply = r.respuesta; this.assistantLoading = false; }, error: e => { this.assistantLoading = false; this.assistantError = e.error?.detail || 'No fue posible consultar'; } }); }
}
