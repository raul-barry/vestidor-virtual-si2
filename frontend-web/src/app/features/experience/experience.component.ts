import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { API_URL } from '../../core/config/api.config';
import { ApiService } from '../../core/services/api.service';

@Component({standalone:true,imports:[CommonModule,FormsModule,RouterLink],
  styles:[`main{padding:2rem;max-width:1000px;margin:auto}form,.controls{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}label{display:grid}input,select,button{padding:.5rem}article{padding:1rem;border-bottom:1px solid #ddd}.stage{position:relative;width:360px;max-width:100%;height:500px;background:#edf0f3;overflow:hidden}.photo{width:100%;height:100%;object-fit:contain}.garment{position:absolute;width:180px;height:240px;transform-origin:center;pointer-events:none}.figure{width:100%;height:100%}table{width:100%}td,th{text-align:left;padding:.5rem}`],
  template:`<main><h1>{{mode === 'recommendations' ? 'Recomendados para ti' : mode === 'fitting' ? 'Vestidor virtual' : 'Seguridad: sesiones'}}</h1><p role="status">{{message}}</p>
    @if(mode === 'recommendations') {
      <form (ngSubmit)="load()"><label>Talla<input name="talla" [(ngModel)]="size" placeholder="M"></label><label>Color<input name="color" [(ngModel)]="color" placeholder="Azul"></label><label>Categoría<input name="categoria" [(ngModel)]="category" placeholder="Camisas"></label><button>Recomendar</button></form>
      @for(r of rows;track r.id_variante){<article><strong>{{r.nombre}}</strong> · {{r.talla}} · {{r.color}} · Bs {{r.precio}}<p>{{r.motivo}}</p><a [routerLink]="['/catalog/product',r.id_producto]">Ver prenda</a> · <button (click)="add(r.id_variante)">Agregar al carrito</button></article>} @empty {<p>No hay prendas disponibles.</p>}
    }
    @if(mode === 'fitting') {
      <p>Vista orientativa con el recurso visual del producto. Las prendas de prueba usan ilustraciones y no calculan el ajuste físico. Ajusta la imagen sobre tu foto o el maniquí; la foto permanece en tu dispositivo.</p>
      <label>Prenda compatible<select [(ngModel)]="variantId" [disabled]="busy" (ngModelChange)="selectionChanged()"><option [ngValue]="0">Seleccionar</option>@for(r of rows;track r.id_variante){<option [ngValue]="r.id_variante">{{r.nombre}} · {{r.talla}} · {{r.color}}</option>}</select></label>
      @if(!rows.length){<p>No hay prendas con recursos visuales disponibles.</p>}
      <button (click)="tryOn()" [disabled]="!variantId || busy">Probar prenda</button>
      <label>Foto opcional<input type="file" accept="image/png,image/jpeg,image/webp" (change)="photo($event)"></label><button (click)="clearPhoto()">Usar maniquí</button>
      <div class="controls"><label>Horizontal<input type="range" min="-100" max="280" [(ngModel)]="x"></label><label>Vertical<input type="range" min="0" max="400" [(ngModel)]="y"></label><label>Tamaño<input type="range" min="0.4" max="2.5" step="0.05" [(ngModel)]="scale"></label><label>Opacidad<input type="range" min="0.2" max="1" step="0.05" [(ngModel)]="opacity"></label></div>
      <div class="stage" aria-label="Vista de prueba virtual">
        @if(photoUrl){<img class="photo" [src]="photoUrl" alt="Tu foto para probar la prenda">} @else {
          <svg class="figure" viewBox="0 0 360 500" role="img" aria-label="Maniquí"><circle cx="180" cy="65" r="35" fill="#b6bdc9"/><path d="M135 110 L225 110 L255 260 L222 270 L210 210 L210 290 L235 470 L190 470 L180 320 L170 470 L125 470 L150 290 L150 210 L138 270 L105 260 Z" fill="#b6bdc9"/></svg>
        }
        @if(selected && resourceUrl){<img class="garment" [src]="resourceUrl" [alt]="selected.nombre" [style.left.px]="x" [style.top.px]="y" [style.transform]="'scale('+scale+')'" [style.opacity]="opacity" (error)="resourceFailed()" (load)="resourceLoaded()">}
      </div>
      @if(selected){<p>{{selected.nombre}} · {{selected.talla}} · {{selected.color}}</p><button (click)="add(selected.id_variante)">Agregar al carrito</button>}
    }
    @if(mode === 'security'){
      <h2>Asignaci?n de sucursal</h2>
      @for(u of staff; track u.id_usuario){<form (ngSubmit)="assign(u)"><span>{{u.nombre}} ? {{u.rol}}</span><select name="sucursal" [(ngModel)]="u.id_sucursal"><option [ngValue]="null">Sin asignaci?n</option>@for(b of branches;track b.id_sucursal){<option [ngValue]="b.id_sucursal">{{b.nombre}}</option>}</select><button [disabled]="busy">Guardar</button></form>}
      <h2>Sesiones</h2><button (click)="load()">Actualizar</button><table><tr><th>Usuario</th><th>Inicio</th><th>Expiración</th><th>Estado</th><th></th></tr>@for(r of rows;track r.id_sesion){<tr><td>{{r.id_usuario}}</td><td>{{r.inicio|date:'short'}}</td><td>{{r.expiracion|date:'short'}}</td><td>{{r.estado}}</td><td>@if(r.estado==='ACTIVA'){<button (click)="revoke(r.id_sesion)" [disabled]="busy">Revocar</button>}</td></tr>}</table>}
  </main>`})
