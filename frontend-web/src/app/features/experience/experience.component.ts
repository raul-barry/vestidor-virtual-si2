import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { FittingThreeViewerComponent } from './components/fitting-three-viewer.component';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, FittingThreeViewerComponent],
  styleUrl: './experience.component.scss',
  template: `<main class="experience-page">
    @if (mode === 'recommendations') {
      <header class="experience-hero"><p class="eyebrow">CURADO PARA TI</p><h1>Prendas que combinan con tu estilo.</h1><p>Afina la selección con talla, color o categoría.</p></header>
      <form class="recommendation-filters" (ngSubmit)="load()"><label>Talla<input name="talla" [(ngModel)]="size" placeholder="M"></label><label>Color<input name="color" [(ngModel)]="color" placeholder="Azul"></label><label>Categoría<input name="categoria" [(ngModel)]="category" placeholder="Camisas"></label><button>Actualizar selección</button></form>
      <section class="recommendation-grid">@for(r of rows;track r.id_variante){<article><p class="eyebrow">{{r.motivo}}</p><h2>{{r.nombre}}</h2><p>{{r.talla}} · {{r.color}} · Bs {{r.precio}}</p><div><a [routerLink]="['/catalog/product',r.id_producto]">Ver prenda</a><button (click)="add(r.id_variante)">Añadir</button></div></article>} @empty {<p class="empty-copy">No hay prendas disponibles con esos criterios.</p>}</section>
    }
    @if (mode === 'fitting') {
      <header class="fitting-hero"><div><p class="eyebrow">EXPERIENCIA INMERSIVA</p><h1>Vestidor virtual <em>3D</em></h1><p>Explora la prenda sobre un avatar masculino, rota la vista 360°, acércala y combina cada selección con un accesorio.</p></div><div class="hero-stat"><strong>360°</strong><span>vista interactiva</span></div></header>
      <section class="fitting-layout"><app-fitting-three-viewer [garment]="selected" [accessory]="accessory" /><aside class="fitting-panel"><div class="panel-label">01 · SELECCIONA TU PRENDA</div><label>Prenda compatible<select [(ngModel)]="variantId" [disabled]="busy" (ngModelChange)="selectionChanged()"><option [ngValue]="0">Seleccionar prenda</option>@for(r of rows;track r.id_variante){<option [ngValue]="r.id_variante">{{r.nombre}} · {{r.talla}} · {{r.color}}</option>}</select></label><button class="try-button" (click)="tryOn()" [disabled]="!variantId || busy">{{busy ? 'Preparando vista…' : 'Probar en 3D'}}</button><div class="panel-label">02 · PERSONALIZA</div><label class="accessory-toggle"><input type="checkbox" [(ngModel)]="accessory"> <span>Agregar accesorio metálico</span></label><p class="viewer-help">Arrastra el avatar para rotar. Usa la rueda o gesto de pinza para acercar y alejar.</p>@if(selected){<div class="selection-summary"><p>SELECCIÓN ACTUAL</p><strong>{{selected.nombre}}</strong><span>{{selected.talla}} · {{selected.color}}</span><button (click)="add(selected.id_variante)">Agregar al carrito</button></div>} @if(!rows.length){<p class="empty-copy">No hay prendas con recursos virtuales disponibles.</p>}</aside></section>
      <p class="fitting-note">Vista demostrativa 3D. La visualización representa color y tipo de prenda; no calcula ajuste corporal físico.</p>
    }
    @if(mode === 'security'){
      <header class="experience-hero"><p class="eyebrow">CONTROL OPERATIVO</p><h1>Seguridad y asignaciones</h1></header><section class="security-card"><h2>Asignación de sucursal</h2>@for(u of staff; track u.id_usuario){<form (ngSubmit)="assign(u)"><span>{{u.nombre}} · {{u.rol}}</span><select name="sucursal" [(ngModel)]="u.id_sucursal"><option [ngValue]="null">Sin asignación</option>@for(b of branches;track b.id_sucursal){<option [ngValue]="b.id_sucursal">{{b.nombre}}</option>}</select><button [disabled]="busy">Guardar</button></form>}</section><section class="security-card"><div class="section-heading"><h2>Sesiones</h2><button (click)="load()">Actualizar</button></div><div class="table-scroll" role="region" aria-label="Tabla de sesiones" tabindex="0"><table><tr><th>Usuario</th><th>Inicio</th><th>Expiración</th><th>Estado</th><th></th></tr>@for(r of rows;track r.id_sesion){<tr><td>{{r.id_usuario}}</td><td>{{r.inicio|date:'short'}}</td><td>{{r.expiracion|date:'short'}}</td><td>{{r.estado}}</td><td>@if(r.estado==='ACTIVA'){<button (click)="revoke(r.id_sesion)" [disabled]="busy">Revocar</button>}</td></tr>}</table></div></section>
    }
    @if(message){<p class="status-message" role="status">{{message}}</p>}
  </main>`
})
export class ExperienceComponent implements OnInit, OnDestroy {
  private api = inject(ApiService); private route = inject(ActivatedRoute);
  mode = ''; rows: any[] = []; staff: any[] = []; branches: any[] = []; message = ''; size = ''; color = ''; category = ''; variantId = 0; selected: any = null; busy = false; accessory = false;
  ngOnInit(): void { this.route.data.subscribe(data => { this.mode = data['mode']; this.load(); }); }
  fail = (e: any): void => { this.busy = false; this.message = e.error?.detail || e.error?.message || 'No se pudo completar la operación'; };
  load(): void {
    if (this.mode === 'security') this.api.get<any>('/api/experience/staff').subscribe({next: result => { this.staff = result.usuarios; this.branches = result.sucursales; }, error: this.fail});
    const path = this.mode === 'security' ? 'sessions' : this.mode === 'recommendations' ? `recommendations?talla=${encodeURIComponent(this.size)}&color=${encodeURIComponent(this.color)}&categoria=${encodeURIComponent(this.category)}` : 'fitting';
    this.api.get<any[]>('/api/experience/' + path).subscribe({next: result => { this.rows = result; if (this.mode === 'fitting') { const product = Number(this.route.snapshot.queryParamMap.get('producto_id')); const variant = Number(this.route.snapshot.queryParamMap.get('variante_id')); const selected = result.find(row => row.id_producto === product && (!variant || row.id_variante === variant)); if (selected) { this.variantId = selected.id_variante; this.tryOn(); } else if (product) this.message = 'Esta prenda no tiene una variante disponible para el vestidor.'; }}, error: this.fail});
  }
  selectionChanged(): void { this.selected = null; this.message = ''; }
  tryOn(): void { const selected = this.rows.find(row => row.id_variante === this.variantId); if (!selected) return; this.busy = true; this.selected = null; this.api.post<any>('/api/experience/fitting', {id_variante: selected.id_variante}).subscribe({next: view => { this.selected = {...selected, ...view}; this.busy = false; this.message = 'Vista 3D lista. Explora el avatar y añade la prenda si te gusta.'; this.api.post('/api/experience/preferences', {tipo: 'seleccion', id_producto: selected.id_producto, id_variante: selected.id_variante}).subscribe({error: () => {}});}, error: this.fail}); }
  add(id: number): void { this.api.post('/api/cart/items', {id_variante: id, cantidad: 1}).subscribe({next: () => this.message = 'Prenda agregada al carrito.', error: this.fail}); }
  assign(user: any): void { this.busy = true; this.api.put('/api/experience/staff/' + user.id_usuario, {id_sucursal: user.id_sucursal}).subscribe({next: () => { this.busy = false; this.message = 'Sucursal asignada.'; }, error: this.fail}); }
  revoke(id: number): void { this.busy = true; this.api.delete('/api/experience/sessions/' + id).subscribe({next: () => { this.busy = false; this.message = 'Sesión revocada.'; this.load(); }, error: this.fail}); }
  ngOnDestroy(): void {}
}