export class ExperienceComponent implements OnInit, OnDestroy {
  private api=inject(ApiService);private route=inject(ActivatedRoute);
  mode='';rows:any[]=[];staff:any[]=[];branches:any[]=[];message='';size='';color='';category='';variantId=0;selected:any=null;busy=false;
  resourceUrl='';photoUrl='';x=90;y=110;scale=1;opacity=.85;
  ngOnInit():void{this.route.data.subscribe(d=>{this.mode=d['mode'];this.load();});}
  fail=(e:any):void=>{this.busy=false;this.message=e.error?.detail || e.error?.message || 'No se pudo completar la operación';};
  load():void{if(this.mode==='security')this.api.get<any>('/api/experience/staff').subscribe({next:r=>{this.staff=r.usuarios;this.branches=r.sucursales;},error:this.fail});const path=this.mode==='security'?'sessions':this.mode==='recommendations'?`recommendations?talla=${encodeURIComponent(this.size)}&color=${encodeURIComponent(this.color)}&categoria=${encodeURIComponent(this.category)}`:'fitting';this.api.get<any[]>('/api/experience/'+path).subscribe({next:r=>{this.rows=r;if(this.mode==='fitting'){const q=this.route.snapshot.queryParamMap;const product=Number(q.get('producto_id'));const variant=Number(q.get('variante_id'));const match=r.find(v=>v.id_producto===product && (!variant || v.id_variante===variant));if(match){this.variantId=match.id_variante;this.tryOn();}else if(product){this.message='El producto o la variante no tiene un recurso visual disponible o está agotado';}}},error:this.fail});}
  selectionChanged():void{this.selected=null;this.resourceUrl='';this.message='';}
  tryOn():void{
    const variant=this.rows.find(r=>r.id_variante===this.variantId);if(!variant)return;
    this.busy=true;this.selected=null;this.resourceUrl='';
    this.api.get<any>('/api/experience/virtual-fitting/'+variant.id_producto).subscribe({next:r=>{
      if(this.variantId!==variant.id_variante){this.busy=false;return;}
      const current=r.variantes.find((v:any)=>v.id_variante===this.variantId);
      if(!current){this.busy=false;this.message='La variante ya no está disponible';return;}
      const resource=r.recursos.find((asset:any)=>asset.tipo_recurso==='imagen');
      if(!resource){this.busy=false;this.message='No hay imagen disponible';return;}
      this.selected=current;this.resourceUrl=new URL(resource.url_archivo, API_URL).href;
      this.x=90;this.y=current.garment==='pants'?265:110;this.scale=1;this.message='Cargando recurso visual...';
      this.api.post('/api/experience/preferences',{tipo:'seleccion',id_producto:current.id_producto,id_variante:current.id_variante}).subscribe({error:()=>{}});
    },error:this.fail});
  }
  resourceLoaded():void{this.busy=false;this.message='Prenda lista para ajustar';}
  resourceFailed():void{this.busy=false;this.selected=null;this.resourceUrl='';this.message='No se pudo cargar la imagen de la prenda';}
  add(id:number):void{this.api.post('/api/cart/items',{id_variante:id,cantidad:1}).subscribe({next:()=>this.message='Prenda agregada al carrito',error:this.fail});}
  photo(event:Event):void{const file=(event.target as HTMLInputElement).files?.[0];if(!file)return;if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>10*1024*1024){this.message='Seleccione PNG, JPEG o WebP de hasta 10 MB';return;}this.clearPhoto();this.photoUrl=URL.createObjectURL(file);}
  clearPhoto():void{if(this.photoUrl)URL.revokeObjectURL(this.photoUrl);this.photoUrl='';}
  ngOnDestroy():void{this.clearPhoto();}
  assign(u:any):void{this.busy=true;this.api.put('/api/experience/staff/'+u.id_usuario,{id_sucursal:u.id_sucursal}).subscribe({next:()=>{this.busy=false;this.message='Sucursal asignada';},error:this.fail});}
  revoke(id:number):void{this.busy=true;this.api.delete('/api/experience/sessions/'+id).subscribe({next:()=>{this.busy=false;this.message='Sesión revocada';this.load();},error:this.fail});}
}
